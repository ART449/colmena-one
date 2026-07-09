#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);
const command = args[0];

function run(scriptName, extraArgs) {
  const scriptPath = path.join(__dirname, '..', 'scripts', scriptName);
  const proc = spawn('python', [scriptPath, ...extraArgs], {
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });
  proc.on('exit', (code) => process.exit(code || 0));
}

if (command === 'agent' || command === undefined) {
  run('colmena-agent.py', args.slice(command ? 1 : 0));
} else if (command === 'index') {
  run('colmena-index.py', args.slice(1));
} else if (command === '--help' || command === '-h') {
  console.log(`
INBEEBOX - Caja de herramientas local de Colmena

Uso:
  npx inbeebox agent [args...]   -> Ejecuta colmena-agent.py
  npx inbeebox index [args...] -> Ejecuta colmena-index.py

Argumentos se pasan directamente a los scripts Python.
Requiere Python 3 y Ollama corriendo en http://localhost:11434.
`);
} else {
  console.error(`Comando desconocido: ${command}`);
  console.error('Usá "inbeebox --help" para ver opciones.');
  process.exit(1);
}
