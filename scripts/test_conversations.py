import urllib.request, json, ssl, time, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

WEBHOOK_URL = "https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"

LEADS = [
    {
        "name": "Nico",
        "phone": "5511999990001",
        "nicho": "clinica",
        "messages": [
            "Oi",
            None,  # wait for AI response, then reply based on context
            "Tenho uma clinica odontologica, atendo uns 30 pacientes por dia",
            None,
            "Sim, o pessoal da recepção não da conta de responder todo mundo",
            None,
            "Quarta de manhã funciona",
            None,
            "nico.teste@gmail.com",
            None,
            "1",  # choose first time slot
            None,
        ]
    },
    {
        "name": "Beltru",
        "phone": "5511999990002",
        "nicho": "imobiliaria",
        "messages": [
            "Bom dia",
            None,
            "Imobiliária, temos uns 15 corretores",
            None,
            "O problema é que os leads do facebook demoram demais pra receber resposta",
            None,
            "Pode ser amanhã à tarde",
            None,
            "beltru.teste@gmail.com",
            None,
            "2",
            None,
        ]
    },
    {
        "name": "Fran",
        "phone": "5511999990003",
        "nicho": "ecommerce",
        "messages": [
            "ola, vi o anuncio de vcs",
            None,
            "Loja online de roupas femininas",
            None,
            "Muito carrinho abandonado, a galera pergunta no whats e some",
            None,
            "Bora, quinta de manhã",
            None,
            "fran.teste@gmail.com",
            None,
            "1",
            None,
        ]
    }
]


def send_message(phone, name, text):
    """Send a simulated Meta WABA webhook message"""
    timestamp = str(int(time.time()))
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "106071169159774",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5511996681596",
                        "phone_number_id": "115216611574100"
                    },
                    "contacts": [{
                        "profile": {"name": name},
                        "wa_id": phone
                    }],
                    "messages": [{
                        "from": phone,
                        "id": "wamid.TEST" + timestamp + phone[-4:],
                        "timestamp": timestamp,
                        "text": {"body": text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    body = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(WEBHOOK_URL, data=body, method='POST', headers={
        "Content-Type": "application/json"
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        return resp.getcode()
    except Exception as e:
        return str(e)


def get_last_ai_response(phone, after_count=0):
    """Get the latest AI response from chat history"""
    url = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&order=created_at.desc&limit=5"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        # Find latest AI message
        for entry in data:
            msg = entry.get('message', {})
            if isinstance(msg, str):
                msg = json.loads(msg)
            if msg.get('type') == 'ai' or msg.get('role') == 'assistant':
                content = msg.get('content', msg.get('text', ''))
                if content and content != 'STOP':
                    return content
        return None
    except Exception as e:
        return f"ERROR: {e}"


def get_chat_count(phone):
    """Get total chat messages for a phone"""
    url = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&select=id"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "count=exact"
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        return len(data)
    except:
        return 0


def run_conversation(lead):
    name = lead["name"]
    phone = lead["phone"]
    print(f"\n{'='*60}")
    print(f"  TESTE: {name} ({phone}) - Nicho: {lead['nicho']}")
    print(f"{'='*60}\n")

    step = 0
    for i, msg in enumerate(lead["messages"]):
        if msg is None:
            # Wait for AI response
            print(f"  [Aguardando resposta do bot...]")
            max_wait = 90
            waited = 0
            prev_count = get_chat_count(phone)
            ai_response = None

            while waited < max_wait:
                time.sleep(5)
                waited += 5
                new_count = get_chat_count(phone)
                if new_count > prev_count:
                    time.sleep(3)  # extra wait for processing
                    ai_response = get_last_ai_response(phone)
                    break

            if ai_response:
                # Truncate for display
                display = ai_response[:300] + "..." if len(ai_response) > 300 else ai_response
                print(f"  BOT: {display}")
                print()
            else:
                print(f"  BOT: [SEM RESPOSTA apos {max_wait}s]")
                print()
                # If no response, try continuing anyway
        else:
            step += 1
            print(f"  [{name}] MSG {step}: {msg}")
            status = send_message(phone, name, msg)
            print(f"  [Enviado | Status: {status}]")
            time.sleep(2)  # small delay between send and wait

    # Final: check contact and observations
    print(f"\n  --- Resultado Final: {name} ---")
    url = f"{SUPABASE_URL}/rest/v1/contacts?telefone=eq.{phone}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        if data:
            c = data[0]
            print(f"  Nome: {c.get('nome')}")
            print(f"  Observacoes: {c.get('observacoes_sdr', 'N/A')[:200]}")
        else:
            print(f"  [Contato nao encontrado]")
    except Exception as e:
        print(f"  Erro: {e}")

    # Full chat history
    print(f"\n  --- Historico Completo: {name} ---")
    url2 = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&order=created_at.asc&limit=30"
    req2 = urllib.request.Request(url2, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    })
    try:
        resp2 = urllib.request.urlopen(req2, context=ctx)
        data2 = json.loads(resp2.read().decode())
        for entry in data2:
            msg = entry.get('message', {})
            if isinstance(msg, str):
                msg = json.loads(msg)
            role = msg.get('type', msg.get('role', '?'))
            content = msg.get('content', msg.get('text', ''))[:200]
            print(f"  [{role}] {content}")
    except Exception as e:
        print(f"  Erro: {e}")


# Run all 3 conversations sequentially
if __name__ == "__main__":
    print("=" * 60)
    print("  TESTE DE CONVERSAS - PROVA VIVA")
    print("  3 leads: Nico (clinica), Beltru (imob), Fran (ecommerce)")
    print("=" * 60)

    for lead in LEADS:
        run_conversation(lead)
        print("\n")

    print("\n=== TESTES FINALIZADOS ===")
