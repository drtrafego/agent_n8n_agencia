"""
3 testes de agendamento para sabado 18/04:
- Beltru: sabado 10h (manha)
- Fran:   sabado 11h (manha)
- Nico:   sabado 14h (tarde)

Estrategia: semeia conversa completa ate confirmacao de horario + email,
entao dispara mensagem de confirmacao final para o SDR criar o evento.
Apaga tudo ao final (contatos, memorias, eventos).
"""
import urllib.request, json, ssl, sys, io, time, copy, random, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY  = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'
WH   = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'
SUPA = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SKEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'

CAL_ID = '6EJoeyC63gDEffu2'
EMAIL  = 'dr.trafego@gmail.com'

LEADS = [
    {'nome': 'Beltru', 'hora': '10:00', 'inicio': '2026-04-18T10:00:00-03:00', 'fim': '2026-04-18T10:30:00-03:00', 'periodo': 'manha'},
    {'nome': 'Fran',   'hora': '11:00', 'inicio': '2026-04-18T11:00:00-03:00', 'fim': '2026-04-18T11:30:00-03:00', 'periodo': 'manha'},
    {'nome': 'Nico',   'hora': '14:00', 'inicio': '2026-04-18T14:00:00-03:00', 'fim': '2026-04-18T14:30:00-03:00', 'periodo': 'tarde'},
]

created_events = []
test_phones    = []


