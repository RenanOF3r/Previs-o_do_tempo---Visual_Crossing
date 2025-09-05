import streamlit as st
import pandas as pd
from app import buscar_previsao_visualcrossing

# Título da aplicação
st.title("Previsão do Tempo com Visual Crossing")

# Aviso sobre a chave da API
if not "VISUALCROSSING_API_KEY" in st.secrets:
    st.error("AVISO: Chave API não configurada em `secrets.toml`!")

# Campo de entrada para a cidade
cidade = st.text_input("Digite o nome da cidade (ex: Boston,MA,USA):")

# Botão para buscar a previsão
if st.button("Buscar Previsão"):
    if not cidade:
        st.error("Por favor, digite o nome de uma cidade.")
    else:
        # Acessa a chave da API do secrets.toml
        api_key = st.secrets["VISUALCROSSING_API_KEY"]

        # Mostra uma mensagem de status enquanto busca os dados
        with st.spinner(f"Buscando previsão para {cidade}..."):
            try:
                # Chama a função de busca de previsão do arquivo app.py
                dados_previsao, erro = buscar_previsao_visualcrossing(cidade, api_key)

                if erro:
                    st.error(erro)
                elif dados_previsao:
                    # Converte a lista de dicionários para um DataFrame do pandas
                    df_previsao = pd.DataFrame(dados_previsao)

                    # Exibe os dados em uma tabela
                    st.subheader("Previsão para os Próximos 7 Dias")
                    st.dataframe(df_previsao)
                else:
                    st.warning("Nenhuma previsão encontrada para esta cidade.")

            except Exception as e:
                st.error(f"Ocorreu um erro inesperado: {e}")
