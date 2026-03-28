# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}
WF_REENG = "aBMaCWPodLaS8I6L"

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
        print("  [sb_get error] %s" % e)
        return []

print("=" * 70)
print("  DEBUG REENGAGEMENT")
print("=" * 70)

# 1. Ultimas execucoes
print("\n[1] ULTIMAS EXECUCOES DO REENGAGEMENT")
execs = n8n_get("/api/v1/executions?workflowId=%s&limit=10" % WF_REENG)
exec_list = execs.get("data", [])
print("  Total: %d execucoes" % len(exec_list))
for ex in exec_list:
    ts = ex.get("startedAt", "?")[:19]
    print("  #%s | %s | status=%s | mode=%s" % (ex["id"], ts, ex.get("status"), ex.get("mode")))

# 2. Detalhes da mais recente (execucao #2143 foi success mas sem nodes?)
if exec_list:
    latest = exec_list[0]
    ex_id = latest["id"]
    print("\n[2] DETALHES DA EXECUCAO #%s" % ex_id)
    try:
        detail = n8n_get("/api/v1/executions/%s" % ex_id)
        data = detail.get("data", {})
        result_data = data.get("resultData", {})
        run_data = result_data.get("runData", {})
        print("  Status: %s" % latest.get("status"))
        print("  Nodes executados: %s" % list(run_data.keys()))

        for node_name, node_runs in run_data.items():
            for run in node_runs:
                if run.get("error"):
                    err = run["error"]
                    print("  ERRO no no '%s': %s - %s" % (node_name, err.get("name",""), err.get("message","")[:300]))

        if "Buscar Leads Elegiveis" in run_data:
            for r in run_data["Buscar Leads Elegiveis"]:
                items = r.get("data", {}).get("main", [[]])[0]
                print("  Leads encontrados: %d" % len(items))
                for item in items[:5]:
                    j = item.get("json", {})
                    print("    phone=%s | stage=%s | fc=%s | last_bot=%s" % (
                        j.get("phone","?"), j.get("stage","?"),
                        j.get("followup_count","?"), str(j.get("last_bot_msg_at","?"))[:16]))

    except Exception as e:
        print("  Erro ao buscar detalhes: %s" % e)

# 3. Buscar leads com critérios mais amplos para entender o que falhou
print("\n[3] TODOS OS CONTACTS COM last_bot_msg_at preenchido")
leads = sb_get(
    "/rest/v1/contacts"
    "?last_bot_msg_at=not.is.null"
    "&select=id,nome,telefone,stage,followup_count,last_bot_msg_at,last_lead_msg_at"
    "&order=last_bot_msg_at.desc&limit=20"
)
print("  Total com last_bot_msg_at: %d" % len(leads))

now = datetime.now(timezone.utc)
print("\n  Analise de elegibilidade:")
print("  %-15s %-25s %-12s %5s %6s %6s %s" % ("phone", "nome", "stage", "fc", "h_bot", "h_lead", "status"))
print("  " + "-" * 90)

for c in leads:
    phone = (c.get("telefone") or "")
    nome = (c.get("nome") or "")[:24]
    stage = (c.get("stage") or "")
    fc = c.get("followup_count") or 0
    last_bot = c.get("last_bot_msg_at")
    last_lead = c.get("last_lead_msg_at")

    reasons = []

    if stage in ("agendado", "agendou", "fechou", "perdido"):
        reasons.append("stage=%s" % stage)

    if fc >= 3:
        reasons.append("fc=%d>=3" % fc)

    h_bot = "N/A"
    h_lead = "N/A"
    if last_bot:
        try:
            lbt = datetime.fromisoformat(last_bot.replace("Z", "+00:00"))
            age_h = (now - lbt).total_seconds() / 3600
            h_bot = "%.1fh" % age_h
            if age_h < 12:
                reasons.append("<12h")
            elif age_h > 72:
                reasons.append(">72h")
        except:
            reasons.append("parse_err_bot")
    else:
        reasons.append("no_last_bot")

    if last_lead and last_bot:
        try:
            llt = datetime.fromisoformat(last_lead.replace("Z", "+00:00"))
            lbt2 = datetime.fromisoformat(last_bot.replace("Z", "+00:00"))
            age_lead_h = (now - llt).total_seconds() / 3600
            h_lead = "%.1fh" % age_lead_h
            if llt > lbt2:
                reasons.append("lead_respondeu")
        except:
            pass

    # check wa_conversation active
    status = "ELEGIVEL" if not reasons else ("BLOQ: " + ", ".join(reasons))
    print("  %-15s %-25s %-12s %5d %6s %6s %s" % (phone[:15], nome[:25], stage[:12], fc, h_bot, h_lead, status))

# 4. Verificar se ha leads com bot_active=true nas conversations
print("\n[4] WA_CONVERSATIONS COM bot_active=true E STATUS=open")
convs = sb_get("/rest/v1/wa_conversations?bot_active=eq.true&status=eq.open&select=id,contact_id,last_message,last_message_at,unread_count&limit=20")
print("  Total: %d" % len(convs))
for cv in convs[:10]:
    # get wa_contact
    wa_cs = sb_get("/rest/v1/wa_contacts?id=eq.%s&select=wa_id,name" % cv["contact_id"])
    wa_id = wa_cs[0]["wa_id"] if wa_cs else "?"
    wa_name = wa_cs[0]["name"] if wa_cs else "?"
    print("  phone=%s | name=%s | last_msg=%s" % (wa_id, wa_name[:20], (cv.get("last_message") or "")[:50]))

# 5. Status do workflow
print("\n[5] STATUS DO WORKFLOW")
wf = n8n_get("/api/v1/workflows/%s" % WF_REENG)
print("  Nome: %s" % wf.get("name"))
print("  Ativo: %s" % wf.get("active"))
nodes = wf.get("nodes", [])
print("  Nodes (%d): %s" % (len(nodes), [n["name"] for n in nodes]))

print("\n" + "=" * 70)
print("  DIAGNOSTICO CONCLUIDO")
print("=" * 70)
