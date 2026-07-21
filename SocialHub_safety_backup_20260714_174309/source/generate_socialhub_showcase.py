from pathlib import Path
from html import escape

W, H = 3840, 2160


def tag(name, attrs=None, content=""):
    attrs = attrs or {}
    attr = " ".join(f'{k}="{escape(str(v), quote=True)}"' for k, v in attrs.items() if v is not None)
    return f"<{name} {attr}>{content}</{name}>" if content else f"<{name} {attr}/>"


def text(x, y, s, size=28, fill="#fff", weight=500, anchor="start", opacity=1):
    return tag("text", {"x": x, "y": y, "font-size": size, "fill": fill, "font-weight": weight,
                        "text-anchor": anchor, "opacity": opacity, "font-family": "Inter, Segoe UI, Arial, sans-serif"}, escape(s))


def rect(x, y, w, h, r=22, fill="#101827", stroke="#263145", sw=1, opacity=1, flt=None):
    return tag("rect", {"x": x, "y": y, "width": w, "height": h, "rx": r, "fill": fill, "stroke": stroke,
                        "stroke-width": sw, "opacity": opacity, "filter": flt})


def circle(cx, cy, r, fill="#fff", stroke=None, sw=1, opacity=1):
    return tag("circle", {"cx": cx, "cy": cy, "r": r, "fill": fill, "stroke": stroke, "stroke-width": sw, "opacity": opacity})


def line(x1, y1, x2, y2, stroke="#fff", sw=2, opacity=1):
    return tag("line", {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "stroke": stroke, "stroke-width": sw,
                        "opacity": opacity, "stroke-linecap": "round"})


def path(d, fill="none", stroke="#fff", sw=2, opacity=1):
    return tag("path", {"d": d, "fill": fill, "stroke": stroke, "stroke-width": sw, "opacity": opacity,
                        "stroke-linecap": "round", "stroke-linejoin": "round"})


def avatar(x, y, r=34, name="", grad="url(#avatarGrad1)"):
    hair = circle(x, y - 3, r * .62, "#2b1b13")
    face = circle(x, y, r * .48, "#d99a66")
    body = path(f"M{x-r*.7},{y+r*.8} C{x-r*.25},{y+r*.2} {x+r*.25},{y+r*.2} {x+r*.7},{y+r*.8}", fill="#6757ff", stroke="none")
    return tag("g", {}, circle(x, y, r + 5, "none", grad, 5) + hair + face + body + text(x, y + r + 28, name, 17, "#dce7ff", 500, "middle", .9))


def icon(x, y, kind, c="#eaf1ff"):
    if kind == "home": return path(f"M{x-11},{y+3} L{x},{y-8} L{x+11},{y+3} M{x-7},{y+2} V{y+12} H{x+7} V{y+2}", stroke=c, sw=2.4)
    if kind == "search": return circle(x-3, y-3, 8, "none", c, 2.3) + line(x+4, y+4, x+13, y+13, c, 2.3)
    if kind == "bell": return path(f"M{x-9},{y+5} C{x-7},{y-4} {x-5},{y-10} {x},{y-10} C{x+5},{y-10} {x+7},{y-4} {x+9},{y+5} L{x+12},{y+10} H{x-12} Z M{x-4},{y+14} C{x-2},{y+17} {x+2},{y+17} {x+4},{y+14}", stroke=c, sw=2)
    if kind == "msg": return path(f"M{x-12},{y-9} H{x+12} V{y+7} H{x-2} L{x-10},{y+13} V{y+7} H{x-12} Z", stroke=c, sw=2)
    if kind == "plus": return line(x-9, y, x+9, y, c, 2.5) + line(x, y-9, x, y+9, c, 2.5)
    if kind == "heart": return path(f"M{x},{y+11} C{x-18},{y} {x-9},{y-13} {x},{y-5} C{x+9},{y-13} {x+18},{y} {x},{y+11}Z", fill=c, stroke="none")
    if kind == "play": return path(f"M{x-7},{y-10} L{x+11},{y} L{x-7},{y+10} Z", fill=c, stroke="none")
    if kind == "save": return path(f"M{x-8},{y-12} H{x+8} V{y+13} L{x},{y+6} L{x-8},{y+13} Z", stroke=c, sw=2)
    return circle(x, y, 10, "none", c, 2) + line(x-6, y, x+6, y, c, 2)


