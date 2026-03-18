import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\GoogleDrive\Bilder Ai\agent_n8n_agencia\current_workflow.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

nodes = wf['nodes']
node_map = {n['name']: n for n in nodes}

MSG = "$json.body.entry[0].changes[0].value.messages[0]"
META = "$json.body.entry[0].changes[0].value.metadata"

# 1. Filter1
f1 = node_map['Filter1']
f1['parameters'] = {
    "conditions": {
        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
        "conditions": [
            {"id": "cond-has-messages", "leftValue": "={{ " + MSG + ".from }}", "rightValue": "", "operator": {"type": "string", "operation": "notEmpty", "singleValue": True}},
            {"id": "cond-prefix-BR", "leftValue": "={{ " + MSG + ".from }}", "rightValue": "55", "operator": {"type": "string", "operation": "startsWith", "name": "filter.operator.startsWith"}},
            {"id": "filter-not-reaction", "leftValue": "={{ " + MSG + ".type }}", "rightValue": "reaction", "operator": {"type": "string", "operation": "notEquals"}}
        ],
        "combinator": "and"
    }
}

# 2. Switch2
sw2 = node_map['Switch2']
def make_switch_rule(msg_type, output_key):
    return {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
            "conditions": [{"leftValue": "={{ " + MSG + ".type }}", "rightValue": msg_type, "operator": {"type": "string", "operation": "equals"}, "id": f"switch2-{msg_type}-meta"}],
            "combinator": "and"
        },
        "renameOutput": True, "outputKey": output_key
    }
sw2['parameters'] = {"rules": {"values": [make_switch_rule("text", "texto"), make_switch_rule("audio", "audio")]}, "options": {}}

# 3. Texto
node_map['Texto']['parameters'] = {
    "assignments": {"assignments": [
        {"id": "from-meta", "name": "From", "value": "={{ " + MSG + ".from }}", "type": "string"},
        {"id": "phone-number-id", "name": "Instance", "value": "={{ " + META + ".phone_number_id }}", "type": "string"},
        {"id": "mensagem-meta", "name": "Mensagem", "value": "={{ " + MSG + ".text.body }}", "type": "string"},
        {"id": "msgid-meta", "name": "MensagemID", "value": "={{ " + MSG + ".id }}", "type": "string"},
        {"id": "datetime-meta", "name": "date_time", "value": "={{ " + MSG + ".timestamp }}", "type": "string"},
        {"id": "timestamp-meta", "name": "timestamp", "value": "={{ " + MSG + ".timestamp }}", "type": "string"},
    ]}, "options": {}
}

# 4. Texto1 (audio)
node_map['Texto1']['parameters'] = {
    "assignments": {"assignments": [
        {"id": "from-meta-a", "name": "From", "value": "={{ " + MSG + ".from }}", "type": "string"},
        {"id": "phone-id-a", "name": "Instance", "value": "={{ " + META + ".phone_number_id }}", "type": "string"},
        {"id": "media-id-meta", "name": "MensagemID", "value": "={{ " + MSG + ".audio.id }}", "type": "string"},
        {"id": "datetime-a", "name": "date_time", "value": "={{ " + MSG + ".timestamp }}", "type": "string"},
        {"id": "timestamp-a", "name": "timestamp", "value": "={{ " + MSG + ".timestamp }}", "type": "string"},
    ]}, "options": {}
}

# 5. Redis prefix agencia:
node_map['Redis']['parameters'] = {"operation": "push", "list": "=agencia:{{ $json.From }}", "messageData": "={{ $json.toJsonString() }}", "tail": True}
node_map['Redis12']['parameters'] = {"operation": "get", "propertyName": "Lista", "key": "=agencia:{{ $json.From }}", "options": {}}
node_map['Redis13']['parameters'] = {"operation": "delete", "key": "=agencia:{{ $('Texto').item.json.From }}"}

# 6. Evolution API3 -> Meta Send Message
ev3 = node_map['Evolution API3']
ev3['type'] = 'n8n-nodes-base.httpRequest'
ev3['typeVersion'] = 4.2
ev3['name'] = 'Meta Send Message'
ev3['parameters'] = {
    "method": "POST",
    "url": '=https://graph.facebook.com/v21.0/{{ $("Code4").item.json.Instance }}/messages',
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": '={{ JSON.stringify({ messaging_product: "whatsapp", to: $("Code4").item.json.telefone, type: "text", text: { body: $json.text } }) }}',
    "options": {}
}
ev3['credentials'] = {"httpHeaderAuth": {"id": "", "name": "Meta WABA Token"}}

