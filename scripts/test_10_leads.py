import urllib.request, json, ssl, time, sys, io, hashlib, hmac

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# Use Vercel webhook (real flow) so messages appear in frontend
WEBHOOK_URL = "https://agente.casaldotrafego.com/api/whatsapp/webhook"
APP_SECRET = "994ad53d1a0e894e01bef243a88dfde6"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=representation"}

LEADS = [
    # 1. Dentista formal
    {"name": "Dr. Ricardo Almeida", "phone": "5511900000001", "msgs": [
        "Boa tarde",
        "Clinica odontologica, 4 dentistas",
        "Pacientes ligam e mandam mensagem perguntando preco e nao agendam consulta",
        "Interessante. Teria quinta pela manha?",
        "ricardo.almeida@clinicasorrir.com.br",
        "1",
    ]},
    # 2. Corretora informal
    {"name": "Juliana Costa", "phone": "5511900000002", "msgs": [
        "oiii vi o anuncio 😊",
        "imobiliaria! somos 8 corretores",
        "a gente perde muito lead pq demora pra responder sabe",
        "nossa isso seria otimo! pode ser amanha de tarde?",
        "ju.costa@imobcasa.com",
        "2",
    ]},
    # 3. Dono de ecommerce direto
    {"name": "Fernando Martins", "phone": "5511900000003", "msgs": [
        "Quero saber mais sobre o agente de IA",
        "Ecommerce de eletronicos",
        "Carrinho abandonado e suporte pos venda sao os maiores problemas",
        "Pode ser sexta 10h",
        "fernando@techshop.com.br",
        "1",
    ]},
    # 4. Advogado cetico
    {"name": "Dra. Camila Souza", "phone": "5511900000004", "msgs": [
        "Boa tarde, gostaria de informacoes",
        "Escritorio de advocacia, direito trabalhista",
        "Nao sei se robo funciona pra advocacia, e muito personalizado",
        "Hmm entendi. E quanto custa isso?",
        "Faz sentido. Quarta a tarde pode ser",
        "camila@souzaadvogados.com.br",
        "1",
    ]},
    # 5. Dono de restaurante ocupado
    {"name": "Carlos Mendes", "phone": "5511900000005", "msgs": [
        "oi",
        "restaurante delivery",
        "muito pedido pelo whats e a equipe nao da conta",
        "bora quarta de manha",
        "carlos@restaurantemendes.com",
        "1",
    ]},
    # 6. Dona de academia entusiasmada
    {"name": "Patricia Lima", "phone": "5511900000006", "msgs": [
        "Oi! Vi o anuncio e achei super interessante!",
        "Academia de musculacao e crossfit",
        "A gente perde aluno porque nao responde rapido quando perguntam sobre planos e horarios",
        "Adorei! Quando posso ver funcionando?",
        "patricia@fitprime.com.br",
        "1",
    ]},
    # 7. Corretor de seguros - objecao preco
    {"name": "Marcos Oliveira", "phone": "5511900000007", "msgs": [
        "Boa tarde",
        "Corretora de seguros, atendo pessoa fisica e juridica",
        "Recebo muitas cotacoes e nao consigo responder todas a tempo",
        "Quanto custa? Ja tenho muitos gastos com a operacao",
        "Hmm faz sentido comparando assim. Pode ser quinta de manha?",
        "marcos@segurosol.com.br",
        "1",
    ]},
    # 8. Esteticista - prefere humano
    {"name": "Vanessa Rocha", "phone": "5511900000008", "msgs": [
        "oi boa tarde",
        "clinica de estetica",
        "minhas clientes gostam de atendimento humano, acho que robo nao funciona pra esse publico",
        "ah entendi, nao sabia que funcionava assim",
        "pode ser sexta a tarde?",
        "vanessa@beautyspace.com.br",
        "1",
    ]},
    # 9. Concessionaria - tecnico
    {"name": "Roberto Santos", "phone": "5511900000009", "msgs": [
        "Bom dia, quero entender como funciona a tecnologia",
        "Concessionaria de veiculos, temos 3 lojas",
        "O lead chega pelo site e pelo instagram mas a equipe de vendas so responde no horario comercial",
        "E ele consegue qualificar se o cliente quer carro novo ou usado, dar informacao de estoque?",
        "Impressionante. Teria quarta as 14h?",
        "roberto@autosantos.com.br",
        "1",
    ]},
    # 10. Contadora quer mais detalhes
    {"name": "Lucia Ferreira", "phone": "5511900000010", "msgs": [
        "Ola, vi o anuncio e quero entender melhor",
        "Escritorio de contabilidade",
        "Recebemos muitas duvidas de clientes sobre prazos de impostos, declaracao, essas coisas",
        "Como funciona na pratica? Ele responde certo mesmo?",
        "Interessante. Pode ser quinta 11h?",
        "lucia@contabilferreira.com.br",
        "1",
    ]},
]