def card_title(x, y, title):
    return text(x, y, title, 24, "#ffffff", 800) + text(x, y + 32, "Premium glassmorphism UI", 14, "#8ea1bd")


def mini_photo(x, y, w, h, grad="url(#photoGrad)"):
    return rect(x, y, w, h, 14, grad, "#2c3a54", 1) + circle(x+w*.72, y+h*.28, min(w,h)*.16, "#fff8", None) + path(f"M{x},{y+h*.78} C{x+w*.22},{y+h*.47} {x+w*.42},{y+h*.7} {x+w*.62},{y+h*.44} C{x+w*.75},{y+h*.28} {x+w*.89},{y+h*.5} {x+w},{y+h*.36} V{y+h} H{x} Z", fill="#062133aa", stroke="none")


svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
svg.append('''<defs>
<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#04070d"/><stop offset=".45" stop-color="#071426"/><stop offset="1" stop-color="#111827"/></linearGradient>
<radialGradient id="glow1" cx="18%" cy="8%" r="50%"><stop stop-color="#7c3cff" stop-opacity=".45"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<radialGradient id="glow2" cx="85%" cy="58%" r="45%"><stop stop-color="#0ea5ff" stop-opacity=".35"/><stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient>
<linearGradient id="brand" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ff4fd8"/><stop offset=".5" stop-color="#7c5cff"/><stop offset="1" stop-color="#00c2ff"/></linearGradient>
<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffd84d"/><stop offset=".38" stop-color="#ff3cac"/><stop offset=".72" stop-color="#784bff"/><stop offset="1" stop-color="#00d4ff"/></linearGradient>
<linearGradient id="panel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#111a28" stop-opacity=".94"/><stop offset="1" stop-color="#07101c" stop-opacity=".88"/></linearGradient>
<linearGradient id="photoGrad" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#74d4ff"/><stop offset=".48" stop-color="#1e6ba8"/><stop offset="1" stop-color="#f1b46b"/></linearGradient>
<linearGradient id="photoGrad2" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffb86b"/><stop offset=".55" stop-color="#764bff"/><stop offset="1" stop-color="#06101e"/></linearGradient>
<linearGradient id="avatarGrad1" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#ffd84d"/><stop offset=".5" stop-color="#ff3cac"/><stop offset="1" stop-color="#00d4ff"/></linearGradient>
<filter id="shadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="25" stdDeviation="28" flood-color="#000" flood-opacity=".45"/></filter>
<filter id="softGlow"><feGaussianBlur stdDeviation="8" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>''')
svg.append(rect(0, 0, W, H, 0, "url(#bg)", "none") + rect(0, 0, W, H, 0, "url(#glow1)", "none") + rect(0, 0, W, H, 0, "url(#glow2)", "none"))

# Header
svg.append(rect(710, 33, 108, 108, 26, "url(#brand)", "none", flt="url(#softGlow)"))
svg.append(text(764, 105, "S", 68, "#fff", 900, "middle") + path("M734,80 C764,42 792,130 822,78", stroke="#fff", sw=5, opacity=.75))
svg.append(text(865, 109, "SocialHub – Modern Social Media Platform", 75, "#f7fbff", 900))
features = [(630,"✧","Modern UI/UX"),(920,"◐","Dark & Light Mode"),(1270,"▣","Fully Responsive"),(1628,"☷","Real-time Chat"),(1940,"▣","Stories & Reels"),(2250,"♬","Creator Tools")]
for x, ic, label in features:
    svg.append(text(x, 185, ic, 30, "#7ca7ff", 700) + text(x+42, 183, label, 22, "#f5f7ff", 500))

