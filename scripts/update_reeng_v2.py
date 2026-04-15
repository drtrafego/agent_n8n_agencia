"""
Follow-up workflow v2: limitar a 2 follow-ups para leads que nunca responderam.
Mudanças:
  - Buscar Leads: se last_lead_msg_at IS NULL, só pegar followup_count 0 e 1
  - Marcar Followup: se last_lead_msg_at IS NULL e followup_count+1 >= 2, marcar sem_interesse
"""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
WF_ID = "aBMaCWPodLaS8I6L"
BUSCAR_NODE_ID = "re-q"
MARCAR_NODE_ID = "re-upd"
BASE = "https://n8n.casaldotrafego.com"

NEW_BUSCAR_QUERY = r"""WITH eligible AS (
  SELECT c.id AS crm_contact_id, c.telefone AS phone,
    SPLIT_PART(SPLIT_PART(COALESCE(c.nome,''), '|', 1), ' ', 1) AS nome,
    c.stage,
    COALESCE(c.followup_count, 0) AS followup_count,
    COALESCE(c.observacoes_sdr, '') AS obs,
    COALESCE(c.nicho, '') AS nicho
  FROM contacts c
  JOIN wa_contacts wac ON wac.wa_id = c.telefone
  JOIN wa_conversations wc ON wc.contact_id = wac.id
  WHERE wc.bot_active = true AND wc.status = 'open'
    AND c.stage NOT IN ('agendado','agendou','fechou','perdido','sem_interesse','realizada')
    AND c.last_bot_msg_at IS NOT NULL
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
    AND (
      -- Lead que NUNCA respondeu: apenas follow-up 0 e 1
      (c.last_lead_msg_at IS NULL AND (
        (COALESCE(c.followup_count,0) = 0
          AND c.last_bot_msg_at < NOW() - INTERVAL '1 hour'
          AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')
        OR (COALESCE(c.followup_count,0) = 1
          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')
      ))
      OR
      -- Lead que JÁ respondeu: todos follow-ups 0 a 5
      (c.last_lead_msg_at IS NOT NULL AND (
        (COALESCE(c.followup_count,0) = 0
          AND c.last_bot_msg_at < NOW() - INTERVAL '1 hour'
          AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')
        OR (COALESCE(c.followup_count,0) = 1
          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')
        OR (COALESCE(c.followup_count,0) = 2
          AND c.last_bot_msg_at < NOW() - INTERVAL '12 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '24 hours')
        OR (COALESCE(c.followup_count,0) = 3
          AND c.last_bot_msg_at < NOW() - INTERVAL '24 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '48 hours')
        OR (COALESCE(c.followup_count,0) = 4
          AND c.last_bot_msg_at < NOW() - INTERVAL '48 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '60 hours')
        OR (COALESCE(c.followup_count,0) = 5
          AND c.last_bot_msg_at < NOW() - INTERVAL '60 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '72 hours')
      ))
    )
  LIMIT 20
),
reagend AS (
  SELECT c.id AS crm_contact_id, c.telefone AS phone,
    SPLIT_PART(SPLIT_PART(COALESCE(c.nome,''), '|', 1), ' ', 1) AS nome,
    c.stage,
    99 AS followup_count,
    COALESCE(c.observacoes_sdr, '') AS obs,
    COALESCE(c.nicho, '') AS nicho
  FROM contacts c
  JOIN wa_contacts wac ON wac.wa_id = c.telefone
  JOIN wa_conversations wc ON wc.contact_id = wac.id
  WHERE c.stage = 'agendado'
    AND c.scheduled_at IS NOT NULL
    AND c.scheduled_at < NOW() - INTERVAL '24 hours'
    AND wc.bot_active = true AND wc.status = 'open'
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
  LIMIT 10
)
SELECT crm_contact_id, phone, followup_count,
  CASE
    -- FOLLOW-UP 0: CURIOSIDADE (1h)
    WHEN followup_count = 0 AND LENGTH(nicho) > 0 THEN
      'Oi ' || TRIM(nome) || E'! Sabia que empresas que respondem em até 5 minutos têm 9 vezes mais chance de fechar? No segmento de ' || TRIM(nicho) || E' isso faz toda a diferença. Posso te mostrar como funciona na prática?'
    WHEN followup_count = 0 AND LENGTH(obs) >= 150 THEN
      'Oi ' || TRIM(nome) || E'! Vi que a gente já conversou um pouco. Empresas que respondem em até 5 minutos têm 9 vezes mais chance de fechar. O Agente faz isso por você 24 horas por dia. Quer ver como ficaria no seu caso?'
    WHEN followup_count = 0 THEN
      'Oi ' || TRIM(nome) || E'! Empresas que respondem em até 5 minutos têm 9 vezes mais chance de fechar. O Agente 24 Horas faz isso no seu WhatsApp, de dia ou de madrugada. Quer ver como funciona?'

    -- FOLLOW-UP 1: VALOR DIRETO (4h)
    WHEN followup_count = 1 AND LENGTH(nicho) > 0 THEN
      'Oi ' || TRIM(nome) || E'! O Agente de IA atende mais de 50 conversas ao mesmo tempo, sem fila e sem espera. Para ' || TRIM(nicho) || E', isso significa nunca mais perder um cliente por demora. São 30 minutos de call pra te mostrar ao vivo. Faz sentido?'
    WHEN followup_count = 1 AND LENGTH(obs) >= 150 THEN
      'Oi ' || TRIM(nome) || E'! Com base no que você me contou, o Agente resolveria o atendimento do seu negócio sem precisar contratar ninguém. Ele atende 24 horas, qualifica e agenda sozinho. Quer ver em 30 minutos como ficaria?'
    WHEN followup_count = 1 THEN
      'Oi ' || TRIM(nome) || E'! O Agente de IA absorve 80% das perguntas repetitivas e libera você pra focar no que realmente importa. Funciona 24 horas, 7 dias, sem folga. São 30 minutos pra te mostrar ao vivo. Quer ver?'

    -- FOLLOW-UP 2: PROVA SOCIAL (12h)
    WHEN followup_count = 2 AND LENGTH(nicho) > 0 THEN
      'Oi ' || TRIM(nome) || E'! Implementamos um agente para um negócio de ' || TRIM(nicho) || E' e em uma semana ele já estava qualificando leads e agendando reuniões no automático. Zero trabalho do dono. Quer que eu te mostre como ficaria no seu?'
    WHEN followup_count = 2 AND LENGTH(obs) >= 150 THEN
      'Oi ' || TRIM(nome) || E'! Um cliente nosso tinha o mesmo desafio que você me contou. Depois do Agente, os leads começaram a ser qualificados sozinhos e as reuniões agendadas no automático. Quer ver como ficaria no seu caso?'
    WHEN followup_count = 2 THEN
      'Oi ' || TRIM(nome) || E'! Um dos nossos clientes estava perdendo leads por não conseguir responder rápido. Em uma semana com o Agente, as reuniões já estavam sendo agendadas sozinhas. Quer ver como funciona?'

    -- FOLLOW-UP 3: URGÊNCIA (24h)
    WHEN followup_count = 3 AND LENGTH(nicho) > 0 THEN
      'Oi ' || TRIM(nome) || E'! Ainda tenho alguns horários essa semana pra te mostrar o Agente funcionando ao vivo para ' || TRIM(nicho) || E'. São 30 minutos e você sai sabendo exatamente como aplicar. Posso reservar um pra você?'
    WHEN followup_count = 3 AND LENGTH(obs) >= 150 THEN
      'Oi ' || TRIM(nome) || E'! Ainda tenho alguns horários essa semana. Na call de 30 minutos eu te mostro o Agente funcionando ao vivo no WhatsApp, personalizado pro seu caso. Posso reservar um pra você?'
    WHEN followup_count = 3 THEN
      'Oi ' || TRIM(nome) || E'! Ainda tenho alguns horários essa semana pra te mostrar o Agente funcionando ao vivo. São 30 minutos sem compromisso. Posso reservar um pra você?'

    -- FOLLOW-UP 4: PROVOCAÇÃO (48h)
    WHEN followup_count = 4 AND LENGTH(nicho) > 0 THEN
      'Oi ' || TRIM(nome) || E'! Cada dia sem responder rápido no WhatsApp são clientes indo pro concorrente. No segmento de ' || TRIM(nicho) || E' isso pesa. Se quiser ver o Agente funcionando, é só responder "quero".'
    WHEN followup_count = 4 AND LENGTH(obs) >= 150 THEN
      'Oi ' || TRIM(nome) || E'! Cada dia sem responder rápido no WhatsApp são clientes que vão embora. O Agente resolve isso em até 7 dias úteis, sem trabalho nenhum do seu lado. Se tiver interesse, é só responder "quero".'
    WHEN followup_count = 4 THEN
      'Oi ' || TRIM(nome) || E'! Cada dia sem responder rápido no WhatsApp são clientes que vão pro concorrente. O Agente 24 Horas resolve isso. Se quiser ver funcionando, é só responder "quero".'

    -- FOLLOW-UP 5: DESPEDIDA (60h)
    WHEN followup_count = 5 THEN
      'Oi ' || TRIM(nome) || E'! Última mensagem por aqui. Se no futuro quiser implementar um Agente de IA no seu negócio, é só me chamar. Desejo muito sucesso!'

    -- REAGENDAMENTO (24h+ após scheduled_at)
    WHEN followup_count = 99 THEN
      'Oi ' || TRIM(nome) || E'! Vi que tínhamos uma reunião agendada mas não conseguimos nos falar. Sem problemas! O Agente 24 Horas continua disponível pra você. Quer reagendar pra essa semana?'

    ELSE
      'Oi ' || TRIM(nome) || E'! Tudo bem? Ficou alguma dúvida sobre o Agente 24 Horas? Estou aqui pra te ajudar!'
  END AS body
FROM (
  SELECT * FROM eligible
  UNION ALL
  SELECT * FROM reagend
) leads"""

