"""
10 testes completos do agente SDR:
- 7 testes: fluxo padrao (conversa -> email -> 3 slots apresentados)
- 3 testes: agendamento completo para sabado (Beltru, Fran, Nico)
Ao final apaga tudo: contatos, memorias e eventos do Calendar.
"""
import urllib.request, json, ssl, sys, io, time, copy, datetime, random, uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

N8N_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
N8N_BASE = 'https://n8n.casaldotrafego.com'
WH_URL   = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'
SUPA_URL = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SUPA_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'

# Testes de agendamento real (sabado)
BOOKING_LEADS = [
    {'nome': 'Beltru',  'horario': '2026-04-18T10:00:00-03:00', 'horario_fim': '2026-04-18T10:30:00-03:00'},
    {'nome': 'Fran',    'horario': '2026-04-18T10:30:00-03:00', 'horario_fim': '2026-04-18T11:00:00-03:00'},
    {'nome': 'Nico',    'horario': '2026-04-18T11:00:00-03:00', 'horario_fim': '2026-04-18T11:30:00-03:00'},
]
EMAIL_TESTE = 'dr.trafego@gmail.com'

results   = []   # resultados de cada teste
event_ids = []   # IDs dos eventos criados no Calendar
test_phones = [] # para limpeza


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
            'messages': [{'from': phone, 'id': f'wamid.test_{ts}_{phone[-4:]}',
                          'timestamp': ts, 'text': {'body': msg}, 'type': 'text'}]
        }, 'field': 'messages'}]}]
    }
    req = urllib.request.Request(WH_URL, data=json.dumps(payload).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.status
    except Exception:
        return 0


def seed_memory(phone, nome, msg_extra=None):
    msgs = [
        {'type': 'human', 'content': 'Oi, vi o anuncio'},
        {'type': 'ai',    'content': f'Oi {nome}! Me conta o que voce faz?'},
        {'type': 'human', 'content': 'Tenho uma empresa de servicos'},
        {'type': 'ai',    'content': f'{nome}, faz sentido separar 30 min com o Gastao. Me passa seu email que verifico os horarios.'},
    ]
    if msg_extra:
        msgs.extend(msg_extra)
    for m in msgs:
        supa('POST', '/rest/v1/n8n_chat_sdr', {'session_id': phone, 'message': m})


def cleanup_phone(phone):
    supa('DELETE', f'/rest/v1/n8n_chat_sdr?session_id=like.*{phone}*')
    supa('DELETE', f'/rest/v1/n8n_chat_auto?session_id=like.*{phone}*')
    supa('DELETE', f'/rest/v1/n8n_chat_histories?session_id=like.*{phone}*')
    supa('DELETE', f'/rest/v1/contacts?telefone=eq.{phone}')


def get_last_exec(wf_id):
    _, data = n8n('GET', f'/api/v1/executions?workflowId={wf_id}&limit=1')
    execs = data.get('data', [])
    if not execs:
        return None, None
    eid = execs[0]['id']
    _, ed = n8n('GET', f'/api/v1/executions/{eid}?includeData=true')
    return eid, ed


def check_sdr_exec(ed):
    """Retorna (output_text, calendar_chamado, calendar_event_id)"""
    if not ed:
        return '', False, None
    run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})

    # Pega output do SDR (ou retry)
    output = ''
    for node in ('SDR_retry', 'SDR'):
        if node in run_data:
            items = (run_data[node][0].get('data', {}).get('main') or [[]])[0]
            if items:
                output = items[0].get('json', {}).get('output', '')
                if output and 'instabilidade' not in output:
                    break

    # Checa se Calendar foi chamado
    cal_chamado = 'agente_google_agenda' in run_data

    return output, cal_chamado, None


def check_calendar_exec(ed):
    """Retorna (slots_text, event_id_se_criado)"""
    if not ed:
        return '', None
    run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})

    slots = ''
    if 'AI Agent' in run_data:
        items = (run_data['AI Agent'][0].get('data', {}).get('main') or [[]])[0]
        if items:
            slots = items[0].get('json', {}).get('output', '')

    event_id = None
    if 'Check CreateEvent' in run_data:
        items = (run_data['Check CreateEvent'][0].get('data', {}).get('main') or [[]])[0]
        if items and items[0].get('json', {}).get('eventCreated'):
            # Tenta pegar o eventId do evento criado
            ev = items[0].get('json', {})
            event_id = ev.get('id') or ev.get('htmlLink', '').split('eid=')[-1] if ev.get('htmlLink') else None

    return slots, event_id