# Desktop dashboard
dx, dy, dw, dh = 80, 235, 2260, 1225
svg.append(rect(dx, dy, dw, dh, 28, "url(#panel)", "#2f3c55", 1.2, flt="url(#shadow)"))
svg.append(rect(dx, dy, 405, dh, 28, "#08111fdd", "#263145"))
svg.append(rect(dx+402, dy, 1, dh, 0, "#263145", "none"))
svg.append(rect(dx+560, dy+25, 820, 60, 18, "#0e1826", "#273449"))
svg.append(icon(dx+595, dy+55, "search", "#97a6bd") + text(dx+635, dy+64, "Search users, posts, #hashtags...", 18, "#93a2b7"))
for i, kind in enumerate(["sun", "msg", "bell"]):
    x = dx + 1865 + i*62
    svg.append(icon(x, dy+55, kind, "#e8f0ff") + (circle(x+15, dy+37, 13, "#6d5cff") + text(x+15, dy+43, "6", 13, "#fff", 800, "middle") if i==1 else ""))
svg.append(avatar(dx+2150, dy+55, 25, ""))
svg.append(circle(dx+58, dy+58, 28, "url(#brand)") + text(dx+58, dy+69, "S", 31, "#fff", 900, "middle") + text(dx+105, dy+67, "Social", 29, "#fff", 800) + text(dx+188, dy+67, "Hub", 29, "#9d7cff", 800))
menu = ["Home","Search","Explore","Reels","Messages","Notifications","Create","Profile","Saved","Collections","Marketplace","Creator Studio","Settings","Wallet"]
for i, m in enumerate(menu):
    y = dy+165+i*60 if i < 8 else dy+270+i*60
    if i == 0: svg.append(rect(dx+24, y-34, 350, 48, 12, "#202b3d", "none"))
    svg.append(icon(dx+67, y-10, ["home","search","compass","play","msg","bell","plus","user","save","grid","bag","chart","settings","wallet"][i] if i<14 else "home", "#e9f2ff") + text(dx+110, y, m, 20, "#edf4ff", 550))
    if m in ["Messages","Notifications"]: svg.append(circle(dx+332, y-10, 18, "#6c5cff") + text(dx+332, y-4, "3" if m=="Messages" else "6", 15, "#fff", 800, "middle"))
svg.append(line(dx+38, dy+680, dx+360, dy+680, "#28374d", 1))
svg.append(avatar(dx+70, dy+1168, 29, "") + text(dx+120, dy+1162, "John Doe", 20, "#fff", 800) + text(dx+120, dy+1188, "@johndoe", 16, "#95a4ba"))

# Stories and feed
sx = dx+435
for i, name in enumerate(["Your story","jennifer34","mark_smith","sophia_97","mike_does","anna_21","tommy_8"]):
    svg.append(avatar(sx+80+i*180, dy+215, 50, name))
    if i == 0: svg.append(circle(sx+122, dy+256, 17, "#6757ff") + text(sx+122, dy+262, "+", 19, "#fff", 800, "middle"))
svg.append(rect(sx, dy+340, 1220, 180, 22, "#111b2a", "#263449"))
svg.append(avatar(sx+62, dy+402, 32, "") + rect(sx+120, dy+373, 1060, 64, 22, "#172333", "#2a374b") + text(sx+150, dy+412, "What’s on your mind, John?", 20, "#9aa8bb"))
for i, item in enumerate([("▣","Photo"),("■","Video"),("▣","Reel"),("●","Feeling")]):
    svg.append(text(sx+60+i*260, dy+488, item[0], 25, ["#27d980","#4aa3ff","#c15cff","#ffd15c"][i], 800) + text(sx+95+i*260, dy+486, item[1], 19, "#dbe6f6"))
px, py = sx, dy+548
svg.append(rect(px, py, 1220, 610, 24, "#101a29", "#2b3950"))
svg.append(avatar(px+64, py+60, 33, "") + text(px+112, py+55, "jennifer34", 20, "#fff", 800) + text(px+112, py+82, "New York, USA", 16, "#91a3b7") + text(px+1110, py+58, "2h  ⋯", 18, "#aeb9cb"))
svg.append(mini_photo(px+28, py+120, 1165, 420))
svg.append(icon(px+60, py+570, "heart", "#ff416d") + text(px+95, py+578, "234", 20, "#dce6f4") + icon(px+200, py+568, "msg") + text(px+235, py+578, "12", 20, "#dce6f4") + icon(px+330, py+568, "send") + text(px+365, py+578, "8", 20, "#dce6f4") + icon(px+1120, py+568, "save"))

