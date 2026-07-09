import argparse
import base64
import json
import sys
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434"


try:
    from colmena_animations import HexLoader as BeeSpinner, MessageReceiver, SplashScreen
except Exception:
    class BeeSpinner:
        def __init__(self, message="Colmena cargando"):
            self.message = message

        def start(self):
            return self

        def stop(self):
            pass

        def __enter__(self):
            return self.start()

        def __exit__(self, *args):
            self.stop()

    MessageReceiver = None
    SplashScreen = None

try:
    import colmena_tts
except Exception:
    colmena_tts = None

SPECIALISTS = {
    "vision": {
        "model": "colmena-vision",
        "description": "Análisis de imágenes, screenshots, diagramas, UI.",
    },
    "cloud_deep": {
        "model": "deepseek-v3.1:671b-cloud",
        "description": "Razonamiento profundo vía nube (requiere conexión y créditos).",
    },
    "cloud_general": {
        "model": "glm-5.1:cloud",
        "description": "Modelo general vía nube.",
    },
    "cloud_code": {
        "model": "gpt-oss:20b-cloud",
        "description": "Modelo cloud enfocado en código.",
    },
    "local": {
        "model": "colmena-one",
        "description": "Asistente local unificado (chat + código).",
    },
}


def ollama_chat(model, messages):
    payload = {"model": model, "messages": messages, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with BeeSpinner("🎭 Colmena router pensando"):
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as e:
        return {"error": str(e)}


def ollama_generate(model, prompt):
    payload = {"model": model, "prompt": prompt, "stream": False}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with BeeSpinner("🎭 Clasificando tarea"):
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode('utf-8', errors='ignore')}"}
    except Exception as e:
        return {"error": str(e)}


def classify_task(prompt):
    """Elige homúnculo de forma conservadora:
    - Cloud solo si el usuario lo pide explícitamente (para no gastar créditos).
    - Visión solo si se pasa imagen.
    - Todo lo demás va al local Colmena-One.
    """
    p = prompt.lower()
    if any(k in p for k in ("deepseek", "razona profundo", "nube razona", "deep reasoning")):
        return "cloud_deep"
    if any(k in p for k in ("gpt-oss", "nube code", "c\u00f3digo en la nube")):
        return "cloud_code"
    if any(k in p for k in ("glm", "nube general", "general en la nube")):
        return "cloud_general"
    return "local"


def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(
        description="Colmena Router: envía el prompt al homúnculo adecuado en Ollama."
    )
    parser.add_argument("prompt", nargs="?", help="Texto del usuario.")
    parser.add_argument("--imagen", "--image", help="Ruta a imagen (activa colmena-vision)")
    parser.add_argument(
        "--modelo",
        choices=list(SPECIALISTS.keys()),
        help="Forzar homúnculo específico en vez de auto-detectar.",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Hablar la respuesta final con una voz/preset (memo, sabina, david, zira, etc.).",
    )
    parser.add_argument(
        "--voice-list",
        action="store_true",
        help="Listar voces/presets disponibles y salir.",
    )
    args = parser.parse_args()

    if args.voice_list:
        if colmena_tts:
            colmena_tts.print_voices()
        else:
            print("⚠️  colmena_tts no disponible. Instalá pyttsx3.")
        sys.exit(0)

    if not args.prompt and not args.imagen:
        parser.error("Se requiere un PROMPT o una imagen (--imagen).")

    if SplashScreen:
        SplashScreen.show()

    if args.imagen:
        specialist = "vision"
        image_b64 = encode_image(args.imagen)
        messages = [
            {
                "role": "user",
                "content": args.prompt,
                "images": [image_b64],
            }
        ]
    else:
        specialist = args.modelo or classify_task(args.prompt)
        messages = [{"role": "user", "content": args.prompt}]

    info = SPECIALISTS[specialist]
    print(f"🎭 Colmena Router → {specialist} ({info['model']})")
    print(f"   {info['description']}\n")

    resp = ollama_chat(info["model"], messages)
    content = None
    if "error" in resp:
        print(f"❌ Error con {info['model']}: {resp['error']}")
        if specialist != "local":
            print("🔄 Fallback a colmena-one...")
            resp = ollama_chat("colmena-one", messages)
            if "error" in resp:
                print(f"❌ Fallback también falló: {resp['error']}")
                sys.exit(1)
            else:
                content = resp.get("message", {}).get("content", "(sin respuesta)")
        else:
            sys.exit(1)
    else:
        content = resp.get("message", {}).get("content", "(sin respuesta)")

    if content:
        if MessageReceiver and sys.stdout.isatty():
            MessageReceiver("📨 Mensaje entrante").play_and_wait()
        print(content)
        if args.voice and colmena_tts:
            try:
                colmena_tts.speak(content[:400], voice=args.voice)
            except Exception as e:
                print(f"⚠️  Error TTS: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
