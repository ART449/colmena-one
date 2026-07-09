import sys
import threading
import time


class _BaseAnimation:
    """Base común para animaciones de terminal."""

    def __init__(self, message="Colmena"):
        self.message = message
        self._stop = threading.Event()
        self._thread = None

    def _clear(self, width=80):
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * width + "\r")
            sys.stdout.flush()

    def _show(self, text):
        if sys.stdout.isatty():
            sys.stdout.write(f"\r{text}")
            sys.stdout.flush()

    def stop(self):
        if self._thread is None:
            return
        self._stop.set()
        self._thread.join(timeout=0.6)
        self._clear()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


class HexLoader(_BaseAnimation):
    """Abejita volando sobre un panal de hexágonos; llena uno por uno."""

    FRAMES = [
        "⬡ ⬡ ⬡ ⬡ ⬡  🐝",
        "⬢ ⬡ ⬡ ⬡ ⬡   🐝",
        "⬢ ⬢ ⬡ ⬡ ⬡    🐝",
        "⬢ ⬢ ⬢ ⬡ ⬡     🐝",
        "⬢ ⬢ ⬢ ⬢ ⬡      🐝",
        "⬢ ⬢ ⬢ ⬢ ⬢       🐝",
        "🐝 ⬢ ⬢ ⬢ ⬢ ⬢     ",
        "  🐝 ⬢ ⬢ ⬢ ⬢    ",
        "   🐝 ⬢ ⬢ ⬢     ",
        "    🐝 ⬢ ⬢      ",
        "     🐝 ⬢       ",
        "      🐝        ",
    ]

    def start(self):
        if not sys.stdout.isatty():
            return self

        def _spin():
            i = 0
            while not self._stop.is_set():
                frame = self.FRAMES[i % len(self.FRAMES)]
                self._show(f"{self.message} {frame}")
                time.sleep(0.18)
                i += 1
            self._clear()

        self._thread = threading.Thread(target=_spin, daemon=True)
        self._thread.start()
        return self


class BeeSwarmLoader(_BaseAnimation):
    """Enjambre de abejas zumbando alrededor de un hexágono."""

    FRAMES = [
        "        ⬡        ",
        "      🐝 ⬡        ",
        "    ⬡   ⬡   🐝     ",
        "      ⬡ 🐝 ⬡       ",
        "   🐝  ⬡  🐝        ",
        "      ⬡    🐝      ",
        "🐝   ⬡             ",
        "   ⬡     🐝        ",
    ]

    def start(self):
        if not sys.stdout.isatty():
            return self

        def _spin():
            i = 0
            while not self._stop.is_set():
                frame = self.FRAMES[i % len(self.FRAMES)]
                self._show(f"{self.message} {frame}")
                time.sleep(0.16)
                i += 1
            self._clear()

        self._thread = threading.Thread(target=_spin, daemon=True)
        self._thread.start()
        return self


class MessageReceiver(_BaseAnimation):
    """Animación corta para cuando llega un mensaje / respuesta."""

    FRAMES = [
        "📡  ~ ~ ~  🐝          ",
        "📡 ~ ~ ~   🐝          ",
        "📡~ ~ ~     🐝          ",
        "✉️  🐝                 ",
        "✉️   🐝                ",
        "✉️    🐝               ",
        "🍯 ⬢                  ",
        "🍯  ⬢                 ",
        "🍯   ⬢                ",
    ]

    def start(self):
        if not sys.stdout.isatty():
            return self

        def _run_once():
            for frame in self.FRAMES:
                if self._stop.is_set():
                    break
                self._show(f"{self.message} {frame}")
                time.sleep(0.18)
            self._clear()

        self._thread = threading.Thread(target=_run_once, daemon=True)
        self._thread.start()
        return self

    def play_and_wait(self):
        """Bloquea hasta terminar la animación (útil tras recibir respuesta)."""
        self.start()
        self._thread.join(timeout=4)
        self._clear()


class SplashScreen:
    """Pantalla de inicio estática con arte de panal + abejas."""

    ART = """
        🍯  COLMENA  🍯
       ⬡  ⬡  ⬡  ⬡  ⬡
        ⬢      🐝    ⬢
       ⬡  ⬡  ⬡  ⬡  ⬡
        ⬢    ⬢    ⬢
       ⬡  ⬡  ⬡  ⬡  ⬡
       ~~~ zumbando ~~~
    """.strip()

    @classmethod
    def show(cls):
        if sys.stdout.isatty():
            print(cls.ART)


# Alias backwards-compatible para el viejo BeeSpinner
BeeSpinner = HexLoader
