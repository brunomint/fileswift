#!/bin/bash
#
# FileSwift - Instalador universal para Linux
# Funciona em qualquer distribuição com python3 disponível (Debian/Ubuntu,
# Fedora, Arch, openSUSE, etc). Cria um ambiente Python isolado (venv) na
# pasta de dados do usuário, sem tocar no Python do sistema.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error() { echo -e "${RED}[ERRO]${NC} $1"; }

if [[ ! -f "main.py" ]]; then
    error "Execute este script no diretório raiz do FileSwift (onde está o main.py)."
    exit 1
fi

# --- Detectar Python ---
detect_python() {
    for python_cmd in python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
        if command -v "$python_cmd" >/dev/null 2>&1; then
            echo "$python_cmd"
            return 0
        fi
    done
}

PYTHON_CMD=$(detect_python)
if [ -z "$PYTHON_CMD" ]; then
    error "Python 3 não encontrado. Instale o Python 3.8 ou superior antes de continuar."
    exit 1
fi
log "Usando $PYTHON_CMD ($($PYTHON_CMD --version))"

# --- Sugestão de correção por distro, caso o venv falhe ---
sugerir_pacotes_sistema() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "${ID}${ID_LIKE:+ $ID_LIKE}" in
            *debian*|*ubuntu*)
                echo "sudo apt install python3-venv python3-tk"
                ;;
            *fedora*|*rhel*)
                echo "sudo dnf install python3-tkinter"
                ;;
            *arch*)
                echo "sudo pacman -S tk"
                ;;
            *opensuse*|*suse*)
                echo "sudo zypper install python3-tk"
                ;;
            *)
                echo "instale os pacotes de 'venv' e 'tkinter' do Python pelo gerenciador de pacotes da sua distro"
                ;;
        esac
    else
        echo "instale os pacotes de 'venv' e 'tkinter' do Python pelo gerenciador de pacotes da sua distro"
    fi
}

# --- Pasta de dados (XDG) ---
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fileswift"
APP_DIR="$DATA_DIR/app"
VENV_DIR="$DATA_DIR/venv"
BIN_DIR="$HOME/.local/bin"

log "Instalando em: $DATA_DIR"
mkdir -p "$APP_DIR" "$BIN_DIR" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"

# --- Copiar arquivos do app (nunca a pasta static/download, que é dado do usuário) ---
log "Copiando arquivos do aplicativo..."
cp -r ./*.py templates requirements.txt "$APP_DIR/"
mkdir -p "$APP_DIR/static"
cp static/logo.png "$APP_DIR/static/"

# --- Criar/atualizar venv isolado ---
if [ ! -x "$VENV_DIR/bin/python3" ]; then
    log "Criando ambiente Python isolado (primeira instalação)..."
    if ! "$PYTHON_CMD" -m venv "$VENV_DIR"; then
        error "Não foi possível criar o ambiente Python (venv)."
        echo "Rode o seguinte comando e tente de novo:"
        echo "  $(sugerir_pacotes_sistema)"
        exit 1
    fi
else
    log "Ambiente Python já existe, reaproveitando."
fi

VENV_PY="$VENV_DIR/bin/python3"

log "Instalando dependências..."
if ! "$VENV_PY" -m pip install -q --upgrade pip 2>/dev/null; then
    warn "Não foi possível atualizar o pip (seguindo mesmo assim)."
fi
if ! "$VENV_PY" -m pip install -q -r "$APP_DIR/requirements.txt"; then
    error "Falha ao instalar as dependências. Verifique sua conexão com a internet."
    exit 1
fi

if ! "$VENV_PY" -c "import tkinter" 2>/dev/null; then
    warn "tkinter não está disponível no Python do sistema — o FileSwift vai abrir no navegador em vez de numa janela própria."
    warn "Para ter a janela nativa, rode: $(sugerir_pacotes_sistema)"
fi

# --- Launcher ---
log "Criando launcher..."
cat > "$BIN_DIR/fileswift" << EOF
#!/bin/bash
export FILESWIFT_DATA_DIR="$DATA_DIR"
VENV_PY="$VENV_DIR/bin/python3"

if [ ! -x "\$VENV_PY" ]; then
    echo "Ambiente do FileSwift não encontrado. Rode o install.sh de novo."
    exit 1
fi

"\$VENV_PY" -c "import flask, werkzeug, zeroconf, qrcode, PIL, requests" 2>/dev/null || {
    echo "Reinstalando dependências..."
    "\$VENV_PY" -m pip install -q -r "$APP_DIR/requirements.txt"
}

cd "$APP_DIR" || exit 1
exec "\$VENV_PY" FileSwift.py "\$@"
EOF
chmod +x "$BIN_DIR/fileswift"

# --- Ícone ---
cp static/logo.png "$HOME/.local/share/icons/hicolor/256x256/apps/fileswift.png"

# --- Atalho .desktop ---
log "Criando atalho no menu de aplicativos..."
cat > "$HOME/.local/share/applications/fileswift.desktop" << EOF
[Desktop Entry]
Type=Application
Name=FileSwift
Comment=Gerenciador de Arquivos Espacial - Organize seus arquivos com estilo
Exec=$BIN_DIR/fileswift
Icon=fileswift
Categories=Utility;FileManager;
Keywords=files;manager;organizer;gallery;
StartupNotify=true
Terminal=false
MimeType=inode/directory;
EOF

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
log "✅ FileSwift instalado com sucesso!"
echo ""
echo "  Abrir pelo menu de aplicativos, ou pelo terminal:"
echo "    fileswift"
echo ""
if ! command -v fileswift >/dev/null 2>&1; then
    warn "$BIN_DIR não está no seu PATH — o atalho do menu funciona normalmente,"
    warn "mas pra rodar 'fileswift' no terminal, adicione ao seu ~/.bashrc ou ~/.zshrc:"
    echo '    export PATH="$HOME/.local/bin:$PATH"'
fi
