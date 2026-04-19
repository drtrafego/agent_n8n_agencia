"""
Corrige o Check CreateEvent node no Calendar workflow.
O codigo JS estava quebrado porque o bash comeu os $('node') quando executado inline.
"""
import urllib.request, json, ssl, sys, io, copy, datetime, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'


def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


# Codigo correto com $() do n8n (sem interferencia do bash)
CHECK_CREATE_EVENT_CODE = (
    "// Verifica se CreateEvent foi executado e inclui resposta do AI Agent\n"
    "const agentResponse = $('AI Agent').first().json.output || '';\n"
    "try {\n"
    "  const items = $('CreateEvent').all();\n"
    "  if (items && items.length > 0 && items[0].json) {\n"
    "    const ev = items[0].json;\n"
    "    return [{\n"
    "      json: {\n"
    "        eventCreated: true,\n"
    "        agentResponse: agentResponse,\n"
    "        summary: ev.summary || 'Call Agente 24 Horas',\n"
    "        start: ev.start?.dateTime || ev.start?.date || '',\n"
    "        htmlLink: ev.htmlLink || '',\n"
    "        attendees: (ev.attendees || []).map(a => a.email).join(', ')\n"
    "      }\n"
    "    }];\n"
    "  }\n"
    "} catch(e) { /* CreateEvent nao foi chamado */ }\n"
    "return [{ json: { eventCreated: false, agentResponse: agentResponse } }];"
)


def main():
    print('Corrigindo Check CreateEvent no Calendar...')

    _, wf = api('GET', '/api/v1/workflows/6EJoeyC63gDEffu2')
    wf_up = copy.deepcopy(wf)

    fixed = False
    for n in wf_up['nodes']:
        if n.get('name') == 'Check CreateEvent':
            n['parameters']['jsCode'] = CHECK_CREATE_EVENT_CODE
            fixed = True
            print('  Check CreateEvent: codigo corrigido')
            # Mostra preview
            print(f'  Preview: {CHECK_CREATE_EVENT_CODE[:100]}...')

    if not fixed:
        print('  ERRO: no nao encontrado')
        return

    # Verifica ReturnToSDR
    has_return = any(n.get('name') == 'ReturnToSDR' for n in wf_up['nodes'])
    print(f'  ReturnToSDR presente: {has_return}')

    ev_conn = wf_up['connections'].get('Evento Criado?', {}).get('main', [])
    false_branch = ev_conn[1] if len(ev_conn) > 1 else []
    print(f'  Evento Criado? FALSE branch: {false_branch}')

    # Deploy
    api('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/deactivate')
    s, resp = api('PUT', '/api/v1/workflows/6EJoeyC63gDEffu2', {
        'name': wf_up['name'],
        'nodes': wf_up['nodes'],
        'connections': wf_up['connections'],
        'settings': wf_up.get('settings', {}),
    })
    print(f'  PUT: {s}')
    if s != 200:
        print(f'  ERRO: {resp}')
        return

    api('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/activate')
    print('  Reativado')

    # Aguarda e busca exec mais recente para verificar
    print('\nAguardando 5s e verificando exec mais recente...')
    time.sleep(5)
    _, execs = api('GET', '/api/v1/executions?workflowId=6EJoeyC63gDEffu2&limit=1')
    last = execs.get('data', [])
    if last:
        eid = last[0]['id']
        print(f'  Ultima exec: [{eid}] {last[0]["status"]} | {last[0]["startedAt"][:19]}')
        _, ed = api('GET', f'/api/v1/executions/{eid}?includeData=true')
        run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
        for node, runs in run_data.items():
            for run in runs:
                items = (run.get('data', {}).get('main') or [[]])[0]
                err = run.get('error')
                if err:
                    print(f'  [ERRO] {node}: {json.dumps(err, ensure_ascii=False)[:200]}')
                elif items:
                    out = str(items[0].get('json', {}))[:150]
                    print(f'  [ok]   {node} ({len(items)}) {out}')

    print('\nDONE - codigo corrigido. Agora precisa de uma nova exec real para validar o ReturnToSDR.')


if __name__ == '__main__':
    main()
