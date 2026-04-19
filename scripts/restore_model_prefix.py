"""
Restaura o prefixo 'models/' no modelo Gemini - como estava nos backups
de 13/04, 14/04, 15/04 quando o bot funcionava.

Estado original (funcionando): models/gemini-2.5-flash
Estado atual (com falhas):      gemini-2.5-flash

O prefixo models/ pode rotear para uma versao diferente/mais estavel.
"""
import urllib.request, json, ssl, sys, io, copy, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY  = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'
TS   = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

WORKFLOWS = {
    'JmiydfZHpeU8tnic': 'SDR BR',
    '6EJoeyC63gDEffu2': 'Google Agenda BR',
    'jgp53YrDLurBIsjp': 'SDR ES',
}

# Modelo original dos backups funcionando
OLD_MODELS = ['gemini-2.5-flash', 'gemini-2.5-flash-lite', 'gemini-2.0-flash', 'gemini-1.5-flash']
NEW_MODEL_MAP = {
    'Gemini Chat Model3': 'models/gemini-2.5-flash',   # SDR principal
    'Gemini Chat Model1': 'models/gemini-2.5-flash-lite',  # Orquestrador (lite OK)
    'Gemini Chat Model2': 'models/gemini-2.5-flash-lite',  # SDR_retry (lite OK)
    'Google Gemini':      'models/gemini-2.5-flash',   # Calendar
    # ES
    'OpenAI Chat Model1': 'models/gemini-2.5-flash',
    'OpenAI Chat Model3': 'models/gemini-2.5-flash',
}


def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def process(wf_id, label):
    print(f'\n{label} ({wf_id})')
    _, wf = api('GET', f'/api/v1/workflows/{wf_id}')
    wf_up = copy.deepcopy(wf)

    changed = False
    for n in wf_up['nodes']:
        if 'lmChatGoogleGemini' not in n.get('type', ''):
            continue
        name = n.get('name', '')
        current = n.get('parameters', {}).get('modelName', '')

        # Determina o modelo certo para este no
        target = NEW_MODEL_MAP.get(name)
        if not target:
            # Para nos nao mapeados, so adiciona o prefixo se necessario
            if current and not current.startswith('models/'):
                target = f'models/{current}'
            else:
                print(f'  {name}: {current} (sem alteracao)')
                continue

        if current == target:
            print(f'  {name}: {current} (ja ok)')
            continue

        n['parameters']['modelName'] = target
        # Remove thinkingBudget que pode estar causando comportamento inesperado
        if 'thinkingBudget' in n.get('parameters', {}).get('options', {}):
            del n['parameters']['options']['thinkingBudget']
        # Restaura typeVersion original
        n['typeVersion'] = 1
        print(f'  {name}: {current} -> {target}')
        changed = True

    if not changed:
        print('  Nada a mudar.')
        return

    api('POST', f'/api/v1/workflows/{wf_id}/deactivate')
    s, _ = api('PUT', f'/api/v1/workflows/{wf_id}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    print(f'  PUT: {s}')
    api('POST', f'/api/v1/workflows/{wf_id}/activate')
    print('  Reativado')


def main():
    print(f'Restaurando prefixo models/ - {TS}')
    print('Motivo: backups 13-15/04 (funcionando) usavam models/gemini-2.5-flash')
    for wf_id, label in WORKFLOWS.items():
        process(wf_id, label)
    print('\nDONE')


if __name__ == '__main__':
    main()
