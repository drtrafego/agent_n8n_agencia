# -*- coding: utf-8 -*-
import urllib.request, json, ssl, sys
from datetime import datetime, timezone

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl._create_unverified_context()
SUPABASE_URL = "https://cfjyxdqrathzremxdkoi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA"
SB_H = {"apikey": SUPABASE_KEY, "Authorization": "Bearer " + SUPABASE_KEY}

def sb_get(path):
    req = urllib.request.Request(SUPABASE_URL + path, headers=SB_H)
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=30)
        return json.loads(resp.read().decode())
    except Exception as e:
        print("  [err] %s" % e)
        return []

now = datetime.now(timezone.utc)

print("=" * 70)
print("  ANALISE: LEADS NAS CONVERSATIONS SEM REENGAGEMENT")
print("=" * 70)

# Pegar todas as 14 conversations ativas
convs = sb_get("/rest/v1/wa_conversations?bot_active=eq.true&status=eq.open&select=id,contact_id,last_message,last_message_at,unread_count&limit=30")
print("\nTotal wa_conversations ativas: %d\n" % len(convs))

print("%-16s %-26s %-12s %3s %6s %6s  %-12s  %-50s" % (
    "phone", "nome", "stage", "fc", "h_bot", "h_lead", "REENG_STATUS", "problema"))
print("-" * 120)

for cv in convs:
    # get wa_contact
    wa_cs = sb_get("/rest/v1/wa_contacts?id=eq.%s&select=wa_id,name" % cv["contact_id"])
    if not wa_cs:
        print("%-16s %-26s %-12s %3s %6s %6s  %-12s  %s" % ("?", "?", "?", "?", "?", "?", "SEM WA_CONTACT", "wa_contact nao encontrado"))
        continue

    wa_id = wa_cs[0]["wa_id"]
    wa_name = wa_cs[0]["name"]

    # get contact CRM
    contacts = sb_get("/rest/v1/contacts?telefone=eq.%s&select=id,nome,stage,followup_count,last_bot_msg_at,last_lead_msg_at" % wa_id)

    if not contacts:
        last_msg = (cv.get("last_message") or "")[:60]
        print("%-16s %-26s %-12s %3s %6s %6s  %-12s  %s" % (
            wa_id[:16], wa_name[:26], "?", "?", "?", "?", "SEM_CRM", "nao tem entrada em contacts"))
        continue

    c = contacts[0]
    nome = (c.get("nome") or "")[:26]
    stage = (c.get("stage") or "")
    fc = c.get("followup_count") or 0
    last_bot = c.get("last_bot_msg_at")
    last_lead = c.get("last_lead_msg_at")

    h_bot = "N/A"
    h_lead = "N/A"
    reasons = []

    if stage in ("agendado", "agendou", "fechou", "perdido"):
        reasons.append("stage=%s" % stage)

    if fc >= 3:
        reasons.append("fc=%d>=3" % fc)

    if not last_bot:
        reasons.append("last_bot_msg=NULL")
        h_bot = "NULL"
    else:
        try:
            lbt = datetime.fromisoformat(last_bot.replace("Z", "+00:00"))
            age_h = (now - lbt).total_seconds() / 3600
            h_bot = "%.1fh" % age_h
            if age_h < 12:
                reasons.append("<12h(%.1fh)" % age_h)
            elif age_h > 72:
                reasons.append(">72h(%.1fh)" % age_h)
        except Exception as e:
            reasons.append("parse_err")

    if last_lead:
        try:
            llt = datetime.fromisoformat(last_lead.replace("Z", "+00:00"))
            age_lead_h = (now - llt).total_seconds() / 3600
            h_lead = "%.1fh" % age_lead_h
            if last_bot:
                lbt2 = datetime.fromisoformat(last_bot.replace("Z", "+00:00"))
                if llt > lbt2:
                    reasons.append("lead_respondeu(%.1fh_atras)" % age_lead_h)
        except:
            pass

    reeng_status = "ELEGIVEL" if not reasons else "BLOQUEADO"
    problema = "; ".join(reasons) if reasons else "-"

    print("%-16s %-26s %-12s %3d %6s %6s  %-12s  %s" % (
        wa_id[:16], nome[:26], stage[:12], fc, h_bot, h_lead, reeng_status, problema[:60]))

# Resumo dos que sao elegíveis agora
print("\n" + "=" * 70)
print("  RESUMO: QUANDO OS LEADS FICARAO ELEGIVEIS")
print("=" * 70)

leads_all = sb_get("/rest/v1/contacts?last_bot_msg_at=not.is.null&select=nome,telefone,stage,followup_count,last_bot_msg_at&order=last_bot_msg_at.desc&limit=20")
for c in leads_all:
    last_bot = c.get("last_bot_msg_at")
    if not last_bot:
        continue
    stage = c.get("stage") or ""
    if stage in ("agendado", "agendou", "fechou", "perdido"):
        continue
    fc = c.get("followup_count") or 0
    if fc >= 3:
        continue
    try:
        lbt = datetime.fromisoformat(last_bot.replace("Z", "+00:00"))
        age_h = (now - lbt).total_seconds() / 3600
        if 12 > age_h > 0:
            falta_h = 12 - age_h
            print("  %s | %s — elegivel em %.1fh" % (c.get("telefone","?"), (c.get("nome") or "")[:30], falta_h))
        elif age_h >= 12 and age_h <= 72:
            print("  %s | %s — JA ELEGIVEL (%.1fh)" % (c.get("telefone","?"), (c.get("nome") or "")[:30], age_h))
    except:
        pass
