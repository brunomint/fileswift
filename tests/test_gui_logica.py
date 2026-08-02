"""gui_logica: lógica da janela tkinter sem nenhum widget — extraída de
gui_launcher.py (crítica do RomuloPBenedetti no PR #3). Testável com mocks
puros, sem construir nenhuma janela."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import gui_logica


class TestPortaEmUso:
    def test_porta_livre(self):
        sock = MagicMock()
        sock.connect_ex.return_value = 1  # != 0, conexão recusada
        with patch("socket.socket", return_value=sock):
            assert gui_logica.porta_em_uso(5678) is False

    def test_porta_ocupada(self):
        sock = MagicMock()
        sock.connect_ex.return_value = 0
        with patch("socket.socket", return_value=sock):
            assert gui_logica.porta_em_uso(5678) is True

    def test_fecha_o_socket_mesmo_com_excecao(self):
        sock = MagicMock()
        sock.connect_ex.side_effect = OSError("boom")
        with patch("socket.socket", return_value=sock):
            with pytest.raises(OSError):
                gui_logica.porta_em_uso(5678)
        sock.close.assert_called_once()


class TestBuscarEstatisticas:
    def test_200_devolve_o_json(self):
        resposta = MagicMock(status_code=200)
        resposta.json.return_value = {"tempo_ativo": "00:01:00"}
        with patch("requests.get", return_value=resposta):
            assert gui_logica.buscar_estatisticas(5678) == {"tempo_ativo": "00:01:00"}

    def test_status_diferente_de_200_devolve_none(self):
        resposta = MagicMock(status_code=401)
        with patch("requests.get", return_value=resposta):
            assert gui_logica.buscar_estatisticas(5678) is None

    def test_excecao_de_rede_devolve_none(self):
        with patch("requests.get", side_effect=requests.RequestException("offline")):
            assert gui_logica.buscar_estatisticas(5678) is None


class TestEncerrarServidorProcesso:
    def test_caminho_feliz_chama_shutdown_http_e_flask(self):
        flask_server = MagicMock()
        with patch("requests.get") as get, patch("subprocess.run") as run, patch("time.sleep"):
            run.return_value = MagicMock(stdout="")
            gui_logica.encerrar_servidor_processo(5678, flask_server)

        get.assert_called_once_with("http://localhost:5678/shutdown", timeout=2)
        flask_server.shutdown.assert_called_once()

    def test_endpoint_falha_mas_flask_server_shutdown_funciona(self):
        flask_server = MagicMock()
        with patch("requests.get", side_effect=requests.RequestException("offline")), \
             patch("subprocess.run") as run, patch("time.sleep"):
            run.return_value = MagicMock(stdout="")
            gui_logica.encerrar_servidor_processo(5678, flask_server)

        flask_server.shutdown.assert_called_once()

    def test_sem_flask_server_nao_quebra(self):
        with patch("requests.get"), patch("subprocess.run") as run, patch("time.sleep"):
            run.return_value = MagicMock(stdout="")
            gui_logica.encerrar_servidor_processo(5678, flask_server=None)

    def test_lsof_nao_acha_nada(self):
        with patch("requests.get"), patch("subprocess.run") as run, patch("os.kill") as kill, patch("time.sleep"):
            run.return_value = MagicMock(stdout="")
            gui_logica.encerrar_servidor_processo(5678)

        kill.assert_not_called()

    def test_lsof_acha_pid_e_mata(self):
        with patch("requests.get"), patch("subprocess.run") as run, patch("os.kill") as kill, patch("time.sleep"):
            run.return_value = MagicMock(stdout="12345\n")
            gui_logica.encerrar_servidor_processo(5678)

        kill.assert_called_once()
        assert kill.call_args[0][0] == 12345

    def test_lsof_indisponivel_nao_quebra(self):
        with patch("requests.get"), \
             patch("subprocess.run", side_effect=FileNotFoundError("lsof não instalado")), \
             patch("time.sleep"):
            gui_logica.encerrar_servidor_processo(5678)
