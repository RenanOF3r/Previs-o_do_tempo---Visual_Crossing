import streamlit as st
import requests
import pandas as pd
from datetime import date
import os

# --- Função para buscar previsão (a mesma lógica de antes) ---
def buscar_previsao_visualcrossing(cidade, chave_api):
    UNIDADE_MEDIDA = 'metric'
    DIAS_PREVISAO = 7
    url_periodo = f"next{DIAS_PREVISAO}days"
    url_base = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    params = {
        'unitGroup': UNIDADE_MEDIDA,
        'key': VISUALCROSSING_API_KEY,
        'contentType': 'json',
        'include': 'days'
    }
    url_completa = f"{url_base}/{cidade}/{url_periodo}"
    print(f"Requisitando API para: {cidade}") # Log (aparecerá no terminal onde o Streamlit roda)

    dados_formatados = []
    erro_msg = None

    try:
        resposta = requests.get(url_completa, params=params)
        resposta.raise_for_status() # Lança erro para status HTTP ruins
        dados_json = resposta.json()

        if 'days' in dados_json:
            for dia in dados_json['days']:
                dados_formatados.append({
                    'Data': dia.get('datetime'),
                    'Temp Max (°C)': dia.get('tempmax'),
                    'Temp Min (°C)': dia.get('tempmin'),
                    'Condições': dia.get('conditions'),
                    'Precipitação (%)': dia.get('precipprob'),
                    'Vento (km/h)': dia.get('windspeed'),
                    'Descrição': dia.get('description')
                })
        else:
             erro_msg = "Resposta da API inválida (não contém 'days'). Verifique o nome da cidade."
             print("Resposta API:", dados_json)

    except requests.exceptions.HTTPError as e:
         # Tenta dar uma mensagem de erro mais amigável
         status_code = e.response.status_code
         print(f"Erro HTTP: {status_code} - {e.response.text}") # Log detalhado
         if status_code == 400:
             erro_msg = f"Erro ao buscar dados para '{cidade}'. Verifique se o nome/formato está correto (ex: 'Boston,MA,USA' ou 'London,UK')."
         elif status_code == 401 or status_code == 403:
             erro_msg = "Erro de autenticação: A chave da API é inválida ou expirou."
         elif status_code == 429:
             erro_msg = "Limite de requisições da API excedido. Tente novamente mais tarde."
         else:
             erro_msg = f"Erro na comunicação com a API de previsão do tempo ({status_code})."

    except requests.exceptions.RequestException as e:
        erro_msg = f"Erro de conexão ao tentar contatar a API: {e}"
        print(erro_msg)
    except Exception as e:
        erro_msg = f"Ocorreu um erro inesperado: {e}"
        print(erro_msg)

    return dados_formatados, erro_msg

# --- Interface da Aplicação Streamlit ---

st.set_page_config(page_title="Previsão do Tempo", layout="wide") # Configura título da aba e layout

st.title("☀️ Previsão do Tempo - Próximos 7 Dias 🌧️")
st.markdown("Use a API Visualcrossing para obter a previsão do tempo para qualquer cidade.")

# --- Gerenciamento da Chave API ---
# Para rodar localmente, você pode definir a variável de ambiente VISUALCROSSING_API_KEY
# Para deploy no Streamlit Community Cloud, use os "Secrets"
CHAVE_API = st.secrets.get("VISUALCROSSING_API_KEY", os.getenv("VISUALCROSSING_API_KEY"))

if not CHAVE_API:
    st.error("Erro Crítico: Chave da API Visualcrossing não configurada!")
    st.markdown("""
        **Para rodar localmente:**
        1. Defina a variável de ambiente `VISUALCROSSING_API_KEY` com sua chave.
        2. Reinicie o Streamlit.

        **Para deploy no Streamlit Community Cloud:**
        1. Crie um arquivo `secrets.toml` em `.streamlit/` no seu repositório ou adicione o Secret diretamente na interface do Streamlit Cloud.
        2. Adicione a linha: `VISUALCROSSING_API_KEY = "SUA_CHAVE_REAL_AQUI"`
    """)
    st.stop() # Interrompe a execução se não houver chave

# --- Input do Usuário ---
# Usando colunas para melhor layout
col1, col2 = st.columns([3, 1]) # Coluna 1 é 3x mais larga que a coluna 2

with col1:
    # Input para a cidade, com valor padrão para facilitar
    cidade_input = st.text_input(
        "Digite a localização:",
        value="Rio de Janeiro,RJ,Brasil",
        placeholder="Ex: Paris,France / Tokyo,Japan / Rio de Janeiro,Brazil"
    )

with col2:
    # Botão para iniciar a busca - Adiciona espaço vertical para alinhar melhor
    st.write("") # Espaçador
    st.write("") # Espaçador
    buscar_botao = st.button("Buscar Previsão", type="primary", use_container_width=True)

# --- Lógica de Busca e Exibição ---
if buscar_botao and cidade_input:
    # Mostra uma mensagem enquanto busca
    with st.spinner(f"Buscando previsão para {cidade_input}..."):
        previsao, erro = buscar_previsao_visualcrossing(cidade_input, CHAVE_API)

    if erro:
        st.error(f"Falha ao obter previsão: {erro}")
    elif previsao:
        st.success(f"Previsão para **{cidade_input}** encontrada:")
        df_previsao = pd.DataFrame(previsao)

        # Opcional: Reordenar ou selecionar colunas para exibição
        colunas_exibir = ['Data', 'Temp Min (°C)', 'Temp Max (°C)', 'Condições', 'Precipitação (%)', 'Vento (km/h)', 'Descrição']
        df_exibir = df_previsao[colunas_exibir]

        st.dataframe(df_exibir, use_container_width=True, hide_index=True) # Exibe a tabela de forma interativa
    else:
        st.warning("Nenhuma previsão encontrada para a localização fornecida.")

elif buscar_botao and not cidade_input:
    st.warning("Por favor, digite o nome de uma cidade.")

st.markdown("---")
st.caption("Dados fornecidos por Visual Crossing Weather API.")