NEW_MARCAR_QUERY = r"""UPDATE contacts
SET followup_count = CASE
      WHEN {{ $('Buscar Leads').item.json.followup_count }} = 99 THEN 100
      ELSE COALESCE(followup_count, 0) + 1
    END,
    last_bot_msg_at = NOW(),
    stage = CASE
      WHEN {{ $('Buscar Leads').item.json.followup_count }} = 99 THEN stage
      WHEN last_lead_msg_at IS NULL AND COALESCE(followup_count, 0) + 1 >= 2 THEN 'sem_interesse'
      WHEN COALESCE(followup_count, 0) + 1 >= 6 THEN 'sem_interesse'
      ELSE stage
    END
WHERE id = {{ $('Buscar Leads').item.json.crm_contact_id }}"""


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", API_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=ctx) as r:
        return r.status, json.loads(r.read())


print("Fetching workflow...")
_, wf = api("GET", f"/api/v1/workflows/{WF_ID}")

# Atualizar Buscar Leads
buscar_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == BUSCAR_NODE_ID)
wf["nodes"][buscar_idx]["parameters"]["query"] = NEW_BUSCAR_QUERY
print("Buscar Leads atualizado")

# Atualizar Marcar Followup
marcar_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == MARCAR_NODE_ID)
wf["nodes"][marcar_idx]["parameters"]["query"] = NEW_MARCAR_QUERY
print("Marcar Followup atualizado")

