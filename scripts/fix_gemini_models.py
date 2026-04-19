"""
Mapeia e corrige todos os nos lmChatGoogleGemini em workflows BR + ES.

Problema: nos com typeVersion 1 e parameters:{options:{}} nao tem modelName setado,
entao n8n usa o default da API (atualmente gemini-2.5-flash, que e thinking model
e gera output vazio ~22% das vezes).

Fix: setar modelName: 'gemini-2.0-flash' explicitamente em todos os nos de chat Gemini.
Nos de embedding (embeddingsGoogleGemini) sao mantidos como estao.
"""

import urllib.request, json, ssl, sys, io, datetime, os, copy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'

WORKFLOWS = {
    'JmiydfZHpeU8tnic': 'SDR principal BR',
    '6EJoeyC63gDEffu2': 'Google Agenda BR',
    'jgp53YrDLurBIsjp': 'SDR principal ES',
    'HXs2dtpyHpKMhQVP': 'Follow-up ES',
}

TARGET_MODEL = 'gemini-2.0-flash'
CHAT_TYPE = 'lmChatGoogleGemini'
EMBED_TYPE = 'embeddingsGoogleGemini'

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)
TIMESTAMP = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')


def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
            return r.status, json.loads(r.read()) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:2000]


def backup(wf_label, data):
    name = wf_label.replace(' ', '_').lower()
    path = os.path.join(BACKUP_DIR, f'gemini_fix_{name}_{TIMESTAMP}.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f'  [BACKUP] {os.path.basename(path)}')


def get_chat_nodes(nodes):
    """Retorna apenas nos lmChatGoogleGemini (exclui embeddings)."""
    return [(i, n) for i, n in enumerate(nodes) if CHAT_TYPE in n.get('type', '')]


def get_model(node):
    p = node.get('parameters', {})
    return p.get('modelName') or p.get('options', {}).get('model') or None


def process_workflow(wf_id, wf_label):
    print(f'\n{"="*60}')
    print(f'Workflow: {wf_label} ({wf_id})')
    print('='*60)

    status, wf = api('GET', f'/api/v1/workflows/{wf_id}')
    if status != 200:
        print(f'  [ERRO] GET {status}: {wf}')
        return False

    nodes = wf.get('nodes', [])
    chat_nodes = get_chat_nodes(nodes)
    embed_nodes = [(i, n) for i, n in enumerate(nodes) if EMBED_TYPE in n.get('type', '')]

    print(f'  Nos de chat Gemini: {len(chat_nodes)}')
    print(f'  Nos de embedding Gemini: {len(embed_nodes)} (nao alterados)')

    if not chat_nodes:
        print('  Nenhum no de chat Gemini. Pulando.')
        return True

    # Mostra estado atual
    needs_fix = []
    for idx, node in chat_nodes:
        model = get_model(node)
        display = model if model else '(default - sem modelName setado)'
        already_ok = model == TARGET_MODEL
        flag = 'ok' if already_ok else 'PRECISA SETAR'
        print(f'  [{flag}] "{node["name"]}" | modelo: {display}')
        if not already_ok:
            needs_fix.append(idx)

    if not needs_fix:
        print(f'  Todos ja tem modelName={TARGET_MODEL}. Nada a fazer.')
        return True

    # Backup
    backup(wf_label, wf)

    # Aplica fix
    wf_updated = copy.deepcopy(wf)
    for idx in needs_fix:
        node = wf_updated['nodes'][idx]
        # Seta modelName diretamente nos parameters
        if 'parameters' not in node:
            node['parameters'] = {}
        node['parameters']['modelName'] = TARGET_MODEL
        print(f'  [SET] "{node["name"]}" -> modelName: {TARGET_MODEL}')

    # Desativa > PUT (apenas campos aceitos) > reativa
    was_active = wf_updated.get('active', False)
    if was_active:
        s, _ = api('POST', f'/api/v1/workflows/{wf_id}/deactivate')
        print(f'  Desativado: {s}')

    put_body = {
        'name': wf_updated['name'],
        'nodes': wf_updated['nodes'],
        'connections': wf_updated['connections'],
        'settings': wf_updated.get('settings', {}),
    }
    s, resp = api('PUT', f'/api/v1/workflows/{wf_id}', put_body)
    if s not in (200, 204):
        print(f'  [ERRO] PUT {s}: {resp}')
        return False
    print(f'  PUT: {s} ok')

    if was_active:
        s, _ = api('POST', f'/api/v1/workflows/{wf_id}/activate')
        print(f'  Reativado: {s}')

    # Verificacao
    s2, wf_check = api('GET', f'/api/v1/workflows/{wf_id}')
    if s2 == 200:
        print('  Verificacao pos-deploy:')
        for _, n in get_chat_nodes(wf_check.get('nodes', [])):
            m = get_model(n)
            ok = m == TARGET_MODEL
            print(f'    {"OK" if ok else "FALHOU"} "{n["name"]}" -> {m}')

    return True


def main():
    print(f'Fix Gemini Models - {TIMESTAMP}')
    print(f'Setando modelName={TARGET_MODEL} em todos os nos lmChatGoogleGemini sem modelo explicito')

    results = {}
    for wf_id, wf_label in WORKFLOWS.items():
        ok = process_workflow(wf_id, wf_label)
        results[wf_label] = ok

    print(f'\n{"="*60}')
    print('RESUMO FINAL')
    print('='*60)
    for label, ok in results.items():
        status = 'OK' if ok else 'ERRO'
        print(f'  {status} - {label}')


if __name__ == '__main__':
    main()
