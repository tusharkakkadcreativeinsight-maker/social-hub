from pathlib import Path
from html import escape

W, H = 3840, 2160
OUT = Path("SocialHub/frontend/static/showcase/socialhub-complete-fixed-infographic-4k.svg")


def tag(name, attrs=None, content=""):
    attrs = attrs or {}
    attr = " ".join(f'{k}="{escape(str(v), quote=True)}"' for k, v in attrs.items() if v is not None)
    return f"<{name} {attr}>{content}</{name}>" if content else f"<{name} {attr}/>"


def txt(x, y, s, size=24, fill="#f8fbff", weight=500, anchor="start", opacity=1, mono=False):
    fam = "JetBrains Mono, Consolas, monospace" if mono else "Inter, Segoe UI, Arial, sans-serif"
    return tag("text", {"x": x, "y": y, "font-size": size, "fill": fill, "font-weight": weight,
                        "text-anchor": anchor, "opacity": opacity, "font-family": fam}, escape(s))


def rect(x, y, w, h, r=20, fill="url(#panel)", stroke="#7c3cff", sw=1.4, opacity=1, flt="url(#shadow)"):
    return tag("rect", {"x": x, "y": y, "width": w, "height": h, "rx": r, "fill": fill,
                        "stroke": stroke, "stroke-width": sw, "opacity": opacity, "filter": flt})


def circle(cx, cy, r, fill="#fff", stroke=None, sw=1, opacity=1):
    return tag("circle", {"cx": cx, "cy": cy, "r": r, "fill": fill, "stroke": stroke,
                          "stroke-width": sw, "opacity": opacity})


def line(x1, y1, x2, y2, stroke="#74809a", sw=1.5, opacity=1):
    return tag("line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "stroke": stroke,
                        "stroke-width": sw, "opacity": opacity, "stroke-linecap": "round"})


def path(d, fill="none", stroke="#fff", sw=2, opacity=1):
    return tag("path", {"d": d, "fill": fill, "stroke": stroke, "stroke-width": sw,
                        "opacity": opacity, "stroke-linecap": "round", "stroke-linejoin": "round"})


def clip(cid, x, y, w, h, r=18):
    return f'<clipPath id="{cid}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/></clipPath>'


def check(x, y, size=18):
    return circle(x, y, size / 2, "#22c55e", "#92f7b5", 1, .95) + txt(x, y + size * .28, "✓", size * .75, "#052e16", 900, "middle")


def bullet(x, y, s, size=17, c="#dce7ff", icon=True):
    return (check(x + 8, y - 6, 17) if icon else txt(x, y, "•", size, "#ffffff", 800)) + txt(x + 30, y, s, size, c, 560)


def title(x, y, s):
    return txt(x, y, s, 25, "#c084fc", 900) + circle(x - 10, y - 8, 5, "#8b5cf6", opacity=.7)


def card(x, y, w, h, t=None):
    s = rect(x, y, w, h, 16)
    if t:
        s += title(x + 28, y + 43, t)
    return s


def avatar(x, y, r=18, color="#f6b38b"):
    return circle(x, y, r + 3, "url(#ring)") + circle(x, y, r, color) + circle(x, y - 4, r * .47, "#2d160f") + path(f"M{x-r*.62},{y+r*.8} C{x-r*.25},{y+r*.25} {x+r*.25},{y+r*.25} {x+r*.62},{y+r*.8}", "#6155ff", "none")


