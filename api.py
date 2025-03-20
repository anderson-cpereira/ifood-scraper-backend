from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from ifood_scraper import scrape_ifood_mercados
from progresso import progresso_lock, progresso_por_task
import asyncio
import os
import json
import logging
import uuid

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="iFood Scraping API")

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Diretórios base
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "dados_ifood")
IMAGENS_DIR = os.path.join(BASE_DIR, "imagens_ifood")
OUTPUT_FILE = os.path.join(DATA_DIR, "ifood_data.json")

# Criar os diretórios se não existirem
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not os.path.exists(IMAGENS_DIR):
    os.makedirs(IMAGENS_DIR)

# Montar o diretório de imagens estáticas
app.mount("/imagens_ifood", StaticFiles(directory=IMAGENS_DIR), name="imagens_ifood")
# Modelos para os itens de entrada
class ProdutoItem(BaseModel):
    produto: str
    quantidade: int

# Modelos para a resposta
class ProdutoDetalhe(BaseModel):
    id: int
    nome: str
    preco: str
    detalhes: str
    imagem_url: Optional[str] = None
    imagem_local: Optional[str] = None

class ProdutoEscolhido(BaseModel):
    item: str
    quantidade: int
    produto: ProdutoDetalhe
    custo: float

class Combinacao(BaseModel):
    item: str
    quantidade: int
    produto: ProdutoDetalhe
    custo: float
    diferenca: float

class Mercado(BaseModel):
    id: int
    nome: str
    rating: str
    distancia: str
    tempo_entrega: str
    custo_entrega: str
    imagem_url: Optional[str] = None
    url: str
    imagem_local: Optional[str] = None
    produtos: dict[str, List[ProdutoDetalhe]]
    custo_total: str
    produtos_escolhidos: List[ProdutoEscolhido]
    combinacoes: List[Combinacao]

class MelhorCompra(BaseModel):
    mercado: str
    custo_total: str
    produtos_escolhidos: List[ProdutoEscolhido]

class ScrapingResponse(BaseModel):
    status: str
    melhor_compra: MelhorCompra
    mercados: List[Mercado]
    output_file: str
    task_id: str

@app.post("/scrape/", response_model=ScrapingResponse)
async def scrape_ifood(type_search: str,produtos: List[ProdutoItem], max_produtos: int = 10, task_id: Optional[str] = None):
    logger.info(f"Iniciando scrape_ifood com produtos no(a): {[p.dict() for p in produtos]}, max_produtos: {max_produtos}, task_id: {task_id}")
    if not task_id:
        task_id = str(uuid.uuid4())
    try:
        # Validar os itens da lista
        for item in produtos:
            if not item.produto or item.produto.strip() == "":
                raise ValueError("O campo 'produto' é obrigatório e não pode ser vazio.")
            if item.quantidade < 1:
                raise ValueError("A quantidade deve ser um número inteiro positivo.")

        # Converter os itens para o formato esperado por scrape_ifood_mercados
        itens_pesquisa = [{"item": p.produto, "quantidade": p.quantidade} for p in produtos]

        # Criar o diretório de saída se não existir
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            logger.info(f"Criado diretório {DATA_DIR}")

        # Inicializar progresso para este task_id
        with progresso_lock:
            progresso_por_task[task_id] = {"percentual": 0, "mensagem": "Iniciando scraping..."}
            
        # Executar o scraping diretamente no mesmo processo, mas em um thread separado
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: scrape_ifood_mercados(type_search, 100, max_produtos, itens_pesquisa, OUTPUT_FILE, IMAGENS_DIR, None, task_id)
        )

        # Verificar se o arquivo JSON foi gerado
        if not os.path.exists(OUTPUT_FILE):
            raise FileNotFoundError(f"O arquivo de saída {OUTPUT_FILE} não foi gerado.")

        # Carregar os dados do arquivo
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        logger.info(f"Scraping concluído, resultado lido de {OUTPUT_FILE}")
        response = {
            "status": "success",
            "melhor_compra": data["melhor_compra"],
            "mercados": data["mercados"],
            "output_file": OUTPUT_FILE,
            "task_id": task_id
        }
        return response

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except FileNotFoundError as fnfe:
        raise HTTPException(status_code=404, detail=str(fnfe))
    except Exception as e:
        logger.error(f"Erro geral ao executar scraper: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao executar scraper: {str(e)}")

@app.get("/progresso/{task_id}", response_class=EventSourceResponse, response_model=None)
async def progresso_endpoint(task_id: str):
    """Endpoint SSE para enviar atualizações de progresso em tempo real para um task_id específico."""
    async def evento_progresso():
        try:
            while True:
                with progresso_lock:
                    progresso = progresso_por_task.get(task_id, {"percentual": 0, "mensagem": "Aguardando..."})
                    yield {
                        "event": "progresso",
                        "data": json.dumps(progresso)
                    }
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    return EventSourceResponse(evento_progresso())