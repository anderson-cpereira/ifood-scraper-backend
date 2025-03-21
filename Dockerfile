FROM python:3.11-slim

# Instalar dependências do sistema, incluindo gnupg
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    xvfb \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Instalar ChromeDriver
RUN wget -O /tmp/chromedriver.zip https://storage.googleapis.com/chrome-for-testing-public/134.0.6998.90/linux64/chromedriver-linux64.zip \
    && unzip /tmp/chromedriver.zip -d /usr/local/bin/ \
    && mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver \
    && rm -rf /tmp/chromedriver.zip /usr/local/bin/chromedriver-linux64

# Configurar diretório de trabalho
WORKDIR /app
COPY . /app

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000

# Comando para rodar a aplicação
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "10000"]