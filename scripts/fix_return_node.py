"""
Corrige o ReturnToSDR para devolver o output do AI Agent no formato
que o n8n toolWorkflow espera: campo 'output' com o texto.
"""
import urllib.request, json, ssl, sys, io, copy, time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'

# ReturnToSDR: extrai agentResponse e devolve como 'output'
# para que o n8n toolWorkflow passe o texto direto ao agente SDR
RETURN_CODE = (
    "const resp = items[0]?.json?.agentResponse || '';\n"
    "return [{ json: { output: resp } }];"
)


def api(method, path, body=None):
    url = f'{BASE}{path}'
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


def main():
    print('Corrigindo ReturnToSDR...')
    _, wf = api('GET', '/api/v1/workflows/6EJoeyC63gDEffu2')
    wf_up = copy.deepcopy(wf)

    for n in wf_up['nodes']:
        if n.get('name') == 'ReturnToSDR':
            n['parameters']['jsCode'] = RETURN_CODE
            print(f'  ReturnToSDR: codigo atualizado')
            print(f'  Code: {RETURN_CODE}')

    # Verifica estrutura final
    print('\n  Verificando estrutura do Calendar:')
    for n in wf_up['nodes']:
        if n.get('name') in ('Check CreateEvent', 'ReturnToSDR', 'Evento Criado?'):
            print(f'    {n["name"]}: ok')

    print(f'  Conexao FALSE branch: {wf_up["connections"].get("Evento Criado?",{}).get("main",[[],[]])[1]}')

    # Deploy
    api('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/deactivate')
    s, resp = api('PUT', '/api/v1/workflows/6EJoeyC63gDEffu2', {
        'name': wf_up['name'],
        'nodes': wf_up['nodes'],
        'connections': wf_up['connections'],
        'settings': wf_up.get('settings', {}),
    })
    print(f'\n  PUT: {s}')
    if s != 200:
        print(f'  ERRO: {resp}')
        return False
    api('POST', '/api/v1/workflows/6EJoeyC63gDEffu2/activate')
    print('  Reativado')
    return True


if __name__ == '__main__':
    ok = main()

    if ok:
        print('\n--- Verificacao pos-deploy ---')
        import urllib.request as ur
        import json, ssl
        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl.CERT_NONE
        req = ur.Request(f'{BASE}/api/v1/workflows/6EJoeyC63gDEffu2', method='GET')
        req.add_header('X-N8N-API-KEY', KEY)
        with ur.urlopen(req, context=ctx2, timeout=30) as r:
            wf2 = json.loads(r.read())
        for n in wf2['nodes']:
            if n.get('name') == 'ReturnToSDR':
                code = n.get('parameters', {}).get('jsCode', '')
                print(f'  ReturnToSDR code: {code}')
        print('DONE')
