# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys, time
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl._create_unverified_context()
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
N8N_WH = "https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103"

def sb_get(path):
    req = urllib.request.Request(SUPABASE_URL + path, headers=SB_H)
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

def trigger_n8n(phone, name, msg_text, wamid_suffix):
    ts = str(int(time.time()))
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "messages": [{
                        "from": phone,
                        "id": "wamid.retrigger" + wamid_suffix,
                        "timestamp": ts,
                        "text": {"body": msg_text},
                        "type": "text"
                    }],
                    "contacts": [{"profile": {"name": name}, "wa_id": phone}],
                    "metadata": {"display_phone_number": "5511996681596", "phone_number_id": "115216611574100"},
                },
            }],
        }],
    }
    body = json.dumps(payload).encode()
    req = urllib.request.Request(N8N_WH, data=body, method="POST",
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        return resp.getcode()
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return str(e)

# Leads para re-disparar
LEADS = [
    ("554197490852", "Symone", "Queria um Agente de IA como funciona?", "sym"),
    ("5521988148421", "Conect", "Queria um Agente de IA como funciona?", "con"),
]

print("=" * 60)
print("  RETRIGGER: BOT RESPONDER A LEADS PENDENTES")
print("=" * 60)

for phone, name, msg, suffix in LEADS:
    print("\n  Disparando para %s (%s)..." % (name, phone))

    # Verificar msgs atuais antes
    wa_cs = sb_get("/rest/v1/wa_contacts?wa_id=eq.%s&select=id" % phone)
    if not wa_cs:
        print("  sem wa_contact, skip")
        continue
    convs = sb_get("/rest/v1/wa_conversations?contact_id=eq.%s&select=id" % wa_cs[0]["id"])
    if not convs:
        print("  sem conversa, skip")
        continue
    msgs_antes = sb_get("/rest/v1/wa_messages?conversation_id=eq.%s&select=direction&order=created_at.asc" % convs[0]["id"])
    outbound_antes = sum(1 for m in msgs_antes if m.get("direction") == "outbound")
    print("  Msgs antes: %d total (%d outbound)" % (len(msgs_antes), outbound_antes))

    # Disparar
    code = trigger_n8n(phone, name, msg, suffix)
    print("  Webhook n8n: %s" % code)

    # Aguardar processamento
    print("  Aguardando 30s...")
    time.sleep(30)

    # Verificar resultado
    msgs_depois = sb_get("/rest/v1/wa_messages?conversation_id=eq.%s&select=direction,body,created_at&order=created_at.asc" % convs[0]["id"])
    outbound_depois = sum(1 for m in msgs_depois if m.get("direction") == "outbound")
    print("  Msgs depois: %d total (%d outbound)" % (len(msgs_depois), outbound_depois))

    if outbound_depois > outbound_antes:
        last_out = [m for m in msgs_depois if m.get("direction") == "outbound"][-1]
        print("  BOT RESPONDEU: %s" % (last_out.get("body") or "")[:100])

        # Verificar last_bot_msg_at
        crm = sb_get("/rest/v1/contacts?telefone=eq.%s&select=last_bot_msg_at" % phone)
        if crm:
            print("  last_bot_msg_at: %s" % (crm[0].get("last_bot_msg_at") or "NULL"))
    else:
        print("  Bot NAO respondeu ainda")

print("\n" + "=" * 60)
print("  RESUMO FINAL - Estado de todos os leads")
print("=" * 60)
all_phones = ["554598374821", "556791099280", "554197490852", "5521988148421"]
now = datetime.now(timezone.utc)
for phone in all_phones:
    crm = sb_get("/rest/v1/contacts?telefone=eq.%s&select=nome,stage,last_bot_msg_at,followup_count" % phone)
    if crm:
        c = crm[0]
        lbt = c.get("last_bot_msg_at")
        h_bot = "NULL"
        if lbt:
            try:
                lbt_dt = datetime.fromisoformat(lbt.replace("Z", "+00:00"))
                h_bot = "%.1fh atras" % ((now - lbt_dt).total_seconds() / 3600)
            except:
                h_bot = lbt[:16]
        print("  %s | %s | stage=%s | last_bot=%s | fc=%s" % (
            phone, (c.get("nome") or "")[:20], c.get("stage"), h_bot, c.get("followup_count")))
