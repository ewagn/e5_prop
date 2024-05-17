from flask import Flask, render_template, request, jsonify
import plotly.graph_objs as go
import plotly.express as px
import numpy as np

# from keras.models import load_model
from tensorflow.keras.models import load_model

from src.get_data import GetData
from src.utils import create_figure, prediction_from_model 
import flask_monitoringdashboard as dashboard
import logging
from logging.handlers import RotatingFileHandler

app = Flask(__name__)

dashboard.config.init_from(file='config.cfg')

data_retriever = GetData(url="https://data.rennesmetropole.fr/api/explore/v2.1/catalog/datasets/etat-du-trafic-en-temps-reel/exports/json?lang=fr&timezone=Europe%2FBerlin&use_labels=true&delimiter=%3B")
data = data_retriever()

model = load_model('model.h5') 

handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)

@app.route('/', methods=['GET', 'POST'])
def index():

    if request.method == 'POST':

        fig_map = create_figure(data)
        graph_json = fig_map.to_json()

        selected_hour = request.form['hour']

        cat_predict = prediction_from_model(model,selected_hour) # Ajout de la prise en compte de l'heure ici

        color_pred_map = {0:["Prédiction : Libre", "green"], 1:["Prédiction : Dense", "orange"], 2:["Prédiction : Bloqué", "red"]}

        return render_template('home.html', graph_json=graph_json, text_pred=color_pred_map[cat_predict][0], color_pred=color_pred_map[cat_predict][1],selected_hour=selected_hour)
# Ajout de la prise en compte de l'heure
    else:

        fig_map = create_figure(data)
        graph_json = fig_map.to_json()

        return render_template('home.html', graph_json=graph_json)
# il n'ya avait pas de route home.html mais index.html donc j'ai dû renommer le nom du html (j'aurai egalement pu renommer les redirection de route tout simplement)
@app.route('/monitor')
def monitor():
    return render_template('monitor.html')
dashboard.bind(app)

if __name__ == '__main__':
    app.run(debug=True)