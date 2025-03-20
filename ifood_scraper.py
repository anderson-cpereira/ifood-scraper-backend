from typing import List, Dict, Optional, Any
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from urllib3.exceptions import InsecureRequestWarning
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from progresso import progresso_lock , progresso_por_task
from datetime import datetime
import os
import logging
import argparse
import re
import random
import time
import requests
import warnings
import json
import base64
import yaml
import platform

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("./ifood_scraping.log", mode='w'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

warnings.simplefilter("ignore", InsecureRequestWarning)

def carregar_config(caminho_config: str = "./config.yaml") -> Dict[str, Any]:
    """Carrega o arquivo de configuração YAML."""
    try:
        with open(caminho_config, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Arquivo de configuração {caminho_config} não encontrado.")
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar configuração: {e}")
        raise

def validar_seletores(type_search: str, driver: webdriver.Chrome, config: Dict[str, Any]) -> bool:
    """Valida se os seletores do config.yaml estão funcionando."""
    try:
        if type_search == 'M':
            driver.get(config["urls"]["markets"])
        else:
            driver.get(config["urls"]["pharmacies"])
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, config["selectors"]["location_button"]))
        )
        logger.info("Seletores principais validados com sucesso.")
        return True
    except TimeoutException:
        logger.error("Seletores do config.yaml não encontrados. Verifique o arquivo de configuração.")
        return False
    
def configurar_driver(headless: bool = True) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 1
    })

    # Detectar o ambiente
    if platform.system() == "Windows":
        chromedriver_path = os.path.join(os.path.dirname(__file__), "chromedriver.exe")
    else:  # Linux (Render)
        chromedriver_path = os.path.join(os.path.dirname(__file__), "chromedriver", "chromedriver")

    if not os.path.exists(chromedriver_path):
        raise FileNotFoundError(f"ChromeDriver não encontrado em: {chromedriver_path}")
    servico = Service(executable_path=chromedriver_path)

    try:
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        driver.set_window_size(1280, 720)
        logger.info("Driver configurado com sucesso (headless={}).".format(headless))
        return driver
    except WebDriverException as e:
        logger.error(f"Falha ao iniciar o ChromeDriver: {e}")
        raise
'''
def configurar_driver(headless: bool = True) -> webdriver.Chrome:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.geolocation": 1
    })
    
    servico = Service(executable_path="./chromedriver.exe")
    try:
        driver = webdriver.Chrome(service=servico, options=chrome_options)
        driver.set_window_size(1280, 720)
        logger.info("Driver configurado com sucesso (headless={}).".format(headless))
        return driver
    except WebDriverException as e:
        logger.error(f"Falha ao iniciar o ChromeDriver: {e}")
        raise
'''

def limpar_diretorio_imagens(pasta: str = "imagens_ifood") -> None:
    """Apaga todas as imagens existentes no diretório antes de salvar novas."""
    if os.path.exists(pasta):
        for arquivo in os.listdir(pasta):
            caminho_arquivo = os.path.join(pasta, arquivo)
            try:
                if os.path.isfile(caminho_arquivo):
                    os.remove(caminho_arquivo)
                    logger.info(f"Imagem antiga removida: {caminho_arquivo}")
            except Exception as e:
                logger.error(f"Erro ao remover imagem {caminho_arquivo}: {e}")
    else:
        os.makedirs(pasta)
        logger.info(f"Diretório {pasta} criado, pois não existia.")

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutException, WebDriverException)),
    before_sleep=lambda retry_state: logger.info(f"Tentativa {retry_state.attempt_number} falhou, retrying...")
)
def definir_localizacao_automatica(type_search: str, driver: webdriver.Chrome, config: Optional[Dict[str, Any]] = None) -> None:
    """Clica no botão 'Usar minha localização' e espera a lista de mercados carregar."""
    if config is None:
        config = carregar_config()
    try:
        if type_search == 'M':
            driver.get(config["urls"]["markets"])
        else:
            driver.get(config["urls"]["pharmacies"])
        logger.info("Aguardando o botão 'Usar minha localização'...")
        botao_localizacao = WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.element_to_be_clickable((By.CLASS_NAME, config["selectors"]["location_button"]))
        )
        botao_localizacao.click()
        
        logger.info("Aguardando a lista de mercados carregar...")
        WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, config["selectors"]["markets"]["card"]))
        )
        logger.info("Localização definida e lista de mercados carregada!")
        
    except TimeoutException as e:
        logger.error(f"Erro ao definir localização automática: {e}")
        logger.info(f"HTML da página: {driver.page_source[:2000]}...")
        raise
    except WebDriverException as e:
        logger.error(f"Erro de WebDriver ao definir localização: {e}")
        raise

