import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"

# Step 1: Create sub-workflow with Code node (isolated from AI Agent = no timeout)
code_js = r"""// Code2 v6 - isolated sub-workflow
var texto = $input.first().json.output || '';
if (!texto || texto.trim().toUpperCase() === 'STOP') return [];
var t = texto.trim().toUpperCase();
if (t === 'AGENTE' || t === 'BOT' || t === 'HUMANO') return [];
if (!texto.trim()) return [];

var mensajes = texto.split(/\n+/).map(function(p){return p.trim()}).filter(function(p){return p.length > 0});
var result = mensajes.map(function(m){ return {json:{text:m}} });

var isScheduled = texto.toLowerCase().indexOf('sessao foi agendada') >= 0
  || texto.toLowerCase().indexOf('convite disparado') >= 0
  || texto.toLowerCase().indexOf('setor de oportunidades') >= 0;

if (isScheduled && result.length > 0) {
  var leadName = $input.first().json.Nome || '';
  var leadPhone = $input.first().json.From || '';
  result[result.length - 1].json.notifyScheduling = true;
  result[result.length - 1].json.leadName = leadName;
  result[result.length - 1].json.leadPhone = leadPhone;
  result[result.length - 1].json.leadDetails = texto;
}

return result;"""

sub_workflow = {
    "name": "Code2_Processor_agencia",
    "nodes": [
        {
            "parameters": {"inputSource": "passthrough"},
            "type": "n8n-nodes-base.executeWorkflowTrigger",
            "typeVersion": 1.1,
            "position": [200, 300],
            "id": "trigger1",
            "name": "Execute Workflow Trigger"
        },
        {
            "parameters": {"jsCode": code_js},
            "type": "n8n-nodes-base.code",
            "typeVersion": 2,
            "position": [450, 300],
            "id": "code1",
            "name": "Process Text"
        }
    ],
    "connections": {
        "Execute Workflow Trigger": {"main": [[{"node": "Process Text", "type": "main", "index": 0}]]}
    },
    "settings": {"executionOrder": "v1"}
}

