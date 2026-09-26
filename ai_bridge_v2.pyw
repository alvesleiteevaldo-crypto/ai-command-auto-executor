import json
import os
import secrets
import shlex
import subprocess
import threading
import time
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Optional
import tkinter as tk
from tkinter import messagebox, ttk

APP_NAME = "AI Command Bridge"
APP_VERSION = "2.0.0"
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
MAX_BODY = 64 * 1024
COMMAND_TIMEOUT = 180

APPDATA = Path(os.environ.get("APPDATA", Path.home())) / "AICommandBridge"
CONFIG_PATH = APPDATA / "config.json"

DEFAULT_ALLOWLIST = [
    "git", "npm", "npx", "node", "python", "py",
    "where", "whoami", "ipconfig", "systeminfo"
]
CMD_BUILTINS = {"dir", "type", "copy", "move", "mkdir", "md", "rmdir", "rd", "echo", "cd"}
FORBIDDEN_META = ["&", "|", ">", "<", "^", "\n", "\r"]
BLOCKED_TOKENS = {
    "format", "shutdown", "restart", "poweroff", "diskpart", "bcdedit",
    "reg", "sc", "taskkill", "net", "wmic"
}


def _default_config() -> Dict[str, Any]:
    home = str(Path.home().resolve())
    return {
        "host": HOST,
        "port": DEFAULT_PORT,
        "require_confirmation": True,
        "strict_mode": True,
        "token": secrets.token_urlsafe(32),
        "allowlist": DEFAULT_ALLOWLIST,
        "allow_cmd_builtins": True,
        "allowed_cwds": [home],
        "timeout_seconds": COMMAND_TIMEOUT,
    }


def load_config() -> Dict[str, Any]:
    APPDATA.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        cfg = _default_config()
        save_config(cfg)
        return cfg
    try:
        cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        cfg = _default_config()
        save_config(cfg)
        return cfg

    changed = False
    defaults = _default_config()
    for k, v in defaults.items():
        if k not in cfg:
            cfg[k] = v
            changed = True
    if not isinstance(cfg.get("token"), str) or len(cfg["token"]) < 20:
        cfg["token"] = secrets.token_urlsafe(32)
        changed = True
    if changed:
        save_config(cfg)
    return cfg


def save_config(cfg: Dict[str, Any]) -> None:
    APPDATA.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


CFG = load_config()
GUI = None


def normalize_cwd(cwd: Optional[str]) -> Path:
    p = Path(cwd or Path.home()).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        raise ValueError("Pasta de trabalho inexistente.")
    allowed = [Path(x).expanduser().resolve() for x in CFG.get("allowed_cwds", [])]
    if not allowed:
        raise ValueError("Nenhuma pasta permitida configurada.")
    ok = any(p == base or base in p.parents for base in allowed)
    if not ok:
        raise PermissionError("Pasta de trabalho fora das áreas permitidas.")
    return p


def split_command(command: str) -> List[str]:
    if not isinstance(command, str):
        raise ValueError("Comando inválido.")
    command = command.strip()
    if not command:
        raise ValueError("Comando vazio.")
    if len(command) > 4096:
        raise ValueError("Comando excede o limite.")
    lowered = command.lower()
    if any(meta in command for meta in FORBIDDEN_META):
        raise PermissionError("Operadores de shell e redirecionamentos não são permitidos.")
    if any(tok in lowered.split() for tok in BLOCKED_TOKENS):
        raise PermissionError("Comando bloqueado por segurança.")
    try:
        return shlex.split(command, posix=False)
    except ValueError as exc:
        raise ValueError(f"Comando inválido: {exc}")


def validate_command(command: str) -> tuple[List[str], bool]:
    argv = split_command(command)
    exe = Path(argv[0].strip('"')).name.lower()
    if exe.endswith(".exe"):
        exe = exe[:-4]

    allow = {str(x).lower().rstrip(".exe") for x in CFG.get("allowlist", [])}
    if exe in CMD_BUILTINS:
        if not CFG.get("allow_cmd_builtins", True):
            raise PermissionError("Comandos internos do CMD estão desativados.")
        return argv, True

    if CFG.get("strict_mode", True) and exe not in allow:
        raise PermissionError(f"'{exe}' não está na lista permitida.")
    return argv, False


def ask_confirmation(command: str, cwd: str) -> bool:
    if not CFG.get("require_confirmation", True):
        return True
    if GUI is None:
        return False
    return GUI.request_confirmation(command, cwd)


