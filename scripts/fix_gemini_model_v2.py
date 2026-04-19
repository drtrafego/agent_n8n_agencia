"""
Troca modelName de gemini-2.0-flash para gemini-1.5-flash nos nos lmChatGoogleGemini.

Motivo: o n8n usa o SDK @google/generative-ai que chama o endpoint v1 (estavel).
gemini-2.0-flash so existe em v1beta e retorna 404 via SDK.
gemini-1.5-flash esta em v1, sem thinking, funciona com googlePalmApi.

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
    'JmiydfZHpeU8tnic': 'SDR principal BR',
    '6EJoeyC63gDEffu2': 'Google Agenda BR',
    'jgp53YrDLurBIsjp': 'SDR principal ES',
}

OLD_MODEL = 'gemini-2.0-flash'
NEW_MODEL = 'gemini-1.5-flash'
CHAT_TYPE = 'lmChatGoogleGemini'

BACKUP_DIR = os.path.join(os.path.dirname(__file__), '..', 'backups')
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


def process(wf_id, wf_label):
    print(f'\n{"="*60}')
    print(f'{wf_label} ({wf_id})')
    print('='*60)

    s, wf = api('GET', f'/api/v1/workflows/{wf_id}')
    if s != 200:
        print(f'  [ERRO] GET {s}')
        return False

    chat_nodes = [(i, n) for i, n in enumerate(wf['nodes'])
                  if CHAT_TYPE in n.get('type', '')]

    needs_fix = [(i, n) for i, n in chat_nodes
                 if n.get('parameters', {}).get('modelName') == OLD_MODEL]

    for _, n in chat_nodes:
        m = n.get('parameters', {}).get('modelName', '(sem modelName)')
        flag = 'TROCAR' if m == OLD_MODEL else 'ok'
        print(f'  [{flag}] "{n["name"]}" -> {m}')

    if not needs_fix:
        print('  Nada a alterar.')
        return True

    # Backup
    bk = os.path.join(BACKUP_DIR, f'gemini_v2_{wf_label.replace(" ","_").lower()}_{TIMESTAMP}.json')
    with open(bk, 'w', encoding='utf-8') as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print(f'  [BACKUP] {os.path.basename(bk)}')

    wf_up = copy.deepcopy(wf)
    for idx, _ in needs_fix:
        wf_up['nodes'][idx]['parameters']['modelName'] = NEW_MODEL
        print(f'  [SET] "{wf_up["nodes"][idx]["name"]}" -> {NEW_MODEL}')

    was_active = wf_up.get('active', False)
    if was_active:
        api('POST', f'/api/v1/workflows/{wf_id}/deactivate')

    s, resp = api('PUT', f'/api/v1/workflows/{wf_id}', {
        'name': wf_up['name'],
        'nodes': wf_up['nodes'],
        'connections': wf_up['connections'],
        'settings': wf_up.get('settings', {}),
    })
    if s not in (200, 204):
        print(f'  [ERRO] PUT {s}: {resp}')
        return False
    print(f'  PUT: {s} ok')

    if was_active:
        api('POST', f'/api/v1/workflows/{wf_id}/activate')
        print('  Reativado')

    # Verificacao
    s2, wf2 = api('GET', f'/api/v1/workflows/{wf_id}')
    if s2 == 200:
        for n in wf2['nodes']:
            if CHAT_TYPE in n.get('type', ''):
                m = n.get('parameters', {}).get('modelName', '?')
                ok = m == NEW_MODEL
                print(f'  {"OK" if ok else "FALHOU"} "{n["name"]}" -> {m}')

    return True


def main():
    print(f'Fix Gemini Model v2 - {TIMESTAMP}')
    print(f'Trocando {OLD_MODEL} -> {NEW_MODEL} (SDK n8n usa endpoint v1 estavel)')
    for wf_id, label in WORKFLOWS.items():
        process(wf_id, label)
    print('\nDONE')


if __name__ == '__main__':
    main()
