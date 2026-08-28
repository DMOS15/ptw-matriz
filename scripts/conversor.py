import pandas as pd
import json
import os
from pathlib import Path

# ============================================================
# CONFIGURAÇÕES
# ============================================================
pasta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_JSON = os.path.join(pasta_raiz, "dados")
ARQUIVO_EXCEL = os.path.join(pasta_raiz, "Treinamentos obrigatórios (SHE-QUALID).xlsx")
ARQUIVO_MATRIZ = os.path.join(pasta_raiz, "SHE 10 - B Work Permit Systems-Responsibility.xlsx")

# ============================================================
# ÁREAS DOS SOLICITANTES
# ============================================================
AREAS_RESPONSAVEIS = [
    "Telhados/Caixas d'água",
    "Logística (interno e pátio externo) + Sala de Baterias",
    "Cavaco, café verde, fornalha, torradores e moagem",
    "Empacatamento - Fabrimas, Raumak's, Robôs e PKD)",
    "Almoxarifado comum e embalagens + Almoxarifado Peças - Manutenção",
    "Sala de Inflamáveis",
    "Tanque de GLP",
    "Facilites (Áreas comuns, externas, ADM's, Convivência, Refeitório, Ambulatório, Portaria, Estacionamento",
    "Central de resíduos, Classe 1 e caixa SAO",
    "Galpão 2",
    "Galpão 3",
    "Subestação elétrica/ QGBT geradores/ compressores",
    "ADM Qualidade, CQCV e Shelf-life",
    "Casa de bombas, caixa dágua de incêndio, painel de emergência, alarmes e hidrantes",
    "Sala e oficiana da Manutenção",
    "Livre Retirada - Manutenção (Galpão 2)",
]

AREAS_SUPERVISORES = [
    "Telhados/Caixas d'água", "Logística (interno e externo)", "Café Verde",
    "Manufatura (fornalha ao empacotamento)", "Almoxarifado", "Sala de Inflamáveis",
    "Tanques de GLP", "Facilites", "DTRS", "Galpão 2", "Galpão 3",
    "subestação elétrica/ geradores/ compressores", "CQ",
    "Sistema de Proteção e Combate a Incêndio", "Áreas Comuns", "Sala da Manutenção",
    "Livre Retirada"
]

AREAS_SOLICITANTES = AREAS_SUPERVISORES

# ============================================================
# FUNÇÃO PARA CONVERTER VALORES
# ============================================================
def safe_str(valor):
    if valor is None:
        return ""
    if pd.isna(valor):
        return ""
    if isinstance(valor, (pd.Timestamp, pd._libs.tslibs.timestamps.Timestamp)):
        return valor.strftime('%d/%m/%Y')
    if isinstance(valor, (list, tuple, pd.Series)):
        return ""
    return str(valor).strip()

