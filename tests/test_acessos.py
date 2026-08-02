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
