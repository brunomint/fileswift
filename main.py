from flask import Flask, send_file, request, render_template, redirect, url_for, flash, send_from_directory, abort, jsonify, session, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import waitress
import logging
from logging.handlers import RotatingFileHandler
import os
import zipfile
import io
import threading
from werkzeug.utils import secure_filename
import shutil
from zeroconf import ServiceInfo, Zeroconf
import socket
import subprocess
import platform
from datetime import datetime, timedelta
from collections import defaultdict
import qrcode
import time
import webbrowser
import sqlite3
import re
import uuid
import hashlib
import json
import secrets
from markupsafe import Markup, escape
from flask_wtf import CSRFProtect

# Logger da aplicação — console sempre (mesmo texto de antes, sem prefixo,
# pra não mudar a experiência de quem acompanha --console), arquivo rotativo
# adicionado em init_app() assim que DATA_DIR é conhecido, pra dar pra pedir
# "me manda o log" pra alguém reportando um problema.
logger = logging.getLogger('fileswift')
logger.setLevel(logging.INFO)
logger.propagate = False
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(_console_handler)

app = Flask(__name__, static_folder=None)

# Protege todo POST/PUT/PATCH/DELETE contra CSRF: sem isso, uma página maliciosa
# aberta no mesmo navegador (com sessão do FileSwift já ativa) podia disparar
# ações destrutivas (apagar arquivo, trocar senha) só pelo cookie de sessão viajar
# automaticamente. O token exigido daqui pra frente não é visível/acessível a um
# site de fora. csrf_token() fica disponível nos templates via injeção do próprio
# Flask-WTF, sem precisar registrar nada a mais.
csrf = CSRFProtect(app)

porta = 5678

# Zeroconf persistente — construído em init_app(), não no import (ver função
# mais abaixo, depois que DATA_DIR/CONFIG_PATH/etc. já estão definidos).
zeroconf = None
servico_mdns = None  # Guardará o último serviço registrado
ip_atual = None  # Guardará o último IP detectado

# Pasta gravável onde ficam os dados do usuário (banco, uploads, anexos, QR code).
# No uso normal (python3 main.py) é a própria pasta do projeto, como sempre foi.
# Em pacotes que rodam de um local somente leitura ou fora da pasta do projeto
# (AppImage, .deb, instalador Windows), FILESWIFT_DATA_DIR é definida pelo
# launcher; no Windows, sem launcher definindo a variável, cai no padrão
# %LOCALAPPDATA%\FileSwift (equivalente Windows do ~/.local/share).
def _data_dir_padrao():
    if platform.system() == 'Windows':
        return os.path.join(os.environ.get('LOCALAPPDATA', app.root_path), 'FileSwift')
    return app.root_path


DATA_DIR = os.environ.get('FILESWIFT_DATA_DIR', _data_dir_padrao())

# --- Configuração persistente (senha de acesso, chave de sessão) ---
# Guardada em DATA_DIR (mesma pasta gravável de fileswift.db etc.), então já
# funciona automaticamente em qualquer forma de instalação, sem tocar nos
# scripts de empacotamento.
#
# Para resetar a senha esquecida: apague o campo "senha_hash" (ou o arquivo
# config.json inteiro) na pasta de dados do FileSwift. Na próxima requisição
# o app volta ao estado de "configuração pendente" e pede uma senha nova.
CONFIG_PATH = os.path.join(DATA_DIR, 'config.json')


def carregar_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if config.get('secret_key'):
                return config
        except (json.JSONDecodeError, OSError):
            pass
    # Não existe ainda, ou está corrompido/sem secret_key: cria do zero.
    # A secret_key precisa existir mesmo antes de haver senha configurada,
    # já que o Flask precisa dela desde a própria tela de configuração inicial.
    config = {'secret_key': secrets.token_hex(32)}
    salvar_config(config)
    return config


def salvar_config(config):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f)
    os.chmod(CONFIG_PATH, 0o600)


# Populado de verdade em init_app() — precisa existir aqui pra funções que
# fecham sobre CONFIG (definir_senha, obter_mdns_nome, etc.) terem uma
# referência de módulo válida mesmo antes de init_app() rodar.
CONFIG = {}


def senha_esta_configurada():
    return bool(CONFIG.get('senha_hash'))


def definir_senha(senha):
    CONFIG['senha_hash'] = generate_password_hash(senha)
    CONFIG['criado_em'] = datetime.now().isoformat()
    salvar_config(CONFIG)


def verificar_senha(senha):
    return check_password_hash(CONFIG.get('senha_hash', ''), senha)


# --- Nome mDNS configurável por máquina ---
# Padrão "fs" preserva o comportamento de sempre (fs.local) pra quem só roda
# uma instância. Fica configurável pra quem roda o FileSwift em mais de uma
# máquina na mesma rede — mDNS não permite duas máquinas anunciando o mesmo
# nome (a segunda simplesmente falha em registrar), então cada uma precisa
# de um nome próprio (ex: "sala", "escritorio").
MDNS_NOME_REGEX = re.compile(r'^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$')


def obter_mdns_nome():
    return CONFIG.get('mdns_nome', 'fs')


def obter_mdns_dominio():
    """FQDN com ponto final, no formato exigido pelo campo 'server' do zeroconf."""
    return f"{obter_mdns_nome()}.local."


def obter_mdns_host():
    """Endereço pra exibir pro usuário (sem o ponto final técnico do DNS)."""
    return f"{obter_mdns_nome()}.local"


def obter_mdns_servico_nome():
    return f"{obter_mdns_nome()}._http._tcp.local."


def mdns_nome_valido(nome):
    return bool(MDNS_NOME_REGEX.fullmatch(nome))


def definir_mdns_nome(nome):
    CONFIG['mdns_nome'] = nome
    salvar_config(CONFIG)


MEDIA_FOLDER = os.path.join(DATA_DIR, 'static', 'download')
UPLOAD_FOLDER = os.path.join(MEDIA_FOLDER, 'uploads')  # pasta padrão de upload

texto = "🚀 Acessar FileSwift"  # Texto do link


def resolver_caminho_seguro(caminho_relativo, base=None):
    """Junta `caminho_relativo` (vindo de URL ou de campo de formulário) a `base`
    (por padrão MEDIA_FOLDER) e confere que o resultado não escapa de `base` via
    sequências como '..' — proteção contra path traversal. Retorna None se o
    caminho tentar sair da pasta base; caso contrário, retorna o caminho absoluto
    já resolvido, pronto pra usar."""
    if base is None:
        base = MEDIA_FOLDER
    base_real = os.path.realpath(base)
    caminho_resolvido = os.path.realpath(os.path.join(base, caminho_relativo or ''))
    if caminho_resolvido != base_real and not caminho_resolvido.startswith(base_real + os.sep):
        return None
    return caminho_resolvido

# --- Textos Rápidos (notas coladas, ex: confirmações de pedido) ---
DB_PATH = os.path.join(DATA_DIR, 'fileswift.db')