# ============================================================
# 1. CONVERTER TREINAMENTOS (SOLICITANTES)
# ============================================================
def converter_treinamentos():
    print("🔄 Convertendo treinamentos da aba PT...")
    
    if not os.path.exists(ARQUIVO_EXCEL):
        print(f"❌ Arquivo Excel não encontrado: {ARQUIVO_EXCEL}")
        return False, "Arquivo não encontrado"
    
    try:
        df_ptw = pd.read_excel(ARQUIVO_EXCEL, sheet_name="PT")
        df_ptw = df_ptw.fillna("")
        
        df_cadastro = pd.read_excel(ARQUIVO_EXCEL, sheet_name="CADASTRO")
        df_cadastro = df_cadastro.fillna("")
        
        status_colaboradores = {}
        for idx, row in df_cadastro.iterrows():
            nome = str(row.get('NOME', '')).strip().upper()
            status = str(row.get('STATUS', '')).strip().upper()
            if nome and nome != '':
                status_colaboradores[nome] = status
        
        registros = []
        for idx, row in df_ptw.iterrows():
            nome = str(row.get('NOME', '')).strip()
            if not nome:
                continue
                
            cargo = str(row.get('CARGO', '')).strip().upper()
            treinamento = str(row.get('TREINAMENTO', '')).strip().upper()
            status_treinamento = str(row.get('STATUS', '')).strip().upper()
            situacao = str(row.get('SITUAÇÃO', '')).strip().upper()
            
            if treinamento not in ["PT", "PTW"]:
                continue
            
            if status_treinamento not in ["NO PRAZO", "APROVADO", "VENCIDO"]:
                continue
            
            nome_upper = nome.upper()
            status_colab = status_colaboradores.get(nome_upper, situacao)
            
            if status_colab != "ATIVO":
                continue
            
            cargo_upper = cargo.upper()
            if "HIRENOW" in cargo_upper or "ESTAGIARIO" in cargo_upper or "APRENDIZ" in cargo_upper or "ESTAGIÁRIO" in cargo_upper:
                continue
            
            area = ""
            for idx2, row_cad in df_cadastro.iterrows():
                nome_cad = str(row_cad.get('NOME', '')).strip().upper()
                if nome_cad == nome_upper:
                    area = str(row_cad.get('ÁREA', '')).strip()
                    break
            
            vence_em = row.get('VENCE EM', '')
            if isinstance(vence_em, pd.Timestamp):
                vence_em = vence_em.strftime('%d/%m/%Y')
            else:
                vence_em = str(vence_em).strip()
            
            treinado_em = row.get('TREINADO EM', '')
            if isinstance(treinado_em, pd.Timestamp):
                treinado_em = treinado_em.strftime('%d/%m/%Y')
            else:
                treinado_em = str(treinado_em).strip()
            
            registros.append({
                "nome": nome,
                "cargo": cargo,
                "area": area,
                "status": status_treinamento,
                "vence_em": vence_em,
                "treinado_em": treinado_em,
                "instrutor": str(row.get('INSTRUTOR', '')).strip(),
                "condicao": str(row.get('CONDIÇÃO', '')).strip(),
                "situacao": status_colab,
                "areas": AREAS_SOLICITANTES
            })
        
        if registros:
            registros_unicos = {}
            for reg in registros:
                nome = reg['nome']
                if nome in registros_unicos:
                    try:
                        data_atual = pd.to_datetime(reg['treinado_em'], dayfirst=True, errors='coerce')
                        data_existente = pd.to_datetime(registros_unicos[nome]['treinado_em'], dayfirst=True, errors='coerce')
                        if data_atual > data_existente:
                            registros_unicos[nome] = reg
                    except:
                        pass
                else:
                    registros_unicos[nome] = reg
            registros = list(registros_unicos.values())
        
        os.makedirs(PASTA_JSON, exist_ok=True)
        caminho_json = os.path.join(PASTA_JSON, 'solicitantes.json')
        with open(caminho_json, 'w', encoding='utf-8') as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
        
        print(f"✅ solicitantes.json gerado com {len(registros)} registros")
        return True, f"✅ {len(registros)} registros processados"
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False, str(e)

# ============================================================
# 2. CONVERTER RESPONSÁVEIS POR ÁREA (DO EXCEL MATRIZ)
# ============================================================
def converter_responsaveis_excel():
    print("🔄 Lendo responsáveis por área do Excel Matriz...")
    
    if not os.path.exists(ARQUIVO_MATRIZ):
        print(f"⚠️ Arquivo Matriz não encontrado: {ARQUIVO_MATRIZ}")
        return []
    
    try:
        df = pd.read_excel(ARQUIVO_MATRIZ, sheet_name="RESPONSAVEIS DE AREA", dtype=str)
        df = df.fillna("")
        
        print(f"📋 Colunas encontradas: {list(df.columns)}")
        
        # Pega os nomes das colunas (áreas) - ignora a primeira coluna que é o nome
        colunas_areas = []
        for col in df.columns:
            if col != 'Nome' and col != 'Responsáveis pela área':
                colunas_areas.append(col)
        
        print(f"📋 Áreas encontradas: {len(colunas_areas)}")
        
        dados = []
        for idx, row in df.iterrows():
            # Tenta encontrar a coluna de nome
            nome = ''
            if 'Nome' in df.columns:
                nome = str(row.get('Nome', '')).strip()
            elif 'Responsáveis pela área' in df.columns:
                nome = str(row.get('Responsáveis pela área', '')).strip()
            
            if not nome:
                continue
            
            areas = []
            for col in AREAS_RESPONSAVEIS:
                if col not in df.columns:
                    continue
                valor = str(row.get(col, '')).strip().upper()
                if valor == 'SIM' or valor == 'X' or valor == '1':
                    areas.append(col)
            
            if areas:
                dados.append({
                    "nome": nome,
                    "cargo": "Responsável por Área",
                    "areas": areas
                })
        
        print(f"✅ Responsáveis carregados: {len(dados)} registros")
        return dados
        
    except Exception as e:
        print(f"❌ Erro ao ler responsáveis: {e}")
        import traceback
        traceback.print_exc()
        return []

