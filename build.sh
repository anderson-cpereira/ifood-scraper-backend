#!/bin/bash
apt-get update
apt-get install -y wget unzip
# Instalar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb
# Instalar ChromeDriver
wget https://chromedriver.storage.googleapis.com/129.0.6668.100/chromedriver_linux64.zip
unzip chromedriver_linux64.zip -d /usr/local/bin/
rm chromedriver_linux64.zip
# Instalar dependências Python
pip install -r requirements.txt