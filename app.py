# from flask import Flask, render_template, request, jsonify
# import plotly.graph_objs as go
# import plotly.express as px
# import numpy as np

# # from keras.models import load_model
# from tensorflow.keras.models import load_model

# from src.get_data import GetData
# from src.utils import create_figure, prediction_from_model 
# import flask_monitoringdashboard as dashboard

# app = Flask(__name__)

# dashboard.config.init_from(file='config.cfg')

# data_retriever = GetData(url="https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/etat-du-trafic-en-temps-reel/exports/json?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B")
# data = data_retriever()

# model = load_model('model.h5') 

# @app.route('/', methods=['GET', 'POST'])
# def index():

#     if request.method == 'POST':

#         fig_map = create_figure(data)
#         graph_json = fig_map.to_json()

#         selected_hour = request.form['hour']

#         cat_predict = prediction_from_model(model,selected_hour) # Ajout de la prise en compte de l'heure ici

#         color_pred_map = {0:["Prédiction : Libre", "green"], 1:["Prédiction : Dense", "orange"], 2:["Prédiction : Bloqué", "red"]}

#         return render_template('home.html', graph_json=graph_json, text_pred=color_pred_map[cat_predict][0], color_pred=color_pred_map[cat_predict][1],selected_hour=selected_hour)
# # Ajout de la prise en compte de l'heure
#     else:

#         fig_map = create_figure(data)
#         graph_json = fig_map.to_json()

#         return render_template('home.html', graph_json=graph_json)
# # il n'ya avait pas de route home.html mais index.html donc j'ai dû renommer le nom du html (j'aurai egalement pu renommer les redirection de route tout simplement)
# @app.route('/monitor')
# def monitor():
#     return render_template('monitor.html')
# dashboard.bind(app)

# if __name__ == '__main__':
#     app.run(debug=True)

from flask import Flask, render_template, request, jsonify, g
import time
import logging
from logging.handlers import RotatingFileHandler
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from tensorflow.keras.models import load_model
from src.get_data import GetData
from src.utils import create_figure, prediction_from_model
import flask_monitoringdashboard as dashboard
from collections import deque
from time import time

app = Flask(__name__)

# Configuration du logger
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Limiteur de taux
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "50 per hour"]
)

# Initialiser le compteur de requêtes et les erreurs HTTP
request_times = deque(maxlen=1000)
error_logs = deque(maxlen=1000)

# Middleware combiné pour mesurer le temps de réponse et les RPS
@app.before_request
def before_request():
    # Mesurer le temps de réponse
    g.start_time = time()
    
    # Suivre les RPS (Requêtes par seconde)
    request_times.append(time())
    # Compter les requêtes dans la dernière seconde
    requests_last_second = len([t for t in request_times if t > time() - 1])
    if requests_last_second > 100:  # Seuil d'alerte pour les RPS
        app.logger.warning(f"Nombre de requêtes par seconde élevé: {requests_last_second} RPS")

@app.after_request
def after_request(response):
    # Mesurer le temps de réponse
    total_time = time() - g.start_time
    if total_time > 3:  # Seuil en secondes pour temps de réponse
        app.logger.warning(f"Temps de réponse élevé: {total_time}s pour la route {request.path}")
    # Surveiller les erreurs HTTP
    if response.status_code >= 400:
        error_logs.append({'timestamp': time(), 'status_code': response.status_code})
        app.logger.error(f"Erreur HTTP {response.status_code} pour la route {request.path}")
    return response

# Route pour fournir les données de monitoring
@app.route('/monitoring-data')
def monitoring_data():
    # Collecter les timestamps et les valeurs pour les graphiques
    response_time_data = {
        'timestamps': list(request_times),
        'response_times': [time() - start for start in request_times]
    }
    rps_data = {
        'timestamps': list(request_times),
        'requests_per_second': [len([t for t in request_times if t > time() - 1])]
    }
    http_error_data = {
        'timestamps': [log['timestamp'] for log in error_logs],
        'error_counts': [log['status_code'] for log in error_logs]
    }

    return jsonify({
        'response_time_data': response_time_data,
        'rps_data': rps_data,
        'http_error_data': http_error_data
    })

# Configuration du dashboard
dashboard.config.init_from(file='config.cfg')

data_retriever = GetData(url="https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/etat-du-trafic-en-temps-reel/exports/json?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B")
data = data_retriever()

model = load_model('model.h5')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_time = time()
        fig_map = create_figure(data)
        graph_json = fig_map.to_json()
        selected_hour = request.form['hour']
        cat_predict = prediction_from_model(model, selected_hour)  # Ajout de la prise en compte de l'heure ici
        prediction_time = time() - start_time
        if prediction_time > 2:  # Seuil d'alerte pour le temps de réponse des prédictions
            app.logger.warning(f"Temps de réponse des prédictions élevé: {prediction_time}s")
        color_pred_map = {0:["Prédiction : Libre", "green"], 1:["Prédiction : Dense", "orange"], 2:["Prédiction : Bloqué", "red"]}
        return render_template('home.html', graph_json=graph_json, text_pred=color_pred_map[cat_predict][0], color_pred=color_pred_map[cat_predict][1], selected_hour=selected_hour)
    else:
        fig_map = create_figure(data)
        graph_json = fig_map.to_json()
        return render_template('home.html', graph_json=graph_json)

@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

dashboard.bind(app)

if __name__ == '__main__':
    app.run(debug=True)