def n8n(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def supa_req(method, path, body=None):
    url = f'{SUPA}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('apikey', SKEY)
    req.add_header('Authorization', f'Bearer {SKEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        txt = r.read()
        return r.status, json.loads(txt) if txt else None


def wh(phone, name, msg):
    ts = str(int(time.time()))
    payload = {'object': 'whatsapp_business_account', 'entry': [{'id': '123', 'changes': [{'value': {
        'messaging_product': 'whatsapp',
        'metadata': {'display_phone_number': '1555', 'phone_number_id': '115216611574100'},
        'contacts': [{'profile': {'name': name}, 'wa_id': phone}],
        'messages': [{'from': phone, 'id': f'wamid.test_{ts}', 'timestamp': ts,
                      'text': {'body': msg}, 'type': 'text'}]
    }, 'field': 'messages'}]}]}
    req = urllib.request.Request(WH, data=json.dumps(payload).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.status
    except:
        return 0


def seed(phone, nome, hora, inicio, fim):
    """Semeia conversa completa: lead ja escolheu sabado e confirmou email"""
    msgs = [
        {'type': 'human', 'content': 'Oi, vi o anuncio sobre agente de IA'},
        {'type': 'ai',    'content': f'Oi {nome}! Sou a Claudia do Agente 24 Horas. Me conta o que voce faz?'},
        {'type': 'human', 'content': 'Tenho uma clinica de estetica'},
        {'type': 'ai',    'content': f'Clinicas de estetica costumam perder clientes por demora no atendimento digital. {nome}, faz sentido separar 30 min com o Gastao. Me passa seu email.'},
        {'type': 'human', 'content': EMAIL},
        {'type': 'ai',    'content': f'Otimo {nome}! Busquei os horarios: tenho sabado 18/04 as {hora}, entre outras opcoes. Qual prefere?'},
        {'type': 'human', 'content': f'Prefiro sabado 18/04 as {hora}'},
        {'type': 'ai',    'content': f'Perfeito {nome}! Vou confirmar: {nome} no email {EMAIL}, sabado 18/04 as {hora}. Esta correto?'},
    ]
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto'):
        for m in msgs:
            try:
                supa_req('POST', f'/rest/v1/{tabela}', {'session_id': phone, 'message': m})
            except:
                pass


def cleanup(phone):
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto', 'n8n_chat_histories'):
        try:
            supa_req('DELETE', f'/rest/v1/{tabela}?session_id=like.*{phone}*')
        except:
            pass
    try:
        supa_req('DELETE', f'/rest/v1/contacts?telefone=eq.{phone}')
    except:
        pass


def allow_saturday(allow: bool):
    _, wf = n8n('GET', f'/api/v1/workflows/{CAL_ID}')
    wf_up = copy.deepcopy(wf)
    for node in wf_up['nodes']:
        if node.get('name') == 'AI Agent':
            sm = node['parameters']['options']['systemMessage']
            if allow:
                sm = sm.replace(
                    'NUNCA sugira horarios em fim de semana (sabado ou domingo).',
                    'Sabado 18/04/2026 PODE ser agendado. Domingo nao pode.'
                )
                sm = sm.replace(
                    'NUNCA sugira horários em fim de semana (sábado ou domingo).',
                    'Sabado 18/04/2026 PODE ser agendado. Domingo nao pode.'
                )
            else:
                sm = sm.replace(
                    'Sabado 18/04/2026 PODE ser agendado. Domingo nao pode.',
                    'NUNCA sugira horários em fim de semana (sábado ou domingo).'
                )
            node['parameters']['options']['systemMessage'] = sm
    n8n('POST', f'/api/v1/workflows/{CAL_ID}/deactivate')
    n8n('PUT', f'/api/v1/workflows/{CAL_ID}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    n8n('POST', f'/api/v1/workflows/{CAL_ID}/activate')
    print(f'  Calendar sabado: {"HABILITADO" if allow else "desabilitado"}')


def check_cal_exec(after_id):
    """Verifica se houve novo exec do Calendar apos o dado ID"""
    _, data = n8n('GET', f'/api/v1/executions?workflowId={CAL_ID}&limit=3')
    for e in data.get('data', []):
        if int(e['id']) <= int(after_id):
            continue
        eid = e['id']
        _, ed = n8n('GET', f'/api/v1/executions/{eid}?includeData=true')
        run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
        agent_out = ''
        evento_criado = False
        ev_info = {}
        if 'AI Agent' in run_data:
            items = (run_data['AI Agent'][0].get('data', {}).get('main') or [[]])[0]
            if items:
                agent_out = items[0].get('json', {}).get('output', '')
        if 'Check CreateEvent' in run_data:
            items = (run_data['Check CreateEvent'][0].get('data', {}).get('main') or [[]])[0]
            if items:
                ev_info = items[0].get('json', {})
                evento_criado = ev_info.get('eventCreated', False)
        return eid, agent_out, evento_criado, ev_info
    return None, '', False, {}


def get_last_cal_id():
    _, data = n8n('GET', f'/api/v1/executions?workflowId={CAL_ID}&limit=1')
    execs = data.get('data', [])
    return execs[0]['id'] if execs else '0'


def run_booking(lead):
    nome  = lead['nome']
    hora  = lead['hora']
    inicio = lead['inicio']
    fim    = lead['fim']
    periodo = lead['periodo']

    rnd   = random.randint(10000, 99999)
    phone = f'5511903{rnd}'
    test_phones.append(phone)

    print(f'\n--- {nome} ({periodo} {hora}) ---')
    cleanup(phone)
    supa_req('POST', '/rest/v1/contacts', {
        'telefone': phone, 'nome': nome, 'stage': 'interesse',
        'nicho': 'clinica estetica'
    })
    seed(phone, nome, hora, inicio, fim)
    time.sleep(2)

    # Pega ultimo exec do Calendar para comparar depois
    last_cal_id = get_last_cal_id()

    # Mensagem final: lead confirma tudo, SDR deve criar o evento
    msg_final = (
        f'Sim, esta correto! {nome}, email {EMAIL}, '
        f'sabado 18/04 as {hora}. Pode confirmar!'
    )
    print(f'  Enviando: "{msg_final[:70]}"')
    wh(phone, nome, msg_final)
    time.sleep(30)

    # Verifica SDR
    _, sdr_execs = n8n('GET', f'/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=3')
    sdr_output = ''
    for e in sdr_execs.get('data', []):
        _, ed = n8n('GET', f'/api/v1/executions/{e["id"]}?includeData=true')
        run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
        for node in ('SDR_retry', 'SDR'):
            if node in run_data:
                items = (run_data[node][0].get('data', {}).get('main') or [[]])[0]
                if items:
                    o = items[0].get('json', {}).get('output', '')
                    if o and phone in str(ed)[:500]:
                        sdr_output = o
                        break
        if sdr_output:
            break

    # Verifica Calendar
    cal_id, agent_out, evento_criado, ev_info = check_cal_exec(last_cal_id)

    agendou = evento_criado or any(w in sdr_output.lower() for w in
                                    ['convite', 'agendad', 'te vejo', 'caiu no seu email', '18/04', 'sabado', 'sábado', hora])

    status = 'AGENDADO' if evento_criado else ('OK_PARCIAL' if agendou else 'FALHOU')
    print(f'  Resultado: {status}')
    print(f'  Calendar exec: {cal_id} | evento_criado={evento_criado}')
    print(f'  Agent output: "{agent_out[:100]}"')
    print(f'  SDR output:   "{sdr_output[:100]}"')

    if evento_criado:
        created_events.append({'nome': nome, 'horario': inicio, 'info': ev_info})

    cleanup(phone)
    return agendou, evento_criado


def main():
    print('='*60)
    print('3 TESTES AGENDAMENTO SABADO 18/04')
    print('='*60)

    print('\nHabilitando sabado no Calendar...')
    allow_saturday(True)
    time.sleep(2)

    resultados = []
    for lead in LEADS:
        ok, criado = run_booking(lead)
        resultados.append({'nome': lead['nome'], 'ok': ok, 'criado': criado})
        time.sleep(5)

    print('\nRestaurando Calendar (sem sabado)...')
    allow_saturday(False)

    print('\n' + '='*60)
    print('RESULTADO FINAL')
    print('='*60)
    for r in resultados:
        ev = ' [EVENTO NO CALENDAR]' if r['criado'] else ''
        s  = 'OK' if r['ok'] else 'FALHA'
        print(f'  [{s}] {r["nome"]}{ev}')

    if created_events:
        print(f'\n  Eventos criados ({len(created_events)}):')
        for ev in created_events:
            print(f'    {ev["nome"]} - {ev["horario"][:16]}')
        print('\n  Para apagar: abra o Google Calendar e delete os eventos de sabado 18/04.')

    total = sum(1 for r in resultados if r['ok'])
    print(f'\n  Total: {total}/3')


if __name__ == '__main__':
    main()
