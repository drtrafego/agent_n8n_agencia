# -*- coding: utf-8 -*-
import urllib.request, json, ssl, time

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
PG_CRED = {"id": "qjAlzv5GyfH3869u", "name": "Postgres agent-n8n-agencia"}

# Delete old workflow if exists
try:
    req = urllib.request.Request(
        "https://n8n.casaldotrafego.com/api/v1/workflows/1iTYl9M0zocdo04j",
        method="DELETE", headers={"X-N8N-API-KEY": API_KEY}
    )
    urllib.request.urlopen(req, context=ctx)
    print("Workflow antigo deletado")
except:
    print("Workflow antigo ja nao existe")

SQL_QUERY = """SELECT
  c.id AS crm_contact_id,
  c.telefone AS phone,
  c.nome,
  c.stage,
  c.observacoes_sdr,
  COALESCE(c.followup_count, 0) AS followup_count,
  wc.id AS conversation_id,
  wc.last_message,
  wc.last_message_at
FROM contacts c
JOIN wa_contacts wac ON wac.wa_id = c.telefone
JOIN wa_conversations wc ON wc.contact_id = wac.id
WHERE wc.bot_active = true
  AND wc.status = 'open'
  AND c.stage NOT IN ('agendado', 'agendou', 'fechou', 'perdido')
  AND COALESCE(c.followup_count, 0) < 3
  AND c.last_bot_msg_at IS NOT NULL
  AND c.last_bot_msg_at < NOW() - INTERVAL '12 hours'
  AND c.last_bot_msg_at > NOW() - INTERVAL '72 hours'
  AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
ORDER BY c.last_bot_msg_at ASC
LIMIT 20;"""

UPDATE_SQL = """UPDATE contacts
SET followup_count = COALESCE(followup_count, 0) + 1,
    last_bot_msg_at = NOW(),
    observacoes_sdr = COALESCE(observacoes_sdr, '') || chr(10) || 'Followup #' || (COALESCE(followup_count, 0) + 1)::text || ' enviado em ' || TO_CHAR(NOW() AT TIME ZONE 'America/Sao_Paulo', 'DD/MM/YYYY HH24:MI') || '.'
WHERE id = {{ $json.crm_contact_id }};"""

MSG_NOVO = '={{ ["Oi " + ($json.nome || "").split("|")[0].trim() + "! Vi que voce se interessou pelo Agente de IA. Posso te explicar rapidinho como funciona? Leva menos de 2 minutos!", "Oi " + ($json.nome || "").split("|")[0].trim() + "! Ainda quer saber como um Agente de IA pode ajudar seu negocio? Estou aqui pra te mostrar!", "E ai " + ($json.nome || "").split("|")[0].trim() + "! Tudo bem? Ficou com alguma duvida sobre o Agente de IA? Me conta que te ajudo!"][Math.floor(Math.random() * 3)] }}'

MSG_QUALIF = '={{ ["Oi " + ($json.nome || "").split("|")[0].trim() + "! Estivemos conversando sobre como o Agente de IA pode ajudar no seu negocio. Quer agendar uma demonstracao rapida?", "Oi " + ($json.nome || "").split("|")[0].trim() + "! Fiquei pensando no que conversamos. Que tal agendarmos 15 minutinhos pra eu te mostrar o Agente ao vivo?", "E ai " + ($json.nome || "").split("|")[0].trim() + "! Ainda pensando sobre o Agente de IA? Posso te mandar um exemplo pratico do seu nicho!"][Math.floor(Math.random() * 3)] }}'

MSG_OUTROS = '={{ ["Oi " + ($json.nome || "").split("|")[0].trim() + "! Tudo certo? Ficou alguma duvida sobre nosso Agente de IA? Estou aqui!", "Oi " + ($json.nome || "").split("|")[0].trim() + "! Passando pra ver se posso te ajudar com mais alguma info sobre o Agente de IA.", "E ai " + ($json.nome || "").split("|")[0].trim() + "! Se quiser, posso te mostrar como o Agente funciona na pratica!"][Math.floor(Math.random() * 3)] }}'