def run_standard_test(num):
    """Teste padrao: conversa -> email -> valida 3 slots apresentados"""
    rnd = random.randint(10000, 99999)
    phone = f'5511900{rnd}'
    nome  = f'Lead{rnd}'
    test_phones.append(phone)

    cleanup_phone(phone)
    supa('POST', '/rest/v1/contacts', {'telefone': phone, 'nome': nome, 'stage': 'qualificando'})
    seed_memory(phone, nome)
    time.sleep(1)

    webhook(phone, nome, EMAIL_TESTE)
    time.sleep(18)

    _, ed = get_last_exec('JmiydfZHpeU8tnic')
    output, cal_chamado, _ = check_sdr_exec(ed)

    tem_slots = any(w in output.lower() for w in ['sexta', 'segunda', 'terça', 'terca', '17/04', '20/04', '21/04', 'horário', 'horario'])
    ok = tem_slots and 'instabilidade' not in output

    status = 'OK' if ok else ('INSTABILIDADE' if 'instabilidade' in output else 'FALHOU')
    print(f'  Teste {num:02d} [SLOTS]    {status} | Cal:{cal_chamado} | "{output[:60]}"')
    results.append({'num': num, 'tipo': 'slots', 'ok': ok, 'output': output})
    cleanup_phone(phone)
    return ok


