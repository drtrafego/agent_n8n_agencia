# -*- coding: utf-8 -*-
import urllib.request, json, ssl

ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
PG = {"id": "qjAlzv5GyfH3869u", "name": "Postgres agent-n8n-agencia"}

# Clean up leftovers
url = "https://n8n.casaldotrafego.com/api/v1/workflows?limit=50"
req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
resp = urllib.request.urlopen(req, context=ctx)
for wf in json.loads(resp.read().decode()).get("data", []):
    if wf["name"] in ["My workflow", "reengagement agent_n8n_agencia"]:
        try:
            r = urllib.request.Request("https://n8n.casaldotrafego.com/api/v1/workflows/" + wf["id"], method="DELETE", headers={"X-N8N-API-KEY": API_KEY})
            urllib.request.urlopen(r, context=ctx)
            print("Deletado:", wf["name"], wf["id"])
        except:
            pass

# Build workflow - EXACTLY like Watchdog format (simple string IDs, same settings)
e = "={{ $json."  # expression prefix

SQL = (
    "SELECT c.id AS crm_contact_id, c.telefone AS phone, c.nome, c.stage, "
    "COALESCE(c.followup_count,0) AS followup_count "
    "FROM contacts c "
    "JOIN wa_contacts wac ON wac.wa_id=c.telefone "
    "JOIN wa_conversations wc ON wc.contact_id=wac.id "
    "WHERE wc.bot_active=true AND wc.status='open' "
    "AND c.stage NOT IN('agendado','agendou','fechou','perdido') "
    "AND COALESCE(c.followup_count,0)<3 "
    "AND c.last_bot_msg_at IS NOT NULL "
    "AND c.last_bot_msg_at<NOW()-INTERVAL '12 hours' "
    "AND c.last_bot_msg_at>NOW()-INTERVAL '72 hours' "
    "AND(c.last_lead_msg_at IS NULL OR c.last_lead_msg_at<c.last_bot_msg_at) "
    "LIMIT 20;"
)

UPD = "UPDATE contacts SET followup_count=COALESCE(followup_count,0)+1,last_bot_msg_at=NOW() WHERE id={{ $json.crm_contact_id }};"

