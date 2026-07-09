"""Colmena TTS - Texto a voz nativo con voces programadas.

Soporta pyttsx3 (SAPI5 local en Windows) y, opcionalmente, edge-tts como fallback.
Las voces programadas son nombres amigables mapeados a voces instaladas.
"""

import os
import sys
import tempfile
import threading
import time

BUILTIN_PRESETS = {
    # mexa / Colmena personalidad
    "memo": ("Microsoft Sabina Desktop", None),
    "mexa": ("Microsoft Sabina Desktop", None),
    "sabina": ("Microsoft Sabina Desktop", None),
    # inglesas
    "zira": ("Microsoft Zira Desktop", None),
    "art": ("Microsoft Zira Desktop", None),
    "helena": ("Microsoft Helena Desktop", None),
    "david": ("Microsoft David Desktop", None),
    "gringo": ("Microsoft David Desktop", None),
}


def _import_pyttsx3():
    try:
        import pyttsx3
        return pyttsx3
    except Exception as e:
        raise RuntimeError("pyttsx3 no está instalado. Corré: pip install pyttsx3") from e


def list_voices():
    """Devuelve lista de tuplas (índice, nombre) de voces instaladas."""
    pyttsx3 = _import_pyttsx3()
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    return [(i, v.name) for i, v in enumerate(voices)]


def resolve_voice_key(key):
    """Convierte un preset o índice en un índice de voz pyttsx3."""
    pyttsx3 = _import_pyttsx3()
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")

    if key is None:
        return None

    k = str(key).strip().lower()

    # 1. Si es índice numérico y es válido
    if k.isdigit():
        idx = int(k)
        if 0 <= idx < len(voices):
            return idx
        raise ValueError(f"Índice de voz {idx} fuera de rango. Hay {len(voices)} voces.")

    # 2. Preset por nombre exacto
    if k in BUILTIN_PRESETS:
        target, _ = BUILTIN_PRESETS[k]
        for i, v in enumerate(voices):
            if target.lower() in v.name.lower():
                return i
        raise RuntimeError(f"Preset '{key}' mapea a '{target}' pero no está instalada.")

    # 3. Substring libre (primera coincidencia)
    for i, v in enumerate(voices):
        if k in v.name.lower():
            return i

    raise RuntimeError(f"No encontré voz que coincida con '{key}'. Usá '--voice-list' para ver disponibles.")


def speak_pyttsx3(text, voice_index=None, rate=160, volume=1.0):
    pyttsx3 = _import_pyttsx3()
    engine = pyttsx3.init()
    if voice_index is not None:
        voices = engine.getProperty("voices")
        engine.setProperty("voice", voices[voice_index].id)
    engine.setProperty("rate", rate)
    engine.setProperty("volume", volume)
    engine.say(text)
    engine.runAndWait()


def speak_edge_tts(text, voice="es-MX-JorgeNeural"):
    """Fallback con edge-tts: genera mp3 y lo reproduce con lo que esté disponible."""
    try:
        import edge_tts
    except Exception as e:
        raise RuntimeError("edge-tts no está instalado. Corré: pip install edge-tts") from e

    async def _run():
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp.close()
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp.name)
        return tmp.name

    # edge-tts es async
    import asyncio
    mp3_path = asyncio.run(_run())

    # Intentar reproducir según plataforma
    if sys.platform == "win32":
        os.system(f'start "" "{mp3_path}"')
    elif sys.platform == "darwin":
        os.system(f"afplay '{mp3_path}'")
    else:
        os.system(f"mpg123 '{mp3_path}'")


def speak(text, voice=None, backend="auto", **kwargs):
    """Punto de entrada principal.

    - voice: preset (memo, sabina, zira, art, helena, david), nombre parcial o índice.
    - backend: 'pyttsx3', 'edge-tts' o 'auto'.
    """
    if not text or not text.strip():
        return

    if backend == "auto":
        backend = "pyttsx3"

    if backend == "pyttsx3":
        idx = resolve_voice_key(voice) if voice else None
        speak_pyttsx3(text, voice_index=idx, **kwargs)
    elif backend == "edge-tts":
        voice_id = voice if voice else "es-MX-JorgeNeural"
        speak_edge_tts(text, voice=voice_id)
    else:
        raise ValueError(f"Backend TTS desconocido: {backend}")


def print_voices():
    voices = list_voices()
    presets = BUILTIN_PRESETS.keys()
    print("🎙️  Voces instaladas:")
    for i, name in voices:
        print(f"   {i}: {name}")
    print("\n🎛️  Presets programados:")
    for p in sorted(presets):
        target, _ = BUILTIN_PRESETS[p]
        print(f"   --voice {p:<10} -> {target}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Colmena TTS")
    parser.add_argument("--list", action="store_true", help="Listar voces")
    parser.add_argument("--voice", default=None, help="Voz/preset (ej: memo, sabina, david)")
    parser.add_argument("--text", default=None, help="Texto a hablar")
    parser.add_argument("--rate", type=int, default=160, help="Velocidad de habla")
    args = parser.parse_args()

    if args.list or args.text is None:
        print_voices()
        sys.exit(0)

    speak(args.text, voice=args.voice, rate=args.rate)
