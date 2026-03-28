# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"

def n8n_get(path):
    req = urllib.request.Request("https://n8n.casaldotrafego.com" + path, headers={"X-N8N-API-KEY": API_KEY})
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

wf = n8n_get("/api/v1/workflows/JmiydfZHpeU8tnic")

print("=" * 70)
print("  WORKFLOW PRINCIPAL - NODES DE ENTRADA")
print("=" * 70)

nodes = wf.get("nodes", [])
print("Total de nodes: %d\n" % len(nodes))

# Mostrar nodes do tipo webhook, code, e os primeiros na cadeia
for node in nodes:
    name = node.get("name", "")
    ntype = node.get("type", "")
    params = node.get("parameters", {})

    # Webhook nodes
    if "webhook" in ntype.lower():
        print("WEBHOOK NODE: %s" % name)
        print("  path: %s" % params.get("path", "?"))
        print("  method: %s" % params.get("httpMethod", "?"))
        print("  auth: %s" % params.get("authentication", "none"))
        print("  responseMode: %s" % params.get("responseMode", "?"))
        print("  options: %s" % params.get("options", {}))
        print()

    # Code nodes (provavelmente primeiro a processar)
    if "code" in ntype.lower():
        print("CODE NODE: %s" % name)
        code = params.get("jsCode", params.get("pythonCode", ""))
        if code:
            # Mostrar primeiras linhas
            lines = code.strip().split('\n')
            print("  Primeiras 30 linhas:")
            for i, line in enumerate(lines[:30]):
                print("  %3d: %s" % (i+1, line[:120]))
        print()

# Mostrar as connections do webhook - para onde ele vai
print("\n" + "=" * 70)
print("  CONNECTIONS DO WEBHOOK NODE")
print("=" * 70)
conns = wf.get("connections", {})
for src, targets in conns.items():
    if "webhook" in src.lower() or "Webhook" in src:
        print("  %s ->" % src)
        for branch in targets.get("main", []):
            for t in branch:
                print("    -> %s" % t.get("node","?"))
