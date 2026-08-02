# Como contribuir

Obrigado pelo interesse em contribuir com o FileSwift! Este arquivo reúne o
que um contribuidor novo precisa pra rodar o projeto, testar uma mudança e
abrir um PR com boa chance de ser aceito rápido.

## Configurando o ambiente

```bash
git clone https://github.com/brunomint/fileswift.git
cd fileswift
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r requirements.dev.txt
python3 main.py --console
```

`requirements.dev.txt` traz só o `pytest`, fixado numa versão que ainda roda
no Python 3.8 — não entra na imagem Docker de produção, só no alvo `test`.

## Rodando os testes

Com Docker, sem instalar nada na máquina:

```bash
docker compose run --rm test
```

Direto na máquina, no virtualenv já configurado:

```bash
pytest
```

Antes de abrir um PR, rode a suíte inteira — o CI roda automaticamente em
todo push/PR (Linux Python 3.8 e 3.11, Windows Python 3.11), e o `main`
está protegido: **PR só mescla se os três checks passarem**.

## Convenções do projeto

- **Comentários em português**, explicando o *porquê*, não o *o quê* — o
  código já mostra o que faz; o comentário existe pra registrar uma decisão
  não óbvia, uma pegadinha, ou o motivo de uma versão estar fixada. Veja
  qualquer comentário em `main.py` ou nos arquivos `requirements*.txt` como
  referência de tom.
- **`FILESWIFT_DATA_DIR` isola dados reais de teste.** Qualquer script/teste
  que importe `main` precisa fazer isso *antes* do import (veja
  `tests/conftest.py`) — sem isso, roda em cima do banco e da pasta de
  arquivos de quem estiver executando.
- **Rotas que recebem caminho de arquivo/pasta do usuário** (upload, mover,
  copiar, apagar) têm que passar por `resolver_caminho_seguro()`
  (`main.py`) — é a proteção contra path traversal, reportada e corrigida
  depois de um review externo. Não faça `os.path.join(MEDIA_FOLDER, ...)`
  direto com entrada do usuário.
- **Toda rota nova que aceita POST/PUT/PATCH/DELETE precisa de token CSRF**
  no formulário (`<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`)
  ou, se for chamada via `fetch()`/`XMLHttpRequest`, do cabeçalho
  `X-CSRFToken` — veja `templates/galeria.html` pra um exemplo de cada.
- **Sem dependência nova sem checar Python 3.8.** O `install.sh` aceita 3.8
  como piso, e o CI testa contra ele. Antes de fixar uma versão nova de
  pacote em `requirements.txt`, confira o `Requires-Python` dela — várias
  bibliotecas (`waitress`, `Flask-WTF`, `WTForms`) já tiveram que ficar numa
  versão mais antiga só por causa disso, com o motivo documentado em
  comentário ao lado do pin.

## O que esperar de review

Os PRs aceitos até agora (Docker, redesign da GUI, suíte de testes) tinham
em comum: escopo bem definido, testado de verdade antes de abrir (não só
"deveria funcionar"), e descrição explicando o *porquê* da mudança, não só
o *o quê*. Issues e sugestões fora do escopo do seu PR são bem-vindas na
descrição — várias correções recentes começaram exatamente assim.

## Reportando bugs de segurança

Encontrou uma vulnerabilidade (path traversal, XSS, CSRF, etc.)? Abra uma
issue normalmente — o projeto ainda não tem volume de usuários que
justifique um processo de disclosure privado separado, mas se preferir
reportar de forma mais discreta, pode abrir a issue com o mínimo de
detalhes públicos e pedir contato direto.
