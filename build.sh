#!/bin/bash
sudo apt-get update
sudo apt-get install -y wget unzip
# Instalar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb
# Instalar ChromeDriver (versão mais recente disponível)
wget https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.100/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
sudo mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
rm -rf chromedriver-linux64.zip chromedriver-linux64
# Instalar dependências Python
pip install -r requirements.txt