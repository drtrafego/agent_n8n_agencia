import urllib.request, json, ssl, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

WEBHOOK_URL = "https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_HEADERS = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=representation"}


def clean_db():
    """Clean all test data"""
    for table in ["n8n_chat_histories", "contacts"]:
        url = f"{SUPABASE_URL}/rest/v1/{table}?id=gt.0"
        req = urllib.request.Request(url, method='DELETE', headers=SB_HEADERS)
        try:
            urllib.request.urlopen(req, context=ctx)
        except:
            pass
    print("[DB] Limpo\n")


def send_msg(phone, name, text):
    """Send simulated webhook message"""
    ts = str(int(time.time()))
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "106071169159774", "changes": [{"value": {
            "messaging_product": "whatsapp",
            "metadata": {"display_phone_number": "5511996681596", "phone_number_id": "115216611574100"},
            "contacts": [{"profile": {"name": name}, "wa_id": phone}],
            "messages": [{"from": phone, "id": f"wamid.{ts}{phone[-4:]}", "timestamp": ts,
                          "text": {"body": text}, "type": "text"}]
        }, "field": "messages"}]}]
    }
    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(WEBHOOK_URL, data=body, method='POST',
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        return True
    except:
        return False


def wait_for_response(phone, prev_ai_count, max_wait=120):
    """Wait for a new AI response in chat history"""
    waited = 0
    while waited < max_wait:
        time.sleep(5)
        waited += 5
        url = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&order=created_at.desc&limit=10"
        req = urllib.request.Request(url, headers={
            "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"
        })
        try:
            resp = urllib.request.urlopen(req, context=ctx)
            data = json.loads(resp.read().decode())
            ai_msgs = []
            for e in data:
                m = e.get('message', {})
                if isinstance(m, str):
                    m = json.loads(m)
                if m.get('type') == 'ai':
                    content = m.get('content', '')
                    if content and content.strip() and content.strip().upper() != 'STOP':
                        ai_msgs.append(content)
            if len(ai_msgs) > prev_ai_count:
                return ai_msgs[0]  # latest
        except:
            pass
    return None


def count_ai_msgs(phone):
    url = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&order=created_at.desc&limit=50"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        count = 0
        for e in data:
            m = e.get('message', {})
            if isinstance(m, str):
                m = json.loads(m)
            if m.get('type') == 'ai':
                content = m.get('content', '')
                if content and content.strip() and content.strip().upper() != 'STOP':
                    count += 1
        return count
    except:
        return 0


def get_contact(phone):
    url = f"{SUPABASE_URL}/rest/v1/contacts?telefone=eq.{phone}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        return data[0] if data else None
    except:
        return None


def run_test(name, phone, messages):
    print(f"\n{'='*60}")
    print(f"  TESTE: {name} ({phone})")
    print(f"{'='*60}\n")

    step = 0
    for msg in messages:
        step += 1
        prev = count_ai_msgs(phone)
        print(f"  [{name}] -> {msg}")
        ok = send_msg(phone, name, msg)
        if not ok:
            print(f"  [ERRO ao enviar]")
            continue

        response = wait_for_response(phone, prev, max_wait=120)
        if response:
            display = response[:250] + "..." if len(response) > 250 else response
            print(f"  [BOT]  <- {display}")
        else:
            print(f"  [BOT]  <- (sem resposta)")
        print()

        # Small delay between turns
        time.sleep(3)

    # Final check
    contact = get_contact(phone)
    print(f"  --- Resultado ---")
    if contact:
        print(f"  Nome DB: {contact.get('nome', 'N/A')}")
        obs = contact.get('observacoes_sdr', '') or ''
        print(f"  Observacoes: {obs[:300]}")
    print()


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("Limpando banco...")
    clean_db()
    time.sleep(2)

    # TESTE 1: Nico - Clinica odontologica
    run_test("Nico", "5511999990001", [
        "Oi",
        "Tenho uma clinica odontologica",
        "O pessoal da recepcao nao da conta de responder whatsapp",
        "Quarta de manha funciona pra mim",
        "nico.teste@gmail.com",
        "1",
    ])

    # TESTE 2: Beltru - Imobiliaria
    run_test("Beltru", "5511999990002", [
        "Bom dia, vi o anuncio de voces",
        "Imobiliaria com 15 corretores",
        "Os leads do facebook demoram demais pra receber resposta e esfriam",
        "Pode ser quinta a tarde",
        "beltru.teste@gmail.com",
        "2",
    ])

    # TESTE 3: Fran - Ecommerce
    run_test("Fran", "5511999990003", [
        "ola vi o anuncio sobre IA",
        "Loja online de roupas femininas",
        "Muito carrinho abandonado e a galera pergunta no whats e some",
        "Bora, sexta de manha",
        "fran.teste@gmail.com",
        "1",
    ])

    print("\n" + "="*60)
    print("  TODOS OS TESTES FINALIZADOS")
    print("="*60)
