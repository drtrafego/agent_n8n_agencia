import urllib.request, json, ssl, sys, time
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com/api/v1'
WEBHOOK_URL = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'

def api(path):
    req = urllib.request.Request(BASE+path, headers={'X-N8N-API-KEY': KEY})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())

def send(phone, name, msg, idx):
    p = {'object':'whatsapp_business_account','entry':[{'id':'TEST','changes':[{'value':{
        'messaging_product':'whatsapp',
        'metadata':{'display_phone_number':'15550000000','phone_number_id':'115216611574100'},
        'contacts':[{'profile':{'name':name},'wa_id':phone}],
        'messages':[{'from':phone,'id':f'test_final_{idx}_{int(time.time())}',
            'timestamp':str(int(time.time())),'text':{'body':msg},'type':'text'}]
    },'field':'messages'}]}]}
    req = urllib.request.Request(WEBHOOK_URL, data=json.dumps(p).encode(),
        method='POST', headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return r.status

testes = [
    ('5511900000001', 'Joao Clinica',    'Oi, tenho uma clinica medica e quero entender como funciona o agente'),
    ('5511900000002', 'Maria Roupas',    'Tenho loja de roupas, quero marcar call sabado de manha com o Gastao'),
    ('5511900000003', 'Pedro Imoveis',   'Trabalho com imobiliaria, email pedro@gmail.com, quero marcar pra sabado 9h'),
    ('5511900000004', 'Ana Restaurante', 'Tenho restaurante, email ana@gmail.com, pode marcar sabado manha?'),
    ('5511900000005', 'Carlos Tech',     'Vi o anuncio de voces, gostaria de saber mais sobre o agente de IA'),
]

print('=== ENVIANDO 5 TESTES ===')
for i, (phone, name, msg) in enumerate(testes, 1):
    s = send(phone, name, msg, i)
    print(f'Teste {i} [{name}]: HTTP {s}')
    time.sleep(3)

print()
print('Aguardando 60s para processar...')
time.sleep(60)

execs = api('/executions?workflowId=JmiydfZHpeU8tnic&limit=10')
items = execs.get('data', [])

ok = err = 0
print()
print('=== RESULTADOS ===')
for e in items[:6]:
    s = e.get('status')
    eid = e.get('id')
    started = e.get('startedAt','')[:19]
    if s == 'success':
        ok += 1
        ed = api(f'/executions/{eid}?includeData=true')
        orq_out = ''
        for nn, runs in ed.get('data',{}).get('resultData',{}).get('runData',{}).items():
            if nn == 'Orquestrador':
                for run in runs:
                    out = run.get('data',{}).get('main',[[]])
                    if out and out[0]:
                        orq_out = out[0][0].get('json',{}).get('output','')[:100]
        print(f'[OK] {started} | Resposta: {orq_out}...')
    else:
        err += 1
        ed = api(f'/executions/{eid}?includeData=true')
        erro = ed.get('data',{}).get('resultData',{}).get('error',{})
        no = erro.get('node',{})
        print(f'[ERRO] {started} | {str(erro.get("message",""))[:100]} | no={no.get("name","") if isinstance(no,dict) else ""}')

print()
print(f'PLACAR FINAL: {ok} sucesso / {err} erro')
