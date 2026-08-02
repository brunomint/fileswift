# Changelog

Principais mudanças do FileSwift, release a release. Formato baseado em
[Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/); datas no formato
AAAA-MM-DD.

## [Não lançado]

### Adicionado
- Nome mDNS configurável por instância, com tela própria em **Configurações** —
  necessário pra rodar o FileSwift em mais de uma máquina na mesma rede, já que
  duas instâncias não podem anunciar o mesmo nome mDNS.
- Edição de Textos Rápidos já criados (antes só dava pra criar, ver e apagar).
- Aviso na tela quando um Texto Rápido é editado em outro dispositivo enquanto
  está aberto.
- Suíte de testes automatizados (pytest) + CI no GitHub Actions, rodando em
  Linux (Python 3.8 e 3.11) e Windows a cada push/PR — contribuição de
  [@RomuloPBenedetti](https://github.com/RomuloPBenedetti).
- Branch protection: PR só mescla na `main` se os testes passarem.
- Suporte a Docker (`Dockerfile` multi-stage, `docker-compose.yml`) —
  contribuição de [@kayqueGovetri](https://github.com/kayqueGovetri).
- Interface gráfica (tkinter) redesenhada — contribuição de
  [@pixelcatBR](https://github.com/pixelcatBR).
- Proteção contra CSRF (`Flask-WTF`) em todas as rotas que alteram dados.

### Corrigido
- Vulnerabilidade de path traversal em rotas de arquivo (upload, apagar, mover,
  copiar, criar pasta) — reportada por
  [@RomuloPBenedetti](https://github.com/RomuloPBenedetti).
- Seção "Atividade do Servidor" da GUI ficava sempre zerada, porque `/api/stats`
  caía atrás do gate de autenticação numa consulta que a própria janela faz
  localmente, sem sessão.
- IP incorreto exibido ao rodar via Docker (mostrava o IP interno do container,
  não o da rede local) — corrigido com `network_mode: host`.

### Alterado
- Servidor de desenvolvimento do Flask/Werkzeug trocado por `waitress` (mais
  adequado pra ficar de pé o tempo todo, o Werkzeug é só pra debug).
- Inicialização do `main.py` (pastas, `config.json`, banco, Zeroconf) deixou de
  rodar automaticamente ao importar o módulo — agora é uma chamada explícita
  (`init_app()`), o que também tornou o módulo testável sem efeitos colaterais.
- Lógica sem dependência de widget do `gui_launcher.py` (checagem de porta,
  leitura de estatísticas, encerramento do servidor) extraída pra
  `gui_logica.py`, testável sem construir a janela.
- Removido código morto: `run_flask()` e a rota `/shutdown`, que nunca eram
  usados pelo fluxo real da aplicação.

## [2026.07.25]

### Adicionado
- Primeira versão pública do FileSwift: servidor de arquivos pra rede local
  (galeria com miniaturas, upload por arrastar-e-soltar, busca) e Textos
  Rápidos (notas com destaque automático de e-mail/CPF/CEP/valores em R$).
- Autenticação por senha única compartilhada, protegendo todo acesso.
- QR Code + mDNS (`fs.local`) pra acesso rápido de qualquer celular na rede.
- Empacotamento: `install.sh` (Linux universal), `.deb` (Debian/Ubuntu/Mint/
  Zorin), instalador Windows (PyInstaller + Inno Setup via GitHub Actions).
- Licença MIT.
