import requests
import os
from pathlib import Path
from urllib.parse import urlparse

# ============================================================
# CONFIGURAÇÕES
# ============================================================
URL_SHAREPOINT = "https://coffeeandtea.sharepoint.com/sites/TreinamentosPiumhi/Registro%20de%20Treinamentos/Banco%20de%20Dados%20Power%20BI/Treinamentos%20obrigat%C3%B3rios%20(SHE-QUALID).xlsx"

# Caminho onde salvar o arquivo
pasta_raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARQUIVO_EXCEL = os.path.join(pasta_raiz, "Treinamentos obrigatórios (SHE-QUALID).xlsx")

def baixar_excel():
    """Baixa o arquivo Excel do SharePoint"""
    print(f"📥 Baixando Excel do SharePoint...")
    print(f"   URL: {URL_SHAREPOINT}")
    
    try:
        # Faz a requisição
        response = requests.get(URL_SHAREPOINT)
        
        if response.status_code == 200:
            # Salva o arquivo
            with open(ARQUIVO_EXCEL, 'wb') as f:
                f.write(response.content)
            print(f"✅ Excel baixado com sucesso!")
            print(f"   📁 Salvo em: {ARQUIVO_EXCEL}")
            return True
        else:
            print(f"❌ Erro ao baixar: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao baixar: {e}")
        print("   ⚠️ Você precisa ter acesso ao SharePoint e estar na rede da empresa")
        print("   🔧 Alternativa: Baixe manualmente e coloque na pasta")
        return False

if __name__ == "__main__":
    baixar_excel()
    