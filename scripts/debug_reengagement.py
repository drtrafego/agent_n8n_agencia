# -*- coding: utf-8 -*-
import urllib.request, json, ssl, time

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
        return []

print("=" * 70)
print("  DEBUG REENGAGEMENT")
print("=" * 70)

# 1. Últimas execuções do reengagement
print("\n[1] ÚLTIMAS EXECUÇÕES DO REENGAGEMENT WORKFLOW")
execs = n8n_get("/api/v1/executions?workflowId=%s&limit=10" % WF_REENG)
exec_list = execs.get("data", [])
print("  Total: %d execuções" % len(exec_list))
for ex in exec_list:
    ts = ex.get("startedAt", "?")[:19]
    print("  #%s | %s | status=%s | mode=%s" % (ex["id"], ts, ex.get("status"), ex.get("mode")))

# 2. Detalhes da execução mais recente
if exec_list:
    latest = exec_list[0]
    ex_id = latest["id"]
    print("\n[2] DETALHES DA EXECUÇÃO MAIS RECENTE (#%s)" % ex_id)
    try:
        detail = n8n_get("/api/v1/executions/%s" % ex_id)
        data = detail.get("data", {})
        result_data = data.get("resultData", {})
        run_data = result_data.get("runData", {})
        print("  Status: %s" % latest.get("status"))
        print("  Started: %s" % latest.get("startedAt", "?")[:19])
        print("  Finished: %s" % latest.get("stoppedAt", "?")[:19])
        print("  Nodes executados: %s" % list(run_data.keys()))

        # Verificar erro em cada nó
        for node_name, node_runs in run_data.items():
            for run in node_runs:
                if run.get("error"):
                    print("\n  !! ERRO no nó '%s':" % node_name)
                    err = run["error"]
                    print("     %s: %s" % (err.get("name", ""), err.get("message", "")[:300]))

        # Verificar quantos leads foram encontrados
        if "Buscar Leads Elegiveis" in run_data:
            leads_run = run_data["Buscar Leads Elegiveis"]
            for r in leads_run:
                items = r.get("data", {}).get("main", [[]])[0]
                print("\n  Leads encontrados pelo SQL: %d" % len(items))
                for item in items[:5]:
                    j = item.get("json", {})
                    print("    - %s | %s | stage=%s | followup=%s | last_bot=%s" % (
                        j.get("phone", "?"), j.get("nome", "?"),
                        j.get("stage", "?"), j.get("followup_count", "?"),
                        str(j.get("last_bot_msg_at", "?"))[:16]
                    ))

        # Ver resultado do envio
        if "Enviar Reengagement" in run_data:
            send_run = run_data["Enviar Reengagement"]
            for r in send_run:
                items = r.get("data", {}).get("main", [[]])[0]
                print("\n  Msgs enviadas: %d" % len(items))
                for item in items[:3]:
                    j = item.get("json", {})
                    print("    status=%s | phone=%s" % (j.get("status"), j.get("phone", "?")))

    except Exception as e:
        print("  Erro ao buscar detalhes: %s" % e)

# 3. Checar leads elegíveis AGORA
print("\n[3] LEADS ELEGÍVEIS AGORA (consulta direta no Supabase)")
# Vamos buscar leads que deveriam ser elegíveis
leads = sb_get(
    "/rest/v1/contacts"
    "?stage=neq.agendado&stage=neq.fechou&stage=neq.perdido"
    "&select=id,nome,telefone,stage,followup_count,last_bot_msg_at,last_lead_msg_at"
    "&order=last_bot_msg_at.desc&limit=20"
)
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc)
eligible = []
not_eligible = []

for c in leads:
    phone = c.get("telefone", "")
    nome = c.get("nome", "")
    stage = c.get("stage", "")
    fc = c.get("followup_count") or 0
    last_bot = c.get("last_bot_msg_at")
    last_lead = c.get("last_lead_msg_at")

    if not last_bot:
        not_eligible.append((phone, nome, stage, "sem last_bot_msg_at"))
        continue
    if fc >= 3:
        not_eligible.append((phone, nome, stage, "followup_count=%d >= 3" % fc))
        continue

    try:
        lbt = datetime.fromisoformat(last_bot.replace("Z", "+00:00"))
        age_h = (now - lbt).total_seconds() / 3600
        if age_h < 12:
            not_eligible.append((phone, nome, stage, "last_bot_msg há %.1fh (< 12h)" % age_h))
            continue
        if age_h > 72:
            not_eligible.append((phone, nome, stage, "last_bot_msg há %.1fh (> 72h)" % age_h))
            continue
    except Exception as e:
        not_eligible.append((phone, nome, stage, "erro parse last_bot: %s" % e))
        continue

    # Check if lead replied after bot
    if last_lead:
        try:
            llt = datetime.fromisoformat(last_lead.replace("Z", "+00:00"))
            if llt > lbt:
                not_eligible.append((phone, nome, stage, "lead respondeu depois do bot"))
                continue
        except:
            pass

    eligible.append((phone, nome, stage, fc, "%.1fh atrás" % age_h))

print("  Elegíveis: %d" % len(eligible))
for p, n, s, fc, age in eligible:
    print("  OK %s | %s | stage=%s | followup=%s | bot_msg %s" % (p, n, s, fc, age))

print("\n  NAO elegiveis: %d" % len(not_eligible))
for p, n, s, reason in not_eligible[:15]:
    print("  XX %s | %s | %s" % (p[:20], (n or "")[:20], reason))

# 4. Verificar se o workflow está ativo
print("\n[4] STATUS DO WORKFLOW")
wf = n8n_get("/api/v1/workflows/%s" % WF_REENG)
print("  Nome: %s" % wf.get("name"))
print("  Ativo: %s" % wf.get("active"))
print("  Nodes: %d" % len(wf.get("nodes", [])))
node_names = [n["name"] for n in wf.get("nodes", [])]
print("  Node list: %s" % node_names)

print("\n" + "=" * 70)
print("  DIAGNÓSTICO CONCLUÍDO")
print("=" * 70)