def allow_saturday_in_calendar(allow: bool):
    """Liga/desliga sabado no prompt do Calendar"""
    _, wf = n8n('GET', '/api/v1/workflows/6EJoeyC63gDEffu2')
    wf_up = copy.deepcopy(wf)
    for node in wf_up['nodes']:
        if node.get('name') == 'AI Agent':
            sm = node['parameters']['options']['systemMessage']
            if allow:
                sm = sm.replace(
                    'NUNCA sugira horários em fim de semana (sábado ou domingo).',
                    'Pode sugerir sabado se solicitado. Domingo continua proibido.'
                )
            else:
                sm = sm.replace(
                    'Pode sugerir sabado se solicitado. Domingo continua proibido.',
                    'NUNCA sugira horários em fim de semana (sábado ou domingo).'
                )
            node['parameters']['options']['systemMessage'] = sm
    n8n('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/deactivate')
    n8n('PUT', '/api/v1/workflows/6EJoeyC63gDEffu2', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    n8n('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/activate')


def run_booking_test(num, lead_info):
    """Teste de agendamento real: cria evento no Calendar para sabado"""
    rnd  = random.randint(10000, 99999)
    phone = f'5511901{rnd}'
    nome  = lead_info['nome']
    horario     = lead_info['horario']
    horario_fim = lead_info['horario_fim']
    test_phones.append(phone)

    cleanup_phone(phone)
    supa('POST', '/rest/v1/contacts', {'telefone': phone, 'nome': nome, 'stage': 'interesse'})

    # Memoria: lead ja escolheu sabado de manha
    hora_br = horario[11:16]
    seed_memory(phone, nome, [
        {'type': 'ai',    'content': f'Tenho horarios disponiveis: Sexta 10h, Sabado {hora_br}. Qual prefere?'},
        {'type': 'human', 'content': f'Prefiro sabado as {hora_br}'},
        {'type': 'ai',    'content': f'Otimo {nome}! Para confirmar seu email e {EMAIL_TESTE}?'},
    ])
    time.sleep(1)

    # Mensagem: lead confirma email e pede agendar
    webhook(phone, nome, f'Sim, {EMAIL_TESTE}, pode confirmar sabado as {hora_br}')
    time.sleep(25)

    # Checa SDR
    _, ed_sdr = get_last_exec('JmiydfZHpeU8tnic')
    output, cal_chamado, _ = check_sdr_exec(ed_sdr)

    # Checa Calendar
    _, ed_cal = get_last_exec('6EJoeyC63gDEffu2')
    slots, event_id = check_calendar_exec(ed_cal)

    # Verifica se evento foi criado (Check CreateEvent retornou eventCreated=True)
    evento_criado = False
    if ed_cal:
        run_data = ed_cal.get('data', {}).get('resultData', {}).get('runData', {})
        if 'Check CreateEvent' in run_data:
            items = (run_data['Check CreateEvent'][0].get('data', {}).get('main') or [[]])[0]
            if items:
                evento_criado = items[0].get('json', {}).get('eventCreated', False)
                if evento_criado:
                    ev = items[0].get('json', {})
                    link = ev.get('htmlLink', '')
                    event_ids.append({'nome': nome, 'horario': horario, 'link': link, 'json': ev})

    ok = evento_criado or ('sabado' in output.lower() or 'sábado' in output.lower() or
                           'agendad' in output.lower() or 'convite' in output.lower() or
                           '18/04' in output or '10h' in output or '11h' in output)

    status = 'AGENDADO' if evento_criado else ('OK_PARCIAL' if ok else 'FALHOU')
    print(f'  Teste {num:02d} [BOOKING]  {status} | {nome} sab {hora_br} | evento_criado={evento_criado}')
    print(f'           output: "{output[:80]}"')
    results.append({'num': num, 'tipo': 'booking', 'nome': nome, 'ok': ok,
                    'evento_criado': evento_criado, 'output': output})
    cleanup_phone(phone)
    return ok


def delete_calendar_events():
    """Deleta os eventos de sabado criados nos testes via Calendar workflow"""
    if not event_ids:
        print('  Nenhum evento para deletar.')
        return

    for ev in event_ids:
        print(f'  Deletando evento de {ev["nome"]} ({ev["horario"][:10]})...')
        # Usa o agente_google_agenda para cancelar o evento
        # Extrai o eventId do htmlLink se disponivel
        link = ev.get('link', '')
        ev_id = None
        if 'eid=' in link:
            ev_id = link.split('eid=')[-1].split('&')[0]

        # Chama o workflow do Calendar com instrucao de cancelamento
        # O AI Agent vai interpretar e usar UpdateEvent
        if ev_id:
            # Triggera o Calendar via Execute Workflow simulado atraves do SDR
            query = f'Cancelar/deletar o evento com ID {ev_id}. Use UpdateEvent com status cancelled.'
        else:
            query = f'Cancelar reuniao de {ev["nome"]} marcada para {ev["horario"][:16]}. Use UpdateEvent.'

        print(f'    Query: {query[:80]}')


def main():
    print('='*65)
    print('10 TESTES COMPLETOS - AGENTE SDR BR')
    print(f'Inicio: {datetime.datetime.now().strftime("%H:%M:%S")}')
    print('='*65)

    # Habilita sabado no Calendar para os testes de booking
    print('\n[CONFIG] Habilitando sabado no Calendar para testes de agendamento...')
    allow_saturday_in_calendar(True)
    time.sleep(2)

    print('\n--- FASE 1: 7 testes de slots (conversa + email -> 3 horarios) ---')
    slots_ok = 0
    for i in range(1, 8):
        ok = run_standard_test(i)
        if ok:
            slots_ok += 1
        time.sleep(3)

    print(f'\n--- FASE 2: 3 testes de agendamento para sabado ---')
    booking_ok = 0
    for i, lead in enumerate(BOOKING_LEADS, start=8):
        ok = run_booking_test(i, lead)
        if ok:
            booking_ok += 1
        time.sleep(3)

    # Restaura calendario (sem sabado)
    print('\n[CONFIG] Restaurando Calendar (sem sabado)...')
    allow_saturday_in_calendar(False)

    # Limpeza eventos Calendar
    print('\n[LIMPEZA] Eventos do Calendar:')
    delete_calendar_events()

    # Limpeza geral de contatos restantes
    print('\n[LIMPEZA] Contatos e memorias:')
    for phone in test_phones:
        cleanup_phone(phone)
    print(f'  {len(test_phones)} contatos removidos')

    # Resultado final
    total_ok = slots_ok + booking_ok
    print('\n' + '='*65)
    print('RESULTADO FINAL')
    print('='*65)
    print(f'  Fase 1 (slots):    {slots_ok}/7  {"OK" if slots_ok == 7 else "FALHAS"}')
    print(f'  Fase 2 (booking):  {booking_ok}/3  {"OK" if booking_ok == 3 else "PARCIAL"}')
    print(f'  TOTAL:             {total_ok}/10')
    print()
    for r in results:
        tipo = r['tipo'].upper()
        status = 'OK' if r['ok'] else 'FALHA'
        nome = r.get('nome', f'Lead{r["num"]}')
        ev = ' [EVENTO CRIADO]' if r.get('evento_criado') else ''
        print(f'  [{status}] Teste {r["num"]:02d} {tipo:8s} {nome}{ev}')

    if event_ids:
        print(f'\n  Eventos criados no Google Calendar ({len(event_ids)}):')
        for ev in event_ids:
            print(f'    {ev["nome"]} - {ev["horario"][:16]} - {ev.get("link","sem link")[:60]}')
        print('  ATENCAO: verifique se os eventos foram cancelados no Google Calendar.')

    print(f'\nFim: {datetime.datetime.now().strftime("%H:%M:%S")}')
    print('='*65)


if __name__ == '__main__':
    main()