# Right sidebar desktop
rx = dx+1700
svg.append(rect(rx, dy+145, 510, 585, 22, "#111b2a", "#263449") + text(rx+28, dy+192, "Suggestions for you", 22, "#fff", 800) + text(rx+420, dy+192, "See all", 16, "#ad92ff", 700))
for i, n in enumerate(["olivia_james","daniel_doe","michael_33","katherine_21","alexa_martin"]):
    y=dy+265+i*92
    svg.append(avatar(rx+55, y, 30, "") + text(rx+100, y-4, n, 18, "#fff", 700) + text(rx+100, y+20, "Follow you", 15, "#8d9db2") + rect(rx+370, y-20, 105, 38, 10, "url(#brand)", "none") + text(rx+422, y+5, "Follow", 15, "#fff", 800, "middle"))
svg.append(rect(rx, dy+760, 510, 390, 22, "#111b2a", "#263449") + text(rx+28, dy+808, "Trending", 22, "#fff", 800) + text(rx+420, dy+808, "See all", 16, "#ad92ff", 700))
for i, htag in enumerate(["#SunsetPhotography","#TravelDiaries","#GoodVibesOnly","#FitnessMotivation"]):
    svg.append(text(rx+30, dy+860+i*62, htag, 19, "#eaf1ff", 650) + text(rx+30, dy+884+i*62, f"{12-i*2}.{i+1}K posts", 15, "#8496ad"))

# Phones
def phone(x, y, title="Reels", messages=False):
    svg.append(rect(x, y, 575, 1280, 72, "#05080d", "#3b3f46", 8, flt="url(#shadow)"))
    svg.append(rect(x+24, y+24, 527, 1232, 55, "#0a111e", "#202a3b", 1))
    svg.append(rect(x+200, y+35, 175, 42, 22, "#020307", "none"))
    svg.append(text(x+58, y+72, "9:41", 18, "#fff", 800) + text(x+472, y+72, "▰  Wi‑Fi  ▬", 16, "#fff", 700))
    if not messages:
        svg.append(mini_photo(x+25, y+92, 525, 1040, "url(#photoGrad2)") + text(x+55, y+150, "Reels", 22, "#fff", 800) + text(x+520, y+150, "▢", 28, "#fff", 700, "middle"))
        svg.append(avatar(x+78, y+970, 28, "") + text(x+120, y+968, "sophia_97", 19, "#fff", 800) + rect(x+218, y+942, 70, 34, 12, "#0008", "#fff7") + text(x+253, y+965, "Follow", 14, "#fff", 800, "middle"))
        svg.append(text(x+55, y+1028, "Enjoying the sunset ✨", 18, "#fff") + text(x+55, y+1075, "♫ Original Audio  ·  Trending", 16, "#fff"))
        for i,(k,l) in enumerate([("heart","12.5K"),("msg","128"),("send","342"),("save","")]):
            yy=y+730+i*115; svg.append(icon(x+500, yy, k, "#fff") + text(x+500, yy+45, l, 16, "#fff", 700, "middle"))
    else:
        svg.append(text(x+285, y+150, "Messages", 22, "#fff", 800, "middle") + rect(x+60, y+195, 455, 52, 18, "#111b2a", "#263449") + icon(x+85, y+220, "search", "#8796aa") + text(x+120, y+228, "Search messages...", 15, "#8796aa"))
        for i,n in enumerate(["Your note","jennifer34","mark_smith","olivia_james"]): svg.append(avatar(x+95+i*125, y+315, 40, n))
        for i,(n,msg,b) in enumerate([("jennifer34","Hey! How are you? 😊 · 2m","2"),("mark_smith","Sent a photo · 10m","1"),("olivia_james","Typing... · Now","3"),("mike_does","Let’s catch up tomorrow! · 30m","") ,("anna_21","Thanks! 🙏 · 1h","") ,("tommy_8","Sounds good! · 2h","")]):
            yy=y+450+i*125
            svg.append(avatar(x+90, yy, 36, "") + text(x+150, yy-8, n, 19, "#fff", 800) + text(x+150, yy+20, msg, 16, "#9baabe") + circle(x+115, yy+28, 8, "#18d17f"))
            if b: svg.append(circle(x+505, yy, 22, "#6c5cff") + text(x+505, yy+7, b, 16, "#fff", 800, "middle"))
    svg.append(rect(x+25, y+1130, 525, 100, 0, "#05080dc8", "none") + icon(x+80, y+1180, "home") + icon(x+200, y+1180, "search") + icon(x+310, y+1180, "plus") + icon(x+420, y+1180, "play") + circle(x+515, y+1180, 16, "#fff"))

