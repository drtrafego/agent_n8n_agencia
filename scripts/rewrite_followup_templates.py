"""
Reescreve os templates de mensagem do follow_up_agent_n8n_agencia_br
aplicando tom consultivo (CLOSER + Chaperon), tirando bordões hardcoded.
"""
import urllib.request, json, ssl, sys, io, datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiZDEwYWMxOGItYjI0Zi00MTNkLWEwN2ItYjdjZTE2MmJjY2FkIiwiaWF0IjoxNzc2MTE3NzE4fQ.2Oog3avp5jaD-9l5COuavA-VkNKq2MkRshvd9OvK2yE'
WF_ID = 'aBMaCWPodLaS8I6L'

NEW_QUERY = r"""WITH eligible AS (
  SELECT c.id AS crm_contact_id, c.telefone AS phone,
    SPLIT_PART(SPLIT_PART(COALESCE(c.nome,''), '|', 1), ' ', 1) AS nome,
    c.stage,
    COALESCE(c.followup_count, 0) AS followup_count,
    COALESCE(c.observacoes_sdr, '') AS obs,
    COALESCE(c.nicho, '') AS nicho
  FROM contacts c
  JOIN wa_contacts wac ON wac.wa_id = c.telefone
  JOIN wa_conversations wc ON wc.contact_id = wac.id
  WHERE wc.bot_active = true AND wc.status = 'open'
    AND c.stage NOT IN ('agendado','agendou','fechou','perdido','sem_interesse','realizada')
    AND c.last_bot_msg_at IS NOT NULL
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
    AND (
      (c.last_lead_msg_at IS NULL AND (
        (COALESCE(c.followup_count,0) = 0
          AND c.last_bot_msg_at < NOW() - INTERVAL '1 hour'
          AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')
        OR (COALESCE(c.followup_count,0) = 1
          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')
      ))
      OR
      (c.last_lead_msg_at IS NOT NULL AND (
        (COALESCE(c.followup_count,0) = 0
          AND c.last_bot_msg_at < NOW() - INTERVAL '1 hour'
          AND c.last_bot_msg_at > NOW() - INTERVAL '4 hours')
        OR (COALESCE(c.followup_count,0) = 1
          AND c.last_bot_msg_at < NOW() - INTERVAL '4 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '12 hours')
        OR (COALESCE(c.followup_count,0) = 2
          AND c.last_bot_msg_at < NOW() - INTERVAL '12 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '24 hours')
        OR (COALESCE(c.followup_count,0) = 3
          AND c.last_bot_msg_at < NOW() - INTERVAL '24 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '48 hours')
        OR (COALESCE(c.followup_count,0) = 4
          AND c.last_bot_msg_at < NOW() - INTERVAL '48 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '60 hours')
        OR (COALESCE(c.followup_count,0) = 5
          AND c.last_bot_msg_at < NOW() - INTERVAL '60 hours'
          AND c.last_bot_msg_at > NOW() - INTERVAL '72 hours')
      ))
    )
  LIMIT 20
),
reagend AS (
  SELECT c.id AS crm_contact_id, c.telefone AS phone,
    SPLIT_PART(SPLIT_PART(COALESCE(c.nome,''), '|', 1), ' ', 1) AS nome,
    c.stage,
    99 AS followup_count,
    COALESCE(c.observacoes_sdr, '') AS obs,
    COALESCE(c.nicho, '') AS nicho
  FROM contacts c
  JOIN wa_contacts wac ON wac.wa_id = c.telefone
  JOIN wa_conversations wc ON wc.contact_id = wac.id
  WHERE c.stage = 'agendado'
    AND c.scheduled_at IS NOT NULL
    AND c.scheduled_at < NOW() - INTERVAL '24 hours'
    AND wc.bot_active = true AND wc.status = 'open'
    AND (c.last_lead_msg_at IS NULL OR c.last_lead_msg_at < c.last_bot_msg_at)
  LIMIT 10
),
SELECT crm_contact_id, phone, followup_count,
  CASE
    -- FOLLOW-UP 0: CHECK-IN LEVE (1h)
    WHEN followup_count = 0 AND LENGTH(nicho) > 0 THEN
      'E aí ' || TRIM(nome) || E', me conta rapidinho: ficou claro como o agente encaixaria no seu trabalho de ' || TRIM(nicho) || E'? Se tiver alguma dúvida, é só mandar.'
    WHEN followup_count = 0 AND LENGTH(obs) >= 150 THEN
      TRIM(nome) || E', pela nossa conversa me pareceu que isso faz sentido pro que voce me contou. Faltou alguma coisa do meu lado?'
    WHEN followup_count = 0 THEN
      TRIM(nome) || E', só pra garantir que não ficou nada perdido aqui: ainda tá de pé a ideia de olhar como um agente de IA encaixaria no seu negócio?'

    -- FOLLOW-UP 1: INSIGHT (4h)
    WHEN followup_count = 1 AND LENGTH(nicho) > 0 THEN
      TRIM(nome) || E', pensei aqui. A maioria dos negócios de ' || TRIM(nicho) || E' que a gente atendeu tinha o mesmo gargalo: lead que chega e some antes de alguém responder. Quer que eu te mostre como resolvemos isso?'
    WHEN followup_count = 1 AND LENGTH(obs) >= 150 THEN
      TRIM(nome) || E', voltei aqui com uma ideia pro caso que você me descreveu. Em 30 minutos consigo te mostrar como ficaria no seu fluxo. Vale?'
    WHEN followup_count = 1 THEN
      TRIM(nome) || E', sem pressão: queria te mostrar uma coisa rápida, como o agente qualifica o lead sozinho antes de chegar na sua equipe. Tem 30 min essa semana?'

    -- FOLLOW-UP 2: MINI CASE (12h)
    WHEN followup_count = 2 AND LENGTH(nicho) > 0 THEN
      TRIM(nome) || E', lembrei de um caso de ' || TRIM(nicho) || E' que a gente atendeu recentemente. O dono perdia vários agendamentos por semana porque ninguém respondia fora do horário. Com o agente, zero perda nesses casos. Vale comparar com o seu?'
    WHEN followup_count = 2 AND LENGTH(obs) >= 150 THEN
      TRIM(nome) || E', um cliente nosso tinha exatamente o mesmo desafio que você comentou. Em uma semana o agente já estava fazendo o trabalho chato sozinho. Posso te contar como foi em 30 min?'
    WHEN followup_count = 2 THEN
      TRIM(nome) || E', um cliente nosso estava perdendo leads porque demorava pra responder. Colocamos o agente e em 7 dias ele já estava agendando reunião no automático. Vale conhecer como funcionou?'

    -- FOLLOW-UP 3: CALL DIRETA (24h)
    WHEN followup_count = 3 AND LENGTH(nicho) > 0 THEN
      TRIM(nome) || E', quer separar 30 min pra eu te mostrar o agente funcionando ao vivo pro tipo de negócio de ' || TRIM(nicho) || E'? Amanhã de manhã ou depois à tarde?'
    WHEN followup_count = 3 AND LENGTH(obs) >= 150 THEN
      TRIM(nome) || E', tenho 30 min pra te mostrar como o agente resolveria o que você me contou. Amanhã de manhã ou depois à tarde?'
    WHEN followup_count = 3 THEN
      TRIM(nome) || E', que tal separar 30 min pra eu te mostrar o agente ao vivo? Amanhã de manhã ou depois à tarde?'

    -- FOLLOW-UP 4: HONESTO (48h)
    WHEN followup_count = 4 AND LENGTH(nicho) > 0 THEN
      TRIM(nome) || E', acho que não deu match aqui e não vou insistir. Uma última coisa: se no futuro você achar que vale olhar como um agente encaixa em ' || TRIM(nicho) || E', dá um oi. Estarei por aqui.'
    WHEN followup_count = 4 AND LENGTH(obs) >= 150 THEN
      TRIM(nome) || E', percebi que você sumiu e não vou insistir mais. Se mudar de ideia e quiser retomar a conversa, é só chamar.'
    WHEN followup_count = 4 THEN
      TRIM(nome) || E', vou parar por aqui pra não te incomodar. Se no futuro quiser olhar como um agente de IA resolveria o atendimento aí, é só chamar.'

    -- FOLLOW-UP 5: DESPEDIDA (60h)
    WHEN followup_count = 5 THEN
      TRIM(nome) || E', última mensagem minha por aqui. Desejo sucesso no que você tá tocando. Se precisar de um agente no futuro, você já sabe onde me achar.'

    -- REAGENDAMENTO (apos scheduled_at + 24h)
    WHEN followup_count = 99 THEN
      TRIM(nome) || E', vi que a gente tinha um horário marcado mas não conseguiu rolar. Sem stress, acontece. Quer remarcar pra essa semana ou a próxima?'

    ELSE
      TRIM(nome) || E', tudo bem por aí? Só queria saber se ficou alguma dúvida sobre o agente. Estou por aqui.'
  END AS body
FROM (
  SELECT * FROM eligible
  UNION ALL
  SELECT * FROM reagend
) leads"""


