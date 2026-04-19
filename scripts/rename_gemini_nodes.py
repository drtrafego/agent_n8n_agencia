"""
Renomeia nos lmChatGoogleGemini que tem "OpenAI" no nome.
Substitui "OpenAI Chat Model" por "Gemini Chat Model" em:
  - nodes[].name
  - connections (chaves e referencias destino/fonte)
  - pinData (se houver)

Workflows: SDR BR, Google Agenda BR, SDR ES
"""

import urllib.request, json, ssl, sys, io, datetime, os, copy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'

WORKFLOWS = {
    'jgp53YrDLurBIsjp': 'SDR principal ES',
}

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


def new_name(old):
    """Substitui 'OpenAI Chat Model' por 'Gemini Chat Model' no nome."""
    return old.replace('OpenAI Chat Model', 'Gemini Chat Model')


def needs_rename(node):
    return 'lmChatGoogleGemini' in node.get('type', '') and 'OpenAI' in node.get('name', '')


def rename_in_connections(connections, rename_map):
    """
    Atualiza connections: troca chaves e referencias de destino.
    rename_map: {old_name: new_name}
    """
    new_conns = {}
    for src, outputs in connections.items():
        new_src = rename_map.get(src, src)
        new_outputs = {}
        for output_type, lists in outputs.items():
            new_lists = []
            for lst in lists:
                new_lst = []
                for dest in lst:
                    new_dest = dict(dest)
                    if new_dest.get('node') in rename_map:
                        new_dest['node'] = rename_map[new_dest['node']]
                    new_lst.append(new_dest)
                new_lists.append(new_lst)
            new_outputs[output_type] = new_lists
        new_conns[new_src] = new_outputs
    return new_conns


def process_workflow(wf_id, wf_label):
    print(f'\n{"="*60}')
    print(f'Workflow: {wf_label} ({wf_id})')
    print('='*60)

    status, wf = api('GET', f'/api/v1/workflows/{wf_id}')
    if status != 200:
        print(f'  [ERRO] GET {status}: {wf}')
        return False

    to_rename = [(i, n) for i, n in enumerate(wf['nodes']) if needs_rename(n)]

    if not to_rename:
        print('  Nenhum no com "OpenAI" no nome para renomear.')
        return True

    rename_map = {n['name']: new_name(n['name']) for _, n in to_rename}
    for old, new in rename_map.items():
        print(f'  [RENAME] "{old}" -> "{new}"')

    # Backup
    bk_name = wf_label.replace(' ', '_').lower()
    bk_path = os.path.join(BACKUP_DIR, f'rename_gemini_{bk_name}_{TIMESTAMP}.json')
    with open(bk_path, 'w', encoding='utf-8') as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print(f'  [BACKUP] {os.path.basename(bk_path)}')

    wf_updated = copy.deepcopy(wf)

    # Renomeia nos
    for idx, _ in to_rename:
        old = wf_updated['nodes'][idx]['name']
        wf_updated['nodes'][idx]['name'] = rename_map[old]

    # Atualiza connections
    wf_updated['connections'] = rename_in_connections(wf_updated['connections'], rename_map)

    # Atualiza pinData se existir e nao for None
    if wf_updated.get('pinData'):
        new_pin = {}
        for k, v in wf_updated['pinData'].items():
            new_pin[rename_map.get(k, k)] = v
        wf_updated['pinData'] = new_pin

    # Deploy
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
        print('  Verificacao:')
        for n in wf_check['nodes']:
            if 'lmChatGoogleGemini' in n.get('type', ''):
                has_openai = 'OpenAI' in n['name']
                flag = 'FALHOU' if has_openai else 'OK'
                print(f'    [{flag}] "{n["name"]}"')

    return True


def main():
    print(f'Rename Gemini Nodes - {TIMESTAMP}')
    print('Substituindo "OpenAI Chat Model" por "Gemini Chat Model"')

    results = {}
    for wf_id, wf_label in WORKFLOWS.items():
        ok = process_workflow(wf_id, wf_label)
        results[wf_label] = ok

    print(f'\n{"="*60}')
    print('RESUMO')
    print('='*60)
    for label, ok in results.items():
        print(f'  {"OK" if ok else "ERRO"} - {label}')


if __name__ == '__main__':
    main()
