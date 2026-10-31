"""SofticX: бесплатная часть.
Каждый час читает каналы-источники, отсеивает мусор и повторы за сутки
(с помощью бесплатной модели OpenRouter) и обновляет digest/latest.json.
Claude потом читает этот файл и пишет посты.
"""
import os, re, json, html, time, urllib.request, datetime as dt

CH = ["petrovtel", "media1337", "blokirovki_runeta", "provod", "retra", "SteamNetwork"]
MSK = dt.timezone(dt.timedelta(hours=3))
OUT = "digest/latest.json"
KEEP_HOURS = 24
LOOKBACK_HOURS = 2          # читаем с запасом, повторы по ссылкам отсекаются
UA = {"User-Agent": "Mozilla/5.0"}
KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
MODEL = os.environ.get("OPENROUTER_MODEL", "").strip()


def log(*a):
    print(*a, flush=True)


def get(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def clean(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def read_channels(start):
    posts = []
    for ch in CH:
        blocks, url = [], f"https://t.me/s/{ch}"
        try:
            for _ in range(4):
                page = get(url, timeout=30).decode("utf-8", "replace")
                blocks = page.split('class="tgme_widget_message_wrap')[1:] + blocks
                ids = re.findall(r'data-post="[^"/]+/(\d+)"', page)
                tms = re.findall(r'<time datetime="([^"]+)"', page)
                if not ids or not tms or dt.datetime.fromisoformat(tms[0]).astimezone(MSK) < start:
                    break
                url = f"https://t.me/s/{ch}?before={min(map(int, ids))}"
        except Exception as e:
            log(f"{ch}: недоступен ({type(e).__name__})")
            if not blocks:
                continue
        seen = set()
        for b in blocks:
            p = re.search(r'data-post="([^"]+)"', b)
            t = re.search(r'<time datetime="([^"]+)"', b)
            if not p or not t or p.group(1) in seen:
                continue
            seen.add(p.group(1))
            ts = dt.datetime.fromisoformat(t.group(1)).astimezone(MSK)
            if ts < start:
                continue
            tx = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', b, re.S)
            raw = tx.group(1) if tx else ""
            links = [html.unescape(l) for l in re.findall(r'href="(https?://[^"]+)"', raw)
                     if "t.me/" not in l and "telegram.org" not in l]
            ph = b.count("tgme_widget_message_photo_wrap")
            vd = b.count("tgme_widget_message_video_player")
            media = ", ".join(x for x in [f"{ph} фото" if ph else "", f"{vd} видео" if vd else ""] if x) or "без медиа"
            posts.append({
                "url": f"https://t.me/{p.group(1)}",
                "channel": ch,
                "time": ts.isoformat(),
                "media": media,
                "links": list(dict.fromkeys(links))[:5],
                "text": clean(raw)[:600],
            })
    return posts


def pick_model():
    if MODEL:
        return MODEL
    try:
        data = json.loads(get("https://openrouter.ai/api/v1/models", timeout=30))["data"]
        free = [m for m in data if m.get("id", "").endswith(":free")]
        free.sort(key=lambda m: -(m.get("context_length") or 0))
        prefer = ("deepseek", "qwen", "llama", "gemma", "mistral")
        for p in prefer:
            for m in free:
                if p in m["id"]:
                    return m["id"]
        return free[0]["id"] if free else ""
    except Exception as e:
        log("не удалось получить список моделей:", type(e).__name__)
        return ""


PROMPT = """Ты помощник редактора Telegram-канала о технологиях и интернете для обычных людей в России.
Ниже НОВЫЕ публикации из каналов-источников и список тем, которые УЖЕ были за последние сутки.

Задача:
1. Выкинь рекламу, розыгрыши, промокоды, подборки, мемы без новости, продвижение каналов и ботов.
2. Выкинь новости, которые повторяют тему из списка «УЖЕ БЫЛО» (то же событие, даже другими словами), если нет существенно нового факта.
3. Склей одну и ту же историю из разных каналов в одну тему.
4. Для каждой оставшейся темы верни: ids (номера публикаций этой темы), title (суть одной строкой по-русски, без эмодзи), games (true, если тема про игры).

Ответь ТОЛЬКО JSON без пояснений: {"topics":[{"ids":[1,4],"title":"...","games":false}]}
Если ничего не осталось: {"topics":[]}

УЖЕ БЫЛО:
%s

НОВЫЕ ПУБЛИКАЦИИ:
%s"""


def ask_llm(model, new_posts, old_titles):
    listing = "\n".join(f"{i}. [{p['channel']}] {p['text'][:400]}" for i, p in enumerate(new_posts, 1))
    prompt = PROMPT % ("\n".join(f"- {t}" for t in old_titles) or "- (пусто)", listing)
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.1}).encode()
    for attempt in range(3):
        try:
            r = json.loads(get("https://openrouter.ai/api/v1/chat/completions", data=body, timeout=120,
                               headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"}))
            txt = r["choices"][0]["message"]["content"]
            m = re.search(r"\{.*\}", txt, re.S)
            return json.loads(m.group(0))["topics"]
        except Exception as e:
            log("модель не ответила:", type(e).__name__, str(e)[:200])
            time.sleep(10)
    return None


def main():
    now = dt.datetime.now(MSK)
    try:
        state = json.load(open(OUT, encoding="utf-8"))
    except Exception:
        state = {"topics": [], "seen_urls": []}
    cutoff = now - dt.timedelta(hours=KEEP_HOURS)
    state["topics"] = [t for t in state["topics"] if dt.datetime.fromisoformat(t["first_seen"]) >= cutoff]
    seen = set(state.get("seen_urls", []))

    posts = read_channels(now - dt.timedelta(hours=LOOKBACK_HOURS))
    new = [p for p in posts if p["url"] not in seen]
    log(f"новых публикаций: {len(new)}")

    if new:
        model = pick_model() if KEY else ""
        log("модель:", model or "нет – без фильтра")
        topics = ask_llm(model, new, [t["title"] for t in state["topics"]]) if model else None
        if topics is None:      # запасной вариант: каждая публикация – отдельная тема, Claude разберётся
            topics = [{"ids": [i], "title": p["text"][:120].replace("\n", " "), "games": p["channel"] == "SteamNetwork"}
                      for i, p in enumerate(new, 1)]
        for t in topics:
            items = [new[i - 1] for i in t.get("ids", []) if isinstance(i, int) and 1 <= i <= len(new)]
            if not items:
                continue
            state["topics"].append({
                "first_seen": now.isoformat(timespec="minutes"),
                "title": str(t.get("title", ""))[:200],
                "games": bool(t.get("games")),
                "posts": items,
            })
        seen.update(p["url"] for p in new)

    state["updated"] = now.isoformat(timespec="minutes")
    state["seen_urls"] = sorted(seen)[-3000:]
    os.makedirs("digest", exist_ok=True)
    json.dump(state, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log(f"тем в выжимке за сутки: {len(state['topics'])}")


if __name__ == "__main__":
    main()
