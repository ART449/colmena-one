import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434"
MODEL = "colmena-one"
MAX_ITERATIONS = 5


def extract_json_tool_calls(content):
    """Extrae objetos JSON que parezcan llamadas a herramientas del contenido del LLM."""
    candidates = []

    # 1) Intentar parsear todo el contenido como JSON
    try:
        obj = json.loads(content.strip())
        candidates.append(obj)
    except Exception:
        pass

    # 2) Buscar bloques ```json ... ```
    for block in re.findall(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL):
        try:
            obj = json.loads(block)
            candidates.append(obj)
        except Exception:
            pass

    # 3) Buscar bloques <tool_call>...</tool_call>
    for block in re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL):
        try:
            obj = json.loads(block)
            candidates.append(obj)
        except Exception:
            pass

    # 4) Buscar objetos JSON genéricos por balance de llaves
    if not candidates:
        brace_count = 0
        start = -1
        for i, ch in enumerate(content):
            if ch == "{":
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0 and start >= 0:
                    try:
                        obj = json.loads(content[start:i + 1])
                        candidates.append(obj)
                    except Exception:
                        pass
                    start = -1

    calls = []
    for obj in candidates:
        if isinstance(obj, dict):
            # Normalizar a diccionario de argumentos
            def norm_args(a):
                if isinstance(a, dict):
                    return a
                if isinstance(a, str):
                    try:
                        return json.loads(a)
                    except Exception:
                        return {}
                return {}

            # Formato {"function": {"name": ..., "arguments": ...}}
            if "function" in obj:
                func = obj["function"]
                if isinstance(func, dict) and "name" in func:
                    args = norm_args(func.get("arguments", {}))
                    calls.append({"function": {"name": func["name"], "arguments": args}})
            # Formato {"name": ..., "arguments": ...}
            elif "name" in obj:
                args = norm_args(obj.get("arguments", {}))
                calls.append({"function": {"name": obj["name"], "arguments": args}})

    return calls


