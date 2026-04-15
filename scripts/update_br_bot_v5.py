"""
Update BR bot (JmiydfZHpeU8tnic):
1. Modelo gemini-2.5-flash nos 3 LM nodes
2. Dia da semana + horario no prompt SDR
3. Expressoes de aceite no prompt SDR
"""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
WF_ID = "JmiydfZHpeU8tnic"
BASE = "https://n8n.casaldotrafego.com"

# Node IDs
SDR_NODE_ID = "33061bc5-ffd0-47cf-8748-ecd408ceba73"
LM1_NODE_ID = "bf014e33-aa3d-4d1a-a29a-ecca22bd7617"  # OpenAI Chat Model1
LM2_NODE_ID = "b45970dd-c0cc-42b9-9944-b4ef3eaf788a"  # OpenAI Chat Model2
LM3_NODE_ID = "5a22cea8-74d9-44a3-83dd-781b2baada46"  # OpenAI Chat Model3


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", API_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=ctx) as r:
        return r.status, json.loads(r.read())


print("=" * 60)
print("UPDATE BR BOT v5 - JmiydfZHpeU8tnic")
print("=" * 60)

# 1. Fetch workflow
print("\n1. Fetching workflow...")
_, wf = api("GET", f"/api/v1/workflows/{WF_ID}")
print(f"   Name: {wf['name']}")
print(f"   Active: {wf['active']}")
print(f"   Nodes: {len(wf['nodes'])}")

# 2. Get current SDR prompt and patch it
print("\n2. Patching SDR prompt...")
sdr_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == SDR_NODE_ID)
current_prompt = wf["nodes"][sdr_idx]["parameters"]["options"]["systemMessage"]

# Check if ClaudIA is already there
if "ClaudIA" not in current_prompt:
    print("   ERRO: Prompt nao e ClaudIA. Abortando para seguranca.")
    exit(1)
print("   Prompt atual e ClaudIA. OK.")

# --- PATCH 1: Add day of week context ---
OLD_DATE_LINE = "Data atual: {{ new Date().toLocaleDateString('pt-BR') }}. Fuso: UTC-3."
NEW_DATE_BLOCK = """CONTEXTO TEMPORAL:
Hoje \u00e9 {{ $now.setZone("America/Sao_Paulo").toFormat("EEEE, dd/MM/yyyy") }}. Hor\u00e1rio atual: {{ $now.setZone("America/Sao_Paulo").toFormat("HH:mm") }}. Fuso: UTC-3.
Use essa informa\u00e7\u00e3o para oferecer agendamentos de forma inteligente. Se hoje for dia \u00fatil e ainda houver hor\u00e1rios dispon\u00edveis, oferte "ainda hoje" como op\u00e7\u00e3o. Se for sexta \u00e0 tarde, oferte "segunda pela manh\u00e3". Nunca oferte fins de semana."""

if OLD_DATE_LINE in current_prompt:
    current_prompt = current_prompt.replace(OLD_DATE_LINE, NEW_DATE_BLOCK)
    print("   Dia da semana adicionado (substituiu linha antiga).")
elif "CONTEXTO TEMPORAL" in current_prompt:
    print("   Dia da semana ja presente. Pulando.")
else:
    # Try alternative date formats
    for alt in [
        'Data atual: {{ new Date().toLocaleDateString(\'pt-BR\') }}',
        'Data atual:',
    ]:
        if alt in current_prompt and "CONTEXTO TEMPORAL" not in current_prompt:
            # Find the line and replace
            lines = current_prompt.split('\n')
            new_lines = []
            replaced = False
            for line in lines:
                if 'Data atual:' in line and not replaced:
                    new_lines.append(NEW_DATE_BLOCK)
                    replaced = True
                else:
                    new_lines.append(line)
            if replaced:
                current_prompt = '\n'.join(new_lines)
                print("   Dia da semana adicionado (formato alternativo).")
                break
    else:
        # Append before SAIDA section
        current_prompt = current_prompt.replace(
            "SA\u00cdDA:",
            NEW_DATE_BLOCK + "\n\nSA\u00cdDA:"
        )
        print("   Dia da semana adicionado (antes de SAIDA).")

# --- PATCH 2: Add acceptance expressions ---
ACCEPTANCE_BLOCK = """EXPRESS\u00d5ES DE ACEITE (REGRA CR\u00cdTICA):
As seguintes express\u00f5es em portugu\u00eas significam ACEITE/SIM. NUNCA encerre a conversa quando receber qualquer uma delas. Siga para o pr\u00f3ximo passo do fluxo:
"pode ser", "bora", "vamo", "vamos", "fechou", "beleza", "por mim tudo bem", "manda ver", "sim", "ok", "pode", "show", "massa", "top", "combinado", "feito", "dale", "partiu", "to dentro", "quero", "quero sim", "manda", "vai la", "blz", "tmj", "isso", "claro", "com certeza", "aham", "uhum", "perfeito", "\u00f3timo"
Se o lead responder com qualquer uma dessas express\u00f5es ap\u00f3s uma proposta de agendamento, trate como ACEITE e avance para pedir email ou hor\u00e1rio."""

