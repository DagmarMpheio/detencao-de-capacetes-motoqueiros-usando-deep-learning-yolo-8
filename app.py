import os
import uuid
import urllib
import argparse
import io
from PIL import Image
import datetime

import torch
import cv2
import numpy as np
import tensorflow as tf
from keras.utils import load_img, img_to_array
from keras.models import load_model

from re import DEBUG, sub

import flask
from flask import Flask, render_template, request, send_file, redirect, url_for, Response
from werkzeug.utils import secure_filename
from flask import send_from_directory
import subprocess
from subprocess import Popen
import re
import requests
import shutil
import time
import glob

from ultralytics import YOLO


app = Flask(__name__)

@app.route('/')
def home():
    return render_template("index.html")
    
# metodo de classificacao do modelo
imgpath = None  # Definir uma variável global para armazenar o nome do arquivo

@app.route("/", methods=["GET", "POST"])
def predict_img():
    global imgpath  # Indicar que a variável imgpath será usada globalmente
    
    if request.method == "POST":
        if 'file' in request.files:
            f = request.files['file']
            basepath = os.path.dirname(__file__)
            filepath = os.path.join(basepath,'uploads', f.filename)
            print("upload folder is ", filepath)
            f.save(filepath)
            
            imgpath = f.filename # Atribuir o nome do arquivo à variável global imgpath
            print("Imagem Detectada: ", imgpath) # Imprimir o valor da variável imgpath

            file_extension = f.filename.rsplit('.',1)[1].lower()
            print("extensao: ",file_extension)

            # se na requisicao tiver um ficheiro e está de acordo com as extensões permitidas, faça
            if file_extension == 'jpg':
                img = cv2.imread(filepath)
                print("img: ",img)

                #Trabalhar com o YOLO na Detenção de imagens
                model = YOLO('best.pt')
                #predictions = model.predict(filepath, save= True)
                predictions = model(filepath, save= True)
                print("predictions: ",predictions["names"])
                
                return display(f.filename)
            
            elif file_extension == 'mp4':
                video_path = filepath
                cap = cv2.VideoCapture(video_path)

                # Pegar as dimenções do video
                frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

                # Definir o codec e criar o objecto VideoWrite
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                out = cv2.VideoWriter('output.mp4', fourcc,30.0,(frame_width, frame_height))

                # Inicializar o modelo YOLO v8 aqui
                model = YOLO('best.pt')

                while cap.isOpened():
                    ret, frame=cap.read()
                    if not ret: 
                        break

                    # Fazer a detenção do YOLO vc8 nos frames aqui
                    results = model(frame, save=True)
                    print(results)
                    cv2.waitKey(1)

                    res_plotted = results[0].plot()
                    cv2.imshow("result", res_plotted)

                    # Escrever o video da saida
                    out.write(res_plotted)

                    if cv2.waitKey(1)==ord('q'):
                        break
            
                return video_feed()
                
    # se o usuario nao preencher o formulario, mantem na mesma pagina
    #else:
        #return render_template('index.html')
    
  
    #folder_path = 'runs/detect'
    #subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    #latest_subfolder = max(subfolders, key=lambda x: os.path.getctime(os.path.join(folder_path, x)))
    #image_path = folder_path+'/'+latest_subfolder+'/'+f.filename
    #return render_template('index.html', image_path=image_path)
    


@app.route('/image/<path:filename>')
def display(filename):
    folder_path = 'runs/detect'
    subfolders = [f for f in os.listdir(folder_path) if os.path.isdir(os.path.join(folder_path, f))]
    latest_subfolder = max(subfolders, key=lambda x: os.path.getctime(os.path.join(folder_path,x)))
    directory = folder_path+'/'+latest_subfolder
    print("Mostrando sub directorios: ", directory)
    files = os.listdir(directory)
    latest_file = files[0]

    print("ultima imagem: ",latest_file)

    filename = os.path.join(folder_path, latest_subfolder, latest_file)
    print("file: ",filename)
    
    
   

    file_extension = filename.rsplit('.',1)[1].lower()

    environ = request.environ
    if file_extension == 'jpg':
        # Copiar o arquivo para o diretório de destino
        shutil.copy(filename, 'static/detencoes')
        
        #return send_from_directory(directory, filename) # Mostrar o resultado detectados no boldenbox
        #return render_template('display_image.html', filename=latest_file, directory=directory)
        # Renderize a mesma página com a imagem enviada
        #return render_template('index.html', latest_file=latest_file)
        # Redirecione para a página que exibirá a imagem enviada
        return render_template('index.html', latest_file=latest_file)
    
    else:
        return " Invalid file format"
    

def get_frame():
    folder_path = os.getcwd()
    mp4_files = 'output.mp4'
    video = cv2.VideoCapture(mp4_files) # caminho de detenção de video
    while True:
        success, image = video.read()
        if not success:
            break
        ret, jpeg = cv2.imencode('.jpg', image)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
        time.sleep(0.1) # Controlar o video pro um(1)ms no ecrá


# Função para detectar objectos em video numa página HTML
@app.route("/video_feed")
def video_feed():
    print ("function called")
    return Response(get_frame(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SISDET")
    parser.add_argument("--port", default=5000, type=int, help="port number")
    args = parser.parse_args()
    app.run(host="0.0.0.0", port=args.port)  # debug=True causes Restarting with stat
