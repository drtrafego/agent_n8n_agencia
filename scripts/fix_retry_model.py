"""
Conecta Gemini Chat Model2 (gemini-2.5-flash-lite) ao SDR_retry.
Atualmente Gemini Chat Model3 (gemini-2.5-flash) conecta tanto ao SDR quanto ao SDR_retry,
causando falha dupla quando o thinking consome tokens.

Apos o fix:
- SDR         -> Gemini Chat Model3 (gemini-2.5-flash)   - poderoso, chama Calendar
- SDR_retry   -> Gemini Chat Model2 (gemini-2.5-flash-lite) - sempre responde, sem thinking
"""
import urllib.request, json, ssl, sys, io, copy, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'


def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def main():
    _, wf = api('GET', '/api/v1/workflows/JmiydfZHpeU8tnic')
    wf_up = copy.deepcopy(wf)
    conns = wf_up['connections']

    # 1. Remove SDR_retry da conexao do Gemini Chat Model3
    if 'Gemini Chat Model3' in conns:
        for output_type, lists in conns['Gemini Chat Model3'].items():
            if output_type == 'ai_languageModel':
                for i, lst in enumerate(lists):
                    original = len(lst)
                    lists[i] = [d for d in lst if d.get('node') != 'SDR_retry']
                    removed = original - len(lists[i])
                    if removed:
                        print(f'  Removido: Gemini Chat Model3 --[ai_languageModel]--> SDR_retry')

    # 2. Adiciona conexao Gemini Chat Model2 -> SDR_retry
    if 'Gemini Chat Model2' not in conns:
        conns['Gemini Chat Model2'] = {}
    if 'ai_languageModel' not in conns['Gemini Chat Model2']:
        conns['Gemini Chat Model2']['ai_languageModel'] = [[]]
    conns['Gemini Chat Model2']['ai_languageModel'][0].append({
        'node': 'SDR_retry',
        'type': 'ai_languageModel',
        'index': 0
    })
    print(f'  Adicionado: Gemini Chat Model2 --[ai_languageModel]--> SDR_retry')

    # 3. Confirma estado atual
    print('\nConexoes ai_languageModel atualizadas:')
    for src, outputs in conns.items():
        for output_type, lists in outputs.items():
            if output_type == 'ai_languageModel':
                for lst in lists:
                    for dest in lst:
                        if dest.get('node') in ('SDR', 'SDR_retry', 'Orquestrador'):
                            print(f'  {src} --> {dest["node"]}')

    # 4. Garante typeVersion e thinkingBudget corretos
    for n in wf_up['nodes']:
        if n.get('name') == 'Gemini Chat Model3':
            # Garante gemini-2.5-flash com thinkingBudget
            n['parameters']['modelName'] = 'gemini-2.5-flash'
            n['parameters']['options']['thinkingBudget'] = 0
            n['typeVersion'] = 1.2
            print(f'\n  Gemini Chat Model3 (SDR): gemini-2.5-flash, thinkingBudget=0')
        if n.get('name') == 'Gemini Chat Model2':
            n['parameters']['modelName'] = 'gemini-2.5-flash-lite'
            print(f'  Gemini Chat Model2 (SDR_retry): gemini-2.5-flash-lite')

    # Deploy
    api('POST', '/api/v1/workflows/JmiydfZHpeU8tnic/deactivate')
    s, resp = api('PUT', '/api/v1/workflows/JmiydfZHpeU8tnic', {
        'name': wf_up['name'],
        'nodes': wf_up['nodes'],
        'connections': wf_up['connections'],
        'settings': wf_up.get('settings', {}),
    })
    print(f'\nPUT: {s}')
    if s != 200:
        print(f'ERRO: {resp}')
        return
    api('POST', '/api/v1/workflows/JmiydfZHpeU8tnic/activate')
    print('Reativado')
    print('DONE')


if __name__ == '__main__':
    main()
