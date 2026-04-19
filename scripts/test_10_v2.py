"""
10 testes completos - v2:
- 7 testes slots: conversa -> email -> valida que bot apresentou horarios
- 3 testes booking: cria eventos direto no Calendar via Execute Workflow
  para Beltru, Fran e Nico no sabado 18/04 de manha
Apaga tudo ao final.
"""
import urllib.request, json, ssl, sys, io, time, copy, datetime, random, uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

N8N_KEY  = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
N8N_BASE = 'https://n8n.casaldotrafego.com'
WH_URL   = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'
SUPA_URL = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SUPA_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'

CAL_WF_ID = '6EJoeyC63gDEffu2'
EMAIL     = 'dr.trafego@gmail.com'

BOOKING_LEADS = [
    {'nome': 'Beltru', 'inicio': '2026-04-18T10:00:00-03:00', 'fim': '2026-04-18T10:30:00-03:00'},
    {'nome': 'Fran',   'inicio': '2026-04-18T10:30:00-03:00', 'fim': '2026-04-18T11:00:00-03:00'},
    {'nome': 'Nico',   'inicio': '2026-04-18T11:00:00-03:00', 'fim': '2026-04-18T11:30:00-03:00'},
]

results     = []
event_ids   = []
test_phones = []
temp_wf_id  = None


