"""Proteção CSRF (Flask-WTF): POST sem token válido tem que ser recusado, mesmo
com sessão autenticada — senão uma página maliciosa aberta no mesmo navegador
consegue disparar ações destrutivas usando só o cookie de sessão."""

import os
import re

import main


def extrair_token_form(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "não achou campo csrf_token no HTML — o template perdeu o token?"
    return m.group(1)


def extrair_token_meta(html):
    m = re.search(r'name="csrf-token" content="([^"]+)"', html)
    assert m, "não achou a meta tag csrf-token no HTML"
    return m.group(1)


def logar(cliente, senha):
    """Login de verdade (com token), pra testar rotas protegidas por sessão."""
    token = extrair_token_form(cliente.get('/login').get_data(as_text=True))
    cliente.post('/login', data={'senha': senha, 'csrf_token': token})


def test_setup_sem_token_e_recusado(cliente, sem_senha):
    resposta = cliente.post('/setup', data={'senha': 'nova-senha', 'confirmacao': 'nova-senha'})

    assert resposta.status_code == 400
    assert not main.senha_esta_configurada()


def test_setup_com_token_valido_funciona(cliente, sem_senha):
    token = extrair_token_form(cliente.get('/setup').get_data(as_text=True))

    resposta = cliente.post(
        '/setup',
        data={'senha': 'nova-senha', 'confirmacao': 'nova-senha', 'csrf_token': token},
        follow_redirects=True,
    )

    assert resposta.status_code == 200
    assert main.senha_esta_configurada()


def test_login_sem_token_e_recusado(cliente, com_senha):
    resposta = cliente.post('/login', data={'senha': com_senha})

    assert resposta.status_code == 400


def test_login_com_token_funciona(cliente, com_senha):
    token = extrair_token_form(cliente.get('/login').get_data(as_text=True))

    resposta = cliente.post('/login', data={'senha': com_senha, 'csrf_token': token}, follow_redirects=True)

    assert resposta.status_code == 200


def test_rota_protegida_sem_token_e_recusada_mesmo_logado(cliente, com_senha):
    logar(cliente, com_senha)

    resposta = cliente.post('/criar_pasta/', data={'nome_pasta': 'forjada-sem-token'})

    assert resposta.status_code == 400


def test_rota_protegida_com_token_funciona_logado(cliente, com_senha):
    logar(cliente, com_senha)
    token = extrair_token_meta(cliente.get('/galeria/').get_data(as_text=True))

    resposta = cliente.post(
        '/criar_pasta/',
        data={'nome_pasta': 'com-token', 'csrf_token': token},
    )

    # 302: redirect(request.referrer), sem valor em teste porque não há Referer.
    # O que importa aqui é que o CSRF deixou passar — a pasta foi criada de verdade.
    assert resposta.status_code == 302
    assert os.path.isdir(os.path.join(main.MEDIA_FOLDER, 'com-token'))


def test_token_no_cabecalho_x_csrftoken_tambem_funciona(cliente, com_senha):
    """Confirma o caminho usado pelas chamadas via fetch()/XHR no JS da galeria
    (mandam o token no cabeçalho, não num campo de formulário)."""
    logar(cliente, com_senha)
    token = extrair_token_meta(cliente.get('/galeria/').get_data(as_text=True))

    resposta = cliente.post('/criar_pasta/', data={'nome_pasta': 'via-header'}, headers={'X-CSRFToken': token})

    assert resposta.status_code == 302
    assert os.path.isdir(os.path.join(main.MEDIA_FOLDER, 'via-header'))


def test_get_nao_precisa_de_token(cliente, com_senha):
    """GET nunca é protegido por CSRF — só POST/PUT/PATCH/DELETE."""
    logar(cliente, com_senha)

    resposta = cliente.get('/galeria/')

    assert resposta.status_code == 200
