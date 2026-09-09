import json
import os
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get('PTW_DATA_DIR', Path('/tmp') / 'ptw_dados'))

AREAS_RESPONSAVEIS = [
    "Telhados/Caixas d'água",
    "Logística (interno e pátio externo) + Sala de Baterias",
    "Cavaco, café verde, fornalha, torradores e moagem",
    "Empacatamento - Fabrimas, Raumak's, Robôs e PKD)",
    "Almoxarifado comum e embalagens + Almoxarifado Peças - Manutenção",
    "Sala de Inflamáveis", "Tanque de GLP",
    "Facilites (Áreas comuns, externas, ADM's, Convivência, Refeitório, Ambulatório, Portaria, Estacionamento",
    "Central de resíduos, Classe 1 e caixa SAO", "Galpãp 2", "Galpão 3",
    "Subestação elétrica/ QGBT geradores/ compressores", "ADM Qualidade, CQCV e Shelf-life",
    "Casa de bombas, caixa dágua de incêndio, painel de emergência, alarmes e hidrantes",
    "Sala e oficiana da Manutenção", "Livre Retirada - Manutenção (Galpão 2)"
]

AREAS_SUPERVISORES = [
    "Telhados/Caixas d'água", "Logística (interno e externo)", "Café Verde",
    "Manufatura (fornalha ao empacotamento)", "Almoxarifado", "Sala de Inflamáveis",
    "Tanques de GLP", "Facilites", "DTRS", "Galpãp 2", "Galpão 3",
    "subestação elétrica/ geradores/ compressores", "CQ",
    "Sistema de Proteção e Combate a Incêndio", "Áreas Comuns", "Sala da Manutenção",
    "Livre Retirada"
]


def text(value):
    if pd.isna(value):
        return ''
    if isinstance(value, pd.Timestamp):
        return value.strftime('%d/%m/%Y')
    return str(value).strip()


def selected(value):
    return text(value).upper() in {'SIM', 'X', '1', 'TRUE', 'VERDADEIRO'}


def normalizar_nome_area(value):
    return re.sub(r'\s+', ' ', text(value)).strip().casefold()


def _write(name, data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def converter_treinamentos(source):
    with pd.ExcelFile(source) as excel:
        df_ptw = pd.read_excel(excel, sheet_name='PT').fillna('')
        df_cadastro = pd.read_excel(excel, sheet_name='CADASTRO').fillna('')
    cadastro = {}
    for _, row in df_cadastro.iterrows():
        nome = text(row.get('NOME', '')).upper()
        if nome:
            cadastro[nome] = row

    registros = {}
    for _, row in df_ptw.iterrows():
        nome = text(row.get('NOME', ''))
        treinamento = text(row.get('TREINAMENTO', '')).upper()
        status = text(row.get('STATUS', '')).upper()
        if not nome or treinamento not in {'PT', 'PTW'} or status not in {'NO PRAZO', 'APROVADO', 'VENCIDO'}:
            continue
        cadastro_row = cadastro.get(nome.upper())
        if cadastro_row is None or text(cadastro_row.get('STATUS', '')).upper() != 'ATIVO':
            continue
        cargo = text(row.get('CARGO', '')).upper()
        if any(item in cargo for item in ('HIRENOW', 'ESTAGIARIO', 'ESTAGIÁRIO', 'APRENDIZ')):
            continue
        registro = {
            'nome': nome, 'cargo': cargo, 'area': text(cadastro_row.get('ÁREA', '')),
            'status': status, 'vence_em': text(row.get('VENCE EM', '')),
            'treinado_em': text(row.get('TREINADO EM', '')),
            'instrutor': text(row.get('INSTRUTOR', '')), 'condicao': text(row.get('CONDIÇÃO', '')),
            'situacao': 'ATIVO', 'areas': AREAS_SUPERVISORES
        }
        registros[nome] = registro
    data = list(registros.values())
    _write('solicitantes.json', data)
    return data


def converter_responsaveis(source):
    df = pd.read_excel(source, sheet_name='RESPONSAVEIS DE AREA', dtype=str).fillna('')
    nome_coluna = 'Responsáveis pela área' if 'Responsáveis pela área' in df.columns else 'Nome'
    colunas_area = {normalizar_nome_area(coluna): coluna for coluna in df.columns}
    data = []
    for _, row in df.iterrows():
        nome = text(row.get(nome_coluna, ''))
        areas = [
            area for area in AREAS_RESPONSAVEIS
            if (coluna := colunas_area.get(normalizar_nome_area(area)))
            and selected(row.get(coluna, ''))
        ]
        if nome and areas:
            data.append({'nome': nome, 'cargo': 'Responsável por Área', 'areas': areas})
    _write('responsaveis.json', data)
    return data


def converter_supervisores(source):
    result = {}
    for sheets, filename in [
        (('SUPERVISOR TRABALHO ALTURA', 'SUPERVISOR TRABALHO EM ALTURA', 'Supervisor de Trabalho a Altura'), 'supervisores_altura.json'),
        (('SUPERVISOR TRABALHO QUENTE', 'SUPERVISOR TRABALHO A QUENTE', 'Supervisor de Trabalho Quente'), 'supervisores_quente.json'),
        (('SUPERVISOR TRABALHO CONFINADO',), 'supervisores_confinado.json')
    ]:
        with pd.ExcelFile(source) as excel:
            sheet = next((nome for nome in sheets if nome in excel.sheet_names), None)
            if sheet is None:
                raise ValueError(f'Nenhuma aba encontrada para {filename}: {", ".join(sheets)}.')
            df = pd.read_excel(excel, sheet_name=sheet, dtype=str).fillna('')
        nome_coluna = 'Nome' if 'Nome' in df.columns else df.columns[0]
        colunas_area = {normalizar_nome_area(coluna): coluna for coluna in df.columns}
        data = []
        for _, row in df.iterrows():
            nome = text(row.get(nome_coluna, ''))
            marcadas = [
                area for area in AREAS_SUPERVISORES
                if (coluna := colunas_area.get(normalizar_nome_area(area)))
                and selected(row.get(coluna, ''))
            ]
            if nome and marcadas:
                data.append({'nome': nome, 'cargo': 'Supervisor', 'areas': marcadas})
        _write(filename, data)
        result[filename] = data
    return result
