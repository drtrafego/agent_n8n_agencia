# -*- coding: utf-8 -*-
import urllib.request, json, ssl

ctx = ssl._create_unverified_context()
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {
    "apikey": SUPABASE_KEY,
    "Authorization": "Bearer " + SUPABASE_KEY,
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

PHONES = ["5511999990099", "5491151133210"]

def sb_get(path):
    req = urllib.request.Request(SUPABASE_URL + path, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        return []

def sb_delete(path):
    req = urllib.request.Request(SUPABASE_URL + path, method="DELETE", headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx)
        data = resp.read().decode()
        return json.loads(data) if data.strip() else []
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print("    HTTP %d: %s" % (e.code, body[:200]))
        return None
    except Exception as e:
        print("    Erro: %s" % e)
        return None

print("=" * 60)
print("  LIMPEZA DE DADOS DE TESTE")
print("  Phones: %s" % ", ".join(PHONES))
print("=" * 60)

for phone in PHONES:
    print("\n--- Phone: %s ---" % phone)

    # 1. Get wa_contacts id
    wa_contacts = sb_get("/rest/v1/wa_contacts?wa_id=eq.%s&select=id,name" % phone)
    wa_contact_ids = [c["id"] for c in wa_contacts]
    print("  wa_contacts encontrados: %d %s" % (len(wa_contact_ids), [c.get("name") for c in wa_contacts]))

    # 2. Get conversation ids
    conv_ids = []
    for wc_id in wa_contact_ids:
        convs = sb_get("/rest/v1/wa_conversations?contact_id=eq.%s&select=id" % wc_id)
        conv_ids += [c["id"] for c in convs]
    print("  wa_conversations encontradas: %d" % len(conv_ids))

    # 3. Delete wa_messages
    msg_count = 0
    for conv_id in conv_ids:
        msgs = sb_delete("/rest/v1/wa_messages?conversation_id=eq.%s" % conv_id)
        if msgs:
            msg_count += len(msgs)
    print("  wa_messages deletadas: %d" % msg_count)

    # 4. Delete wa_conversations
    conv_count = 0
    for wc_id in wa_contact_ids:
        deleted = sb_delete("/rest/v1/wa_conversations?contact_id=eq.%s" % wc_id)
        if deleted:
            conv_count += len(deleted)
    print("  wa_conversations deletadas: %d" % conv_count)

    # 5. Delete wa_contacts
    deleted_wa = sb_delete("/rest/v1/wa_contacts?wa_id=eq.%s" % phone)
    print("  wa_contacts deletados: %d" % (len(deleted_wa) if deleted_wa else 0))

    # 6. Delete contacts (CRM)
    deleted_crm = sb_delete("/rest/v1/contacts?telefone=eq.%s" % phone)
    print("  contacts (CRM) deletados: %d" % (len(deleted_crm) if deleted_crm else 0))

    # 7. Delete n8n_chat_histories
    deleted_hist = sb_delete("/rest/v1/n8n_chat_histories?session_id=eq.%s" % phone)
    print("  n8n_chat_histories deletados: %d" % (len(deleted_hist) if deleted_hist else 0))

    # 8. Delete n8n_chat_sdr
    deleted_sdr = sb_delete("/rest/v1/n8n_chat_sdr?session_id=eq.%s" % phone)
    print("  n8n_chat_sdr deletados: %d" % (len(deleted_sdr) if deleted_sdr else 0))

    # 9. Delete n8n_chat_auto
    deleted_auto = sb_delete("/rest/v1/n8n_chat_auto?session_id=eq.%s" % phone)
    print("  n8n_chat_auto deletados: %d" % (len(deleted_auto) if deleted_auto else 0))

    # 10. Delete wa_webhook_logs (by phone field if exists)
    try:
        deleted_logs = sb_delete("/rest/v1/wa_webhook_logs?phone=eq.%s" % phone)
        print("  wa_webhook_logs deletados: %d" % (len(deleted_logs) if deleted_logs else 0))
    except:
        pass  # table may not have phone column

print("\n" + "=" * 60)
print("  LIMPEZA CONCLUIDA!")
print("=" * 60)
