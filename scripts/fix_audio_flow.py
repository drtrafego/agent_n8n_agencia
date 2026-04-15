"""
Fix audio transcription flow in JmiydfZHpeU8tnic:
1. Fix Aggregate2 renameField bug (text field renamed to empty string)
2. Fix Normalize Transcription to handle Gemini 2.5 flash thinking mode
3. Disable thinking in transcription request (unnecessary for audio)
"""
import urllib.request, json, ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
WF_ID = "JmiydfZHpeU8tnic"
BASE = "https://n8n.casaldotrafego.com"

AGGREGATE_NODE_ID = "98ff3af6-f00c-41b0-aff9-f30c121ee112"
TRANSCRIBE_NODE_ID = "9127b615-fef8-45e5-acd7-896f58b4e465"
NORMALIZE_NODE_ID = "a1b2c3d4-norm-transcription-001"


def api(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("X-N8N-API-KEY", API_KEY)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, context=ctx) as r:
        return r.status, json.loads(r.read())


print("=" * 60)
print("FIX AUDIO FLOW - JmiydfZHpeU8tnic")
print("=" * 60)

print("\n1. Fetching workflow...")
_, wf = api("GET", f"/api/v1/workflows/{WF_ID}")
print(f"   Name: {wf['name']}")

# --- FIX 1: Aggregate2 renameField ---
print("\n2. Fixing Aggregate2 renameField...")
agg_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == AGGREGATE_NODE_ID)
agg_fields = wf["nodes"][agg_idx]["parameters"]["fieldsToAggregate"]["fieldToAggregate"]

for i, field in enumerate(agg_fields):
    if field.get("fieldToAggregate") == "text":
        old_rename = field.get("renameField", "NONE")
        print(f"   Old renameField for 'text': '{old_rename}'")
        # Remove the broken renameField - keep original name "text"
        if "renameField" in field:
            del field["renameField"]
        print("   Removed renameField. Field will keep name 'text'.")
        agg_fields[i] = field

wf["nodes"][agg_idx]["parameters"]["fieldsToAggregate"]["fieldToAggregate"] = agg_fields

# --- FIX 2: Transcription request - disable thinking ---
print("\n3. Fixing transcription request (disable thinking)...")
trans_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == TRANSCRIBE_NODE_ID)
# Update the body to disable thinking and ensure clean transcription
new_body = (
    '={"contents":[{"parts":[{"inline_data":{"mime_type":"{{ $json.mimetype }}",'
    '"data":"{{ $json.base64 }}"}},{"text":"Transcreva este \u00e1udio em portugu\u00eas. '
    'Retorne apenas o texto transcrito, sem nenhuma explica\u00e7\u00e3o."}]}],'
    '"generationConfig":{"thinkingConfig":{"thinkingBudget":0}}}'
)
old_body = wf["nodes"][trans_idx]["parameters"]["body"]
wf["nodes"][trans_idx]["parameters"]["body"] = new_body
print(f"   Added thinkingConfig.thinkingBudget=0")
print(f"   Old body length: {len(old_body)}")
print(f"   New body length: {len(new_body)}")

# --- FIX 3: Normalize Transcription - handle both formats ---
print("\n4. Fixing Normalize Transcription (handle thinking parts)...")
norm_idx = next(i for i, n in enumerate(wf["nodes"]) if n["id"] == NORMALIZE_NODE_ID)
# Use expression that gets the LAST non-thinking part (works for both 2.0 and 2.5)
old_expr = wf["nodes"][norm_idx]["parameters"]["assignments"]["assignments"][0]["value"]
# New expression: get candidates[0].content.parts, filter out thought parts, get last text
new_expr = '={{ $json.candidates[0].content.parts.filter(p => !p.thought).pop().text }}'
wf["nodes"][norm_idx]["parameters"]["assignments"]["assignments"][0]["value"] = new_expr
print(f"   Old: {old_expr}")
print(f"   New: {new_expr}")

# --- DEPLOY ---
print("\n5. Deploying...")
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

# --- VERIFY ---
print("\n6. Verificando...")
_, wf2 = api("GET", f"/api/v1/workflows/{WF_ID}")

agg2 = next(n for n in wf2["nodes"] if n["id"] == AGGREGATE_NODE_ID)
for field in agg2["parameters"]["fieldsToAggregate"]["fieldToAggregate"]:
    if field.get("fieldToAggregate") == "text":
        has_rename = "renameField" in field
        print(f"   Aggregate2 text renameField removed: {not has_rename}")

trans2 = next(n for n in wf2["nodes"] if n["id"] == TRANSCRIBE_NODE_ID)
print(f"   Transcription has thinkingBudget:0: {'thinkingBudget' in trans2['parameters']['body']}")

norm2 = next(n for n in wf2["nodes"] if n["id"] == NORMALIZE_NODE_ID)
expr = norm2["parameters"]["assignments"]["assignments"][0]["value"]
print(f"   Normalize uses filter: {'filter' in expr}")
print(f"   Normalize expression: {expr}")

print(f"\n   Workflow active: {wf2['active']}")
print("\n" + "=" * 60)
print("DONE! Audio flow fixed.")
print("=" * 60)
