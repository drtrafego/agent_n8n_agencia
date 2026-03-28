# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ctx = ssl._create_unverified_context()
API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"

def n8n_get(path):
    req = urllib.request.Request("https://n8n.casaldotrafego.com" + path, headers={"X-N8N-API-KEY": API_KEY})
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode())

# Execucoes com erro dos 3 leads
EXEC_IDS = {
    "2090": "Symone (11:23)",
    "2097": "Conect (14:22)",
    "2099": "Suh (15:28)",
    # Tambem verificar os erros recentes
    "2148": "recente (00:11)",
    "2147": "recente (00:04)",
    "2146": "recente (00:04)",
    "2145": "recente (00:03)",
    # E outros erros do mesmo dia
    "2109": "erro 19:13",
    "2106": "erro 18:55",
    "2102": "erro 16:36",
    "2094": "erro 13:03",
}

for ex_id, label in EXEC_IDS.items():
    print("\n" + "=" * 60)
    print("  Exec #%s - %s" % (ex_id, label))
    print("=" * 60)
    try:
        detail = n8n_get("/api/v1/executions/%s" % ex_id)
        d = detail.get("data", {})
        result_data = d.get("resultData", {})
        run_data = result_data.get("runData", {})
        error_msg = result_data.get("error", {})

        if error_msg:
            print("  Error global: %s" % str(error_msg)[:300])

        nodes_ran = list(run_data.keys())
        print("  Nodes executados: %s" % nodes_ran)

        last_node_error = result_data.get("lastNodeExecuted")
        if last_node_error:
            print("  Ultimo node: %s" % last_node_error)

        for node_name, runs in run_data.items():
            for run in runs:
                err = run.get("error")
                if err:
                    print("\n  ERRO no '%s':" % node_name)
                    print("    name: %s" % err.get("name",""))
                    print("    message: %s" % (err.get("message",""))[:400])
                    desc = err.get("description","")
                    if desc:
                        print("    desc: %s" % str(desc)[:300])

        # Se nao tem run_data, pode ser que o workflow falhou antes de executar
        if not run_data:
            print("  SEM run_data - falhou antes de executar qualquer node")
            # Tentar pegar o erro do executionData
            exec_data = d.get("executionData", {})
            if exec_data:
                print("  executionData keys: %s" % list(exec_data.keys()))

    except urllib.error.HTTPError as e:
        print("  HTTP %d - nao disponivel" % e.code)
    except Exception as e:
        print("  Erro: %s" % e)
