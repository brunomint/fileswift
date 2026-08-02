"""formatar_tempo_ativo: função pura extraída de obter_estatisticas_servidor,
pedida pelo Romulo no PR #3 (a formatação vivia dentro da rota)."""

from datetime import datetime, timedelta

import main


def test_sem_data_de_inicio_devolve_zerado():
    assert main.formatar_tempo_ativo(None) == "00:00:00"


def test_calcula_horas_minutos_segundos():
    agora = datetime(2026, 1, 1, 15, 0, 0)
    desde = agora - timedelta(hours=2, minutes=34, seconds=56)

    assert main.formatar_tempo_ativo(desde, agora) == "02:34:56"


def test_menos_de_um_minuto():
    agora = datetime(2026, 1, 1, 12, 0, 30)
    desde = datetime(2026, 1, 1, 12, 0, 5)

    assert main.formatar_tempo_ativo(desde, agora) == "00:00:25"


def test_usa_agora_real_quando_nao_informado():
    desde = datetime.now() - timedelta(seconds=5)

    resultado = main.formatar_tempo_ativo(desde)

    assert resultado.startswith("00:00:0")
