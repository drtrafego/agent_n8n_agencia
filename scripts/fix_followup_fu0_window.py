"""
Corrige a janela do FU0 na query do follow-up.
Remove o limite superior de 4h para FU0 — se o lead nunca recebeu follow-up
e o bot foi o último a falar há mais de 2h, envia FU0 independente de quando foi.
"""
import urllib.request, json, ssl, sys
sys.stdout.reconfigure(encoding='utf-8')
ctx = ssl.create_default_context()
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com/api/v1'

def api(path, method='GET', data=None):
    req = urllib.request.Request(BASE+path, headers={'X-N8N-API-KEY': KEY, 'Content-Type': 'application/json'}, method=method)
    if data: req.data = json.dumps(data).encode()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return json.loads(r.read())

wf = api('/workflows/aBMaCWPodLaS8I6L')

for n in wf['nodes']:
    if n['name'] == 'Buscar Leads':
        q = n['parameters']['query']

        # FU0 sem_lead_msg: remover limite superior de 4h
        old1 = "(COALESCE(c.followup_count,0) = 0\n          AND c.last_bot_msg_at < NOW() - INTERVAL '1 hour'\n          AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')\n        OR (COALESCE(c.followup_count,0) = 1\n          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'\n          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')\n      ))"
        new1 = "(COALESCE(c.followup_count,0) = 0\n          AND c.last_bot_msg_at < NOW() - INTERVAL '2 hours')\n        OR (COALESCE(c.followup_count,0) = 1\n          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'\n          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')\n      ))"

        # FU0 com_lead_msg: remover limite superior de 4h
        old2 = "(COALESCE(c.followup_count,0) = 0\n          AND c.last_bot_msg_at < NOW() - INTERVAL '1 hour'\n          AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')\n        OR (COALESCE(c.followup_count,0) = 1\n          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'\n          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')\n        OR (COALESCE(c.followup_count,0) = 2"
        new2 = "(COALESCE(c.followup_count,0) = 0\n          AND c.last_bot_msg_at < NOW() - INTERVAL '2 hours')\n        OR (COALESCE(c.followup_count,0) = 1\n          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'\n          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')\n        OR (COALESCE(c.followup_count,0) = 2"

        if old1 in q:
            q = q.replace(old1, new1)
            print('FU0 janela corrigida (sem_lead_msg)')
        else:
            print('AVISO: padrao 1 nao encontrado')

        if old2 in q:
            q = q.replace(old2, new2)
            print('FU0 janela corrigida (com_lead_msg)')
        else:
            print('AVISO: padrao 2 nao encontrado')

        n['parameters']['query'] = q
        break

payload = {'name': wf['name'], 'nodes': wf['nodes'], 'connections': wf['connections'],
           'settings': wf.get('settings', {}), 'staticData': wf.get('staticData')}
result = api('/workflows/aBMaCWPodLaS8I6L', method='PUT', data=payload)
print('Deploy OK:', result.get('id'), '| ativo:', result.get('active'))
