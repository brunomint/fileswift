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
from main import app, porta, obter_endereco_ip, criar_qrcode_simples, monitorar_ip_e_registrar

class FileSwiftGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("FileSwift - Gerenciador de Arquivos Web")

        # Altura inicial respeita o tamanho real da tela (telas pequenas não
        # cabem 900px de janela + barra de tarefas). O conteúdo tem scroll
        # (ver create_widgets), então mesmo numa janela baixa nada fica
        # inacessível — só passa a rolar em vez de cortar.
        screen_height = self.root.winfo_screenheight()
        altura_inicial = min(900, max(500, screen_height - 100))
        self.root.geometry(f"580x{altura_inicial}")
        self.root.resizable(True, True)  # Permitir redimensionar
        self.root.minsize(550, 400)
        
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
        self.flask_server = None  # Referência para o servidor Flask controlável
        
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
        """Configurar estilo da interface"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar cores
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground='#2c3e50')
        style.configure('Status.TLabel', font=('Arial', 10), foreground='#27ae60')
        style.configure('URL.TLabel', font=('Arial', 11, 'bold'), foreground='#3498db')
        style.configure('Action.TButton', font=('Arial', 10, 'bold'))
    
    def create_widgets(self):
        """Criar todos os widgets da interface"""
        # Canvas + scrollbar: garante que a parte de baixo da janela (botões
        # de controle) sempre fique acessível, mesmo em telas onde a janela
        # não cabe inteira — em vez de cortar o conteúdo, ele passa a rolar.
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Frame principal com scroll se necessário
        main_frame = ttk.Frame(canvas, padding="10")
        janela_conteudo = canvas.create_window((0, 0), window=main_frame, anchor="nw")

        def _atualizar_scrollregion(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _ajustar_largura_conteudo(event):
            canvas.itemconfig(janela_conteudo, width=event.width)

        main_frame.bind("<Configure>", _atualizar_scrollregion)
        canvas.bind("<Configure>", _ajustar_largura_conteudo)

        def _rolar_mouse(event):
            if event.num == 5 or event.delta < 0:
                canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-1, "units")

        # Windows/macOS usam <MouseWheel> com event.delta; Linux usa os
        # botões 4/5 do "mouse" para rolar.
        canvas.bind_all("<MouseWheel>", _rolar_mouse)
        canvas.bind_all("<Button-4>", _rolar_mouse)
        canvas.bind_all("<Button-5>", _rolar_mouse)
        
        # Título
        title_label = ttk.Label(main_frame, text="🚀 FileSwift", style='Title.TLabel')
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, text="Gerenciador de Arquivos Web", 
                                 font=('Arial', 12), foreground='#7f8c8d')
        subtitle_label.pack(pady=(0, 20))
        
        # Status do servidor
        status_frame = ttk.LabelFrame(main_frame, text="Status do Servidor", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="⏳ Iniciando servidor...", 
                                    style='Status.TLabel')
        self.status_label.pack()
        
        # Barra de progresso
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(10, 0))
        
        # URL de acesso
        url_frame = ttk.LabelFrame(main_frame, text="Acesso ao FileSwift", padding="10")
        url_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.url_label = ttk.Label(url_frame, text="Aguardando servidor...", 
                                 style='URL.TLabel')
        self.url_label.pack(pady=(0, 10))
        
        # Botões de ação
        button_frame = ttk.Frame(url_frame)
        button_frame.pack(fill=tk.X)
        
        self.open_browser_btn = ttk.Button(button_frame, text="🌐 Abrir no Navegador", 
                                         command=self.abrir_navegador, style='Action.TButton',
                                         state='disabled')
        self.open_browser_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.copy_url_btn = ttk.Button(button_frame, text="📋 Copiar URL", 
                                     command=self.copiar_url, style='Action.TButton',
                                     state='disabled')
        self.copy_url_btn.pack(side=tk.LEFT)
        
        # QR Code (mais compacto)
        qr_frame = ttk.LabelFrame(main_frame, text="QR Code - Acesso Móvel", padding="10")
        qr_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.qr_label = ttk.Label(qr_frame, text="QR Code será gerado após inicialização...")
        self.qr_label.pack()
        
        # Informações adicionais (mais compacto)
        info_frame = ttk.LabelFrame(main_frame, text="Informações", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = """📁 Pasta: static/download/ | 🌐 Rede local | 📱 QR Code móvel | 🔄 mDNS: fs.local"""
        
        info_label = ttk.Label(info_frame, text=info_text, font=('Arial', 8), wraplength=450)
        info_label.pack()
        
        # Atividade do Servidor
        activity_frame = ttk.LabelFrame(main_frame, text="📊 Atividade do Servidor", padding="8")
        activity_frame.pack(fill=tk.X, pady=(0, 8))
        
        self.tempo_ativo_label = ttk.Label(activity_frame, text="🌐 Servidor ativo há: 00:00:00", font=('Arial', 9))
        self.tempo_ativo_label.pack(anchor='w')
        
        self.dispositivos_label = ttk.Label(activity_frame, text="📱 Dispositivos conectados: 0", font=('Arial', 9))
        self.dispositivos_label.pack(anchor='w')
        
        self.acessos_label = ttk.Label(activity_frame, text="📈 Acessos hoje: 0", font=('Arial', 9))
        self.acessos_label.pack(anchor='w')
        
        self.rede_label = ttk.Label(activity_frame, text="📶 Rede: Detectando...", font=('Arial', 9))
        self.rede_label.pack(anchor='w')
        
        # Botões de controle (SEMPRE VISÍVEL) - padding reduzido
        control_frame = ttk.LabelFrame(main_frame, text="🎛️ Controles do Servidor", padding="8")
        control_frame.pack(fill=tk.X, pady=(5, 10), expand=False)
        
        # Criar grid de botões para melhor organização
        button_grid = ttk.Frame(control_frame)
        button_grid.pack(fill=tk.X, expand=True)
        
        # Primeira linha - botões de controle com mais espaçamento
        self.stop_btn = ttk.Button(button_grid, text="⏹️ Parar Servidor", 
                                 command=self.parar_servidor, state='disabled',
                                 width=15)
        self.stop_btn.grid(row=0, column=0, padx=(0, 10), pady=5, sticky='w')
        
        self.restart_btn = ttk.Button(button_grid, text="🔄 Reiniciar", 
                                    command=self.reiniciar_servidor, state='disabled',
                                    width=15)
        self.restart_btn.grid(row=0, column=1, padx=10, pady=5, sticky='w')
        
        # Botão sair à direita
        exit_btn = ttk.Button(button_grid, text="❌ Sair FileSwift", 
                             command=self.sair_aplicacao, width=15)
        exit_btn.grid(row=0, column=2, padx=(10, 0), pady=5, sticky='e')
        
        # Configurar peso das colunas para distribuição uniforme
        button_grid.columnconfigure(0, weight=1)
        button_grid.columnconfigure(1, weight=1)
        button_grid.columnconfigure(2, weight=1)
        
        # Adicionar espaço mínimo no final
        ttk.Label(main_frame, text="").pack(pady=5)
    
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
            self.status_label.config(text="⏳ Iniciando servidor...", foreground='#f39c12')
            
            # Iniciar threads do servidor
            self.monitor_thread = threading.Thread(target=monitorar_ip_e_registrar, daemon=True)
            self.monitor_thread.start()
            
            self.flask_thread = threading.Thread(target=self.run_flask_server, daemon=True)
            self.flask_thread.start()
            
            # Verificar se servidor iniciou
            self.root.after(3000, self.verificar_servidor)
    
    def run_flask_server(self):
        """Executar servidor Flask"""
        try:
            # Importar make_server para controle do servidor
            from werkzeug.serving import make_server
            
            # Verificar se porta está livre antes de iniciar
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', porta))
            sock.close()
            
            if result == 0:
                # Porta ocupada, aguardar um pouco mais
                time.sleep(2)
            
            # Inicialização do servidor (antes estava no before_first_request)
            from main import registrar_mdns, obter_endereco_ip, criar_qrcode_simples
            from datetime import datetime
            import main
            main.servidor_iniciado_em = datetime.now()  # Marcar início do servidor
            
            # Criar servidor controlável
            self.flask_server = make_server("0.0.0.0", porta, app, threaded=True)
            self.flask_server.serve_forever()
            
        except OSError as e:
            if "Address already in use" in str(e):
                # Tentar aguardar e reiniciar
                time.sleep(3)
                try:
                    self.flask_server = make_server("0.0.0.0", porta, app, threaded=True)
                    self.flask_server.serve_forever()
                except Exception as e2:
                    self.root.after(0, lambda: self.erro_servidor(f"Porta {porta} ocupada. Tente reiniciar em alguns segundos."))
            else:
                self.root.after(0, lambda: self.erro_servidor(str(e)))
        except Exception as e:
            self.root.after(0, lambda: self.erro_servidor(str(e)))
    
    def verificar_servidor(self):
        """Verificar se servidor está rodando"""
        try:
            # Testar conexão local
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
        self.status_label.config(text="✅ Servidor rodando!", foreground='#27ae60')
        
        # Atualizar URL
        self.url_atual = f"http://{obter_endereco_ip(True)}"
        self.url_label.config(text=self.url_atual)
        
        # Habilitar botões
        self.open_browser_btn.config(state='normal')
        self.copy_url_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        self.restart_btn.config(state='normal')
        
        # Gerar e exibir QR Code
        self.gerar_qr_code()
        
        # Abrir navegador automaticamente
        self.root.after(1000, self.abrir_navegador)
        
        # Iniciar atualização de estatísticas
        self.atualizar_estatisticas()
    
    def erro_servidor(self, erro):
        """Callback para erro no servidor"""
        self.progress.stop()
        self.status_label.config(text=f"❌ Erro: {erro}", foreground='#e74c3c')
        messagebox.showerror("Erro", f"Falha ao iniciar servidor:\n{erro}")
    
    def gerar_qr_code(self):
        """Gerar e exibir QR Code"""
        try:
            # Gerar QR Code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.url_atual)
            qr.make(fit=True)
            
            # Criar imagem (menor para economizar espaço)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_img = qr_img.resize((120, 120))
            
            # Converter para PhotoImage
            photo = ImageTk.PhotoImage(qr_img)
            
            # Atualizar label
            self.qr_label.config(image=photo, text="")
            self.qr_label.image = photo  # Manter referência
            
        except Exception as e:
            self.qr_label.config(text=f"Erro ao gerar QR Code: {str(e)}")
    
    def abrir_navegador(self):
        """Abrir navegador com a URL"""
        if self.url_atual:
            webbrowser.open(self.url_atual)
    
    def copiar_url(self):
        """Copiar URL para clipboard"""
        if self.url_atual:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.url_atual)
            messagebox.showinfo("Copiado", "URL copiada para a área de transferência!")
    
    def parar_servidor(self, show_message=True):
        """Parar servidor Flask completamente"""
        if self.servidor_rodando:
            self.status_label.config(text="⏹️ Parando servidor...", foreground='#f39c12')
            
            # Usar a função completa de parada
            self.parar_servidor_completo()
            
            # Atualizar interface
            self.status_label.config(text="⏹️ Servidor parado", foreground='#e74c3c')
            self.open_browser_btn.config(state='disabled')
            self.copy_url_btn.config(state='disabled')
            self.stop_btn.config(state='disabled')
            # MANTER REINICIAR HABILITADO quando servidor está parado
            self.restart_btn.config(state='normal')  
            self.qr_label.config(image='', text="QR Code indisponível")
            
            # Só mostrar mensagem se solicitado (não durante reinicialização)
            if show_message:
                messagebox.showinfo("Servidor", "Servidor parado completamente!\n\nUse o botão 'Reiniciar' para iniciar novamente.")
    
    def reiniciar_servidor(self):
        """Reiniciar servidor"""
        # Se servidor está rodando, parar primeiro
        if self.servidor_rodando:
            self.parar_servidor(show_message=False)  # Não mostrar mensagem durante reinicialização
            # Aguardar 5 segundos antes de reiniciar (mais tempo para liberar porta)
            self.root.after(5000, self._restart_after_stop)
        else:
            # Se já está parado, iniciar diretamente
            self._restart_after_stop()
    
    def _restart_after_stop(self):
        """Método auxiliar para reiniciar após parada"""
        self.status_label.config(text="🔄 Verificando porta...", foreground='#f39c12')
        self.restart_btn.config(state='disabled')
        self.progress.start()
        
        # Verificar se porta está livre antes de tentar iniciar
        self._check_port_and_start()
    
    def _check_port_and_start(self):
        """Verificar se porta está livre e iniciar servidor"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', porta))
            sock.close()
            
            if result != 0:
                # Porta livre, pode iniciar
                self.status_label.config(text="🔄 Reiniciando servidor...", foreground='#f39c12')
                
                # Resetar variáveis
                self.servidor_rodando = False
                self.flask_thread = None
                self.flask_server = None
                self.monitor_thread = None
                
                # Iniciar servidor
                self.root.after(1000, self.iniciar_servidor)
            else:
                # Porta ainda ocupada, aguardar mais
                self.status_label.config(text="⏳ Aguardando porta liberar...", foreground='#f39c12')
                self.root.after(2000, self._check_port_and_start)
                
        except Exception as e:
            # Em caso de erro, tentar iniciar mesmo assim
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
        
        # Marcar como não rodando
        self.servidor_rodando = False
        
        # Método 1: Tentar parar via endpoint /shutdown
        try:
            requests.get(f"http://localhost:{porta}/shutdown", timeout=2)
            print("✅ Servidor parado via endpoint")
        except:
            print("⚠️ Endpoint shutdown não respondeu")
        
        # Método 2: Parar servidor diretamente
        if self.flask_server:
            try:
                self.flask_server.shutdown()
                print("✅ Servidor Flask parado diretamente")
            except:
                print("⚠️ Erro ao parar servidor Flask")
        
        # Método 3: Matar processo Python na porta
        try:
            import subprocess
            import signal
            
            # Encontrar processo na porta
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
        
        # Aguardar um pouco para limpeza
        time.sleep(1)
        print("🏁 FileSwift encerrado")
    
    def sair_aplicacao(self):
        """Sair da aplicação"""
        self.on_closing()
    
    def atualizar_estatisticas(self):
        """Atualizar estatísticas do servidor em tempo real"""
        if self.servidor_rodando:
            try:
                # Fazer requisição para obter estatísticas
                response = requests.get(f"http://localhost:{porta}/api/stats", timeout=2)
                if response.status_code == 200:
                    stats = response.json()
                    
                    # Atualizar labels
                    self.tempo_ativo_label.config(text=f"🌐 Servidor ativo há: {stats['tempo_ativo']}")
                    self.dispositivos_label.config(text=f"📱 Dispositivos conectados: {stats['dispositivos_conectados']}")
                    self.acessos_label.config(text=f"📈 Acessos hoje: {stats['acessos_hoje']}")
                    self.rede_label.config(text=f"📶 Rede: {stats['nome_rede']}")
                else:
                    # Erro na API, mostrar valores padrão
                    self._reset_estatisticas()
            except:
                # Servidor não responde, mostrar valores padrão
                self._reset_estatisticas()
        else:
            # Servidor parado
            self._reset_estatisticas()
        
        # Agendar próxima atualização (a cada 3 segundos)
        self.root.after(3000, self.atualizar_estatisticas)
    
    def _reset_estatisticas(self):
        """Resetar estatísticas para valores padrão"""
        self.tempo_ativo_label.config(text="🌐 Servidor ativo há: 00:00:00")
        self.dispositivos_label.config(text="📱 Dispositivos conectados: 0")
        self.acessos_label.config(text="📈 Acessos hoje: 0")
        self.rede_label.config(text="📶 Rede: Desconectado")
    
    def run(self):
        """Executar a GUI"""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.sair_aplicacao()

if __name__ == "__main__":
    # Verificar se PIL está disponível
    try:
        from PIL import Image, ImageTk
    except ImportError:
        print("⚠️  Instalando dependência PIL...")
        os.system("pip install Pillow")
        from PIL import Image, ImageTk
    
    # Iniciar GUI
    gui = FileSwiftGUI()
    gui.run()