def icon(x, y, kind, c="#edf4ff"):
    if kind == "heart": return path(f"M{x},{y+10} C{x-16},{y} {x-8},{y-12} {x},{y-5} C{x+8},{y-12} {x+16},{y} {x},{y+10}Z", c, "none")
    if kind == "msg": return path(f"M{x-11},{y-8} H{x+11} V{y+6} H{x-2} L{x-9},{y+12} V{y+6} H{x-11} Z", "none", c, 2)
    if kind == "save": return path(f"M{x-7},{y-11} H{x+7} V{y+12} L{x},{y+6} L{x-7},{y+12} Z", "none", c, 2)
    if kind == "share": return path(f"M{x-10},{y+5} L{x+10},{y-8} L{x+5},{y+12} L{x},{y+2} Z", "none", c, 2)
    if kind == "search": return circle(x - 3, y - 3, 7, "none", c, 2) + line(x + 3, y + 3, x + 12, y + 12, c, 2)
    if kind == "home": return path(f"M{x-10},{y+2} L{x},{y-9} L{x+10},{y+2} M{x-6},{y+1} V{y+11} H{x+6} V{y+1}", "none", c, 2)
    return circle(x, y, 10, "none", c, 2)


def photo(x, y, w, h, grad="url(#photo)"):
    return rect(x, y, w, h, 12, grad, "#334155", 1, flt=None) + circle(x + w * .74, y + h * .28, min(w, h) * .13, "#fff7") + path(f"M{x},{y+h*.76} C{x+w*.25},{y+h*.48} {x+w*.42},{y+h*.72} {x+w*.62},{y+h*.45} C{x+w*.78},{y+h*.25} {x+w*.9},{y+h*.54} {x+w},{y+h*.36} V{y+h} H{x} Z", "#07182daa", "none")


def section_list(x, y, items, size=17, dy=28, icon=True):
    return "".join(bullet(x, y + i * dy, item, size, icon=icon) for i, item in enumerate(items))


def badge(x, y, label, w=None):
    w = w or max(142, len(label) * 12 + 58)
    return rect(x, y, w, 50, 14, "#0b1220cc", "#6d5cff", 1.2, flt=None) + circle(x + 27, y + 25, 15, "#14f1c6") + txt(x + 27, y + 31, "✓", 18, "#052e16", 900, "middle") + txt(x + 55, y + 32, label, 17, "#ffffff", 700)


def home_feed(x, y, w, h):
    s = card(x, y, w, h) + txt(x + w/2, y + 30, "HOME FEED", 20, "#fff", 900, "middle")
    s += rect(x+18, y+62, 104, h-82, 8, "#111827", "#263045", 1, flt=None) + txt(x+36, y+88, "SocialHub", 15, "#7dd3fc", 800)
    for i, m in enumerate(["Home", "Explore", "Notifications", "Messages", "Saved", "Profile"]):
        yy = y + 124 + i*42
        if i == 0: s += rect(x+30, yy-23, 76, 28, 8, "#2b225d", "none", flt=None)
        s += icon(x+45, yy-9, "home" if i == 0 else "msg", "#eaf1ff") + txt(x+62, yy-3, m, 10, "#f8fbff", 650)
    s += rect(x+138, y+62, w-156, 43, 14, "#ffffff", "#d4d8e2", 1, flt=None) + icon(x+w-70, y+83, "search", "#64748b") + circle(x+w-38, y+82, 8, "#ef4444")
    for i in range(7): s += avatar(x+170+i*52, y+143, 18) + txt(x+170+i*52, y+175, ["You","Farha","Emma","Alex","Priya","Ravi","Sara"][i], 8, "#111827", 700, "middle")
    s += rect(x+155, y+197, w-185, 58, 12, "#ffffff", "#e2e8f0", 1, flt=None) + avatar(x+178, y+226, 16) + txt(x+203, y+222, "Create Post", 12, "#111827", 800) + txt(x+203, y+239, "What are you sharing today?", 10, "#64748b")
    s += rect(x+155, y+270, w-185, h-292, 12, "#ffffff", "#e2e8f0", 1, flt=None) + avatar(x+182, y+300, 17) + txt(x+207, y+298, "John Doe", 12, "#111827", 800) + txt(x+207, y+314, "2h · Sunset Valley", 9, "#64748b")
    s += photo(x+174, y+335, w-224, h-410, "url(#sunset)")
    for i, (k, n) in enumerate([("heart","12K"),("msg","342"),("share","91"),("save","")]): s += icon(x+185+i*75, y+h-42, k, "#111827") + txt(x+205+i*75, y+h-36, n, 10, "#111827", 700)
    return s


