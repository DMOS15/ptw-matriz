import os
import json
import pandas as pd
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path

app = Flask(__name__)
CORS(app)

PASTA_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DADOS = os.path.join(PASTA_RAIZ, 'dados')
ARQUIVO_TREINAMENTOS = os.path.join(PASTA_RAIZ, 'Treinamentos obrigatórios (SHE-QUALID).xlsx')
ARQUIVO_MATRIZ = os.path.join(PASTA_RAIZ, 'SHE 10 - B Work Permit Systems-Responsibility.xlsx')

os.makedirs(PASTA_DADOS, exist_ok=True)

print("="*50)
print("🚀 SERVIDOR DE UPLOAD - MATRIZ PTW")
print("="*50)

# ============================================================
# IMPORTA AS FUNÇÕES DO CONVERSOR
# ============================================================
import conversor

# ============================================================
# FUNÇÃO AUXILIAR CORS
# ============================================================
def _cors_response():
    response = jsonify({'sucesso': True})
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

# ============================================================
# ROTA: UPLOAD TREINAMENTOS (SOLICITANTES)
# ============================================================
@app.route('/api/upload_treinamentos', methods=['POST', 'OPTIONS'])
def upload_treinamentos():
    if request.method == 'OPTIONS':
        return _cors_response()
    
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
            return jsonify({'sucesso': False, 'mensagem': mensagem}), 500
        
        return jsonify({'sucesso': True, 'mensagem': f'✅ Treinamentos atualizados! {mensagem}'})
        
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: UPLOAD MATRIZ (RESPONSÁVEIS + SUPERVISORES)
# ============================================================
@app.route('/api/upload_matriz', methods=['POST', 'OPTIONS'])
def upload_matriz():
    if request.method == 'OPTIONS':
        return _cors_response()
    
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
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ Matriz atualizada!\nResponsáveis: {len(dados_resp)}\nAltura: {len(altura)} | Quente: {len(quente)} | Confinado: {len(confinado)}'
        })
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: UPLOAD RESPONSÁVEIS (INDIVIDUAL)
# ============================================================
@app.route('/api/upload_responsaveis', methods=['POST', 'OPTIONS'])
def upload_responsaveis():
    if request.method == 'OPTIONS':
        return _cors_response()
    
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
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ Responsáveis atualizados! ({len(dados)} registros)'
        })
        
    except Exception as e:
        return jsonify({'sucesso': False, 'mensagem': str(e)}), 500

# ============================================================
# ROTA: UPLOAD SUPERVISORES (INDIVIDUAL)
# ============================================================
@app.route('/api/upload_supervisores', methods=['POST', 'OPTIONS'])
def upload_supervisores():
    if request.method == 'OPTIONS':
        return _cors_response()
    
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
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'✅ Supervisores atualizados!\nAltura: {len(altura)} | Quente: {len(quente)} | Confinado: {len(confinado)}'
        })
        
    except Exception as e:
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