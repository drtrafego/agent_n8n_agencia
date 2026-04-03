"""
Fix stage classification in bot:
1. Update toolDescription with strict stage criteria
2. Ensure bot only advances stage when lead truly qualifies
"""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
WF_ID = "JmiydfZHpeU8tnic"
BASE = "https://n8n.casaldotrafego.com"

OBS_NODE_ID = "185d7d51-3fef-4c2d-bbc1-7430259dfc55"


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", API_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=ctx) as r:
        return r.status, json.loads(r.read())


NEW_TOOL_DESCRIPTION = """Salva observacoes do lead no CRM. OBRIGATORIO passar os 5 parametros SEMPRE:
- observacoes: resumo acumulado da conversa e situacao do lead
- stage: classificacao do lead conforme CRITERIOS ABAIXO. NUNCA deixe vazio.
- nome: nome confirmado do lead (ou vazio se nao confirmou)
- nicho: setor ou segmento do negocio do lead (ex: saude, imobiliaria, varejo, advocacia). Deixe vazio se nao foi mencionado.
- scheduled_at: data e hora da call agendada em formato ISO 8601 UTC-3. Preencha SOMENTE quando agendamento confirmado via agente_google_agenda.

CRITERIOS DE STAGE (siga RIGOROSAMENTE):
- 'novo': lead mandou a PRIMEIRA mensagem e voce ainda nao obteve resposta a nenhuma pergunta de qualificacao. Use SEMPRE na primeira interacao.
- 'qualificando': lead RESPONDEU a pelo menos 2 perguntas suas (ex: informou nicho, contou sobre o negocio, respondeu sobre equipe). Conversa ativa com troca de informacoes.
- 'interesse': lead PEDIU EXPLICITAMENTE para agendar, OU deu email para receber convite, OU disse que quer avancar/fechar. Curiosidade ("como funciona?") NAO e interesse. Perguntar preco NAO e interesse.
- 'agendado': call foi CONFIRMADA no Google Calendar com data e hora. Preencheu scheduled_at.
- 'sem_interesse': lead REJEITOU explicitamente 2x ou disse claramente que nao quer.

REGRA DE OURO: na duvida, use o stage ANTERIOR (mais conservador). Nunca avance stage sem evidencia clara do lead."""


print("=" * 60)
print("FIX STAGE CLASSIFICATION")
print("=" * 60)

print("\n1. Fetching workflow...")
_, wf = api("GET", f"/api/v1/workflows/{WF_ID}")
print(f"   Name: {wf['name']}")

# Update toolDescription
print("\n2. Updating toolDescription...")
obs_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == OBS_NODE_ID)
old_desc = wf["nodes"][obs_idx]["parameters"]["toolDescription"]
print(f"   Old desc length: {len(old_desc)}")

wf["nodes"][obs_idx]["parameters"]["toolDescription"] = NEW_TOOL_DESCRIPTION
print(f"   New desc length: {len(NEW_TOOL_DESCRIPTION)}")

# Also update the $fromAI stage description in the query to match
print("\n3. Updating stage $fromAI description in SQL query...")
old_query = wf["nodes"][obs_idx]["parameters"]["query"]

# Replace the $fromAI stage description
old_stage_desc = 'Stage OBRIGATORIO do lead. Valores exatos: novo, qualificando, interesse, agendado, sem_interesse. NUNCA deixe vazio'
new_stage_desc = 'Stage do lead. CRITERIO: novo=primeira msg sem resposta, qualificando=respondeu 2+ perguntas, interesse=pediu agendar ou deu email, agendado=call confirmada, sem_interesse=rejeitou 2x. Na duvida use o stage anterior'

new_query = old_query.replace(old_stage_desc, new_stage_desc)
if new_query != old_query:
    wf["nodes"][obs_idx]["parameters"]["query"] = new_query
    print("   Updated $fromAI stage descriptions in query")
    count = old_query.count(old_stage_desc)
    print(f"   Replaced {count} occurrences")
else:
    print("   WARNING: Could not find old stage description in query")

# Deploy
print("\n4. Deploying...")
payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {
        "executionOrder": wf["settings"].get("executionOrder"),
        "callerPolicy": wf["settings"].get("callerPolicy"),
    }
}

print("   Deactivating...")
api("POST", f"/api/v1/workflows/{WF_ID}/deactivate")

print("   Updating...")
status, result = api("PUT", f"/api/v1/workflows/{WF_ID}", payload)
print(f"   PUT status: {status}")
if status != 200:
    print("   ERRO:", str(result)[:500])
    exit(1)

print("   Reactivating...")
api("POST", f"/api/v1/workflows/{WF_ID}/activate")

# Verify
print("\n5. Verificando...")
_, wf2 = api("GET", f"/api/v1/workflows/{WF_ID}")

obs2 = next(n for n in wf2["nodes"] if n["id"] == OBS_NODE_ID)
desc2 = obs2["parameters"]["toolDescription"]
query2 = obs2["parameters"]["query"]

print(f"   CRITERIOS in desc: {'CRITERIOS' in desc2}")
print(f"   'REGRA DE OURO' in desc: {'REGRA DE OURO' in desc2}")
print(f"   New stage desc in query: {'Na duvida use o stage anterior' in query2}")
print(f"   Workflow active: {wf2['active']}")

print("\n" + "=" * 60)
print("DONE! Stage classification updated.")
print("=" * 60)
