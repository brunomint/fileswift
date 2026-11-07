# 🚀 FileSwift

🇧🇷 [Português](README.md)

FileSwift is a file server for your local network: access, organize and share photos, videos and documents through the browser, from any device on the same Wi-Fi — no cloud, no app to install on the phone. It also comes with **Quick Texts**, a notepad that can attach PDFs (shipping labels, invoices, etc.), made for people who paste order confirmations all day long.

## ✨ Features

- 📁 **File gallery** — browse by folder, with thumbnails for images and videos, kept apart from documents
- 📤 **Upload by click or drag-and-drop**, many files at once
- 📝 **Quick Texts** — notes with automatic highlighting of e-mails, Brazilian IDs (CPF), postal codes (CEP) and amounts in R$, with PDF attachments (several per note)
- 🔄 **Live updates** — the gallery and the text lists refresh on their own when another device uploads or deletes something, no reload needed
- 📱 **QR Code + mDNS** (`fs.local` by default, name configurable per instance) — quick access from any phone on the network, without typing an IP
- 🔍 **Global search** across folders and files
- 📋 Copy, move, delete (one by one or in bulk), create folders
- 🔒 **Password protected** — protected by default; nobody on the network gets in without the password you set on first run
- ⚙️ **Settings** — change the mDNS name at any time (useful if you run FileSwift on more than one PC on the same network)
- 📲 Phone-friendly interface (side menu, touch drag-and-drop)

> The interface is in Portuguese for now. Translations are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## 🔒 Security

FileSwift asks for a single password (like a Wi-Fi password, not a per-user login) before allowing any access — this is mandatory and cannot be skipped. The first time you open it, you land straight on a screen to set that password.

Important points about the current security model:
- Made for home use, on a Wi-Fi network you already trust — there is no HTTPS (the session cookie travels unencrypted inside your local network).
- A session lasts 30 days per device (it favors not asking for the password all the time).
- 5 wrong password attempts temporarily block the IP for a few minutes.
- **Forgot the password?** Delete the `config.json` file in the data folder (see "Where your data lives" below) and restart — the app asks you to set a new password again.
- All forms are protected against CSRF, but exposing this server directly to the internet (outside your local network) is not recommended.

## 📦 Installation

Pick the method for your system:

### Linux — any distribution (Ubuntu, Fedora, Arch, etc.)
```bash
git clone https://github.com/brunomint/fileswift.git
cd fileswift
./install.sh
```
Creates a shortcut in the applications menu and a `fileswift` command in the terminal. To uninstall: `./uninstall.sh` (keeps your data — use `--purge` to delete everything).

### Debian / Ubuntu / Linux Mint / Zorin OS
Download the latest `.deb` (or build your own: `./build-deb.sh`) and install it with:
```bash
sudo apt install ./fileswift_<version>_all.deb
```
`apt` resolves the system dependencies by itself (Python, venv, tkinter).

### Windows
The installer is built automatically by GitHub Actions for each release — see the repository's [Actions](../../actions/workflows/build-windows.yml) tab to download the latest `.exe` (look for the `FileSwiftSetup-*` artifact). Per-user install, no administrator needed.

### macOS
Not supported yet.

### Running from source (dev)
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py --console
```

## 🐳 Installing with Docker

FileSwift can also run with Docker, which makes installation easier and keeps dependencies isolated.

### Requirements

* Docker
* Docker Compose (v2 or later)

### Running

The ready-made image (PC and Raspberry Pi 4/5, 64-bit) is at `ghcr.io/brunomint/fileswift`. With the [`docker-compose.yml`](docker-compose.yml) in a folder:

```bash
docker compose up -d
```

Or directly, without compose:

```bash
docker run -d --name fileswift --network host --restart unless-stopped \
  -e FILESWIFT_DATA_DIR=/data -v ./data:/data \
  ghcr.io/brunomint/fileswift:latest
```

If you cloned the repository and want to run your own code, use `docker compose up -d --build`.

Once it starts, FileSwift is available at:

```text
http://localhost:5678
```

### Data persistence

All FileSwift data is stored in the `data/` directory, mounted automatically as a volume by `docker-compose.yml`.

This includes:

* `config.json`
* `fileswift.db`
* Uploaded files
* Quick Texts attachments
* Any other persistent application data

So updating or recreating the container **does not remove your files or your settings**.

### Updating

```bash
docker compose pull
docker compose up -d
```

Docker downloads the latest version and restarts the container, keeping all the data stored in `data/`. (Running your own code: `docker compose up -d --build`.)

### Stopping

```bash
docker compose down
```

### CasaOS

In the CasaOS dashboard: **App Store → "+" (Custom Install) → Import** and paste the contents of [`casaos/docker-compose.yml`](casaos/docker-compose.yml). Data is kept in `/DATA/AppData/fileswift`.

### Portainer (and Umbrel)

In Portainer: **Stacks → Add stack**, name it `fileswift` and paste into the editor:

```yaml
services:
  fileswift:
    image: ghcr.io/brunomint/fileswift:latest
    network_mode: host
    environment:
      FILESWIFT_DATA_DIR: /data
    volumes:
      - fileswift-data:/data
    restart: unless-stopped
