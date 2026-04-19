"""
Popula o campo placement para todos os leads que já têm adset_id mas não têm placement.
Usa a Meta Ads API para buscar o targeting do adset.
"""
import urllib.request, json, ssl, sys, time
sys.stdout.reconfigure(encoding='utf-8')

ctx = ssl.create_default_context()
META_TOKEN = 'EAANCYW8PaTQBQWzye2CR2hLTZBJ68EZCDMyOPCu22JGE03XM34yg34NlckIlrit3AGAbO8Yw4JsbiucnOLdoKjLaeP8DZCQ0thJOWIiq37MLXLZAEHYHlGbmbwfF0duYzT7rKbjYGfNNsp3jdtpqvHt2ZCk7YnUxXF9P9ZCdsF0Uo2ALL0Y2cjl4iUw9OzF1U21AZDZD'
SUPABASE_URL = 'https://cfjyxdqrathzremxdkoi.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNmanl4ZHFyYXRoenJlbXhka29pIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3Mzc5NTk2NiwiZXhwIjoyMDg5MzcxOTY2fQ.emqwy588MEnDPqTw8ns3C7_28pVmNT-eqa4GndawQoA'

POSITION_LABELS = {
    'feed': 'Facebook Feed',
    'story': 'Facebook Stories',
    'video_feeds': 'Facebook Video',
    'marketplace': 'Marketplace',
    'search': 'Facebook Search',
    'stream': 'Instagram Feed',
    'reels': 'Reels',
    'explore': 'Instagram Explore',
    'profile_feed': 'Instagram Profile',
}

def resolve_placement(targeting):
    parts = []
    platforms = targeting.get('publisher_platforms', [])
    if 'instagram' in platforms:
        pos = targeting.get('instagram_positions', [])
        if not pos or 'stream' in pos:
            parts.append('Instagram Feed')
        if 'story' in pos:
            parts.append('Instagram Stories')
        if 'reels' in pos and 'Reels' not in parts:
            parts.append('Reels')
        if 'explore' in pos:
            parts.append('Instagram Explore')
    if 'facebook' in platforms:
        pos = targeting.get('facebook_positions', [])
        if not pos or 'feed' in pos:
            parts.append('Facebook Feed')
        if 'story' in pos and 'Facebook Stories' not in parts:
            parts.append('Facebook Stories')
    if not parts and platforms:
        label_map = {'instagram': 'Instagram', 'facebook': 'Facebook',
                     'audience_network': 'Audience Network', 'messenger': 'Messenger'}
        return ', '.join(label_map.get(p, p) for p in platforms)
    return ', '.join(parts) if parts else None

def supabase_get(path):
    req = urllib.request.Request(
        SUPABASE_URL + path,
        headers={'apikey': SUPABASE_KEY, 'Authorization': 'Bearer ' + SUPABASE_KEY}
    )
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read())

def supabase_patch(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        SUPABASE_URL + path,
        data=body, method='PATCH',
        headers={
            'apikey': SUPABASE_KEY,
            'Authorization': 'Bearer ' + SUPABASE_KEY,
            'Content-Type': 'application/json',
            'Prefer': 'return=minimal'
        }
    )
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return r.status

def meta_get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
        return json.loads(r.read())

# 1. Buscar leads com adset_id mas sem placement
leads = supabase_get('/rest/v1/contacts?select=id,telefone,adset_id&adset_id=not.is.null&placement=is.null&limit=200')
print(f'Leads para processar: {len(leads)}')

# Cache de adset → placement para não repetir chamadas
adset_cache = {}
ok = skipped = errors = 0

for lead in leads:
    adset_id = lead.get('adset_id')
    contact_id = lead.get('id')

    if not adset_id:
        skipped += 1
        continue

    try:
        if adset_id not in adset_cache:
            url = f'https://graph.facebook.com/v21.0/{adset_id}?fields=targeting&access_token={META_TOKEN}'
            data = meta_get(url)
            targeting = data.get('targeting', {})
            placement = resolve_placement(targeting)
            adset_cache[adset_id] = placement
            time.sleep(0.2)  # rate limit suave
        else:
            placement = adset_cache[adset_id]

        if placement:
            status = supabase_patch(f'/rest/v1/contacts?id=eq.{contact_id}', {'placement': placement})
            print(f'  [{contact_id}] {lead["telefone"][-4:]} → {placement} ({status})')
            ok += 1
        else:
            skipped += 1

    except Exception as e:
        print(f'  ERRO [{contact_id}]: {e}')
        errors += 1

print()
print(f'Concluido: {ok} atualizados, {skipped} sem placement, {errors} erros')
