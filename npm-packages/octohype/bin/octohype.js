#!/usr/bin/env node
const { spawn } = require('child_process');
const path = require('path');

const args = process.argv.slice(2);

function run(scriptName, extraArgs) {
  const scriptPath = path.join(__dirname, '..', 'scripts', scriptName);
  const proc = spawn('python', [scriptPath, ...extraArgs], {
    stdio: 'inherit',
    shell: process.platform === 'win32',
  });
  proc.on('exit', (code) => process.exit(code || 0));
}

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
OctoHype - Orquestador de homúnculos Colmena

Uso:
  npx octohype "Tu pregunta"
  npx octohype "Dime qué errores veo" --image screenshot.png

Requiere:
  - Python 3 y Ollama en http://localhost:11434
  - Modelos instalados: colmena-one, colmena-vision
`);
  process.exit(0);
}

run('colmena-router.py', args);
