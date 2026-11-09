import sys, json, re, html, time, os, urllib.request, urllib.parse, uuid
TOKEN = open(sys.argv[1]).read().strip()
POST_URL, TEXT_FILE, SERVICE_FILE = sys.argv[2], sys.argv[3], sys.argv[4]
EXTRA = sys.argv[5:]
CHAT = "8646732556"
SIGN = ''
API = "https://api.telegram.org/bot" + TOKEN + "/"
MAXF = 48 * 1024 * 1024
UA = {"User-Agent": "Mozilla/5.0"}
MANUAL = "Медиа из исходного поста получить не удалось – забрать вручную"

def log(*a): print(*a, flush=True)

def api(method, fields, files=None):
    if files:
        b = uuid.uuid4().hex
        body = b""
        for k, v in fields.items():
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, (fn, data) in files.items():
            body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n\r\n'.encode() + data + b"\r\n"
        body += f"--{b}--\r\n".encode()
        req = urllib.request.Request(API + method, data=body, headers={"Content-Type": "multipart/form-data; boundary=" + b})
    else:
        req = urllib.request.Request(API + method, data=urllib.parse.urlencode(fields).encode())
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        try: d = json.load(e)
        except Exception: d = {"ok": False, "description": f"HTTP {e.code}"}
    except Exception as e:
        d = {"ok": False, "description": type(e).__name__ + ": " + str(e).replace(TOKEN, "[TOKEN]")}
    log(method, d.get("ok"), d.get("description", ""))
    if d.get("ok") and method.startswith("send"):
        res = d.get("result")
        for m in (res if isinstance(res, list) else [res]):
            if isinstance(m, dict) and "message_id" in m: POST_IDS.append(m["message_id"])
    time.sleep(1.5)
    return d.get("ok")

POST_IDS = []

def get(url, limit=MAXF):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = r.read(limit + 1)
    return None if len(data) > limit else data

def media_from_post(post_url):
    m = re.match(r"https://t\.me/(?:s/)?([\w\d_]+)/(\d+)", post_url)
    if not m: return [], ""
    try:
        page = get(f"https://t.me/{m.group(1)}/{m.group(2)}?embed=1&mode=tme", 5 * 1024 * 1024).decode("utf-8", "replace")
    except Exception as e:
        log("t.me fetch fail", type(e).__name__)
        return [], MANUAL
    items, too_big = [], "Media is too big" in page
    for tag in re.finditer(r'<a class="tgme_widget_message_(photo_wrap|video_player)[^"]*"[^>]*>(.*?)</a>|<a class="tgme_widget_message_photo_wrap[^>]*>', page, re.S):
        chunk = tag.group(0)
        if "video_player" in chunk[:80]:
            v = re.search(r'<video[^>]+src="([^"]+)"', chunk)
            if v: items.append(("video", html.unescape(v.group(1))))
            elif "too big" in chunk: too_big = True
        else:
            p = re.search(r"background-image:url\('([^']+)'\)", chunk)
            if p: items.append(("photo", html.unescape(p.group(1))))
    seen, out = set(), []
    for t, u in items:
        if u not in seen: seen.add(u); out.append((t, u))
    global SRC_LINKS
    tx = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', page, re.S)
    SRC_LINKS = [html.unescape(l) for l in re.findall(r'href="(https?://[^"]+)"', tx.group(1) if tx else "") if "t.me/" not in l and "telegram.org" not in l]
    return out[:10], ("Видео слишком большое – забрать из исходного поста" if too_big else "")

def plain_len(h): return len(html.unescape(re.sub(r"<[^>]+>", "", h)))

SRC_LINKS = []
SIGNS = {
    "softicx": '<tg-emoji emoji-id="5251489485283140234">✈️</tg-emoji><b><a href="https://t.me/+haLyYIwgZKc5NTQy">SofticX</a></b>',
    "зелёный steam": '<tg-emoji emoji-id="5454014450468142883">🎮</tg-emoji><b><a href="https://t.me/+AAhgPheOQyIzOTZi">Зелёный Steam</a></b>',
}
service = open(SERVICE_FILE, encoding="utf-8").read().strip()
_ch = re.sub(r"<[^>]+>", "", service.split("\n")[0]).strip().lower().replace("зеленый", "зелёный")
SIGN = SIGNS.get(_ch, "")
text = open(TEXT_FILE, encoding="utf-8").read().strip()
if SIGN and "t.me/+haLyYIwgZKc5NTQy" not in text and "t.me/+AAhgPheOQyIzOTZi" not in text:
    text += "\n\n" + SIGN