def rolar_pagina(driver: webdriver.Chrome, max_items: int, classe_cards: str) -> List[Any]:
    """Rola a página até carregar o número desejado de itens e retorna os elementos."""
    logger.info(f"Rolando a página para carregar até {max_items} itens...")
    altura_atual = 0
    
    while True:
        items = driver.find_elements(By.CLASS_NAME, classe_cards)
        if len(items) >= max_items:
            logger.info(f"Carregados {len(items)} itens, suficiente para {max_items}.")
            return items[:max_items]
        
        altura_total = driver.execute_script("return document.body.scrollHeight")
        if altura_atual >= altura_total:
            logger.info("Fim da página alcançado.")
            return items
        
        driver.execute_script("window.scrollBy(0, 500);")
        altura_atual += 500
        time.sleep(0.1)

def baixar_imagem(url_imagem: Optional[str], nome_arquivo: str, pasta: str = "imagens_ifood") -> Optional[str]:
    """Baixa a imagem da URL ou decodifica base64 e salva localmente sem alterar o fundo."""
    if url_imagem is None:
        logger.warning("URL da imagem é None, skipping download.")
        return None

    imagem_url: str = url_imagem

    if not os.path.exists(pasta):
        os.makedirs(pasta)
    nome_arquivo = "".join(c for c in nome_arquivo if c.isalnum() or c in " _-")[:100]
    caminho_final = os.path.join(pasta, f"{nome_arquivo}.png")  # Salva como PNG

    if imagem_url.startswith("data:image"):
        try:
            header, encoded = imagem_url.split(",", 1)
            extensao = header.split("/")[1].split(";")[0]
            imagem_data = base64.b64decode(encoded)
            
            with open(caminho_final, "wb") as f:
                f.write(imagem_data)
            logger.info(f"Imagem base64 salva em: {caminho_final}")
            return f"/imagens_ifood/{nome_arquivo}.png"  # Caminho relativo para o FastAPI
        except Exception as e:
            logger.error(f"Erro ao decodificar imagem base64 {imagem_url[:50]}...: {e}")
            return None

    try:
        response = requests.get(imagem_url, timeout=10, verify=False)
        response.raise_for_status()
        
        with open(caminho_final, "wb") as f:
            f.write(response.content)
        logger.info(f"Imagem salva em: {caminho_final}")
        return f"/imagens_ifood/{nome_arquivo}.png"  # Caminho relativo para o FastAPI
    except requests.exceptions.SSLError as e:
        logger.error(f"Erro SSL ao baixar a imagem {imagem_url}: {e}")
        return None
    except requests.RequestException as e:
        logger.error(f"Erro ao baixar a imagem {imagem_url}: {e}")
        return None

