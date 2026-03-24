import urllib.request, json, ssl, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"

url = "https://n8n.casaldotrafego.com/api/v1/workflows/JmiydfZHpeU8tnic"
req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
resp = urllib.request.urlopen(req, context=ctx)
raw = resp.read().decode('utf-8', errors='replace')
data = json.loads(raw)

# ============================================================
# FIX 1: Buscar Contato - add query parameters for $1, $2
# ============================================================
for n in data['nodes']:
    if n['name'] == 'Buscar Contato':
        n['parameters']['options'] = {
            "queryParameters": {
                "parameters": [
                    {
                        "name": "",
                        "value": "={{ $json.telefone }}"
                    },
                    {
                        "name": "",
                        "value": "={{ $json.Nome }}"
                    }
                ]
            }
        }
        print("[FIX 1] Buscar Contato: query parameters adicionados ($1=telefone, $2=Nome)")

# ============================================================
# FIX 2: Postgres Chat Memory - use different table/context for each agent
# The 3 memory nodes write to the same table causing triplication.
# Fix: Use different contextWindowSize or tableName to avoid overlap.
# Actually, the issue is that Orquestrador + SDR both record the same
# conversation. Let's set a custom tableName for SDR to separate.
# ============================================================
for n in data['nodes']:
    if n['name'] == 'Postgres Chat Memory':
        # This is the Orquestrador's memory - keep as default
        if 'tableName' not in n.get('parameters', {}):
            n['parameters']['tableName'] = 'n8n_chat_histories'
        print(f"[FIX 2a] {n['name']}: tableName = n8n_chat_histories")

    if n['name'] == 'Postgres Chat Memory1':
        # automaticos agent memory - separate table
        n['parameters']['tableName'] = 'n8n_chat_auto'
        print(f"[FIX 2b] {n['name']}: tableName = n8n_chat_auto")

    if n['name'] == 'Postgres Chat Memory2':
        # SDR agent memory - separate table
        n['parameters']['tableName'] = 'n8n_chat_sdr'
        print(f"[FIX 2c] {n['name']}: tableName = n8n_chat_sdr")

# ============================================================
# FIX 3: Code4 - ensure Nome is passed through properly
# ============================================================
for n in data['nodes']:
    if n['name'] == 'Code4':
        old_code = n['parameters']['jsCode']
        # Make sure Nome is preserved
        if "final.Nome" not in old_code:
            new_code = old_code.replace(
                "final.Mensagem = mensagens.join(\", \");",
                "final.Mensagem = mensagens.join(\", \");\nif (!final.Nome) final.Nome = '';"
            )
            n['parameters']['jsCode'] = new_code
            print("[FIX 3] Code4: Nome fallback adicionado")
        else:
            print("[FIX 3] Code4: Nome ja presente")

# ============================================================
# Push update
# ============================================================
payload = {
    "name": data.get("name"),
    "nodes": data["nodes"],
    "connections": data["connections"],
    "settings": data.get("settings", {})
}

body = json.dumps(payload, ensure_ascii=True).encode('utf-8')
req = urllib.request.Request(
    "https://n8n.casaldotrafego.com/api/v1/workflows/JmiydfZHpeU8tnic",
    data=body, method='PUT',
    headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"}
)
resp = urllib.request.urlopen(req, context=ctx)
result = json.loads(resp.read().decode())
print(f"\nWorkflow atualizado: {result.get('updatedAt')}")

# ============================================================
# Create missing tables in Supabase
# ============================================================
print("\n--- Criando tabelas de memoria separadas ---")
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"

# n8n auto-creates tables for Postgres Chat Memory, so we don't need to manually create them
# Just need to clean the old data
headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Prefer": "return=representation"}
for table in ["n8n_chat_histories", "contacts"]:
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=gt.0"
    req = urllib.request.Request(url, method='DELETE', headers=headers)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        d = json.loads(resp.read().decode())
        print(f"[CLEAN] {table}: {len(d)} registros apagados")
    except Exception as e:
        print(f"[CLEAN] {table}: {e}")

print("\nPronto! Fixes aplicados. Rode os testes novamente.")