if "EXPRESS\u00d5ES DE ACEITE" not in current_prompt:
    # Insert before ENCERRAMENTO section
    if "ENCERRAMENTO:" in current_prompt:
        current_prompt = current_prompt.replace(
            "ENCERRAMENTO:",
            ACCEPTANCE_BLOCK + "\n\nENCERRAMENTO:"
        )
        print("   Expressoes de aceite adicionadas (antes de ENCERRAMENTO).")
    else:
        # Insert before FLUXO section
        current_prompt = current_prompt.replace(
            "FLUXO:",
            ACCEPTANCE_BLOCK + "\n\nFLUXO:"
        )
        print("   Expressoes de aceite adicionadas (antes de FLUXO).")
else:
    print("   Expressoes de aceite ja presentes. Pulando.")

# --- PATCH 3: Add clarification to ENCERRAMENTO ---
if "IMPORTANTE:" not in current_prompt.split("ENCERRAMENTO:")[1] if "ENCERRAMENTO:" in current_prompt else True:
    old_enc = 'Se rejeitar a mesma ideia 2 vezes, encerre da mesma forma.'
    new_enc = """Se rejeitar a mesma ideia 2 vezes, encerre da mesma forma.
IMPORTANTE: "pode ser", "bora", "beleza" e similares N\u00c3O s\u00e3o rejei\u00e7\u00e3o. S\u00e3o aceite. Releia a lista de EXPRESS\u00d5ES DE ACEITE acima."""
    if old_enc in current_prompt:
        current_prompt = current_prompt.replace(old_enc, new_enc)
        print("   Clarificacao no ENCERRAMENTO adicionada.")

# --- PATCH 4: Add flexible flow instruction ---
FLEX_INSTRUCTION = "REGRA: O fluxo acima \u00e9 um GUIA, n\u00e3o um script r\u00edgido. Adapte ao ritmo do lead. Se ele j\u00e1 demonstrou interesse e quer agendar, pule etapas. Se ele est\u00e1 conversando sobre um problema espec\u00edfico, explore antes de mudar de assunto. Seja natural, n\u00e3o mec\u00e2nico."
if "GUIA, n\u00e3o um script" not in current_prompt:
    # Add after the REGRA about curiosidade
    old_regra = 'REGRA: Curiosidade ("como funciona?", "quanto custa?") N\u00c3O \u00e9 pedido de agendamento. Continue qualificando.'
    if old_regra in current_prompt:
        current_prompt = current_prompt.replace(old_regra, old_regra + "\n" + FLEX_INSTRUCTION)
        print("   Instrucao de fluxo flexivel adicionada.")
    else:
        print("   Nao encontrou ponto de insercao para fluxo flexivel.")
else:
    print("   Fluxo flexivel ja presente. Pulando.")

# Save patched prompt
wf["nodes"][sdr_idx]["parameters"]["options"]["systemMessage"] = current_prompt

# 3. Update LM nodes to gemini-2.5-flash
print("\n3. Updating LM nodes to gemini-2.5-flash...")
for node_id in [LM1_NODE_ID, LM2_NODE_ID, LM3_NODE_ID]:
    idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == node_id)
    wf["nodes"][idx]["parameters"]["modelName"] = "models/gemini-2.5-flash"
    print(f"   {wf['nodes'][idx]['name']} -> models/gemini-2.5-flash")

# 4. Deploy
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

# 5. Verify
print("\n5. Verificando...")
_, wf2 = api("GET", f"/api/v1/workflows/{WF_ID}")

sdr2 = next(n for n in wf2["nodes"] if n["id"] == SDR_NODE_ID)
sm = sdr2["parameters"]["options"]["systemMessage"]
print(f"   ClaudIA: {'ClaudIA' in sm}")
print(f"   Contexto temporal: {'CONTEXTO TEMPORAL' in sm}")
print(f"   Dia da semana (EEEE): {'EEEE' in sm}")
print(f"   Expressoes aceite: {'EXPRESS' in sm}")
print(f"   Pode ser como aceite: {'pode ser' in sm}")
print(f"   Fluxo flexivel: {'GUIA' in sm}")
print(f"   Clarificacao encerramento: {'similares' in sm}")

for node_id in [LM1_NODE_ID, LM2_NODE_ID, LM3_NODE_ID]:
    n = next(n for n in wf2["nodes"] if n["id"] == node_id)
    model = n["parameters"].get("modelName", "DEFAULT")
    print(f"   {n['name']}: {model}")

print(f"\n   Workflow active: {wf2['active']}")
print("\n" + "=" * 60)
print("DONE!")
print("=" * 60)