def baixar_imagens_em_paralelo(imagens: List[Dict[str, str]], pasta: str = "imagens_ifood") -> None:
    """Baixa várias imagens em paralelo usando threads."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(baixar_imagem, img["url"], img["nome"], pasta): img
            for img in imagens if img["url"]
        }
        for future in as_completed(futures):
            img_data = futures[future]
            try:
                img_data["caminho"] = future.result()
            except Exception as e:
                logger.error(f"Erro ao baixar imagem {img_data['url']}: {e}")
                img_data["caminho"] = None

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutException, WebDriverException)),
    before_sleep=lambda retry_state: logger.info(f"Tentativa {retry_state.attempt_number} falhou, retrying...")
)
def scrape_produtos_mercado(
    driver: webdriver.Chrome,
    nome_mercado: str,
    url_mercado: str,
    item_pesquisa: str,
    max_produtos: int = 10,
    imagens_pasta: str = "imagens_ifood",
    config: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """Faz scraping dos produtos de um mercado específico pesquisando por um item."""
    if config is None:
        config = carregar_config()
    produtos: List[Dict[str, Any]] = []
    try:
        logger.info(f"Acessando o mercado: {url_mercado}")
        driver.get(url_mercado)
        
        termos = item_pesquisa.split()
        termo_principal = " ".join([t for t in termos if not t.isdigit()])
        filtro_num = next((t for t in termos if t.isdigit()), None)
        
        logger.info(f"Pesquisando por '{termo_principal}' em {nome_mercado} (filtro numérico: {filtro_num})")
        campo_pesquisa = WebDriverWait(driver, 10, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.CLASS_NAME, config["selectors"]["products"]["search_field"]))
        )
        campo_pesquisa.clear()
        campo_pesquisa.send_keys(termo_principal)
        WebDriverWait(driver, 2, poll_frequency=0.1).until(
            EC.element_to_be_clickable((By.CLASS_NAME, config["selectors"]["products"]["search_field"]))
        )
        campo_pesquisa.send_keys(Keys.ENTER)
        
        logger.info("Aguardando primeiros resultados da pesquisa...")
        wait = WebDriverWait(driver, 10)
        try:
            total_records_info = wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, config["selectors"]["products"]["total_records"]))
            )
            if total_records_info:
                total_records_message = driver.find_element(By.CLASS_NAME, config["selectors"]["products"]["total_records"])
                records_message = total_records_message.text
                if ' 0 ' in records_message or records_message.startswith('0 ') or records_message.endswith(' 0'):
                    logger.info(f"Nenhum resultado encontrado para '{termo_principal}' em {nome_mercado}")
                    return produtos                
                                    
        except TimeoutException:
            pass
        
        wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, config["selectors"]["products"]["card"]))
        )
        
        items = rolar_pagina(driver, max_produtos, config["selectors"]["products"]["card"])
        
        logger.info(f"Total de produtos encontrados para '{termo_principal}': {len(items)}")
        
        imagens_para_baixar = []
        for i, item in enumerate(items, 1):
            try:
                produto_data: Dict[str, Any] = {"id": i}
                
                try:
                    nome_produto = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['products']['name']}").text
                    produto_data["nome"] = nome_produto
                except NoSuchElementException:
                    nome_produto = "Nome não encontrado"
                    produto_data["nome"] = nome_produto
                
                try:
                    produto_data["preco"] = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['products']['price']}").text
                except NoSuchElementException:
                    produto_data["preco"] = "Não disponível"
                
                try:
                    produto_data["detalhes"] = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['products']['details']}").text
                except NoSuchElementException:
                    produto_data["detalhes"] = "Não disponível"
                
                if filtro_num:
                    padroes = [filtro_num, f"{filtro_num}ml", f"{filtro_num}g", f"{filtro_num} gramas", f"{filtro_num} gr"]
                    if not any(re.search(r'\b' + re.escape(p) + r'\b', nome_produto.lower()) for p in padroes):
                        continue
                
                if len(produtos) < max_produtos:
                    try:
                        imagem_url = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['products']['image']}").get_attribute("src")
                        produto_data["imagem_url"] = imagem_url
                        imagens_para_baixar.append({"url": imagem_url, "nome": f"produto_{nome_mercado}_{nome_produto}", "caminho": None})
                    except NoSuchElementException:
                        produto_data["imagem_url"] = None
                        logger.warning(f"Imagem não encontrada para o produto {produto_data['nome']} em {nome_mercado}")
                    
                    produtos.append(produto_data)
                    logger.info(f"Produto {len(produtos)} processado: {produto_data['nome']}")
                
            except Exception as e:
                logger.error(f"Erro ao processar produto {i}: {e}")
                continue
        
        if imagens_para_baixar:
            baixar_imagens_em_paralelo(imagens_para_baixar, imagens_pasta)
            for produto, img_data in zip(produtos, imagens_para_baixar):
                produto["imagem_local"] = img_data["caminho"]
        
        logger.info(f"Total de produtos filtrados: {len(produtos)}")
        return produtos
    
    except TimeoutException as e:
        logger.error(f"Timeout ao carregar produtos do mercado {url_mercado}: {e}")
        raise
    except WebDriverException as e:
        logger.error(f"Erro de WebDriver ao raspar produtos do mercado {url_mercado}: {e}")
        raise

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TimeoutException, NoSuchElementException, WebDriverException)),
    before_sleep=lambda retry_state: logger.info(f"Tentativa {retry_state.attempt_number} falhou, retrying...")
)
def scrape_ifood_mercados(
    type_search: str,
    max_items: int = 10,
    max_produtos: int = 10,
    itens_pesquisa: List[Dict[str, Any]] = [{"item": "Coca-Cola", "quantidade": 1}],
    output_file: str = "./dados_ifood/ifood_data.json",
    imagens_pasta: str = "imagens_ifood",
    config: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None
) -> None:
    """Faz scraping de mercados e seus produtos no iFood pesquisando por múltiplos itens com quantidades."""
    if config is None:
        config = carregar_config()
    driver: Optional[webdriver.Chrome] = None
    dados: List[Dict[str, Any]] = []
    
    try:
        logger.info("Limpando diretório de imagens antes de nova busca...")
        limpar_diretorio_imagens(imagens_pasta)
        with progresso_lock:
            if task_id:
                progresso_por_task[task_id] = {"percentual": 5, "mensagem": "Configurando ambiente..."}

        logger.info("Configurando o driver...")
        driver = configurar_driver(headless=True)
        
        if not validar_seletores(type_search, driver, config):
            raise Exception("Validação de seletores falhou. Abortando execução.")
        
        definir_localizacao_automatica(type_search, driver, config)
        items = rolar_pagina(driver, max_items, config["selectors"]["markets"]["card"])
        
        logger.info(f"Total de mercados encontrados: {len(items)}")
        with progresso_lock:
            if task_id:
                progresso_por_task[task_id] = {"percentual": 10, "mensagem": f"Carregados {len(items)} mercados..."}

        if not items:
            logger.warning("Nenhum mercado encontrado.")
            return
        
        mercados_info = []
        imagens_mercados = []
        total_mercados = min(len(items), max_items)
        total_itens = len(itens_pesquisa)
        
        # Dividir o progresso: 10% a 50% para mercados, 50% a 90% para produtos, 90% a 100% para finalização
        progresso_base = 10
        progresso_por_mercado = 40.0 / total_mercados  # 10% a 50%
        progresso_por_produto = 40.0 / (total_mercados * total_itens)  # 50% a 90%

        for i, item in enumerate(items[:max_items], 1):
            try:
                mercado_data: Dict[str, Any] = {"id": i}
                
                mercado_data["nome"] = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['markets']['name']}").text or "Nome não encontrado"
                mercado_data["rating"] = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['markets']['rating']}").text or "Não disponível"
                
                info = item.find_element(By.CLASS_NAME, config["selectors"]["markets"]["info"]).text
                if "km" in info:
                    for part in info.split(" • "):
                        if "km" in part:
                            mercado_data["distancia"] = part.strip()
                else:
                    mercado_data["distancia"] = "Não disponível"
                
                footer = item.find_element(By.CLASS_NAME, config["selectors"]["markets"]["footer"]).text
                parts = [p.strip() for p in footer.split("\n") if p.strip() and p.strip() != "•"]
                mercado_data["tempo_entrega"] = parts[0] if parts else "Não disponível"
                mercado_data["custo_entrega"] = parts[-1] if len(parts) > 1 else "Não disponível"
                
                imagem_url = item.find_element(By.CSS_SELECTOR, f".{config['selectors']['markets']['image']}").get_attribute("src")
                mercado_data["imagem_url"] = imagem_url
                imagens_mercados.append({"url": imagem_url, "nome": mercado_data["nome"], "caminho": None})
                
                href = item.get_attribute("href")
                mercado_data["url"] = f"https://www.ifood.com.br{href}" if href and href.startswith("/") else href
                
                mercados_info.append(mercado_data)
                logger.info(f"Informações coletadas do mercado {i}: {mercado_data['nome']}")
                
                # Atualizar progresso após processar cada mercado
                with progresso_lock:
                    if task_id:
                        progresso_base += progresso_por_mercado
                        progresso_por_task[task_id] = {"percentual": min(progresso_base, 50), "mensagem": f"Processando mercado {i} de {total_mercados}..."}

            except NoSuchElementException as e:
                logger.warning(f"Elemento não encontrado para mercado {i}: {e}")
                continue
            except Exception as e:
                logger.error(f"Erro ao coletar informações do mercado {i}: {e}")
                continue
        
        if imagens_mercados:
            baixar_imagens_em_paralelo(imagens_mercados, imagens_pasta)
            for mercado_data, img_data in zip(mercados_info, imagens_mercados):
                mercado_data["imagem_local"] = img_data["caminho"]
        
        for j, mercado_data in enumerate(mercados_info, 1):
            try:
                mercado_data["produtos"] = {}
                if mercado_data.get("url"):
                    for k, item_data in enumerate(itens_pesquisa, 1):
                        item = item_data["item"]
                        logger.info(f"Pesquisando '{item}' no mercado {mercado_data['nome']}...")
                        produtos = scrape_produtos_mercado(
                            driver, mercado_data["nome"], mercado_data["url"], item, max_produtos, imagens_pasta, config
                        )
                        mercado_data["produtos"][item] = produtos
                        time.sleep(random.uniform(0.5, 1.5))
                        
                        # Atualizar progresso após processar cada item
                        with progresso_lock:
                            if task_id:
                                progresso_base += progresso_por_produto
                                progresso_por_task[task_id] = {"percentual": min(progresso_base, 90), "mensagem": f"Processando item {k} de {total_itens} no mercado {j} de {total_mercados}..."}

                else:
                    mercado_data["produtos"] = {item_data["item"]: [] for item_data in itens_pesquisa}
                    logger.warning(f"Sem URL para raspar produtos do mercado {mercado_data['nome']}")
                
                dados.append(mercado_data)
                logger.info(f"Mercado processado com produtos: {mercado_data['nome']}")
                
            except Exception as e:
                logger.error(f"Erro ao processar produtos do mercado {mercado_data['nome']}: {e}")
                continue
        
        # Finalização
        with progresso_lock:
            if task_id:
                progresso_por_task[task_id] = {"percentual": 95, "mensagem": "Calculando melhor compra..."}

        resultado = calcular_melhor_compra(dados, itens_pesquisa, max_items)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=4)
        logger.info(f"Dados finais salvos em: {output_file}")
        
        with progresso_lock:
            if task_id:
                progresso_por_task[task_id] = {"percentual": 100, "mensagem": "Scraping concluído!"}
        
    except Exception as e:
        logger.error(f"Erro geral: {e}")
        import traceback
        traceback.print_exc()
        with progresso_lock:
            if task_id:
                progresso_por_task[task_id] = {"percentual": 0, "mensagem": f"Erro: {str(e)}"}
        raise
    
    finally:
        if driver is not None:
            driver.quit()
            logger.info("Navegador fechado.")

def calcular_melhor_compra(dados: List[Dict[str, Any]], itens_pesquisa: List[Dict[str, Any]], max_items: int) -> Dict[str, Any]:
    """Calcula onde é mais barato comprar os itens e retorna resultados estruturados."""
    logger.info("Calculando a melhor opção de compra...")

    custos_por_mercado = {}
    itens_faltantes_por_mercado = {}
    combinacoes_por_mercado = {}

    def converter_preco(preco: str) -> float:
        try:
            match = re.search(r'R?\$\s*(\d+[.,]\d+)', preco)
            if match:
                return float(match.group(1).replace(",", "."))
            return float("inf")
        except (ValueError, AttributeError):
            logger.warning(f"Preço inválido encontrado: {preco}")
            return float("inf")
    
    def converter_custo_entrega(custo: str) -> float:
        if custo.lower() == "grátis" or "grátis" in custo.lower():
            return 0.0
        return converter_preco(custo)

    for mercado in dados:
        nome_mercado = mercado["nome"]
        custo_entrega = converter_custo_entrega(mercado.get("custo_entrega", "Não disponível"))
        produtos = mercado.get("produtos", {})
        
        custo_total_produtos = 0.0
        itens_faltantes = []
        produtos_escolhidos = []
        combinacoes = []

        for item_data in itens_pesquisa:
            item = item_data["item"]
            quantidade = item_data["quantidade"]
            produtos_item = produtos.get(item, [])
            
            if not produtos_item:
                itens_faltantes.append(f"{item} ({quantidade}x)")
                continue
            
            precos_validos = [
                {"produto": p, "preco": converter_preco(p["preco"])}
                for p in produtos_item
                if p.get("preco") and converter_preco(p["preco"]) != float("inf")
            ]
            
            if not precos_validos:
                itens_faltantes.append(f"{item} ({quantidade}x)")
                continue
            
            # Ordenar por preço para garantir o mais barato como escolhido
            precos_validos.sort(key=lambda x: x["preco"])
            preco_mais_barato = precos_validos[0]["preco"]
            produto_mais_barato = precos_validos[0]["produto"]
            custo_item = preco_mais_barato * quantidade
            custo_total_produtos += custo_item
            produtos_escolhidos.append({
                "item": item,
                "quantidade": quantidade,
                "produto": produto_mais_barato,
                "custo": custo_item
            })

            # Adicionar até 2 alternativas (excluindo o mais barato)
            for i, alt in enumerate(precos_validos[1:], 1):  # Começa do segundo item
                if i > max_items:  # Limita a 2 alternativas
                    break
                custo_alt = alt["preco"] * quantidade
                combinacoes.append({
                    "item": item,
                    "quantidade": quantidade,
                    "produto": alt["produto"],
                    "custo": custo_alt,
                    "diferenca": custo_alt - custo_item
                })

        custo_total = custo_total_produtos + custo_entrega if produtos_escolhidos else float("inf")
        custos_por_mercado[nome_mercado] = custo_total
        itens_faltantes_por_mercado[nome_mercado] = itens_faltantes
        combinacoes_por_mercado[nome_mercado] = combinacoes

        mercado["custo_total"] = f"R$ {custo_total:.2f}" if custo_total != float("inf") else "N/A"
        mercado["produtos_escolhidos"] = produtos_escolhidos
        mercado["combinacoes"] = combinacoes

    mercados_ordenados = sorted(
        custos_por_mercado.items(),
        key=lambda x: x[1] if x[1] != float("inf") else float("inf")
    )
    
    resultado = {
        "melhor_compra": {
            "mercado": mercados_ordenados[0][0],
            "custo_total": f"R$ {mercados_ordenados[0][1]:.2f}" if mercados_ordenados[0][1] != float("inf") else "N/A",
            "produtos_escolhidos": next(m["produtos_escolhidos"] for m in dados if m["nome"] == mercados_ordenados[0][0])
        },
        "mercados": dados
    }

    logger.info(f"Mercado mais barato: {resultado['melhor_compra']['mercado']} - R$ {resultado['melhor_compra']['custo_total']}")
    return resultado

def main() -> None:
    parser = argparse.ArgumentParser(description="Scraping de mercados e produtos no iFood com pesquisa por múltiplos itens e quantidades.")
    parser.add_argument("--type-search", type=str, default='M', help="Tipo de Estabelecimento")
    parser.add_argument("--max-items", type=int, default=10, help="Número máximo de mercados a processar")
    parser.add_argument("--max-produtos", type=int, default=10, help="Número máximo de produtos por mercado por item")
    parser.add_argument("--item", type=str, default="Coca-Cola:1", help="Itens e quantidades a pesquisar, no formato 'item:quantidade' separados por vírgula (ex.: 'coca:1, queijo:3')")
    parser.add_argument("--output", default=f"./dados_ifood/ifood_data.json", help="Arquivo base de saída JSON")
    parser.add_argument("--imagens-pasta", type=str, default="imagens_ifood", help="Pasta para salvar as imagens")
    parser.add_argument("--config", type=str, default="./config.yaml", help="Caminho do arquivo de configuração")
    
    args = parser.parse_args()
    config = carregar_config(args.config)
    
    itens_pesquisa = []
    for item_str in args.item.split(","):
        try:
            item, quantidade = item_str.strip().split(":")
            itens_pesquisa.append({"item": item.strip(), "quantidade": int(quantidade.strip())})
        except ValueError:
            logger.error(f"Formato inválido para item: '{item_str}'. Use 'item:quantidade' (ex.: 'coca:1').")
            raise
    
    scrape_ifood_mercados(args.type_search, args.max_items, args.max_produtos, itens_pesquisa, args.output, args.imagens_pasta, config)

if __name__ == "__main__":
    main()