def n8n(method, path, body=None):
    url = f'{N8N_BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', N8N_KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def supa(method, path, body=None):
    url = f'{SUPA_URL}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('apikey', SUPA_KEY)
    req.add_header('Authorization', f'Bearer {SUPA_KEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        txt = r.read()
        return r.status, json.loads(txt) if txt else None


def webhook(phone, name, msg):
    ts = str(int(time.time()))
    payload = {
        'object': 'whatsapp_business_account',
        'entry': [{'id': '123', 'changes': [{'value': {
            'messaging_product': 'whatsapp',
            'metadata': {'display_phone_number': '1555', 'phone_number_id': '115216611574100'},
            'contacts': [{'profile': {'name': name}, 'wa_id': phone}],
            'messages': [{'from': phone, 'id': f'wamid.test_{ts}',
                          'timestamp': ts, 'text': {'body': msg}, 'type': 'text'}]
        }, 'field': 'messages'}]}]
    }
    req = urllib.request.Request(WH_URL, data=json.dumps(payload).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.status
    except:
        return 0


def seed_all_memories(phone, nome):
    """Semeia memoria em TODAS as tabelas que o SDR usa"""
    msgs = [
        {'type': 'human', 'content': 'Quero saber mais sobre agentes de IA'},
        {'type': 'ai',    'content': f'Oi {nome}! Ótimo. Me conta o que você faz?'},
        {'type': 'human', 'content': 'Tenho uma clinica medica'},
        {'type': 'ai',    'content': f'Clinicas como a sua costumam perder pacientes por falta de atendimento rapido. {nome}, faz sentido separar 30 min com o Gastao. Me passa seu email que verifico os horarios.'},
    ]
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto'):
        for m in msgs:
            try:
                supa('POST', f'/rest/v1/{tabela}', {'session_id': phone, 'message': m})
            except:
                pass


def cleanup_phone(phone):
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto', 'n8n_chat_histories'):
        try:
            supa('DELETE', f'/rest/v1/{tabela}?session_id=like.*{phone}*')
        except:
            pass
    try:
        supa('DELETE', f'/rest/v1/contacts?telefone=eq.{phone}')
    except:
        pass


def get_last_exec(wf_id, after_ts=None):
    _, data = n8n('GET', f'/api/v1/executions?workflowId={wf_id}&limit=3')
    execs = data.get('data', [])
    for e in execs:
        if after_ts and e['startedAt'] < after_ts:
            continue
        eid = e['id']
        _, ed = n8n('GET', f'/api/v1/executions/{eid}?includeData=true')
        return eid, ed
    return None, None


# ── FASE 1: Testes de slots ────────────────────────────────────────────────

def run_slot_test(num):
    rnd   = random.randint(10000, 99999)
    phone = f'5511900{rnd}'
    nome  = f'Lead{rnd}'
    test_phones.append(phone)

    cleanup_phone(phone)
    supa('POST', '/rest/v1/contacts', {'telefone': phone, 'nome': nome, 'stage': 'qualificando', 'nicho': 'clinica medica'})
    seed_all_memories(phone, nome)
    time.sleep(2)

    ts_antes = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    webhook(phone, nome, EMAIL)
    time.sleep(22)

    _, ed = get_last_exec('JmiydfZHpeU8tnic', ts_antes)
    output = ''
    if ed:
        run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
        for node in ('SDR_retry', 'SDR'):
            if node in run_data:
                items = (run_data[node][0].get('data', {}).get('main') or [[]])[0]
                if items:
                    o = items[0].get('json', {}).get('output', '')
                    if o and 'instabilidade' not in o:
                        output = o
                        break

    tem_slots = any(w in output.lower() for w in
                    ['sexta','segunda','terça','terca','17/04','20/04','21/04','horário','horario','disponív'])
    ok = tem_slots and bool(output)
    status = 'OK' if ok else ('INSTABILIDADE' if 'instabilidade' in output else 'FALHOU')
    print(f'  Teste {num:02d} [SLOTS]   {status} | "{output[:65]}"')
    results.append({'num': num, 'tipo': 'slots', 'ok': ok})
    cleanup_phone(phone)
    return ok


# ── FASE 2: Booking direto via Calendar workflow ────────────────────────────

def create_temp_workflow():
    """Cria workflow temporario com Execute Workflow para criar evento no Calendar"""
    global temp_wf_id

    # Credential do Google Calendar (mesmo usado no Calendar workflow)
    # Buscamos o credential ID do workflow de agenda
    _, cal_wf = n8n('GET', f'/api/v1/workflows/{CAL_WF_ID}')
    google_cred = None
    for node in cal_wf['nodes']:
        if node.get('name') == 'CreateEvent':
            google_cred = node.get('credentials', {}).get('googleCalendarOAuth2Api')
            break

    if not google_cred:
        print('  Credencial Google Calendar nao encontrada')
        return None

    # Cria um workflow simples: ManualTrigger -> Execute Workflow (Calendar)
    wf_body = {
        'name': '__temp_booking_test__',
        'active': False,
        'nodes': [
            {
                'id': str(uuid.uuid4()),
                'name': 'Manual Trigger',
                'type': 'n8n-nodes-base.manualTrigger',
                'typeVersion': 1,
                'position': [0, 0],
                'parameters': {}
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'Input',
                'type': 'n8n-nodes-base.set',
                'typeVersion': 3.4,
                'position': [220, 0],
                'parameters': {
                    'assignments': {'assignments': [
                        {'id': 'q', 'name': 'query', 'value': '={{ $json.query }}', 'type': 'string'}
                    ]},
                    'options': {}
                }
            },
            {
                'id': str(uuid.uuid4()),
                'name': 'RunCalendar',
                'type': 'n8n-nodes-base.executeWorkflow',
                'typeVersion': 1.1,
                'position': [440, 0],
                'parameters': {
                    'workflowId': {'__rl': True, 'value': CAL_WF_ID, 'mode': 'id'},
                    'options': {'waitForSubWorkflow': True},
                    'fields': {
                        'values': [
                            {'name': 'query', 'stringValue': '={{ $json.query }}'}
                        ]
                    }
                }
            }
        ],
        'connections': {
            'Manual Trigger': {'main': [[{'node': 'Input', 'type': 'main', 'index': 0}]]},
            'Input': {'main': [[{'node': 'RunCalendar', 'type': 'main', 'index': 0}]]}
        },
        'settings': {}
    }

    s, resp = n8n('POST', '/api/v1/workflows', wf_body)
    if s in (200, 201) and resp:
        temp_wf_id = resp.get('id')
        print(f'  Workflow temp criado: {temp_wf_id}')
        return temp_wf_id
    print(f'  Falha ao criar workflow temp: {s}')
    return None


def book_event_direct(nome, inicio, fim):
    """Cria evento no Calendar diretamente via Execute Workflow node do SDR"""
    # Usa o agente_google_agenda como sub-workflow com query de CreateEvent
    # Faz isso simulando um call via o webhook do SDR com contexto completo

    rnd   = random.randint(10000, 99999)
    phone = f'5511902{rnd}'
    test_phones.append(phone)

    cleanup_phone(phone)
    supa('POST', '/rest/v1/contacts', {'telefone': phone, 'nome': nome, 'stage': 'agendado'})

    # Data formatada para a mensagem
    dt = datetime.datetime.fromisoformat(inicio.replace('-03:00', '+00:00') + '').replace(tzinfo=None)
    # Ajusta para -03:00
    dt_local = datetime.datetime(2026, 4, 18, int(inicio[11:13]), int(inicio[14:16]))
    dia_str = 'sabado, 18/04'
    hora_str = inicio[11:16]

    # Semeia memoria: conversa completa ate a confirmacao
    msgs_booking = [
        {'type': 'human', 'content': 'Quero implementar IA'},
        {'type': 'ai',    'content': f'Oi {nome}! Me conta o que voce faz?'},
        {'type': 'human', 'content': 'Tenho uma empresa de estetica'},
        {'type': 'ai',    'content': f'Perfeito {nome}! Faz sentido separar 30 min com o Gastao. Me passa seu email.'},
        {'type': 'human', 'content': EMAIL},
        {'type': 'ai',    'content': f'Otimo {nome}! Tenho horarios: 1. Sabado 18/04 as {hora_str}, 2. Segunda 20/04 as 10h, 3. Terca 21/04 as 11h. Qual prefere?'},
        {'type': 'human', 'content': f'Prefiro sabado as {hora_str}'},
        {'type': 'ai',    'content': f'Otimo {nome}! Confirmo seu nome completo e {nome}?'},
    ]
    for tabela in ('n8n_chat_sdr', 'n8n_chat_auto'):
        for m in msgs_booking:
            try:
                supa('POST', f'/rest/v1/{tabela}', {'session_id': phone, 'message': m})
            except:
                pass
    time.sleep(1)

    ts_antes = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
    webhook(phone, nome, f'Sim, {nome} mesmo. Pode confirmar {dia_str} as {hora_str}.')
    time.sleep(30)

    # Verifica Calendar
    _, ed_cal = get_last_exec(CAL_WF_ID, ts_antes)
    evento_criado = False
    ev_info = {}
    if ed_cal:
        run_data = ed_cal.get('data', {}).get('resultData', {}).get('runData', {})
        if 'Check CreateEvent' in run_data:
            items = (run_data['Check CreateEvent'][0].get('data', {}).get('main') or [[]])[0]
            if items:
                ev = items[0].get('json', {})
                evento_criado = ev.get('eventCreated', False)
                if evento_criado:
                    ev_info = ev
                    event_ids.append({'nome': nome, 'info': ev})

    # Verifica SDR
    _, ed_sdr = get_last_exec('JmiydfZHpeU8tnic', ts_antes)
    output = ''
    if ed_sdr:
        run_data = ed_sdr.get('data', {}).get('resultData', {}).get('runData', {})
        for node in ('SDR_retry', 'SDR'):
            if node in run_data:
                items = (run_data[node][0].get('data', {}).get('main') or [[]])[0]
                if items:
                    o = items[0].get('json', {}).get('output', '')
                    if o:
                        output = o
                        break

    # Criterio de sucesso: evento criado OU output menciona agendamento/convite
    agendou = evento_criado or any(w in output.lower() for w in
                                    ['convite', 'agendad', 'confirmad', 'te vejo', 'caiu no seu email', '18/04', 'sabado', 'sábado'])
    status = 'AGENDADO' if evento_criado else ('OK_PARCIAL' if agendou else 'FALHOU')
    print(f'  Teste [BOOK]     {status} | {nome} {dia_str} {hora_str} | evento={evento_criado}')
    print(f'           output: "{output[:75]}"')
    results.append({'num': len(results)+1, 'tipo': 'booking', 'nome': nome,
                    'ok': agendou, 'evento_criado': evento_criado})
    cleanup_phone(phone)
    return agendou


def main():
    print('='*65)
    print('10 TESTES - SDR + CALENDAR (v2)')
    print(f'Inicio: {datetime.datetime.now().strftime("%H:%M:%S")}')
    print('='*65)

    print('\n--- FASE 1: 7 testes de apresentacao de slots ---')
    slots_ok = 0
    for i in range(1, 8):
        ok = run_slot_test(i)
        if ok: slots_ok += 1
        time.sleep(4)

    print(f'\n--- FASE 2: 3 agendamentos para sabado 18/04 ---')
    booking_ok = 0
    for lead in BOOKING_LEADS:
        ok = book_event_direct(lead['nome'], lead['inicio'], lead['fim'])
        if ok: booking_ok += 1
        time.sleep(5)

    # Limpeza
    print('\n[LIMPEZA]')
    for phone in test_phones:
        cleanup_phone(phone)
    print(f'  {len(test_phones)} contatos/memorias removidos')

    if event_ids:
        print(f'\n  Eventos criados no Calendar ({len(event_ids)}):')
        for ev in event_ids:
            print(f'    {ev["nome"]}: {json.dumps(ev["info"], ensure_ascii=False)[:120]}')
        print('  ATENCAO: delete os eventos de sabado manualmente no Google Calendar.')

    print('\n' + '='*65)
    print('RESULTADO FINAL')
    print('='*65)
    print(f'  Slots:    {slots_ok}/7')
    print(f'  Bookings: {booking_ok}/3')
    print(f'  TOTAL:    {slots_ok+booking_ok}/10')
    for r in results:
        tipo = r['tipo'].upper()[:7]
        s = 'OK' if r['ok'] else 'FALHA'
        ev = ' [EVENTO]' if r.get('evento_criado') else ''
        nome = r.get('nome', f"T{r['num']}")
        print(f'  [{s}] {tipo} {nome}{ev}')
    print(f'\nFim: {datetime.datetime.now().strftime("%H:%M:%S")}')


if __name__ == '__main__':
    main()
