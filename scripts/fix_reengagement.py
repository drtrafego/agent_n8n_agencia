# -*- coding: utf-8 -*-
"""
Fix reengagement workflow: move message selection to SQL.
n8n cannot handle IIFEs or complex Switch/Set via API.
Solution: SQL returns phone + body directly, workflow just sends and updates.
Only uses: scheduleTrigger, webhook, postgres, httpRequest, wait, noOp (all safe for API).
"""
import urllib.request, json, ssl

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
WF_ID = "aBMaCWPodLaS8I6L"
PG = {"id": "qjAlzv5GyfH3869u", "name": "Postgres agent-n8n-agencia"}
BASE = "https://n8n.casaldotrafego.com"

# SQL that returns phone, crm_contact_id, followup_count, AND the message body
# Message is built in SQL using CASE WHEN, avoiding n8n expression complexity
SQL_LEADS = """
WITH eligible AS (
  SELECT c.id AS crm_contact_id, c.telefone AS phone,
    SPLIT_PART(SPLIT_PART(COALESCE(c.nome,''), '|', 1), ' ', 1) AS nome,
    c.stage,
    COALESCE(c.followup_count, 0) AS followup_count,
    COALESCE(c.observacoes_sdr, '') AS obs
  FROM contacts c
  JOIN wa_contacts wac ON wac.wa_id = c.telefone
  JOIN wa_conversations wc ON wc.contact_id = wac.id
  WHERE wc.bot_active = true AND wc.status = 'open'
    AND c.stage NOT IN ('agendado','agendou','fechou','perdido','sem_interesse','realizada')
    AND c.last_bot_msg_at IS NOT NULL
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
    AND (
      (COALESCE(c.followup_count,0) = 0
        AND c.last_bot_msg_at < NOW() - INTERVAL '30 minutes'
        AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')
      OR (COALESCE(c.followup_count,0) = 1
        AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'
        AND c.last_bot_msg_at > NOW() - INTERVAL '24 hours')
      OR (COALESCE(c.followup_count,0) = 2
        AND c.last_bot_msg_at < NOW() - INTERVAL '24 hours'
        AND c.last_bot_msg_at > NOW() - INTERVAL '48 hours')
      OR (COALESCE(c.followup_count,0) = 3
        AND c.last_bot_msg_at < NOW() - INTERVAL '48 hours'
        AND c.last_bot_msg_at > NOW() - INTERVAL '60 hours')
      OR (COALESCE(c.followup_count,0) = 4
        AND c.last_bot_msg_at < NOW() - INTERVAL '60 hours'
        AND c.last_bot_msg_at > NOW() - INTERVAL '72 hours')
    )
  LIMIT 20
),
reagend AS (
  SELECT c.id AS crm_contact_id, c.telefone AS phone,
    SPLIT_PART(SPLIT_PART(COALESCE(c.nome,''), '|', 1), ' ', 1) AS nome,
    c.stage,
    99 AS followup_count,
    COALESCE(c.observacoes_sdr, '') AS obs
  FROM contacts c
  JOIN wa_contacts wac ON wac.wa_id = c.telefone
  JOIN wa_conversations wc ON wc.contact_id = wac.id
  WHERE c.stage = 'agendado'
    AND c.stage_updated_at IS NOT NULL
    AND c.stage_updated_at < NOW() - INTERVAL '36 hours'
    AND wc.bot_active = true AND wc.status = 'open'
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
  LIMIT 10
)
SELECT crm_contact_id, phone, followup_count,
  CASE
    WHEN followup_count = 0 AND LENGTH(obs) >= 20 THEN
      'Oi ' || TRIM(nome) || E'! Vi que estávamos conversando. Ficou alguma d\u00favida que posso te ajudar a esclarecer sobre o Agente de IA?'
    WHEN followup_count = 0 THEN
      'Oi ' || TRIM(nome) || E'! Para eu te mostrar de forma pr\u00e1tica como funciona no seu caso, me conta: seu neg\u00f3cio \u00e9 mais voltado para sa\u00fade, servi\u00e7os, im\u00f3veis, varejo ou outro segmento?'
    WHEN followup_count = 1 AND LENGTH(obs) >= 20 THEN
      'Oi ' || TRIM(nome) || E'! Vi que voc\u00ea j\u00e1 me contou um pouco sobre o seu neg\u00f3cio. Faz sentido reservarmos 15 minutinhos essa semana para te mostrar exatamente como o Agente de IA funcionaria no seu caso?'
    WHEN followup_count = 1 THEN
      'Oi ' || TRIM(nome) || E'! Vi que voc\u00ea se interessou no Agente de IA. A gente treina o agente com o seu neg\u00f3cio e entrega tudo pronto no seu WhatsApp. Zero trabalho do seu lado. Quer ver um caso do seu segmento?'
    WHEN followup_count = 2 AND LENGTH(obs) >= 20 THEN
      'Oi ' || TRIM(nome) || E'! Ainda tenho hor\u00e1rios essa semana para te mostrar o Agente funcionando ao vivo. S\u00e3o 15 minutos e voc\u00ea j\u00e1 sai com uma vis\u00e3o clara de como aplicar no seu neg\u00f3cio. Posso reservar um pra voc\u00ea?'
    WHEN followup_count = 2 THEN
      'Oi ' || TRIM(nome) || E'! O Agente de IA \u00e9 como ter um vendedor que nunca dorme, nunca falta e custa menos que um funcion\u00e1rio. Nossos clientes est\u00e3o qualificando leads e agendando reuni\u00f5es no piloto autom\u00e1tico. Faz sentido conversarmos?'
    WHEN followup_count = 3 THEN
      'Oi ' || TRIM(nome) || E'! Ainda tenho uns hor\u00e1rios essa semana pra te mostrar o Agente funcionando ao vivo no WhatsApp. S\u00e3o 15 minutos e voc\u00ea j\u00e1 sai sabendo exatamente como aplicar no seu neg\u00f3cio. Posso reservar um pra voc\u00ea?'
    WHEN followup_count = 4 THEN
      'Oi ' || TRIM(nome) || E'! \u00daltima mensagem por aqui. Se no futuro quiser implementar um Agente de IA no seu neg\u00f3cio, \u00e9 s\u00f3 me chamar. Desejo muito sucesso!'
    WHEN followup_count = 99 THEN
      'Oi ' || TRIM(nome) || E'! Tudo bem? Vi que t\u00ednhamos uma reuni\u00e3o agendada mas n\u00e3o conseguimos nos falar. Sem problemas! O Agente 24 Horas continua dispon\u00edvel pra voc\u00ea. Quer reagendar pra essa semana?'
    ELSE
      'Oi ' || TRIM(nome) || E'! Tudo bem? Ficou alguma d\u00favida sobre o Agente 24 Horas? Estou aqui pra te ajudar!'
  END AS body
FROM (
  SELECT * FROM eligible
  UNION ALL
  SELECT * FROM reagend
) leads;
"""