items, note = media_from_post(POST_URL)
log("media found:", [t for t, _ in items], note)

files = []
for t, u in items:
    try:
        d = get(u)
        if d: files.append((t, d))
        else: note = (note + "; " if note else "") + "видео/фото больше 48 МБ – забрать из исходного поста"
    except Exception as e:
        log("download fail", t, type(e).__name__)
if items and not files and not note:
    note = MANUAL
if not files and EXTRA:
    for u in EXTRA:
        try:
            d = get(u, 10 * 1024 * 1024)
            if d:
                files.append(("photo", d))
                if note: note += " (сейчас приложена картинка из статьи)"
                break
        except Exception as e:
            log("extra download fail", type(e).__name__)

cap_ok = plain_len(text) <= 1024
sent = False
if len(files) == 1:
    t, d = files[0]
    m = "sendPhoto" if t == "photo" else "sendVideo"
    f = {"chat_id": CHAT}
    if cap_ok: f.update(caption=text, parse_mode="HTML")
    if t == "video": f["supports_streaming"] = "true"
    sent = api(m, f, {t: ("f.jpg" if t == "photo" else "f.mp4", d)})
    if sent and not cap_ok:
        api("sendMessage", {"chat_id": CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"})
elif len(files) > 1:
    media, up = [], {}
    for i, (t, d) in enumerate(files):
        e = {"type": t, "media": f"attach://m{i}"}
        if i == 0 and cap_ok: e.update(caption=text, parse_mode="HTML")
        media.append(e); up[f"m{i}"] = (f"m{i}." + ("jpg" if t == "photo" else "mp4"), d)
    sent = api("sendMediaGroup", {"chat_id": CHAT, "media": json.dumps(media)}, up)
    if sent and not cap_ok:
        api("sendMessage", {"chat_id": CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"})
if not files and (items or EXTRA):
    cands = [(t, u) for t, u in items] or [("photo", u) for u in EXTRA]
    for t, u in cands[:1]:
        m = "sendPhoto" if t == "photo" else "sendVideo"
        f = {"chat_id": CHAT, t: u}
        if cap_ok: f.update(caption=text, parse_mode="HTML")
        sent = api(m, f)
        if sent:
            if not items and note: note += " (сейчас приложена картинка из статьи)"
            if not cap_ok:
                api("sendMessage", {"chat_id": CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"})
if not sent:
    if files: note = MANUAL
    api("sendMessage", {"chat_id": CHAT, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"})
lost = [l for l in dict.fromkeys(SRC_LINKS) if l.split("?")[0].rstrip("/") not in html.unescape(text)]
if SRC_LINKS and len(lost) == len(dict.fromkeys(SRC_LINKS)):
    log("WARNING: links from source post are missing in the post:", lost)
    note = (note + "\n" if note else "") + "⚠️ Ссылка из исходного поста не вставлена в пост: " + " ".join(lost)
if note: service += "\n" + html.escape(note)
ids = ",".join(map(str, POST_IDS))
kb = {"inline_keyboard": [[{"text": "📢 В SofticX", "callback_data": "a|sx|" + ids},
                           {"text": "🎮 В Зелёный Steam", "callback_data": "a|gs|" + ids}],
                          [{"text": "✏️ Заголовки", "callback_data": "h0||" + ids}],
                          [{"text": "✖️ Не надо", "callback_data": "r||" + ids}]]}
f = {"chat_id": CHAT, "text": service, "parse_mode": "HTML", "disable_web_page_preview": "true"}
if POST_IDS and len("h0||" + ids) <= 64:
    f["reply_markup"] = json.dumps(kb)
    text_id = POST_IDS[0] if (files and cap_ok) else POST_IDS[-1]
    f["reply_parameters"] = json.dumps({"message_id": text_id, "allow_sending_without_reply": True})
api("sendMessage", f)