# ============================================================
# 3. CONVERTER SUPERVISORES (DO EXCEL MATRIZ)
# ============================================================
def converter_supervisores_excel(aba_nome):
    print(f"🔄 Lendo supervisores da aba '{aba_nome}'...")
    
    if not os.path.exists(ARQUIVO_MATRIZ):
        print(f"⚠️ Arquivo Matriz não encontrado: {ARQUIVO_MATRIZ}")
        return []
    
    try:
        df = pd.read_excel(ARQUIVO_MATRIZ, sheet_name=aba_nome, dtype=str)
        df = df.fillna("")
        
        print(f"   Colunas: {list(df.columns)}")
        
        # Pega os nomes das colunas (áreas) - ignora a primeira coluna que é o nome
        colunas_areas = [col for col in AREAS_SUPERVISORES if col in df.columns]
        
        dados = []
        for idx, row in df.iterrows():
            # Tenta encontrar a coluna de nome
            nome = ''
            if 'Nome' in df.columns:
                nome = str(row.get('Nome', '')).strip()
            else:
                # Se não tiver coluna 'Nome', tenta a primeira coluna
                nome = str(row.iloc[0]).strip()
            
            if not nome:
                continue
            
            areas = []
            for col in colunas_areas:
                valor = str(row.get(col, '')).strip().upper()
                if valor == 'SIM' or valor == 'X' or valor == '1':
                    areas.append(col)
            
            if areas:
                dados.append({
                    "nome": nome,
                    "cargo": "Supervisor",
                    "areas": areas
                })
        
        print(f"✅ Supervisores '{aba_nome}': {len(dados)} registros")
        return dados
        
    except Exception as e:
        print(f"❌ Erro ao ler supervisores: {e}")
        import traceback
        traceback.print_exc()
        return []