def send_via_vercel(phone, name, text):
    ts = str(int(time.time()))
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "106071169159774", "changes": [{"value": {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "5511996681596", "phone_number_id": "115216611574100"},
        "contacts": [{"profile": {"name": name}, "wa_id": phone}],
        "messages": [{"from": phone, "id": f"wamid.{ts}{phone[-4:]}", "timestamp": ts,
                      "text": {"body": text}, "type": "text"}]
    }, "field": "messages"}]}]}
    body = json.dumps(payload)
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()
    req = urllib.request.Request(WEBHOOK_URL, data=body.encode('utf-8'), method='POST',
                                 headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        return True
    except:
        return False


def get_last_bot_response(phone, prev_count, max_wait=120):
    waited = 0
    while waited < max_wait:
        time.sleep(8)
        waited += 8
        url = f"{SUPABASE_URL}/rest/v1/wa_messages?order=created_at.desc&limit=5"
        req = urllib.request.Request(url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
        try:
            resp = urllib.request.urlopen(req, context=ctx)
            msgs = json.loads(resp.read().decode())
            # Find outbound messages for this conversation
            for m in msgs:
                if m.get('direction') == 'outbound' and m.get('sent_by') == 'bot':
                    body_text = m.get('body', '')
                    if body_text:
                        return body_text
        except:
            pass
        # Also check n8n_chat_histories as fallback
        url2 = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&order=created_at.desc&limit=3"
        req2 = urllib.request.Request(url2, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
        try:
            resp2 = urllib.request.urlopen(req2, context=ctx)
            data2 = json.loads(resp2.read().decode())
            ai_count = 0
            for e in data2:
                m = e.get('message', {})
                if isinstance(m, str): m = json.loads(m)
                if m.get('type') == 'ai':
                    content = m.get('content', '')
                    if content and content.strip().upper() != 'STOP':
                        ai_count += 1
                        if ai_count > prev_count:
                            return content
        except:
            pass
    return None


def count_ai(phone):
    url = f"{SUPABASE_URL}/rest/v1/n8n_chat_histories?session_id=eq.{phone}&order=created_at.desc&limit=50"
    req = urllib.request.Request(url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        count = 0
        for e in data:
            m = e.get('message', {})
            if isinstance(m, str): m = json.loads(m)
            if m.get('type') == 'ai':
                c = m.get('content', '')
                if c and c.strip().upper() != 'STOP':
                    count += 1
        return count
    except:
        return 0


def run_lead(idx, lead):
    name = lead["name"]
    phone = lead["phone"]
    print(f"\n{'='*55}")
    print(f"  LEAD {idx}/10: {name} ({phone})")
    print(f"{'='*55}\n")

    for msg in lead["msgs"]:
        prev = count_ai(phone)
        print(f"  [{name.split()[0]}] -> {msg}")
        ok = send_via_vercel(phone, name, msg)
        if not ok:
            print(f"           [ERRO envio]")
            continue

        resp = get_last_bot_response(phone, prev)
        if resp:
            if '<contexto' in resp:
                resp = resp.split('<contexto')[0].strip()
            display = resp[:220] + "..." if len(resp) > 220 else resp
            print(f"  [BOT]  <- {display}")
        else:
            print(f"  [BOT]  <- (sem resposta)")
        print()
        time.sleep(3)

    # Check contact
    url = f"{SUPABASE_URL}/rest/v1/contacts?telefone=eq.{phone}"
    req = urllib.request.Request(url, headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"})
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        c = json.loads(resp.read().decode())
        if c:
            print(f"  Nome: {c[0].get('nome')} | Obs: {str(c[0].get('observacoes_sdr',''))[:150]}")
    except:
        pass
    print()


if __name__ == "__main__":
    # Clean test data from n8n tables (keep wa_ tables for frontend)
    for table in ["n8n_chat_histories", "contacts"]:
        url = f"{SUPABASE_URL}/rest/v1/{table}?id=gt.0"
        req = urllib.request.Request(url, method='DELETE', headers=SB_H)
        try: urllib.request.urlopen(req, context=ctx)
        except: pass
    print("[DB] n8n tables limpos\n")

    for i, lead in enumerate(LEADS, 1):
        run_lead(i, lead)

    print("\n" + "="*55)
    print("  10 TESTES FINALIZADOS")
    print("="*55)