def execute_command(command: str, cwd: Optional[str]) -> Dict[str, Any]:
    started = time.time()
    try:
        workdir = normalize_cwd(cwd)
        argv, builtin = validate_command(command)
        if not ask_confirmation(command, str(workdir)):
            return {
                "ok": False, "exit_code": 125, "stdout": "",
                "stderr": "Execução não autorizada pelo usuário.",
                "command": command, "cwd": str(workdir)
            }

        timeout = int(CFG.get("timeout_seconds", COMMAND_TIMEOUT))
        if builtin:
            # Somente builtins pré-aprovados e sem metacaracteres.
            run_argv = ["cmd.exe", "/d", "/s", "/c", command]
        else:
            run_argv = argv

        result = subprocess.run(
            run_argv,
            cwd=str(workdir),
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout[-200000:],
            "stderr": result.stderr[-200000:],
            "command": command,
            "cwd": str(workdir),
            "duration_seconds": round(time.time() - started, 3),
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False, "exit_code": 124,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": "Comando excedeu o tempo limite.",
            "command": command, "cwd": cwd,
        }
    except Exception as exc:
        return {
            "ok": False, "exit_code": 1, "stdout": "",
            "stderr": str(exc), "command": command, "cwd": cwd,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "AICommandBridge/2.0"

    def _json(self, payload: Dict[str, Any], status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/health":
            self._json({"ok": True, "status": "running", "version": APP_VERSION})
        else:
            self._json({"ok": False, "error": "rota desconhecida"}, 404)

    def do_POST(self):
        if self.path != "/execute":
            self._json({"ok": False, "error": "rota desconhecida"}, 404)
            return

        token = self.headers.get("X-AI-Bridge-Token", "")
        if not secrets.compare_digest(token, str(CFG.get("token", ""))):
            self._json({"ok": False, "error": "token inválido"}, 401)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json({"ok": False, "error": "Content-Length inválido"}, 400)
            return
        if length <= 0 or length > MAX_BODY:
            self._json({"ok": False, "error": "corpo inválido ou grande demais"}, 413)
            return

        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            command = payload.get("command", "")
            cwd = payload.get("cwd")
        except Exception:
            self._json({"ok": False, "error": "JSON inválido"}, 400)
            return

        result = execute_command(command, cwd)
        if GUI is not None:
            GUI.log_request(result)
        self._json(result, 200 if result.get("ok") else 400)

    def log_message(self, fmt, *args):
        return


class BridgeGUI:
    def __init__(self, root: tk.Tk):
        global GUI
        GUI = self
        self.root = root
        self.server = None
        self.thread = None
        self.running = False

        root.title(f"{APP_NAME} {APP_VERSION}")
        root.geometry("780x560")
        root.minsize(720, 520)
        root.configure(bg="#071421")
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.status_var = tk.StringVar(value="Parado")
        self.confirm_var = tk.BooleanVar(value=bool(CFG.get("require_confirmation", True)))

        title = tk.Frame(root, bg="#071421")
        title.pack(fill="x", padx=18, pady=(16, 8))
        tk.Label(title, text="AI Command Bridge", bg="#071421", fg="#f5f7fb",
                 font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(title, text="Ponte local segura para automação no Windows",
                 bg="#071421", fg="#19c6ff", font=("Segoe UI", 10, "bold")).pack(anchor="w")

        card = tk.Frame(root, bg="#0b1f30", padx=14, pady=12,
                        highlightthickness=1, highlightbackground="#1e4964")
        card.pack(fill="x", padx=18, pady=6)

        tk.Label(card, text="Status:", bg="#0b1f30", fg="white").grid(row=0, column=0, sticky="w")
        self.status_label = tk.Label(card, textvariable=self.status_var, bg="#0b1f30",
                                     fg="#ff5460", font=("Segoe UI", 10, "bold"))
        self.status_label.grid(row=0, column=1, sticky="w", padx=8)

        tk.Label(card, text="Endpoint:", bg="#0b1f30", fg="white").grid(row=1, column=0, sticky="w", pady=(8,0))
        tk.Label(card, text=f"http://{CFG.get('host', HOST)}:{CFG.get('port', DEFAULT_PORT)}/execute",
                 bg="#0b1f30", fg="#19c6ff").grid(row=1, column=1, sticky="w", padx=8, pady=(8,0))

        btns = tk.Frame(root, bg="#071421")
        btns.pack(fill="x", padx=18, pady=8)
        tk.Button(btns, text="▶ Iniciar", command=self.start_server, bg="#00a85a", fg="white",
                  relief="flat", padx=18, pady=8).pack(side="left", padx=(0,6))
        tk.Button(btns, text="■ Parar", command=self.stop_server, bg="#a82733", fg="white",
                  relief="flat", padx=18, pady=8).pack(side="left", padx=6)
        tk.Button(btns, text="⏻ Fechar", command=self.on_close, bg="#5d2c7d", fg="white",
                  relief="flat", padx=18, pady=8).pack(side="left", padx=6)
        tk.Button(btns, text="📁 Abrir configuração", command=self.open_config, bg="#174a6a", fg="white",
                  relief="flat", padx=18, pady=8).pack(side="right")

        sec = tk.Frame(root, bg="#0b1f30", padx=14, pady=10,
                       highlightthickness=1, highlightbackground="#1e4964")
        sec.pack(fill="x", padx=18, pady=6)

        tk.Checkbutton(sec, text="Pedir confirmação antes de cada comando",
                       variable=self.confirm_var, command=self.toggle_confirmation,
                       bg="#0b1f30", fg="white", selectcolor="#0b1f30",
                       activebackground="#0b1f30", activeforeground="white").pack(anchor="w")

        token_row = tk.Frame(sec, bg="#0b1f30")
        token_row.pack(fill="x", pady=(8,0))
        tk.Label(token_row, text="Token local:", bg="#0b1f30", fg="white").pack(side="left")
        self.token_entry = tk.Entry(token_row, show="•", width=52, readonlybackground="#071421",
                                    fg="white", bg="#071421", relief="flat")
        self.token_entry.pack(side="left", padx=8, ipady=4)
        self.token_entry.insert(0, str(CFG.get("token", "")))
        self.token_entry.config(state="readonly")
        tk.Button(token_row, text="Copiar", command=self.copy_token, bg="#174a6a", fg="white",
                  relief="flat").pack(side="left")

        tk.Label(root, text="Histórico desta sessão", bg="#071421", fg="white",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=18, pady=(10,4))

        self.log = tk.Text(root, bg="#06101a", fg="#c7d5df", insertbackground="white",
                           relief="flat", height=14, wrap="word")
        self.log.pack(fill="both", expand=True, padx=18, pady=(0,16))
        self.log.insert("end", "Servidor limitado a 127.0.0.1. Comandos exigem token e validação.\n")
        self.log.config(state="disabled")

    def write_log(self, line: str):
        self.log.config(state="normal")
        self.log.insert("end", line + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def start_server(self):
        if self.running:
            return
        host = str(CFG.get("host", HOST))
        port = int(CFG.get("port", DEFAULT_PORT))
        if host not in ("127.0.0.1", "localhost"):
            messagebox.showerror("Segurança", "Por segurança, o host deve ser 127.0.0.1.")
            return
        try:
            self.server = ThreadingHTTPServer((HOST, port), Handler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.running = True
            self.status_var.set(f"Rodando em {HOST}:{port}")
            self.status_label.config(fg="#00e676")
            self.write_log(f"Servidor iniciado em http://{HOST}:{port}")
        except Exception as exc:
            messagebox.showerror("Erro", str(exc))

    def stop_server(self):
        if self.server is not None:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
        self.server = None
        self.running = False
        self.status_var.set("Parado")
        self.status_label.config(fg="#ff5460")
        self.write_log("Servidor parado.")

    def request_confirmation(self, command: str, cwd: str) -> bool:
        event = threading.Event()
        result = {"ok": False}

        def ask():
            result["ok"] = messagebox.askyesno(
                "Autorizar comando",
                f"Uma solicitação quer executar:\n\n{command}\n\nPasta:\n{cwd}\n\nAutorizar?",
                parent=self.root,
            )
            event.set()

        self.root.after(0, ask)
        event.wait(60)
        return bool(result["ok"])

    def log_request(self, result: Dict[str, Any]):
        def update():
            status = "OK" if result.get("ok") else "ERRO"
            self.write_log(f"[{status}] {result.get('command','')} | {result.get('cwd','')}")
        self.root.after(0, update)

    def toggle_confirmation(self):
        CFG["require_confirmation"] = bool(self.confirm_var.get())
        save_config(CFG)

    def copy_token(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(str(CFG.get("token", "")))
        self.root.update()
        self.write_log("Token copiado para a área de transferência.")

    def open_config(self):
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        save_config(CFG)
        os.startfile(str(CONFIG_PATH))

    def on_close(self):
        self.stop_server()
        self.root.destroy()


def main():
    root = tk.Tk()
    BridgeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
