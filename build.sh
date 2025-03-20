#!/bin/bash
apt-get update
apt-get install -y wget unzip
# Instalar Google Chrome
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb
# Instalar ChromeDriver
wget https://storage.googleapis.com/chrome-for-testing-public/129.0.6668.100/linux64/chromedriver-linux64.zip
unzip chromedriver-linux64.zip
mv chromedriver-linux64/chromedriver /usr/local/bin/chromedriver
rm -rf chromedriver-linux64.zip chromedriver-linux64
# Instalar dependências Python
pip install -r requirements.txt