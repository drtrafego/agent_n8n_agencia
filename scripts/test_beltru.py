# -*- coding: utf-8 -*-
import urllib.request, json, ssl, time, hashlib, hmac

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
APP_SECRET = "994ad53d1a0e894e01bef243a88dfde6"
WEBHOOK_URL = "https://agente.casaldotrafego.com/api/whatsapp/webhook"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}

PHONE = "5511999990099"
NAME = "Beltru Teste"

MSGS = [
    "Oi vi o anuncio do agente de IA",
    "Tenho uma clinica veterinaria",
    "Meu problema eh que muitos clientes ligam pra marcar consulta e a gente nao consegue atender todos",
]

def send_webhook(phone, name, text):
    ts = str(int(time.time()))
    payload = {"object": "whatsapp_business_account", "entry": [{"id": "106071169159774", "changes": [{"value": {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "5511996681596", "phone_number_id": "115216611574100"},
        "contacts": [{"profile": {"name": name}, "wa_id": phone}],
        "messages": [{"from": phone, "id": "wamid." + ts + phone[-4:], "timestamp": ts,
                       "text": {"body": text}, "type": "text"}]
    }, "field": "messages"}]}]}
    body = json.dumps(payload).encode()
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), body, hashlib.sha256).hexdigest()
    req = urllib.request.Request(WEBHOOK_URL, data=body, method="POST",
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)

def wait_n8n_exec(min_id, timeout=120):
    for _ in range(timeout // 5):
        time.sleep(5)
        url = "https://n8n.casaldotrafego.com/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=1"
        req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        if data.get("data"):
            ex = data["data"][0]
            if int(ex["id"]) > min_id and ex.get("status") in ["success", "error"]:
                return ex
    return None

def get_bot_reply(phone):
    url = SUPABASE_URL + "/rest/v1/n8n_chat_histories?session_id=eq." + phone + "&order=created_at.desc&limit=3"
    req = urllib.request.Request(url, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        rows = json.loads(resp.read().decode())
        for r in rows:
            m = r.get("message", {})
            if isinstance(m, str):
                try:
                    m = json.loads(m)
                except:
                    continue
            if isinstance(m, dict) and m.get("type") == "ai":
                c = m.get("content", "")
                if c and c.strip().upper() != "STOP":
                    return c
    except:
        pass
    return None

# Get baseline exec ID
url = "https://n8n.casaldotrafego.com/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=1"
req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
resp = urllib.request.urlopen(req, context=ctx)
last_id = int(json.loads(resp.read().decode()).get("data", [{}])[0].get("id", 0))

print("=" * 60)
print("  TESTE COMPLETO: %s (%s)" % (NAME, PHONE))
print("  Fluxo: Next.js webhook -> n8n -> AI -> bot-send -> inbox")
print("=" * 60)

for i, msg in enumerate(MSGS):
    print("")
    print("  MSG %d/3: \"%s\"" % (i + 1, msg))

    code = send_webhook(PHONE, NAME, msg)
    print("  Webhook: %s" % code)

    if code != 200:
        print("  ERRO no webhook!")
        continue

    print("  Aguardando n8n...", end=" ")
    import sys
    sys.stdout.flush()
    ex = wait_n8n_exec(last_id, timeout=120)

    if ex:
        last_id = int(ex["id"])
        status = ex.get("status")
        print("%s (#%s)" % (status, ex["id"]))

        if status == "success":
            time.sleep(2)
            reply = get_bot_reply(PHONE)
            if reply:
                for line in reply.strip().split("\n")[:4]:
                    print("  BOT: %s" % line[:120])
            else:
                print("  BOT: (sem resposta no DB)")
        else:
            print("  ERRO na execucao")
    else:
        print("TIMEOUT")

    time.sleep(5)

# Verificar dados no inbox
print("")
print("=" * 60)
print("  VERIFICANDO DADOS NO SISTEMA")
print("=" * 60)

# contacts (CRM)
url = SUPABASE_URL + "/rest/v1/contacts?telefone=eq." + PHONE + "&select=id,nome,telefone,stage,observacoes_sdr,followup_count"
req = urllib.request.Request(url, headers=SB_H)
resp = urllib.request.urlopen(req, context=ctx)
contacts = json.loads(resp.read().decode())
if contacts:
    c = contacts[0]
    print("  CRM: nome=%s, stage=%s, followups=%s" % (c.get("nome"), c.get("stage"), c.get("followup_count")))
    obs = (c.get("observacoes_sdr") or "")[:200]
    if obs:
        print("  SDR: %s" % obs)
else:
    print("  CRM: NAO ENCONTRADO")

# wa_contacts
url2 = SUPABASE_URL + "/rest/v1/wa_contacts?wa_id=eq." + PHONE + "&select=id,name,wa_id"
req2 = urllib.request.Request(url2, headers=SB_H)
resp2 = urllib.request.urlopen(req2, context=ctx)
wa_c = json.loads(resp2.read().decode())
if wa_c:
    contact_id = wa_c[0]["id"]
    print("  wa_contacts: OK (name=%s)" % wa_c[0].get("name"))

    # wa_conversations
    url3 = SUPABASE_URL + "/rest/v1/wa_conversations?contact_id=eq." + contact_id + "&select=id,status,bot_active,last_message,last_message_at,unread_count"
    req3 = urllib.request.Request(url3, headers=SB_H)
    resp3 = urllib.request.urlopen(req3, context=ctx)
    convs = json.loads(resp3.read().decode())
    if convs:
        cv = convs[0]
        print("  wa_conversations: status=%s, bot=%s, unread=%s" % (cv.get("status"), cv.get("bot_active"), cv.get("unread_count")))
        print("  last_msg: %s" % (cv.get("last_message") or "")[:100])

        # wa_messages
        url4 = SUPABASE_URL + "/rest/v1/wa_messages?conversation_id=eq." + cv["id"] + "&select=direction,body,sent_by,created_at&order=created_at.asc"
        req4 = urllib.request.Request(url4, headers=SB_H)
        resp4 = urllib.request.urlopen(req4, context=ctx)
        msgs = json.loads(resp4.read().decode())
        inb = sum(1 for m in msgs if m.get("direction") == "inbound")
        outb = sum(1 for m in msgs if m.get("direction") == "outbound")
        print("  wa_messages: %d total (%d in, %d out)" % (len(msgs), inb, outb))
        for m in msgs:
            arrow = ">>>" if m.get("direction") == "outbound" else "<<<"
            sent = m.get("sent_by", "?")
            body = (m.get("body") or "")[:90]
            print("    %s [%s] %s" % (arrow, sent, body))
    else:
        print("  wa_conversations: NAO ENCONTRADA")
else:
    print("  wa_contacts: NAO ENCONTRADO")

print("")
print("=" * 60)
print("  TESTE CONCLUIDO")
print("=" * 60)
