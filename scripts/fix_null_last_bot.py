# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY, "Content-Type": "application/json"}
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
        print("  [err] %s" % e)
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

# Leads com last_bot_msg_at = NULL
NULL_PHONES = ["554598374821", "556791099280", "554197490852", "5521988148421"]

print("=" * 70)
print("  FIX: last_bot_msg_at = NULL e investigacao de bot sem resposta")
print("=" * 70)

for phone in NULL_PHONES:
    print("\n--- %s ---" % phone)

    # Buscar wa_contact e conversa
    wa_cs = sb_get("/rest/v1/wa_contacts?wa_id=eq.%s&select=id,name" % phone)
    if not wa_cs:
        print("  sem wa_contact, skip")
        continue
    wc_id = wa_cs[0]["id"]
    name = wa_cs[0]["name"]
    print("  nome: %s" % name)

    convs = sb_get("/rest/v1/wa_conversations?contact_id=eq.%s&select=id" % wc_id)
    if not convs:
        print("  sem conversa")
        continue
    conv_id = convs[0]["id"]

    # Mensagens da conversa
    msgs = sb_get("/rest/v1/wa_messages?conversation_id=eq.%s&select=direction,body,created_at,sent_by&order=created_at.asc" % conv_id)
    outbound = [m for m in msgs if m.get("direction") == "outbound"]
    inbound = [m for m in msgs if m.get("direction") == "inbound"]
    print("  msgs: %d inbound, %d outbound" % (len(inbound), len(outbound)))

    if outbound:
        # Bot respondeu: usar o timestamp da última msg outbound como last_bot_msg_at
        last_out_time = outbound[-1]["created_at"]
        print("  Bot respondeu em: %s" % last_out_time[:19])
        result = sb_patch("/rest/v1/contacts?telefone=eq.%s" % phone, {"last_bot_msg_at": last_out_time})
        print("  CORRIGIDO: last_bot_msg_at = %s" % last_out_time[:19])
    else:
        # Bot NUNCA respondeu - investigar n8n
        print("  Bot NUNCA respondeu! Investigando n8n...")
        # Buscar execucoes do workflow principal nos ultimos 2 dias
        execs = n8n_get("/api/v1/executions?workflowId=%s&limit=50" % WF_MAIN)
        exec_list = execs.get("data", [])

        # Filtrar execucoes com esse phone (verificar nas mais recentes)
        found = False
        for ex in exec_list:
            ts = ex.get("startedAt", "")
            if not ts:
                continue
            # Pegar detalhes para ver se o phone está no input
            try:
                detail = n8n_get("/api/v1/executions/%s" % ex["id"])
                d = detail.get("data", {})
                # Verificar no input do webhook
                trigger_data = d.get("resultData", {}).get("runData", {})
                for node_name, runs in trigger_data.items():
                    for run in runs:
                        input_data = str(run)
                        if phone in input_data:
                            print("  Encontrado em exec #%s (%s) - status=%s" % (ex["id"], ts[:16], ex.get("status")))
                            found = True
                            break
                    if found:
                        break
            except:
                pass
            if found:
                break

        if not found:
            print("  NAO encontrado em nenhuma execucao n8n recente")
            print("  -> Causa: webhook nao chegou ao n8n ou exec muito antiga")

        # Checar last_lead_msg_at
        crm = sb_get("/rest/v1/contacts?telefone=eq.%s&select=last_lead_msg_at" % phone)
        if crm:
            print("  last_lead_msg_at: %s" % crm[0].get("last_lead_msg_at"))

print("\n" + "=" * 70)
print("  VERIFICACAO FINAL - Estado dos 4 leads")
print("=" * 70)
for phone in NULL_PHONES:
    crm = sb_get("/rest/v1/contacts?telefone=eq.%s&select=nome,stage,last_bot_msg_at,last_lead_msg_at,followup_count" % phone)
    if crm:
        c = crm[0]
        print("  %s | %s | last_bot=%s | last_lead=%s" % (
            phone, (c.get("nome") or "")[:25],
            str(c.get("last_bot_msg_at") or "NULL")[:19],
            str(c.get("last_lead_msg_at") or "NULL")[:19]
        ))
