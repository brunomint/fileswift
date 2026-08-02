"""Portaria do app: quem entra sem sessão, o que fica de fora da portaria de
propósito, e para onde o login manda o usuário depois."""

import main


def test_api_stats_responde_sem_sessao(cliente):
    """Regressão do c29c0ce: a janela tkinter consulta essa rota localmente sem
    sessão. Quando ela caiu na portaria, a GUI passou a mostrar tudo zerado."""
    resposta = cliente.get("/api/stats")

    assert resposta.status_code == 200
    assert "tempo_ativo" in resposta.get_json()


def test_static_nao_esta_isento():
    """MEDIA_FOLDER mora dentro de static/, então isentar o endpoint static
    exporia os arquivos do usuário sem senha. Tem que ficar de fora da lista."""
    assert "static" not in main.ENDPOINTS_ISENTOS
    assert "api_stats" in main.ENDPOINTS_ISENTOS


def test_arquivo_em_static_nao_sai_sem_senha(cliente, com_senha):
    """O app é criado com static_folder=None para a rota automática do Flask não
    existir. ela serviria MEDIA_FOLDER, que mora dentro de static/. O que
    importa aqui é que o arquivo não saia: 404 se a rota não existe, redirect
    para o login se existe e é protegida. O que não pode é 200."""
    assert cliente.get("/static/download/qualquer.jpg").status_code != 200


def test_sem_senha_configurada_manda_para_setup(cliente, sem_senha):
    resposta = cliente.get("/configuracoes")

    assert resposta.status_code == 302
    assert "/setup" in resposta.headers["Location"]


def test_com_senha_e_sem_login_manda_para_login(cliente, com_senha):
    resposta = cliente.get("/configuracoes")

    assert resposta.status_code == 302
    assert "/login" in resposta.headers["Location"]


def test_senha_certa_autentica_e_errada_nao(com_senha):
    assert main.verificar_senha(com_senha) is True
    assert main.verificar_senha("outra-coisa") is False


class TestDestinoPosLogin:
    """Proteção contra open redirect: o ?next= só pode levar para dentro do app."""

    def test_caminho_interno_e_mantido(self):
        with main.app.test_request_context():
            assert main._destino_pos_login("/pasta/fotos") == "/pasta/fotos"

    def test_url_externa_e_descartada(self):
        with main.app.test_request_context():
            destino = main._destino_pos_login("http://site-malicioso.com")
            assert destino == main.url_for("index")

    def test_barra_dupla_e_descartada(self):
        # "//site.com" é URL protocol-relative: o navegador trataria como
        # externa, mesmo começando com barra.
        with main.app.test_request_context():
            assert main._destino_pos_login("//site-malicioso.com") == main.url_for(
                "index"
            )

    def test_vazio_cai_no_inicio(self):
        with main.app.test_request_context():
            assert main._destino_pos_login("") == main.url_for("index")
            assert main._destino_pos_login(None) == main.url_for("index")


class TestBloqueioDeTentativas:
    """Rate limit do login, em memória."""

    def test_ip_novo_nao_esta_bloqueado(self):
        assert main.ip_esta_bloqueado("10.0.0.1") is False

    def test_bloqueia_no_limite_de_tentativas(self):
        for _ in range(main.LOGIN_MAX_TENTATIVAS):
            main.registrar_tentativa_falha("10.0.0.2")

        assert main.ip_esta_bloqueado("10.0.0.2") is True

    def test_uma_tentativa_antes_do_limite_ainda_passa(self):
        for _ in range(main.LOGIN_MAX_TENTATIVAS - 1):
            main.registrar_tentativa_falha("10.0.0.3")

        assert main.ip_esta_bloqueado("10.0.0.3") is False

    def test_login_certo_limpa_o_contador(self):
        for _ in range(main.LOGIN_MAX_TENTATIVAS):
            main.registrar_tentativa_falha("10.0.0.4")
        main.limpar_tentativas("10.0.0.4")

        assert main.ip_esta_bloqueado("10.0.0.4") is False

    def test_bloqueio_e_por_ip(self):
        for _ in range(main.LOGIN_MAX_TENTATIVAS):
            main.registrar_tentativa_falha("10.0.0.5")

        assert main.ip_esta_bloqueado("10.0.0.6") is False
