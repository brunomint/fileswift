#!/bin/bash
#
# FileSwift - Build do pacote .deb (Debian/Ubuntu/Mint/Zorin)
#
# Gera um pacote que o apt sabe instalar de verdade, resolvendo as
# dependências de sistema (python3-venv, python3-tk) sozinho. As bibliotecas
# Python (Flask, etc) continuam indo para um venv isolado em /opt/fileswift,
# criado no postinst, para garantir sempre as versões travadas no
# requirements.txt independente da versão empacotada pela distro.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }
error() { echo -e "${RED}[ERRO]${NC} $1"; }

if [[ ! -f "main.py" ]]; then
    error "Execute este script no diretório raiz do FileSwift."
    exit 1
fi

if ! command -v dpkg-deb >/dev/null 2>&1; then
    error "dpkg-deb não encontrado (esse script só funciona em sistemas baseados em Debian)."
    exit 1
fi

VERSION=$(date +%Y.%m.%d)
PKG_DIR="fileswift-deb"
PKG_NAME="fileswift_${VERSION}_all.deb"

log "Limpando build anterior..."
rm -rf "$PKG_DIR"
rm -f fileswift_*_all.deb

log "Criando estrutura do pacote..."
mkdir -p "$PKG_DIR/DEBIAN"
mkdir -p "$PKG_DIR/opt/fileswift/app"
mkdir -p "$PKG_DIR/usr/bin"
mkdir -p "$PKG_DIR/usr/share/applications"
mkdir -p "$PKG_DIR/usr/share/icons/hicolor/256x256/apps"

log "Copiando arquivos do aplicativo..."
cp -r ./*.py templates requirements.txt "$PKG_DIR/opt/fileswift/app/"
mkdir -p "$PKG_DIR/opt/fileswift/app/static"
cp static/logo.png "$PKG_DIR/opt/fileswift/app/static/"
cp static/logo.png "$PKG_DIR/usr/share/icons/hicolor/256x256/apps/fileswift.png"

log "Gerando DEBIAN/control..."
cat > "$PKG_DIR/DEBIAN/control" << EOF
Package: fileswift
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.8), python3-venv, python3-pip, python3-tk
Maintainer: Bruno Fragoso <brunofragosoa@gmail.com>
Description: Gerenciador de Arquivos Espacial e Textos Rápidos
 FileSwift e um servidor de arquivos local com interface web, feito para
 compartilhar e organizar arquivos na rede local pelo navegador (com QR
 code, descoberta via mDNS e galeria de fotos/videos), alem de um recurso
 de Textos Rapidos para notas com anexos em PDF (etiquetas, notas fiscais).
EOF

log "Gerando scripts de instalação (postinst/postrm)..."
cat > "$PKG_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e

VENV_DIR="/opt/fileswift/venv"
APP_DIR="/opt/fileswift/app"

if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "Preparando ambiente Python do FileSwift..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo "AVISO: não foi possível criar o ambiente Python do FileSwift." >&2
        exit 0
    fi
fi

"$VENV_DIR/bin/python3" -m pip install -q --upgrade pip 2>/dev/null || true

if ! "$VENV_DIR/bin/python3" -m pip install -q -r "$APP_DIR/requirements.txt"; then
    echo "AVISO: falha ao instalar as dependências do FileSwift (verifique sua internet)." >&2
    echo "Rode manualmente depois:" >&2
    echo "  sudo $VENV_DIR/bin/python3 -m pip install -r $APP_DIR/requirements.txt" >&2
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database /usr/share/applications 2>/dev/null || true

exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postinst"

cat > "$PKG_DIR/DEBIAN/postrm" << 'EOF'
#!/bin/bash
set -e

case "$1" in
    remove|purge)
        rm -rf /opt/fileswift/venv
        # dpkg já tentou remover /opt/fileswift/app e /opt/fileswift antes deste
        # script rodar, mas não conseguiu porque a venv ainda estava lá dentro.
        # Tenta de novo agora que a pasta está realmente vazia (rmdir só apaga
        # se estiver vazia, então é seguro).
        rmdir /opt/fileswift/app 2>/dev/null || true
        rmdir /opt/fileswift 2>/dev/null || true
        ;;
esac

exit 0
EOF
chmod 755 "$PKG_DIR/DEBIAN/postrm"

log "Gerando launcher (/usr/bin/fileswift)..."
cat > "$PKG_DIR/usr/bin/fileswift" << 'EOF'
#!/bin/bash
export FILESWIFT_DATA_DIR="$HOME/.local/share/fileswift"
VENV_PY="/opt/fileswift/venv/bin/python3"

if [ ! -x "$VENV_PY" ]; then
    echo "Ambiente do FileSwift não encontrado. Tente reinstalar o pacote:"
    echo "  sudo apt install --reinstall fileswift"
    exit 1
fi

cd /opt/fileswift/app || exit 1
exec "$VENV_PY" FileSwift.py "$@"
EOF
chmod 755 "$PKG_DIR/usr/bin/fileswift"

log "Gerando atalho .desktop..."
cat > "$PKG_DIR/usr/share/applications/fileswift.desktop" << 'EOF'
[Desktop Entry]
Type=Application
Name=FileSwift
Comment=Gerenciador de Arquivos Espacial - Organize seus arquivos com estilo
Exec=/usr/bin/fileswift
Icon=fileswift
Categories=Utility;FileManager;
Keywords=files;manager;organizer;gallery;
StartupNotify=true
Terminal=false
MimeType=inode/directory;
EOF

log "Ajustando permissões..."
find "$PKG_DIR" -type d -exec chmod 755 {} \;
find "$PKG_DIR/opt/fileswift/app" -type f -exec chmod 644 {} \;
find "$PKG_DIR/usr/share" -type f -exec chmod 644 {} \;
chmod 755 "$PKG_DIR/usr/bin/fileswift"
chmod 755 "$PKG_DIR/DEBIAN/postinst" "$PKG_DIR/DEBIAN/postrm"

log "Empacotando..."
dpkg-deb --build --root-owner-group "$PKG_DIR" "$PKG_NAME"

echo ""
log "✅ Pacote criado: $PKG_NAME"
echo ""
echo "  Instalar:   sudo apt install ./$PKG_NAME"
echo "  Remover:    sudo apt remove fileswift"
echo "  Remover+dados: sudo apt purge fileswift  (dados do usuário ficam em ~/.local/share/fileswift, não são apagados)"
