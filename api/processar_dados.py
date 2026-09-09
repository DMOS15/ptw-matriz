import json
import hashlib
import hmac
import os
import secrets
import tempfile
from io import BytesIO
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get('PTW_DATA_DIR', Path(tempfile.gettempdir()) / 'ptw_dados'))
PIN_ADMIN = os.environ.get('PTW_ADMIN_PIN', 'JDEPIU')
MAX_ATTEMPTS = 3
BLOCK_MINUTES = 5
LOGIN_FAILURES = {}
HISTORY_FILE = Path(tempfile.gettempdir()) / 'ptw_historico_atualizacoes.json'
HISTORY_REPO_PATH = 'dados/historico_atualizacoes.json'
UPLOAD_METADATA_PATH = 'dados/uploads/arquivos_atuais.json'
CURRENT_UPLOAD_PATHS = {
    'treinamentos': 'dados/uploads/treinamentos_atual.xlsx',
    'matriz': 'dados/uploads/responsaveis_supervisores_atual.xlsx',
    'responsaveis': 'dados/uploads/responsaveis_supervisores_atual.xlsx',
    'supervisores': 'dados/uploads/responsaveis_supervisores_atual.xlsx'
}
TOKEN_SECRET = os.environ.get('PTW_TOKEN_SECRET', 'ptw-development-secret-change-me')
JSON_FILES = (
    'solicitantes.json',
    'responsaveis.json',
    'supervisores_altura.json',
    'supervisores_quente.json',
    'supervisores_confinado.json'
)

try:
    from api import conversor
except ImportError:
    import conversor

app = Flask(__name__)
CORS(app)


def _json_error(message, status=400):
    return jsonify({'sucesso': False, 'mensagem': message}), status


