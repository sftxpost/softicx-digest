import sys,json,re,html,time,urllib.request as R,urllib.parse as P,uuid
T=open(sys.argv[1]).read().strip();U,PF,SF=sys.argv[2:5];C="8646732556";A="https://api.telegram.org/bot"+T+"/";IDS=[];ER=[]
def api(m,f,fl=None):
    if fl:
        b=uuid.uuid4().hex;d=b"".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k,v in f.items())
        for k,(n,x) in fl.items(): d+=f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{n}"\r\n\r\n'.encode()+x+b"\r\n"
        q=R.Request(A+m,data=d+f"--{b}--\r\n".encode(),headers={"Content-Type":"multipart/form-data; boundary="+b})
    else: q=R.Request(A+m,data=P.urlencode(f).encode())
    try: r=json.load(R.urlopen(q,timeout=120))
    except Exception as e:
        try: r=json.load(e)
        except Exception: r={"ok":False,"description":type(e).__name__}
    print(m,r.get("ok"),r.get("description",""));time.sleep(1);ER.append(r.get("description",""))
    if r.get("ok") and f.get("text")!=svc:
        x=r.get("result");[IDS.append(i["message_id"]) for i in (x if isinstance(x,list) else [x]) if isinstance(i,dict)]
    return r.get("ok")
def get(u,l=48<<20):
    for k in range(3):
        try: d=R.urlopen(R.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=60).read(l+1);return None if len(d)>l else d
        except Exception:
            if k==2: raise
            time.sleep(3*(k+1))
SG={"softicx":'<tg-emoji emoji-id="5251489485283140234">✈️</tg-emoji><b><a href="https://t.me/+haLyYIwgZKc5NTQy">SofticX</a></b>',
"зелёный steam":'<tg-emoji emoji-id="5454014450468142883">🎮</tg-emoji><b><a href="https://t.me/+AAhgPheOQyIzOTZi">Зелёный Steam</a></b>'}
svc=open(SF,encoding="utf-8").read().strip();txt=open(PF,encoding="utf-8").read().strip()
s=SG.get(re.sub(r"<[^>]+>","",svc.split("\n")[0]).strip().lower().replace("зеленый","зелёный"))
if s and "t.me/+" not in txt: txt+="\n\n"+s
items,links,note=[],[],""
m=re.match(r"https://t\.me/(?:s/)?(\w+)/(\d+)",U)
if m:
    try:
        pg=get(f"https://t.me/{m[1]}/{m[2]}?embed=1&mode=tme",5<<20).decode("utf-8","replace")
        for g in re.finditer(r'<a class="tgme_widget_message_(photo_wrap|video_player)[^>]*>(.*?)</a>|<a class="tgme_widget_message_photo_wrap[^>]*>',pg,re.S):
            c=g[0];v=re.search(r'<video[^>]+src="([^"]+)"',c);p=re.search(r"background-image:url\('([^']+)'\)",c)
            if "video_player" in c[:80]:
                if v: items.append(("video",html.unescape(v[1])))
                else:
                    note="Видео слишком большое – в посте превью, видео забрать из исходного поста"
                    if p: items.append(("photo",html.unescape(p[1])))
            elif p: items.append(("photo",html.unescape(p[1])))
        if not items and "tgme_widget_message_error" in pg: note="Исходный пост недоступен (удалён или закрыт) – медиа забрать вручную"
        tx=re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',pg,re.S)
        links=[html.unescape(l) for l in re.findall(r'href="(https?://[^"]+)"',tx[1] if tx else "") if "t.me/" not in l]
    except Exception as e: note="Медиа получить не удалось ("+type(e).__name__+") – забрать вручную"
items=list(dict.fromkeys(items))[:10];files=[]
for t,u in items:
    try:
        d=get(u)
        if d: files.append((t,d))
        else: note="Видео больше 48 МБ – забрать из исходного поста"
    except Exception as e: note=f"Не скачалось медиа ({type(e).__name__}) – забрать из исходного поста"
ok=len(html.unescape(re.sub(r"<[^>]+>","",txt)))<=1024;H={"parse_mode":"HTML"};sent=False
if len(files)==1:
    t,d=files[0];f={"chat_id":C};f.update(caption=txt,**H) if ok else 0
    sent=api("sendPhoto" if t=="photo" else "sendVideo",f,{t:("f.jpg" if t=="photo" else "f.mp4",d)}) or api("sendDocument",f,{"document":("f.jpg" if t=="photo" else "f.mp4",d)})
elif files:
    md=[dict(type=t,media=f"attach://m{i}",**({"caption":txt,**H} if i==0 and ok else {})) for i,(t,d) in enumerate(files)]
    for _ in range(2):
        sent=api("sendMediaGroup",{"chat_id":C,"media":json.dumps(md)},{f"m{i}":(f"m{i}."+("jpg" if t=="photo" else "mp4"),d) for i,(t,d) in enumerate(files)})
        if sent: break
if files and not sent: note+="\nМедиа не отправилось: "+(ER[-1] if ER else "")
if not sent or not ok: api("sendMessage",{"chat_id":C,"text":txt,"link_preview_options":json.dumps({"is_disabled":True}),**H})
if links and not any(l.split("?")[0].rstrip("/") in html.unescape(txt) for l in links): note+="\n⚠️ Ссылка из исходного поста не вставлена: "+" ".join(links)
if note: svc+="\n"+html.escape(note.strip())
i=",".join(map(str,IDS));f={"chat_id":C,"text":svc,"link_preview_options":json.dumps({"is_disabled":True}),**H}
if IDS and len(i)<60:
    f["reply_markup"]=json.dumps({"inline_keyboard":[[{"text":"📢 В SofticX","callback_data":"a|sx|"+i},{"text":"🎮 В Зелёный Steam","callback_data":"a|gs|"+i}],[{"text":"✏️ Заголовки","callback_data":"h0||"+i}],[{"text":"✖️ Не надо","callback_data":"r||"+i}]]})
    f["reply_parameters"]=json.dumps({"message_id":IDS[0] if files and ok else IDS[-1],"allow_sending_without_reply":True})
api("sendMessage",f)