workflow = {
    "name": "reengagement agent_n8n_agencia",
    "settings": {"executionOrder": "v1", "callerPolicy": "workflowsFromSameOwner", "availableInMCP": False},
    "nodes": [
        {
            "parameters": {"rule": {"interval": [{"field": "cronExpression", "expression": "0 13 * * *"}]}},
            "type": "n8n-nodes-base.scheduleTrigger", "typeVersion": 1.2,
            "position": [-1400, 300], "id": "re-schedule", "name": "Trigger 10h BRT"
        },
        {
            "parameters": {"httpMethod": "POST", "path": "reengagement-run-x7k9", "responseMode": "lastNode", "options": {}},
            "type": "n8n-nodes-base.webhook", "typeVersion": 2,
            "position": [-1400, 60], "id": "re-webhook", "name": "Webhook Teste", "webhookId": "re-webhook-id"
        },
        {
            "parameters": {"operation": "executeQuery", "query": SQL, "options": {}},
            "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
            "position": [-1060, 180], "id": "re-query", "name": "Buscar Leads Elegiveis",
            "credentials": {"postgres": PG}
        },
        {
            "parameters": {"conditions": {"options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"}, "conditions": [{"id": "re-f1", "leftValue": e + "phone }}", "rightValue": "", "operator": {"type": "string", "operation": "isNotEmpty"}}], "combinator": "and"}},
            "type": "n8n-nodes-base.filter", "typeVersion": 2,
            "position": [-780, 180], "id": "re-filter", "name": "Tem Leads?"
        },
        {
            "parameters": {"assignments": {"assignments": [
                {"id": "re-s1", "name": "phone", "value": e + "phone }}", "type": "string"},
                {"id": "re-s2", "name": "nome", "value": e + "nome }}", "type": "string"},
                {"id": "re-s3", "name": "stage", "value": e + "stage }}", "type": "string"},
                {"id": "re-s4", "name": "crm_contact_id", "value": e + "crm_contact_id }}", "type": "number"},
                {"id": "re-s5", "name": "followup_count", "value": e + "followup_count }}", "type": "number"}
            ]}, "options": {}},
            "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": [-500, 180], "id": "re-set", "name": "Preparar Dados"
        },
        {
            "parameters": {"rules": {"values": [
                {"id": "re-r1", "outputIndex": 0, "conditions": {"conditions": [{"id": "re-rc1", "leftValue": e + 'stage }}', "rightValue": "novo", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}},
                {"id": "re-r2", "outputIndex": 1, "conditions": {"conditions": [{"id": "re-rc2", "leftValue": e + 'stage }}', "rightValue": "qualificando", "operator": {"type": "string", "operation": "equals"}}], "combinator": "and"}}
            ], "fallbackOutput": 2}, "options": {}},
            "type": "n8n-nodes-base.switch", "typeVersion": 3.2,
            "position": [-200, 180], "id": "re-switch", "name": "Qual Etapa?"
        },
        {
            "parameters": {"assignments": {"assignments": [
                {"id": "re-n1", "name": "body", "value": '={{ "Oi " + ($json.nome||"").split("|")[0].trim() + "! Vi que voce se interessou pelo Agente de IA. Posso te explicar?" }}', "type": "string"},
                {"id": "re-n2", "name": "phone", "value": e + "phone }}", "type": "string"},
                {"id": "re-n3", "name": "crm_contact_id", "value": e + "crm_contact_id }}", "type": "number"}
            ]}, "options": {}},
            "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": [120, -20], "id": "re-msg1", "name": "Msg Novo Lead"
        },
        {
            "parameters": {"assignments": {"assignments": [
                {"id": "re-q1", "name": "body", "value": '={{ "Oi " + ($json.nome||"").split("|")[0].trim() + "! Quer agendar uma demonstracao do Agente de IA?" }}', "type": "string"},
                {"id": "re-q2", "name": "phone", "value": e + "phone }}", "type": "string"},
                {"id": "re-q3", "name": "crm_contact_id", "value": e + "crm_contact_id }}", "type": "number"}
            ]}, "options": {}},
            "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": [120, 200], "id": "re-msg2", "name": "Msg Qualificando"
        },
        {
            "parameters": {"assignments": {"assignments": [
                {"id": "re-o1", "name": "body", "value": '={{ "Oi " + ($json.nome||"").split("|")[0].trim() + "! Ficou alguma duvida sobre o Agente de IA?" }}', "type": "string"},
                {"id": "re-o2", "name": "phone", "value": e + "phone }}", "type": "string"},
                {"id": "re-o3", "name": "crm_contact_id", "value": e + "crm_contact_id }}", "type": "number"}
            ]}, "options": {}},
            "type": "n8n-nodes-base.set", "typeVersion": 3.4,
            "position": [120, 420], "id": "re-msg3", "name": "Msg Outros"
        },
        {
            "parameters": {"method": "POST", "url": "https://agente.casaldotrafego.com/api/whatsapp/bot-send", "sendBody": True, "specifyBody": "json", "jsonBody": '={{ JSON.stringify({phone:$json.phone,body:$json.body}) }}', "options": {}},
            "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
            "position": [440, 200], "id": "re-send", "name": "Enviar Reengagement"
        },
        {
            "parameters": {"amount": 3, "unit": "seconds"},
            "type": "n8n-nodes-base.wait", "typeVersion": 1.1,
            "position": [700, 200], "id": "re-wait", "name": "Esperar 3s"
        },
        {
            "parameters": {"operation": "executeQuery", "query": UPD, "options": {}},
            "type": "n8n-nodes-base.postgres", "typeVersion": 2.5,
            "position": [960, 200], "id": "re-update", "name": "Marcar Followup",
            "credentials": {"postgres": PG}
        },
        {
            "parameters": {},
            "type": "n8n-nodes-base.noOp", "typeVersion": 1,
            "position": [1220, 200], "id": "re-end", "name": "Concluido"
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
req2 = urllib.request.Request(
    "https://n8n.casaldotrafego.com/api/v1/workflows",
    data=body, method="POST",
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
)
try:
    resp2 = urllib.request.urlopen(req2, context=ctx, timeout=30)
    result = json.loads(resp2.read().decode())
    wf_id = result.get("id")
    print("CRIADO! ID:", wf_id)
    print("Nome:", result.get("name"))
    print("Nodes:", len(result.get("nodes", [])))
    shared = result.get("shared", [])
    print("Shared:", json.dumps(shared)[:300] if shared else "empty")

    # Now verify we can read it back
    req3 = urllib.request.Request("https://n8n.casaldotrafego.com/api/v1/workflows/" + wf_id, headers={"X-N8N-API-KEY": API_KEY})
    resp3 = urllib.request.urlopen(req3, context=ctx)
    verify = json.loads(resp3.read().decode())
    print("Verified nodes:", len(verify.get("nodes", [])))
    print("Verified shared:", json.dumps(verify.get("shared", []))[:200])
    print()
    print("URL: https://n8n.casaldotrafego.com/workflow/" + wf_id)

except urllib.error.HTTPError as e:
    print("ERRO:", e.code, e.read().decode()[:500])
