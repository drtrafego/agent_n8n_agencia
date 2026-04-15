const https = require('https');

const N8N_BASE = 'https://n8n.casaldotrafego.com';
const API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U';
const WORKFLOW_ID = 'JmiydfZHpeU8tnic';
const OBS_NODE_ID = '185d7d51-3fef-4c2d-bbc1-7430259dfc55';

function request(method, path, body) {
  return new Promise((resolve, reject) => {
    const data = body ? JSON.stringify(body) : null;
    const opts = {
      hostname: 'n8n.casaldotrafego.com',
      path,
      method,
      headers: {
        'X-N8N-API-KEY': API_KEY,
        'Content-Type': 'application/json',
        ...(data ? { 'Content-Length': Buffer.byteLength(data) } : {})
      },
      rejectUnauthorized: false
    };
    const req = https.request(opts, res => {
      let buf = '';
      res.on('data', d => buf += d);
      res.on('end', () => {
        try { resolve({ status: res.statusCode, body: JSON.parse(buf) }); }
        catch(e) { resolve({ status: res.statusCode, body: buf }); }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function main() {
  console.log('Fetching workflow...');
  const { body: wf } = await request('GET', `/api/v1/workflows/${WORKFLOW_ID}`);
  
  const nodeIdx = wf.nodes.findIndex(n => n.id === OBS_NODE_ID);
  if (nodeIdx === -1) throw new Error('Node not found');
  
  const node = wf.nodes[nodeIdx];
  
  // Update tool description
  node.parameters.toolDescription = 
    'Salva observacoes do lead no CRM. OBRIGATORIO passar os 4 parametros SEMPRE:\n' +
    '- observacoes: resumo acumulado da conversa e situacao do lead\n' +
    '- stage: classificacao OBRIGATORIA do lead. Valores EXATOS: \'novo\', \'qualificando\', \'interesse\', \'agendado\', \'sem_interesse\'. NUNCA deixe vazio.\n' +
    '- nome: nome confirmado do lead (ou vazio se nao confirmou)\n' +
    '- nicho: setor ou segmento do negocio do lead (ex: saude, imobiliaria, varejo, advocacia, emprestimo consignado, restaurante, etc). Deixe vazio se nao foi mencionado.';

  const newQuery = `INSERT INTO contacts (telefone, observacoes_sdr, stage, stage_updated_at, nome, nicho)
VALUES (
  '{{ $('Code4').item.json.telefone }}',
  '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}',
  CASE
    WHEN '{{ $fromAI("stage", "Stage OBRIGATORIO do lead. Valores exatos: novo, qualificando, interesse, agendado, sem_interesse. NUNCA deixe vazio", "string") }}' != '' THEN '{{ $fromAI("stage", "Stage OBRIGATORIO do lead. Valores exatos: novo, qualificando, interesse, agendado, sem_interesse. NUNCA deixe vazio", "string") }}'
    WHEN '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%agendou%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%agendad%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%call agendad%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%convite disparado%' THEN 'agendado'
    WHEN '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%sem interesse%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%sem_interesse%' THEN 'sem_interesse'
    WHEN '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%qualificando%' THEN 'qualificando'
    ELSE 'novo'
  END,
  NOW(),
  '{{ $fromAI("nome", "Nome confirmado pelo lead na conversa. Deixe vazio se nao houve confirmacao de nome", "string") }}',
  NULLIF('{{ $fromAI("nicho", "Setor ou segmento do negocio do lead, ex: saude, imobiliaria, varejo, advocacia, emprestimo consignado, restaurante. Deixe vazio se nao foi mencionado", "string") }}', '')
)
ON CONFLICT (telefone)
DO UPDATE SET
  observacoes_sdr = EXCLUDED.observacoes_sdr,
  stage = CASE
    WHEN EXCLUDED.stage != '' AND EXCLUDED.stage != 'novo' THEN EXCLUDED.stage
    WHEN EXCLUDED.observacoes_sdr ILIKE '%agendou%' OR EXCLUDED.observacoes_sdr ILIKE '%agendad%' OR EXCLUDED.observacoes_sdr ILIKE '%call agendad%' OR EXCLUDED.observacoes_sdr ILIKE '%convite disparado%' THEN 'agendado'
    WHEN EXCLUDED.observacoes_sdr ILIKE '%sem interesse%' OR EXCLUDED.observacoes_sdr ILIKE '%sem_interesse%' THEN 'sem_interesse'
    WHEN EXCLUDED.observacoes_sdr ILIKE '%qualificando%' THEN 'qualificando'
    ELSE contacts.stage
  END,
  stage_updated_at = NOW(),
  updated_at = NOW(),
  nome = COALESCE(NULLIF(EXCLUDED.nome, ''), contacts.nome),
  nicho = COALESCE(NULLIF('{{ $fromAI("nicho", "Setor ou segmento do negocio do lead, ex: saude, imobiliaria, varejo, advocacia, emprestimo consignado, restaurante. Deixe vazio se nao foi mencionado", "string") }}', ''), contacts.nicho)`;

  node.parameters.query = newQuery;
  wf.nodes[nodeIdx] = node;
  
  // Strip read-only fields from payload
  const payload = {
    name: wf.name,
    nodes: wf.nodes,
    connections: wf.connections,
    settings: wf.settings || {},
    staticData: wf.staticData || null,
    meta: wf.meta || {}
  };
  
  console.log('Deactivating...');
  await request('POST', `/api/v1/workflows/${WORKFLOW_ID}/deactivate`);
  
  console.log('Updating...');
  const { status, body: result } = await request('PUT', `/api/v1/workflows/${WORKFLOW_ID}`, payload);
  console.log('PUT status:', status);
  if (status !== 200) {
    console.error('Error:', JSON.stringify(result).slice(0, 800));
    process.exit(1);
  }
  
  console.log('Reactivating...');
  const { status: actStatus } = await request('POST', `/api/v1/workflows/${WORKFLOW_ID}/activate`);
  console.log('Activate status:', actStatus);
  
  console.log('Done! observacoes_sdr now saves nicho field.');
}

main().catch(e => { console.error(e); process.exit(1); });
