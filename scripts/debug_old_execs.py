# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"

def n8n_get(path):
    req = urllib.request.Request("https://n8n.casaldotrafego.com" + path, headers={"X-N8N-API-KEY": API_KEY})
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

# Buscar execucoes mais antigas (pular as 30 mais recentes)
print("Execucoes de ontem (11h-16h) - buscando com cursor...")

# n8n API suporta cursor pagination via lastId
# Execucoes 2110 pra baixo: usar limit grande
data = n8n_get("/api/v1/executions?workflowId=JmiydfZHpeU8tnic&limit=200")
all_execs = data.get("data", [])
print("Total retornado: %d" % len(all_execs))
print("IDs: de #%s ate #%s" % (all_execs[-1]["id"] if all_execs else "?", all_execs[0]["id"] if all_execs else "?"))

# Filtrar execucoes entre 11:00 e 16:00 de ontem (2026-03-27)
relevant = [ex for ex in all_execs if "2026-03-27T1" in ex.get("startedAt", "")]
print("\nExecucoes no dia 27 entre 11h-19h:")
for ex in relevant:
    ts = ex.get("startedAt","")[:16]
    print("  #%s | %s | %s | %s" % (ex["id"], ts, ex.get("status"), ex.get("mode")))

# Verificar execucoes com erro - detalhar as mais recentes
print("\n4 execucoes com ERRO mais recentes:")
errors = [ex for ex in all_execs if ex.get("status") == "error"][:4]
for ex in errors:
    print("\n  #%s | %s" % (ex["id"], ex.get("startedAt","")[:16]))
    try:
        detail = n8n_get("/api/v1/executions/%s" % ex["id"])
        d = detail.get("data", {})
        run_data = d.get("resultData", {}).get("runData", {})
        for node_name, runs in run_data.items():
            for run in runs:
                if run.get("error"):
                    err = run["error"]
                    print("    ERRO no '%s': %s" % (node_name, (err.get("message",""))[:200]))
    except Exception as e:
        print("    [detalhe indisponivel: %s]" % e)