SYSTEM_PROMPT = """Eres Colmena-Agente, la versión operativa de Colmena-One con herramientas reales en la máquina local.

REGLAS DURAS:
- Solo invoca una herramienta si realmente necesitas datos externos para responder.
- Nunca inventes resultados de herramientas. Si no puedes ejecutar algo, di "no verificado".
- Para comandos destructivos (borrar, formatear, detener servicios, etc.) pide confirmación al usuario antes de ejecutar.
- No reveles secretos ni datos sensibles.
- Responde siempre en español mexicano: corto, claro, sin humo.

PROTOCOLO DE HERRAMIENTAS:
- Las herramientas se invocan mediante tool_calls en JSON.
- Recibirás los resultados y podrás invocar otra herramienta o responder al usuario.
- Si el resultado es muy largo, resume lo relevante.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee el contenido de un archivo de texto local.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta absoluta o relativa del archivo."},
                    "limit": {"type": "integer", "description": "Máximo de líneas a leer (default 200)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "Lista archivos y carpetas de un directorio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta del directorio (default directorio actual)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "Busca un patrón de texto dentro de archivos de un directorio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Texto o regex a buscar."},
                    "path": {"type": "string", "description": "Directorio donde buscar."},
                    "include": {"type": "string", "description": "Glob de archivos a incluir, ej. '*.py' (default '*')."},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Ejecuta un comando en la shell local (PowerShell en Windows, bash en Linux/Mac).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Comando a ejecutar."},
                    "explanation": {"type": "string", "description": "Breve explicación de por qué es necesario."},
                },
                "required": ["command", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_environment_summary",
            "description": "Obtiene un resumen del entorno: sistema operativo, modelos Ollama disponibles y directorio actual.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]

DANGEROUS_KEYWORDS = [
    "rm ", "rm -", "remove-item", "del ", "erase", "format", "shutdown", "restart-computer",
    "stop-service", "kill ", "taskkill", "rd ", "rmdir", "> ", "out-file", "set-content", "clear-content",
    "reg delete", "mkfs", "dd if", ":(){ :|:& };:", "Invoke-Expression", "iex",
]


def ollama_chat(messages, tools=None):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 8192},
    }
    if tools:
        payload["tools"] = tools
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as e:
        return {"error": str(e)}


def tool_read_file(path, limit=200):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        total = len(lines)
        if limit and total > limit:
            content = "".join(lines[:limit])
            return f"(mostrando {limit} de {total} líneas)\n{content}"
        return "".join(lines)
    except Exception as e:
        return f"Error leyendo archivo: {e}"


def tool_list_directory(path="."):
    try:
        entries = os.listdir(path)
        lines = []
        for e in entries:
            full = os.path.join(path, e)
            kind = "DIR " if os.path.isdir(full) else "FILE"
            size = ""
            if os.path.isfile(full):
                size = f" ({os.path.getsize(full)} bytes)"
            lines.append(f"{kind}: {e}{size}")
        return "\n".join(lines) if lines else "(directorio vacío)"
    except Exception as e:
        return f"Error listando directorio: {e}"


def tool_search_files(pattern, path, include="*"):
    results = []
    try:
        for root, dirs, files in os.walk(path):
            # skip venvs, node_modules, .git, etc.
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv", "venv"}]
            for fn in files:
                if include != "*" and not re.search(include.replace("*", ".*"), fn):
                    continue
                full = os.path.join(root, fn)
                try:
                    with open(full, "r", encoding="utf-8", errors="ignore") as f:
                        for i, line in enumerate(f, 1):
                            if re.search(pattern, line, re.IGNORECASE):
                                results.append(f"{full}:{i}: {line.strip()}")
                                if len(results) >= 50:
                                    break
                        if len(results) >= 50:
                            break
                except Exception:
                    continue
            if len(results) >= 50:
                break
        if not results:
            return "No se encontraron coincidencias."
        return "\n".join(results[:50])
    except Exception as e:
        return f"Error buscando archivos: {e}"


def is_dangerous(command):
    c = command.lower()
    return any(k in c for k in DANGEROUS_KEYWORDS)


def tool_run_shell(command, explanation, auto_confirm=False):
    if is_dangerous(command) and not auto_confirm:
        print(f"\n⚠️  Comando potencialmente destructivo:")
        print(f"   {command}")
        print(f"   Razón: {explanation}")
        ans = input("   ¿Ejecutar? [s/N]: ").strip().lower()
        if ans not in ("s", "si", "sí"):
            return "Cancelado por el usuario."
    try:
        if os.name == "nt":
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", command],
                capture_output=True,
                text=True,
                timeout=60,
                shell=False,
            )
        else:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                shell=True,
            )
        out = proc.stdout or ""
        err = proc.stderr or ""
        if proc.returncode != 0:
            return f"Exit code {proc.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        # trim long output
        combined = (out + err).strip()
        if len(combined) > 4000:
            combined = combined[:4000] + "\n... (output truncado)"
        return combined or "(comando ejecutado sin salida)"
    except Exception as e:
        return f"Error ejecutando comando: {e}"


def tool_get_environment_summary():
    try:
        import platform
        models = "no verificado"
        try:
            req = urllib.request.Request(f"{OLLAMA_URL}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                names = [m.get("name") for m in data.get("models", [])]
                models = ", ".join(names) if names else "ninguno"
        except Exception as e:
            models = f"error: {e}"
        return f"OS: {platform.system()} {platform.release()}\nDir actual: {os.getcwd()}\nModelos Ollama: {models}"
    except Exception as e:
        return f"Error resumiendo entorno: {e}"


def execute_tool(call, auto_confirm=False):
    name = call.get("function", {}).get("name")
    args = call.get("function", {}).get("arguments", {}) or {}
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except Exception:
            args = {}
    if name == "read_file":
        return name, tool_read_file(args.get("path"), args.get("limit", 200))
    elif name == "list_directory":
        return name, tool_list_directory(args.get("path", "."))
    elif name == "search_files":
        return name, tool_search_files(args.get("pattern"), args.get("path"), args.get("include", "*"))
    elif name == "run_shell":
        return name, tool_run_shell(args.get("command"), args.get("explanation", ""), auto_confirm)
    elif name == "get_environment_summary":
        return name, tool_get_environment_summary()
    else:
        return name, f"Herramienta desconocida: {name}"


def main():
    parser = argparse.ArgumentParser(
        description="Colmena-Agente: Colmena-One con herramientas reales."
    )
    parser.add_argument("prompt", help="Tarea o pregunta para el agente.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Permite ejecutar comandos de shell destructivos sin confirmación (¡cuidado!).",
    )
    args = parser.parse_args()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": args.prompt},
    ]

    for i in range(MAX_ITERATIONS):
        resp = ollama_chat(messages, tools=TOOLS)
        if "error" in resp:
            print(f"❌ Error de Ollama: {resp['error']}")
            sys.exit(1)

        message = resp.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")

        # Some Ollama versions put tool_calls in content as text/markdown; try to detect
        if not tool_calls and content:
            raw_calls = extract_json_tool_calls(content)
            if raw_calls:
                tool_calls = raw_calls
                # strip all JSON-ish tool text from displayed content
                content = re.sub(r"<tool_call>.*?</tool_call>", "", content, flags=re.DOTALL).strip()
                content = re.sub(r"```(?:json)?\s*.*?\s*```", "", content, flags=re.DOTALL).strip()

        if not tool_calls:
            print(content or "(sin respuesta)")
            return

        # Execute tool calls
        print(f"🔧 Iteración {i+1}: invocando {len(tool_calls)} herramienta(s)...")
        for call in tool_calls:
            name, result = execute_tool(call, auto_confirm=args.yes)
            print(f"   → {name}")
            messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": [call],
            })
            messages.append({
                "role": "tool",
                "content": result,
            })

    print("⚠️  Se alcanzó el máximo de iteraciones. El agente no terminó de responder.")


if __name__ == "__main__":
    main()