volumes:
  fileswift-data:
```

On Umbrel, install Portainer from the app store and follow the same steps.

In every case FileSwift uses the server's own network (`network_mode: host`), so `fs.local` and the QR Code work: open `http://<server-ip>:5678`. Port 5678 must be free.

## 🌐 How to access

Once started, the server is available at:
- **On this machine:** `http://localhost:5678`
- **From other devices on the same network:** `http://<machine-IP>:5678` or `http://fs.local:5678`
- **From your phone:** scan the QR Code shown on the home page

Running FileSwift on more than one machine on the same network? Each one needs its own name (mDNS does not allow two machines announcing `fs.local` at the same time — the second one simply does not register). Change it in **Settings** in the gallery's side bar.

## 🗂 Where your data lives

Nothing is written inside the install folder. Everything goes to a separate folder, per device:

| Installation | Data folder |
|---|---|
| `install.sh` / `.deb` (Linux) | `~/.local/share/fileswift/` |
| Windows | `%LOCALAPPDATA%\FileSwift\` |
| Running from source | the project folder itself |

Inside it: `fileswift.db` (quick texts), `static/download/` (your files), `textos_anexos/` (attached PDFs), `config.json` (password and settings — never committed to Git) and `fileswift.log` (rotating log, up to 4 files of 1 MB — handy to send to whoever is helping you with a problem).

## 📋 Supported formats

**Images:** PNG, JPG, JPEG, GIF, WebP, HEIC/HEVC
**Videos:** MP4, WebM, OGG, MOV, HEIF
**Quick Texts attachments:** PDF
**Other files:** any type is accepted for upload and listed as a document (no extension restriction)

## 🆘 Common problems

**I forgot the password** — delete `config.json` in the data folder (see the table above) and restart the app.

**"Port 5678 in use"** — another FileSwift instance is already running (on this machine or in the background); close it before opening again.

**Python without `venv`/`tkinter` (Ubuntu 23.04+ / recent Debian)** — `install.sh` detects this and shows the right command to install them (`sudo apt install python3-venv python3-tk`); with the `.deb`, `apt` takes care of it automatically.

## 🧑‍💻 For developers

Want to contribute? See [CONTRIBUTING.md](CONTRIBUTING.md) (setup, conventions, what to expect from review — in Portuguese, but issues and pull requests in English are welcome) and [CHANGELOG.md](CHANGELOG.md) (history of changes).

- `main.py` — Flask server (all the routes, SQLite database, authentication)
- `gui_launcher.py` — optional tkinter window (the app works the same without it, opening straight in the browser)
- `gui_logica.py` — window logic with no widget dependency (port check, reading statistics, shutting the server down), testable without building the GUI
- `templates/` — HTML (Jinja2), one file per screen
- `tests/` — test suite (pytest)
- `install.sh`, `build-deb.sh`, `fileswift.spec` + `.github/workflows/build-windows.yml` — packaging per platform

### Running the tests

With Docker, without installing anything on your machine:

```bash
docker compose run --rm test
```

The `test` service lives in a separate profile, so it does not start with `docker compose up`. The code is mounted as a volume so editing a test does not require a rebuild. The container's `/data` is `tmpfs`: it exists only in memory and is thrown away at the end, so no test can reach real data.

Directly on your machine, in a virtualenv:

```bash
pip install -r requirements.txt -r requirements.dev.txt
pytest
```

An important detail of [tests/conftest.py](tests/conftest.py): importing `main.py` by itself no longer does anything — folders, `config.json`, the database and Zeroconf are only created by `main.init_app()`, called explicitly. `conftest.py` points `FILESWIFT_DATA_DIR` to a temporary folder **before** the import, and calls `init_app()` right after. If you write a new test that imports `main` outside that path (without going through `conftest.py`), it will touch the real data of whoever is running it.

In CI, the [Tests](.github/workflows/testes.yml) workflow runs the suite on every push and pull request, in three combinations: Linux and Windows on Python 3.11, plus the 3.8 minimum that `install.sh` accepts. The Windows installer build depends on this workflow: if the suite breaks, no installer is published.

## 📄 License

MIT — see the [LICENSE](LICENSE) file.

## ☕ Support the project

If FileSwift was useful to you, consider supporting it at [ko-fi.com/brunofragosodealmeida](https://ko-fi.com/brunofragosodealmeida).
