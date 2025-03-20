#!/bin/bash
# Instalar dependências básicas para o Chrome e Xvfb
apt-get update
apt-get install -y wget unzip libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1 libx11-6 libxext6 libxrender1 libxi6 libxtst6 libxkbcommon0 libdbus-1-3 libgtk-3-0 libasound2 libgbm1 libxshmfence1 libgl1-mesa-glx xvfb
# Baixar e instalar Chrome manualmente
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
ar x google-chrome-stable_current_amd64.deb
tar -xvf data.tar.xz
mkdir -p ./chrome
mv opt/google/chrome/chrome ./chrome/chrome
chmod +x ./chrome/chrome
rm -rf google-chrome-stable_current_amd64.deb data.tar.xz opt control.tar.gz
# Instalar ChromeDriver no diretório local (versão compatível com Chrome 134)
wget https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.117/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
chmod +x chromedriver-linux64/chromedriver
mkdir -p ./chromedriver
mv chromedriver-linux64/chromedriver ./chromedriver/chromedriver
rm -rf chromedriver-linux64.zip chromedriver-linux64
# Verificar instalação
./chromedriver/chromedriver --version
./chrome/chrome --version
# Instalar dependências Python
pip install -r requirements.txt