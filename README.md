# 🚀 FileSwift

FileSwift é um servidor de arquivos para a sua rede local: acesse, organize e compartilhe fotos, vídeos e documentos pelo navegador, de qualquer dispositivo conectado ao mesmo Wi-Fi — sem depender de nuvem, sem instalar app nenhum no celular. Vem também com **Textos Rápidos**, um bloco de notas com suporte a anexar PDFs (etiquetas dos Correios, notas fiscais, etc.), pensado pra quem cola confirmações de pedido o dia inteiro.

## ✨ Funcionalidades

- 📁 **Galeria de arquivos** — navegação por pastas, com miniaturas de imagens e vídeos, separados de documentos
- 📤 **Upload por clique ou arrastar-e-soltar**, múltiplos arquivos de uma vez
- 📝 **Textos Rápidos** — notas com destaque automático de e-mail/CPF/CEP/valores em R$, com anexo de PDFs (várias por texto)
- 🔄 **Atualização automática** — a galeria e as listas de textos se atualizam sozinhas quando outro dispositivo envia ou apaga algo, sem precisar recarregar a página
- 📱 **QR Code + mDNS** (`fs.local`) — acesso rápido de qualquer celular na rede, sem digitar IP
- 🔍 **Busca global** entre pastas e arquivos
- 📋 Copiar, mover, apagar (individual ou em lote), criar pastas
- 🔒 **Acesso por senha** — protegido por padrão; ninguém na rede acessa sem a senha que você define na primeira execução
- 📲 Interface adaptada pra celular (menu lateral, drag-and-drop tocável)

## 🔒 Segurança

O FileSwift pede uma senha única (tipo senha de Wi-Fi, não é login por usuário) antes de liberar qualquer acesso — isso é obrigatório, não dá pra pular. Na primeira vez que abrir, você vai cair direto numa tela pra definir essa senha.

Pontos importantes sobre o modelo de segurança atual:
- Pensado pra uso doméstico, numa rede Wi-Fi que você já confia — não há HTTPS (o cookie de sessão trafega sem criptografia dentro da sua rede local).
- Sessão dura 30 dias por dispositivo (prioriza não pedir senha toda hora).
- 5 tentativas erradas de senha bloqueiam temporariamente o IP por alguns minutos.
- **Esqueceu a senha?** Apague o arquivo `config.json` da pasta de dados (veja "Onde ficam os dados" abaixo) e reinicie — o app volta a pedir pra definir uma senha nova.
- Não tem proteção contra CSRF nem é recomendado expor esse servidor diretamente pra internet (fora da sua rede local).

## 📦 Instalação

Escolha o método pro seu sistema:

### Linux — qualquer distribuição (Ubuntu, Fedora, Arch, etc.)
```bash
git clone https://github.com/brunomint/fileswift.git
cd fileswift
./install.sh
```
Cria um atalho no menu de aplicativos e um comando `fileswift` no terminal. Pra desinstalar: `./uninstall.sh` (mantém seus dados — use `--purge` pra apagar tudo).

### Debian / Ubuntu / Linux Mint / Zorin OS
Baixe o `.deb` mais recente (ou gere o seu: `./build-deb.sh`) e instale com:
```bash
sudo apt install ./fileswift_<versão>_all.deb
```
O `apt` resolve as dependências de sistema sozinho (Python, venv, tkinter).

### Windows
Instalador gerado automaticamente via GitHub Actions a cada release — veja a aba [Actions](../../actions/workflows/build-windows.yml) do repositório pra baixar o `.exe` mais recente (procure pelo artefato `FileSwiftSetup-*`). Instalação por usuário, sem precisar de administrador.

### macOS
Ainda não suportado.

