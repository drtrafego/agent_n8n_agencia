const fs = require('fs');
const key = fs.readFileSync('.env.local', 'utf8').match(/N8N_API_KEY=(.+)/)?.[1]?.trim();
const base = 'https://n8n.casaldotrafego.com/api/v1';

async function api(method, path, body) {
  const r = await fetch(base + path, {
    method,
    headers: { 'X-N8N-API-KEY': key, 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  return r.json();
}

async function main() {
  const fu = await api('GET', '/workflows/aBMaCWPodLaS8I6L');
  const gemini = fu.nodes.find(n => n.name === 'Gemini Follow-up');

  gemini.parameters.modelId = {
    __rl: true,
    value: 'models/gemini-1.5-flash',
    mode: 'list',
    cachedResultName: 'models/gemini-1.5-flash',
  };
  gemini.retryOnFail = true;
  gemini.maxTries = 3;
  gemini.waitBetweenTries = 5000;

  await api('POST', '/workflows/aBMaCWPodLaS8I6L/deactivate');
  const r = await api('PUT', '/workflows/aBMaCWPodLaS8I6L', {
    name: fu.name, nodes: fu.nodes, connections: fu.connections,
    settings: { executionOrder: fu.settings?.executionOrder, callerPolicy: fu.settings?.callerPolicy },
  });
  await api('POST', '/workflows/aBMaCWPodLaS8I6L/activate');

  // Confirmar
  const fu2 = await api('GET', '/workflows/aBMaCWPodLaS8I6L');
  const g2 = fu2.nodes.find(n => n.name === 'Gemini Follow-up');
  console.log('Modelo:', g2.parameters.modelId?.value);
  console.log('Ativo:', fu2.active);

  // Também verificar se prompt está correto
  const prep = fu2.nodes.find(n => n.name === 'Preparar Contexto');
  const fields = prep?.parameters?.assignments?.assignments?.map(a => a.name);
  console.log('Campos Preparar Contexto:', fields);
}

main().catch(console.error);
