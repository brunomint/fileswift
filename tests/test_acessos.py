"""acessos_diarios: contagem de acessos do dia precisa sobreviver a um reinício
do servidor no meio do dia — antes ficava só em memória (main.acessos_por_dia)
e zerava a cada boot."""

import main


def test_dia_sem_acesso_ainda_devolve_zero():
    assert main.obter_acessos_do_dia('2026-01-01') == 0


def test_um_acesso_incrementa_a_contagem():
    main.registrar_acesso_do_dia('2026-01-02')

    assert main.obter_acessos_do_dia('2026-01-02') == 1


def test_varios_acessos_no_mesmo_dia_acumulam():
    for _ in range(5):
        main.registrar_acesso_do_dia('2026-01-03')

    assert main.obter_acessos_do_dia('2026-01-03') == 5


def test_dias_diferentes_nao_se_misturam():
    main.registrar_acesso_do_dia('2026-01-04')
    main.registrar_acesso_do_dia('2026-01-04')
    main.registrar_acesso_do_dia('2026-01-05')

    assert main.obter_acessos_do_dia('2026-01-04') == 2
    assert main.obter_acessos_do_dia('2026-01-05') == 1


def test_contagem_sobrevive_a_reabertura_da_conexao_com_banco():
    """Simula o que acontece de verdade num restart: cada chamada abre e fecha
    sua própria conexão (get_db_connection), então não há cache em memória
    escondendo uma falha de persistência real."""
    main.registrar_acesso_do_dia('2026-01-06')
    main.registrar_acesso_do_dia('2026-01-06')

    conn = main.get_db_connection()
    linha = conn.execute(
        'SELECT contagem FROM acessos_diarios WHERE data = ?', ('2026-01-06',)
    ).fetchone()
    conn.close()

    assert linha['contagem'] == 2


def test_registrar_acesso_incrementa_o_dia_de_hoje():
    """registrar_acesso() (chamada em todo before_request) também deve persistir,
    não só a função de baixo nível registrar_acesso_do_dia()."""
    from datetime import datetime

    hoje = datetime.now().strftime('%Y-%m-%d')
    antes = main.obter_acessos_do_dia(hoje)

    main.registrar_acesso('10.0.0.99')

    assert main.obter_acessos_do_dia(hoje) == antes + 1


def test_obter_estatisticas_reflete_acessos_persistidos():
    from datetime import datetime

    hoje = datetime.now().strftime('%Y-%m-%d')
    main.registrar_acesso_do_dia(hoje)
    esperado = main.obter_acessos_do_dia(hoje)

    stats = main.obter_estatisticas_servidor()

    assert stats['acessos_hoje'] == esperado


class TestNaoContarOProprioServidorComoDispositivo:
    """A janela tkinter consulta /api/stats via 127.0.0.1, e a aba que abre
    sozinha no navegador usa o IP da própria máquina — nenhum dos dois é um
    dispositivo de verdade."""

    def test_localhost_nao_conta_como_dispositivo(self):
        main.dispositivos_conectados.discard('127.0.0.1')

        main.registrar_acesso('127.0.0.1')

        assert '127.0.0.1' not in main.dispositivos_conectados

    def test_ip_do_proprio_servidor_nao_conta_como_dispositivo(self, monkeypatch):
        monkeypatch.setattr(main, 'ip_atual', '192.168.0.50')
        main.dispositivos_conectados.discard('192.168.0.50')

        main.registrar_acesso('192.168.0.50')

        assert '192.168.0.50' not in main.dispositivos_conectados

    def test_ip_diferente_continua_contando_normalmente(self, monkeypatch):
        monkeypatch.setattr(main, 'ip_atual', '192.168.0.50')
        main.dispositivos_conectados.discard('192.168.0.77')

        main.registrar_acesso('192.168.0.77')

        assert '192.168.0.77' in main.dispositivos_conectados
        main.dispositivos_conectados.discard('192.168.0.77')

    def test_sem_ip_atual_definido_nao_quebra(self, monkeypatch):
        monkeypatch.setattr(main, 'ip_atual', None)
        main.dispositivos_conectados.discard('192.168.0.88')

        main.registrar_acesso('192.168.0.88')

        assert '192.168.0.88' in main.dispositivos_conectados
        main.dispositivos_conectados.discard('192.168.0.88')


class TestPollingNaoContaComoAcesso:
    """/api/stats e as demais rotas de auto-atualização não devem inflar
    'acessos hoje' — só ações reais de página."""

    def test_registrar_acesso_com_contar_como_acesso_false_nao_incrementa(self):
        from datetime import datetime

        hoje = datetime.now().strftime('%Y-%m-%d')
        antes = main.obter_acessos_do_dia(hoje)

        main.registrar_acesso('10.0.0.100', contar_como_acesso=False)

        assert main.obter_acessos_do_dia(hoje) == antes

    def test_endpoints_de_polling_estao_marcados(self):
        esperado = {
            'api_stats', 'api_galeria_assinatura', 'api_textos_contagem',
            'api_textos_lista', 'api_textos_anexos', 'api_textos_versao',
        }
        assert esperado <= main.ENDPOINTS_POLLING

    def test_requisicao_a_api_stats_nao_incrementa_acessos_hoje(self, cliente):
        from datetime import datetime

        hoje = datetime.now().strftime('%Y-%m-%d')
        antes = main.obter_acessos_do_dia(hoje)

        cliente.get('/api/stats')
        cliente.get('/api/stats')

        assert main.obter_acessos_do_dia(hoje) == antes

    def test_requisicao_a_pagina_real_incrementa_acessos_hoje(self, cliente, com_senha):
        from datetime import datetime

        token = None
        import re
        html = cliente.get('/login').get_data(as_text=True)
        m = re.search(r'name="csrf_token" value="([^"]+)"', html)
        token = m.group(1)
        cliente.post('/login', data={'senha': com_senha, 'csrf_token': token})

        hoje = datetime.now().strftime('%Y-%m-%d')
        antes = main.obter_acessos_do_dia(hoje)

        cliente.get('/galeria/')

        assert main.obter_acessos_do_dia(hoje) == antes + 1
