#!/usr/bin/env python3
"""
Script para instalar dependências do FileSwift
"""

import subprocess
import sys
import os

def install_requirements():
    """Instalar dependências do requirements.txt"""
    print("📦 FileSwift - Instalador de Dependências")
    print("=" * 50)
    
    requirements_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    
    if not os.path.exists(requirements_file):
        print("❌ Arquivo requirements.txt não encontrado!")
        return False
    
    try:
        print("⏳ Instalando dependências...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", requirements_file
        ])
        print("✅ Todas as dependências foram instaladas com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro na instalação: {e}")
        return False
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return False

def check_dependencies():
    """Verificar se dependências estão instaladas"""
    required_modules = ['flask', 'werkzeug', 'zeroconf', 'qrcode', 'PIL', 'requests']
    missing = []
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    return missing

if __name__ == "__main__":
    print("🔍 Verificando dependências...")
    missing = check_dependencies()
    
    if missing:
        print(f"⚠️  Dependências faltando: {', '.join(missing)}")
        if install_requirements():
            print("\n🚀 Pronto! Agora você pode executar o FileSwift.")
        else:
            print("\n❌ Falha na instalação. Tente instalar manualmente:")
            print("pip install -r requirements.txt")
    else:
        print("✅ Todas as dependências estão instaladas!")
        print("🚀 FileSwift pronto para uso!")
    
    input("\nPressione Enter para continuar...")
