import json
import urllib.request


def send_command(command: str, cwd: str = None):
    payload = {"command": command}
    if cwd:
        payload["cwd"] = cwd

    req = urllib.request.Request(
        "http://127.0.0.1:8765/execute",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=180) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    result = send_command("dir C:\\Users")
    print(json.dumps(result, ensure_ascii=False, indent=2))


