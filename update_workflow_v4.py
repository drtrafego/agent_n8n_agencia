import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r'D:\GoogleDrive\Bilder Ai\agent_n8n_agencia\workflow_v3_meta.json', 'r', encoding='utf-8') as f:
    wf = json.load(f)

nodes = wf['nodes']
node_map = {n['name']: n for n in nodes}

# ============================================================
# 1. Google Sheets3 → Postgres (busca contato por telefone)
#    Antes: buscava na planilha por Telefone
#    Agora: SELECT da tabela contacts
# ============================================================
gs3 = node_map['Google Sheets3']
gs3['type'] = 'n8n-nodes-base.postgres'
gs3['typeVersion'] = 2.5
gs3['name'] = 'Buscar Contato'
gs3['parameters'] = {
    "operation": "executeQuery",
    "query": "SELECT * FROM contacts WHERE telefone = $1 LIMIT 1",
    "options": {
        "queryParameters": "={{ $json.telefone }}"
    }
}
gs3['credentials'] = {
    "postgres": {
        "id": "",
        "name": "Supabase Postgres"
    }
}

# ============================================================
# 2. observacoes_sdr1 → Postgres Tool (SDR anota observações)
#    Antes: Google Sheets Tool que atualizava Observações_SDR
#    Agora: Postgres tool que faz UPSERT na tabela contacts
# ============================================================
obs = node_map['observacoes_sdr1']
obs['type'] = 'n8n-nodes-base.postgresTool'
obs['typeVersion'] = 2.5
obs['name'] = 'observacoes_sdr'
obs['parameters'] = {
    "descriptionType": "manual",
    "toolDescription": "Atualiza observações sobre o contato na tabela contacts. Use para salvar informações coletadas como número de funcionários, faturamento, gastos do cliente, ou qualquer informação relevante da conversa.",
    "operation": "executeQuery",
    "query": "INSERT INTO contacts (telefone, observacoes_sdr) VALUES ($1, $2) ON CONFLICT (telefone) DO UPDATE SET observacoes_sdr = EXCLUDED.observacoes_sdr",
    "options": {
        "queryParameters": "={{ $json.telefone }}, ={{ $fromAI('observacoes', '', 'string') }}"
    }
}
obs['credentials'] = {
    "postgres": {
        "id": "",
        "name": "Supabase Postgres"
    }
}

# ============================================================
# 3. Update Postgres Chat Memory nodes
#    Remove .split('@')[0] pois Meta WABA já envia número limpo
# ============================================================
for name in ['Postgres Chat Memory1', 'Postgres Chat Memory', 'Postgres Chat Memory2']:
    node = node_map[name]
    node['parameters'] = {
        "sessionIdType": "customKey",
        "sessionKey": "={{ $('Code4').item.json.From }}"
    }

# ============================================================
# 4. Update Supabase Vector Store3 tool description
#    Mudar de "Agência Rei" para genérico
# ============================================================
vs3 = node_map['Supabase Vector Store3']
vs3['parameters']['toolDescription'] = (
    "Banco de dados com todos os documentos importantes sobre a empresa. "
    "Use para contextualizar as respostas para perguntas do usuário."
)

# ============================================================
# 5. Update connections (rename nodes)
# ============================================================
conn = wf['connections']
renames = {
    'Google Sheets3': 'Buscar Contato',
    'observacoes_sdr1': 'observacoes_sdr',
}

for old, new in renames.items():
    if old in conn:
        conn[new] = conn.pop(old)

for source, outputs in conn.items():
    for ok, cl in outputs.items():
        for cg in cl:
            for c in cg:
                if c.get('node', '') in renames:
                    c['node'] = renames[c['node']]

# ============================================================
# Save
# ============================================================
# Remove extra keys for API
allowed = {'name', 'nodes', 'connections', 'settings', 'staticData'}
clean = {k: v for k, v in wf.items() if k in allowed}

with open(r'D:\GoogleDrive\Bilder Ai\agent_n8n_agencia\workflow_v4_final.json', 'w', encoding='utf-8') as f:
    json.dump(clean, f, ensure_ascii=True, indent=2)

print("Workflow v4 salvo!")
print("\nModificados:")
print("  - Google Sheets3 -> Buscar Contato (Postgres query)")
print("  - observacoes_sdr1 -> observacoes_sdr (Postgres Tool)")
print("  - Postgres Chat Memory 1/2/3 -> sessionKey sem split('@')")
print("  - Supabase Vector Store3 -> description atualizada")

# List all nodes with their types
print(f"\nTotal nodes: {len(nodes)}")
print("\nResumo por tipo:")
types = {}
for n in nodes:
    t = n['type']
    types[t] = types.get(t, 0) + 1
for t, c in sorted(types.items()):
    print(f"  {t}: {c}")
