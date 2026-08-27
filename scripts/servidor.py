import os
import json
import secrets
from datetime import datetime
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path

PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DADOS = os.path.join(PASTA_RAIZ, 'dados')
ARQUIVO_TREINAMENTOS = os.path.join(PASTA_RAIZ, 'Treinamentos obrigatórios (SHE-QUALID).xlsx')
ARQUIVO_MATRIZ = os.path.join(PASTA_RAIZ, 'SHE 10 - B Work Permit Systems-Responsibility.xlsx')
ARQUIVO_HISTORICO = os.path.join(PASTA_DADOS, 'historico_atualizacoes.json')
PIN_ADMIN = os.environ.get('PTW_ADMIN_PIN', 'JDEPIU')
TOKENS_ADMIN = set()

app = Flask(__name__, static_folder=None)
CORS(app)

os.makedirs(PASTA_DADOS, exist_ok=True)

print("="*50)
print("🚀 SERVIDOR DE UPLOAD - MATRIZ PTW")
print("="*50)

# ============================================================
# IMPORTA AS FUNÇÕES DO CONVERSOR
# ============================================================
import conversor


@app.route('/')
def pagina_inicial():
    return send_from_directory(PASTA_RAIZ, 'index.html')


@app.route('/<path:nome_arquivo>')
def arquivos_publicos(nome_arquivo):
    return send_from_directory(PASTA_RAIZ, nome_arquivo)

# ============================================================
# FUNÇÃO AUXILIAR CORS
# ============================================================
def _cors_response():
    response = jsonify({'sucesso': True})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, X-Admin-Token')
    return response


def _admin_autorizado():
    token = request.headers.get('X-Admin-Token', '')
    return bool(token) and token in TOKENS_ADMIN


def _resposta_nao_autorizada():
    return jsonify({'sucesso': False, 'mensagem': 'Acesso administrativo necessário.'}), 401


def _registrar_historico(tipo, nome_arquivo, sucesso, mensagem):
    historico = []
    if os.path.exists(ARQUIVO_HISTORICO):
        try:
            with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as arquivo:
                historico = json.load(arquivo)
        except (OSError, json.JSONDecodeError):
            historico = []

    historico.insert(0, {
        'data': datetime.now().isoformat(timespec='seconds'),
        'tipo': tipo,
        'arquivo': nome_arquivo,
        'sucesso': sucesso,
        'mensagem': mensagem
    })
    with open(ARQUIVO_HISTORICO, 'w', encoding='utf-8') as arquivo:
        json.dump(historico[:100], arquivo, ensure_ascii=False, indent=2)


@app.route('/api/admin/login', methods=['POST', 'OPTIONS'])
def admin_login():
    if request.method == 'OPTIONS':
        return _cors_response()

    dados = request.get_json(silent=True) or {}
    if dados.get('pin') != PIN_ADMIN:
        return jsonify({'sucesso': False, 'mensagem': 'PIN inválido.'}), 401

    token = secrets.token_urlsafe(32)
    TOKENS_ADMIN.add(token)
    return jsonify({'sucesso': True, 'token': token})


@app.route('/api/admin/historico', methods=['GET', 'OPTIONS'])
def admin_historico():
    if request.method == 'OPTIONS':
        return _cors_response()
    if not _admin_autorizado():
        return _resposta_nao_autorizada()

    if not os.path.exists(ARQUIVO_HISTORICO):
        return jsonify([])
    try:
        with open(ARQUIVO_HISTORICO, 'r', encoding='utf-8') as arquivo:
            return jsonify(json.load(arquivo))
    except (OSError, json.JSONDecodeError):
        return jsonify([])