# Pasta onde ficam os PDFs anexados aos textos rápidos (etiquetas, notas fiscais, etc.)
TEXTOS_ANEXOS_FOLDER = os.path.join(DATA_DIR, 'textos_anexos')


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS textos_rapidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            conteudo TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS textos_anexos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            texto_id INTEGER NOT NULL,
            nome_arquivo TEXT NOT NULL,
            nome_original TEXT NOT NULL,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS acessos_diarios (
            data TEXT PRIMARY KEY,
            contagem INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # Migração: banco de instalação já existente pode não ter a coluna
    # atualizado_em (adicionada pra detectar edição feita em outro dispositivo).
    colunas = [c['name'] for c in conn.execute('PRAGMA table_info(textos_rapidos)').fetchall()]
    if 'atualizado_em' not in colunas:
        # SQLite não aceita DEFAULT não-constante (CURRENT_TIMESTAMP) num ALTER TABLE ADD COLUMN,
        # por isso o valor pras linhas existentes é preenchido explicitamente logo abaixo; novas
        # linhas sempre recebem atualizado_em explicitamente nas próprias queries de INSERT/UPDATE.
        conn.execute('ALTER TABLE textos_rapidos ADD COLUMN atualizado_em TIMESTAMP')
        conn.execute('UPDATE textos_rapidos SET atualizado_em = criado_em WHERE atualizado_em IS NULL')

    conn.commit()
    conn.close()


REGEX_EMAIL = re.compile(r'[\w.\-]+@[\w.\-]+\.\w+')
REGEX_VALOR = re.compile(r'R\$\s?\d{1,3}(?:\.\d{3})*,\d{2}')
REGEX_CPF = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')
REGEX_CEP = re.compile(r'\d{5}-\d{3}')


def destacar_texto(texto_bruto):
    """Escapa o texto e envolve e-mail, CPF, CEP e valores em R$ com <span> destacado."""
    texto_html = str(escape(texto_bruto))

    def marcar(regex, classe, s):
        return regex.sub(lambda m: f'<span class="destaque {classe}">{m.group(0)}</span>', s)

    texto_html = marcar(REGEX_EMAIL, 'destaque-email', texto_html)
    texto_html = marcar(REGEX_VALOR, 'destaque-valor', texto_html)
    texto_html = marcar(REGEX_CPF, 'destaque-cpf', texto_html)
    texto_html = marcar(REGEX_CEP, 'destaque-cep', texto_html)

    return Markup(texto_html.replace('\n', '<br>'))


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'ogg', 'pdf', 'txt', 'doc', 'docx', 'html', 'zip', 'py', 'md', 'xml', 'sh', 'script', 'lck', 'log', 'properties', 'docx', 'dot', 'odt', 'xls', 'csv', 'ods', 'ppt', 'pptx', 'odp', 'mp3', 'wav', 'svg', 'json', 'hevc', 'heif', 'mov'}

# Variáveis globais para monitoramento
servidor_iniciado_em = None
# "Conectado agora" é uma noção transitória por natureza — depois de reiniciar
# o servidor não tem mesmo ninguém conectado ainda, então isso fica só em
# memória, sem necessidade de persistir. Acessos do dia, ao contrário, é uma
# contagem que deveria valer o dia inteiro mesmo com reinício no meio — por
# isso mora na tabela acessos_diarios (ver registrar_acesso() mais abaixo).
dispositivos_conectados = set()
ultimo_acesso_por_ip = {}

# Rate limiting de tentativas de login (em memória, reinicia a cada boot —
# suficiente para o modelo de ameaça doméstico, não precisa persistir).
tentativas_login_por_ip = defaultdict(list)
LOGIN_MAX_TENTATIVAS = 5
LOGIN_JANELA = timedelta(minutes=10)


def obter_ip_cliente(req):
    ip_cliente = req.environ.get('HTTP_X_FORWARDED_FOR', req.environ.get('REMOTE_ADDR', 'unknown'))
    if ',' in ip_cliente:
        ip_cliente = ip_cliente.split(',')[0].strip()
    return ip_cliente


def ip_esta_bloqueado(ip):
    agora = datetime.now()
    tentativas = [t for t in tentativas_login_por_ip.get(ip, []) if agora - t < LOGIN_JANELA]
    tentativas_login_por_ip[ip] = tentativas
    return len(tentativas) >= LOGIN_MAX_TENTATIVAS


def registrar_tentativa_falha(ip):
    tentativas_login_por_ip[ip].append(datetime.now())


def limpar_tentativas(ip):
    tentativas_login_por_ip.pop(ip, None)


def obter_nome_rede_wifi():
    """Obter nome da rede WiFi conectada"""
    try:
        sistema = platform.system().lower()
        
        if sistema == "linux":
            # Tentar nmcli primeiro (NetworkManager)
            try:
                result = subprocess.run(['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'], 
                                      capture_output=True, text=True, timeout=5)
                for linha in result.stdout.split('\n'):
                    if linha.startswith('yes:'):
                        return linha.split(':', 1)[1].strip()
            except:
                pass
            
            # Tentar iwgetid como alternativa
            try:
                result = subprocess.run(['iwgetid', '-r'], capture_output=True, text=True, timeout=5)
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except:
                pass
                
        elif sistema == "darwin":  # macOS
            try:
                result = subprocess.run(['/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport', '-I'], 
                                      capture_output=True, text=True, timeout=5)
                for linha in result.stdout.split('\n'):
                    if 'SSID:' in linha:
                        return linha.split('SSID:')[1].strip()
            except:
                pass
                
        elif sistema == "windows":
            try:
                result = subprocess.run(['netsh', 'wlan', 'show', 'profiles'], 
                                      capture_output=True, text=True, timeout=5)
                # Implementação simplificada - pode precisar de ajustes
                for linha in result.stdout.split('\n'):
                    if 'Perfil de Todos os Usuários' in linha or 'All User Profile' in linha:
                        return linha.split(':')[1].strip()
            except:
                pass
        
        return "Rede não identificada"
        
    except Exception as e:
        return "Erro ao detectar rede"

def registrar_acesso_do_dia(hoje):
    """Incrementa o contador de acessos de `hoje` (formato AAAA-MM-DD) no banco,
    criando a linha se ainda não existir. Separado de registrar_acesso() pra
    poder testar sem precisar de um IP de verdade."""
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO acessos_diarios (data, contagem) VALUES (?, 1) '
        'ON CONFLICT(data) DO UPDATE SET contagem = contagem + 1',
        (hoje,)
    )
    conn.commit()
    conn.close()


def obter_acessos_do_dia(hoje):
    conn = get_db_connection()
    linha = conn.execute('SELECT contagem FROM acessos_diarios WHERE data = ?', (hoje,)).fetchone()
    conn.close()
    return linha['contagem'] if linha else 0


