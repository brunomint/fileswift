# 🚀 FileSwift - Gerenciador de Arquivos Web

FileSwift é um gerenciador de arquivos web moderno e intuitivo que permite compartilhar, visualizar e gerenciar arquivos através do navegador em sua rede local.

## ✨ Funcionalidades

- 📁 **Navegação de pastas** - Interface intuitiva para explorar arquivos
- 📤 **Upload de arquivos** - Drag & drop com múltiplos formatos
- 🖼️ **Galeria visual** - Visualização de imagens, vídeos e documentos
- 📱 **QR Code** - Acesso rápido via dispositivos móveis
- 🔍 **Busca global** - Encontre arquivos rapidamente
- 📋 **Operações de arquivo** - Copiar, mover, deletar, criar pastas
- 🌐 **mDNS** - Acesso via `fileswift.local`
- 💻 **Interface gráfica** - Launcher amigável para usuários

## 🚀 Como usar

### Método 1: Interface Gráfica (Recomendado)

1. **Execute o launcher principal:**
   ```bash
   python FileSwift.py
   ```

2. **A interface gráfica será aberta** mostrando:
   - ✅ Status do servidor
   - 🌐 URL de acesso clicável
   - 📱 QR Code para dispositivos móveis
   - 🔘 Botões de controle (Abrir, Copiar URL, Parar, etc.)

3. **O navegador abrirá automaticamente** com o FileSwift

### Método 2: Modo Console

```bash
python main.py --console
```

### Método 3: Modo Original

```bash
python main.py
```

## 📦 Instalação de Dependências

### Automática
```bash
python install_dependencies.py
```

### Manual
```bash
pip install -r requirements.txt
```

## 🔧 Dependências

- **Flask** - Framework web
- **Pillow** - Processamento de imagens
- **qrcode** - Geração de QR codes
- **zeroconf** - Descoberta mDNS
- **tkinter** - Interface gráfica (incluído no Python)

## 📱 Acesso

- **Local:** `http://localhost:5678`
- **Rede:** `http://[SEU_IP]:5678`
- **mDNS:** `http://fileswift.local:5678`
- **QR Code:** Escaneie com seu celular

## 📁 Estrutura

```
fileswift_2/
├── FileSwift.py          # 🚀 Launcher principal (USE ESTE!)
├── main.py               # 🔧 Servidor Flask
├── gui_launcher.py       # 💻 Interface gráfica
├── install_dependencies.py # 📦 Instalador
├── requirements.txt      # 📋 Dependências
├── static/
│   ├── download/         # 📁 Pasta de arquivos
│   ├── logo.png          # 🎨 Logo
│   └── qrcode.png        # 📱 QR Code gerado
└── templates/            # 🌐 Templates HTML
```

## 🎯 Para Usuários Finais

### ▶️ **Iniciar:**
1. **Execute:** `FileSwift.py`
2. **Aguarde** a interface gráfica abrir
3. **Clique** em "Abrir no Navegador"
4. **Pronto!** Use o FileSwift normalmente

### ⏹️ **Parar o Servidor:**
- **Método 1:** Clique no botão "⏹️ Parar Servidor" na interface
- **Método 2:** Feche a janela do FileSwift (recomendado)
- **Método 3:** Clique no "❌ Sair FileSwift"

**Nota:** Fechar a janela para o servidor automaticamente!

### 📐 **Interface:**
- **Tamanho da janela:** 550x830 pixels (otimizada)
- **Redimensionável:** Sim (mínimo 500x750)
- **Todos os controles sempre visíveis** sem necessidade de scroll
- **📊 Atividade do Servidor:** Monitoramento em tempo real
  - Tempo de atividade do servidor
  - Dispositivos conectados (últimos 5 minutos)
  - Acessos do dia atual
  - Nome da rede WiFi conectada

## 🔧 Para Desenvolvedores

- **GUI:** `gui_launcher.py` - Interface tkinter
- **Servidor:** `main.py` - Flask backend
- **Fallback:** Modo console se GUI falhar
- **Auto-instalação:** Dependências instaladas automaticamente

## 📋 Formatos Suportados

**Imagens:** PNG, JPG, JPEG, GIF, WebP, HEVC  
**Vídeos:** MP4, WebM, OGG, MOV, HEIF  
**Documentos:** PDF, TXT, DOC, DOCX, HTML, MD, XML  
**Outros:** ZIP, PY, JSON, CSV, XLS, PPT, MP3, WAV

## 🆘 Solução de Problemas

### GUI não abre
- Execute: `python install_dependencies.py`
- Ou use: `python main.py --console`

### Porta ocupada
- O sistema tentará usar porta 5678
- Se ocupada, será exibido erro na GUI
- **Reinicialização:** Aguarda automaticamente a porta liberar

### Reinicialização lenta
- O botão "Reiniciar" aguarda 5 segundos para garantir que a porta seja liberada
- Status mostra: "Verificando porta..." → "Aguardando porta liberar..." → "Reiniciando..."
- Isso evita conflitos de "Address already in use"

### Dependências faltando
- Execute o instalador automático
- Ou instale manualmente: `pip install -r requirements.txt`

## 🎉 Pronto para usar!

Agora o FileSwift tem uma interface gráfica amigável que elimina a "sopa de letrinhas" do terminal. Perfeito para usuários comuns! 🚀