workflow = {
    "name": "reengagement agent_n8n_agencia",
    "settings": {"executionOrder": "v1"},
    "nodes": [
        {
            "parameters": {
                "rule": {"interval": [{"field": "cronExpression", "expression": "0 13 * * *"}]}
            },
            "name": "Trigger 10h BRT",
            "type": "n8n-nodes-base.scheduleTrigger",
            "typeVersion": 1.2,
            "position": [-1400, 300]
        },
        {
            "parameters": {
                "httpMethod": "POST",
                "path": "reengagement-run-x7k9",
                "responseMode": "lastNode",
                "options": {}
            },
            "name": "Webhook Teste",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2,
            "position": [-1400, 60],
            "webhookId": "reengagement-run-x7k9"
        },
        {
            "parameters": {
                "operation": "executeQuery",
                "query": SQL_QUERY,
                "options": {}
            },
            "name": "Buscar Leads Elegiveis",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [-1060, 180],
            "credentials": {"postgres": PG_CRED}
        },
        {
            "parameters": {
                "conditions": {
                    "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                    "conditions": [
                        {"id": "f1", "leftValue": "={{ $json.phone }}", "rightValue": "", "operator": {"type": "string", "operation": "isNotEmpty"}}
                    ],
                    "combinator": "and"
                }
            },
            "name": "Tem Leads?",
            "type": "n8n-nodes-base.filter",
            "typeVersion": 2,
            "position": [-780, 180]
        },
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {"id": "s1", "name": "phone", "value": "={{ $json.phone }}", "type": "string"},
                        {"id": "s2", "name": "nome", "value": "={{ $json.nome }}", "type": "string"},
                        {"id": "s3", "name": "stage", "value": "={{ $json.stage }}", "type": "string"},
                        {"id": "s4", "name": "observacoes", "value": "={{ $json.observacoes_sdr }}", "type": "string"},
                        {"id": "s5", "name": "last_message", "value": "={{ $json.last_message }}", "type": "string"},
                        {"id": "s6", "name": "crm_contact_id", "value": "={{ $json.crm_contact_id }}", "type": "number"},
                        {"id": "s7", "name": "followup_count", "value": "={{ $json.followup_count }}", "type": "number"}
                    ]
                },
                "options": {}
            },
            "name": "Preparar Dados",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [-500, 180]
        },
        {
            "parameters": {
                "rules": {
                    "values": [
                        {"outputIndex": 0, "conditions": {"conditions": [{"leftValue": "={{ $json.stage }}", "rightValue": "novo", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}},
                        {"outputIndex": 1, "conditions": {"conditions": [{"leftValue": "={{ $json.stage }}", "rightValue": "qualificando", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}}
                    ],
                    "fallbackOutput": 2
                },
                "options": {}
            },
            "name": "Qual Etapa?",
            "type": "n8n-nodes-base.switch",
            "typeVersion": 3.2,
            "position": [-200, 180]
        },
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {"id": "m1", "name": "body", "value": MSG_NOVO, "type": "string"},
                        {"id": "m1p", "name": "phone", "value": "={{ $json.phone }}", "type": "string"},
                        {"id": "m1c", "name": "crm_contact_id", "value": "={{ $json.crm_contact_id }}", "type": "number"},
                        {"id": "m1f", "name": "followup_count", "value": "={{ $json.followup_count }}", "type": "number"}
                    ]
                },
                "options": {}
            },
            "name": "Msg Novo Lead",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [120, -20]
        },
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {"id": "m2", "name": "body", "value": MSG_QUALIF, "type": "string"},
                        {"id": "m2p", "name": "phone", "value": "={{ $json.phone }}", "type": "string"},
                        {"id": "m2c", "name": "crm_contact_id", "value": "={{ $json.crm_contact_id }}", "type": "number"},
                        {"id": "m2f", "name": "followup_count", "value": "={{ $json.followup_count }}", "type": "number"}
                    ]
                },
                "options": {}
            },
            "name": "Msg Qualificando",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [120, 200]
        },
        {
            "parameters": {
                "assignments": {
                    "assignments": [
                        {"id": "m3", "name": "body", "value": MSG_OUTROS, "type": "string"},
                        {"id": "m3p", "name": "phone", "value": "={{ $json.phone }}", "type": "string"},
                        {"id": "m3c", "name": "crm_contact_id", "value": "={{ $json.crm_contact_id }}", "type": "number"},
                        {"id": "m3f", "name": "followup_count", "value": "={{ $json.followup_count }}", "type": "number"}
                    ]
                },
                "options": {}
            },
            "name": "Msg Outros",
            "type": "n8n-nodes-base.set",
            "typeVersion": 3.4,
            "position": [120, 420]
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
            "name": "Enviar Reengagement",
            "type": "n8n-nodes-base.httpRequest",
            "typeVersion": 4.2,
            "position": [440, 200]
        },
        {
            "parameters": {"amount": 3, "unit": "seconds"},
            "name": "Esperar 3s",
            "type": "n8n-nodes-base.wait",
            "typeVersion": 1.1,
            "position": [700, 200]
        },
        {
            "parameters": {
                "operation": "executeQuery",
                "query": UPDATE_SQL,
                "options": {}
            },
            "name": "Marcar Followup",
            "type": "n8n-nodes-base.postgres",
            "typeVersion": 2.5,
            "position": [960, 200],
            "credentials": {"postgres": PG_CRED}
        },
        {
            "parameters": {},
            "name": "Concluido",
            "type": "n8n-nodes-base.noOp",
            "typeVersion": 1,
            "position": [1220, 200]
        }
    ],
    "connections": {
        "Trigger 10h BRT": {"main": [[{"node": "Buscar Leads Elegiveis", "type": "main", "index": 0}]]},
        "Webhook Teste": {"main": [[{"node": "Buscar Leads Elegiveis", "type": "main", "index": 0}]]},
        "Buscar Leads Elegiveis": {"main": [[{"node": "Tem Leads?", "type": "main", "index": 0}]]},
        "Tem Leads?": {"main": [[{"node": "Preparar Dados", "type": "main", "index": 0}]]},
        "Preparar Dados": {"main": [[{"node": "Qual Etapa?", "type": "main", "index": 0}]]},
        "Qual Etapa?": {"main": [
            [{"node": "Msg Novo Lead", "type": "main", "index": 0}],
            [{"node": "Msg Qualificando", "type": "main", "index": 0}],
            [{"node": "Msg Outros", "type": "main", "index": 0}]
        ]},
        "Msg Novo Lead": {"main": [[{"node": "Enviar Reengagement", "type": "main", "index": 0}]]},
        "Msg Qualificando": {"main": [[{"node": "Enviar Reengagement", "type": "main", "index": 0}]]},
        "Msg Outros": {"main": [[{"node": "Enviar Reengagement", "type": "main", "index": 0}]]},
        "Enviar Reengagement": {"main": [[{"node": "Esperar 3s", "type": "main", "index": 0}]]},
        "Esperar 3s": {"main": [[{"node": "Marcar Followup", "type": "main", "index": 0}]]},
        "Marcar Followup": {"main": [[{"node": "Concluido", "type": "main", "index": 0}]]}
    }
}