def registrar_acesso(ip_cliente, contar_como_acesso=True):
    """Registrar acesso de um dispositivo"""
    global dispositivos_conectados, ultimo_acesso_por_ip

    # O próprio servidor "se visita" o tempo todo: a janela tkinter consulta
    # /api/stats via localhost a cada poucos segundos, e a aba que abre sozinha
    # no navegador ao iniciar usa o IP da própria máquina. Nenhum dos dois é um
    # dispositivo de verdade — contar os dois só infla o número sem significar
    # que tem mais gente usando.
    eh_o_proprio_servidor = ip_cliente == '127.0.0.1' or (ip_atual and ip_cliente == ip_atual)

    if not eh_o_proprio_servidor:
        dispositivos_conectados.add(ip_cliente)
        ultimo_acesso_por_ip[ip_cliente] = datetime.now()

    # Registrar acesso do dia (persiste no banco — sobrevive a reinício no meio do dia)
    if contar_como_acesso:
        registrar_acesso_do_dia(datetime.now().strftime('%Y-%m-%d'))

    # Limpar dispositivos inativos (mais de 5 minutos sem acesso)
    agora = datetime.now()
    dispositivos_inativos = []
    for ip, ultimo_acesso in ultimo_acesso_por_ip.items():
        if agora - ultimo_acesso > timedelta(minutes=5):
            dispositivos_inativos.append(ip)
    
    for ip in dispositivos_inativos:
        dispositivos_conectados.discard(ip)
        del ultimo_acesso_por_ip[ip]

