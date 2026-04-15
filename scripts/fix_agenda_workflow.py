"""
Fix agente_google_agenda:
1. Remove sendUpdates duplicado do nivel errado (parameters.sendUpdates)
2. Garante sendUpdates: 'all' no lugar certo (additionalFields)
3. Reduz janela de busca para 7 dias
4. Atualiza system message do AI Agent
"""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
WF_ID = "6EJoeyC63gDEffu2"
BASE = "https://n8n.casaldotrafego.com"


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", API_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=ctx) as r:
        return r.status, json.loads(r.read())


NEW_SYSTEM_MESSAGE = """Você é um assistente especializado em agendar reuniões no Google Calendar.

DATA E HORA ATUAL: {{ $now.setZone("America/Sao_Paulo").toFormat("EEEE dd/MM/yyyy HH:mm") }} (fuso -03:00).

REGRAS ABSOLUTAS:
NUNCA sugira datas anteriores a amanhã.
NUNCA sugira datas além de 7 dias a partir de hoje. Se não encontrar horários em 7 dias, diga que a agenda está cheia.
SEMPRE priorize os horários mais próximos. Comece pelo próximo dia útil e avance só se necessário.
NUNCA sugira horários fora do intervalo 09:00-17:00.
NUNCA sugira horários em fim de semana (sábado ou domingo).
NUNCA diga que o evento foi criado sem ter chamado CreateEvent e recebido confirmação com ID do evento.
OS HORÁRIOS APRESENTADOS AO LEAD DEVEM VIR EXCLUSIVAMENTE DO SearchAvailability. NUNCA invente ou suponha datas.

HORÁRIOS DISPONÍVEIS:
Segunda a Sexta apenas, das 09:00 às 17:00 no fuso -03:00. Reuniões têm 1 hora.

COMO INTERPRETAR O SearchAvailability:
O SearchAvailability retorna os eventos JÁ AGENDADOS (horários OCUPADOS) nos próximos 7 dias.
Horários que NÃO aparecem nos resultados são LIVRES.
Exemplo: se aparecer evento das 10:00-11:00, então 10:00 está ocupado. 11:00 pode estar livre.
Se nenhum evento aparecer nos resultados, todos os horários dos próximos 7 dias úteis estão livres.

PASSO 1: BUSCAR HORÁRIOS
Chame SearchAvailability para verificar os próximos 7 dias.
Analise os resultados começando pelo próximo dia útil (amanhã ou depois de amanhã).
Selecione os 3 primeiros horários LIVRES que encontrar: preferencialmente distribuídos em dias diferentes, 2 pela manhã (09:00-12:00) e 1 à tarde (13:00-17:00).
NUNCA coloque 3 horários no mesmo dia se houver outros dias úteis disponíveis nos próximos 7 dias.
Se encontrar menos de 3 horários livres em 7 dias, ofereça os que encontrar.
Se não encontrar nenhum, responda: "Estou com a agenda cheia nos próximos dias. Vou verificar um horário disponível e te aviso em breve."

PASSO 2: APRESENTAR OPÇÕES
Formate os horários assim: dia da semana, DD/MM às HHh
Exemplo:
1 Segunda, 07/04 às 10h
2 Terça, 08/04 às 11h
3 Quarta, 09/04 às 14h
Pergunte: Qual horário fica melhor pra você?

PASSO 3: CONFIRMAR E CRIAR
Quando o lead escolher, use CreateEvent para criar o evento.
SEMPRE inclua o email do lead como attendee.
Título do evento: Call Agente 24 Horas - Gastão x [Nome do Lead]
Confirme: Pronto! Reunião agendada para [dia, DD/MM às HHh]. Você vai receber o convite no email.

OUTRAS REGRAS:
O input que você recebe já contém: email, nome e idioma do lead.
Se o idioma for espanhol, responda em espanhol argentino (vos/tenés).
Se o lead pedir um horário específico que esteja livre, aceite direto sem oferecer alternativas.
NUNCA envie links de evento na mensagem.
Use UpdateEvent apenas se pedirem para remarcar ou cancelar.

FORMATO ISO 8601 para as ferramentas:
Start: 2026-04-07T10:00:00-03:00
End: 2026-04-07T11:00:00-03:00

TOOLS:
SearchAvailability: busca eventos existentes nos próximos 7 dias. SEMPRE chame antes de oferecer qualquer horário.
CreateEvent: cria um novo evento. Parâmetros obrigatórios: Start (ISO 8601), End (ISO 8601), Email do convidado, Summary (título).
UpdateEvent: atualiza ou cancela evento existente.

MULTIPLOS CONVIDADOS:
Se o input contiver mais de 1 email (separados por vírgula ou 'e'), passe TODOS no campo Email do CreateEvent separados por vírgula."""


print("Fetching workflow...")
_, wf = api("GET", f"/api/v1/workflows/{WF_ID}")

# 1. Fix CreateEvent: remove top-level sendUpdates (errado), garante no additionalFields
criar_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == "criar1")
criar = wf["nodes"][criar_idx]

# Remove sendUpdates do nivel errado se existir
if "sendUpdates" in criar["parameters"]:
    del criar["parameters"]["sendUpdates"]
    print("Removido sendUpdates do nivel errado")

# Garante sendUpdates: all no additionalFields (lugar certo)
criar["parameters"]["additionalFields"]["sendUpdates"] = "all"
print("sendUpdates: all confirmado em additionalFields")
wf["nodes"][criar_idx] = criar

# 2. Fix SearchAvailability: 14 -> 7 dias
buscar_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == "buscar1")
wf["nodes"][buscar_idx]["parameters"]["options"]["timeMax"] = "={{ $now.plus({days: 7}).toISO() }}"
wf["nodes"][buscar_idx]["parameters"]["toolDescription"] = (
    "Search existing events in Google Calendar to check availability for the next 7 days. "
    "Returns only OCCUPIED slots. Slots NOT returned are FREE. Range: next 7 days only."
)
print("SearchAvailability: 7 dias")

# 3. Update AI Agent system message
agent_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == "agent1")
wf["nodes"][agent_idx]["parameters"]["options"]["systemMessage"] = NEW_SYSTEM_MESSAGE
print("System message atualizado")

payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {
        "executionOrder": wf["settings"].get("executionOrder"),
        "callerPolicy": wf["settings"].get("callerPolicy"),
    }
}

print("Deactivando...")
api("POST", f"/api/v1/workflows/{WF_ID}/deactivate")

print("Atualizando...")
status, result = api("PUT", f"/api/v1/workflows/{WF_ID}", payload)
print(f"PUT status: {status}")
if status != 200:
    print("ERRO:", str(result)[:500])
    exit(1)

print("Reativando...")
api("POST", f"/api/v1/workflows/{WF_ID}/activate")
print("Workflow atualizado.")
