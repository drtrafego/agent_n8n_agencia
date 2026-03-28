#!/usr/bin/env python3
"""
Full flow test: Next.js webhook -> Supabase -> n8n -> bot-send -> inbox
Sends 3 messages from test phone to simulate a conversation.
"""
import urllib.request, json, ssl, time, sys, io, hashlib, hmac
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ─── Config ───────────────────────────────────────────────────────────
WEBHOOK_URL = "https://agente.casaldotrafego.com/api/whatsapp/webhook"
APP_SECRET  = "994ad53d1a0e894e01bef243a88dfde6"
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
N8N_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJlYTQzZjAyNS1iMzg0LTQ1MDMtODZjOC1iYWExNGNlMzQ3OGUiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMjBmOThjMGMtZmI4NC00OGQyLWI5OTMtZDU2NzMzODllMDFiIiwiaWF0IjoxNzczMDY4MTI3LCJleHAiOjE3NzU2MjA4MDB9.hm8UFgTEuOoOoWeAXPpasRXbuXcKkkSx4sQN2CYfM6U"
SB_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

TEST_PHONE = "5511988880071"
TEST_NAME  = "TESTE_FluxoCompleto"

MESSAGES = [
    "Ola, boa tarde! Vi o anuncio de voces sobre agente de IA",
    "Tenho uma loja de roupas online, recebo muitas perguntas no WhatsApp",
    "Quero saber como funciona e quanto custa",
]

# ─── Helpers ──────────────────────────────────────────────────────────

def log(tag, msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"  [{ts}] [{tag}] {msg}")

def supabase_get(path):
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    req = urllib.request.Request(url, headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    })
    resp = urllib.request.urlopen(req, context=ctx, timeout=30)
    return json.loads(resp.read().decode('utf-8'))

