"""
Add scheduled_at field to observacoes_sdr node and update reengagement SQL.
"""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
BASE = "https://n8n.casaldotrafego.com"

SDR_WF_ID = "JmiydfZHpeU8tnic"
OBS_NODE_ID = "185d7d51-3fef-4c2d-bbc1-7430259dfc55"

REENG_WF_ID = "aBMaCWPodLaS8I6L"


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("X-N8N-API-KEY", API_KEY)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, context=ctx) as r:
        return r.status, json.loads(r.read())


# ──────────────────────────────────────────────────────────
# PART 1: update observacoes_sdr node in SDR workflow
# ──────────────────────────────────────────────────────────
print("=== PART 1: SDR workflow - add scheduled_at ===")
_, wf = api("GET", f"/api/v1/workflows/{SDR_WF_ID}")

node_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == OBS_NODE_ID)
node = wf["nodes"][node_idx]

# Update tool description to mention scheduled_at
node["parameters"]["toolDescription"] = (
    "Salva observacoes do lead no CRM. OBRIGATORIO passar os 5 parametros SEMPRE:\n"
    "- observacoes: resumo acumulado da conversa e situacao do lead\n"
    "- stage: classificacao OBRIGATORIA do lead. Valores EXATOS: 'novo', 'qualificando', 'interesse', 'agendado', 'sem_interesse'. NUNCA deixe vazio.\n"
    "- nome: nome confirmado do lead (ou vazio se nao confirmou)\n"
    "- nicho: setor ou segmento do negocio do lead (ex: saude, imobiliaria, varejo, advocacia, emprestimo consignado, restaurante, etc). Deixe vazio se nao foi mencionado.\n"
    "- scheduled_at: data e hora da call agendada em formato ISO 8601 UTC-3 (ex: 2026-04-02T14:00:00-03:00). Preencha SOMENTE quando um agendamento for confirmado via agente_google_agenda. Deixe vazio nos demais casos."
)

# New SQL with scheduled_at
node["parameters"]["query"] = """INSERT INTO contacts (telefone, observacoes_sdr, stage, stage_updated_at, nome, nicho, scheduled_at)
VALUES (
  '{{ $('Code4').item.json.telefone }}',
  '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}',
  CASE
    WHEN '{{ $fromAI("stage", "Stage OBRIGATORIO do lead. Valores exatos: novo, qualificando, interesse, agendado, sem_interesse. NUNCA deixe vazio", "string") }}' != '' THEN '{{ $fromAI("stage", "Stage OBRIGATORIO do lead. Valores exatos: novo, qualificando, interesse, agendado, sem_interesse. NUNCA deixe vazio", "string") }}'
    WHEN '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%agendou%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%agendad%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%call agendad%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%convite disparado%' THEN 'agendado'
    WHEN '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%sem interesse%' OR '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%sem_interesse%' THEN 'sem_interesse'
    WHEN '{{ $fromAI("observacoes", "Resumo completo e acumulado do lead incluindo nicho, dor, equipe, objecoes, email, horario, status", "string") }}' ILIKE '%qualificando%' THEN 'qualificando'
    ELSE 'novo'
  END,
  NOW(),
  '{{ $fromAI("nome", "Nome confirmado pelo lead na conversa. Deixe vazio se nao houve confirmacao de nome", "string") }}',
  NULLIF('{{ $fromAI("nicho", "Setor ou segmento do negocio do lead, ex: saude, imobiliaria, varejo, advocacia, emprestimo consignado, restaurante. Deixe vazio se nao foi mencionado", "string") }}', ''),
  NULLIF('{{ $fromAI("scheduled_at", "Data e hora da call agendada em ISO 8601 UTC-3, ex: 2026-04-02T14:00:00-03:00. Preencha SOMENTE quando agendamento confirmado via agente_google_agenda. Deixe vazio caso contrario", "string") }}', '')::TIMESTAMPTZ
)
ON CONFLICT (telefone)
DO UPDATE SET
  observacoes_sdr = EXCLUDED.observacoes_sdr,
  stage = CASE
    WHEN EXCLUDED.stage != '' AND EXCLUDED.stage != 'novo' THEN EXCLUDED.stage
    WHEN EXCLUDED.observacoes_sdr ILIKE '%agendou%' OR EXCLUDED.observacoes_sdr ILIKE '%agendad%' OR EXCLUDED.observacoes_sdr ILIKE '%call agendad%' OR EXCLUDED.observacoes_sdr ILIKE '%convite disparado%' THEN 'agendado'
    WHEN EXCLUDED.observacoes_sdr ILIKE '%sem interesse%' OR EXCLUDED.observacoes_sdr ILIKE '%sem_interesse%' THEN 'sem_interesse'
    WHEN EXCLUDED.observacoes_sdr ILIKE '%qualificando%' THEN 'qualificando'
    ELSE contacts.stage
  END,
  stage_updated_at = NOW(),
  updated_at = NOW(),
  nome = COALESCE(NULLIF(EXCLUDED.nome, ''), contacts.nome),
  nicho = COALESCE(NULLIF('{{ $fromAI("nicho", "Setor ou segmento do negocio do lead, ex: saude, imobiliaria, varejo, advocacia, emprestimo consignado, restaurante. Deixe vazio se nao foi mencionado", "string") }}', ''), contacts.nicho),
  scheduled_at = COALESCE(NULLIF('{{ $fromAI("scheduled_at", "Data e hora da call agendada em ISO 8601 UTC-3, ex: 2026-04-02T14:00:00-03:00. Preencha SOMENTE quando agendamento confirmado via agente_google_agenda. Deixe vazio caso contrario", "string") }}', '')::TIMESTAMPTZ, contacts.scheduled_at)"""