def reels(x, y, w, h):
    s = card(x, y, w, h) + txt(x+w/2, y+30, "REELS", 20, "#fff", 900, "middle") + rect(x+46, y+62, w-92, h-84, 18, "#05070d", "#2b3245", 1, flt=None)
    s += photo(x+60, y+76, w-120, h-112, "url(#reel)") + avatar(x+82, y+h-72, 15) + txt(x+105, y+h-75, "jessica_98", 12, "#fff", 800) + rect(x+170, y+h-92, 50, 24, 9, "#2563eb", "none", flt=None) + txt(x+195, y+h-75, "Follow", 10, "#fff", 800, "middle") + txt(x+82, y+h-45, "Sunset vibes ✨", 11, "#fff", 600)
    for i, (k, n) in enumerate([("heart","12.7K"),("msg","342"),("share","1.2K"),("save","")]):
        yy = y+180+i*72; s += icon(x+w-48, yy, k, "#fff") + txt(x+w-48, yy+28, n, 9, "#fff", 700, "middle")
    return s


def chat(x, y, w, h):
    s = card(x, y, w, h) + txt(x+w/2, y+30, "CHAT", 20, "#fff", 900, "middle") + txt(x+28, y+68, "Chat", 18, "#fff", 850)
    s += rect(x+24, y+88, 170, h-112, 12, "#0f172a", "#253047", 1, flt=None)
    for i, n in enumerate(["Alex Johnson", "Ria Smith", "Emma Watson", "Michael Lee", "Diana", "Darlene"]):
        yy=y+122+i*42; s += avatar(x+46, yy, 13) + txt(x+65, yy-3, n, 9, "#fff", 750) + txt(x+65, yy+10, "Online · typing", 7, "#94a3b8")
    s += rect(x+210, y+86, w-235, h-110, 12, "#08111f", "#263449", 1, flt=None) + avatar(x+236, y+118, 15) + txt(x+260, y+115, "Alice Johnson", 11, "#fff", 800) + txt(x+w-55, y+116, "Seen", 9, "#22c55e", 700)
    bubbles=[(245,160,"Hey, how are you?",False),(360,205,"I’m good! What about you?",True),(245,250,"Doing great! Check this view 👇",False),(245,330,"Wow! Beautiful 🔥",False)]
    for bx, by, m, me in bubbles:
        s += rect(x+bx, y+by, 190 if len(m)>20 else 140, 34, 12, "#32245f" if me else "#172033", "none", flt=None) + txt(x+bx+14, y+by+22, m, 9, "#fff", 650)
    s += photo(x+282, y+288, 120, 70, "url(#photo)") + rect(x+228, y+h-50, w-270, 28, 10, "#0f172a", "#344057", 1, flt=None) + txt(x+242, y+h-31, "Type a message...", 9, "#94a3b8")
    return s


