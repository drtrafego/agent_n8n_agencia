import urllib.request, json, ssl, sys, time
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com/api/v1'
WEBHOOK_URL = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'

def api(path, method='GET', data=None):
    req = urllib.request.Request(BASE+path, headers={'X-N8N-API-KEY': KEY, 'Content-Type': 'application/json'}, method=method)
    if data: req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())

wf = api('/workflows/JmiydfZHpeU8tnic')

for n in wf['nodes']:
    if n['name'] == 'Code2':
        assignments = n['parameters']['assignments']['assignments']
        for a in assignments:
            old = a['value']
            # Trocar referencia de SDR para Orquestrador
            new = old.replace("$('SDR').first()", "$('Orquestrador').first()")
            a['value'] = new
            print('Code2 ANTES:', old[:120])
            print('Code2 DEPOIS:', new[:120])
        break

payload = {'name': wf['name'], 'nodes': wf['nodes'], 'connections': wf['connections'],
           'settings': wf.get('settings', {}), 'staticData': wf.get('staticData')}
result = api('/workflows/JmiydfZHpeU8tnic', method='PUT', data=payload)
print('Deploy OK:', result.get('id'), '| ativo:', result.get('active'))

# Verificar Code2 no resultado
for n in result.get('nodes', []):
    if n['name'] == 'Code2':
        expr = n['parameters']['assignments']['assignments'][0]['value']
        print('Code2 final expr:', expr[:150])

# Enviar teste
time.sleep(2)
p = {
    'object': 'whatsapp_business_account',
    'entry': [{'id': 'TEST', 'changes': [{'value': {
        'messaging_product': 'whatsapp',
        'metadata': {'display_phone_number': '15550000000', 'phone_number_id': '115216611574100'},
        'contacts': [{'profile': {'name': 'Teste Lead 1'}, 'wa_id': '5511900000001'}],
        'messages': [{'from': '5511900000001', 'id': f'test6_{int(time.time())}',
            'timestamp': str(int(time.time())),
            'text': {'body': 'Oi, tenho uma clinica medica e quero entender o agente de IA'},
            'type': 'text'}]
    }, 'field': 'messages'}]}]
}
req = urllib.request.Request(WEBHOOK_URL, data=json.dumps(p).encode(),
    method='POST', headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
    print('Teste enviado: HTTP', r.status)

print('Aguardando 50s...')
time.sleep(50)

execs = api('/executions?workflowId=JmiydfZHpeU8tnic&limit=3')
for e in execs.get('data', []):
    s = e.get('status')
    eid = e.get('id')
    print(f'[{s}] {e.get("startedAt","")[:19]} | id={eid}')
    ed = api(f'/executions/{eid}?includeData=true')
    if s == 'success':
        for nn, runs in ed.get('data',{}).get('resultData',{}).get('runData',{}).items():
            if nn in ['Orquestrador', 'Code2', 'Meta Send Message']:
                for run in runs:
                    out = run.get('data',{}).get('main',[[]])
                    if out and out[0]:
                        print(f'  {nn}: {str(out[0][0].get("json",{}))[:200]}')
    elif s == 'error':
        err = ed.get('data',{}).get('resultData',{}).get('error',{})
        no = err.get('node',{})
        print(f'  ERRO: {str(err.get("message",""))[:200]}')
        print(f'  NO: {no.get("name","") if isinstance(no,dict) else ""}')