wf["nodes"][node_idx] = node

payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {
        "executionOrder": wf["settings"].get("executionOrder"),
        "callerPolicy": wf["settings"].get("callerPolicy"),
    }
}

api("POST", f"/api/v1/workflows/{SDR_WF_ID}/deactivate")
status, _ = api("PUT", f"/api/v1/workflows/{SDR_WF_ID}", payload)
print(f"SDR PUT: {status}")
if status != 200:
    print("ERRO no SDR")
    exit(1)
api("POST", f"/api/v1/workflows/{SDR_WF_ID}/activate")
print("SDR atualizado e reativado.")


# ──────────────────────────────────────────────────────────
# PART 2: update reengagement SQL - use scheduled_at
# ──────────────────────────────────────────────────────────
print("\n=== PART 2: Reengagement workflow - use scheduled_at ===")
_, wf_r = api("GET", f"/api/v1/workflows/{REENG_WF_ID}")

pg_node_idx = next(
    i for i, n in enumerate(wf_r["nodes"])
    if n.get("type", "") == "n8n-nodes-base.postgres"
)
pg_node = wf_r["nodes"][pg_node_idx]

# Replace only the reagend CTE condition
old_reagend = """  WHERE c.stage = 'agendado'
    AND c.stage_updated_at IS NOT NULL
    AND c.stage_updated_at < NOW() - INTERVAL '72 hours'
    AND wc.bot_active = true AND wc.status = 'open'
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)"""

new_reagend = """  WHERE c.stage = 'agendado'
    AND c.scheduled_at IS NOT NULL
    AND c.scheduled_at < NOW() - INTERVAL '24 hours'
    AND wc.bot_active = true AND wc.status = 'open'
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)"""

current_query = pg_node["parameters"]["query"]
if old_reagend not in current_query:
    print("AVISO: trecho exato nao encontrado, tentando busca parcial...")
    # fallback: replace any reagend stage_updated_at condition
    import re
    current_query = re.sub(
        r"WHERE c\.stage = 'agendado'\s+AND c\.\w+_at IS NOT NULL\s+AND c\.\w+_at < NOW\(\) - INTERVAL '[^']+'\s+AND wc\.bot_active",
        "WHERE c.stage = 'agendado'\n    AND c.scheduled_at IS NOT NULL\n    AND c.scheduled_at < NOW() - INTERVAL '24 hours'\n    AND wc.bot_active",
        current_query
    )
else:
    current_query = current_query.replace(old_reagend, new_reagend)

pg_node["parameters"]["query"] = current_query
wf_r["nodes"][pg_node_idx] = pg_node

payload_r = {
    "name": wf_r["name"],
    "nodes": wf_r["nodes"],
    "connections": wf_r["connections"],
    "settings": {
        "executionOrder": wf_r["settings"].get("executionOrder"),
        "callerPolicy": wf_r["settings"].get("callerPolicy"),
    }
}

api("POST", f"/api/v1/workflows/{REENG_WF_ID}/deactivate")
status, _ = api("PUT", f"/api/v1/workflows/{REENG_WF_ID}", payload_r)
print(f"Reengagement PUT: {status}")
if status != 200:
    print("ERRO no reengajamento")
    exit(1)
api("POST", f"/api/v1/workflows/{REENG_WF_ID}/activate")
print("Reengagement atualizado e reativado.")

# ── Verify ──
print("\n=== Verificando ===")
_, wf_check = api("GET", f"/api/v1/workflows/{REENG_WF_ID}")
pg2 = wf_check["nodes"][pg_node_idx]
q = pg2["parameters"]["query"]
if "scheduled_at < NOW() - INTERVAL '24 hours'" in q:
    print("OK: reengajamento usa scheduled_at + 24h")
else:
    print("AVISO: verificar query manualmente")

_, wf_sdr2 = api("GET", f"/api/v1/workflows/{SDR_WF_ID}")
obs2 = next(n for n in wf_sdr2["nodes"] if n["id"] == OBS_NODE_ID)
if "scheduled_at" in obs2["parameters"]["query"]:
    print("OK: observacoes_sdr salva scheduled_at")
else:
    print("AVISO: verificar observacoes_sdr")

print("\nDone!")
