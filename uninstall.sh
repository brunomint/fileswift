#!/bin/bash
#
# FileSwift - Desinstalador
# Remove o app e o ambiente Python instalados pelo install.sh.
# Por padrão, NÃO apaga seus dados (banco de textos rápidos, arquivos
# enviados, anexos). Use --purge se quiser apagar tudo também.

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[AVISO]${NC} $1"; }

PURGE=0
if [ "$1" = "--purge" ]; then
    PURGE=1
fi

DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fileswift"
BIN_DIR="$HOME/.local/bin"

log "Removendo atalho e ícone..."
rm -f "$HOME/.local/share/applications/fileswift.desktop"
rm -f "$HOME/.local/share/icons/hicolor/256x256/apps/fileswift.png"
rm -f "$BIN_DIR/fileswift"

log "Removendo aplicativo e ambiente Python..."
rm -rf "$DATA_DIR/app"
rm -rf "$DATA_DIR/venv"

if [ "$PURGE" = "1" ]; then
    warn "Removendo TAMBÉM seus dados (banco de textos, arquivos enviados, anexos)..."
    rm -rf "$DATA_DIR"
else
    if [ -d "$DATA_DIR" ]; then
        echo ""
        log "Seus dados foram mantidos em: $DATA_DIR"
        echo "  (banco de textos rápidos, arquivos enviados, anexos em PDF)"
        echo "  Rode '$0 --purge' se quiser apagar tudo também."
    fi
fi

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo ""
log "✅ FileSwift desinstalado."