# ============================================================
# ROTA: UPLOAD TREINAMENTOS (SOLICITANTES)
# ============================================================
@app.route('/api/upload_treinamentos', methods=['POST', 'OPTIONS'])
def upload_treinamentos():
    if request.method == 'OPTIONS':
        return _cors_response()
    if not _admin_autorizado():
        return _resposta_nao_autorizada()
    
    try:
        print("📤 Upload de TREINAMENTOS...")
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo selecionado'}), 400
        
        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'sucesso': False, 'mensagem': 'Formato inválido. Use .xlsx ou .xls'}), 400
        
        arquivo.save(ARQUIVO_TREINAMENTOS)
        print(f"✅ Treinamentos salvos em: {ARQUIVO_TREINAMENTOS}")
        
        sucesso, mensagem = conversor.converter_treinamentos()
        if not sucesso:
            _registrar_historico('treinamentos', arquivo.filename, False, mensagem)
            return jsonify({'sucesso': False, 'mensagem': mensagem}), 500
        
        _registrar_historico('treinamentos', arquivo.filename, True, mensagem)
        return jsonify({'sucesso': True, 'mensagem': f'✅ Treinamentos atualizados! {mensagem}'})
        
    except Exception as e:
        _registrar_historico('treinamentos', request.files.get('arquivo', {}).filename if 'arquivo' in request.files else '', False, str(e))
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: UPLOAD MATRIZ (RESPONSÁVEIS + SUPERVISORES)
# ============================================================
@app.route('/api/upload_matriz', methods=['POST', 'OPTIONS'])
def upload_matriz():
    if request.method == 'OPTIONS':
        return _cors_response()
    if not _admin_autorizado():
        return _resposta_nao_autorizada()
    
    try:
        print("📤 Upload da MATRIZ (Responsáveis + Supervisores)...")
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo selecionado'}), 400
        
        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'sucesso': False, 'mensagem': 'Formato inválido. Use .xlsx ou .xls'}), 400
        
        arquivo.save(ARQUIVO_MATRIZ)
        print(f"✅ Matriz salva em: {ARQUIVO_MATRIZ}")
        
        # ===== 1. RESPONSÁVEIS =====
        dados_resp = conversor.converter_responsaveis_excel()
        if not dados_resp:
            print("⚠️ Usando backup de responsáveis...")
            dados_resp = conversor.converter_responsaveis()
        
        with open(os.path.join(PASTA_DADOS, 'responsaveis.json'), 'w', encoding='utf-8') as f:
            json.dump(dados_resp, f, ensure_ascii=False, indent=2)
        
        # ===== 2. SUPERVISORES =====
        altura = conversor.converter_supervisores_excel("SUPERVISOR TRABALHO EM ALTURA")
        quente = conversor.converter_supervisores_excel("SUPERVISOR TRABALHO A QUENTE")
        confinado = conversor.converter_supervisores_excel("SUPERVISOR TRABALHO CONFINADO")
        
        if not altura:
            print("⚠️ Usando backup de altura...")
            altura = conversor.converter_supervisores_altura()
        if not quente:
            print("⚠️ Usando backup de quente...")
            quente = conversor.converter_supervisores_quente()
        if not confinado:
            print("⚠️ Usando backup de confinado...")
            confinado = conversor.converter_supervisores_confinado()
        
        with open(os.path.join(PASTA_DADOS, 'supervisores_altura.json'), 'w', encoding='utf-8') as f:
            json.dump(altura, f, ensure_ascii=False, indent=2)
        
        with open(os.path.join(PASTA_DADOS, 'supervisores_quente.json'), 'w', encoding='utf-8') as f:
            json.dump(quente, f, ensure_ascii=False, indent=2)
        
        with open(os.path.join(PASTA_DADOS, 'supervisores_confinado.json'), 'w', encoding='utf-8') as f:
            json.dump(confinado, f, ensure_ascii=False, indent=2)
        
        mensagem = f'Responsáveis: {len(dados_resp)} | Altura: {len(altura)} | Quente: {len(quente)} | Confinado: {len(confinado)}'
        _registrar_historico('matriz', arquivo.filename, True, mensagem)
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ Matriz atualizada!\n{mensagem}'
        })
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        _registrar_historico('matriz', request.files.get('arquivo', {}).filename if 'arquivo' in request.files else '', False, str(e))
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: UPLOAD RESPONSÁVEIS (INDIVIDUAL)
# ============================================================
@app.route('/api/upload_responsaveis', methods=['POST', 'OPTIONS'])
def upload_responsaveis():
    if request.method == 'OPTIONS':
        return _cors_response()
    if not _admin_autorizado():
        return _resposta_nao_autorizada()
    
    try:
        print("📤 Upload de RESPONSÁVEIS POR ÁREA...")
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo selecionado'}), 400
        
        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'sucesso': False, 'mensagem': 'Formato inválido. Use .xlsx ou .xls'}), 400
        
        arquivo.save(ARQUIVO_MATRIZ)
        print(f"✅ Matriz salva em: {ARQUIVO_MATRIZ}")
        
        dados = conversor.converter_responsaveis_excel()
        if not dados:
            print("⚠️ Usando backup de responsáveis...")
            dados = conversor.converter_responsaveis()
        
        with open(os.path.join(PASTA_DADOS, 'responsaveis.json'), 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        
        mensagem = f'Responsáveis atualizados! ({len(dados)} registros)'
        _registrar_historico('responsaveis', arquivo.filename, True, mensagem)
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ {mensagem}'
        })
        
    except Exception as e:
        _registrar_historico('responsaveis', request.files.get('arquivo', {}).filename if 'arquivo' in request.files else '', False, str(e))
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: UPLOAD SUPERVISORES (INDIVIDUAL)
# ============================================================
@app.route('/api/upload_supervisores', methods=['POST', 'OPTIONS'])
def upload_supervisores():
    if request.method == 'OPTIONS':
        return _cors_response()
    if not _admin_autorizado():
        return _resposta_nao_autorizada()
    
    try:
        print("📤 Upload de SUPERVISORES...")
        
        if 'arquivo' not in request.files:
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo enviado'}), 400
        
        arquivo = request.files['arquivo']
        if arquivo.filename == '':
            return jsonify({'sucesso': False, 'mensagem': 'Nenhum arquivo selecionado'}), 400
        
        if not arquivo.filename.endswith(('.xlsx', '.xls')):
            return jsonify({'sucesso': False, 'mensagem': 'Formato inválido. Use .xlsx ou .xls'}), 400
        
        arquivo.save(ARQUIVO_MATRIZ)
        print(f"✅ Matriz salva em: {ARQUIVO_MATRIZ}")
        
        altura = conversor.converter_supervisores_excel("SUPERVISOR TRABALHO EM ALTURA")
        quente = conversor.converter_supervisores_excel("SUPERVISOR TRABALHO A QUENTE")
        confinado = conversor.converter_supervisores_excel("SUPERVISOR TRABALHO CONFINADO")
        
        if not altura:
            print("⚠️ Usando backup de altura...")
            altura = conversor.converter_supervisores_altura()
        if not quente:
            print("⚠️ Usando backup de quente...")
            quente = conversor.converter_supervisores_quente()
        if not confinado:
            print("⚠️ Usando backup de confinado...")
            confinado = conversor.converter_supervisores_confinado()
        
        with open(os.path.join(PASTA_DADOS, 'supervisores_altura.json'), 'w', encoding='utf-8') as f:
            json.dump(altura, f, ensure_ascii=False, indent=2)
        
        with open(os.path.join(PASTA_DADOS, 'supervisores_quente.json'), 'w', encoding='utf-8') as f:
            json.dump(quente, f, ensure_ascii=False, indent=2)
        
        with open(os.path.join(PASTA_DADOS, 'supervisores_confinado.json'), 'w', encoding='utf-8') as f:
            json.dump(confinado, f, ensure_ascii=False, indent=2)
        
        mensagem = f'Supervisores atualizados!\nAltura: {len(altura)} | Quente: {len(quente)} | Confinado: {len(confinado)}'
        _registrar_historico('supervisores', arquivo.filename, True, mensagem)
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ {mensagem}'
        })
        
    except Exception as e:
        _registrar_historico('supervisores', request.files.get('arquivo', {}).filename if 'arquivo' in request.files else '', False, str(e))
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: STATUS
# ============================================================
@app.route('/api/status', methods=['GET'])
def status():
    return jsonify({
        'status': 'online',
        'versao': '4.0',
        'treinamentos': os.path.exists(ARQUIVO_TREINAMENTOS),
        'matriz': os.path.exists(ARQUIVO_MATRIZ)
    })

# ============================================================
# ROTA: TESTE
# ============================================================
@app.route('/api/teste', methods=['GET'])
def teste():
    return jsonify({
        'mensagem': 'Servidor rodando!',
        'rotas': [
            'POST /api/upload_treinamentos',
            'POST /api/upload_matriz',
            'POST /api/upload_responsaveis',
            'POST /api/upload_supervisores',
            'GET /api/status',
            'GET /api/teste'
        ]
    })

# ============================================================
# INICIAR O SERVIDOR
# ============================================================
if __name__ == '__main__':
    print("🌐 Servidor rodando em: http://localhost:5000")
    print("📡 Rotas disponíveis:")
    print("   POST /api/upload_treinamentos - Atualiza Solicitantes")
    print("   POST /api/upload_matriz - Atualiza Responsáveis + Supervisores")
    print("   POST /api/upload_responsaveis - Atualiza apenas Responsáveis")
    print("   POST /api/upload_supervisores - Atualiza apenas Supervisores")
    print("   GET  /api/status - Verifica status")
    print("   GET  /api/teste - Testa conexão")
    print("="*50)
    app.run(host='0.0.0.0', port=5000, debug=True)