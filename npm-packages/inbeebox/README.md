# INBEEBOX

Caja de herramientas local de la Colmena.

## Instalación

```bash
npm install -g inbeebox
# o
npx inbeebox agent --help
```

## Requisitos

- Python 3.x
- Ollama corriendo en `http://localhost:11434`
- Modelos creados localmente: `colmena-one`, `colmena-vision`, `nomic-embed-text:latest`

## Uso

```bash
# Agente Colmena con herramientas reales
inbeebox agent "lee README.md"
inbeebox agent "lista los archivos de C:\\mi-repo" --yes

# Indexador de repositorios para búsqueda semántica
inbeebox index index C:\\mi-repo
inbeebox index search "autenticación"
```

## Licencia

Apache-2.0
