import urllib.request, json, ssl, sys
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com/api/v1'

def api(path, method='GET', data=None):
    req = urllib.request.Request(BASE+path, headers={'X-N8N-API-KEY': KEY, 'Content-Type': 'application/json'}, method=method)
    if data: req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())

wf = api('/workflows/aBMaCWPodLaS8I6L')

for n in wf['nodes']:
    if n['name'] == 'Buscar Leads':
        q = n['parameters']['query']
        # A vírgula indevida fica logo após o fechamento da CTE reagend (LIMIT 10\n),\nSELECT)
        # Precisa ser (LIMIT 10\n)\nSELECT)
        old = '  LIMIT 10\n),\nSELECT'
        new = '  LIMIT 10\n)\nSELECT'
        if old in q:
            n['parameters']['query'] = q.replace(old, new)
            print('Vírgula removida. Query corrigida.')
        else:
            # Tentar variações de whitespace
            import re
            fixed = re.sub(r'(LIMIT\s+10\s*\n\s*\)\s*),(\s*\nSELECT)', r'\1\2', q)
            if fixed != q:
                n['parameters']['query'] = fixed
                print('Vírgula removida via regex. Query corrigida.')
            else:
                print('Padrão não encontrado. Mostrando trecho:')
                idx = q.find('LIMIT 10')
                print(repr(q[idx:idx+30]))
        break

payload = {'name': wf['name'], 'nodes': wf['nodes'], 'connections': wf['connections'],
           'settings': wf.get('settings', {}), 'staticData': wf.get('staticData')}
result = api('/workflows/aBMaCWPodLaS8I6L', method='PUT', data=payload)
print('Deploy OK:', result.get('id'), '| ativo:', result.get('active'))