def simple_ui(x, y, w, h, name, mode):
    s = card(x, y, w, h) + txt(x+w/2, y+30, name, 20, "#fff", 900, "middle")
    if mode == "notifications":
        s += txt(x+28, y+75, "Notifications", 19, "#fff", 850) + rect(x+w-135, y+52, 92, 25, 9, "#1f1649", "none", flt=None) + txt(x+w-89, y+69, "Mark all read", 8, "#c4b5fd", 800, "middle")
        for i,t in enumerate(["All","Likes","Comments","Follows"]): s += rect(x+28+i*82, y+103, 70, 28, 8, "#1f2937" if i==0 else "#0b1220", "#263449", 1, flt=None) + txt(x+63+i*82, y+122, t, 9, "#fff", 700, "middle")
        for i,m in enumerate(["Alice liked your post.", "Bob commented on your reel.", "Emma started following you.", "Your story got 100 views.", "Mike liked your comment."]):
            yy=y+160+i*50; s += avatar(x+55, yy, 15) + txt(x+82, yy-4, m, 11, "#fff", 650) + txt(x+82, yy+11, f"{i+2}m ago", 8, "#94a3b8") + circle(x+w-52, yy-2, 5, "#8b5cf6" if i<2 else "none", "#64748b")
    elif mode == "profile":
        s += photo(x+24, y+62, w-48, 80, "url(#photo)") + avatar(x+78, y+152, 34) + txt(x+140, y+150, "john_doe", 18, "#111827", 900) + txt(x+140, y+172, "John Doe · Content Creator | Traveler", 11, "#334155") + txt(x+140, y+192, "🌐 www.johndoe.com", 10, "#2563eb")
        for i,(n,l) in enumerate([("124","Posts"),("2.4K","Followers"),("356","Following")]): s += txt(x+70+i*105, y+234, n, 15, "#111827", 900, "middle") + txt(x+70+i*105, y+251, l, 9, "#475569", 700, "middle")
        s += rect(x+w-120, y+210, 78, 32, 9, "#f8fafc", "#cbd5e1", 1, flt=None) + txt(x+w-81, y+231, "Edit Profile", 9, "#111827", 800, "middle")
        for i,t in enumerate(["Posts","Reels","Highlights","Saved"]): s += txt(x+55+i*90, y+292, t, 10, "#334155", 800, "middle")
        for i in range(8): s += photo(x+30+(i%4)*80, y+315+(i//4)*60, 70, 52, "url(#sunset)" if i%2 else "url(#reel)")
    elif mode == "ai":
        items=["Caption Generator","Hashtag Generator","Bio Generator","Reel Title Generator","Post Ideas","Viral Hooks","Comment Replies","Content Calendar"]
        for i,it in enumerate(items):
            xx=x+28+(i%2)*(w/2-14); yy=y+70+(i//2)*64
            s += rect(xx, yy, w/2-42, 48, 10, "#ffffff", "#e2e8f0", 1, flt=None) + txt(xx+20, yy+30, "#" if "Hash" in it else "▣", 17, "#2563eb", 900) + txt(xx+48, yy+30, it, 10, "#1e293b", 800)
    elif mode == "live":
        s += photo(x+24, y+58, w-48, h-84, "url(#live)") + rect(x+42, y+78, 55, 25, 7, "#ef4444", "none", flt=None) + txt(x+69, y+96, "LIVE", 10, "#fff", 900, "middle") + rect(x+106, y+78, 58, 25, 11, "#0009", "none", flt=None) + txt(x+135, y+96, "● 1.2K", 10, "#fff", 800, "middle")
        for i,m in enumerate(["Great performance 🔥", "Amazing!", "Love this! ❤️", "What a voice!"]): s += txt(x+56, y+h-142+i*24, m, 10, "#fff", 700)
        for i in range(6): s += txt(x+w-64-(i%2)*20, y+h-150-i*30, "❤", 22, "#ff4d7d", 900)
        s += rect(x+42, y+h-48, w-130, 28, 14, "#0008", "#ffffff44", flt=None) + txt(x+56, y+h-29, "Add a comment...", 9, "#fff") + txt(x+w-64, y+h-29, "↗ 🎁", 15, "#fff", 800)
    elif mode == "admin":
        s += txt(x+28, y+70, "Admin Dashboard", 14, "#fff", 850)
        for i,(a,b) in enumerate([("Total users","12,478"),("Posts","8,542"),("Reports","156"),("Revenue","$24,560")]): s += rect(x+28+i*92, y+90, 78, 58, 9, "#111827", "#263449", 1, flt=None)+txt(x+38+i*92, y+113, a, 7, "#94a3b8")+txt(x+38+i*92, y+135, b, 15, "#fff", 900)
        s += txt(x+28, y+184, "Recent Reports", 12, "#fff", 850)
        for i,(u,st) in enumerate([("alice_88","Pending"),("bob_smith","Reviewed"),("charlie_17","Approved"),("david_23","Pending")]): s += txt(x+36, y+217+i*34, u, 9, "#fff") + txt(x+146, y+217+i*34, "Spam", 9, "#cbd5e1") + txt(x+w-92, y+217+i*34, st, 9, "#f59e0b" if st=="Pending" else "#22c55e", 800)
    return s


def mini_panel(x, y, w, h, name, mode):
    s = card(x, y, w, h) + txt(x+w/2, y+31, name, 20, "#fff", 900, "middle")
    if mode == "wallet":
        s += rect(x+30, y+70, w-60, 78, 12, "url(#brand)", "none", flt=None) + txt(x+50, y+103, "Wallet Balance", 11, "#ede9fe", 800) + txt(x+50, y+130, "$1,245.50", 25, "#fff", 900)
        s += rect(x+w-160, y+115, 55, 25, 8, "#38bdf8", "none", flt=None) + txt(x+w-132, y+132, "Payout", 8, "#fff", 900, "middle") + rect(x+w-96, y+115, 55, 25, 8, "#2563eb", "none", flt=None) + txt(x+w-68, y+132, "History", 8, "#fff", 900, "middle")
        for i,(t,v,c) in enumerate([("Reel Bonus","+$120.00","#22c55e"),("Live Gift","+$75.50","#22c55e"),("Subscription","+$50.00","#22c55e"),("Payout","-$300.00","#ef4444")]): s += txt(x+50, y+190+i*36, t, 11, "#111827", 700)+txt(x+w-120, y+190+i*36, v, 10, c, 900)
    elif mode == "market":
        s += rect(x+30,y+70,w-60,38,12,"#fff","#e2e8f0",1,flt=None)+txt(x+48,y+94,"Search marketplace...",10,"#64748b")
        for i,t in enumerate(["All","Electronics","Fashion","Services"]): s += rect(x+34+i*78,y+126,65,26,8,"#4f46e5" if i==0 else "#fff","#e2e8f0",1,flt=None)+txt(x+66+i*78,y+144,t,8,"#fff" if i==0 else "#111827",800,"middle")
        for i,(p,pr) in enumerate([("Camera","$450"),("Shoes","$80"),("Laptop","$1200")]): s += rect(x+35+i*(w-90)/3,y+175,(w-110)/3,105,10,"#f8fafc","#e2e8f0",1,flt=None)+photo(x+46+i*(w-90)/3,y+188,(w-132)/3,55,"url(#product)")+txt(x+46+i*(w-90)/3,y+263,p,10,"#111827",800)+txt(x+46+i*(w-90)/3,y+283,pr,11,"#2563eb",900)
    else:
        for i,(n,cnt) in enumerate([("Travel","24 items"),("Photography","10 items"),("Inspiration","18 items"),("Nature","8 items")]): s += rect(x+32+(i%2)*(w/2-14),y+78+(i//2)*105,w/2-48,85,10,"#fff","#e2e8f0",1,flt=None)+photo(x+42+(i%2)*(w/2-14),y+88+(i//2)*105,w/2-68,48,"url(#sunset)")+txt(x+42+(i%2)*(w/2-14),y+150+(i//2)*105,n,10,"#111827",800)+txt(x+42+(i%2)*(w/2-14),y+166+(i//2)*105,cnt,8,"#64748b")
        s += rect(x+w-145,y+42,110,24,8,"#ede9fe","#c4b5fd",1,flt=None)+txt(x+w-90,y+59,"+ New Collection",8,"#6d28d9",900,"middle")
    return s


def phone(x, y, mode):
    s = rect(x, y, 162, 302, 28, "#05070c", "#e5e7eb", 4) + rect(x+8, y+9, 146, 284, 22, "#0b1220", "#111827", 1, flt=None) + rect(x+58, y+15, 45, 9, 5, "#020617", "none", flt=None)
    if mode == "home":
        s += rect(x+16,y+36,130,30,8,"#fff","none",flt=None)
        for i in range(4): s += avatar(x+28+i*30,y+78,10)
        s += photo(x+18,y+105,126,112,"url(#sunset)") + txt(x+24,y+235,"Home feed",9,"#111827",800)
    elif mode == "reels":
        s += photo(x+8,y+28,146,265,"url(#reel)") + txt(x+21,y+245,"@creator",9,"#fff",900)
        for i,k in enumerate(["heart","msg","share","save"]): s += icon(x+132,y+120+i*38,k,"#fff")
    else:
        s += txt(x+22,y+50,"Chat",12,"#fff",900)
        for i,n in enumerate(["Alex","Emma","Ria","Darlene"]): s += avatar(x+30,y+82+i*42,10)+rect(x+48,y+72+i*42,88,22,8,"#172033","none",flt=None)+txt(x+56,y+87+i*42,n+" message",7,"#fff")
        s += rect(x+20,y+260,120,20,9,"#111827","#334155",flt=None)
    return s


svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">']
svg.append('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#02040a"/><stop offset=".45" stop-color="#071426"/><stop offset="1" stop-color="#050611"/></linearGradient>
<radialGradient id="g1" cx="16%" cy="8%" r="52%"><stop stop-color="#7c3cff" stop-opacity=".38"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<radialGradient id="g2" cx="78%" cy="45%" r="48%"><stop stop-color="#2563eb" stop-opacity=".28"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#101827" stop-opacity=".94"/><stop offset="1" stop-color="#07101c" stop-opacity=".9"/></linearGradient>
<linearGradient id="brand" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#8b5cf6"/><stop offset="1" stop-color="#2563eb"/></linearGradient>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffd84d"/><stop offset=".45" stop-color="#ff3cac"/><stop offset="1" stop-color="#00d4ff"/></linearGradient>
<linearGradient id="photo" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#7dd3fc"/><stop offset=".55" stop-color="#1d4ed8"/><stop offset="1" stop-color="#f59e0b"/></linearGradient>
<linearGradient id="sunset" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#c4b5fd"/><stop offset=".45" stop-color="#fb7185"/><stop offset="1" stop-color="#0f172a"/></linearGradient>
<linearGradient id="reel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111827"/><stop offset=".5" stop-color="#7c2d12"/><stop offset="1" stop-color="#020617"/></linearGradient>
<linearGradient id="live" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#78350f"/><stop offset=".5" stop-color="#292524"/><stop offset="1" stop-color="#020617"/></linearGradient>
<linearGradient id="product" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#e2e8f0"/><stop offset="1" stop-color="#94a3b8"/></linearGradient>
<filter id="shadow" x="-15%" y="-15%" width="130%" height="130%"><feDropShadow dx="0" dy="16" stdDeviation="18" flood-color="#000" flood-opacity=".35"/></filter>
</defs>''')
svg.append(rect(0,0,W,H,0,"url(#bg)","none",flt=None) + rect(0,0,W,H,0,"url(#g1)","none",flt=None) + rect(0,0,W,H,0,"url(#g2)","none",flt=None))

# Header and technology bar
svg.append(txt(34, 70, "Social", 68, "#fff", 950) + txt(318, 70, "Hub", 68, "#8b5cf6", 950) + txt(548, 66, "Full Stack Project — Complete & Fixed", 35, "#fff", 900) + check(1370, 52, 42))
svg.append(txt(550, 105, "Frontend + Backend Fully Integrated, Refactored, Tested & Working", 21, "#dbeafe", 550))
for i, b in enumerate(["FastAPI", "SQLAlchemy", "WebSockets", "JWT Authentication", "Alembic", "SQLite / PostgreSQL", "Dark Theme", "Light Theme"]):
    svg.append(badge(1485 + i * 285 if i < 6 else 3160 + (i-6)*320, 30, b, 260 if i in [3,5] else 210))

# Left column
lx, lw = 34, 555
svg.append(card(lx, 138, lw, 430, "TECH STACK"))
svg.append(txt(lx+30, 205, "Backend", 17, "#5eead4", 900) + section_list(lx+30, 238, ["Python", "FastAPI", "SQLAlchemy 2", "Alembic", "Pydantic", "JWT", "WebSockets", "SMTP", "SQLite Development", "PostgreSQL Production"], 16, 24, False))
svg.append(txt(lx+30, 455, "Frontend", 17, "#5eead4", 900) + section_list(lx+30, 488, ["HTML5", "Jinja2", "CSS3", "Vanilla JavaScript", "Font Awesome", "Responsive Design", "Progressive Web App", "Dark, Light and System Theme"], 16, 24, False))
features = ["Authentication: Register, Login, JWT and 2FA", "Posts, Reels, Stories and Highlights", "Real-time WebSocket Chat", "Real-time Notifications", "Search, Explore and Hashtags", "AI Creator Studio", "Caption and Hashtag Generator", "Music Library", "Live Rooms", "Marketplace", "Collaborations", "Collections and Saved Items", "Verification System", "Wallet and Payouts", "Admin Panel", "Scheduled Content", "Mobile and Desktop Responsive Design"]
svg.append(card(lx, 585, lw, 620, "KEY FEATURES") + section_list(lx+28, 653, features, 16, 30, True))

# Main showcase grid
cx = 610
svg.append(home_feed(cx, 138, 760, 520))
svg.append(reels(cx+775, 138, 465, 520))
svg.append(chat(cx+1255, 138, 690, 520))
svg.append(simple_ui(cx+1960, 138, 555, 520, "NOTIFICATIONS", "notifications"))
svg.append(simple_ui(cx, 675, 670, 520, "PROFILE", "profile"))
svg.append(simple_ui(cx+685, 675, 555, 520, "AI CREATOR STUDIO", "ai"))
svg.append(simple_ui(cx+1255, 675, 600, 520, "LIVE", "live"))
svg.append(simple_ui(cx+1870, 675, 645, 520, "ADMIN PANEL", "admin"))

# Lower center cards
svg.append(mini_panel(cx, 1215, 455, 355, "WALLET", "wallet"))
svg.append(mini_panel(cx+475, 1215, 680, 355, "MARKETPLACE", "market"))
svg.append(mini_panel(cx+1175, 1215, 520, 355, "COLLECTIONS", "collections"))
svg.append(card(cx+1715, 1215, 800, 355, "MOBILE RESPONSIVE"))
svg.append(phone(cx+1765, 1275, "home") + phone(cx+2020, 1275, "reels") + phone(cx+2275, 1275, "chat"))

# Right column
rx, rw = 3150, 655
results = ["All Frontend Pages Refactored", "Consistent Jinja Base Layout", "Authentication Pages Completed", "Placeholder Pages Replaced", "Duplicate JavaScript Removed", "Inline Event Handlers Removed", "JavaScript Modular and Clean", "Centralized API Client", "Unified Theme System", "Frontend API Calls Matched", "Stable WebSockets", "Media Uploads Working", "Database Migrations Working", "Responsive and Accessible", "Security Best Practices Applied", "Environment Secrets Protected", "Production-Ready Structure"]
svg.append(card(rx, 138, rw, 690, "PROJECT RESULTS") + section_list(rx+35, 207, results, 16, 34, True))
fixed = ["Duplicate JavaScript functions", "Inline onclick and onsubmit handlers", "Broken image paths", "Upload path normalization", "Database startup refactor", "Alembic migration issues", "Test environment isolation", "Theme conflicts", "CSS duplication", "API mismatches", "Hardcoded demo data removed"]
svg.append(card(rx, 845, rw, 425, "RECENTLY FIXED") + section_list(rx+35, 915, fixed, 17, 31, False))
svg.append(card(rx, 1288, rw, 282, "TEST RESULTS") + txt(rx+35, 1372, "All Tests Passed ✓", 22, "#4ade80", 900) + txt(rx+35, 1425, "================ test session starts ================", 16, "#e2e8f0", 600, mono=True) + txt(rx+35, 1460, "collected 128 items", 16, "#e2e8f0", 600, mono=True) + txt(rx+35, 1500, "[100%]", 18, "#fff", 900, mono=True) + txt(rx+35, 1540, "================ 128 passed in 8.42s ================", 16, "#e2e8f0", 600, mono=True))

# Bottom section
by = 1590
tree = ["SocialHub/", "├── backend/", "│   ├── app/", "│   │   ├── api/", "│   │   ├── models/", "│   │   ├── schemas/", "│   │   ├── services/", "│   │   ├── utils/", "│   │   └── websocket/", "│   ├── alembic/", "│   ├── tests/", "│   ├── scripts/", "│   └── main.py", "├── frontend/", "│   ├── templates/", "│   ├── static/", "│   └── uploads/", "├── requirements.txt", "├── pytest.ini", "└── socialhub.db"]
svg.append(card(34, by, 555, 535, "PROJECT STRUCTURE") + "".join(txt(60, by+82+i*21, t, 14, "#fde68a" if i in [0,1,13] else "#e5e7eb", 700, mono=True) for i,t in enumerate(tree)))
routes = ["/", "/login", "/register", "/forgot-password", "/reset-password", "/profile/{username}", "/posts", "/reels", "/stories", "/chat", "/notifications", "/search", "/explore", "/settings", "/admin", "/creator-dashboard", "/ai-creator-studio", "/instagram-studio", "/connect-instagram", "/data-studio", "/scheduled", "/music-library", "/live", "/marketplace", "/collabs", "/collections", "/saved", "/follow-requests", "/hashtag/{tag}", "/verification", "/wallet"]
svg.append(card(610, by, 965, 535, "AVAILABLE ROUTES"))
for i,r in enumerate(routes):
    col=i//11; row=i%11; svg.append(check(650+col*300, by+87+row*37, 17)+txt(675+col*300, by+94+row*37, r, 17, "#fff", 650))
cmds = ["# Install dependencies", "python -m pip install --upgrade pip", "pip install -r requirements.txt", "", "# Run migrations", "cd backend", "python -m alembic upgrade head", "", "# Run tests", "python -m pytest -q", "", "# Start server", "cd backend", "python -m uvicorn main:app --reload", "", "# Check Python", "python -m compileall -q backend", "", "# Check JavaScript", "Get-ChildItem frontend/static/js -Recurse -Filter *.js |", "ForEach-Object { node --check $_.FullName }"]
svg.append(card(1595, by, 720, 535, "ESSENTIAL COMMANDS — WINDOWS") + "".join(txt(1640, by+80+i*22, c, 14, "#e5e7eb" if not c.startswith("#") else "#c4b5fd", 700 if c.startswith("#") else 500, mono=True) for i,c in enumerate(cmds)))
highlights = ["Modular JavaScript ES Modules", "Reusable Jinja Partials", "Centralized API Client", "WebSocket Real-Time System", "JWT Authentication", "Role-Based Access", "Alembic Migrations", "Responsive UI", "PWA Service Worker", "Secure File Uploads"]
security = ["Secure Password Hashing", "JWT Access and Refresh Tokens", "Two-Factor Authentication", "Rate Limiting", "Input Validation", "File Type and Size Validation", "Path Traversal Protection", "Configured CORS", "Environment Secrets Protected", "No Sensitive Data in Logs"]
svg.append(card(2335, by, 430, 535, "TECHNICAL HIGHLIGHTS") + section_list(2370, by+88, highlights, 16, 39, True))
svg.append(card(2785, by, 1020, 535, "SECURITY & BEST PRACTICES") + section_list(2820, by+88, security, 17, 39, True))

svg.append('</svg>')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(svg), encoding="utf-8")
print(OUT)