### Rodando direto do código-fonte (dev)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py --console
```

## 🐳 Instalação com Docker

O FileSwift também pode ser executado utilizando Docker, facilitando a instalação e o isolamento das dependências.

### Pré-requisitos

* Docker
* Docker Compose (v2 ou superior)

### Executando

Clone o repositório e acesse a pasta do projeto:

```bash
git clone https://github.com/brunomint/fileswift.git
cd fileswift
```

Inicie a aplicação:

```bash
docker compose up -d --build
```

Após a inicialização, o FileSwift estará disponível em:

```text
http://localhost:5678
```

### Persistência dos dados

Todos os dados do FileSwift são armazenados no diretório `data/`, montado automaticamente como volume pelo `docker-compose.yml`.

Isso inclui:

* `config.json`
* `fileswift.db`
* Uploads de arquivos
* Anexos dos Textos Rápidos
* Demais dados persistentes da aplicação

Dessa forma, atualizar ou recriar o container **não remove seus arquivos nem suas configurações**.

### Atualizando

Após atualizar o código-fonte do projeto, execute:

```bash
docker compose up -d --build
```

O Docker reconstruirá a imagem e iniciará a versão mais recente, preservando todos os dados armazenados no diretório `data/`.

### Parando a aplicação

```bash
docker compose down
```

## 🌐 Como acessar

Depois de iniciado, o servidor fica disponível em:
- **Nesta máquina:** `http://localhost:5678`
- **De outros dispositivos na mesma rede:** `http://<IP-da-máquina>:5678` ou `http://fs.local:5678`
- **Pelo celular:** escaneie o QR Code exibido na página inicial

Rodando o FileSwift em mais de uma máquina na mesma rede? Cada uma precisa de um nome próprio (mDNS não permite duas máquinas anunciando `fs.local` ao mesmo tempo — a segunda simplesmente não registra). Troque em **Configurações** na barra lateral da galeria.

## 🗂 Onde ficam os seus dados

Nada é gravado dentro da pasta de instalação. Tudo fica numa pasta própria, separada por dispositivo:

| Instalação | Pasta de dados |
|---|---|
| `install.sh` / `.deb` (Linux) | `~/.local/share/fileswift/` |
| Windows | `%LOCALAPPDATA%\FileSwift\` |
| Rodando do código-fonte | a própria pasta do projeto |

Lá dentro: `fileswift.db` (textos rápidos), `static/download/` (seus arquivos), `textos_anexos/` (PDFs anexados) e `config.json` (senha e configuração — nunca é versionado no Git).

## 📋 Formatos suportados

**Imagens:** PNG, JPG, JPEG, GIF, WebP, HEIC/HEVC
**Vídeos:** MP4, WebM, OGG, MOV, HEIF
**Anexos de Textos Rápidos:** PDF
**Demais arquivos:** qualquer tipo é aceito no upload e listado como documento (sem restrição de extensão)

## 🆘 Problemas comuns

**Esqueci a senha** — apague `config.json` na pasta de dados (veja tabela acima) e reinicie o app.

**"Porta 5678 em uso"** — outra instância do FileSwift já está rodando (nesta máquina ou em segundo plano); feche-a antes de abrir de novo.

**Python sem `venv`/`tkinter` (Ubuntu 23.04+ / Debian recente)** — o `install.sh` detecta isso e mostra o comando certo pra instalar (`sudo apt install python3-venv python3-tk`); com o `.deb`, isso já é resolvido automaticamente pelo `apt`.

## 🧑‍💻 Para desenvolvedores

- `main.py` — servidor Flask (toda a lógica de rotas, banco SQLite, autenticação)
- `gui_launcher.py` — janela tkinter opcional (o app funciona igual sem ela, abrindo direto no navegador)
- `templates/` — HTML (Jinja2), um arquivo por tela
- `install.sh`, `build-deb.sh`, `fileswift.spec` + `.github/workflows/build-windows.yml` — empacotamento por plataforma

## 📄 Licença

MIT — veja o arquivo [LICENSE](LICENSE).

## ☕ Apoie o projeto

Se o FileSwift foi útil pra você, considere apoiar em [ko-fi.com/brunofragosodealmeida](https://ko-fi.com/brunofragosodealmeida).