body = json.dumps(sub_workflow, ensure_ascii=True).encode('utf-8')
req = urllib.request.Request("https://n8n.casaldotrafego.com/api/v1/workflows", data=body, method='POST',
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"})
resp = urllib.request.urlopen(req, context=ctx)
sub_result = json.loads(resp.read().decode())
sub_id = sub_result.get('id')
print(f"Sub-workflow created: {sub_id}")

# Step 2: Update main workflow - replace Code2 with Execute Workflow
url = "https://n8n.casaldotrafego.com/api/v1/workflows/JmiydfZHpeU8tnic"
req2 = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
resp2 = urllib.request.urlopen(req2, context=ctx)
raw2 = resp2.read().decode('utf-8', errors='replace')
data = json.loads(raw2)

for i, n in enumerate(data['nodes']):
    if n['name'] == 'Code2':
        pos = n.get('position', [784, 2064])
        data['nodes'][i] = {
            "parameters": {
                "source": "database",
                "workflowId": {"__rl": True, "value": sub_id, "mode": "id"},
                "options": {}
            },
            "type": "n8n-nodes-base.executeWorkflow",
            "typeVersion": 1.2,
            "position": pos,
            "id": n.get('id', ''),
            "name": "Code2"
        }
        print(f"Code2 -> Execute Workflow ({sub_id})")

# Preserve ALL credentials
ALL_CREDS = {
    'Meta Send Message': {'httpHeaderAuth': {'id': '6vZScy0DKrtEtfg2', 'name': 'Meta WABA Token'}},
    'Meta Send Direct': {'httpHeaderAuth': {'id': '6vZScy0DKrtEtfg2', 'name': 'Meta WABA Token'}},
    'Meta Get Media': {'httpHeaderAuth': {'id': '6vZScy0DKrtEtfg2', 'name': 'Meta WABA Token'}},
    'Transcribe a recording': {'googlePalmApi': {'id': 'U7A0TWdvHi9DZoJq', 'name': 'Google Gemini(PaLM) Api account'}},
    'Google Drive': {'googleDriveOAuth2Api': {'id': '8SecSOKTyF0R0LBm', 'name': 'Google Drive OAuth2'}},
    'Google Drive Trigger': {'googleDriveOAuth2Api': {'id': '8SecSOKTyF0R0LBm', 'name': 'Google Drive OAuth2'}},
    'Google Drive Trigger1': {'googleDriveOAuth2Api': {'id': '8SecSOKTyF0R0LBm', 'name': 'Google Drive OAuth2'}},
    'Supabase Vector Store': {'supabaseApi': {'id': 'Jc7okVff0fNO3GIp', 'name': 'Supabase agent-n8n-agencia'}},
    'Supabase Vector Store3': {'supabaseApi': {'id': 'Jc7okVff0fNO3GIp', 'name': 'Supabase agent-n8n-agencia'}},
    'Delete Row': {'supabaseApi': {'id': 'Jc7okVff0fNO3GIp', 'name': 'Supabase agent-n8n-agencia'}},
    'Embeddings OpenAI1': {'googlePalmApi': {'id': 'U7A0TWdvHi9DZoJq', 'name': 'Google Gemini(PaLM) Api account'}},
    'Embeddings OpenAI2': {'googlePalmApi': {'id': 'U7A0TWdvHi9DZoJq', 'name': 'Google Gemini(PaLM) Api account'}},
    'OpenAI Chat Model1': {'googlePalmApi': {'id': 'U7A0TWdvHi9DZoJq', 'name': 'Google Gemini(PaLM) Api account'}},
    'OpenAI Chat Model2': {'googlePalmApi': {'id': 'U7A0TWdvHi9DZoJq', 'name': 'Google Gemini(PaLM) Api account'}},
    'OpenAI Chat Model3': {'googlePalmApi': {'id': 'U7A0TWdvHi9DZoJq', 'name': 'Google Gemini(PaLM) Api account'}},
    'Postgres Chat Memory': {'postgres': {'id': 'qjAlzv5GyfH3869u', 'name': 'Postgres agent-n8n-agencia'}},
    'Postgres Chat Memory1': {'postgres': {'id': 'qjAlzv5GyfH3869u', 'name': 'Postgres agent-n8n-agencia'}},
    'Postgres Chat Memory2': {'postgres': {'id': 'qjAlzv5GyfH3869u', 'name': 'Postgres agent-n8n-agencia'}},
    'Redis': {'redis': {'id': 'O9M0TmSnZ8jeN6k3', 'name': 'Redis Local'}},
    'Redis12': {'redis': {'id': 'O9M0TmSnZ8jeN6k3', 'name': 'Redis Local'}},
    'Redis13': {'redis': {'id': 'O9M0TmSnZ8jeN6k3', 'name': 'Redis Local'}},
    'alterarreunioes1': {'googleCalendarOAuth2Api': {'id': 'IktwWGIvthTqBTme', 'name': 'Google Calendar OAuth2'}},
    'criarreunioes1': {'googleCalendarOAuth2Api': {'id': 'IktwWGIvthTqBTme', 'name': 'Google Calendar OAuth2'}},
    'Buscarhorarios1': {'googleCalendarOAuth2Api': {'id': 'IktwWGIvthTqBTme', 'name': 'Google Calendar OAuth2'}},
    'Buscar Contato': {'postgres': {'id': 'qjAlzv5GyfH3869u', 'name': 'Postgres agent-n8n-agencia'}},
    'observacoes_sdr': {'postgres': {'id': 'qjAlzv5GyfH3869u', 'name': 'Postgres agent-n8n-agencia'}},
}

for n in data['nodes']:
    if n['name'] in ALL_CREDS:
        n['credentials'] = ALL_CREDS[n['name']]

payload = {"name": data["name"], "nodes": data["nodes"], "connections": data["connections"], "settings": data.get("settings", {})}
body2 = json.dumps(payload, ensure_ascii=True).encode('utf-8')
req3 = urllib.request.Request(url, data=body2, method='PUT', headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"})
resp3 = urllib.request.urlopen(req3, context=ctx)
result = json.loads(resp3.read().decode())

missing = [n['name'] for n in result.get('nodes', []) if n['type'] == 'n8n-nodes-base.httpRequest' and not n.get('credentials')]
print(f"Updated: {result.get('updatedAt')}")
print(f"Creds: {'ALL OK' if not missing else missing}")

for n in result.get('nodes', []):
    if n['name'] == 'Code2':
        print(f"Code2 type: {n['type']}")