payload = {
    "name": wf["name"],
    "nodes": wf["nodes"],
    "connections": wf["connections"],
    "settings": {
        "executionOrder": wf["settings"].get("executionOrder"),
        "callerPolicy": wf["settings"].get("callerPolicy"),
    }
}

print("Deactivating...")
api("POST", f"/api/v1/workflows/{WF_ID}/deactivate")

print("Updating...")
status, result = api("PUT", f"/api/v1/workflows/{WF_ID}", payload)
print(f"PUT status: {status}")
if status != 200:
    print("ERRO:", str(result)[:500])
    exit(1)

print("Reactivating...")
api("POST", f"/api/v1/workflows/{WF_ID}/activate")

print("\nVerificando...")
_, wf2 = api("GET", f"/api/v1/workflows/{WF_ID}")
buscar2 = next(n for n in wf2["nodes"] if n["id"] == BUSCAR_NODE_ID)
marcar2 = next(n for n in wf2["nodes"] if n["id"] == MARCAR_NODE_ID)
bq = buscar2["parameters"]["query"]
mq = marcar2["parameters"]["query"]
print(f"Buscar: split por last_lead_msg_at: {'last_lead_msg_at IS NULL AND (' in bq}")
print(f"Buscar: respondeu pega todos: {'last_lead_msg_at IS NOT NULL AND (' in bq}")
print(f"Marcar: sem_interesse >= 2 p/ NULL: {'last_lead_msg_at IS NULL AND COALESCE(followup_count, 0) + 1 >= 2' in mq}")
print(f"Marcar: sem_interesse >= 6 p/ respondeu: {'COALESCE(followup_count, 0) + 1 >= 6' in mq}")
print(f"Ativo: {wf2['active']}")
print("\nDone! Follow-up v2 ativo.")
