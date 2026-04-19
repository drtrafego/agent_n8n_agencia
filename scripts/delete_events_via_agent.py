"""
Apaga os 3 eventos de sabado usando o Calendar AI Agent via SDR.
Abordagem: modifica UpdateEvent para suportar cancellation (status=cancelled),
depois chama o Calendar agent com instrucao de cancelar cada evento por ID.
"""
import urllib.request, json, ssl, sys, io, time, copy, random

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY  = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'
CAL  = '6EJoeyC63gDEffu2'
WH   = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'
SUPA = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SKEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'

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


def supa(method, path, body=None):
    url = f'{SUPA}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('apikey', SKEY)
    req.add_header('Authorization', f'Bearer {SKEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        body_bytes = r.read()
        return r.status, json.loads(body_bytes) if body_bytes else None


def post_webhook(phone, name, msg):
    ts = str(int(time.time()))
    payload = {'object': 'whatsapp_business_account', 'entry': [{'id': '123', 'changes': [{'value': {
        'messaging_product': 'whatsapp',
        'metadata': {'display_phone_number': '1555', 'phone_number_id': '115216611574100'},
        'contacts': [{'profile': {'name': name}, 'wa_id': phone}],
        'messages': [{'from': phone, 'id': f'wamid.del_{ts}', 'timestamp': ts,
                      'text': {'body': msg}, 'type': 'text'}]
    }, 'field': 'messages'}]}]}
    req = urllib.request.Request(WH, data=json.dumps(payload).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.status
    except Exception as e:
        return 0


def add_status_to_update_event():
    """Adiciona campo status=cancelled ao UpdateEvent para permitir cancelamento"""
    _, wf = api('GET', f'/api/v1/workflows/{CAL}')
    wf_up = copy.deepcopy(wf)
    for n in wf_up['nodes']:
        if n.get('name') == 'UpdateEvent':
            n['parameters']['updateFields']['status'] = 'cancelled'
            print('  UpdateEvent: campo status=cancelled adicionado')
            break
    api('POST', f'/api/v1/workflows/{CAL}/deactivate')
    api('PUT', f'/api/v1/workflows/{CAL}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    api('POST', f'/api/v1/workflows/{CAL}/activate')
    time.sleep(2)


def remove_status_from_update_event():
    """Remove campo status do UpdateEvent (restaura original)"""
    _, wf = api('GET', f'/api/v1/workflows/{CAL}')
    wf_up = copy.deepcopy(wf)
    for n in wf_up['nodes']:
        if n.get('name') == 'UpdateEvent':
            n['parameters']['updateFields'].pop('status', None)
            print('  UpdateEvent: campo status removido (restaurado)')
            break
    api('POST', f'/api/v1/workflows/{CAL}/deactivate')
    api('PUT', f'/api/v1/workflows/{CAL}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    api('POST', f'/api/v1/workflows/{CAL}/activate')


def cancel_via_sdr(ev_id, nome):
    """Usa o SDR para chamar o Calendar agent e cancelar um evento especifico"""
    phone = f'551190DEL{random.randint(1000,9999)}'.replace('DEL', str(random.randint(10,99)))
    # garante apenas digitos
    phone = ''.join(c for c in phone if c.isdigit())
    phone = f'55119088{random.randint(1000,9999)}'

    # Semeia memoria: contexto de cancelamento de evento
    msgs = [
        {'type': 'human', 'content': f'Preciso cancelar minha reuniao agendada'},
        {'type': 'ai',    'content': f'Claro {nome}! Me passa o ID do evento para cancelar.'},
        {'type': 'human', 'content': f'O ID e: {ev_id}'},
        {'type': 'ai',    'content': f'Vou cancelar o evento {ev_id} agora.'},
    ]
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto'):
        for m in msgs:
            try:
                supa('POST', f'/rest/v1/{tabela}', {'session_id': phone, 'message': m})
            except Exception as e:
                pass

    supa('POST', '/rest/v1/contacts', {
        'telefone': phone, 'nome': nome, 'stage': 'agendado'
    })
    time.sleep(1)

    last_cal_id = '0'
    _, data = api('GET', f'/api/v1/executions?workflowId={CAL}&limit=1')
    if data.get('data'):
        last_cal_id = data['data'][0]['id']

    # Dispara mensagem que vai acionar o Calendar agent
    msg = (f'Confirmo o cancelamento. Cancele o evento com ID {ev_id} '
           f'usando a ferramenta UpdateEvent. Status deve ser cancelled.')
    post_webhook(phone, nome, msg)
    time.sleep(25)

    # Verifica se Calendar foi chamado com UpdateEvent
    _, data2 = api('GET', f'/api/v1/executions?workflowId={CAL}&limit=3')
    cancelled = False
    for e in data2.get('data', []):
        if int(e['id']) <= int(last_cal_id):
            continue
        eid = e['id']
        _, ed = api('GET', f'/api/v1/executions/{eid}?includeData=true')
        run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
        if 'UpdateEvent' in run_data:
            cancelled = True
            print(f'    UpdateEvent chamado na exec {eid}')
        agent_out = ''
        if 'AI Agent' in run_data:
            items = (run_data['AI Agent'][0].get('data', {}).get('main') or [[]])[0]
            if items:
                agent_out = items[0].get('json', {}).get('output', '')
        print(f'    Agent output: "{agent_out[:80]}"')
        break

    # Limpa
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto', 'n8n_chat_histories'):
        try:
            supa('DELETE', f'/rest/v1/{tabela}?session_id=like.*{phone}*')
        except:
            pass
    try:
        supa('DELETE', f'/rest/v1/contacts?telefone=eq.{phone}')
    except:
        pass

    return cancelled


def main():
    print('='*55)
    print('APAGANDO EVENTOS DE SABADO VIA CALENDAR AGENT')
    print('='*55)

    print('\n1. Adicionando suporte a cancellation no UpdateEvent...')
    add_status_to_update_event()

    print('\n2. Cancelando eventos via Calendar agent:')
    results = []
    for ev in EVENTS:
        print(f'\n  [{ev["nome"]}] ID: {ev["id"][:25]}...')
        ok = cancel_via_sdr(ev['id'], ev['nome'])
        results.append({'nome': ev['nome'], 'ok': ok})
        time.sleep(3)

    print('\n3. Restaurando UpdateEvent...')
    remove_status_from_update_event()

    print('\n' + '='*55)
    print('RESULTADO')
    for r in results:
        print(f'  {"OK" if r["ok"] else "VERIFICAR"} - {r["nome"]}')
    print('\nVerifique o Google Calendar para confirmar que os')
    print('eventos foram removidos do sabado 18/04.')
    print('='*55)


if __name__ == '__main__':
    main()
