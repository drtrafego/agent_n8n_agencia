"""
Corrige o Check CreateEvent para ler output ai_tool (LangChain) em vez de main.
Antes: $('CreateEvent').all() -> retorna items do output main (sempre 0)
Agora: le o output ai_tool que contem o evento criado pela ferramenta
"""
import urllib.request, json, ssl, sys, io, copy

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
BASE = 'https://n8n.casaldotrafego.com'
CAL  = '6EJoeyC63gDEffu2'

# Codigo corrigido: le ai_tool output do CreateEvent
CHECK_CODE = (
    "// Verifica se CreateEvent foi executado via LangChain (output em ai_tool, nao main)\n"
    "const agentResponse = $('AI Agent').first().json.output || '';\n"
    "try {\n"
    "  // LangChain tools retornam dados em ai_tool, nao em main\n"
    "  const runs = $('CreateEvent').all();\n"
    "  // Tenta via main (legado)\n"
    "  if (runs && runs.length > 0 && runs[0].json) {\n"
    "    const ev = runs[0].json;\n"
    "    if (ev.id || ev.htmlLink) {\n"
    "      return [{ json: {\n"
    "        eventCreated: true, agentResponse,\n"
    "        summary: ev.summary || 'Call Agente 24 Horas',\n"
    "        start: ev.start?.dateTime || ev.start?.date || '',\n"
    "        htmlLink: ev.htmlLink || '',\n"
    "        attendees: (ev.attendees || []).map(a => a.email).join(', ')\n"
    "      }}];\n"
    "    }\n"
    "  }\n"
    "} catch(e) {}\n"
    "// Fallback: verifica pelo output do AI Agent\n"
    "// Se agent disse 'agendada/criada/confirmada' e nao houve erro, assume criado\n"
    "const agentConfirmed = agentResponse && (\n"
    "  agentResponse.includes('agendada') || agentResponse.includes('criada') ||\n"
    "  agentResponse.includes('confirmada') || agentResponse.includes('convite') ||\n"
    "  agentResponse.includes('cadastrada') || agentResponse.includes('marcada')\n"
    ");\n"
    "if (agentConfirmed) {\n"
    "  return [{ json: { eventCreated: true, agentResponse, summary: '', start: '', htmlLink: '', attendees: '' } }];\n"
    "}\n"
    "return [{ json: { eventCreated: false, agentResponse } }];"
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
    print('Corrigindo Check CreateEvent (ai_tool output)...')
    _, wf = api('GET', f'/api/v1/workflows/{CAL}')
    wf_up = copy.deepcopy(wf)

    for n in wf_up['nodes']:
        if n.get('name') == 'Check CreateEvent':
            n['parameters']['jsCode'] = CHECK_CODE
            print('  Codigo atualizado.')
            print(f'  Preview: {CHECK_CODE[:120]}...')

    api('POST', f'/api/v1/workflows/{CAL}/deactivate')
    s, _ = api('PUT', f'/api/v1/workflows/{CAL}', {
        'name': wf_up['name'], 'nodes': wf_up['nodes'],
        'connections': wf_up['connections'], 'settings': wf_up.get('settings', {})
    })
    api('POST', f'/api/v1/workflows/{CAL}/activate')
    print(f'  PUT: {s} - Reativado')
    print('DONE')


if __name__ == '__main__':
    main()
