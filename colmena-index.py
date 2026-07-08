import argparse
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434"
EMBEDDING_MODEL = "nomic-embed-text:latest"

# Extensiones útiles para repositorios de código, documentación y config.
CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs",
    ".c", ".cpp", ".h", ".hpp", ".java", ".kt", ".swift",
    ".rb", ".php", ".cs", ".sh", ".ps1", ".bat", ".cmd",
    ".yaml", ".yml", ".json", ".toml", ".ini", ".cfg",
    ".md", ".txt", ".modelfile", "Dockerfile", ".tf", ".bicep",
}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    "dist", "build", "target", ".idea", ".vscode", ".ollama",
    ".cache", "coverage", "out", "bin", "obj",
}

MAX_FILE_BYTES = 500_000
CHUNK_SIZE = 1_500
CHUNK_OVERLAP = 200


def get_embedding(text):
    payload = {"model": EMBEDDING_MODEL, "prompt": text}
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/embeddings",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        d = json.loads(resp.read().decode("utf-8"))
    return d.get("embedding", [])


def chunk_file(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Divide un texto en chunks de aproximadamente chunk_size caracteres respetando saltos de línea."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            chunks.append(text[start:])
            break
        # buscar último salto de línea antes del límite
        nl = text.rfind("\n", start, end)
        if nl > start:
            end = nl + 1
        chunks.append(text[start:end])
        start = max(start + 1, end - overlap)
    return chunks


def iter_source_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            ext = Path(fn).suffix.lower()
            base = fn.lower()
            if ext in CODE_EXTENSIONS or base in ("dockerfile", "makefile", "modelfile"):
                full = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(full)
                except OSError:
                    continue
                if size > MAX_FILE_BYTES:
                    continue
                yield full


def index_repository(root, db_path):
    root = os.path.abspath(root)
    records = []
    files = list(iter_source_files(root))
    print(f"Indexando {len(files)} archivos desde {root}...")

    for idx, full in enumerate(files, 1):
        rel = os.path.relpath(full, root)
        print(f"[{idx}/{len(files)}] {rel}")
        try:
            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except Exception as e:
            print(f"    error leyendo: {e}")
            continue
        if not text.strip():
            continue
        chunks = chunk_file(text)
        for i, chunk in enumerate(chunks):
            try:
                vec = get_embedding(chunk[:4000])  # truncar por seguridad
            except Exception as e:
                print(f"    error embedding chunk {i}: {e}")
                continue
            if vec:
                records.append({
                    "source": rel,
                    "chunk_index": i,
                    "text": chunk,
                    "vector": vec,
                })

    os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({"root": root, "records": records}, f, ensure_ascii=False)
    print(f"\nIndex ready: {len(records)} chunks guardados en {db_path}")


def normalize(vec):
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0 else vec


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


def search_codebase(query, db_path, top_k=5):
    with open(db_path, "r", encoding="utf-8") as f:
        db = json.load(f)
    records = db.get("records", [])
    if not records:
        print("La base de vectores está vacía. Indexá un repositorio primero.")
        return
    q_vec = normalize(get_embedding(query))
    scored = []
    for r in records:
        r_vec = normalize(r["vector"])
        score = cosine(q_vec, r_vec)
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    print(f"Top {top_k} resultados para: {query}\n")
    for score, r in scored[:top_k]:
        source = r["source"]
        preview = r["text"].replace("\n", " ")[:250]
        print(f"score {score:.4f} | {source}")
        print(f"    {preview}\n")


def main():
    parser = argparse.ArgumentParser(description="Colmena Index: indexa repositorios con embeddings de nomic-embed-text.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser("index", help="Indexar un directorio")
    p_index.add_argument("path", help="Ruta del repositorio/directorio a indexar")
    p_index.add_argument(
        "--db",
        default=os.path.join(str(Path.home()), ".colmena", "vectordb.json"),
        help="Ruta de salida de la base de vectores",
    )

    p_search = sub.add_parser("search", help="Buscar en una base indexada")
    p_search.add_argument("query", help="Consulta semántica")
    p_search.add_argument(
        "--db",
        default=os.path.join(str(Path.home()), ".colmena", "vectordb.json"),
        help="Ruta de la base de vectores",
    )
    p_search.add_argument("--top-k", type=int, default=5, help="Cantidad de resultados")

    args = parser.parse_args()

    if args.command == "index":
        index_repository(args.path, args.db)
    elif args.command == "search":
        search_codebase(args.query, args.db, args.top_k)


if __name__ == "__main__":
    main()
