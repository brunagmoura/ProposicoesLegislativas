import streamlit as st
import pandas as pd
import warnings
import requests
from datetime import datetime as dt
import pytz

timezone = pytz.timezone('America/Sao_Paulo')
now = dt.now(timezone)
warnings.filterwarnings('ignore')

st.set_page_config(page_title="Monitor de proposições legislativas", page_icon="📑",
                   layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<div style='text-align: left; color: #666666; font-size: 1em; background-color: #f0f0f0; padding: 10px; border-radius: 5px;margin-bottom: 20px;'>
    💡&nbsp;&nbsp;&nbsp;A busca utiliza a base de dados da Câmara dos Deputados e do Senado Federal e se refere às proposições legislativas selecionadas para acompanhamento. Os resultados são atualizados em tempo real de acordo com a atualização das bases consultadas.
</div>
""", unsafe_allow_html=True)

@st.cache_data(ttl=3600)
def fetch_projetos_deputados(tipo_numeros_anos):
    projetos_deputados = []
    for tipo, numero, ano in tipo_numeros_anos:
        url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
        params = {
            "siglaTipo": tipo,
            "numero": numero,
            "ano": ano,
            "ordenarPor": "ano",
            "ordem": "asc",
            "itens": 1
        }
        response = requests.get(url, params=params)
        if response.status_code == 200:
            projetos_deputados.extend(response.json()["dados"])
        else:
            st.write(f"Erro ao fazer requisição para a API para {numero}/{ano}: {response.status_code}")
    return projetos_deputados

@st.cache_data(ttl=3600)
def fetch_tramitacoes_deputados(id_proposicao):
    url_tramitacoes = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/tramitacoes"
    response_tramitacoes = requests.get(url_tramitacoes)
    if response_tramitacoes.status_code == 200:
        tramitacoes = response_tramitacoes.json()['dados']
        tramitacoes_formatadas = []
        for tr in tramitacoes:
            dataHora = tr.get('dataHora', 'Sem data')
            descricaoTramitacao = tr.get('descricaoTramitacao', 'Sem tramitação')
            apreciacao = tr.get('apreciacao', 'Sem apreciação')
            despacho = tr.get('despacho', 'Sem despacho')
            tramitacao_formatada = f"Data/Hora: {dataHora}, Tramitação: {descricaoTramitacao}, Apreciação: {apreciacao}, Despacho: {despacho} \n"
            tramitacoes_formatadas.append(tramitacao_formatada)
        return "\n ".join(tramitacoes_formatadas)
    else:
        st.write(f"Erro ao obter as tramitações da proposição {id_proposicao}: {response_tramitacoes.status_code}")
        return "Erro ao obter tramitações"

@st.cache_data(ttl=3600)
def fetch_detalhes_deputados(id_proposicao):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}"
    response = requests.get(url)
    if response.status_code == 200:
        dados = response.json()['dados']
        status_proposicao = dados.get('statusProposicao', {})
        return {
            'dataHora': status_proposicao.get('dataHora', 'Sem data'),
            'descricaoTramitacao': status_proposicao.get('descricaoTramitacao', 'Sem tramitação'),
            'descricaoSituacao': status_proposicao.get('descricaoSituacao', 'Sem situação'),
            'despacho': status_proposicao.get('despacho', 'Sem despacho'),
            'apreciacao': status_proposicao.get('apreciacao', 'Sem apreciação')
        }
    else:
        st.write(f"Erro ao obter os detalhes da proposição {id_proposicao}: {response.status_code}")
        return {}

@st.cache_data(ttl=3600)
def fetch_autor_deputados(id_proposicao):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/autores"
    response = requests.get(url)
    if response.status_code == 200:
        dados = response.json()['dados']
        if dados:
            nome_autor = dados[0].get('nome', 'Sem nome do autor')
            return {'autor': nome_autor}
        else:
            return {'autor': 'Sem autores'}
    else:
        st.write(f"Erro ao obter os autores da proposição {id_proposicao}: {response.status_code}")
        return {'autor': 'Erro ao obter dados'}

@st.cache_data(ttl=3600)
def fetch_relacionadas_deputados(id_proposicao):
    url = f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}/relacionadas"
    response = requests.get(url)
    if response.status_code == 200:
        relacionadas = response.json()['dados']
        return [relacionada['id'] for relacionada in relacionadas]
    else:
        st.write(f"Erro ao obter proposições relacionadas para {id_proposicao}: {response.status_code}")
        return []

def create_dataframe_deputados(projetos_deputados):
    if not projetos_deputados:
        st.write("Nenhum projeto foi carregado da API.")
        return pd.DataFrame()  # Retorna um DataFrame vazio se não houver projetos

    for proposicao in projetos_deputados:
        id_proposicao = proposicao.get('id')
        if id_proposicao:
            detalhes = fetch_detalhes_deputados(id_proposicao)
            proposicao.update(detalhes)
            autor = fetch_autor_deputados(id_proposicao)
            proposicao.update(autor)
            relacionadas = fetch_relacionadas_deputados(id_proposicao)
            proposicao['relacionadas'] = ", ".join(map(str, relacionadas))
            tramitacoes = fetch_tramitacoes_deputados(id_proposicao)
            proposicao['tramitacoes'] = tramitacoes

    colunas = ['id', 'siglaTipo', 'numero', 'ano', 'autor', 'ementa', 'dataHora',
               'descricaoTramitacao', 'descricaoSituacao', 'despacho', 'apreciacao', 'tramitacoes', 'relacionadas']
    df_deputados = pd.DataFrame(projetos_deputados, columns=colunas)

    if df_deputados.empty:
        st.write("DataFrame está vazio após limpar NaNs.")
        return df_deputados

    df_deputados['dataHora'] = pd.to_datetime(df_deputados['dataHora'], errors='coerce')
    df_deputados = df_deputados.sort_values(by='dataHora', ascending=False)
    df_deputados['ano'] = df_deputados['ano'].astype(int)
    df_deputados['numero'] = df_deputados['numero'].astype(int)

    df_deputados.columns = ["ID Proposição", "Tipo", "Número", "Ano", "Autor", "Ementa", "Data e Hora da última tramitação",
                            "Última tramitação", "Última situação", "Último despacho", "Última apreciação", "Histórico de tramitações", "Proposições relacionadas"]
    return df_deputados

# Lista de números e anos das proposições
tipo_numeros_anos = [
    ("PL", 5531, 2020), ("PL", 5861, 2023), ("PL", 4154, 2019), ("PL", 4522, 2021), ("PL", 2408, 2023), ("PL", 2941, 2023),
    ("PL", 2133, 2023), ("PL", 1032, 2023), ("PL", 2987, 2023), ("PLP", 143, 2020), ("PL", 4435, 2021), ("PL", 3127, 2023),
    ("PL", 3457, 2023), ("PL", 3433, 2021), ("PL", 6093, 2023), ("PL", 2414, 2023), ("PL", 7938, 2017), ("PL", 285, 2015),
    ("PL", 3105, 2020), ("PL", 5277, 2023), ("PL", 1496, 2023), ("PL", 2857, 2022), ("PL", 2910, 2023), ("PL", 4423, 2016),
    ("PL", 2413, 2023), ("PL", 578, 2023), ("PL", 3928, 2012), ("PL", 4518, 2021), ("PL", 2521, 2015), ("PL", 3226, 2023),
    ("PL", 10147, 2018), ("PL", 4977, 2016), ("PL", 3165, 2015), ("PL", 4907, 2019), ("PL", 4049, 2023), ("PDL", 334, 2023),
    ("PL", 484, 2022), ("PL", 97, 2023), ("PLP", 101, 2022), ("PL", 3876, 2015), ("PLP", 79, 2022), ("PLP", 191, 2019),
    ("PL", 3636, 2015), ("PL", 9163, 2017), ("PL", 2678, 2022), ("PL", 561, 2022), ("PL", 3394, 2015), ("PL", 1202, 2007),
    ("REQ", 90, 2023)
]

projetos_deputados = fetch_projetos_deputados(tipo_numeros_anos)
df_deputados = create_dataframe_deputados(projetos_deputados)

#Ano está formatado como número
def formatar_numero(valor):
    return f"{valor}"

dados_formatados_deputados = df_deputados.style.format({'Número': formatar_numero,
                                                        'Ano': formatar_numero})

st.markdown(
    "<div style='text-align: center; color: #555555; font-size: 1.3em;margin-bottom: 20px;'>Proposições legislativas selecionadas na Câmara dos Deputados</div>",
    unsafe_allow_html=True)

st.dataframe(dados_formatados_deputados, use_container_width=True, hide_index=True, height=500)

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

csv_deputados = convert_df(df_deputados)

st.download_button(
   "Pressione para fazer o download",
   csv_deputados,
   "proposicoes_deputados.csv",
   "text/csv",
   key='download-csv'
)
