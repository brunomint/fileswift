#!/usr/bin/env python3
"""
FileSwift - Gerenciador de Arquivos Web
Launcher principal com interface gráfica
"""

import sys
import os

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    try:
        # Tentar importar e executar a GUI
        from gui_launcher import FileSwiftGUI
        
        print("🚀 FileSwift - Iniciando interface gráfica...")
        gui = FileSwiftGUI()
        gui.run()
        
    except ImportError as e:
        print(f"⚠️  Dependência não encontrada: {e}")
        print("📦 Instalando dependências necessárias...")
        
        # Tentar instalar Pillow
        try:
            import subprocess
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            print("✅ Pillow instalado com sucesso!")
            
            # Tentar novamente
            from gui_launcher import FileSwiftGUI
            gui = FileSwiftGUI()
            gui.run()
            
        except Exception as install_error:
            print(f"❌ Erro na instalação: {install_error}")
            print("🔄 Executando em modo console...")
            fallback_to_console()
    
    except Exception as e:
        print(f"❌ Erro na interface gráfica: {e}")
        print("🔄 Executando em modo console...")
        fallback_to_console()

def fallback_to_console():
    """Fallback para modo console se GUI falhar"""
    try:
        from main import run_console_mode
        run_console_mode()
    except Exception as e:
        print(f"❌ Erro crítico: {e}")
        input("Pressione Enter para sair...")

if __name__ == "__main__":
    main()