# 7. Evolution API -> Meta Send Direct
ev1 = node_map['Evolution API']
ev1['type'] = 'n8n-nodes-base.httpRequest'
ev1['typeVersion'] = 4.2
ev1['name'] = 'Meta Send Direct'
ev1['parameters'] = {
    "method": "POST",
    "url": '=https://graph.facebook.com/v21.0/{{ $("Code4").item.json.Instance }}/messages',
    "authentication": "genericCredentialType",
    "genericAuthType": "httpHeaderAuth",
    "sendBody": True,
    "specifyBody": "json",
    "jsonBody": '={{ JSON.stringify({ messaging_product: "whatsapp", to: $("Code4").item.json.telefone, type: "text", text: { body: $("Orquestrador").item.json.output } }) }}',
    "options": {}
}
ev1['credentials'] = {"httpHeaderAuth": {"id": "", "name": "Meta WABA Token"}}

# 8. Obter mídia -> Meta Get Media
media_node = None
for n in nodes:
    if 'dia em base64' in n['name']:
        media_node = n
        break
if media_node:
    old_media_name = media_node['name']
    media_node['type'] = 'n8n-nodes-base.httpRequest'
    media_node['typeVersion'] = 4.2
    media_node['name'] = 'Meta Get Media'
    media_node['parameters'] = {
        "method": "GET",
        "url": "=https://graph.facebook.com/v21.0/{{ $json.MensagemID }}",
        "authentication": "genericCredentialType",
        "genericAuthType": "httpHeaderAuth",
        "options": {}
    }
    media_node['credentials'] = {"httpHeaderAuth": {"id": "", "name": "Meta WABA Token"}}

# 9. Code in JavaScript - adapt for Meta media
node_map['Code in JavaScript']['parameters'] = {
    "jsCode": "// Meta WABA: previous node returned media metadata with URL\n// Pass the download URL to Transcribe node\nconst mediaUrl = items[0].json.url;\nreturn [{ json: { audioUrl: mediaUrl, MensagemID: items[0].json.id } }];"
}

# 10. Code4 - telefone without @s.whatsapp.net
node_map['Code4']['parameters'] = {
    "jsCode": "const final = {};\nlet mensagens = [];\n\nfor (const item of items) {\n  const json = item.json;\n  if (json.Mensagem) mensagens.push(json.Mensagem);\n  for (const key in json) {\n    if (key !== 'Mensagem') final[key] = json[key];\n  }\n  // Meta WABA: From ja vem como numero limpo (ex: 5571993643490)\n  if (json.From && !final.telefone) {\n    final.telefone = json.From;\n  }\n}\n\nfinal.Mensagem = mensagens.join('\\n');\nreturn [{ json: final }];"
}

# Update connections (rename nodes)
conn = wf['connections']
renames = {
    'Evolution API3': 'Meta Send Message',
    'Evolution API': 'Meta Send Direct',
}
if media_node:
    renames[old_media_name] = 'Meta Get Media'

for old, new in renames.items():
    if old in conn:
        conn[new] = conn.pop(old)

for source, outputs in conn.items():
    for ok, cl in outputs.items():
        for cg in cl:
            for c in cg:
                node_name = c.get('node', '')
                if node_name in renames:
                    c['node'] = renames[node_name]

wf['settings'] = {"executionOrder": "v1"}

with open(r'D:\GoogleDrive\Bilder Ai\agent_n8n_agencia\workflow_v3_meta.json', 'w', encoding='utf-8') as f:
    json.dump(wf, f, ensure_ascii=True, indent=2)

print("Workflow v3 salvo!")
print(f"Total nodes: {len(nodes)}")
print("\nModificados:")
for name in ['Filter1', 'Switch2', 'Texto', 'Texto1', 'Redis', 'Redis12', 'Redis13', 'Code4', 'Code in JavaScript']:
    print(f"  - {name}")
print("Substituidos:")
print("  - Evolution API3 -> Meta Send Message")
print("  - Evolution API -> Meta Send Direct")
print("  - Obter midia -> Meta Get Media")