def _token_ok():
    token = request.headers.get('X-Admin-Token', '')
    try:
        issued, signature = token.rsplit('.', 1)
        expected = hmac.new(TOKEN_SECRET.encode(), issued.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(signature, expected)
    except ValueError:
        return False


def _history(tipo, filename, success, message, count=0):
    now = datetime.now()
    try:
        entries = json.loads(HISTORY_FILE.read_text(encoding='utf-8')) if HISTORY_FILE.exists() else []
    except (OSError, json.JSONDecodeError):
        entries = []
    if not entries:
        try:
            repository, branch = _github_repository()
            if repository:
                content = repository.get_contents(HISTORY_REPO_PATH, ref=branch)
                entries = json.loads(content.decoded_content.decode('utf-8'))
        except (OSError, ValueError, json.JSONDecodeError):
            entries = []
    entries.insert(0, {
        'data': now.isoformat(timespec='seconds'),
        'hora': now.strftime('%H:%M:%S'),
        'tipo': tipo,
        'arquivo': filename,
        'sucesso': success,
        'mensagem': message,
        'registros': count,
        'usuario': 'Admin'
    })
    try:
        HISTORY_FILE.write_text(json.dumps(entries[:100], ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError:
        pass
    try:
        repository, branch = _github_repository()
        if repository:
            serialized = json.dumps(entries[:100], ensure_ascii=False, indent=2)
            try:
                current = repository.get_contents(HISTORY_REPO_PATH, ref=branch)
                repository.update_file(HISTORY_REPO_PATH, f'Histórico PTW: {tipo}', serialized, current.sha, branch=branch)
            except Exception:
                repository.create_file(HISTORY_REPO_PATH, f'Histórico PTW: {tipo}', serialized, branch=branch)
    except Exception:
        pass


def _save_json(name, data):
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _load_upload_metadata():
    local_file = DATA_DIR / 'uploads' / 'arquivos_atuais.json'
    if local_file.exists():
        try:
            return json.loads(local_file.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            pass
    repository, branch = _github_repository()
    if repository:
        try:
            content = repository.get_contents(UPLOAD_METADATA_PATH, ref=branch)
            return json.loads(content.decoded_content.decode('utf-8'))
        except Exception:
            pass
    return {}


def salvar_upload_atual(source, tipo, filename):
    upload_dir = DATA_DIR / 'uploads'
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_name = Path(CURRENT_UPLOAD_PATHS[tipo]).name
    (upload_dir / target_name).write_bytes(source.read_bytes())
    metadata = _load_upload_metadata()
    now = datetime.now()
    metadata[tipo] = {
        'arquivo': filename,
        'data': now.strftime('%d/%m/%Y'),
        'hora': now.strftime('%H:%M'),
        'tamanho': source.stat().st_size,
        'caminho': CURRENT_UPLOAD_PATHS[tipo]
    }
    local_metadata = upload_dir / 'arquivos_atuais.json'
    local_metadata.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')


def publicar_uploads_atuais(data_dir, repository, branch, message):
    upload_dir = data_dir / 'uploads'
    if not upload_dir.exists():
        return
    for source in upload_dir.iterdir():
        if not source.is_file():
            continue
        path = f'dados/uploads/{source.name}'
        content = source.read_bytes() if source.suffix.lower() == '.xlsx' else source.read_text(encoding='utf-8')
        try:
            current = repository.get_contents(path, ref=branch)
            repository.update_file(path, message, content, current.sha, branch=branch)
        except Exception:
            repository.create_file(path, message, content, branch=branch)


def _xlsx_response(tipo):
    if tipo not in CURRENT_UPLOAD_PATHS:
        raise ValueError('Tipo de arquivo inválido.')
    metadata = _load_upload_metadata().get(tipo)
    if not metadata:
        raise FileNotFoundError('Nenhum arquivo XLSX atual foi enviado para este tipo.')
    repository, branch = _github_repository()
    content = None
    if repository:
        try:
            content = repository.get_contents(metadata['caminho'], ref=branch).decoded_content
        except Exception:
            content = None
    if content is None:
        local_file = DATA_DIR / 'uploads' / Path(metadata['caminho']).name
        if not local_file.exists():
            raise FileNotFoundError('Arquivo XLSX atual não encontrado.')
        content = local_file.read_bytes()
    return send_file(BytesIO(content), as_attachment=True, download_name=metadata['arquivo'], mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


def _store_upload(file, destination):
    if not file or not file.filename:
        raise ValueError('Nenhum arquivo selecionado.')
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise ValueError('Formato inválido. Use um arquivo .xlsx ou .xls.')
    destination.parent.mkdir(exist_ok=True)
    file.save(destination)
    return file.filename


def _github_repository():
    from github import Github
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return None, None
    repository = Github(token).get_repo(os.environ.get('GITHUB_REPOSITORY', 'DMOS15/ptw-matriz'))
    return repository, os.environ.get('GITHUB_BRANCH', 'main')


def criar_backup_atual():
    """Copia os JSON publicados antes de qualquer processamento novo."""
    backup_dir = DATA_DIR / 'backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    repository, branch = _github_repository()
    criados = []

    for filename in JSON_FILES:
        content = None
        if repository:
            try:
                content = repository.get_contents(f'dados/{filename}', ref=branch).decoded_content.decode('utf-8')
            except Exception:
                content = None
        if content is None:
            local_file = ROOT / 'dados' / filename
            if local_file.exists():
                content = local_file.read_text(encoding='utf-8')
        if content is None:
            continue
        target = backup_dir / f'backup_{timestamp}_{filename}'
        target.write_text(content, encoding='utf-8')
        criados.append(target)

    if not criados:
        raise RuntimeError('Não foi possível localizar os JSON atuais para criar o backup.')
    return criados


def process_training(source):
    conversor.ARQUIVO_EXCEL = str(source)
    conversor.DATA_DIR = DATA_DIR
    data = conversor.converter_treinamentos(source)
    return len(data), f'{len(data)} registros processados'


def process_matrix(source, process_responsaveis=True, process_supervisores=True):
    conversor.ARQUIVO_MATRIZ = str(source)
    conversor.DATA_DIR = DATA_DIR
    total = 0
    messages = []
    if process_responsaveis:
        data = conversor.converter_responsaveis(source)
        if not data:
            raise ValueError('Nenhum responsável foi encontrado na aba RESPONSAVEIS DE AREA.')
        _save_json('responsaveis.json', data)
        total += len(data)
        messages.append(f'Responsáveis: {len(data)}')
    if process_supervisores:
        supervisores = conversor.converter_supervisores(source)
        for filename, label in [
            ('supervisores_altura.json', 'Altura'),
            ('supervisores_quente.json', 'Quente'),
            ('supervisores_confinado.json', 'Confinado')
        ]:
            data = supervisores[filename]
            if not data:
                raise ValueError(f'Nenhum supervisor foi encontrado na categoria {label}.')
            _save_json(filename, data)
            total += len(data)
            messages.append(f'{label}: {len(data)}')
    return total, ' | '.join(messages)


@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({'status': 'online', 'versao': '4.0'})


@app.route('/api/admin/login', methods=['POST'])
def login():
    address = request.remote_addr or 'unknown'
    now = datetime.now()
    state = LOGIN_FAILURES.get(address, {'attempts': 0, 'blocked_until': None})
    if state['blocked_until'] and now < state['blocked_until']:
        remaining = int((state['blocked_until'] - now).total_seconds() // 60) + 1
        return _json_error(f'Muitas tentativas. Aguarde {remaining} minuto(s).', 429)
    if state['blocked_until']:
        state = {'attempts': 0, 'blocked_until': None}
    payload = request.get_json(silent=True) or {}
    if str(payload.get('pin', '')) != PIN_ADMIN:
        state['attempts'] += 1
        if state['attempts'] >= MAX_ATTEMPTS:
            state['blocked_until'] = now + timedelta(minutes=BLOCK_MINUTES)
            LOGIN_FAILURES[address] = state
            return _json_error('PIN bloqueado por 5 minutos após 3 tentativas.', 429)
        LOGIN_FAILURES[address] = state
        return _json_error(f'PIN inválido. Tentativa {state["attempts"]} de {MAX_ATTEMPTS}.', 401)
    LOGIN_FAILURES.pop(address, None)
    issued = f'{int(now.timestamp())}.{secrets.token_urlsafe(24)}'
    signature = hmac.new(TOKEN_SECRET.encode(), issued.encode(), hashlib.sha256).hexdigest()
    token = f'{issued}.{signature}'
    return jsonify({'sucesso': True, 'token': token})


@app.route('/api/admin/historico', methods=['GET'])
def history():
    if not _token_ok():
        return _json_error('Acesso administrativo necessário.', 401)
    try:
        if HISTORY_FILE.exists():
            return jsonify(json.loads(HISTORY_FILE.read_text(encoding='utf-8')))
        repository, branch = _github_repository()
        if repository:
            content = repository.get_contents(HISTORY_REPO_PATH, ref=branch)
            return jsonify(json.loads(content.decoded_content.decode('utf-8')))
        return jsonify([])
    except (OSError, json.JSONDecodeError):
        return jsonify([])


@app.route('/api/admin/exportar/<tipo>', methods=['GET'])
def exportar(tipo):
    if not _token_ok():
        return _json_error('Acesso administrativo necessário.', 401)
    try:
        return _xlsx_response(tipo)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as error:
        return _json_error(str(error), 400)
    except Exception:
        return _json_error('Não foi possível gerar o arquivo Excel.', 500)


@app.route('/api/admin/uploads-atuais', methods=['GET'])
def uploads_atuais():
    if not _token_ok():
        return _json_error('Acesso administrativo necessário.', 401)
    return jsonify(_load_upload_metadata())


handler = app
