import urllib.request, json, ssl, sys, io, copy
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

_, wf = api('GET', '/api/v1/workflows/6EJoeyC63gDEffu2')
wf_up = copy.deepcopy(wf)
for n in wf_up['nodes']:
    if n.get('name') == 'AI Agent':
        sm = n['parameters']['options']['systemMessage']
        before = sm
        sm = sm.replace('Sabado 18/04 PODE ser usado. Domingo continua proibido.',
                        'NUNCA sugira horarios em fim de semana (sabado ou domingo).')
        n['parameters']['options']['systemMessage'] = sm
        print(f'Prompt alterado: {"Sim" if sm != before else "Nao (ja estava ok)"}')
        idx = sm.find('NUNCA sugira horarios')
        if idx >= 0:
            print(f'  Trecho: {sm[idx:idx+60]}')

api('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/deactivate')
s, _ = api('PUT', '/api/v1/workflows/6EJoeyC63gDEffu2', {
    'name': wf_up['name'], 'nodes': wf_up['nodes'],
    'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
})
api('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/activate')
print(f'Calendar restaurado: {s}')
