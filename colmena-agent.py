import argparse
import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434"
MODEL = "colmena-one"
EMBEDDING_MODEL = "nomic-embed-text:latest"
VISION_MODEL = "colmena-vision"
MAX_ITERATIONS = 6

SYSTEM_PROMPT = """Eres Colmena-Agente: la versión operativa de Colmena-One con herramientas reales en la máquina local.

REGLAS DURAS:
- Solo invoca herramientas si realmente necesitas datos o acciones externas para responder.
- Nunca inventes resultados de herramientas. Si no puedes ejecutar algo, di "no verificado".
- Para operaciones destructivas o mutadoras (borrar, sobrescribir, ejecutar código/shell) pide confirmación al usuario o indícame que use --yes.
- No reveles secretos, tokens, contraseñas ni datos sensibles del usuario.
- Responde siempre en español mexicano: corto, claro, sin humo.
- Eres experto en múltiples lenguajes: Python, JavaScript/TypeScript, Go, Rust, C/C++, Java, Kotlin, shell/PowerShell y más. Para conocer el código de tus repositorios indexados, primero usa search_codebase.

PROTOCOLO DE HERRAMIENTAS:
- Invoca herramientas mediante tool_calls en JSON.
- Recibirás los resultados y podrás invocar otra herramienta o responder al usuario.
- Si el resultado es muy largo, resume lo relevante para la tarea.
- Si una herramienta no alcanza, explica por qué y detente.
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
                    "path": {"type": "string", "description": "Ruta del archivo (absoluta o relativa al directorio de trabajo)."},
                    "limit": {"type": "integer", "description": "Máximo de líneas a leer (default 200)."},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Crea o sobrescribe un archivo de texto. USAR SOLO si el usuario lo pide explícitamente o es obvio que quiere guardar algo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta del archivo a crear/sobrescribir."},
                    "content": {"type": "string", "description": "Contenido completo del archivo."},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Edita un archivo reemplazando old_string por new_string. USAR SOLO si el usuario pide modificar un archivo existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta del archivo."},
                    "old_string": {"type": "string", "description": "Texto exacto a reemplazar (debe aparecer en el archivo)."},
                    "new_string": {"type": "string", "description": "Texto nuevo que ocupará su lugar."},
                },
                "required": ["path", "old_string", "new_string"],
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
                    "include": {"type": "string", "description": "Glob de archivos a incluir (default '*')."},
                },
                "required": ["pattern", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Ejecuta un comando en la shell local (PowerShell en Windows, bash en Linux/Mac). USAR SOLO cuando sea necesario y seguro.",
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
            "name": "run_python",
            "description": "Ejecuta código Python temporalmente en un entorno aislado (un script temporal). Útil para cálculos, transformaciones de datos o automatización segura.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "Código Python completo a ejecutar."},
                    "explanation": {"type": "string", "description": "Breve explicación de qué hace el código."},
                },
                "required": ["code", "explanation"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Descarga el contenido de una URL pública (GET) y lo devuelve como texto. Útil para leer documentación o artículos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL completa (debe empezar con http:// o https://)."},
                    "max_chars": {"type": "integer", "description": "Máximo de caracteres a devolver (default 6000)."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_embedding",
            "description": "Genera un embedding vectorial de un texto usando nomic-embed-text. Útil para búsqueda semántica y comparación de similitud.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Texto a vectorizar."},
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_image",
            "description": "Analiza una imagen usando colmena-vision (basado en gemma3:4b). Devuelve una descripción o interpretación de la imagen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta de la imagen (jpg, png, etc.)."},
                    "prompt": {"type": "string", "description": "Pregunta o instrucción sobre la imagen (default: describe lo que ves)."},
                },
                "required": ["path"],
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
    {
        "type": "function",
        "function": {
            "name": "search_codebase",
            "description": "Busca información semántica en repositorios indexados con embeddings (usa la base de vectores de Colmena). Usar cuando la pregunta sea sobre código o documentación de tus repos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Pregunta o términos de búsqueda en lenguaje natural."},
                    "top_k": {"type": "integer", "description": "Cantidad máxima de resultados (default 5)."},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "index_codebase",
            "description": "Indexa un directorio/repositorio en la base de vectores de Colmena para búsqueda semántica futura. Puede tardar varios minutos en repos grandes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Ruta del repositorio/directorio a indexar."},
                },
                "required": ["path"],
            },
        },
    },
]

DANGEROUS_SHELL = [
    "rm ", "rm -", "remove-item", "del ", "erase", "format", "shutdown", "restart-computer",
    "stop-service", "kill ", "taskkill", "rd ", "rmdir", "> ", ">> ", "out-file", "set-content",
    "clear-content", "reg delete", "mkfs", "dd if", ":(){ :|:& };:", "Invoke-Expression", "iex",
    "wget -O", "curl -O", "Invoke-WebRequest", "certutil -f", "bitsadmin",
]

WORKING_DIR = os.getcwd()


def is_path_safe(path):
    """Marca como insegura rutas absolutas fuera del working dir o con '..'.
       En modo --yes se permite todo, aquí solo reportamos."""
    abs_path = os.path.abspath(path)
    try:
        rel = os.path.relpath(abs_path, WORKING_DIR)
    except Exception:
        return False, abs_path
    if rel.startswith("..") or os.path.isabs(path):
        return False, abs_path
    return True, abs_path


def truncate(text, length=6000, indicator="\n... (truncado)"):
    if text and len(text) > length:
        return text[:length] + indicator
    return text


def confirm(msg):
    try:
        ans = input(f"\n⚠️  {msg}\n   ¿Continuar? [s/N]: ").strip().lower()
    except EOFError:
        return False
    return ans in ("s", "si", "sí", "y", "yes")


def extract_json_tool_calls(content):
    """Extrae objetos JSON que parezcan llamadas a herramientas del contenido del LLM."""
    candidates = []

    try:
        obj = json.loads(content.strip())
        candidates.append(obj)
    except Exception:
        pass

    for block in re.findall(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL):
        try:
            obj = json.loads(block)
            candidates.append(obj)
        except Exception:
            pass

    for block in re.findall(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", content, re.DOTALL):
        try:
            obj = json.loads(block)
            candidates.append(obj)
        except Exception:
            pass

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
        if not isinstance(obj, dict):
            continue

        def norm_args(a):
            if isinstance(a, dict):
                return a
            if isinstance(a, str):
                try:
                    return json.loads(a)
                except Exception:
                    return {}
            return {}

        if "function" in obj:
            func = obj["function"]
            if isinstance(func, dict) and "name" in func:
                args = norm_args(func.get("arguments", {}))
                calls.append({"function": {"name": func["name"], "arguments": args}})
        elif "name" in obj:
            args = norm_args(obj.get("arguments", {}))
            calls.append({"function": {"name": obj["name"], "arguments": args}})

    return calls


def ollama_chat(messages, tools=None):
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3, "num_ctx": 8192},
    }
    if tools:
        payload["tools"] = tools
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as e:
        return {"error": str(e)}


def ollama_generate(model, prompt):
    payload = {"model": model, "prompt": prompt, "stream": False}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=900) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as e:
        return {"error": str(e)}


def ollama_embeddings(text):
    payload = {"model": EMBEDDING_MODEL, "prompt": text}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"error": str(e)}


def tool_read_file(path, limit=200):
    try:
        safe, abs_path = is_path_safe(path)
        if not safe:
            return f"⚠️ Ruta fuera del directorio de trabajo habitual. Para operar aquí, el usuario debe usar --yes. Ruta: {abs_path}"
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        total = len(lines)
        if limit and total > limit:
            content = "".join(lines[:limit])
            return f"(mostrando {limit} de {total} líneas)\n{content}"
        return "".join(lines)
    except Exception as e:
        return f"Error leyendo archivo: {e}"


def tool_write_file(path, content, auto_confirm=False):
    safe, abs_path = is_path_safe(path)
    if not safe and not auto_confirm:
        return f"⚠️ Ruta fuera del directorio de trabajo habitual. Usa --yes para permitir escribir aquí: {abs_path}"
    if os.path.exists(abs_path) and not auto_confirm:
        if not confirm(f"El archivo ya existe: {abs_path}\n¿Sobrescribir?"):
            return "Escritura cancelada por el usuario."
    try:
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Archivo escrito exitosamente: {abs_path} ({len(content)} caracteres)."
    except Exception as e:
        return f"Error escribiendo archivo: {e}"


def tool_edit_file(path, old_string, new_string, auto_confirm=False):
    safe, abs_path = is_path_safe(path)
    if not safe and not auto_confirm:
        return f"⚠️ Ruta fuera del directorio de trabajo habitual. Usa --yes para permitir editar aquí: {abs_path}"
    try:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
        if old_string not in text:
            return "No se encontró old_string en el archivo. Operación cancelada."
        if not auto_confirm:
            if not confirm(f"Se va a modificar el archivo: {abs_path}\n¿Continuar?"):
                return "Edición cancelada por el usuario."
        text = text.replace(old_string, new_string, 1)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(text)
        return f"Archivo editado exitosamente: {abs_path}"
    except Exception as e:
        return f"Error editando archivo: {e}"


def tool_list_directory(path="."):
    try:
        entries = os.listdir(path)
        lines = []
        for e in entries[:200]:
            full = os.path.join(path, e)
            kind = "DIR " if os.path.isdir(full) else "FILE"
            size = ""
            if os.path.isfile(full):
                size = f" ({os.path.getsize(full)} bytes)"
            lines.append(f"{kind}: {e}{size}")
        if len(entries) > 200:
            lines.append(f"... y {len(entries)-200} entradas más")
        return "\n".join(lines) if lines else "(directorio vacío)"
    except Exception as e:
        return f"Error listando directorio: {e}"


def tool_search_files(pattern, path, include="*"):
    results = []
    try:
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv", "venv", ".ollama"}]
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
    return any(k in c for k in DANGEROUS_SHELL)


def tool_run_shell(command, explanation, auto_confirm=False):
    if is_dangerous(command) and not auto_confirm:
        if not confirm(f"Comando potencialmente destructivo:\n   {command}\nRazón: {explanation}\n¿Ejecutar?"):
            return "Comando cancelado por el usuario."
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
            proc = subprocess.run(command, capture_output=True, text=True, timeout=60, shell=True)
        out = proc.stdout or ""
        err = proc.stderr or ""
        if proc.returncode != 0:
            return truncate(f"Exit code {proc.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}", 4000)
        combined = (out + err).strip()
        return truncate(combined or "(comando ejecutado sin salida)", 4000)
    except Exception as e:
        return f"Error ejecutando comando: {e}"


def tool_run_python(code, explanation, auto_confirm=False):
    if not auto_confirm:
        summary = textwrap.shorten(code, width=120, placeholder="...")
        if not confirm(f"Se va a ejecutar código Python:\n   {summary}\nRazón: {explanation}\n¿Continuar?"):
            return "Ejecución cancelada por el usuario."
    try:
        fd, tmp_path = tempfile.mkstemp(suffix=".py")
        os.write(fd, code.encode("utf-8"))
        os.close(fd)
        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=WORKING_DIR,
        )
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        out = proc.stdout or ""
        err = proc.stderr or ""
        if proc.returncode != 0:
            return truncate(f"Exit code {proc.returncode}\nSTDOUT:\n{out}\nSTDERR:\n{err}", 4000)
        return truncate(out.strip() or "(script ejecutado sin salida)", 4000)
    except Exception as e:
        return f"Error ejecutando Python: {e}"


def tool_web_fetch(url, max_chars=6000):
    if not url.startswith(("http://", "https://")):
        return "URL inválida. Solo se permiten http:// o https://"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Colmena-Agent"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read(200_000)
            charset = resp.headers.get_content_charset() or "utf-8"
            text = raw.decode(charset, errors="ignore")
            return truncate(text, max_chars)
    except Exception as e:
        return f"Error descargando URL: {e}"


def tool_compute_embedding(text):
    resp = ollama_embeddings(text)
    if "error" in resp:
        return f"Error en embeddings: {resp['error']}"
    vec = resp.get("embedding", [])
    if not vec:
        return "No se recibió embedding."
    preview = ", ".join(f"{v:.4f}" for v in vec[:8])
    return f"Embedding generado. Dimensiones: {len(vec)}. Primeros valores: [{preview}, ...]"


def tool_analyze_image(path, prompt="describe lo que ves", auto_confirm=False):
    safe, abs_path = is_path_safe(path)
    if not safe and not auto_confirm:
        return f"⚠️ Ruta fuera del directorio de trabajo habitual. Usa --yes para analizar aquí: {abs_path}"
    try:
        with open(abs_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        return f"Error leyendo imagen: {e}"
    messages = [
        {
            "role": "user",
            "content": prompt,
            "images": [b64],
        }
    ]
    return ollama_chat_raw(VISION_MODEL, messages)


def ollama_chat_raw(model, messages):
    payload = {"model": model, "messages": messages, "stream": False}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            d = json.loads(resp.read().decode("utf-8"))
            return d.get("message", {}).get("content", "(sin respuesta)")
    except Exception as e:
        return f"Error en chat con visión: {e}"


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
        return f"OS: {platform.system()} {platform.release()}\nDir de trabajo: {WORKING_DIR}\nModelos Ollama: {models}"
    except Exception as e:
        return f"Error resumiendo entorno: {e}"


DEFAULT_VECTOR_DB = os.path.join(os.path.expanduser("~"), ".colmena", "vectordb.json")


def _indexer_path():
    local = os.path.join(os.path.dirname(os.path.abspath(__file__)), "colmena-index.py")
    return local if os.path.exists(local) else "colmena-index.py"


def tool_search_codebase(query, top_k=5):
    if not os.path.exists(DEFAULT_VECTOR_DB):
        return "No hay base de vectores indexada. Ejecutá primero: python colmena-index.py index <ruta>"
    cmd = [sys.executable, _indexer_path(), "search", query, "--db", DEFAULT_VECTOR_DB, "--top-k", str(top_k)]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        return truncate((proc.stdout or "") + (proc.stderr or ""), 6000)
    except Exception as e:
        return f"Error buscando en base de vectores: {e}"


def tool_index_codebase(path):
    cmd = [sys.executable, _indexer_path(), "index", path, "--db", DEFAULT_VECTOR_DB]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        return truncate((proc.stdout or "") + (proc.stderr or ""), 6000)
    except Exception as e:
        return f"Error indexando repositorio: {e}"


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
    elif name == "write_file":
        return name, tool_write_file(args.get("path"), args.get("content", ""), auto_confirm)
    elif name == "edit_file":
        return name, tool_edit_file(args.get("path"), args.get("old_string", ""), args.get("new_string", ""), auto_confirm)
    elif name == "list_directory":
        return name, tool_list_directory(args.get("path", "."))
    elif name == "search_files":
        return name, tool_search_files(args.get("pattern"), args.get("path"), args.get("include", "*"))
    elif name == "run_shell":
        return name, tool_run_shell(args.get("command"), args.get("explanation", ""), auto_confirm)
    elif name == "run_python":
        return name, tool_run_python(args.get("code"), args.get("explanation", ""), auto_confirm)
    elif name == "web_fetch":
        return name, tool_web_fetch(args.get("url"), args.get("max_chars", 6000))
    elif name == "compute_embedding":
        return name, tool_compute_embedding(args.get("text", ""))
    elif name == "analyze_image":
        return name, tool_analyze_image(args.get("path"), args.get("prompt", "describe lo que ves"), auto_confirm)
    elif name == "get_environment_summary":
        return name, tool_get_environment_summary()
    elif name == "search_codebase":
        return name, tool_search_codebase(args.get("query"), args.get("top_k", 5))
    elif name == "index_codebase":
        return name, tool_index_codebase(args.get("path"))
    else:
        return name, f"Herramienta desconocida: {name}"


def main():
    parser = argparse.ArgumentParser(
        description="Colmena-Agente: agente local con herramientas reales."
    )
    parser.add_argument("prompt", help="Tarea o pregunta para el agente.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Permite operaciones destructivas/mutadoras sin confirmación interactiva (¡cuidado!).",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=MAX_ITERATIONS,
        help=f"Máximo de iteraciones de herramientas (default {MAX_ITERATIONS}).",
    )
    args = parser.parse_args()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": args.prompt},
    ]

    for i in range(args.max_iters):
        resp = ollama_chat(messages, tools=TOOLS)
        if "error" in resp:
            print(f"❌ Error de Ollama: {resp['error']}")
            sys.exit(1)

        message = resp.get("message", {})
        content = message.get("content", "")
        tool_calls = message.get("tool_calls")

        # Adaptar si el modelo devuelve JSON en texto en vez de tool_calls nativo
        if not tool_calls and content:
            parsed = extract_json_tool_calls(content)
            if parsed:
                tool_calls = parsed
                content = re.sub(r"<tool_call>.*?</tool_call>", "", content, flags=re.DOTALL).strip()
                content = re.sub(r"```(?:json)?\s*.*?\s*```", "", content, flags=re.DOTALL).strip()

        if not tool_calls:
            print(content or "(sin respuesta)")
            return

        print(f"🛠️  Iteración {i+1}: invocando {len(tool_calls)} herramienta(s)...")
        for call in tool_calls:
            name, result = execute_tool(call, auto_confirm=args.yes)
            print(f"   → {name}")
            # No imprimir el resultado completo para no saturar la conversación; dejarlo en messages
            if len(result) > 300:
                print(f"      ({len(result)} caracteres devueltos)")
            else:
                for line in result.splitlines()[:3]:
                    print(f"      {line}")
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [call],
            })
            messages.append({
                "role": "tool",
                "content": result,
            })

    print("⚠️  Se alcanzó el máximo de iteraciones. El agente no terminó de responder.")


if __name__ == "__main__":
    main()
