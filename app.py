from flask import Flask, request, jsonify, render_template
import requests
import pandas as pd
from datetime import date, timedelta
import os

app = Flask(__name__)

# --- Função para buscar previsão (adaptada do script original) ---
def buscar_previsao_visualcrossing(cidade, chave_api):
    UNIDADE_MEDIDA = 'metric'
    DIAS_PREVISAO = 7
    url_periodo = f"next{DIAS_PREVISAO}days"
    url_base = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
    params = {
        'unitGroup': UNIDADE_MEDIDA,
        'key': chave_api,
        'contentType': 'json',
        'include': 'days'
    }
    url_completa = f"{url_base}/{cidade}/{url_periodo}"
    print(f"Requisitando API para: {cidade}") # Log no servidor

    dados_formatados = []
    erro_msg = None

    try:
        resposta = requests.get(url_completa, params=params)
        resposta.raise_for_status()
        dados_json = resposta.json()

        if 'days' in dados_json:
            for dia in dados_json['days']:
                dados_formatados.append({
                    'Data': dia.get('datetime'),
                    'Temp Max': dia.get('tempmax'),
                    'Temp Min': dia.get('tempmin'),
                    'Condicoes': dia.get('conditions'),
                    'Precipitacao (%)': dia.get('precipprob'),
                    # Adicione outros campos se desejar
                })
        else:
             erro_msg = "Resposta da API inválida (sem 'days')."
             print("Resposta API:", dados_json)


    except requests.exceptions.HTTPError as e:
         erro_msg = f"Erro na API VisualCrossing: {e.response.status_code} - {e.response.text}"
         print(erro_msg) # Log do erro detalhado no servidor
         if e.response.status_code == 400:
             erro_msg = "Erro ao buscar dados: Verifique o nome da cidade/localização."
         elif e.response.status_code == 401 or e.response.status_code == 403:
             erro_msg = "Erro de autenticação: Verifique sua chave API."
         else:
             erro_msg = f"Erro na API VisualCrossing ({e.response.status_code}). Tente novamente mais tarde."

    except requests.exceptions.RequestException as e:
        erro_msg = f"Erro de conexão ao tentar contatar a API: {e}"
        print(erro_msg)
    except Exception as e:
        erro_msg = f"Ocorreu um erro inesperado no servidor: {e}"
        print(erro_msg)

    return dados_formatados, erro_msg

# --- Rotas da Aplicação Web ---
@app.route('/')
def index():
    # Simplesmente serve o arquivo HTML principal
    # Coloque o index.html em uma pasta chamada 'templates'
    return render_template('index.html')

@app.route('/previsao', methods=['POST'])
def obter_previsao():
    # Pega a cidade enviada pelo formulário (via JavaScript)
    dados_requisicao = request.get_json()
    cidade = dados_requisicao.get('cidade')

    if not cidade:
        return jsonify({'erro': 'Nome da cidade não fornecido.'}), 400

    # IMPORTANTE: Pegue a chave API de forma segura (variável de ambiente é ideal)
    CHAVE_API = os.getenv('VISUALCROSSING_API_KEY', 'SUA_CHAVE_API_AQUI') # Substitua ou configure a variável de ambiente

    if CHAVE_API == 'SUA_CHAVE_API_AQUI':
         print("AVISO: Chave API não configurada no backend!")
         return jsonify({'erro': 'Erro interno no servidor (API Key).'}), 500


    previsao, erro = buscar_previsao_visualcrossing(cidade, CHAVE_API)

    if erro:
        return jsonify({'erro': erro}), 500 # Retorna erro para o frontend
    else:
        return jsonify({'previsao': previsao}) # Retorna os dados formatados

# --- Execução ---
if __name__ == '__main__':
    # Use '0.0.0.0' para ser acessível na rede local, se necessário
    # debug=True é útil durante o desenvolvimento, mas desative em produção
    app.run(debug=True, port=5001) # Usa porta 5001 para evitar conflito com outras apps