phone(2525, 170, "Reels", False)
phone(3175, 170, "Messages", True)

# Bottom panels
panel_y = 1500
panels = [(75,630,"Create Post"),(765,630,"Stories Viewer"),(1455,720,"Profile Page"),(2240,780,"Creator Dashboard"),(3070,700,"Live Stream")]
for x,w,t in panels:
    svg.append(rect(x, panel_y, w, 830, 28, "url(#panel)", "#2d3a51", 1.2, flt="url(#shadow)") + text(x+w/2, panel_y+52, t, 26, "#fff", 850, "middle"))

# Create post panel
x=75; y=panel_y
svg.append(rect(x+45,y+95,540,690,22,"#101827","#304158") + text(x+295,y+150,"Create New Post",21,"#fff",750,"middle") + text(x+65,y+150,"‹",34,"#fff") + text(x+555,y+150,"×",28,"#fff"))
svg.append(mini_photo(x+72,y+190,220,310)+mini_photo(x+300,y+190,250,145,"url(#photoGrad2)")+mini_photo(x+300,y+345,118,155)+mini_photo(x+432,y+345,118,155,"url(#photoGrad2)"))
svg.append(text(x+72,y+560,"Write a caption...",17,"#9aa8bb")+line(x+72,y+595,x+550,y+595,"#28374d",1)+rect(x+72,y+640,165,44,12,"#172333","#2c3b52") + text(x+92,y+668,"#  Add Hashtag",16,"#aebcff") + rect(x+250,y+640,155,44,12,"#172333","#2c3b52") + text(x+270,y+668,"⌖  Add Location",16,"#d4ddec") + text(x+75,y+730,"◎  Everyone⌄",16,"#d4ddec") + rect(x+420,y+695,150,55,12,"url(#brand)","none") + text(x+495,y+730,"Share",17,"#fff",800,"middle"))

# Stories viewer
x=765; y=panel_y
svg.append(rect(x+45,y+95,540,690,22,"#0b1220","#304158") + mini_photo(x+80,y+130,470,585) + rect(x+92,y+126,105,7,4,"#fff")+rect(x+205,y+126,105,7,4,"#ffffff80")+rect(x+318,y+126,105,7,4,"#ffffff80")+rect(x+431,y+126,105,7,4,"#ffffff80") + avatar(x+105,y+165,24,"") + text(x+145,y+170,"jennifer34  2h",16,"#fff",800)+text(x+535,y+170,"×",32,"#fff",700,"middle") + rect(x+95,y+720,380,52,22,"#07101ccc","#ffffff55") + text(x+120,y+753,"Send message...",17,"#fff") + icon(x+520,y+746,"heart","#ff5577"))

