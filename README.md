# Colmena-One v0.2.0-preview

Modelo local unificado para Ollama: personalidad directa mexa + capacidades de código, herramientas reales, visión, embeddings y orquestación entre modelos locales y nube.

## ¿Qué incluye esta preview?

| # | Archivo | Rol |
|---|---|---|
| 1 | `colmena-one.modelfile` | Modelo base unificado (chat + código) sobre `qwen2.5-coder:7b`. |
| 2 | `colmena-vision.modelfile` | Homúnculo de visión sobre `gemma3:4b` (imágenes, UI, screenshots). |
| 3 | `colmena-router.py` | Enrutador que elige el mejor homúnculo según la tarea. |
| 4 | `colmena-agent.py` | Agente con herramientas reales: archivos, shell, Python, web, embeddings, visión. |
| 5 | `colmena-index.py` | Indexador de repositorios con `nomic-embed-text` para búsqueda semántica (RAG local). |
| 6 | `README.md` | Esta guía. |

## Arquitectura

- **Base principal**: `qwen2.5-coder:7b` (Alibaba Cloud, Apache 2.0)
- **Base visión**: `gemma3:4b` (Google DeepMind)
- **Embeddings**: `nomic-embed-text:latest`
- **Formato**: Ollama Modelfile
- **Dependencias del agente**: solo librería estándar de Python

## Instalación rápida

```bash
# 1. Modelo principal
ollama create colmena-one -f colmena-one.modelfile

# 2. Homúnculo de visión
ollama create colmena-vision -f colmena-vision.modelfile

# 3. Probar
ollama run colmena-one
```

## Los Homúnculos de la Colmena

Colmena-One es el operador principal, pero no todos los modelos se pudieron fusionar en un solo GGUF por diferencias de arquitectura. En vez de desperdiciarlos, cada uno queda como especialista.

| Rol | Modelo | Qué hace |
|---|---|---|
| **Nexo / General** | `colmena-one` | Chat, código, debugging, arquitectura, operaciones técnicas. Sabe Go, Rust, Python, JS/TS, C/C++, Java, shell/PowerShell. |
| **Ojo / Visión** | `colmena-vision` | Analiza imágenes, screenshots, diagramas, UI. |
| **Memoria / RAG** | `nomic-embed-text:latest` | Genera embeddings para búsqueda semántica local. |
| **Sabio profundo** | `deepseek-v3.1:671b-cloud` | Razonamiento pesado vía nube (requiere conexión y créditos). |
| **General cloud** | `glm-5.1:cloud` | Asistente general vía nube. |
| **Código cloud** | `gpt-oss:20b-cloud` | Variante cloud para código. |

## 1. Router (`colmena-router.py`)

Elige el homúnculo correcto por tarea.

```bash
# Visión
python colmena-router.py "Dime qué errores veo en esta captura" --image screenshot.png

# Local por defecto
python colmena-router.py "Explícame qué es un transformer"

# Forzar nube
python colmena-router.py "Razona paso a paso" --modelo cloud_deep
```

**Opciones:** `local`, `vision`, `cloud_deep`, `cloud_code`, `cloud_general`.

## 2. Agente (`colmena-agent.py`)

Colmena-One con herramientas reales en tu máquina.

### Herramientas 1x1

| # | Herramienta | Qué hace | ¿Pregunta de seguridad? |
|---|---|---|---|
| 1 | `read_file` | Lee archivos de texto. | No |
| 2 | `list_directory` | Lista archivos y carpetas. | No |
| 3 | `search_files` | Busca texto/regex en archivos. | No |
| 4 | `write_file` | Crea/sobrescribe archivos. | Sí |
| 5 | `edit_file` | Reemplaza texto en archivos. | Sí |
| 6 | `run_shell` | Ejecuta comandos en shell. | Sí (destructivos) |
| 7 | `run_python` | Ejecuta scripts Python temporales. | Sí |
| 8 | `web_fetch` | Descarga contenido de URLs públicas. | No |
| 9 | `compute_embedding` | Embeddings con nomic-embed-text. | No |
| 10 | `analyze_image` | Analiza imágenes con colmena-vision. | No |
| 11 | `get_environment_summary` | OS, modelos Ollama, directorio actual. | No |
| 12 | `search_codebase` | Búsqueda semántica en repos indexados. | No |
| 13 | `index_codebase` | Indexa un repositorio para búsqueda futura. | No |

### Ejemplos

```bash
# Leer
python colmena-agent.py "lee README.md"

# Buscar
python colmena-agent.py "busca dónde se define HF_TOKEN"

# Comando seguro
python colmena-agent.py "qué versión de Python tengo"

# Modo sin confirmación (cuidado)
python colmena-agent.py "muestra el uso de disco" --yes

# Más iteraciones permitidas
python colmena-agent.py "investiga este bug paso a paso" --max-iters 10
```

## 3. Indexador (`colmena-index.py`)

Crea una base de vectores local de tus repositorios usando `nomic-embed-text:latest`.

```bash
# Indexar un repo
python colmena-index.py index C:\mi-repo

# Buscar/python colmena-index.py search "funciones de autenticación"
```

La base de vectores se guarda por defecto en `~/.colmena/vectordb.json`. El agente la usa automáticamente con `search_codebase`.

**Formatos indexados:** `.py`, `.js`, `.ts`, `.go`, `.rs`, `.c`, `.cpp`, `.java`, `.kt`, `.swift`, `.rb`, `.php`, `.cs`, `.sh`, `.ps1`, `.md`, `.yaml`, `.json`, `.tf`, `.bicep`, `Dockerfile`, `Makefile`, `Modelfile`.

**Ignora:** `.git`, `node_modules`, `__pycache__`, `venv`, `dist`, `build`, `target`, etc.

## Seguridad

- Operaciones destructivas o mutadoras piden confirmación antes de ejecutarse.
- `--yes` deshabilita confirmaciones; usalo solo en tu propia máquina y sabiendo qué hacés.
- Los modelos cloud consumen créditos; el router y el agente los usan solo por palabras clave explícitas o `--modelo`.
- No se envían datos a terceros fuera de Ollama local y los clouds que vos configures.

## Características de Colmena-One

- Chat general en español mexicano directo, sin relleno corporativo.
- Coding, debugging, arquitectura y operaciones técnicas.
- Maneja múltiples lenguajes: **Go, Rust**, Python, JavaScript/TypeScript, C/C++, Java, Kotlin, shell/PowerShell.
- Verdad operativa exigente: separa evidencia real de memoria/hipótesis.
- Límites claros: no inventa estados de sistemas ni suplanta permisos.

## Licencia

Los Modelfiles, el system prompt y el código se comparten bajo Apache License 2.0, siguiendo la licencia del modelo base Qwen2.5-Coder.

```
Copyright 2024 Alibaba Cloud
Licensed under the Apache License, Version 2.0
```

## Agradecimientos

- Qwen2.5-Coder por Alibaba Cloud.
- Gemma3 por Google DeepMind.
- Nomic Embed Text por Nomic AI.
- Ollama por el ecosistema de ejecución local.

---

**Preview version:** v0.2.0-preview — todo junto: modelo, visión, router, agente e indexador.