def supabase_delete(table, filter_str):
    """DELETE from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filter_str}"
    req = urllib.request.Request(url, method='DELETE', headers=SB_HEADERS)
    try:
        urllib.request.urlopen(req, context=ctx, timeout=30)
        return True
    except Exception as e:
        log("WARN", f"Delete {table} failed: {e}")
        return False

def send_webhook(phone, name, text, msg_index=0):
    """Send a message through the Next.js webhook with proper HMAC signature."""
    ts = str(int(time.time()))
    wamid = f"wamid.TEST{ts}{msg_index:03d}"

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "106071169159774",
            "changes": [{
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "5511996681596",
                        "phone_number_id": "115216611574100"
                    },
                    "contacts": [{"profile": {"name": name}, "wa_id": phone}],
                    "messages": [{
                        "from": phone,
                        "id": wamid,
                        "timestamp": ts,
                        "text": {"body": text},
                        "type": "text"
                    }]
                },
                "field": "messages"
            }]
        }]
    }

    body = json.dumps(payload)
    sig = "sha256=" + hmac.new(APP_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()

    req = urllib.request.Request(
        WEBHOOK_URL,
        data=body.encode('utf-8'),
        method='POST',
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig,
        }
    )

    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=60)
        status = resp.getcode()
        resp_body = resp.read().decode('utf-8')
        return status, resp_body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        return 0, str(e)

def check_wa_messages(phone, expected_min=1, max_wait=10):
    """Check wa_messages table for messages from this phone."""
    # First get the contact id
    contacts = supabase_get(f"wa_contacts?wa_id=eq.{phone}")
    if not contacts:
        return None, []
    contact_id = contacts[0]['id']
    msgs = supabase_get(f"wa_messages?contact_id=eq.{contact_id}&order=created_at.asc")
    return contacts[0], msgs

def wait_for_bot_response(phone, prev_outbound_count, max_wait=120):
    """Wait for n8n to process and bot response to appear in wa_messages."""
    waited = 0
    while waited < max_wait:
        time.sleep(8)
        waited += 8
        log("WAIT", f"Checking for bot response... ({waited}s / {max_wait}s)")

        contacts = supabase_get(f"wa_contacts?wa_id=eq.{phone}")
        if not contacts:
            continue
        contact_id = contacts[0]['id']

        # Check outbound messages from bot
        msgs = supabase_get(
            f"wa_messages?contact_id=eq.{contact_id}&direction=eq.outbound&sent_by=eq.bot&order=created_at.desc&limit=5"
        )

        if len(msgs) > prev_outbound_count:
            return msgs[0]

        # Also check n8n_chat_histories as fallback indicator
        n8n_msgs = supabase_get(
            f"n8n_chat_histories?session_id=eq.{phone}&order=created_at.desc&limit=3"
        )
        for entry in n8n_msgs:
            m = entry.get('message', {})
            if isinstance(m, str):
                try: m = json.loads(m)
                except: continue
            if m.get('type') == 'ai':
                content = m.get('content', '')
                if content and content.strip().upper() != 'STOP':
                    log("INFO", f"Found AI response in n8n_chat_histories (bot-send may have failed)")
                    # Still wait a bit more for wa_messages
                    time.sleep(5)
                    msgs2 = supabase_get(
                        f"wa_messages?contact_id=eq.{contact_id}&direction=eq.outbound&sent_by=eq.bot&order=created_at.desc&limit=5"
                    )
                    if len(msgs2) > prev_outbound_count:
                        return msgs2[0]
                    return {"body": content, "_source": "n8n_chat_histories_only"}
    return None

def check_wa_contacts(phone):
    """Check wa_contacts table."""
    return supabase_get(f"wa_contacts?wa_id=eq.{phone}")

def check_wa_conversations(phone):
    """Check wa_conversations table."""
    contacts = supabase_get(f"wa_contacts?wa_id=eq.{phone}")
    if not contacts:
        return []
    return supabase_get(f"wa_conversations?contact_id=eq.{contacts[0]['id']}")

def count_outbound_bot(phone):
    """Count existing outbound bot messages for this phone."""
    contacts = supabase_get(f"wa_contacts?wa_id=eq.{phone}")
    if not contacts:
        return 0
    contact_id = contacts[0]['id']
    msgs = supabase_get(
        f"wa_messages?contact_id=eq.{contact_id}&direction=eq.outbound&sent_by=eq.bot"
    )
    return len(msgs)


# ─── Cleanup ──────────────────────────────────────────────────────────

def cleanup_test_data():
    """Remove previous test data for this phone number."""
    log("CLEAN", f"Removing previous test data for {TEST_PHONE}...")

    # Get contact id first
    contacts = supabase_get(f"wa_contacts?wa_id=eq.{TEST_PHONE}")
    if contacts:
        cid = contacts[0]['id']
        # Delete messages
        supabase_delete("wa_messages", f"contact_id=eq.{cid}")
        # Delete conversations
        supabase_delete("wa_conversations", f"contact_id=eq.{cid}")
        # Delete contact
        supabase_delete("wa_contacts", f"wa_id=eq.{TEST_PHONE}")

    # Clean n8n tables for this phone
    supabase_delete("n8n_chat_histories", f"session_id=eq.{TEST_PHONE}")
    supabase_delete("contacts", f"telefone=eq.{TEST_PHONE}")

    log("CLEAN", "Done.")


# ─── Main Test ────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  FULL FLOW TEST: Webhook -> Supabase -> n8n -> bot-send")
    print(f"  Phone: {TEST_PHONE} | Name: {TEST_NAME}")
    print(f"  Messages: {len(MESSAGES)}")
    print("=" * 60)
    print()

    # Step 0: Cleanup
    cleanup_test_data()
    time.sleep(2)

    results = {
        "webhook_sent": [],
        "messages_saved": [],
        "bot_responses": [],
        "contact_ok": False,
        "conversation_ok": False,
    }

    for i, msg_text in enumerate(MESSAGES):
        print()
        print(f"{'─' * 60}")
        print(f"  MESSAGE {i+1}/{len(MESSAGES)}: {msg_text}")
        print(f"{'─' * 60}")

        # Count existing bot responses before sending
        prev_bot_count = count_outbound_bot(TEST_PHONE)

        # ── Step 1: Send webhook ──
        log("SEND", f"Sending via webhook...")
        status, resp_body = send_webhook(TEST_PHONE, TEST_NAME, msg_text, i)
        log("SEND", f"Response: HTTP {status} | {resp_body}")

        webhook_ok = status == 200
        results["webhook_sent"].append(webhook_ok)

        if not webhook_ok:
            log("FAIL", f"Webhook returned HTTP {status}. Aborting this message.")
            results["messages_saved"].append(False)
            results["bot_responses"].append(None)
            continue

        # ── Step 2: Verify message saved ──
        time.sleep(2)
        log("CHECK", "Checking wa_messages table...")
        contact, msgs = check_wa_messages(TEST_PHONE)

        inbound_msgs = [m for m in msgs if m.get('direction') == 'inbound']
        msg_saved = len(inbound_msgs) >= (i + 1)
        results["messages_saved"].append(msg_saved)

        if msg_saved:
            last_inbound = inbound_msgs[-1]
            log("OK", f"Message saved: id={last_inbound['id']}, body='{last_inbound.get('body', '')[:80]}'")
        else:
            log("FAIL", f"Expected {i+1} inbound messages, found {len(inbound_msgs)}")

        # ── Step 3: Wait for n8n + bot response ──
        log("WAIT", "Waiting for n8n processing + bot response...")
        bot_msg = wait_for_bot_response(TEST_PHONE, prev_bot_count, max_wait=120)

        if bot_msg:
            body_text = bot_msg.get('body', '')
            if '<contexto' in body_text:
                body_text = body_text.split('<contexto')[0].strip()
            display = body_text[:200] + "..." if len(body_text) > 200 else body_text
            source = bot_msg.get('_source', 'wa_messages')
            log("OK", f"Bot response ({source}): {display}")
            results["bot_responses"].append(body_text)
        else:
            log("FAIL", "No bot response within timeout")
            results["bot_responses"].append(None)

        # Brief pause between messages
        if i < len(MESSAGES) - 1:
            log("WAIT", "Pausing 5s before next message...")
            time.sleep(5)

    # ── Step 4: Final checks on all tables ──
    print()
    print(f"{'=' * 60}")
    print("  FINAL TABLE CHECKS")
    print(f"{'=' * 60}")

    # wa_contacts
    print()
    log("CHECK", "wa_contacts:")
    contacts = check_wa_contacts(TEST_PHONE)
    if contacts:
        c = contacts[0]
        results["contact_ok"] = True
        log("OK", f"  id={c['id']}, wa_id={c['wa_id']}, name={c.get('name')}, phone={c.get('phone')}")
        log("OK", f"  created_at={c.get('created_at')}, updated_at={c.get('updated_at')}")
    else:
        log("FAIL", "  Contact NOT found in wa_contacts")

    # wa_conversations
    print()
    log("CHECK", "wa_conversations:")
    convs = check_wa_conversations(TEST_PHONE)
    if convs:
        cv = convs[0]
        results["conversation_ok"] = True
        log("OK", f"  id={cv['id']}, contact_id={cv['contact_id']}")
        log("OK", f"  last_message={str(cv.get('last_message',''))[:100]}")
        log("OK", f"  last_message_at={cv.get('last_message_at')}")
        log("OK", f"  unread_count={cv.get('unread_count')}, bot_active={cv.get('bot_active')}")
    else:
        log("FAIL", "  Conversation NOT found in wa_conversations")

    # wa_messages (all)
    print()
    log("CHECK", "wa_messages (all for this contact):")
    if contacts:
        all_msgs = supabase_get(
            f"wa_messages?contact_id=eq.{contacts[0]['id']}&order=created_at.asc"
        )
        for m in all_msgs:
            direction = m.get('direction', '?')
            sent_by = m.get('sent_by', '?')
            body_preview = str(m.get('body', ''))[:100]
            log("MSG", f"  [{direction}|{sent_by}] {body_preview}")
        log("INFO", f"  Total messages: {len(all_msgs)} (inbound: {sum(1 for m in all_msgs if m.get('direction')=='inbound')}, outbound: {sum(1 for m in all_msgs if m.get('direction')=='outbound')})")

    # n8n contacts table
    print()
    log("CHECK", "contacts (n8n bot table):")
    n8n_contacts = supabase_get(f"contacts?telefone=eq.{TEST_PHONE}")
    if n8n_contacts:
        nc = n8n_contacts[0]
        log("OK", f"  nome={nc.get('nome')}, source={nc.get('source')}, stage={nc.get('stage')}")
        log("OK", f"  observacoes_sdr={str(nc.get('observacoes_sdr',''))[:150]}")
    else:
        log("INFO", "  Not found in contacts table (n8n may not have created it yet)")

    # n8n_chat_histories
    print()
    log("CHECK", "n8n_chat_histories:")
    chat_hist = supabase_get(f"n8n_chat_histories?session_id=eq.{TEST_PHONE}&order=created_at.asc")
    log("INFO", f"  {len(chat_hist)} entries")
    for entry in chat_hist[-6:]:  # show last 6
        m = entry.get('message', {})
        if isinstance(m, str):
            try: m = json.loads(m)
            except: m = {"raw": m}
        mtype = m.get('type', '?')
        content = str(m.get('content', m.get('raw', '')))[:120]
        log("HIST", f"  [{mtype}] {content}")

    # ── Summary ──
    print()
    print("=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    total_pass = 0
    total_tests = 0

    for i, msg_text in enumerate(MESSAGES):
        total_tests += 3
        w = "PASS" if results["webhook_sent"][i] else "FAIL"
        s = "PASS" if results["messages_saved"][i] else "FAIL"
        b = "PASS" if results["bot_responses"][i] else "FAIL"
        total_pass += sum([results["webhook_sent"][i], results["messages_saved"][i], bool(results["bot_responses"][i])])
        print(f"  Msg {i+1}: webhook={w} | saved={s} | bot_response={b}")

    total_tests += 2
    c_status = "PASS" if results["contact_ok"] else "FAIL"
    cv_status = "PASS" if results["conversation_ok"] else "FAIL"
    total_pass += results["contact_ok"] + results["conversation_ok"]
    print(f"  wa_contacts: {c_status}")
    print(f"  wa_conversations: {cv_status}")
    print()
    print(f"  TOTAL: {total_pass}/{total_tests} passed")
    print("=" * 60)


if __name__ == "__main__":
    main()