def api(method, path, body=None):
    url = f'https://n8n.casaldotrafego.com{path}'
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('X-N8N-API-KEY', KEY)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=60) as r:
            return r.status, json.loads(r.read()) if r.status != 204 else None
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


def main():
    s, wf = api('GET', f'/api/v1/workflows/{WF_ID}')
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'D:/Bilder Ai/agent_n8n_agencia/backups/followup_templates_{ts}.json', 'w', encoding='utf-8') as f:
        json.dump(wf, f, ensure_ascii=False, indent=2)
    print(f'backup: followup_templates_{ts}.json')

    for n in wf['nodes']:
        if n.get('name') == 'Buscar Leads':
            old_len = len(n['parameters']['query'])
            n['parameters']['query'] = NEW_QUERY
            print(f'Query: {old_len} -> {len(NEW_QUERY)} chars')
            break

    api('POST', f'/api/v1/workflows/{WF_ID}/deactivate')
    s, r = api('PUT', f'/api/v1/workflows/{WF_ID}', {
        'name': wf['name'], 'nodes': wf['nodes'], 'connections': wf['connections'],
        'settings': {'executionOrder': wf['settings'].get('executionOrder'),
                     'callerPolicy': wf['settings'].get('callerPolicy')}
    })
    print(f'PUT: {s}')
    if s != 200:
        print('ERR:', r)
        return
    api('POST', f'/api/v1/workflows/{WF_ID}/activate')

    # Verify
    _, wf2 = api('GET', f'/api/v1/workflows/{WF_ID}')
    for n in wf2['nodes']:
        if n.get('name') == 'Buscar Leads':
            q = n['parameters']['query']
            print(f'remote query length: {len(q)}')
            print(f'  contains old bordao "78% dos clientes": {"78%" in q}')
            print(f'  contains new "me conta rapidinho": {"me conta rapidinho" in q}')
            print(f'  contains new "pensei aqui": {"pensei aqui" in q}')
            break
    print(f'active: {wf2.get("active")}')


if __name__ == '__main__':
    main()