body = json.dumps(workflow).encode()
req = urllib.request.Request(
    "https://n8n.casaldotrafego.com/api/v1/workflows",
    data=body, method="POST",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
)
try:
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    result = json.loads(resp.read().decode())
    wf_id = result.get("id")
    print("Workflow criado!")
    print("ID:", wf_id)
    print("Nome:", result.get("name"))
    print("Nodes:", len(result.get("nodes", [])))
    for n in result.get("nodes", []):
        print("  %s: pos=%s" % (n["name"], n.get("position")))

    # Now activate it
    print("\nAtivando workflow...")
    activate_url = "https://n8n.casaldotrafego.com/api/v1/workflows/%s" % wf_id
    req2 = urllib.request.Request(activate_url, headers={"X-N8N-API-KEY": API_KEY})
    resp2 = urllib.request.urlopen(req2, context=ctx)
    current = json.loads(resp2.read().decode())

    # PUT with active=true
    current["active"] = True
    # Remove fields that cause issues
    for key in ["createdAt", "updatedAt", "id", "versionId", "tags"]:
        current.pop(key, None)
    body2 = json.dumps(current).encode()
    req3 = urllib.request.Request(activate_url, data=body2, method="PUT",
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"})
    resp3 = urllib.request.urlopen(req3, context=ctx)
    res3 = json.loads(resp3.read().decode())
    print("Active:", res3.get("active"))

    # Test webhook trigger
    print("\n--- TESTANDO via webhook ---")
    webhook_url = "https://n8n.casaldotrafego.com/webhook/reengagement-run-x7k9"
    req4 = urllib.request.Request(webhook_url, data=b'{"test": true}', method="POST",
        headers={"Content-Type": "application/json"})
    try:
        resp4 = urllib.request.urlopen(req4, context=ctx, timeout=60)
        result4 = resp4.read().decode()
        print("Resposta webhook:", result4[:500])
    except urllib.error.HTTPError as e:
        print("Erro webhook %d: %s" % (e.code, e.read().decode()[:300]))
    except Exception as e:
        print("Erro webhook:", e)

except urllib.error.HTTPError as e:
    err = e.read().decode()
    print("Erro HTTP %d: %s" % (e.code, err[:500]))
except Exception as e:
    print("Erro:", e)
