# Colmena-One

Modelo local para Ollama que unifica la personalidad directa de Memo con las capacidades de código de [Qwen2.5-Coder-7B](https://ollama.com/library/qwen2.5-coder:7b).

## Arquitectura

- **Base**: `qwen2.5-coder:7b` (Alibaba Cloud, Apache 2.0)
- **Formato**: Ollama Modelfile
- **Cuantización**: Q4_K_M (heredada del modelo base)

## Uso rápido

```bash
ollama create colmena-one -f colmena-one.public.modelfile
ollama run colmena-one
```

## Los Homúnculos de la Colmena

Colmena-One es el operador principal, pero no todos los modelos locales se pudieron fundir en un solo GGUF por diferencias de arquitectura o función. En vez de desperdiciarlos, cada especialista queda como un **homúnculo** al que el router manda tareas específicas.

| Rol | Modelo | Qué hace |
|---|---|---|
| **Nexo / General** | `colmena-one` | Chat, código, debugging, arquitectura, operaciones técnicas. |
| **Ojo / Visión** | `colmena-vision` | Análisis de imágenes, screenshots, diagramas y UI. Basado en `gemma3:4b`. |
| **Memoria / RAG** | `nomic-embed-text:latest` | Genera embeddings para búsqueda semántica y RAG local. |
| **Sabio profundo** | `deepseek-v3.1:671b-cloud` | Razonamiento pesado vía nube (requiere conexión y créditos). |
| **General cloud** | `glm-5.1:cloud` | Asistente general vía nube. |
| **Código cloud** | `gpt-oss:20b-cloud` | Variante cloud para código. |

Instalar visión:

```bash
ollama create colmena-vision -f colmena-vision.modelfile
```

## Router de la Colmena

`colmena-router.py`recibe un prompt y decide a qué homúnculo mandarlo. Por defecto usa el **modelo local** (`colmena-one`) para no consumir créditos de nube sin aviso.

```bash
# Visión: pasa una imagen
python colmena-router.py "Dime qué errores veo en esta captura" --image screenshot.png

# Local por defecto
python colmena-router.py "Explícame qué es un transformer"

# Forzar un homúnculo específico
python colmena-router.py "Razona paso a paso sobre este problema complejo" --modelo cloud_deep
```

**Reglas del router:**
- Si pasas `--image`, va a `colmena-vision`.
- Si el prompt menciona palabras clave cloud (`deepseek`, `razona profundo`, `gpt-oss`, `nube code`, `glm`, `nube general`), rutea al cloud correspondiente.
- En cualquier otro caso, usa `colmena-one` local.
- Si un modelo cloud falla, hace fallback a `colmena-one`.

### Requisitos

- Ollama corriendo localmente en `http://localhost:11434`.
- Python 3 (sin dependencias externas: usa solo librería estándar).

### Uso avanzado: forzar homúnculo

```bash
python colmena-router.py "Tu pregunta" --modelo vision
python colmena-router.py "Tu pregunta" --modelo cloud_code
```

Opciones válidas: `local`, `vision`, `cloud_deep`, `cloud_code`, `cloud_general`.

## 🤖 Colmena-Agente

`colmena-agent.py` le da herramientas reales a `colmena-one`. Puede:

- Leer archivos (`read_file`)
- Listar directorios (`list_directory`)
- Buscar texto en archivos (`search_files`)
- Ejecutar comandos de shell (`run_shell`, con confirmación para comandos destructivos)
- Resumir el entorno (`get_environment_summary`)

### Ejemplos

```bash
# Leer un archivo
python colmena-agent.py "lee el contenido de README.md"

# Buscar en el proyecto
python colmena-agent.py "busca dónde se define HF_TOKEN en el código"

# Ejecutar un comando seguro
python colmena-agent.py "qué versión de Python tengo instalada"

# Modo sin confirmación (cuidado con rm/format)
python colmena-agent.py "muestra el uso de disco" --yes
```

### Seguridad

- Comandos potencialmente destructivos (`rm`, `del`, `format`, etc.) piden confirmación interactiva.
- Usa `--yes` solo si sabés lo que hacés y en tu propia máquina.
- El agente no puede (y no intenta) conectarse a máquinas remotas ni eliminar datos sin permiso.

## Características de Colmena-One

- Chat general en español mexicano directo, sin relleno corporativo.
- Coding, debugging, arquitectura y operaciones técnicas.
- Verdad operativa exigente: separa evidencia real de memoria/hipótesis.
- Límites claros: no inventa estados de sistemas ni suplanta permisos.

## Licencia

El Modelfile y el system prompt se comparten bajo Apache License 2.0, siguiendo la licencia del modelo base Qwen2.5-Coder.

```
Copyright 2024 Alibaba Cloud
Licensed under the Apache License, Version 2.0
```

## Agradecimientos

- Qwen2.5-Coder por Alibaba Cloud.
- Gemma3 por Google DeepMind.
- Ollama por el ecosistema de ejecución local.