# Profile
x=1455; y=panel_y
svg.append(avatar(x+105,y+150,58,"") + text(x+250,y+135,"128",26,"#fff",850,"middle")+text(x+250,y+164,"Posts",16,"#cbd5e1",500,"middle")+text(x+390,y+135,"15.2K",26,"#fff",850,"middle")+text(x+390,y+164,"Followers",16,"#cbd5e1",500,"middle")+text(x+545,y+135,"342",26,"#fff",850,"middle")+text(x+545,y+164,"Following",16,"#cbd5e1",500,"middle"))
svg.append(text(x+72,y+242,"Jennifer Martinez",23,"#fff",850)+text(x+72,y+272,"Digital Creator ⭐",17,"#d3def0")+text(x+72,y+300,"Travel | Lifestyle | Photography",17,"#d3def0")+text(x+72,y+330,"⌖ New York, USA",17,"#d3def0")+text(x+72,y+360,"🔗 linktr.ee/jennifer34",17,"#97b7ff")+rect(x+72,y+395,280,55,12,"url(#brand)","none") + text(x+212,y+431,"Follow",18,"#fff",850,"middle") + rect(x+370,y+395,220,55,12,"#202b3b","#2f3d55") + text(x+480,y+431,"Message",18,"#fff",750,"middle"))
for i in range(6): svg.append(mini_photo(x+72+(i%3)*205,y+540+(i//3)*150,190,135,"url(#photoGrad2)" if i%2 else "url(#photoGrad)"))

# Creator dashboard
x=2240; y=panel_y
svg.append(text(x+35,y+120,"Welcome back, John! 👋",24,"#fff",850)+text(x+35,y+152,"Here’s your overview",16,"#93a2b7"))
stats=[("Total Views","245.8K","+12.5%"),("Profile Visits","18.3K","+8.2%"),("Followers","12.5K","+15.3%"),("Engagement","6.7%","+3.1%")]
for i,(a,b,c) in enumerate(stats):
    xx=x+35+(i%2)*370; yy=y+210+(i//2)*165
    svg.append(rect(xx,yy,335,120,16,"#142033","#2a3850")+text(xx+25,yy+42,a,15,"#a6b5cb")+text(xx+25,yy+78,b,25,"#fff",850)+text(xx+25,yy+104,c,15,"#31d990")+circle(xx+278,yy+60,34,"#ffffff12") )
svg.append(text(x+35,y+565,"Analytics Overview",22,"#fff",850)+text(x+680,y+565,"Last 7 days ›",14,"#9aa8bb",500,"end"))
svg.append(path(f"M{x+55},{y+720} L{x+160},{y+640} L{x+280},{y+590} L{x+400},{y+640} L{x+520},{y+590} L{x+640},{y+635} L{x+725},{y+585}", stroke="#8b5cff", sw=5) + path(f"M{x+55},{y+720} L{x+160},{y+640} L{x+280},{y+590} L{x+400},{y+640} L{x+520},{y+590} L{x+640},{y+635} L{x+725},{y+585} V{y+760} H{x+55} Z", fill="#8b5cff33", stroke="none"))
for i in range(7): svg.append(circle(x+55+i*112,y+720-[0,80,130,80,130,85,135][i],7,"#b08cff"))

# Live stream
x=3070; y=panel_y
svg.append(mini_photo(x+45,y+75,610,580,"url(#photoGrad2)")+rect(x+70,y+105,75,42,9,"#ff2f5f","none") + text(x+108,y+132,"LIVE",16,"#fff",850,"middle") + rect(x+160,y+105,90,42,18,"#0009","none") + text(x+205,y+132,"● 1.2K",16,"#fff",800,"middle"))
for i,(n,m) in enumerate([("emily_21","Hello! 👋"),("mike_does","Awesome! 🔥"),("sophia_97","Nice stream! 💜")]): svg.append(avatar(x+78,y+515+i*62,23,"")+text(x+115,y+510+i*62,n,16,"#fff",800)+text(x+115,y+532+i*62,m,16,"#fff"))
for i in range(8): svg.append(text(x+580-(i%3)*25,y+470-i*45,"❤",28,["#ff5b7d","#ff9b5b","#b15cff"][i%3],800,opacity=.85))
svg.append(rect(x+70,y+700,300,58,24,"#111b2acc","#ffffff33") + text(x+95,y+736,"Add a comment...",17,"#d5deec") + icon(x+420,y+728,"msg") + icon(x+485,y+728,"send") + circle(x+565,y+728,35,"#ffffff12") + text(x+565,y+737,"⚡",26,"#fff",800,"middle"))

# Feature strip
strip_y=2020
svg.append(rect(460,strip_y,2920,140,12,"#07101ccc","#263449"))
for i,(ic,label) in enumerate([("☀️🌙","Dark & Light Mode"),("▯▯","Fully Responsive"),("⚡","Real-time Updates"),("🔒","Secure & Private"),("🚀","Fast & Optimized")]):
    x=560+i*590
    svg.append(text(x,strip_y+85,ic,38,"#8a7cff",800)+text(x+95,strip_y+82,label,24,"#ffffff",750))

svg.append('</svg>')

out_dir = Path("SocialHub/frontend/static/showcase")
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "socialhub-promotional-showcase-4k.svg"
out.write_text("\n".join(svg), encoding="utf-8")
print(out)
