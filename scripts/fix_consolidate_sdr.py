# -*- coding: utf-8 -*-
"""
Consolidacao do agente SDR:
1. Remove memoria duplicada do Orquestrador (n8n_chat_auto - dead weight)
2. Remove conexao do automaticos (desativado) com Orquestrador
3. Simplifica system message do Orquestrador para roteador puro
"""
import urllib.request, json, ssl, datetime, io, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
WF_ID = 'JmiydfZHpeU8tnic'
BASE = 'https://n8n.casaldotrafego.com'


def api(method, path, body=None):
    req = urllib.request.Request(
        f'{BASE}{path}',
        data=json.dumps(body).encode() if body else None,
        method=method
    )
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
        return r.status, json.loads(r.read()) if r.status != 204 else None


# Orquestrador vira roteador puro: sempre chama SDR, STOP so se lead mandou STOP
NEW_ORQ_SM = (
    "Missao: encaminhar a mensagem do lead para a ferramenta SDR.\n\n"
    "REGRA UNICA: SEMPRE acione a ferramenta SDR. Sem excecao.\n\n"
    "STOP: responda apenas a string STOP se a mensagem do lead for exatamente "
    "STOP, cancelar ou sair. Nenhuma outra condicao.\n\n"
    "SAIDA: retorne unicamente o texto que a ferramenta SDR devolver. Nada mais."
)


def main():
    print('=' * 60)
    print('SDR CONSOLIDATION')
    print('=' * 60)

    _, wf = api('GET', f'/api/v1/workflows/{WF_ID}')
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = f'D:/Bilder Ai/agent_n8n_agencia/backups/sdr_consolidation_{ts}.json'
    with open(backup, 'w', encoding='utf-8') as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print(f'backup: {backup}')

    # 1. Remover conexoes de Orquestrador: memoria e automaticos mortos
    conns = wf['connections']
    dead_nodes = {'Postgres Chat Memory1', 'automaticos', 'OpenAI Chat Model2', 'Postgres Chat Memory2'}
    for src in dead_nodes:
        if src in conns:
            new_outputs = {}
            for dtype, dlists in conns[src].items():
                filtered = []
                for dlist in dlists:
                    clean = [d for d in dlist if d.get('node') != 'Orquestrador']
                    filtered.append(clean)
                new_outputs[dtype] = filtered
            conns[src] = new_outputs
            print(f'  desconectado: {src} -> Orquestrador')

    # 2. Simplificar system message do Orquestrador
    for n in wf['nodes']:
        if n['name'] == 'Orquestrador':
            old = n['parameters']['options'].get('systemMessage', '')
            n['parameters']['options']['systemMessage'] = NEW_ORQ_SM
            print(f'  Orquestrador SM: {len(old)} -> {len(NEW_ORQ_SM)} chars')

    # 3. Deploy
    print('\nDeployando...')
    api('POST', f'/api/v1/workflows/{WF_ID}/deactivate')
    s, r = api('PUT', f'/api/v1/workflows/{WF_ID}', {
        'name': wf['name'],
        'nodes': wf['nodes'],
        'connections': wf['connections'],
        'settings': wf['settings']
    })
    print(f'  PUT: {s}')
    if s != 200:
        print(f'  ERR: {str(r)[:400]}')
        return
    api('POST', f'/api/v1/workflows/{WF_ID}/activate')
    print('  reativado')

    # 4. Verificar
    _, wf2 = api('GET', f'/api/v1/workflows/{WF_ID}')
    for n in wf2['nodes']:
        if n['name'] == 'Orquestrador':
            sm = n['parameters']['options'].get('systemMessage', '')
            print(f'\nVerificacao Orquestrador:')
            print(f'  SM chars: {len(sm)}')
            print(f'  contem REGRA UNICA: {"REGRA UNICA" in sm}')
    print(f'  active: {wf2.get("active")}')
    print('\nDONE')


if __name__ == '__main__':
    main()
