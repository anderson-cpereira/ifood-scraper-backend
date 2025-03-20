# progresso.py
import threading

progresso_atual = {"percentual": 0, "mensagem": "Iniciando..."}
progresso_lock = threading.Lock()  # Lock para sincronização entre threads
progresso_por_task = {}