import json
import os
import secrets
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, jsonify, request
from flask_cors import CORS

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get('PTW_DATA_DIR', Path(tempfile.gettempdir()) / 'ptw_dados'))
PIN_ADMIN = os.environ.get('PTW_ADMIN_PIN', '1234')
MAX_ATTEMPTS = 3
BLOCK_MINUTES = 5
TOKENS = set()
LOGIN_FAILURES = {}
HISTORY_FILE = Path(tempfile.gettempdir()) / 'ptw_historico_atualizacoes.json'

sys.path.insert(0, str(ROOT / 'scripts'))
import conversor

app = Flask(__name__)
CORS(app)


def _json_error(message, status=400):
    return jsonify({'sucesso': False, 'mensagem': message}), status


def _token_ok():
    return request.headers.get('X-Admin-Token', '') in TOKENS


def _history(tipo, filename, success, message, count=0):
    try:
        entries = json.loads(HISTORY_FILE.read_text(encoding='utf-8')) if HISTORY_FILE.exists() else []
    except (OSError, json.JSONDecodeError):
        entries = []
    entries.insert(0, {
        'data': datetime.now().isoformat(timespec='seconds'),
        'tipo': tipo,
        'arquivo': filename,
        'sucesso': success,
        'mensagem': message,
        'registros': count
    })
    try:
        HISTORY_FILE.write_text(json.dumps(entries[:100], ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError:
        pass


def _save_json(name, data):
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def _store_upload(file, destination):
    if not file or not file.filename:
        raise ValueError('Nenhum arquivo selecionado.')
    if not file.filename.lower().endswith(('.xlsx', '.xls')):
        raise ValueError('Formato inválido. Use um arquivo .xlsx ou .xls.')
    destination.parent.mkdir(exist_ok=True)
    file.save(destination)
    return file.filename


def _process_training(source):
    conversor.ARQUIVO_EXCEL = str(source)
    conversor.PASTA_JSON = str(DATA_DIR)
    success, message = conversor.converter_treinamentos()
    if not success:
        raise ValueError(message)
    data = json.loads((DATA_DIR / 'solicitantes.json').read_text(encoding='utf-8'))
    return len(data), message


def _process_matrix(source, process_responsaveis=True, process_supervisores=True):
    conversor.ARQUIVO_MATRIZ = str(source)
    conversor.PASTA_JSON = str(DATA_DIR)
    total = 0
    messages = []
    if process_responsaveis:
        data = conversor.converter_responsaveis_excel()
        if not data:
            raise ValueError('Nenhum responsável foi encontrado na aba RESPONSAVEIS DE AREA.')
        _save_json('responsaveis.json', data)
        total += len(data)
        messages.append(f'Responsáveis: {len(data)}')
    if process_supervisores:
        for sheet, filename, label in [
            ('SUPERVISOR TRABALHO EM ALTURA', 'supervisores_altura.json', 'Altura'),
            ('SUPERVISOR TRABALHO A QUENTE', 'supervisores_quente.json', 'Quente'),
            ('SUPERVISOR TRABALHO CONFINADO', 'supervisores_confinado.json', 'Confinado')
        ]:
            data = conversor.converter_supervisores_excel(sheet)
            if not data:
                raise ValueError(f'Nenhum supervisor foi encontrado na aba {sheet}.')
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
    blocked_until = state['blocked_until']
    if blocked_until and now < blocked_until:
        remaining = int((blocked_until - now).total_seconds() // 60) + 1
        return _json_error(f'Muitas tentativas. Aguarde {remaining} minuto(s).', 429)
    if blocked_until:
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
    token = secrets.token_urlsafe(32)
    TOKENS.add(token)
    return jsonify({'sucesso': True, 'token': token})


@app.route('/api/admin/historico', methods=['GET'])
def history():
    if not _token_ok():
        return _json_error('Acesso administrativo necessário.', 401)
    try:
        return jsonify(json.loads(HISTORY_FILE.read_text(encoding='utf-8')) if HISTORY_FILE.exists() else [])
    except (OSError, json.JSONDecodeError):
        return jsonify([])


def upload(kind):
    if not _token_ok():
        return _json_error('Acesso administrativo necessário.', 401)
    file = request.files.get('arquivo')
    try:
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / (file.filename if file else 'upload.xlsx')
            filename = _store_upload(file, source)
            if kind == 'treinamentos':
                count, message = _process_training(source)
            elif kind == 'responsaveis':
                count, message = _process_matrix(source, True, False)
            elif kind == 'supervisores':
                count, message = _process_matrix(source, False, True)
            else:
                count, message = _process_matrix(source, True, True)
        _history(kind, filename, True, message, count)
        return jsonify({'sucesso': True, 'mensagem': f'Concluído! {message}', 'registros': count})
    except Exception as error:
        filename = file.filename if file else ''
        _history(kind, filename, False, str(error))
        return _json_error(str(error), 500)


@app.route('/api/upload_treinamentos', methods=['POST'])
def upload_treinamentos():
    return upload('treinamentos')


@app.route('/api/upload_responsaveis', methods=['POST'])
def upload_responsaveis():
    return upload('responsaveis')


@app.route('/api/upload_supervisores', methods=['POST'])
def upload_supervisores():
    return upload('supervisores')


@app.route('/api/upload_matriz', methods=['POST'])
def upload_matriz():
    return upload('matriz')


handler = app
