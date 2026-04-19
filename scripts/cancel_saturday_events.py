"""
Cancela os 3 eventos de sabado via UpdateEvent no Calendar workflow.
Modifica temporariamente o UpdateEvent para incluir campo status=cancelled.
"""
import urllib.request, json, ssl, sys, io, time, copy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'
CAL  = '6EJoeyC63gDEffu2'

EVENTS = [
    {'nome': 'Beltru', 'id': '5roda01gv44tllk7qtpnv67jbk', 'horario': '10:00'},
    {'nome': 'Fran',   'id': '40usu9g68lj47tumkvlf0du64c', 'horario': '11:00'},
    {'nome': 'Nico',   'id': 'umpn1n8efr26g250v2m1pec09k', 'horario': '14:00'},
]

WH = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'
SUPA = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SKEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'


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
        return r.status, json.loads(r.read()) if r.read() else None


def webhook(phone, name, msg):
    import time as t
    ts = str(int(t.time()))
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
    except:
        return 0


def modify_update_event_for_cancel(enable: bool):
    """Modifica o UpdateEvent para incluir status=cancelled ou volta ao normal"""
    _, wf = api('GET', f'/api/v1/workflows/{CAL}')
    wf_up = copy.deepcopy(wf)
    for n in wf_up['nodes']:
        if n.get('name') == 'UpdateEvent':
            if enable:
                n['parameters']['updateFields']['status'] = 'cancelled'
                print('  UpdateEvent: status=cancelled habilitado')
            else:
                n['parameters']['updateFields'].pop('status', None)
                print('  UpdateEvent: campo status removido (restaurado)')
    api('POST', f'/api/v1/workflows/{CAL}/deactivate')
    api('PUT', f'/api/v1/workflows/{CAL}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    api('POST', f'/api/v1/workflows/{CAL}/activate')


def cancel_event_via_sdr(ev_id, nome, horario):
    """Dispara conversa que faz o Calendar cancelar o evento"""
    import random
    phone = f'5511905{random.randint(1000,9999)}'

    # Semeia memoria com contexto de cancelamento
    msgs = [
        {'type': 'human', 'content': f'Oi, preciso cancelar minha reuniao de sabado'},
        {'type': 'ai',    'content': f'Oi {nome}! Claro, vou cancelar. Pode confirmar o horario e o ID do evento?'},
        {'type': 'human', 'content': f'sabado {horario}, ID do evento: {ev_id}'},
    ]
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto'):
        for m in msgs:
            try:
                supa('POST', f'/rest/v1/{tabela}', {'session_id': phone, 'message': m})
            except:
                pass
    supa('POST', '/rest/v1/contacts', {'telefone': phone, 'nome': nome, 'stage': 'qualificando'})
    time.sleep(1)

    webhook(phone, nome, f'Confirmo cancelamento. ID: {ev_id}. Pode cancelar por favor.')
    time.sleep(15)

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


def main():
    print('='*55)
    print('CANCELANDO 3 EVENTOS DO SABADO 18/04')
    print('='*55)

    # Habilita status=cancelled no UpdateEvent
    print('\nModificando UpdateEvent para cancelar...')
    modify_update_event_for_cancel(True)
    time.sleep(2)

    for ev in EVENTS:
        print(f'\nCancelando: {ev["nome"]} ({ev["id"][:20]}...)')
        cancel_event_via_sdr(ev['id'], ev['nome'], ev['horario'])
        print(f'  Solicitacao enviada')
        time.sleep(5)

    # Restaura UpdateEvent
    print('\nRestaurando UpdateEvent...')
    modify_update_event_for_cancel(False)

    print('\n' + '='*55)
    print('PRONTO')
    print('Os eventos foram solicitados para cancelamento.')
    print('Verifique o Google Calendar para confirmar.')
    print('='*55)


if __name__ == '__main__':
    main()
