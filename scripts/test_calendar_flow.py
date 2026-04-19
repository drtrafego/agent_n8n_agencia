"""
Testa o fluxo completo do Calendar:
1. Cria contato de teste
2. Semeia memoria de chat ate o ponto onde o lead deu o email
3. Dispara mensagem via webhook do SDR
4. Aguarda execucao e verifica se Calendar foi chamado e retornou horarios
5. Limpa tudo ao final
"""
import urllib.request, json, ssl, sys, io, time, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

N8N_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
N8N_BASE = 'https://n8n.casaldotrafego.com'
WH_URL = 'https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103'

SUPABASE_URL = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'

import random
_RND = random.randint(1000, 9999)
TEST_PHONE = f'5511900{_RND}'   # numero unico por rodada
TEST_NAME  = f'Lead Teste {_RND}'
TEST_EMAIL = 'dr.trafego@gmail.com'


def n8n(method, path, body=None):
    url = f'{N8N_BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', N8N_KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def supa(method, path, body=None):
    url = f'{SUPABASE_URL}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('apikey', SUPABASE_KEY)
    req.add_header('Authorization', f'Bearer {SUPABASE_KEY}')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Prefer', 'return=representation')
    with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
        txt = r.read()
        return r.status, json.loads(txt) if txt else None


def post_webhook(msg_text):
    ts = str(int(time.time()))
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"display_phone_number": "15550000001", "phone_number_id": "115216611574100"},
                    "contacts": [{"profile": {"name": TEST_NAME}, "wa_id": TEST_PHONE}],
                    "messages": [{
                        "from": TEST_PHONE,
                        "id": f"wamid.test_{ts}",
                        "timestamp": ts,
                        "text": {"body": msg_text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }
    req = urllib.request.Request(WH_URL, data=json.dumps(payload).encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
            return r.status, r.read().decode()[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def cleanup():
    print('\n--- LIMPEZA ---')
    # Remove contato
    supa('DELETE', f'/rest/v1/contacts?telefone=eq.{TEST_PHONE}')
    # Remove memoria
    supa('DELETE', f'/rest/v1/n8n_chat_sdr?session_id=like.%25{TEST_PHONE}%25')
    supa('DELETE', f'/rest/v1/n8n_chat_auto?session_id=like.%25{TEST_PHONE}%25')
    supa('DELETE', f'/rest/v1/n8n_chat_histories?session_id=like.%25{TEST_PHONE}%25')
    print('  Contato e memorias removidos')


def get_last_sdrbr_exec():
    _, data = n8n('GET', '/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=1')
    execs = data.get('data', [])
    if not execs:
        return None
    eid = execs[0]['id']
    _, ed = n8n('GET', f'/api/v1/executions/{eid}?includeData=true')
    return eid, ed


def get_last_cal_exec():
    _, data = n8n('GET', '/api/v1/executions?workflowId=6EJoeyC63gDEffu2&limit=1')
    execs = data.get('data', [])
    if not execs:
        return None
    eid = execs[0]['id']
    _, ed = n8n('GET', f'/api/v1/executions/{eid}?includeData=true')
    return eid, ed


def print_exec(eid, ed, label=''):
    run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
    status = ed.get('status')
    print(f'  {label} [{eid}] {status}')
    for node, runs in run_data.items():
        for run in runs:
            items = (run.get('data', {}).get('main') or [[]])[0]
            err = run.get('error')
            if err:
                print(f'    [ERRO] {node}: {json.dumps(err, ensure_ascii=False)[:200]}')
            elif items:
                out = str(items[0].get('json', {}))[:120]
                print(f'    [ok]   {node} ({len(items)}) {out}')


def main():
    print('='*60)
    print('TESTE COMPLETO DO CALENDAR FLOW')
    print('='*60)

    # 1. Garante contato limpo
    cleanup()
    time.sleep(1)

    # 2. Cria contato manualmente com stage qualificando
    s, resp = supa('POST', '/rest/v1/contacts', {
        'telefone': TEST_PHONE,
        'nome': TEST_NAME,
        'stage': 'qualificando',
        'nicho': 'agencia de trafego',
    })
    print(f'\n[1] Contato criado: {s}')

    # 3. Semeia memoria: conversa chegou ao ponto de proposta de call
    MESSAGES = [
        {'type': 'human', 'content': 'Oi, vi o anuncio'},
        {'type': 'ai', 'content': f'Oi {TEST_NAME}! Me conta o que voce faz?'},
        {'type': 'human', 'content': 'Tenho uma agencia de trafego pago'},
        {'type': 'ai', 'content': 'Agencias de trafego costumam perder leads quentes quando o time demora a responder. Voce sente isso? Faz sentido separar 30 min com o Gastao para mostrar como um agente de IA resolve isso. Me passa seu email que ja verifico os horarios.'},
    ]
    session_id = TEST_PHONE
    for msg in MESSAGES:
        supa('POST', '/rest/v1/n8n_chat_sdr', {
            'session_id': session_id,
            'message': msg
        })
    print(f'[2] Memoria semeada ({len(MESSAGES)} msgs)')

    # 4. Dispara mensagem com o email (proximo passo natural)
    print(f'\n[3] Disparando mensagem com email: "{TEST_EMAIL}"')
    s, r = post_webhook(TEST_EMAIL)
    print(f'  Webhook: {s} {r[:100]}')

    # 5. Aguarda processamento
    print('\n[4] Aguardando 20s para processamento...')
    time.sleep(20)

    # 6. Verifica exec SDR
    print('\n[5] SDR BR:')
    result = get_last_sdrbr_exec()
    if result:
        eid, ed = result
        print_exec(eid, ed, 'SDR')
        # Checa se calendar foi chamado
        run_data = ed.get('data', {}).get('resultData', {}).get('runData', {})
        cal_called = 'agente_google_agenda' in run_data
        cal_ok = False
        if cal_called:
            for run in run_data.get('agente_google_agenda', []):
                err = run.get('error')
                if not err:
                    cal_ok = True
        print(f'\n  Calendar chamado: {cal_called}')
        print(f'  Calendar sem erro: {cal_ok}')

    # 7. Verifica exec Calendar
    print('\n[6] Calendar (ultima exec):')
    result_cal = get_last_cal_exec()
    if result_cal:
        eid_cal, ed_cal = result_cal
        print_exec(eid_cal, ed_cal, 'Calendar')
        # Checa se ReturnToSDR rodou
        run_data_cal = ed_cal.get('data', {}).get('resultData', {}).get('runData', {})
        has_return = 'ReturnToSDR' in run_data_cal
        agent_output = ''
        if 'AI Agent' in run_data_cal:
            items = (run_data_cal['AI Agent'][0].get('data', {}).get('main') or [[]])[0]
            if items:
                agent_output = items[0].get('json', {}).get('output', '')
        print(f'\n  ReturnToSDR executou: {has_return}')
        print(f'  AI Agent output: {agent_output[:200]}')

    # 8. Verifica mensagem enviada ao lead
    print('\n[7] Ultima mensagem outbound enviada:')
    s, msgs = supa('GET', f'/rest/v1/wa_messages?direction=eq.outbound&order=created_at.desc&limit=3')
    if msgs:
        for m in msgs:
            print(f'  [{m["created_at"][:19]}] {m["body"][:150]}')

    # 9. Limpeza
    cleanup()

    print('\n' + '='*60)
    print('TESTE CONCLUIDO')
    print('='*60)


if __name__ == '__main__':
    main()
