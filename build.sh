#!/bin/bash
# Instalar dependências básicas
apt-get update
apt-get install -y wget unzip libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1
# Instalar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -f -y
rm google-chrome-stable_current_amd64.deb
# Instalar ChromeDriver no diretório local
wget https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.100/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
chmod +x chromedriver-linux64/chromedriver
mkdir -p ./chromedriver
mv chromedriver-linux64/chromedriver ./chromedriver/chromedriver
rm -rf chromedriver-linux64.zip chromedriver-linux64
# Verificar instalação
./chromedriver/chromedriver --version
# Instalar dependências Python
pip install -r requirements.txt