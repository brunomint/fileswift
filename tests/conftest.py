"""Preparo comum dos testes.

O app é monolítico, importar o main tem efeito colateral, cria pasta de dados, escreve o
config.json, abre o banco e sobe o Zeroconf, tudo no momento do import. Por isso o
FILESWIFT_DATA_DIR é apontado para uma pasta temporária ANTES do import, Sem isso o teste
mexeria nos dados reais de quem está rodando. A longo prazo é importante desacoplar o
código do app.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["FILESWIFT_DATA_DIR"] = tempfile.mkdtemp(prefix="fileswift-test-")

import pytest

import main


@pytest.fixture(scope="session", autouse=True)
def _fechar_zeroconf():
    """O Zeroconf abre sockets no import e deixa threads vivas. Fecha no fim
    para a suíte não travar esperando por elas."""
    yield
    try:
        main.zeroconf.close()
    except Exception:
        pass


@pytest.fixture
def cliente():
    """Cliente HTTP sem sessão nenhuma, como um visitante novo."""
    main.app.config["TESTING"] = True
    with main.app.test_client() as c:
        yield c


@pytest.fixture
def sem_senha():
    """App no estado de primeira execução, antes de alguém definir senha."""
    anterior = main.CONFIG.pop("senha_hash", None)
    yield
    if anterior is not None:
        main.CONFIG["senha_hash"] = anterior


@pytest.fixture
def com_senha():
    """App já configurado. Devolve a senha em texto para quem quiser logar."""
    anterior = main.CONFIG.get("senha_hash")
    senha = "senha-de-teste"
    main.definir_senha(senha)
    yield senha
    if anterior is None:
        main.CONFIG.pop("senha_hash", None)
    else:
        main.CONFIG["senha_hash"] = anterior


@pytest.fixture(autouse=True)
def _limpar_tentativas_login():
    """As tentativas de login vivem num dicionário de módulo. Zera entre testes
    para um não contaminar o outro."""
    main.tentativas_login_por_ip.clear()
    yield
    main.tentativas_login_por_ip.clear()
