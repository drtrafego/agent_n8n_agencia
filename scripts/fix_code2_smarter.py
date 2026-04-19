"""
Duas correcoes:
1. SDR_retry prompt: corrige query de agendamento para 'entre 10h e 15h'
2. Code2: se SDR falhou mas Calendar retornou slots, usa os slots direto
   em vez de mandar mensagem de instabilidade
"""
import urllib.request, json, ssl, sys, io, copy, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'

# Code2 novo: se SDR vazio mas Calendar retornou, usa direto
# $('agente_google_agenda') nao e acessivel fora do agente, mas podemos
# tentar ler o ultimo output da ferramenta via contexto do SDR node
CODE2_VALUE = (
    "={{ (() => {\n"
    "  const out = $('SDR').first().json.output || '';\n"
    "  const isGarbage = !out || out.trim() === '' || "
    "out.includes('\"output\":\"\"') || "
    "out.trim().startsWith('[{') || out.trim().startsWith('{\"');\n"
    "  if (!isGarbage) return out;\n"
    "  // SDR falhou: tenta extrair slots do intermediateSteps do agente\n"
    "  try {\n"
    "    const steps = $('SDR').first().json.intermediateSteps || [];\n"
    "    for (const step of steps) {\n"
    "      const obs = step?.observation || '';\n"
    "      if (obs && obs.includes('h') && (obs.includes('Sexta') || "
    "obs.includes('Segunda') || obs.includes('Terca') || "
    "obs.includes('Ter\\u00e7a') || obs.includes('Quinta') || "
    "obs.includes('/04') || obs.includes('/05'))) {\n"
    "        return obs;\n"
    "      }\n"
    "    }\n"
    "  } catch(e) {}\n"
    "  return 'Oi! Tive uma instabilidade aqui. Pode repetir sua mensagem?';\n"
    "})() }}"
)


def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def main():
    print('Aplicando fixes no SDR BR...')
    _, wf = api('GET', '/api/v1/workflows/JmiydfZHpeU8tnic')
    wf_up = copy.deepcopy(wf)
    changes = []

    for n in wf_up['nodes']:
        name = n.get('name', '')

        # Fix 1: SDR_retry system message - corrige query agendamento
        if name == 'SDR_retry':
            sm = n.get('parameters', {}).get('options', {}).get('systemMessage', '')
            old = '"Buscar 3 horários disponíveis nos próximos 3 dias úteis, 2 manhã e 1 tarde."'
            new = '"Buscar 3 horários disponíveis nos próximos 3 dias úteis entre 10h e 15h."'
            if old in sm:
                n['parameters']['options']['systemMessage'] = sm.replace(old, new)
                changes.append('SDR_retry: query agendamento -> entre 10h e 15h')

        # Fix 2: Code2 - mais inteligente para extrair slots do intermediateSteps
        if name == 'Code2':
            assignments = n.get('parameters', {}).get('assignments', {}).get('assignments', [])
            for a in assignments:
                if a.get('id') == 'text-output':
                    a['value'] = CODE2_VALUE
                    changes.append('Code2: agora tenta extrair slots do intermediateSteps antes de mandar instabilidade')

    if not changes:
        print('Nenhuma mudanca necessaria.')
        return

    for c in changes:
        print(f'  {c}')

    api('POST', '/api/v1/workflows/JmiydfZHpeU8tnic/deactivate')
    s, resp = api('PUT', '/api/v1/workflows/JmiydfZHpeU8tnic', {
        'name': wf_up['name'],
        'nodes': wf_up['nodes'],
        'connections': wf_up['connections'],
        'settings': wf_up.get('settings', {}),
    })
    print(f'  PUT: {s}')
    if s != 200:
        print(f'  ERRO: {resp}')
        return
    api('POST', '/api/v1/workflows/JmiydfZHpeU8tnic/activate')
    print('  Reativado')
    print('DONE')


if __name__ == '__main__':
    main()
