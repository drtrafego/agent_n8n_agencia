# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY, "Content-Type": "application/json"}

def n8n_get(path):
    req = urllib.request.Request("https://n8n.casaldotrafego.com" + path, headers={"X-N8N-API-KEY": API_KEY})
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

def sb_get(path):
    req = urllib.request.Request(SUPABASE_URL + path, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        return []

def sb_patch(path, data):
    body = json.dumps(data).encode()
    headers = dict(SB_H)
    headers["Prefer"] = "return=representation"
    req = urllib.request.Request(SUPABASE_URL + path, data=body, method="PATCH", headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        result = resp.read().decode()
        return json.loads(result) if result.strip() else []
    except urllib.error.HTTPError as e:
        print("  HTTP %d: %s" % (e.code, e.read().decode()[:200]))
        return None

PHONES_NO_BOT = ["556791099280", "554197490852", "5521988148421"]

print("=" * 70)
print("  INVESTIGAR: BOT NAO RESPONDEU A ESSES LEADS")
print("=" * 70)

# 1. Verificar webhook logs para esses phones
print("\n[1] WA_WEBHOOK_LOGS - verificar se webhooks chegaram")
# Checar estrutura da tabela primeiro
logs_sample = sb_get("/rest/v1/wa_webhook_logs?limit=3&select=*")
if logs_sample:
    print("  Colunas da tabela: %s" % list(logs_sample[0].keys()))

    # Tentar buscar por conteudo
    all_logs = sb_get("/rest/v1/wa_webhook_logs?limit=200&order=created_at.desc&select=id,created_at,source,status")
    print("  Total logs recentes: %d" % len(all_logs))

    # Logs por hora/dia para ver quando pararam
    for log in all_logs[:20]:
        print("  [%s] source=%s status=%s" % (
            str(log.get("created_at",""))[:19],
            log.get("source","?"),
            log.get("status","?")
        ))
else:
    print("  Sem logs ou tabela vazia")

# 2. Verificar execucoes n8n por timestamp
print("\n[2] EXECUCOES N8N PRINCIPAL - ultimas 30")
execs = n8n_get("/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=30")
exec_list = execs.get("data", [])
print("  Total: %d" % len(exec_list))
for ex in exec_list[:30]:
    ts = ex.get("startedAt", "?")[:16]
    print("  #%s | %s | %s | %s" % (ex["id"], ts, ex.get("status"), ex.get("mode")))

# 3. Para os leads sem resposta: ver a mensagem que mandaram e quando
print("\n[3] MENSAGENS DOS LEADS SEM BOT REPLY")
for phone in PHONES_NO_BOT:
    wa_cs = sb_get("/rest/v1/wa_contacts?wa_id=eq.%s&select=id,name" % phone)
    if not wa_cs: continue
    wc_id = wa_cs[0]["id"]
    convs = sb_get("/rest/v1/wa_conversations?contact_id=eq.%s&select=id" % wc_id)
    if not convs: continue
    msgs = sb_get("/rest/v1/wa_messages?conversation_id=eq.%s&select=direction,body,created_at&order=created_at.asc" % convs[0]["id"])
    print("\n  %s (%s):" % (phone, wa_cs[0]["name"]))
    for m in msgs:
        print("    [%s] %s: %s" % (
            str(m.get("created_at",""))[:16],
            m.get("direction"),
            (m.get("body") or "")[:80]
        ))

# 4. Fix: atualizar last_lead_msg_at para esses contacts
# (usando timestamp da mensagem inbound)
print("\n[4] CORRIGINDO last_lead_msg_at para leads sem botr resposta")
for phone in PHONES_NO_BOT:
    wa_cs = sb_get("/rest/v1/wa_contacts?wa_id=eq.%s&select=id,name" % phone)
    if not wa_cs: continue
    wc_id = wa_cs[0]["id"]
    convs = sb_get("/rest/v1/wa_conversations?contact_id=eq.%s&select=id" % wc_id)
    if not convs: continue
    msgs = sb_get("/rest/v1/wa_messages?conversation_id=eq.%s&direction=eq.inbound&select=created_at&order=created_at.desc&limit=1" % convs[0]["id"])
    if msgs:
        last_in_ts = msgs[0]["created_at"]
        result = sb_patch("/rest/v1/contacts?telefone=eq.%s" % phone, {"last_lead_msg_at": last_in_ts})
        print("  %s: last_lead_msg_at = %s %s" % (phone, last_in_ts[:19], "OK" if result is not None else "ERRO"))

print("\n" + "=" * 70)
print("  CONCLUSAO")
print("=" * 70)
print("""
PROBLEMA RAIZ:
  - 3 leads (Suh, Symone, Conect) mandaram mensagem mas o n8n NAO processou
  - Causa provavel: execucao do n8n nao encontrada para esses phones
  - Pode ser: timeout, n8n fora do ar naquele momento, ou mensagem perdida

FIXES APLICADOS HOJE:
  1. bot-send/route.ts -> agora atualiza contacts.last_bot_msg_at = NOW()
  2. webhook/route.ts  -> agora atualiza contacts.last_lead_msg_at = NOW()
  3. Cintia: last_bot_msg_at corrigido manualmente
  4. Suh/Symone/Conect: last_lead_msg_at corrigido manualmente

PROXIMOS PASSOS:
  - Suh/Symone/Conect precisam do bot principal responder primeiro
  - Depois que o bot responder, last_bot_msg_at sera atualizado automaticamente
  - 12h depois, o reengagement os pega normalmente
  - 8 leads atuais ficam elegiveis em ~1-2h (12h desde ultima msg do bot)
""")