def formatar_tempo_ativo(desde, agora=None):
    """Formata a duração entre `desde` e `agora` (padrão: agora) como HH:MM:SS.
    Pura: não lê estado de módulo, só os argumentos recebidos."""
    if desde is None:
        return "00:00:00"
    tempo_ativo = (agora or datetime.now()) - desde
    horas = int(tempo_ativo.total_seconds() // 3600)
    minutos = int((tempo_ativo.total_seconds() % 3600) // 60)
    segundos = int(tempo_ativo.total_seconds() % 60)
    return f"{horas:02d}:{minutos:02d}:{segundos:02d}"


def obter_estatisticas_servidor():
    """Obter estatísticas do servidor"""
    global servidor_iniciado_em, dispositivos_conectados

    tempo_ativo_str = formatar_tempo_ativo(servidor_iniciado_em)

    # Acessos hoje (persistido no banco, sobrevive a reinício no meio do dia)
    hoje = datetime.now().strftime('%Y-%m-%d')
    acessos_hoje = obter_acessos_do_dia(hoje)

    # Nome da rede
    nome_rede = obter_nome_rede_wifi()
    
    return {
        'tempo_ativo': tempo_ativo_str,
        'dispositivos_conectados': len(dispositivos_conectados),
        'acessos_hoje': acessos_hoje,
        'nome_rede': nome_rede,
        'servidor_iniciado_em': servidor_iniciado_em
    }

# Função para obter o endereço IP local com tratamento de erro e formato com porta
def obter_endereco_ip(com_porta=False):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return f"{ip}:{porta}" if com_porta else ip


# Função que gera a tag <a> pronta
def gerar_link():
    endereco = obter_endereco_ip(com_porta=True)
    return f'<a href="http://{endereco}" target="_blank">Endereço da página: http://{endereco}</a>'


# Pasta gravável onde o QR code é salvo (mesma lógica do DATA_DIR acima)
QRCODE_FOLDER = os.path.join(DATA_DIR, 'static')
QRCODE_PATH = os.path.join(QRCODE_FOLDER, 'qrcode.png')

_INICIALIZADO = False


def init_app():
    """Efeitos colaterais de inicialização (pastas, config.json, banco, Zeroconf).
    Não roda mais no import — chamada explicitamente por quem for de fato servir
    requisições (run_console_mode, FileSwiftGUI.__init__) e por quem for testar
    (conftest.py). Idempotente: chamada repetida não faz nada."""
    global CONFIG, zeroconf, _INICIALIZADO
    if _INICIALIZADO:
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    arquivo_log = RotatingFileHandler(
        os.path.join(DATA_DIR, 'fileswift.log'), maxBytes=1_000_000, backupCount=3, encoding='utf-8'
    )
    arquivo_log.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(arquivo_log)
    CONFIG = carregar_config()
    app.secret_key = CONFIG['secret_key']
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(TEXTOS_ANEXOS_FOLDER, exist_ok=True)
    init_db()
    os.makedirs(QRCODE_FOLDER, exist_ok=True)
    zeroconf = Zeroconf()
    _INICIALIZADO = True


# Função para gerar QR Code
def gerar_qrcode(url):
    # Gerar QR Code a partir da URL
    qr = qrcode.make(url)
    # Salva a imagem gerada em um arquivo temporário
    qr.save(QRCODE_PATH)
    return QRCODE_PATH

def criar_qrcode_simples():
    endereco = obter_endereco_ip(com_porta=True)
    url = f"http://{endereco}/"

    qr = qrcode.make(url)
    qr.save(QRCODE_PATH)

    logger.info(f"QR Code gerado em {QRCODE_PATH} para {url}")






def allowed_file(filename):
    # Aceitar TODOS os tipos de arquivo - sem filtro!
    return True


@app.route('/upload/', defaults={'pasta': ''}, methods=['GET', 'POST'])
@app.route('/upload/<path:pasta>', methods=['GET', 'POST'])
def upload(pasta):
    logger.info(f"🔍 Upload iniciado - Pasta: '{pasta}', Método: {request.method}")

    caminho_pasta = resolver_caminho_seguro(pasta)
    logger.info(f"📁 Caminho da pasta: {caminho_pasta}")

    if caminho_pasta is None or not os.path.exists(caminho_pasta):
        logger.error(f"❌ Pasta não existe: {caminho_pasta}")
        abort(404)

    if request.method == 'POST':
        logger.info("📤 Processando POST de upload...")
        
        # Verificar se há arquivos na requisição
        logger.info(f"🔍 Arquivos na requisição: {list(request.files.keys())}")
        
        if 'file' not in request.files:
            logger.error("❌ Nenhum campo 'file' encontrado na requisição")
            flash('Nenhum arquivo enviado')
            return redirect(request.url)

        arquivos = request.files.getlist('file')
        logger.info(f"📋 {len(arquivos)} arquivo(s) recebido(s)")

        enviados = []
        erros = []

        for i, file in enumerate(arquivos):
            logger.info(f"📄 Processando arquivo {i+1}: '{file.filename}'")
            
            if file.filename == '':
                logger.warning(f"⚠️ Arquivo {i+1} sem nome, pulando...")
                continue
                
            if not allowed_file(file.filename):
                erro = f"Arquivo '{file.filename}' não permitido"
                logger.error(f"❌ {erro}")
                erros.append(erro)
                continue
                
            try:
                filename = secure_filename(file.filename)
                caminho_arquivo = os.path.join(caminho_pasta, filename)
                logger.info(f"💾 Salvando em: {caminho_arquivo}")
                
                # Verificar se a pasta tem permissão de escrita
                if not os.access(caminho_pasta, os.W_OK):
                    erro = f"Sem permissão de escrita na pasta: {caminho_pasta}"
                    logger.error(f"❌ {erro}")
                    erros.append(erro)
                    continue
                
                # Verificar se o arquivo já existe
                if os.path.exists(caminho_arquivo):
                    logger.warning(f"⚠️ Arquivo já existe, será sobrescrito: {filename}")
                
                file.save(caminho_arquivo)
                logger.info(f"✅ Arquivo salvo com sucesso: {filename}")
                enviados.append(filename)
                
            except Exception as e:
                erro = f"Erro ao salvar '{file.filename}': {str(e)}"
                logger.error(f"❌ {erro}")
                erros.append(erro)

        # Preparar mensagens de resultado
        mensagens = []
        if enviados:
            msg_sucesso = f'✅ Arquivos enviados: {", ".join(enviados)}'
            logger.info(msg_sucesso)
            mensagens.append(msg_sucesso)
            
        if erros:
            for erro in erros:
                logger.error(f"❌ {erro}")
                mensagens.append(f"❌ {erro}")
        
        if not enviados and not erros:
            msg_erro = 'Nenhum arquivo válido foi enviado.'
            logger.warning(f"⚠️ {msg_erro}")
            mensagens.append(msg_erro)

        # Flash todas as mensagens
        for msg in mensagens:
            flash(msg)

        logger.info(f"🔄 Redirecionando para galeria da pasta: '{pasta}'")
        return redirect(url_for('galeria', pasta=pasta))

    logger.info("📄 Renderizando template de upload...")
    return render_template('upload.html', pasta=pasta)


@app.route('/static/logo.png')
def static_logo():
    """Serve o logo (asset fixo do app, empacotado com o código — não dado do usuário)."""
    return send_from_directory(os.path.join(app.root_path, 'static'), 'logo.png')


@app.route('/static/qrcode.png')
def static_qrcode():
    """Serve o QR code a partir da pasta gravável (DATA_DIR), não da pasta estática somente leitura do AppImage."""
    return send_from_directory(QRCODE_FOLDER, 'qrcode.png')


@app.route('/')
def index():
    link = gerar_link()
    logger.info(f"Link gerado: {link}")
    return render_template('index.html', link=link, mdns_dominio=obter_mdns_host(), porta=porta)

@app.route('/test-upload')
def test_upload():
    """Página de teste para debug de upload"""
    return render_template('test_upload.html')


@app.route('/browser')
def browser():
    """Redireciona para a galeria - interface unificada"""
    return redirect(url_for('galeria'))




@app.route('/galeria/', defaults={'pasta': ''})
@app.route('/galeria/<path:pasta>')
def galeria(pasta):
    caminho_pasta = resolver_caminho_seguro(pasta)
    if caminho_pasta is None or not os.path.exists(caminho_pasta):
        abort(404)
    
    arquivos = os.listdir(caminho_pasta)
    
    # Filtrar apenas pastas
    subpastas = [nome for nome in arquivos if os.path.isdir(os.path.join(caminho_pasta, nome))]
    
    # Filtrar apenas arquivos (não pastas)
    apenas_arquivos = [f for f in arquivos if os.path.isfile(os.path.join(caminho_pasta, f))]
    
    # Categorizar apenas imagens e vídeos - resto vai para documentos
    imagens = [f for f in apenas_arquivos if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.hevc'))]
    videos = [f for f in apenas_arquivos if f.lower().endswith(('.mp4', '.webm', '.ogg', '.mov', '.heif'))]
    
    # TODOS os outros arquivos vão para documentos (sem filtro!)
    documentos = [f for f in apenas_arquivos if not f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.hevc', '.mp4', '.webm', '.ogg', '.mov', '.heif'))]
    
    response = make_response(render_template('galeria.html', pasta=pasta, imagens=imagens, videos=videos, subpastas=subpastas, documentos=documentos))
    
    # Evitar cache para sempre mostrar arquivos atualizados
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response


@app.route('/api/galeria_assinatura/', defaults={'pasta': ''})
@app.route('/api/galeria_assinatura/<path:pasta>')
def api_galeria_assinatura(pasta):
    """Retorna um 'hash' do conteúdo da pasta, usado pela galeria para detectar mudanças (upload/apagar) feitas por outro dispositivo e se atualizar sozinha."""
    caminho_pasta = resolver_caminho_seguro(pasta)
    if caminho_pasta is None or not os.path.exists(caminho_pasta):
        abort(404)

    entradas = []
    for nome in os.listdir(caminho_pasta):
        caminho = os.path.join(caminho_pasta, nome)
        try:
            info = os.stat(caminho)
            entradas.append(f"{nome}:{info.st_mtime_ns}:{info.st_size}:{os.path.isdir(caminho)}")
        except OSError:
            continue
    entradas.sort()

    assinatura = hashlib.md5('|'.join(entradas).encode('utf-8', 'surrogateescape')).hexdigest()
    return jsonify({'assinatura': assinatura})


@app.route('/media/<path:filepath>')
def media(filepath):
    caminho_arquivo = resolver_caminho_seguro(filepath)
    if caminho_arquivo is None or not os.path.exists(caminho_arquivo):
        abort(404)
    return send_from_directory(os.path.dirname(caminho_arquivo), os.path.basename(caminho_arquivo))

@app.route('/download_pasta/<path:pasta>')
def download_pasta(pasta):
    caminho_pasta = resolver_caminho_seguro(pasta)
    if caminho_pasta is None or not os.path.isdir(caminho_pasta):
        abort(404)

    # Cria um arquivo zip na memória
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(caminho_pasta):
            for file in files:
                caminho_arquivo = os.path.join(root, file)
                # Para manter a estrutura relativa dentro do zip
                arcname = os.path.relpath(caminho_arquivo, caminho_pasta)
                zipf.write(caminho_arquivo, arcname)
    memory_file.seek(0)

    nome_zip = f"{os.path.basename(caminho_pasta)}.zip"
    return send_file(memory_file, download_name=nome_zip, as_attachment=True)


@app.route('/criar_pasta/', defaults={'pasta': ''}, methods=['POST'])
@app.route('/criar_pasta/<path:pasta>', methods=['POST'])
def criar_pasta(pasta):
    nome_pasta = request.form.get('nome_pasta')

    if not nome_pasta:
        flash('Nome da pasta não pode ser vazio')
        return redirect(request.referrer)

    caminho_nova_pasta = resolver_caminho_seguro(os.path.join(pasta, nome_pasta) if pasta else nome_pasta)
    if caminho_nova_pasta is None:
        flash('Nome de pasta inválido.')
        return redirect(request.referrer)

    try:
        os.makedirs(caminho_nova_pasta, exist_ok=True)
        flash(f'Pasta "{nome_pasta}" criada com sucesso!')
    except Exception as e:
        flash(f'Erro ao criar pasta: {str(e)}')

    return redirect(request.referrer)


@app.route('/copiar/<path:filepath>', methods=['POST'])
def copiar(filepath):
    """Copia arquivo ou pasta para área de transferência."""
    caminho_origem = resolver_caminho_seguro(filepath)

    if caminho_origem is None or not os.path.exists(caminho_origem):
        flash('Arquivo ou pasta não encontrado.')
        return redirect(request.referrer)
    
    session['clipboard'] = {
        'path': filepath,
        'nome': os.path.basename(filepath),
        'tipo': 'pasta' if os.path.isdir(caminho_origem) else 'arquivo'
    }
    
    flash(f"{session['clipboard']['tipo'].capitalize()} '{session['clipboard']['nome']}' copiado.")
    return redirect(request.referrer)


@app.route('/colar', methods=['POST'])
def colar():
    """Cola item da área de transferência."""
    if 'clipboard' not in session:
        flash('Nada para colar.')
        return redirect(request.referrer)
    
    clip = session['clipboard']
    pasta_destino = request.form.get('pasta_destino', '')

    caminho_origem = resolver_caminho_seguro(clip['path'])
    nome_item = clip['nome']

    destino_relativo = os.path.join(pasta_destino, nome_item) if pasta_destino else nome_item
    caminho_destino = resolver_caminho_seguro(destino_relativo)

    if caminho_destino is None:
        flash('Pasta de destino inválida.')
        return redirect(request.referrer)

    if caminho_origem is None or not os.path.exists(caminho_origem):
        flash('Arquivo original não encontrado.')
        session.pop('clipboard', None)
        return redirect(request.referrer)

    if os.path.exists(caminho_destino):
        flash(f'Já existe um item com o nome "{nome_item}" no destino.')
        return redirect(request.referrer)
    
    try:
        if os.path.isdir(caminho_origem):
            shutil.copytree(caminho_origem, caminho_destino)
        else:
            shutil.copy2(caminho_origem, caminho_destino)
        
        flash(f'{clip["tipo"].capitalize()} "{nome_item}" colado com sucesso!')
    except Exception as e:
        flash(f'Erro ao colar: {str(e)}')
    
    return redirect(request.referrer)


@app.route('/apagar_pasta/<path:pasta>', methods=['POST'])
def apagar_pasta(pasta):
    caminho_pasta = resolver_caminho_seguro(pasta)

    if caminho_pasta is None or not os.path.isdir(caminho_pasta):
        flash('Pasta não encontrada.')
        return redirect(request.referrer)

    try:
        shutil.rmtree(caminho_pasta)
        flash(f'Pasta "{os.path.basename(pasta)}" apagada com sucesso!')
    except Exception as e:
        flash(f'Erro ao apagar pasta: {str(e)}')

    # Voltar para a pasta anterior (onde estava a pasta apagada)
    pasta_anterior = os.path.dirname(pasta)
    return redirect(url_for('galeria', pasta=pasta_anterior) if pasta_anterior else url_for('galeria'))

@app.route('/apagar_arquivo/<path:filepath>', methods=['POST'])
def apagar_arquivo(filepath):
    caminho_arquivo = resolver_caminho_seguro(filepath)

    if caminho_arquivo is None or not os.path.isfile(caminho_arquivo):
        flash('Arquivo não encontrado.')
        return redirect(request.referrer)

    try:
        os.remove(caminho_arquivo)
        flash(f'Arquivo "{os.path.basename(filepath)}" apagado com sucesso!')
    except Exception as e:
        flash(f'Erro ao apagar arquivo: {str(e)}')

    # Voltar para a galeria da pasta atual
    pasta_atual = os.path.dirname(filepath)
    return redirect(url_for('galeria', pasta=pasta_atual) if pasta_atual else url_for('galeria'))


@app.route('/apagar_multiplos', methods=['POST'])
def apagar_multiplos():
    """Apaga múltiplos arquivos e pastas selecionados"""
    arquivos_selecionados = request.form.getlist('arquivos_selecionados')
    pasta_atual = request.form.get('pasta_atual', '')
    
    if not arquivos_selecionados:
        flash('Nenhum arquivo selecionado para apagar.')
        return redirect(request.referrer)
    
    apagados = []
    erros = []
    
    for arquivo_path in arquivos_selecionados:
        try:
            caminho_completo = resolver_caminho_seguro(arquivo_path)

            if caminho_completo is None:
                erros.append(f'❌ {os.path.basename(arquivo_path)} (caminho inválido)')
            elif os.path.exists(caminho_completo):
                if os.path.isdir(caminho_completo):
                    shutil.rmtree(caminho_completo)
                    apagados.append(f'📁 {os.path.basename(arquivo_path)}')
                else:
                    os.remove(caminho_completo)
                    apagados.append(f'📄 {os.path.basename(arquivo_path)}')
            else:
                erros.append(f'❌ {os.path.basename(arquivo_path)} (não encontrado)')
                
        except Exception as e:
            erros.append(f'❌ {os.path.basename(arquivo_path)} (erro: {str(e)})')
    
    # Mensagens de resultado
    if apagados:
        flash(f'✅ Apagados com sucesso: {", ".join(apagados)}')
    
    if erros:
        flash(f'⚠️ Erros: {", ".join(erros)}')
    
    # Redirecionar para a galeria da pasta atual
    return redirect(url_for('galeria', pasta=pasta_atual) if pasta_atual else url_for('galeria'))


@app.route('/api/busca_global')
def busca_global():
    termo = request.args.get('q', '').lower()
    if not termo:
        return jsonify([])
    
    resultados = []
    
    # Buscar em toda a estrutura de pastas
    for root, dirs, files in os.walk(MEDIA_FOLDER):
        # Calcular caminho relativo
        pasta_relativa = os.path.relpath(root, MEDIA_FOLDER)
        if pasta_relativa == '.':
            pasta_relativa = ''
        
        # Buscar em pastas
        for pasta in dirs:
            if termo in pasta.lower():
                caminho_pasta = os.path.join(pasta_relativa, pasta) if pasta_relativa else pasta
                resultados.append({
                    'nome': pasta,
                    'tipo': 'pasta',
                    'caminho': caminho_pasta,
                    'url': url_for('galeria', pasta=caminho_pasta)
                })
        
        # Buscar em arquivos
        for arquivo in files:
            if termo in arquivo.lower():
                caminho_arquivo = os.path.join(pasta_relativa, arquivo) if pasta_relativa else arquivo
                
                # Determinar tipo do arquivo
                ext = arquivo.lower().split('.')[-1] if '.' in arquivo else ''
                if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'hevc']:
                    tipo = 'imagem'
                elif ext in ['mp4', 'webm', 'ogg', 'mov', 'heif']:
                    tipo = 'video'
                elif ext in ['pdf', 'txt', 'doc', 'docx', 'html', 'py', 'md', 'xml', 'zip']:
                    tipo = 'documento'
                else:
                    tipo = 'arquivo'
                
                resultados.append({
                    'nome': arquivo,
                    'tipo': tipo,
                    'caminho': caminho_arquivo,
                    'pasta': pasta_relativa,
                    'url': url_for('galeria', pasta=pasta_relativa) if pasta_relativa else url_for('galeria')
                })
    
    # Limitar resultados para evitar sobrecarga
    return jsonify(resultados[:50])


@app.route('/api/listar_pastas')
def listar_pastas():
    """Retorna lista de todas as pastas disponíveis para mover arquivos"""
    try:
        pastas = []
        
        # Verificar se MEDIA_FOLDER existe
        if not os.path.exists(MEDIA_FOLDER):
            return jsonify([{'nome': 'Raiz', 'caminho': '', 'nivel': -1}])
        
        # Adicionar pasta raiz primeiro
        pastas.append({'nome': 'Raiz', 'caminho': '', 'nivel': -1})
        
        # Percorrer todas as pastas
        for root, dirs, files in os.walk(MEDIA_FOLDER):
            pasta_relativa = os.path.relpath(root, MEDIA_FOLDER)
            if pasta_relativa == '.':
                pasta_relativa = ''
            
            # Adicionar subpastas da pasta atual
            for pasta in dirs:
                if pasta_relativa:
                    caminho_completo = f"{pasta_relativa}/{pasta}".replace('\\', '/')
                else:
                    caminho_completo = pasta
                
                nivel = caminho_completo.count('/')
                
                pastas.append({
                    'nome': pasta,
                    'caminho': caminho_completo,
                    'nivel': nivel
                })
        
        # Ordenar por caminho para manter hierarquia
        pastas_ordenadas = [pastas[0]]  # Manter raiz no início
        outras_pastas = sorted(pastas[1:], key=lambda x: x['caminho'])
        pastas_ordenadas.extend(outras_pastas)
        
        return jsonify(pastas_ordenadas)
        
    except Exception as e:
        logger.error(f"Erro ao listar pastas: {e}")
        return jsonify([{'nome': 'Raiz', 'caminho': '', 'nivel': -1}]), 500


@app.route('/mover_arquivo/<path:filepath>', methods=['POST'])
def mover_arquivo(filepath):
    """Move um arquivo ou pasta para outra pasta"""
    pasta_destino = request.form.get('pasta_destino', '')

    # Caminhos de origem e destino
    caminho_origem = resolver_caminho_seguro(filepath)
    nome_item = os.path.basename(filepath)

    destino_relativo = os.path.join(pasta_destino, nome_item) if pasta_destino else nome_item
    caminho_destino = resolver_caminho_seguro(destino_relativo)

    if caminho_destino is None:
        flash('Pasta de destino inválida.')
        return redirect(request.referrer)

    # Verificar se arquivo/pasta existe
    if caminho_origem is None or not os.path.exists(caminho_origem):
        flash('Arquivo ou pasta não encontrado.')
        return redirect(request.referrer)
    
    # Verificar se pasta destino existe
    pasta_destino_dir = os.path.dirname(caminho_destino)
    if not os.path.exists(pasta_destino_dir):
        flash('Pasta de destino não encontrada.')
        return redirect(request.referrer)
    
    # Verificar se já existe item com mesmo nome no destino
    if os.path.exists(caminho_destino):
        tipo_item = 'pasta' if os.path.isdir(caminho_origem) else 'arquivo'
        flash(f'Já existe um {tipo_item} com o nome "{nome_item}" na pasta de destino.')
        return redirect(request.referrer)
    
    # Verificar se não está tentando mover uma pasta para dentro dela mesma
    if os.path.isdir(caminho_origem):
        caminho_origem_abs = os.path.abspath(caminho_origem)
        caminho_destino_abs = os.path.abspath(caminho_destino)
        if caminho_destino_abs.startswith(caminho_origem_abs + os.sep):
            flash('Não é possível mover uma pasta para dentro dela mesma.')
            return redirect(request.referrer)
    
    try:
        shutil.move(caminho_origem, caminho_destino)
        pasta_destino_nome = os.path.basename(pasta_destino) if pasta_destino else 'Raiz'
        tipo_item = 'Pasta' if os.path.isdir(caminho_destino) else 'Arquivo'
        flash(f'{tipo_item} "{nome_item}" movido para "{pasta_destino_nome}" com sucesso!')
    except Exception as e:
        flash(f'Erro ao mover: {str(e)}')
    
    return redirect(request.referrer)


def salvar_anexos_pdf(conn, texto_id, arquivos):
    """Salva os PDFs enviados para um texto rápido e registra no banco. Retorna a quantidade salva."""
    salvos = 0
    for f in arquivos:
        if not f or not f.filename:
            continue
        if not f.filename.lower().endswith('.pdf'):
            continue

        pasta_texto = os.path.join(TEXTOS_ANEXOS_FOLDER, str(texto_id))
        os.makedirs(pasta_texto, exist_ok=True)

        nome_original = secure_filename(f.filename)
        nome_arquivo = f"{uuid.uuid4().hex}.pdf"
        f.save(os.path.join(pasta_texto, nome_arquivo))

        conn.execute(
            'INSERT INTO textos_anexos (texto_id, nome_arquivo, nome_original) VALUES (?, ?, ?)',
            (texto_id, nome_arquivo, nome_original)
        )
        salvos += 1
    return salvos


@app.route('/api/textos_contagem')
def api_textos_contagem():
    """Retorna quantos textos rápidos foram criados desde um timestamp, para notificação em tempo real na galeria."""
    desde = request.args.get('desde', '')
    conn = get_db_connection()
    if desde:
        novos = conn.execute('SELECT COUNT(*) AS c FROM textos_rapidos WHERE criado_em > ?', (desde,)).fetchone()['c']
    else:
        novos = 0
    ultimo = conn.execute('SELECT criado_em FROM textos_rapidos ORDER BY id DESC LIMIT 1').fetchone()
    conn.close()
    return jsonify({'novos': novos, 'ultimo_criado_em': ultimo['criado_em'] if ultimo else None})


@app.route('/textos/')
def textos_lista():
    conn = get_db_connection()
    textos = conn.execute('''
        SELECT t.id, t.titulo, t.conteudo, t.criado_em, COUNT(a.id) AS num_anexos
        FROM textos_rapidos t
        LEFT JOIN textos_anexos a ON a.texto_id = t.id
        GROUP BY t.id
        ORDER BY t.id DESC
    ''').fetchall()
    conn.close()
    return render_template('textos_lista.html', textos=textos)


@app.route('/api/textos_lista')
def api_textos_lista():
    """Lista de textos rápidos em JSON, usada pela página /textos/ para se atualizar sozinha."""
    conn = get_db_connection()
    textos = conn.execute('''
        SELECT t.id, t.titulo, t.conteudo, t.criado_em, COUNT(a.id) AS num_anexos
        FROM textos_rapidos t
        LEFT JOIN textos_anexos a ON a.texto_id = t.id
        GROUP BY t.id
        ORDER BY t.id DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(t) for t in textos])


@app.route('/textos/novo', methods=['GET', 'POST'])
def textos_novo():
    if request.method == 'POST':
        conteudo = request.form.get('conteudo', '').strip()
        if not conteudo:
            flash('O texto não pode ser vazio.')
            return redirect(url_for('textos_novo'))

        primeira_linha = next((l.strip() for l in conteudo.splitlines() if l.strip()), 'Texto sem título')
        titulo = primeira_linha[:80]

        conn = get_db_connection()
        cursor = conn.execute(
            'INSERT INTO textos_rapidos (titulo, conteudo, atualizado_em) VALUES (?, ?, CURRENT_TIMESTAMP)',
            (titulo, conteudo)
        )
        novo_id = cursor.lastrowid

        salvar_anexos_pdf(conn, novo_id, request.files.getlist('anexos'))

        conn.commit()
        conn.close()

        return redirect(url_for('textos_ver', id=novo_id))

    return render_template('textos_form.html')


@app.route('/textos/<int:id>/editar', methods=['GET', 'POST'])
def textos_editar(id):
    conn = get_db_connection()
    texto = conn.execute('SELECT * FROM textos_rapidos WHERE id = ?', (id,)).fetchone()
    if not texto:
        conn.close()
        abort(404)

    if request.method == 'POST':
        conteudo = request.form.get('conteudo', '').strip()
        if not conteudo:
            conn.close()
            flash('O texto não pode ser vazio.')
            return redirect(url_for('textos_editar', id=id))

        primeira_linha = next((l.strip() for l in conteudo.splitlines() if l.strip()), 'Texto sem título')
        titulo = primeira_linha[:80]

        conn.execute(
            'UPDATE textos_rapidos SET titulo = ?, conteudo = ?, atualizado_em = CURRENT_TIMESTAMP WHERE id = ?',
            (titulo, conteudo, id)
        )

        salvar_anexos_pdf(conn, id, request.files.getlist('anexos'))

        conn.commit()
        conn.close()

        return redirect(url_for('textos_ver', id=id))

    conn.close()
    return render_template('textos_form.html', texto=texto)


@app.route('/textos/<int:id>')
def textos_ver(id):
    conn = get_db_connection()
    texto = conn.execute('SELECT * FROM textos_rapidos WHERE id = ?', (id,)).fetchone()
    if not texto:
        conn.close()
        abort(404)

    anexos = conn.execute('SELECT * FROM textos_anexos WHERE texto_id = ? ORDER BY id', (id,)).fetchall()
    conn.close()

    return render_template('textos_ver.html', texto=texto, anexos=anexos, conteudo_formatado=destacar_texto(texto['conteudo']))


@app.route('/api/textos/<int:id>/anexos')
def api_textos_anexos(id):
    """Lista de anexos de um texto em JSON, usada pela página /textos/<id> para se atualizar sozinha quando um anexo é enviado/apagado por outro dispositivo."""
    conn = get_db_connection()
    texto = conn.execute('SELECT id FROM textos_rapidos WHERE id = ?', (id,)).fetchone()
    if not texto:
        conn.close()
        abort(404)

    anexos = conn.execute('SELECT id, nome_original FROM textos_anexos WHERE texto_id = ? ORDER BY id', (id,)).fetchall()
    conn.close()
    return jsonify([dict(a) for a in anexos])


@app.route('/api/textos/<int:id>/versao')
def api_textos_versao(id):
    """Retorna quando o texto foi editado pela última vez, usado pela página /textos/<id>
    para avisar quando outro dispositivo edita o mesmo texto enquanto está aberto."""
    conn = get_db_connection()
    texto = conn.execute('SELECT atualizado_em FROM textos_rapidos WHERE id = ?', (id,)).fetchone()
    conn.close()
    if not texto:
        abort(404)
    return jsonify({'atualizado_em': texto['atualizado_em']})


@app.route('/textos/<int:id>/anexo', methods=['POST'])
def textos_anexo_add(id):
    conn = get_db_connection()
    texto = conn.execute('SELECT id FROM textos_rapidos WHERE id = ?', (id,)).fetchone()
    if not texto:
        conn.close()
        abort(404)

    salvos = salvar_anexos_pdf(conn, id, request.files.getlist('anexos'))
    conn.commit()
    conn.close()

    if salvos:
        flash(f'{salvos} PDF(s) anexado(s) com sucesso.')
    else:
        flash('Nenhum PDF válido foi enviado.')

    return redirect(url_for('textos_ver', id=id))


@app.route('/textos/anexo/<int:anexo_id>')
def textos_anexo_ver(anexo_id):
    conn = get_db_connection()
    anexo = conn.execute('SELECT * FROM textos_anexos WHERE id = ?', (anexo_id,)).fetchone()
    conn.close()

    if not anexo:
        abort(404)

    pasta_texto = os.path.join(TEXTOS_ANEXOS_FOLDER, str(anexo['texto_id']))
    return send_from_directory(pasta_texto, anexo['nome_arquivo'])


@app.route('/textos/anexo/<int:anexo_id>/download')
def textos_anexo_download(anexo_id):
    conn = get_db_connection()
    anexo = conn.execute('SELECT * FROM textos_anexos WHERE id = ?', (anexo_id,)).fetchone()
    conn.close()

    if not anexo:
        abort(404)

    pasta_texto = os.path.join(TEXTOS_ANEXOS_FOLDER, str(anexo['texto_id']))
    return send_from_directory(pasta_texto, anexo['nome_arquivo'], as_attachment=True, download_name=anexo['nome_original'])


@app.route('/textos/anexo/<int:anexo_id>/apagar', methods=['POST'])
def textos_anexo_apagar(anexo_id):
    conn = get_db_connection()
    anexo = conn.execute('SELECT * FROM textos_anexos WHERE id = ?', (anexo_id,)).fetchone()
    if not anexo:
        conn.close()
        abort(404)

    texto_id = anexo['texto_id']
    caminho_arquivo = os.path.join(TEXTOS_ANEXOS_FOLDER, str(texto_id), anexo['nome_arquivo'])
    if os.path.exists(caminho_arquivo):
        os.remove(caminho_arquivo)

    conn.execute('DELETE FROM textos_anexos WHERE id = ?', (anexo_id,))
    conn.commit()
    conn.close()

    flash('Anexo removido.')
    return redirect(url_for('textos_ver', id=texto_id))


@app.route('/textos/<int:id>/apagar', methods=['POST'])
def textos_apagar(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM textos_rapidos WHERE id = ?', (id,))
    conn.execute('DELETE FROM textos_anexos WHERE texto_id = ?', (id,))
    conn.commit()
    conn.close()

    pasta_texto = os.path.join(TEXTOS_ANEXOS_FOLDER, str(id))
    if os.path.exists(pasta_texto):
        shutil.rmtree(pasta_texto, ignore_errors=True)

    flash('Texto apagado com sucesso.')
    return redirect(url_for('textos_lista'))


def registrar_mdns(ip_str):
    global servico_mdns
    ip_bytes = socket.inet_aton(ip_str)
    if servico_mdns:
        try:
            zeroconf.unregister_service(servico_mdns)
        except Exception as e:
            logger.warning(f"⚠️ Erro ao remover mDNS antigo: {e}")
    dominio = obter_mdns_dominio()
    servico_mdns = ServiceInfo(
        "_http._tcp.local.",
        obter_mdns_servico_nome(),
        addresses=[ip_bytes],
        port=porta,
        properties={},
        server=dominio,
    )
    zeroconf.register_service(servico_mdns)
    logger.info(f"🔗 mDNS registrado: http://{obter_mdns_host()}:{porta}")


@app.before_request
def before_request():
    """Registrar acesso antes de cada requisição"""
    registrar_acesso(obter_ip_cliente(request), contar_como_acesso=request.endpoint not in ENDPOINTS_POLLING)


# Endpoints de polling automático — a própria página se atualizando sozinha em
# segundo plano (estatísticas da GUI a cada 3s, galeria/lista de textos
# checando se algo mudou). Continuam mantendo o dispositivo como "conectado"
# (é atividade de verdade), mas não entram no contador de "acessos hoje" — só
# inflariam o número sem representar uma visita de verdade.
ENDPOINTS_POLLING = {
    'api_stats', 'api_galeria_assinatura', 'api_textos_contagem',
    'api_textos_lista', 'api_textos_anexos', 'api_textos_versao',
}


# Endpoints acessíveis sem estar logado: as próprias telas de login/configuração
# inicial, os dois assets fixos (logo e QR code) que elas precisam carregar, e
# api_stats (a janela tkinter consulta essa rota localmente, sem sessão, pra
# mostrar tempo ativo/dispositivos/acessos/rede — só dados agregados, nenhum
# arquivo ou conteúdo pessoal, por isso é seguro deixar aberta).
# Note que NÃO inclui o endpoint 'static' genérico do Flask — ele foi
# desativado de propósito (static_folder=None) porque MEDIA_FOLDER mora dentro
# de static/, e deixar o endpoint automático ligado exporia todos os arquivos
# do usuário sem autenticação nenhuma.
ENDPOINTS_ISENTOS = {'login', 'setup', 'static_logo', 'static_qrcode', 'api_stats'}


@app.before_request
def exigir_autenticacao():
    if request.endpoint in ENDPOINTS_ISENTOS or request.endpoint is None:
        return

    if not senha_esta_configurada():
        if request.endpoint != 'setup':
            return redirect(url_for('setup'))
        return

    if not session.get('autenticado'):
        if request.path.startswith('/api/'):
            return jsonify({'erro': 'nao_autenticado'}), 401
        if request.endpoint != 'login':
            return redirect(url_for('login', next=request.path))
        return


def _destino_pos_login(bruto):
    """Só aceita caminhos internos (evita open-redirect via ?next=http://...)."""
    if bruto and bruto.startswith('/') and not bruto.startswith('//'):
        return bruto
    return url_for('index')


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if senha_esta_configurada():
        return redirect(url_for('login'))

    if request.method == 'POST':
        senha = request.form.get('senha', '')
        confirmacao = request.form.get('confirmacao', '')

        if not senha or len(senha) < 4:
            flash('A senha precisa ter pelo menos 4 caracteres.')
            return redirect(url_for('setup'))
        if senha != confirmacao:
            flash('As senhas não coincidem.')
            return redirect(url_for('setup'))

        definir_senha(senha)
        session['autenticado'] = True
        session.permanent = True
        flash('Senha definida com sucesso!')
        return redirect(url_for('index'))

    return render_template('login.html', modo='setup')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        ip_cliente = obter_ip_cliente(request)

        if ip_esta_bloqueado(ip_cliente):
            flash('Muitas tentativas seguidas. Aguarde alguns minutos e tente de novo.')
            return redirect(url_for('login'))

        senha = request.form.get('senha', '')
        if verificar_senha(senha):
            limpar_tentativas(ip_cliente)
            session['autenticado'] = True
            session.permanent = True
            return redirect(_destino_pos_login(request.form.get('next')))

        registrar_tentativa_falha(ip_cliente)
        flash('Senha incorreta.')
        return redirect(url_for('login', next=request.form.get('next', '')))

    return render_template('login.html', modo='login', next=request.args.get('next', ''))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/trocar_senha', methods=['GET', 'POST'])
def trocar_senha():
    if request.method == 'POST':
        senha_atual = request.form.get('senha_atual', '')
        nova_senha = request.form.get('senha', '')
        confirmacao = request.form.get('confirmacao', '')

        if not verificar_senha(senha_atual):
            flash('Senha atual incorreta.')
            return redirect(url_for('trocar_senha'))
        if not nova_senha or len(nova_senha) < 4:
            flash('A nova senha precisa ter pelo menos 4 caracteres.')
            return redirect(url_for('trocar_senha'))
        if nova_senha != confirmacao:
            flash('As senhas não coincidem.')
            return redirect(url_for('trocar_senha'))

        definir_senha(nova_senha)
        flash('Senha alterada com sucesso!')
        return redirect(url_for('index'))

    return render_template('login.html', modo='trocar_senha')


@app.route('/configuracoes', methods=['GET', 'POST'])
def configuracoes():
    if request.method == 'POST':
        nome = request.form.get('mdns_nome', '').strip().lower()

        if not mdns_nome_valido(nome):
            flash('Nome inválido. Use só letras minúsculas, números e hífen, começando e terminando com letra ou número (até 63 caracteres).')
            return redirect(url_for('configuracoes'))

        definir_mdns_nome(nome)
        # Reaplica o mDNS na hora com o novo nome, sem precisar reiniciar o servidor.
        if ip_atual:
            registrar_mdns(ip_atual)
        flash('Nome atualizado! Já está em uso na rede.')
        return redirect(url_for('configuracoes'))

    return render_template(
        'configuracoes.html',
        mdns_nome=obter_mdns_nome(),
        mdns_dominio=obter_mdns_host(),
        porta=porta,
    )


def monitorar_ip_e_registrar():
    global ip_atual
    while True:
        novo_ip = obter_endereco_ip(False)
        if novo_ip != ip_atual:
            ip_atual = novo_ip
            registrar_mdns(novo_ip)
            criar_qrcode_simples()
        time.sleep(5)


def run_console_mode():
    """Executar em modo console (sem GUI)"""
    init_app()
    logger.info("🚀 FileSwift - Gerenciador de Arquivos Web")
    logger.info("=" * 50)
    logger.info("⏳ Iniciando servidor...")
    
    threading.Thread(target=monitorar_ip_e_registrar, daemon=True).start()
    
    # Aguardar um pouco para o mDNS se registrar
    time.sleep(2)
    
    endereco = obter_endereco_ip(True)
    url = f"http://{endereco}"
    
    logger.info("✅ Servidor iniciado com sucesso!")
    logger.info(f"🌐 Acesse: {url}")
    logger.info(f"📱 QR Code: static/qrcode.png")
    logger.info(f"🔗 mDNS: http://{obter_mdns_host()}:{porta}")
    logger.info("=" * 50)
    logger.info("🌐 Abrindo navegador automaticamente...")
    
    # Abrir navegador
    webbrowser.open(url)
    
    # Iniciar servidor (waitress: werkzeug é só um servidor de desenvolvimento,
    # não deve ser usado nem em modo --console)
    try:
        waitress.serve(app, host="0.0.0.0", port=porta)
    except KeyboardInterrupt:
        logger.info("\n👋 FileSwift encerrado pelo usuário")
    except Exception as e:
        logger.error(f"❌ Erro no servidor: {e}")


@app.route('/api/stats')
def api_stats():
    """API para obter estatísticas do servidor"""
    return jsonify(obter_estatisticas_servidor())


if __name__ == '__main__':
    import sys

    # Verificar se deve usar GUI ou console
    if len(sys.argv) > 1 and sys.argv[1] == '--console':
        run_console_mode()
    else:
        # Tentar importar GUI
        try:
            from gui_launcher import FileSwiftGUI
            logger.info("🚀 Iniciando FileSwift com interface gráfica...")
            gui = FileSwiftGUI()
            gui.run()
        except ImportError as e:
            logger.warning(f"⚠️  GUI não disponível ({e})")
            logger.info("🔄 Executando em modo console...")
            run_console_mode()
        except Exception as e:
            logger.error(f"❌ Erro na GUI: {e}")
            logger.info("🔄 Executando em modo console...")
            run_console_mode()