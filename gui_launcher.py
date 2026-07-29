import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser
import os
import sys
import time
import requests
from PIL import Image, ImageTk
import qrcode
import io
import socket
import subprocess
import signal
from main import app, porta, obter_endereco_ip, criar_qrcode_simples, monitorar_ip_e_registrar, obter_mdns_host

class FileSwiftGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FileSwift - Gerenciador de Arquivos Web")
        
        # Configurar cores e estilo moderno
        self.colors = {
            'bg': '#1a1a2e',
            'bg2': '#16213e',
            'bg3': '#0f3460',
            'accent': '#e94560',
            'accent2': '#533483',
            'text': '#ffffff',
            'text2': '#b0b0b0',
            'success': '#4ade80',
            'warning': '#fbbf24',
            'error': '#f87171',
            'blue': '#60a5fa'  # Azul usado no link
        }
        
        # Altura inicial respeita o tamanho real da tela
        screen_height = self.root.winfo_screenheight()
        altura_inicial = min(900, max(550, screen_height - 100))
        self.root.geometry(f"650x{altura_inicial}")
        self.root.resizable(True, True)
        self.root.minsize(600, 450)
        
        # Configurar ícone se existir
        try:
            icon_path = os.path.join(os.path.dirname(__file__), 'static', 'logo.png')
            if os.path.exists(icon_path):
                self.root.iconphoto(False, tk.PhotoImage(file=icon_path))
        except:
            pass
        
        # Variáveis de controle
        self.servidor_rodando = False
        self.flask_thread = None
        self.monitor_thread = None
        self.url_atual = ""
        self.flask_server = None
        
        # Configurar estilo
        self.setup_style()
        
        # Criar interface
        self.create_widgets()
        
        # Centralizar janela
        self.center_window()
        
        # Configurar evento de fechamento da janela
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Iniciar servidor automaticamente
        self.root.after(1000, self.iniciar_servidor)
    
    def setup_style(self):
        """Configurar estilo da interface com tema moderno"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar cores do tema
        bg = self.colors['bg']
        bg2 = self.colors['bg2']
        bg3 = self.colors['bg3']
        accent = self.colors['accent']
        text = self.colors['text']
        blue = self.colors['blue']
        
        # Estilo para frames
        style.configure('Modern.TFrame', background=bg)
        style.configure('Dark.TFrame', background=bg2)
        style.configure('Card.TFrame', background=bg3)
        
        # Estilo para labels
        style.configure('Title.TLabel', 
                       font=('Segoe UI', 24, 'bold'), 
                       foreground=text,
                       background=bg)
        style.configure('Subtitle.TLabel', 
                       font=('Segoe UI', 12), 
                       foreground=self.colors['text2'],
                       background=bg)
        style.configure('Status.TLabel', 
                       font=('Segoe UI', 11), 
                       foreground=self.colors['success'],
                       background=bg2)
        style.configure('URL.TLabel', 
                       font=('Segoe UI', 12, 'bold'), 
                       foreground=blue,  # Usando a cor azul
                       background=bg2)
        style.configure('Info.TLabel', 
                       font=('Segoe UI', 9), 
                       foreground=self.colors['text2'],
                       background=bg2)
        style.configure('Stat.TLabel', 
                       font=('Segoe UI', 10), 
                       foreground=text,
                       background=bg3)
        
        # Estilo para botões - maiores e mais modernos
        style.configure('Action.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 12),
                       background=accent,
                       foreground='white',
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Action.TButton',
                 background=[('active', '#c73550'), ('pressed', '#b02e45')],
                 foreground=[('active', 'white'), ('pressed', 'white')])
        
        # NOVO: Estilo azul para o botão Copiar URL (mesma cor do link)
        style.configure('Blue.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 12),
                       background=blue,  # Usando a mesma cor azul do link
                       foreground='white',
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Blue.TButton',
                 background=[('active', '#3b82f6'), ('pressed', '#2563eb')],
                 foreground=[('active', 'white'), ('pressed', 'white')])
        
        style.configure('Success.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 12),
                       background='#22c55e',
                       foreground='white',
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Success.TButton',
                 background=[('active', '#16a34a'), ('pressed', '#15803d')])
        
        style.configure('Danger.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 12),
                       background='#ef4444',
                       foreground='white',
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Danger.TButton',
                 background=[('active', '#dc2626'), ('pressed', '#b91c1c')])
        
        style.configure('Warning.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 12),
                       background='#f59e0b',
                       foreground='white',
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Warning.TButton',
                 background=[('active', '#d97706'), ('pressed', '#b45309')])

        # Estilo cinza-azulado para o botão Configurações (diferente do azul do Copiar URL)
        style.configure('Settings.TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=(20, 12),
                       background='#64748b',
                       foreground='white',
                       borderwidth=0,
                       focusthickness=0,
                       focuscolor='none')
        style.map('Settings.TButton',
                 background=[('active', '#475569'), ('pressed', '#334155')],
                 foreground=[('active', 'white'), ('pressed', 'white')])

        # Estilo para LabelFrame
        style.configure('Card.TLabelframe',
                       background=bg2,
                       foreground=text,
                       borderwidth=2,
                       relief='flat')
        style.configure('Card.TLabelframe.Label',
                       font=('Segoe UI', 11, 'bold'),
                       foreground=text,
                       background=bg2)
        
        # Estilo para progressbar
        style.configure('Modern.Horizontal.TProgressbar',
                       background=accent,
                       troughcolor=bg3,
                       borderwidth=0,
                       lightcolor=accent,
                       darkcolor=accent)
        
        # Estilo para scrollbar
        style.configure('Modern.Vertical.TScrollbar',
                       background=bg3,
                       troughcolor=bg,
                       borderwidth=0,
                       arrowsize=13)
    
    def create_widgets(self):
        """Criar todos os widgets da interface com design moderno"""
        # Container principal com scroll
        container = ttk.Frame(self.root, style='Modern.TFrame')
        container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0,
                          bg=self.colors['bg'])
        scrollbar = ttk.Scrollbar(container, orient="vertical", 
                                 command=canvas.yview,
                                 style='Modern.Vertical.TScrollbar')
        canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Frame principal
        main_frame = ttk.Frame(canvas, style='Modern.TFrame', padding="20")
        canvas_window = canvas.create_window((0, 0), window=main_frame, anchor="nw")
        
        def _atualizar_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        
        def _ajustar_largura_conteudo(event):
            canvas.itemconfig(canvas_window, width=event.width)
        
        main_frame.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura_conteudo)
        
        def _rolar_mouse(event):
            if event.num == 5 or event.delta < 0:
                canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-1, "units")
        
        canvas.bind_all("<MouseWheel>", _rolar_mouse)
        canvas.bind_all("<Button-4>", _rolar_mouse)
        canvas.bind_all("<Button-5>", _rolar_mouse)
        
        # ===== TÍTULO =====
        title_frame = ttk.Frame(main_frame, style='Modern.TFrame')
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Emoji/Ícone grande
        icon_label = tk.Label(title_frame, text="🚀", 
                            font=('Segoe UI', 48),
                            bg=self.colors['bg'],
                            fg=self.colors['accent'])
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        title_container = ttk.Frame(title_frame, style='Modern.TFrame')
        title_container.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        title_label = ttk.Label(title_container, text="FileSwift", style='Title.TLabel')
        title_label.pack(anchor='w')
        
        subtitle_label = ttk.Label(title_container, text="Gerenciador de Arquivos Web", 
                                 style='Subtitle.TLabel')
        subtitle_label.pack(anchor='w')
        
        # ===== STATUS DO SERVIDOR =====
        status_frame = ttk.LabelFrame(main_frame, text=" Status do Servidor ", 
                                     style='Card.TLabelframe', padding="15")
        status_frame.pack(fill=tk.X, pady=(0, 15))
        
        status_content = ttk.Frame(status_frame, style='Dark.TFrame')
        status_content.pack(fill=tk.X)
        
        self.status_label = ttk.Label(status_content, text="⏳ Iniciando servidor...", 
                                    style='Status.TLabel')
        self.status_label.pack(pady=(0, 10))
        
        self.progress = ttk.Progressbar(status_content, mode='indeterminate',
                                       style='Modern.Horizontal.TProgressbar')
        self.progress.pack(fill=tk.X, pady=(5, 0))
        
        # ===== URL DE ACESSO =====
        url_frame = ttk.LabelFrame(main_frame, text=" 🌐 Acesso ao FileSwift ", 
                                  style='Card.TLabelframe', padding="15")
        url_frame.pack(fill=tk.X, pady=(0, 15))
        
        self.url_label = ttk.Label(url_frame, text="Aguardando servidor...",
                                 style='URL.TLabel')
        self.url_label.pack(pady=(0, 4))

        self.mdns_label = ttk.Label(url_frame, text="", style='Info.TLabel')
        self.mdns_label.pack(pady=(0, 15))
        
        # Botões de ação - maiores
        button_container = ttk.Frame(url_frame, style='Dark.TFrame')
        button_container.pack(fill=tk.X)
        
        self.open_browser_btn = ttk.Button(button_container, text="🌐 Abrir Navegador", 
                                         command=self.abrir_navegador, 
                                         style='Success.TButton',
                                         state='disabled')
        self.open_browser_btn.pack(side=tk.LEFT, padx=(0, 10), expand=True, fill=tk.X)
        
        # ALTERAÇÃO: Botão Copiar URL agora usa o estilo 'Blue.TButton'
        self.copy_url_btn = ttk.Button(button_container, text="📋 Copiar URL", 
                                     command=self.copiar_url, 
                                     style='Blue.TButton',  # Mudança aqui
                                     state='disabled')
        self.copy_url_btn.pack(side=tk.LEFT, expand=True, fill=tk.X)

        self.config_btn = ttk.Button(button_container, text="⚙️ Configurações",
                                   command=self.abrir_configuracoes,
                                   style='Settings.TButton',
                                   state='disabled')
        self.config_btn.pack(side=tk.LEFT, padx=(10, 0), expand=True, fill=tk.X)

        # ===== QR CODE =====
        qr_frame = ttk.LabelFrame(main_frame, text=" 📱 QR Code - Acesso Móvel ", 
                                 style='Card.TLabelframe', padding="15")
        qr_frame.pack(fill=tk.X, pady=(0, 15))
        
        qr_container = ttk.Frame(qr_frame, style='Dark.TFrame')
        qr_container.pack()
        
        self.qr_label = ttk.Label(qr_container, text="QR Code será gerado após inicialização...", 
                                 style='Info.TLabel')
        self.qr_label.pack(pady=10)
        
        # ===== INFORMAÇÕES =====
        info_frame = ttk.LabelFrame(main_frame, text=" ℹ️ Informações ", 
                                   style='Card.TLabelframe', padding="12")
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        info_text = f"""📁 Pasta: static/download/\n🌐 Rede local\n📱 QR Code móvel\n🔄 mDNS: {obter_mdns_host()}"""
        self.info_label = ttk.Label(info_frame, text=info_text, style='Info.TLabel',
                             justify=tk.LEFT)
        self.info_label.pack(anchor='w')

        # ===== ESTATÍSTICAS =====
        stats_frame = ttk.LabelFrame(main_frame, text=" 📊 Atividade do Servidor ", 
                                    style='Card.TLabelframe', padding="15")
        stats_frame.pack(fill=tk.X, pady=(0, 15))
        
        stats_grid = ttk.Frame(stats_frame, style='Dark.TFrame')
        stats_grid.pack(fill=tk.X)
        
        # Grid 2x2 para estatísticas
        self.tempo_ativo_label = ttk.Label(stats_grid, text="🌐 Ativo há: 00:00:00", 
                                         style='Stat.TLabel')
        self.tempo_ativo_label.grid(row=0, column=0, sticky='w', pady=5, padx=5)
        
        self.dispositivos_label = ttk.Label(stats_grid, text="📱 Dispositivos: 0", 
                                          style='Stat.TLabel')
        self.dispositivos_label.grid(row=0, column=1, sticky='w', pady=5, padx=5)
        
        self.acessos_label = ttk.Label(stats_grid, text="📈 Acessos hoje: 0", 
                                     style='Stat.TLabel')
        self.acessos_label.grid(row=1, column=0, sticky='w', pady=5, padx=5)
        
        self.rede_label = ttk.Label(stats_grid, text="📶 Rede: Detectando...", 
                                  style='Stat.TLabel')
        self.rede_label.grid(row=1, column=1, sticky='w', pady=5, padx=5)
        
        # ===== CONTROLES =====
        control_frame = ttk.LabelFrame(main_frame, text=" 🎛️ Controles do Servidor ", 
                                      style='Card.TLabelframe', padding="15")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Grid de botões - maiores
        button_grid = ttk.Frame(control_frame, style='Dark.TFrame')
        button_grid.pack(fill=tk.X, expand=True)
        
        # Botão Parar
        self.stop_btn = ttk.Button(button_grid, text="⏹️ Parar Servidor", 
                                 command=self.parar_servidor, 
                                 style='Danger.TButton',
                                 state='disabled')
        self.stop_btn.grid(row=0, column=0, padx=(0, 10), pady=5, sticky='ew')
        
        # Botão Reiniciar
        self.restart_btn = ttk.Button(button_grid, text="🔄 Reiniciar", 
                                    command=self.reiniciar_servidor, 
                                    style='Warning.TButton',
                                    state='disabled')
        self.restart_btn.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
        
        # Botão Sair
        exit_btn = ttk.Button(button_grid, text="❌ Sair", 
                            command=self.sair_aplicacao, 
                            style='Danger.TButton')
        exit_btn.grid(row=0, column=2, padx=(10, 0), pady=5, sticky='ew')
        
        # Configurar pesos das colunas
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        button_grid.columnconfigure(2, weight=1)
        
        # Espaço final
        ttk.Label(main_frame, text="", style='Modern.TFrame').pack(pady=5)
    
    def center_window(self):
        """Centralizar janela na tela"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def iniciar_servidor(self):
        """Iniciar o servidor Flask"""
        if not self.servidor_rodando:
            self.progress.start()
            self.status_label.config(text="⏳ Iniciando servidor...", 
                                   foreground=self.colors['warning'])
            
            self.monitor_thread = threading.Thread(target=monitorar_ip_e_registrar, daemon=True)
            self.monitor_thread.start()
            
            self.flask_thread = threading.Thread(target=self.run_flask_server, daemon=True)
            self.flask_thread.start()
            
            self.root.after(3000, self.verificar_servidor)
    
    def run_flask_server(self):
        """Executar servidor Flask"""
        try:
            from werkzeug.serving import make_server
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', porta))
            sock.close()
            
            if result == 0:
                time.sleep(2)
            
            from main import registrar_mdns, obter_endereco_ip, criar_qrcode_simples
            from datetime import datetime
            import main
            main.servidor_iniciado_em = datetime.now()
            
            self.flask_server = make_server("0.0.0.0", porta, app, threaded=True)
            self.flask_server.serve_forever()
            
        except OSError as e:
            if "Address already in use" in str(e):
                time.sleep(3)
                try:
                    self.flask_server = make_server("0.0.0.0", porta, app, threaded=True)
                    self.flask_server.serve_forever()
                except Exception as e2:
                    self.root.after(0, lambda: self.erro_servidor(f"Porta {porta} ocupada."))
            else:
                self.root.after(0, lambda: self.erro_servidor(str(e)))
        except Exception as e:
            self.root.after(0, lambda: self.erro_servidor(str(e)))
    
    def verificar_servidor(self):
        """Verificar se servidor está rodando"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', porta))
            sock.close()
            
            if result == 0:
                self.servidor_iniciado()
            else:
                self.root.after(2000, self.verificar_servidor)
        except:
            self.root.after(2000, self.verificar_servidor)
    
    def servidor_iniciado(self):
        """Callback quando servidor está pronto"""
        self.servidor_rodando = True
        self.progress.stop()
        self.status_label.config(text="✅ Servidor rodando!", 
                               foreground=self.colors['success'])
        
        self.url_atual = f"http://{obter_endereco_ip(True)}"
        self.url_label.config(text=self.url_atual)
        self.mdns_label.config(text=f"🔄 http://{obter_mdns_host()}:{porta}")

        self.open_browser_btn.config(state='normal')
        self.copy_url_btn.config(state='normal')
        self.config_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        self.restart_btn.config(state='normal')
        
        self.gerar_qr_code()
        self.root.after(1000, self.abrir_navegador)
        self.atualizar_estatisticas()
    
    def erro_servidor(self, erro):
        """Callback para erro no servidor"""
        self.progress.stop()
        self.status_label.config(text=f"❌ Erro: {erro}", 
                               foreground=self.colors['error'])
        messagebox.showerror("Erro", f"Falha ao iniciar servidor:\n{erro}")
    
    def gerar_qr_code(self):
        """Gerar e exibir QR Code"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.url_atual)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((130, 130))
            
            photo = ImageTk.PhotoImage(qr_img)
            self.qr_label.config(image=photo, text="")
            self.qr_label.image = photo
            
        except Exception as e:
            self.qr_label.config(text=f"Erro ao gerar QR Code: {str(e)}")
    
    def abrir_navegador(self):
        """Abrir navegador com a URL"""
        if self.url_atual:
            webbrowser.open(self.url_atual)
    
    def abrir_configuracoes(self):
        """Abrir a tela de Configurações (nome mDNS) no navegador"""
        if self.url_atual:
            webbrowser.open(f"{self.url_atual}/configuracoes")

    def copiar_url(self):
        """Copiar URL para clipboard"""
        if self.url_atual:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.url_atual)
            messagebox.showinfo("Copiado", "URL copiada para a área de transferência!")
    
    def parar_servidor(self, show_message=True):
        """Parar servidor Flask completamente"""
        if self.servidor_rodando:
            self.status_label.config(text="⏹️ Parando servidor...", 
                                   foreground=self.colors['warning'])
            
            self.parar_servidor_completo()
            
            self.status_label.config(text="⏹️ Servidor parado", 
                                   foreground=self.colors['error'])
            self.open_browser_btn.config(state='disabled')
            self.copy_url_btn.config(state='disabled')
            self.config_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            self.restart_btn.config(state='normal')
            self.qr_label.config(image='', text="QR Code indisponível")
            
            if show_message:
                messagebox.showinfo("Servidor", "Servidor parado completamente!")
    
    def reiniciar_servidor(self):
        """Reiniciar servidor"""
        if self.servidor_rodando:
            self.parar_servidor(show_message=False)
            self.root.after(5000, self._restart_after_stop)
        else:
            self._restart_after_stop()
    
    def _restart_after_stop(self):
        """Método auxiliar para reiniciar após parada"""
        self.status_label.config(text="🔄 Verificando porta...", 
                               foreground=self.colors['warning'])
        self.restart_btn.config(state='disabled')
        self.progress.start()
        self._check_port_and_start()
    
    def _check_port_and_start(self):
        """Verificar se porta está livre e iniciar servidor"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', porta))
            sock.close()
            
            if result != 0:
                self.status_label.config(text="🔄 Reiniciando servidor...", 
                                       foreground=self.colors['warning'])
                self.servidor_rodando = False
                self.flask_thread = None
                self.flask_server = None
                self.monitor_thread = None
                self.root.after(1000, self.iniciar_servidor)
            else:
                self.status_label.config(text="⏳ Aguardando porta liberar...", 
                                       foreground=self.colors['warning'])
                self.root.after(2000, self._check_port_and_start)
                
        except Exception as e:
            self.root.after(1000, self.iniciar_servidor)
    
    def on_closing(self):
        """Handler para fechamento da janela"""
        if messagebox.askokcancel("Sair", "Deseja realmente sair do FileSwift?\n\nO servidor será parado automaticamente."):
            self.parar_servidor_completo()
            self.root.quit()
            self.root.destroy()
            sys.exit(0)
    
    def parar_servidor_completo(self):
        """Parar servidor Flask de forma completa e forçada"""
        print("🛑 Encerrando FileSwift...")
        self.servidor_rodando = False
        
        try:
            requests.get(f"http://localhost:{porta}/shutdown", timeout=2)
            print("✅ Servidor parado via endpoint")
        except:
            print("⚠️ Endpoint shutdown não respondeu")
        
        if self.flask_server:
            try:
                self.flask_server.shutdown()
                print("✅ Servidor Flask parado diretamente")
            except:
                print("⚠️ Erro ao parar servidor Flask")
        
        try:
            import subprocess
            import signal
            result = subprocess.run(['lsof', '-ti', f':{porta}'], 
                                  capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        os.kill(int(pid), signal.SIGTERM)
                        print(f"✅ Processo {pid} terminado")
                    except:
                        pass
        except:
            print("⚠️ Não foi possível matar processos da porta")
        
        time.sleep(1)
        print("🏁 FileSwift encerrado")
    
    def sair_aplicacao(self):
        """Sair da aplicação"""
        self.on_closing()
    
    def atualizar_estatisticas(self):
        """Atualizar estatísticas do servidor em tempo real"""
        self.info_label.config(
            text=f"📁 Pasta: static/download/\n🌐 Rede local\n📱 QR Code móvel\n🔄 mDNS: {obter_mdns_host()}"
        )
        if self.servidor_rodando:
            self.mdns_label.config(text=f"🔄 http://{obter_mdns_host()}:{porta}")
            try:
                response = requests.get(f"http://localhost:{porta}/api/stats", timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    self.tempo_ativo_label.config(text=f"🌐 Ativo há: {stats['tempo_ativo']}")
                    self.dispositivos_label.config(text=f"📱 Dispositivos: {stats['dispositivos_conectados']}")
                    self.acessos_label.config(text=f"📈 Acessos hoje: {stats['acessos_hoje']}")
                    self.rede_label.config(text=f"📶 Rede: {stats['nome_rede']}")
                else:
                    self._reset_estatisticas()
            except:
                self._reset_estatisticas()
        else:
            self._reset_estatisticas()
        
        self.root.after(3000, self.atualizar_estatisticas)
    
    def _reset_estatisticas(self):
        """Resetar estatísticas para valores padrão"""
        self.tempo_ativo_label.config(text="🌐 Ativo há: 00:00:00")
        self.dispositivos_label.config(text="📱 Dispositivos: 0")
        self.acessos_label.config(text="📈 Acessos hoje: 0")
        self.rede_label.config(text="📶 Rede: Desconectado")
    
    def run(self):
        """Executar a GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.sair_aplicacao()

if __name__ == "__main__":
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("⚠️ Instalando dependência PIL...")
        os.system("pip install Pillow")
        from PIL import Image, ImageTk
    
    gui = FileSwiftGUI()
    gui.run()
