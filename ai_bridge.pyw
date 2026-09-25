import json
import os
import sys
import threading
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
import subprocess
import tkinter as tk
from tkinter import messagebox
import webbrowser


class Config:
    def __init__(self, path: str = "config.json"):
        self.path = path
        self.data = self._load()

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {
                "host": "127.0.0.1",
                "port": 8765,
                "require_confirmation": False,
                "strict_mode": True,
                "allowlist": ["git ", "npm ", "node ", "python ", "py ", "dir ", "type ", "copy ", "move ", "mkdir ", "rmdir ", "cd ", "echo ", "where ", "echo.", "cls", "ipconfig", "whoami", "systeminfo", "curl ", "powershell ", "start "],
                "blocklist": [
                    "format ",
                    "shutdown ",
                    "restart ",
                    "poweroff",
                    "del /f /q c:",
                    "rd /s /q ",
                    "rmdir /s /q ",
                    "net user ",
                    "net localgroup administrators",
                    "sc delete",
                    "reg delete",
                    "Remove-Item -Recurse -Force /",
                    "rm -rf /",
                    "taskkill /f",
                    "diskpart",
                    "bcdedit",
                    "attrib +s +h",
                    "mklink /d",
                    "explorer.exe",
                    "start /b cmd"
                ],
                "allowed_cwds": [
                    "C:/",
                    "C:/Users"
                ]
            }

        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get(self, key: str, default=None):
        return self.data.get(key, default)


CFG = Config()


def is_windows() -> bool:
    return os.name == "nt"


def normalize_command(cmd: str) -> str:
    return cmd.strip()


def matches_allowlist(cmd: str, allowlist) -> bool:
    if not allowlist:
        return True

    lowered = cmd.lower()
    for pattern in allowlist:
        if pattern.lower() in lowered:
            return True
    return False


def contains_blocked_pattern(cmd: str, blocklist) -> bool:
    if not blocklist:
        return False

    lowered = cmd.lower()
    for pattern in blocklist:
        if pattern.lower() in lowered:
            return True
    return False


def is_command_safe(command: str, config: Dict[str, Any]) -> tuple[bool, str]:
    cmd = normalize_command(command)
    if not cmd:
        return False, "Comando vazio."

    if ";" in cmd or "&&" in cmd or "||" in cmd:
        return False, "Comandos encadeados não são permitidos neste bridge."

    if contains_blocked_pattern(cmd, config.get("blocklist", [])):
        return False, "Comando bloqueado pela lista negra."

    strict_mode = config.get("strict_mode", True)
    if strict_mode:
        if not matches_allowlist(cmd, config.get("allowlist", [])):
            return False, "Comando não está na lista branca permitida."

    return True, "ok"


def execute_shell_command(command: str, cwd: str = None) -> Dict[str, Any]:
    if is_windows():
        shell_cmd = ["cmd", "/s", "/c", command]
    else:
        shell_cmd = ["bash", "-lc", command]

    try:
        result = subprocess.run(
            shell_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=180,
            shell=False,
        )
        return {
            "ok": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": command,
            "cwd": cwd,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "exit_code": 124,
            "stdout": exc.stdout or "",
            "stderr": "Comando excedeu o tempo limite.",
            "command": command,
            "cwd": cwd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": str(exc),
            "command": command,
            "cwd": cwd,
        }


class Handler(BaseHTTPRequestHandler):
    server_version = "AICommandBridge/1.0"

    def _send_json(self, payload: Dict[str, Any], status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send_json({"ok": True, "status": "running"})
            return
        self._send_json({"ok": False, "error": "rota desconhecida"}, 404)

    def do_POST(self):
        if self.path != "/execute":
            self._send_json({"ok": False, "error": "rota desconhecida"}, 404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send_json({"ok": False, "error": "JSON inválido."}, 400)
            return

        command = payload.get("command", "")
        cwd = payload.get("cwd")

        ok, message = is_command_safe(command, CFG.data)
        if not ok:
            self._send_json({"ok": False, "error": message, "command": command}, 403)
            return

        result = execute_shell_command(command, cwd=cwd)
        self._send_json(result)

    def log_message(self, format: str, *args):
        return


class AIBridgeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Command Bridge")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        self.server = None
        self.server_thread = None
        self.running = False

        # Labels
        tk.Label(root, text="AI Command Bridge v1.0", font=("Arial", 16, "bold")).pack(pady=20)
        tk.Label(root, text="Servidor para executar comandos de IA no CMD/PowerShell", font=("Arial", 10)).pack()

        # Status
        self.status_label = tk.Label(root, text="Status: Parado", font=("Arial", 12), fg="red")
        self.status_label.pack(pady=10)

        # Info
        tk.Label(root, text="http://127.0.0.1:8765", font=("Arial", 10), fg="blue").pack()

        # Buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=20)

        tk.Button(button_frame, text="Iniciar", command=self.start_server, width=15, bg="green", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Parar", command=self.stop_server, width=15, bg="red", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Configurar", command=self.open_config, width=15, bg="blue", fg="white").pack(side=tk.LEFT, padx=5)

        # Info text
        info_text = tk.Text(root, height=12, width=70, bg="#f0f0f0", state=tk.DISABLED)
        info_text.pack(pady=10, padx=10)

        info_text.config(state=tk.NORMAL)
        info_text.insert(tk.END, "Instruções de uso:\n\n")
        info_text.insert(tk.END, "1. Clique em 'Iniciar' para começar o servidor\n")
        info_text.insert(tk.END, "2. Configure a IA para enviar comandos para:\n")
        info_text.insert(tk.END, "   POST http://127.0.0.1:8765/execute\n\n")
        info_text.insert(tk.END, "3. Formato JSON esperado:\n")
        info_text.insert(tk.END, '   {"command": "seu_comando", "cwd": "C:\\\\path"}\n\n')
        info_text.insert(tk.END, "4. Por segurança, apenas comandos permitidos são executados\n")
        info_text.insert(tk.END, "5. Edite config.json para adicionar/bloquear comandos\n\n")
        info_text.insert(tk.END, "GitHub: github.com/alvesleiteevaldo-crypto/ai-command-auto-executor")
        info_text.config(state=tk.DISABLED)

    def start_server(self):
        if self.running:
            messagebox.showwarning("Aviso", "Servidor já está rodando!")
            return

        host = CFG.get("host", "127.0.0.1")
        port = int(CFG.get("port", 8765))

        try:
            self.server = ThreadingHTTPServer((host, port), Handler)
            self.running = True
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()
            self.status_label.config(text=f"Status: Rodando em {host}:{port}", fg="green")
            messagebox.showinfo("Sucesso", f"Servidor iniciado em http://{host}:{port}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao iniciar servidor: {e}")
            self.running = False

    def stop_server(self):
        if not self.running:
            messagebox.showwarning("Aviso", "Servidor não está rodando!")
            return

        try:
            self.server.shutdown()
            self.running = False
            self.status_label.config(text="Status: Parado", fg="red")
            messagebox.showinfo("Sucesso", "Servidor parado")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao parar servidor: {e}")

    def open_config(self):
        config_path = Path("config.json").resolve()
        if config_path.exists():
            os.startfile(config_path)
        else:
            messagebox.showerror("Erro", "Arquivo config.json não encontrado")


def main():
    root = tk.Tk()
    gui = AIBridgeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
