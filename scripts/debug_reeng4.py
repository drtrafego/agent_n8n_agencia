# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
WF_MAIN = "JmiydfZHpeU8tnic"

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

now = datetime.now(timezone.utc)

# Leads com last_bot_msg_at = NULL
NULL_PHONES = ["554598374821", "556791099280", "554197490852", "5521988148421"]

print("=" * 70)
print("  ANALISE DOS LEADS COM last_bot_msg_at = NULL")
print("=" * 70)

for phone in NULL_PHONES:
    print("\n--- %s ---" % phone)

    # wa_contacts
    wa_cs = sb_get("/rest/v1/wa_contacts?wa_id=eq.%s&select=id,name" % phone)
    if not wa_cs:
        print("  SEM wa_contact")
        continue
    wc_id = wa_cs[0]["id"]
    print("  name: %s" % wa_cs[0]["name"])

    # conversations
    convs = sb_get("/rest/v1/wa_conversations?contact_id=eq.%s&select=id,status,bot_active,last_message,last_message_at" % wc_id)
    for cv in convs:
        print("  conv: status=%s | bot=%s | last_msg=%s" % (cv.get("status"), cv.get("bot_active"), (cv.get("last_message") or "")[:60]))
        # messages
        msgs = sb_get("/rest/v1/wa_messages?conversation_id=eq.%s&select=direction,body,sent_by,created_at&order=created_at.asc" % cv["id"])
        print("  mensagens: %d total" % len(msgs))
        for m in msgs:
            arrow = ">>>" if m.get("direction") == "outbound" else "<<<"
            body = (m.get("body") or "")[:80]
            print("    %s [%s] %s" % (arrow, m.get("sent_by","?"), body))

    # contact CRM
    crm = sb_get("/rest/v1/contacts?telefone=eq.%s&select=id,nome,stage,last_bot_msg_at,last_lead_msg_at,followup_count" % phone)
    if crm:
        c = crm[0]
        print("  CRM: stage=%s | last_bot=%s | last_lead=%s" % (c.get("stage"), c.get("last_bot_msg_at"), c.get("last_lead_msg_at")))
    else:
        print("  CRM: NAO ENCONTRADO")

# Verificar o workflow principal - especificamente se ele atualiza last_bot_msg_at
print("\n" + "=" * 70)
print("  WORKFLOW PRINCIPAL - NODES QUE ATUALIZAM CRM")
print("=" * 70)
wf = n8n_get("/api/v1/workflows/%s" % WF_MAIN)
print("  Nome: %s | Ativo: %s | Nodes: %d" % (wf.get("name"), wf.get("active"), len(wf.get("nodes",[]))))

for node in wf.get("nodes", []):
    name = node.get("name", "")
    ntype = node.get("type", "")
    params = node.get("parameters", {})

    # Procurar nos que fazem UPDATE no banco ou HTTP para atualizar contatos
    if "postgres" in ntype.lower() or "Postgres" in name:
        query = params.get("query", "")
        if query:
            print("\n  Node: %s" % name)
            print("  Query: %s" % query[:300])

    if "httpRequest" in ntype or "Http" in name or "HTTP" in name or "bot-send" in str(params).lower() or "Salvar" in name or "Atualiz" in name or "Update" in name or "CRM" in name:
        print("\n  Node: %s (%s)" % (name, ntype))
        # Mostrar parâmetros relevantes
        url = params.get("url", "")
        body = params.get("jsonBody", params.get("body", ""))
        if url:
            print("  URL: %s" % url)
        if body:
            print("  Body: %s" % str(body)[:200])
