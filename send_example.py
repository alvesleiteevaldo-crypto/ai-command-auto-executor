import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
import subprocess


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
                "allowlist": ["dir ", "echo ", "git ", "npm ", "python ", "cd ", "type ", "where ", "whoami"],
                "blocklist": [
                    "format ",
                    "shutdown ",
                    "restart ",
                    "del /f /q c:",
                    "rd /s /q ",
                    "net user ",
                    "reg delete",
                    "taskkill /f",
                    "rm -rf /",
                    "sc delete"
                ],
                "allowed_cwds": ["C:/", "C:/Users"]
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

    # bloqueia execução de múltiplos comandos por segurança
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


def main():
    host = CFG.get("host", "127.0.0.1")
    port = int(CFG.get("port", 8765))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"AI bridge rodando em http://{host}:{port}")
    print("Use /health para testar e /execute para mandar comandos.")
    server.serve_forever()


if __name__ == "__main__":
    main()

