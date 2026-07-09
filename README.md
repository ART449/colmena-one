---
tags:
- ollama
- local-llm
- agent
- rag
- colmena
- qwen2.5-coder
license: apache-2.0
---

# Colmena-One v1.0.0

Modelo local unificado para Ollama: personalidad directa mexa + capacidades de código, **pantallas de carga con panal de abejas**, **TTS nativo con voces programadas**, herramientas reales, visión, embeddings y orquestación entre modelos locales y nube.

## ¿Qué incluye?

| # | Archivo | Rol |
|---|---|---|
| 1 | `colmena-one.modelfile` | Modelo base unificado (chat + código) sobre `qwen2.5-coder:7b`. |
| 2 | `colmena-vision.modelfile` | Homúnculo de visión sobre `gemma3:4b`. |
| 3 | `colmena-router.py` | Enrutador con animaciones de panal y abeja. |
| 4 | `colmena-agent.py` | Agente con 13 herramientas reales + animaciones + TTS. |
| 5 | `colmena-index.py` | Indexador RAG con animaciones y soporte de voz para resultados. |
| 6 | `colmena_animations.py` | Panal hexagonal, abejas volando, animación de mensaje entrante. |
| 7 | `colmena_tts.py` | TTS nativo Windows (pyttsx3/SAPI5) con presets programados. |
| 8 | `npm-packages/inbeebox/` | Paquete npm toolbox. |
| 9 | `npm-packages/octohype/` | Paquete npm orquestador. |
| 10 | `README.md` | Esta guía. |

## Arquitectura

- **Base principal**: `qwen2.5-coder:7b` (Alibaba Cloud, Apache 2.0)
- **Base visión**: `gemma3:4b` (Google DeepMind)
- **Embeddings**: `nomic-embed-text:latest`
- **Formato**: Ollama Modelfile
- **Animaciones**: Python stdlib (terminal TTY)
- **TTS nativo**: `pyttsx3` + SAPI5 en Windows
- **Dependencias del agente**: solo librería estándar de Python (TTS opcional)

## Instalación rápida

```bash
# 1. Modelo principal
ollama create colmena-one -f colmena-one.modelfile

# 2. Homúnculo de visión
ollama create colmena-vision -f colmena-vision.modelfile

# 3. TTS opcional (Windows)
pip install pyttsx3

# 4. Probar
python colmena-agent.py --voice-list
ollama run colmena-one
```

## Los Homúnculos de la Colmena

Colmena-One es el operador principal, pero no todos los modelos se pudieron fusionar en un solo GGUF por diferencias de arquitectura. Cada uno queda como especialista.

| Rol | Modelo | Qué hace |
|---|---|---|
| **Nexo / General** | `colmena-one` | Chat, código, debugging, arquitectura, operaciones técnicas. Sabe Go, Rust, Python, JS/TS, C/C++, Java, shell/PowerShell. |
| **Ojo / Visión** | `colmena-vision` | Analiza imágenes, screenshots, diagramas, UI. |
| **Memoria / RAG** | `nomic-embed-text:latest` | Genera embeddings para búsqueda semántica local. |
| **Sabio profundo** | `deepseek-v3.1:671b-cloud` | Razonamiento pesado vía nube (requiere conexión y créditos). |
| **General cloud** | `glm-5.1:cloud` | Asistente general vía nube. |
| **Código cloud** | `gpt-oss:20b-cloud` | Variante cloud para código. |

## Pantallas de carga (panal de abejas)

Los scripts muestran animaciones en la terminal mientras Ollama piensa:

- `HexLoader` — panal de hexágonos `⬡` que se llenan `⬢` mientras una abeja `🐝` vuela alrededor.
- `BeeSwarmLoader` — enjambre de abejas zumbando.
- `MessageReceiver` — animación de `📡` → `✉️` → `🍯` cuando llega la respuesta.
- `SplashScreen` — arte de inicio con panal y abejas.

Activas si la terminal soporta TTY. En pipes o CI se desactivan automáticamente para no romper logs.

## TTS nativo con voces programadas

Colmena habla la respuesta final usando el sintetizador nativo de Windows (pyttsx3/SAPI5).

### Voces disponibles

```bash
# Listar voces instaladas y presets
python colmena-agent.py --voice-list
python colmena-router.py --voice-list
python colmena-index.py search "login" --voice-list
```

### Presets programados

| Preset | Voz | Idioma/accento |
|---|---|---|
| `memo`, `mexa`, `sabina` | Microsoft Sabina | Español México |
| `zira`, `art` | Microsoft Zira | Inglés US |
| `helena` | Microsoft Helena | Español España |
| `david`, `gringo` | Microsoft David | Inglés US |

### Usar

```bash
# Agent habla la respuesta
python colmena-agent.py "dime hola" --voice memo

# Router con voz del abogado gringo
python colmena-router.py "qué hora es" --voice david

# Búsqueda RAG lee el top-1
python colmena-index.py search "autenticación" --voice sabina
```

## 1. Router (`colmena-router.py`)

Elige el homúnculo correcto por tarea.

```bash
# Visión
python colmena-router.py "Dime qué errores veo en esta captura" --image screenshot.png

# Local por defecto
python colmena-router.py "Explícame qué es un transformer"

# Forzar nube
python colmena-router.py "Razona paso a paso" --modelo cloud_deep

# Con voz
python colmena-router.py "dame un chiste técnico" --voice sabina
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

# Más iteraciones + voz
python colmena-agent.py "investiga este bug paso a paso" --max-iters 10 --voice memo

# Listar voces
python colmena-agent.py --voice-list
```

## 3. Indexador (`colmena-index.py`)

Crea una base de vectores local de tus repositorios usando `nomic-embed-text:latest`.

```bash
# Indexar un repo
python colmena-index.py index C:\mi-repo

# Buscar
python colmena-index.py search "funciones de autenticación"

# Buscar y leer el top-1 en voz alta
python colmena-index.py search "login" --voice sabina
```

La base de vectores se guarda por defecto en `~/.colmena/vectordb.json`. El agente la usa automáticamente con `search_codebase`.

## 4. Paquetes npm

### INBEEBOX (toolbox)

```bash
npm install -g inbeebox
inbeebox agent "lee README.md"
inbeebox index index C:\mi-repo
inbeebox index search "auth"
```

### OctoHype (orquestador)

```bash
npm install -g octohype
octohype "Analiza esta imagen" --image screenshot.png
octohype "Razona profundo" --modelo cloud_deep
```

## Seguridad

- Operaciones destructivas o mutadoras piden confirmación antes de ejecutarse.
- `--yes` deshabilita confirmaciones; usalo solo en tu propia máquina.
- Los modelos cloud consumen créditos; se usan solo por palabras clave explícitas o `--modelo`.
- No se envían datos a terceros fuera de Ollama local y los clouds que configures.
- `colmena_tts.py` habla solo lo que le pedís; no graba ni transmite audio.

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
