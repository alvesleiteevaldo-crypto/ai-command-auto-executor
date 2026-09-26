# AI Command Bridge 2.0

Aplicativo local para Windows 10/11 que recebe solicitações de automação em JSON e executa somente comandos permitidos.

## Segurança da versão 2.0

- servidor preso a `127.0.0.1`
- token local obrigatório no header `X-AI-Bridge-Token`
- confirmação visual por comando ativada por padrão
- allowlist por nome exato do executável
- bloqueio de operadores de shell como `& | > < ^`
- restrição da pasta de trabalho às áreas permitidas
- limite do corpo HTTP e timeout de execução
- configuração salva em `%APPDATA%\AICommandBridge\config.json`

## Executar em desenvolvimento

```powershell
python ai_bridge_v2.pyw
```

## Compilar no Windows

Dê dois cliques em:

`build_exe.bat`

Ele cria:

- `dist\AICommandBridge.exe`
- `dist\installer\AICommandBridge-Setup-2.0.0.exe` quando Inno Setup 6 estiver instalado.

## API

Teste:

`GET http://127.0.0.1:8765/health`

Execução:

`POST http://127.0.0.1:8765/execute`

Header:

`X-AI-Bridge-Token: <token mostrado pelo aplicativo>`

JSON:

```json
{
  "command": "git status",
  "cwd": "C:\\Users\\SeuUsuario\\Projeto"
}
```

> O bridge é local. Um ChatGPT executando na nuvem não alcança automaticamente `127.0.0.1`; é necessário um cliente ou conector local que envie as requisições para ele.
