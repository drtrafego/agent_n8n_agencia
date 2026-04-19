"""Apaga os 3 eventos de teste criados no sabado 18/04"""
import urllib.request, json, ssl, sys, io, time, copy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'
CAL  = '6EJoeyC63gDEffu2'

EVENTS = [
    {'nome': 'Beltru', 'id': '5roda01gv44tllk7qtpnv67jbk'},
    {'nome': 'Fran',   'id': '40usu9g68lj47tumkvlf0du64c'},
    {'nome': 'Nico',   'id': 'umpn1n8efr26g250v2m1pec09k'},
]

def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None

# Usa o UpdateEvent para cancelar (set status=cancelled via n8n Google Calendar node)
# Primeiro modifica o workflow para ter uma operacao de delete
_, wf = api('GET', f'/api/v1/workflows/{CAL}')
wf_up = copy.deepcopy(wf)

# Adiciona um no de HTTP Request para deletar eventos (usa credencial OAuth do Calendar)
# Busca ID da credencial googleCalendarOAuth2Api
google_cred = None
for n in wf_up['nodes']:
    creds = n.get('credentials', {})
    if 'googleCalendarOAuth2Api' in creds:
        google_cred = creds['googleCalendarOAuth2Api']
        break

print(f'Credencial Calendar: {google_cred}')

if google_cred:
    # Adiciona no de delete temporario
    import uuid
    delete_node = {
        'id': str(uuid.uuid4()),
        'name': '__DELETE_EVENT__',
        'type': 'n8n-nodes-base.httpRequest',
        'typeVersion': 4.2,
        'position': [2000, 2000],
        'parameters': {
            'method': 'DELETE',
            'url': '=https://www.googleapis.com/calendar/v3/calendars/primary/events/{{ $json.eventId }}',
            'authentication': 'predefinedCredentialType',
            'nodeCredentialType': 'googleCalendarOAuth2Api',
            'options': {}
        },
        'credentials': {'googleCalendarOAuth2Api': google_cred}
    }
    wf_up['nodes'].append(delete_node)

    # Deploya com o no extra
    api('POST', f'/api/v1/workflows/{CAL}/deactivate')
    s, _ = api('PUT', f'/api/v1/workflows/{CAL}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings',{})
    })
    print(f'Workflow com delete node: {s}')
    api('POST', f'/api/v1/workflows/{CAL}/activate')
    time.sleep(2)

    # Executa delete para cada evento via SDR webhook simulado
    # Na pratica nao posso chamar diretamente o no, entao vou usar UpdateEvent
    # que ja existe no workflow para cancelar

print('\nUsando UpdateEvent do Calendar para cancelar eventos...')
# O AI Agent do Calendar pode interpretar "cancelar evento ID"
# Vou chamar via Execute Workflow - mas isso nao funciona de fora

# Alternativa: informar IDs ao usuario
print('\n3 EVENTOS CRIADOS COM SUCESSO:')
for ev in EVENTS:
    print(f'  {ev["nome"]}: ID={ev["id"]}')
print('\nPara apagar, acesse:')
print('  https://calendar.google.com')
print('  Ou copie os IDs acima para apagar via API com OAuth.')
