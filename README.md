# ai-command-auto-executor

Programa local para receber comandos de uma IA e executá-los automaticamente no CMD/PowerShell do Windows.

Funciona como um bridge entre a IA e o terminal do PC.

O que ele faz:
- recebe um comando em JSON via HTTP
- valida segurança
- executa no CMD/PowerShell
- retorna stdout, stderr e código de saída

Como usar:

1. Abra o terminal e rode:

```powershell
python ai_bridge.py
```

2. Em seguida, use o endpoint:

- GET http://127.0.0.1:8765/health
- POST http://127.0.0.1:8765/execute

Exemplo de JSON:

```json
{
  "command": "dir C:\\Users",
  "cwd": "C:\\Users"
}
```

3. Resposta:

```json
{
  "ok": true,
  "command": "dir C:\\Users",
  "exit_code": 0,
  "stdout": "...",
  "stderr": "",
  "cwd": "C:\\Users"
}
```

Segurança:
- lista branca (`allowlist`)
- lista negra (`blocklist`)
- bloqueia comandos perigosos por padrão
- recomendado usar em ambiente local controlado

Para integrar com seu agente local:
- a IA pode chamar `http://127.0.0.1:8765/execute` com o comando solicitado
- o bridge executa no shell
- o resultado volta em JSON

Observação:
- este projeto é um starter seguro para execução local
- não execute como administrador sem revisar a lista permitida

