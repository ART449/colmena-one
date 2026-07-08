# Colmena-One

Modelo local para Ollama que unifica la personalidad directa de Memo con las capacidades de código de [Qwen2.5-Coder-7B](https://ollama.com/library/qwen2.5-coder:7b).

## Arquitectura

- **Base**: `qwen2.5-coder:7b` (Alibaba Cloud, Apache 2.0)
- **Formato**: Ollama Modelfile
- **Cuantización**: Q4_K_M (heredada del modelo base)

## Uso

```bash
ollama create colmena-one -f colmena-one.public.modelfile
ollama run colmena-one
```

## Características

- Chat general en español mexicano directo y sin relleno corporativo.
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
- Ollama por el ecosistema de ejecución local.
