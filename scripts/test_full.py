# -*- coding: utf-8 -*-
import urllib.request, json, ssl, time, sys

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

N8N_WEBHOOK = "https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}

leads = [
    {"phone": "5511988880061", "name": "TESTE_Diana", "msgs": [
        "Oi, vi o anuncio do agente de IA",
        "Tenho uma clinica odontologica",
        "Pacientes pedem orcamento pelo whatsapp e a gente demora pra responder",
    ]},
    {"phone": "5511988880062", "name": "TESTE_Eduardo", "msgs": [
        "Boa tarde, quero informacoes",
        "Sou dono de uma imobiliaria",
        "Recebemos muitos contatos e nao conseguimos atender todos rapido",
    ]},
    {"phone": "5511988880063", "name": "TESTE_Fernanda", "msgs": [
        "Ola, me interessei",
        "Trabalho com ecommerce de cosmeticos",
        "Nosso suporte no whatsapp ta sobrecarregado e perdemos vendas",
    ]},
]

def send_webhook(phone, name, text):
    ts = str(int(time.time()))
    payload = {"object":"whatsapp_business_account","entry":[{"id":"106071169159774","changes":[{"value":{
        "messaging_product":"whatsapp",
        "metadata":{"display_phone_number":"5511996681596","phone_number_id":"115216611574100"},
        "contacts":[{"profile":{"name":name},"wa_id":phone}],
        "messages":[{"from":phone,"id":"wamid."+ts+phone[-4:],"timestamp":ts,
                     "text":{"body":text},"type":"text"}]
    },"field":"messages"}]}]}
    body = json.dumps(payload).encode()
    req = urllib.request.Request(N8N_WEBHOOK, data=body, method="POST", headers={"Content-Type":"application/json"})
    try:
        urllib.request.urlopen(req, context=ctx, timeout=30)
        return True
    except Exception as e:
        print("    ERRO envio: " + str(e))
        return False

def wait_exec(min_id, timeout=120):
    for _ in range(timeout // 5):
        time.sleep(5)
        url = "https://n8n.casaldotrafego.com/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=1"
        req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
        try:
            resp = urllib.request.urlopen(req, context=ctx)
            data = json.loads(resp.read().decode())
            if data.get("data"):
                ex = data["data"][0]
                if int(ex["id"]) > min_id and ex.get("status") in ["success","error"]:
                    return ex
        except:
            pass
    return None

def get_bot_reply(phone):
    url = SUPABASE_URL + "/rest/v1/n8n_chat_histories?session_id=eq." + phone + "&order=created_at.desc&limit=5"
    req = urllib.request.Request(url, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        rows = json.loads(resp.read().decode())
        for r in rows:
            m = r.get("message", {})
            if isinstance(m, str):
                try: m = json.loads(m)
                except: continue
            if isinstance(m, dict) and m.get("type") == "ai":
                c = m.get("content", "")
                if c and c.strip().upper() != "STOP":
                    return c
    except:
        pass
    return None

def check_contact(phone):
    url = SUPABASE_URL + "/rest/v1/contacts?telefone=eq." + phone + "&select=id,nome,telefone,etapa_funil"
    req = urllib.request.Request(url, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = json.loads(resp.read().decode())
        return data[0] if data else None
    except:
        return None

def check_inbox_msgs(phone):
    url = SUPABASE_URL + "/rest/v1/messages?contact_phone=eq." + phone + "&select=id,direction,content,created_at&order=created_at.desc&limit=8"
    req = urllib.request.Request(url, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except:
        return []

# Get baseline exec ID
url = "https://n8n.casaldotrafego.com/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=1"
req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
resp = urllib.request.urlopen(req, context=ctx)
last_id = int(json.loads(resp.read().decode()).get("data", [{}])[0].get("id", 0))

print("=" * 60)
print("  TESTE COMPLETO - 3 LEADS x 3 MSGS (fluxo real)")
print("  Webhook -> n8n -> AI Agent -> WhatsApp -> Inbox")
print("=" * 60)

results = {"ok": 0, "erro": 0, "timeout": 0}

for i, lead in enumerate(leads):
    print("")
    print("-" * 60)
    print("  LEAD %d/3: %s (%s)" % (i+1, lead["name"], lead["phone"]))
    print("-" * 60)

    for j, msg in enumerate(lead["msgs"]):
        print("")
        print("  MSG %d/3: \"%s\"" % (j+1, msg))
        sys.stdout.write("  Enviando... ")
        sys.stdout.flush()

        ok = send_webhook(lead["phone"], lead["name"], msg)
        if not ok:
            results["erro"] += 1
            continue
        print("OK")

        sys.stdout.write("  Aguardando n8n... ")
        sys.stdout.flush()
        ex = wait_exec(last_id, timeout=120)

        if ex:
            last_id = int(ex["id"])
            status = ex.get("status")
            eid = ex["id"]

            if status == "success":
                results["ok"] += 1
                print("OK (exec #%s)" % eid)
                time.sleep(2)
                reply = get_bot_reply(lead["phone"])
                if reply:
                    for line in reply.strip().split("\n")[:3]:
                        print("  BOT: " + line[:120])
                else:
                    print("  BOT: (sem resposta no DB)")
            else:
                results["erro"] += 1
                print("ERRO (exec #%s, status=%s)" % (eid, status))
        else:
            results["timeout"] += 1
            print("TIMEOUT (120s)")

        time.sleep(4)

# Verify contacts + inbox
print("")
print("=" * 60)
print("  VERIFICANDO CONTATOS + INBOX")
print("=" * 60)

for lead in leads:
    contact = check_contact(lead["phone"])
    msgs = check_inbox_msgs(lead["phone"])
    inbound = sum(1 for m in msgs if m.get("direction") == "inbound")
    outbound = sum(1 for m in msgs if m.get("direction") == "outbound")

    if contact:
        print("  %s: contato OK (etapa=%s), inbox: %d in / %d out" % (
            lead["name"], contact.get("etapa_funil","?"), inbound, outbound))
    else:
        print("  %s: SEM contato no DB, inbox: %d in / %d out" % (
            lead["name"], inbound, outbound))

    # Show last messages
    for m in reversed(msgs[:4]):
        arrow = ">>>" if m.get("direction") == "outbound" else "<<<"
        c = (m.get("content") or "")[:90]
        print("    %s %s" % (arrow, c))

print("")
print("=" * 60)
total = results["ok"] + results["erro"] + results["timeout"]
print("  RESULTADO: %d/%d OK | %d ERROS | %d TIMEOUTS" % (results["ok"], total, results["erro"], results["timeout"]))
print("=" * 60)