# ============================================================
# 4. CONVERTER RESPONSÁVEIS (BACKUP - DADOS FIXOS)
# ============================================================
def converter_responsaveis():
    print("🔄 Gerando responsáveis por área (backup)...")
    
    dados = [
        {"nome": "Ana Pereira", "cargo": "Responsável por Área", "areas": ["Sala de Inflamáveis", "Tanque de GLP"]},
        {"nome": "Andre Costa", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis", "Tanque de GLP"]},
        {"nome": "Eliezer Silva", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis", "Tanque de GLP"]},
        {"nome": "Henrique Cardoso", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis", "Tanque de GLP"]},
        {"nome": "Igor Sousa", "cargo": "Responsável por Área", "areas": ["ADM Qualidade"]},
        {"nome": "Pedro Coelho", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis"]},
        {"nome": "Ana Martins", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis"]},
        {"nome": "Aline Fernandes", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis", "Tanque de GLP", "Facilites"]},
        {"nome": "Caio Ferreira", "cargo": "Responsável por Área", "areas": ["Casa de bombas"]},
        {"nome": "Camila Basílio", "cargo": "Responsável por Área", "areas": ["Facilites", "Galpão 2", "Galpão 3"]},
        {"nome": "Cristina Aparecida Silva", "cargo": "Responsável por Área", "areas": ["Facilites", "Galpão 2", "Galpão 3"]},
        {"nome": "Fábio Oliveira", "cargo": "Responsável por Área", "areas": ["Logística"]},
        {"nome": "Gian Silva", "cargo": "Responsável por Área", "areas": ["Logística"]},
        {"nome": "Giovanna Biffaratte", "cargo": "Responsável por Área", "areas": ["Cavaco", "Empacotamento"]},
        {"nome": "Guilherme Oliveira", "cargo": "Responsável por Área", "areas": ["Telhados", "Facilites", "Galpão 2", "Galpão 3", "Manutenção"]},
        {"nome": "Izabella Pugliesi", "cargo": "Responsável por Área", "areas": ["Cavaco", "Empacotamento"]},
        {"nome": "Leonardo Junior", "cargo": "Responsável por Área", "areas": ["Cavaco", "Empacotamento"]},
        {"nome": "Michelle Faria", "cargo": "Responsável por Área", "areas": ["Cavaco", "Empacotamento"]},
        {"nome": "Moises Costa", "cargo": "Responsável por Área", "areas": ["Cavaco", "Empacotamento"]},
        {"nome": "Rafael Souza", "cargo": "Responsável por Área", "areas": ["Logística"]},
        {"nome": "Relton Moraes", "cargo": "Responsável por Área", "areas": ["Cavaco", "Empacotamento"]},
        {"nome": "Rubens Teixeira", "cargo": "Responsável por Área", "areas": ["Galpão 2", "Galpão 3"]},
        {"nome": "Ruth Ribeiro", "cargo": "Responsável por Área", "areas": ["Galpão 2", "Galpão 3"]},
        {"nome": "Samuel Camargos", "cargo": "Responsável por Área", "areas": ["Telhados", "Facilites", "Galpão 2", "Galpão 3", "Manutenção"]},
        {"nome": "Sarah Teixeira", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis", "Tanque de GLP", "Facilites", "Galpão 2", "Galpão 3"]},
        {"nome": "Tais Costa", "cargo": "Responsável por Área", "areas": ["Casa de bombas"]},
        {"nome": "Talita Campos", "cargo": "Responsável por Área", "areas": ["Almoxarifado", "Sala de Inflamáveis", "Tanque de GLP"]},
        {"nome": "Tiago Carvalho", "cargo": "Responsável por Área", "areas": ["Telhados", "Facilites", "Galpão 2", "Galpão 3", "Manutenção"]},
        {"nome": "Angela Santos", "cargo": "Responsável por Área", "areas": ["Empacotamento"]},
        {"nome": "Rafael Santos", "cargo": "Responsável por Área", "areas": ["Logística"]},
        {"nome": "Alice Ramos Morais", "cargo": "Responsável por Área", "areas": ["Manutenção"]},
        {"nome": "Thaissa Leonel Oliveira", "cargo": "Responsável por Área", "areas": ["Manutenção"]},
        {"nome": "Ana Luiza de Paula", "cargo": "Responsável por Área", "areas": ["Manutenção"]},
        {"nome": "Deyvidson Carlos Peres dos Santos", "cargo": "Responsável por Área", "areas": ["Manutenção"]}
    ]
    
    os.makedirs(PASTA_JSON, exist_ok=True)
    caminho_json = os.path.join(PASTA_JSON, 'responsaveis.json')
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    
    print(f"✅ responsaveis.json gerado com {len(dados)} registros (backup)")
    return dados

# ============================================================
# 5. CONVERTER SUPERVISORES (BACKUP - DADOS FIXOS)
# ============================================================
def _supervisores(nomes, areas):
    return [
        {"nome": nome, "cargo": "Supervisor", "areas": list(areas)}
        for nome in nomes
    ]

def converter_supervisores_altura():
    print("🔄 Gerando supervisores de altura (backup)...")
    nomes = [
        "Alex Teixeira", "Alexandre Oliveira", "Alexandre Costa", "Angela Santos",
        "Angelo Teixeira", "Arthur Silva", "Caluan Guimaraes", "Carlos Souza",
        "Daniel Madureira", "Diogo Silva", "Ednaldo Silva", "Eduardo Candido",
        "Edvaldo Silva", "Edvan Santos", "Evanio Santos", "Fabio Coelho",
        "Fabricio Brant", "Felipe Simoes", "Fernando Santos", "Gean Silva",
        "Henrique Cardoso", "Igor Sousa", "Jader Costa", "Joao Vitor Oliveira",
        "Jose Ribamar Junior", "Jose Roberto Medeiros", "Joviano Machado",
        "Julho Cesar Silva", "Lucas Obrien", "Lucas Carvalho",
    ]
    dados = _supervisores(nomes, AREAS_SOLICITANTES)
    os.makedirs(PASTA_JSON, exist_ok=True)
    caminho_json = os.path.join(PASTA_JSON, 'supervisores_altura.json')
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"✅ supervisores_altura.json gerado com {len(dados)} registros (backup)")
    return dados

def converter_supervisores_quente():
    print("🔄 Gerando supervisores de quente (backup)...")
    AREAS_QUENTE = [
        "Trabalhos Cargas", "Logística", "Carib Verde", "Natalina empaçamento",
        "Almancaritos", "Sala do GIP", "Facilites", "TRS", "Gaiapo 2", "Gaiapo 3",
        "Subestação elétrica solaris", "CA", "CRS", "Áreas Comuns", "Sala da Mantiqueira", "Livro Retirada"
    ]
    nomes = [
        "Alex Teixeira", "Alex Bernardes", "Alexandre Oliveira", "Alexandre Costa",
        "Amanda Melo", "André Costa", "Angela Santos", "Angelo Teixeira",
        "Arthur Silva", "Bruno Silva", "Caique Ventura", "Camila Alves",
        "Carlos Souza", "Dayane Martins", "Diego Oliveira", "Edvan Santos",
        "Evanio Santos", "Fernando Santos", "Gean Silva", "Guilherme Silva",
        "Guilherme Oliveira", "Henrique Lima", "Igor Sousa", "Ivomar Costa",
        "Izabela Pugliesi", "Joelma Inone", "Jordy Coutinho", "Jose Ribamar Junior",
        "Jucilene Azevedo", "Karina Amaral", "Lucas Obrien", "Lucas Vaz",
        "Lucas Carvalho", "Luciane Santos", "Luiz Nascimento", "Luzia Cordeiro",
        "Luzia Rodrigues", "Marcelo Oliveira", "Marcelo Araújo", "Marcos Terra",
        "Mauricio Ferreira", "Maximiliano Oliveira", "Moises Costa", "Natalia Mendonça",
        "Nilton Costa", "Rafael Salgado", "Rafael Santos", "Raniele Santos",
        "Rogger Morais", "Romero Chaves", "Rubens Teixeira", "Samuel Camargos",
        "Sara Lobato", "Sarah Teixeira", "Sebastião Filho", "Talita Costa",
        "Tiago Carvalho", "Valdeci Simoes", "Vicente Silva", "Vilbert Santos",
        "Vinícios Ramos", "Vitor Xavier", "Wallace Pereira", "Wesley Jesus",
        "Weverton Medeiros"
    ]
    dados = _supervisores(nomes, AREAS_QUENTE)
    os.makedirs(PASTA_JSON, exist_ok=True)
    caminho_json = os.path.join(PASTA_JSON, 'supervisores_quente.json')
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"✅ supervisores_quente.json gerado com {len(dados)} registros (backup)")
    return dados

def converter_supervisores_confinado():
    print("🔄 Gerando supervisores de confinado (backup)...")
    nomes = [
        "Alexandre Oliveira", "Alexandre Costa", "Angelo Teixeira", "Daniel Madureira",
        "Ednaldo Silva", "Edvan Henrique", "Fabio Coelho", "Fernando Santos",
        "Guilherme Oliveira", "Igor Sousa", "Joviano Machado", "Lucas Obrien",
        "Lucas Carvalho", "Luiz Henrique Silva", "Natalia Mendonça", "Patrick Pessoa",
        "Rubens Teixeira", "Sebastião Filho", "Tiago Carvalho", "Vilbert Santos",
        "Wallace Pereira"
    ]
    dados = _supervisores(nomes, AREAS_SOLICITANTES)
    os.makedirs(PASTA_JSON, exist_ok=True)
    caminho_json = os.path.join(PASTA_JSON, 'supervisores_confinado.json')
    with open(caminho_json, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    print(f"✅ supervisores_confinado.json gerado com {len(dados)} registros (backup)")
    return dados

# ============================================================
# 6. EXECUTAR TODAS AS CONVERSÕES (PARA TESTE)
# ============================================================
if __name__ == "__main__":
    print("="*50)
    print("🚀 EXECUTANDO TODAS AS CONVERSÕES")
    print("="*50)
    
    os.makedirs(PASTA_JSON, exist_ok=True)
    
    # Testa leitura do Excel Matriz
    print("\n📌 Testando leitura do Excel Matriz:")
    dados_resp = converter_responsaveis_excel()
    if dados_resp:
        print(f"   Responsáveis: {len(dados_resp)} registros")
    
    for aba in ["SUPERVISOR TRABALHO EM ALTURA", "SUPERVISOR TRABALHO A QUENTE", "SUPERVISOR TRABALHO CONFINADO"]:
        dados_sup = converter_supervisores_excel(aba)
        if dados_sup:
            print(f"   {aba}: {len(dados_sup)} registros")
    
    print("\n📌 Gerando JSONs (com backup se necessário):")
    converter_treinamentos()
    converter_responsaveis()
    converter_supervisores_altura()
    converter_supervisores_quente()
    converter_supervisores_confinado()
    
    print("="*50)
    print("✅ CONVERSÃO CONCLUÍDA!")
    print(f"📁 Arquivos salvos em: {PASTA_JSON}")
    print("="*50)