# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}

def n8n_get(path):
    req = urllib.request.Request("https://n8n.casaldotrafego.com" + path, headers={"X-N8N-API-KEY": API_KEY})
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

def sb_get(path):
    req = urllib.request.Request(SUPABASE_URL + path, headers=SB_H)
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

wf = n8n_get("/api/v1/workflows/JmiydfZHpeU8tnic")
nodes = {n["name"]: n for n in wf.get("nodes", [])}

# Mostrar Filter1 e todos os primeiros nodes da cadeia
print("=" * 70)
print("  CADEIA INICIAL: Webhook -> Filter1 -> ...")
print("=" * 70)

key_nodes = ["Filter1", "Webhook", "Code4", "Buscar Contato"]
for name in key_nodes:
    if name in nodes:
        node = nodes[name]
        print("\nNODE: %s (%s)" % (name, node.get("type","")))
        params = node.get("parameters", {})
        print("  Params: %s" % json.dumps(params, ensure_ascii=False)[:500])

# Mostrar todas as conexões do workflow (mapa completo)
print("\n" + "=" * 70)
print("  MAPA DE CONEXOES (primeiros 20)")
print("=" * 70)
conns = wf.get("connections", {})
for src, targets in list(conns.items())[:20]:
    for i, branch in enumerate(targets.get("main", [])):
        for t in branch:
            print("  %s [out%d] -> %s" % (src, i, t.get("node","?")))

# Verificar uma execucao bem sucedida para comparar o payload
print("\n" + "=" * 70)
print("  EXECUCAO BEM SUCEDIDA #2136 - ver run_data")
print("=" * 70)
detail = n8n_get("/api/v1/executions/2136")
d = detail.get("data", {})
run_data = d.get("resultData", {}).get("runData", {})
print("  Nodes executados: %s" % list(run_data.keys()))
if "Webhook" in run_data:
    for r in run_data["Webhook"]:
        items = r.get("data", {}).get("main", [[]])[0]
        if items:
            print("  Webhook input (primeiro item): %s" % json.dumps(items[0].get("json",{}), ensure_ascii=False)[:600])

# Verificar execucao com erro RECENTE para comparar
print("\n" + "=" * 70)
print("  EXECUCAO COM ERRO #2148 - ver o que chegou")
print("=" * 70)
detail2 = n8n_get("/api/v1/executions/2148")
d2 = detail2.get("data", {})
full_data = d2  # ver tudo
run_data2 = d2.get("resultData", {}).get("runData", {})
print("  Nodes executados: %s" % list(run_data2.keys()))
print("  Keys no data: %s" % list(d2.keys()))
exec_data = d2.get("executionData", {})
print("  executionData keys: %s" % list(exec_data.keys()) if exec_data else "  sem executionData")
result_data = d2.get("resultData", {})
print("  resultData keys: %s" % list(result_data.keys()))
err = result_data.get("error")
print("  resultData.error: %s" % str(err)[:300] if err else "  sem error em resultData")

# Comparar input de uma execucao com sucesso vs erro
print("\n" + "=" * 70)
print("  EXECUTANDO TESTE DIRETO NO WEBHOOK DO N8N")
print("=" * 70)

# Payload que o Next.js envia para o n8n
# Baseado no webhook handler, linha 235
test_payload = {
    "object": "whatsapp_business_account",
    "entry": [{
        "changes": [{
            "value": {
                "messaging_product": "whatsapp",
                "messages": [{
                    "from": "556791099280",
                    "id": "wamid.test123",
                    "timestamp": "1743078000",
                    "text": {"body": "Queria um Agente de IA como funciona?"},
                    "type": "text"
                }],
                "contacts": [{"profile": {"name": "Suh"}, "wa_id": "556791099280"}],
                "metadata": {"display_phone_number": "5511996681596", "phone_number_id": "115216611574100"},
            },
        }],
    }],
}

import ssl, urllib.request
ctx2 = ssl._create_unverified_context()
body = json.dumps(test_payload).encode()
N8N_WH_URL = "https://n8n.casaldotrafego.com/webhook/waba-agencia-21b9e103"
req = urllib.request.Request(N8N_WH_URL, data=body, method="POST",
    headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, context=ctx2, timeout=60)
    print("  Status: %d" % resp.getcode())
    print("  Response: %s" % resp.read().decode()[:300])
except urllib.error.HTTPError as e:
    print("  HTTP %d: %s" % (e.code, e.read().decode()[:300]))
except Exception as e:
    print("  Erro: %s" % e)
