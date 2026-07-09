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
- Modelos: `colmena-one`, `colmena-vision`

## Relación con INBEEBOX

`octohype` se enfoca en **enrutar la tarea** al homúnculo correcto. Para el agente con herramientas reales y el indexador, usá `inbeebox`.

## Licencia

Apache-2.0
