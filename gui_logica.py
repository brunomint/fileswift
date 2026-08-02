"""Lógica da janela tkinter que não depende de nenhum widget: checagem de porta,
leitura de /api/stats e encerramento do processo do servidor. Extraído de
gui_launcher.py (crítica do RomuloPBenedetti no PR #3: essa lógica estava presa
aos widgets, impossível de testar sem construir a janela inteira). Sem
`import tkinter` de propósito, pra dar pra testar com pytest puro.
"""

import os
import signal
import socket
import subprocess
import time

import requests


def porta_em_uso(porta, host='localhost', timeout=1.0):
    """True se algo já está escutando em host:porta."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, porta)) == 0
    finally:
        sock.close()


def buscar_estatisticas(porta, timeout=2.0):
    """GET /api/stats local; None em qualquer falha (offline, timeout, não-200)."""
    try:
        resposta = requests.get(f"http://localhost:{porta}/api/stats", timeout=timeout)
        return resposta.json() if resposta.status_code == 200 else None
    except requests.RequestException:
        return None


def encerrar_servidor_processo(porta, flask_server=None):
    """Shutdown por HTTP, depois flask_server.shutdown(), depois lsof+SIGTERM
    como último recurso."""
    try:
        requests.get(f"http://localhost:{porta}/shutdown", timeout=2)
    except requests.RequestException:
        pass

    if flask_server:
        try:
            flask_server.shutdown()
        except Exception:
            pass

    try:
        resultado = subprocess.run(['lsof', '-ti', f':{porta}'], capture_output=True, text=True)
        for pid in resultado.stdout.strip().split('\n'):
            if pid:
                try:
                    os.kill(int(pid), signal.SIGTERM)
                except Exception:
                    pass
    except Exception:
        pass

    time.sleep(1)
