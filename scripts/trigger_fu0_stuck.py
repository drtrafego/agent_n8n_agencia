"""
Dispara FU0 manual para leads presos em qualificando com followup_count=0
onde o bot foi o último a falar (last_bot_msg_at > last_lead_msg_at).
"""
import urllib.request, json, ssl, sys, time
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()

SUPABASE_URL = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'
BOT_SEND_URL = 'https://agente.casaldotrafego.com/api/whatsapp/bot-send'
BOT_SEND_TOKEN = '4e777faca88fdd617926355a55b03733c65e2b9700ee33f8a619b09e5ccdb470'

def supabase_sql(query):
    body = json.dumps({'query': query}).encode()
    req = urllib.request.Request(
        SUPABASE_URL + '/rest/v1/rpc/exec_sql',
        data=body, method='POST',
        headers={'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY,
                 'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            return json.loads(r.read())
    except:
        return None

def supabase_patch(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        SUPABASE_URL + path, data=body, method='PATCH',
        headers={'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY,
                 'Content-Type': 'application/json', 'Prefer': 'return=minimal'}
    )
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.status

def bot_send(phone, message):
    body = json.dumps({'phone': phone, 'body': message}).encode()
    req = urllib.request.Request(BOT_SEND_URL, data=body, method='POST',
        headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + BOT_SEND_TOKEN})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.status

# Leads presos: qualificando, FU0, bot foi o último a falar
leads = [
    {'id': 1946, 'nome': 'Maria das Graças', 'phone': '5524999460330', 'nicho': ''},
    {'id': 1722, 'nome': 'Benedito',          'phone': '553491294870',  'nicho': ''},
    {'id': 1712, 'nome': 'Moyses',            'phone': '554188698945',  'nicho': ''},
    {'id': 1661, 'nome': 'Luiz',              'phone': '5521966799115', 'nicho': ''},
    {'id': 1658, 'nome': 'Gilvando',          'phone': '556692777781',  'nicho': ''},
    {'id': 1523, 'nome': 'Carlos',            'phone': '5524981510824', 'nicho': ''},
    {'id': 1500, 'nome': 'Ana Clara',         'phone': '553788079924',  'nicho': ''},
]

def get_first_name(nome):
    return nome.strip().split()[0] if nome.strip() else 'Olá'

def fu0_message(nome):
    n = get_first_name(nome)
    return f'{n}, tudo bem? Só queria saber se ficou alguma dúvida sobre o que conversamos.'

print(f'Disparando FU0 para {len(leads)} leads presos...')
ok = errors = 0

for lead in leads:
    nome = lead['nome']
    phone = lead['phone']
    contact_id = lead['id']
    msg = fu0_message(nome)

    try:
        status = bot_send(phone, msg)
        if status == 200:
            # Incrementar followup_count e atualizar last_bot_msg_at
            supabase_patch(
                f'/rest/v1/contacts?id=eq.{contact_id}',
                {'followup_count': 1, 'last_bot_msg_at': 'NOW()'}
            )
            print(f'  OK [{phone[-4:]}] {nome}: FU0 enviado')
            ok += 1
        else:
            print(f'  ERRO [{phone[-4:]}] {nome}: bot-send retornou {status}')
            errors += 1
    except Exception as e:
        print(f'  ERRO [{phone[-4:]}] {nome}: {e}')
        errors += 1

    time.sleep(2)

print()
print(f'Concluido: {ok} enviados, {errors} erros')