SQL_UPDATE = (
    "UPDATE contacts SET "
    "followup_count = CASE WHEN {{ $('Buscar Leads').item.json.followup_count }} = 99 THEN 100 "
    "ELSE COALESCE(followup_count, 0) + 1 END, "
    "last_bot_msg_at = NOW(), "
    "stage = CASE WHEN {{ $('Buscar Leads').item.json.followup_count }} = 99 THEN stage "
    "WHEN COALESCE(followup_count, 0) + 1 >= 5 THEN 'sem_interesse' "
    "ELSE stage END "
    "WHERE id = {{ $('Buscar Leads').item.json.crm_contact_id }};"
)

workflow = {
    "name": "reengagement agent_n8n_agencia",
    "settings": {"executionOrder": "v1", "callerPolicy": "workflowsFromSameOwner", "availableInMCP": True},
    "nodes": [
        {
            "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "*/30 * * * *"}]}},
            "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2,
            "position": [-200, 300], "id": "re-cron", "name": "Trigger 30min"
        },
        {
            "parameters": {"httpMethod": "POST", "path": "reengagement-test-run", "responseMode": "lastNode", "options": {}},
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [-200, 60], "id": "re-wh", "name": "Webhook Teste", "webhookId": "re-wh-001", "disabled": True
        },
        {
            "parameters": {"operation": "executeQuery", "query": SQL_LEADS, "options": {}},
            "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
            "position": [120, 180], "id": "re-q", "name": "Buscar Leads",
            "credentials": {"postgres": PG},
            "alwaysOutputData": False,
            "onError": "continueRegularOutput"
        },
        {
            "parameters": {
                "method": "POST",
                "url": "https://agente.casaldotrafego.com/api/whatsapp/bot-send",
                "sendBody": True,
                "specifyBody": "json",
                "jsonBody": '={{ JSON.stringify({phone: $json.phone, body: $json.body}) }}',
                "options": {}
            },
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [440, 180], "id": "re-send", "name": "Enviar Msg",
            "onError": "continueRegularOutput"
        },
        {
            "parameters": {"amount": 3, "unit": "seconds"},
            "type": "n8n-nodes-base.wait", "typeVersion": 1.1,
            "position": [700, 180], "id": "re-wait", "name": "Esperar 3s"
        },
        {
            "parameters": {"operation": "executeQuery", "query": SQL_UPDATE, "options": {}},
            "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
            "position": [960, 180], "id": "re-upd", "name": "Marcar Followup",
            "credentials": {"postgres": PG}
        },
        {
            "parameters": {},
            "type": "n8n-nodes-base.noOp", "typeVersion": 1,
            "position": [1220, 180], "id": "re-end", "name": "Concluido"
        }
    ],
    "connections": {
        "Trigger 30min": {"main": [[{"node": "Buscar Leads", "type": "main", "index": 0}]]},
        "Webhook Teste": {"main": [[{"node": "Buscar Leads", "type": "main", "index": 0}]]},
        "Buscar Leads": {"main": [[{"node": "Enviar Msg", "type": "main", "index": 0}]]},
        "Enviar Msg": {"main": [[{"node": "Esperar 3s", "type": "main", "index": 0}]]},
        "Esperar 3s": {"main": [[{"node": "Marcar Followup", "type": "main", "index": 0}]]},
        "Marcar Followup": {"main": [[{"node": "Concluido", "type": "main", "index": 0}]]}
    }
}

# --- Update via PUT ---
body = json.dumps(workflow).encode()
req = urllib.request.Request(
    f"{BASE}/api/v1/workflows/{WF_ID}",
    data=body, method="PUT",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    result = json.loads(resp.read().decode())
    print("ATUALIZADO! ID:", result.get("id"))
    print("Nome:", result.get("name"))
    print("Nodes:", len(result.get("nodes", [])))
    print("Active:", result.get("active"))

    # Re-activate
    activate_body = json.dumps({"active": True}).encode()
    req2 = urllib.request.Request(
        f"{BASE}/api/v1/workflows/{WF_ID}",
        data=activate_body, method="PATCH",
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
    )
    resp2 = urllib.request.urlopen(req2, context=ctx, timeout=10)
    result2 = json.loads(resp2.read().decode())
    print("Reativado! Active:", result2.get("active"))
    print()
    print("URL: https://n8n.casaldotrafego.com/workflow/" + WF_ID)

except urllib.error.HTTPError as e:
    print("ERRO:", e.code, e.read().decode()[:1000])
