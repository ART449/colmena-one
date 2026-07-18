# OctoHype

Orquestador de homúnculos de la Colmena.

## Instalación

```bash
npm install -g octohype
# o
npx octohype "Tu pregunta"
```

## Uso

```bash
# Local por defecto
octohype "Explícame qué es un transformer"

# Visión
octohype "Analiza esta captura" --image screenshot.png

# Forzar cloud
octohype "Razona profundo" --modelo cloud_deep
```

## Requisitos

- Python 3.x
- Ollama corriendo en `http://localhost:11434`
- Modelos locales en Ollama: `colmena-one`, `colmena-vision`

### Creación de Modelos en Ollama

Para configurar los modelos requeridos en cualquier máquina:

1. **colmena-one** (Chat y Código - requiere `qwen2.5-coder:7b`):
   ```bash
   ollama pull qwen2.5-coder:7b
   ollama create colmena-one -f colmena-one.modelfile
   ```

2. **colmena-vision** (Visión e Imágenes - requiere `gemma3:4b`):
   ```bash
   ollama pull gemma3:4b
   ollama create colmena-vision -f colmena-vision.modelfile
   ```

*Nota: Los archivos `.modelfile` se encuentran en la raíz del repositorio de ByFlow (o en la carpeta raíz del paquete instalado globalmente de npm).*

## Relación con INBEEBOX

`octohype` se enfoca en **enrutar la tarea** al homúnculo correcto. Para el agente con herramientas reales y el indexador, usá `inbeebox`.

## Licencia

Apache-2.0
