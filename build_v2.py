import json, html, re, urllib.parse
from pathlib import Path

DATA=json.load(open('notion_pages.json'))

def get_blocks(data):
    return {k:v['value']['value'] for k,v in data.get('recordMap',{}).get('block',{}).items() if v.get('value',{}).get('value')}
ALL={}
for d in DATA.values(): ALL.update(get_blocks(d))

def rich(prop):
    out=[]
    for seg in prop or []:
        text=html.escape(seg[0])
        ann=seg[1] if len(seg)>1 else []
        href=None
        for a in ann:
            if a[0]=='a': href=a[1]
        if any(a[0]=='b' for a in ann): text=f'<strong>{text}</strong>'
        if any(a[0]=='i' for a in ann): text=f'<em>{text}</em>'
        if any(a[0]=='c' for a in ann): text=f'<code>{text}</code>'
        if href: text=f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{text}</a>'
        out.append(text)
    return ''.join(out).replace('\n','<br>')

def plain(prop): return ''.join(seg[0] for seg in prop or [])
def btitle(b): return rich(b.get('properties',{}).get('title'))
def bplain(b): return plain(b.get('properties',{}).get('title'))
def slug(s):
    s=re.sub(r'\s+','-',s.strip().lower())
    s=re.sub(r'[^\w\u4e00-\u9fff-]+','',s)
    return s[:70] or 'chapter'

def image_url(bid,b):
    fmt=b.get('format',{})
    u=fmt.get('display_source')
    if not u:
        prop=b.get('properties',{}).get('source')
        if prop: u=prop[0][0]
    if not u: return ''
    if 'secure.notion-static.com' in u or 'prod-files-secure' in u:
        return 'https://ertland.notion.site/image/'+urllib.parse.quote(u,safe='')+f'?table=block&id={bid}&cache=v2'
    return u

def render_children(pid):
    ids=ALL.get(pid,{}).get('content') or []
    parts=[]; i=0
    while i<len(ids):
        bid=ids[i]; b=ALL.get(bid)
        if not b: i+=1; continue
        t=b.get('type')
        if t in ('bulleted_list','numbered_list'):
            tag='ul' if t=='bulleted_list' else 'ol'; items=[]
            while i<len(ids) and ALL.get(ids[i],{}).get('type')==t:
                ib=ALL[ids[i]]
                items.append(f'<li>{btitle(ib)}{render_children(ids[i])}</li>')
                i+=1
            parts.append(f'<{tag}>{"".join(items)}</{tag}>'); continue
        parts.append(render_block(bid,b)); i+=1
    return ''.join(parts)

def render_block(bid,b):
    t=b.get('type'); txt=btitle(b); child=render_children(bid) if b.get('content') and t!='page' else ''
    if t=='text': return f'<p>{txt}</p>{child}' if txt else child
    if t=='header': return f'<h2>{txt}</h2>{child}'
    if t=='sub_header': return f'<h3>{txt}</h3>{child}'
    if t=='sub_sub_header': return f'<h4>{txt}</h4>{child}'
    if t=='divider': return '<hr>'
    if t=='to_do':
        checked=b.get('properties',{}).get('checked',[["No"]])[0][0]=='Yes'
        return f'<div class="check"><span>{"✓" if checked else ""}</span><p>{txt}</p></div>{child}'
    if t=='toggle': return f'<details class="inner-toggle"><summary>{txt}</summary>{child}</details>'
    if t=='code':
        raw=plain(b.get('properties',{}).get('title'))
        return f'<pre><code>{html.escape(raw)}</code></pre>'
    if t=='image':
        src=image_url(bid,b); cap=rich(b.get('properties',{}).get('caption'))
        return f'<figure><img loading="lazy" src="{html.escape(src)}" alt="{html.escape(cap or "Ertland image")}">{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'
    if t=='file':
        src=image_url(bid,b); label=txt or '下载文件'
        return f'<p><a class="file" href="{html.escape(src)}" target="_blank">{label}</a></p>'
    if t in ('column_list','column'):
        return f'<div class="columns">{child}</div>' if t=='column_list' else f'<div class="column">{child}</div>'
    return child if t=='page' else (f'<p>{txt}</p>{child}' if txt else child)

def collect_pages(pid,out):
    for cid in ALL.get(pid,{}).get('content') or []:
        if ALL.get(cid,{}).get('type')=='page': out.append(cid)
        else: collect_pages(cid,out)

root='c7fede65-1a85-4126-899c-d21599479714'
pages=[]; collect_pages(root,pages)
chapters=[]
for i,pid in enumerate(pages,1):
    b=ALL[pid]; title=bplain(b); sid=slug(title)
    body=render_children(pid)
    # summary: first 90 Chinese chars from text blocks
    raw=[]
    for cid in b.get('content') or []:
        cb=ALL.get(cid,{})
        if cb.get('type') in ('text','sub_header','sub_sub_header'):
            s=bplain(cb); 
            if s: raw.append(s)
        if len(''.join(raw))>100: break
    summary=(''.join(raw)[:96]+'…') if raw else '查看本章完整内容。'
    chapters.append(dict(i=i,pid=pid,title=title,sid=sid,summary=summary,body=body))

cards=''.join(f'''<a class="chapter-card" href="#{c['sid']}" data-title="{html.escape(c['title'])}">
  <span class="card-index">{c['i']:02d}</span><h3>{html.escape(c['title'])}</h3><p>{html.escape(c['summary'])}</p><span class="card-link">查看章节 →</span>
</a>''' for c in chapters)
nav=''.join(f'<a href="#{c["sid"]}">{c["i"]:02d}. {html.escape(c["title"])}</a>' for c in chapters)
chapter_html=''.join(f'''<section class="chapter" id="{c['sid']}">
  <div class="chapter-head"><span>{c['i']:02d}</span><div><h2>{html.escape(c['title'])}</h2><p>{html.escape(c['summary'])}</p></div></div>
  <details class="chapter-body"><summary>展开阅读完整内容</summary><div class="article">{c['body']}</div></details>
</section>''' for c in chapters)
community=render_children(root)

DOC=f'''<!doctype html><html lang="zh-CN"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>新西兰 WHV 打工度假攻略 | Ertland</title>
<meta name="description" content="Ertland 新西兰 WHV 打工度假攻略：资格、流程、抢名额、递签与社群。">
<meta property="og:title" content="新西兰 WHV 打工度假攻略 | Ertland"><meta property="og:url" content="https://ertland.ai.com/">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
:root{{--blue:#146ef5;--blue2:#57b8ff;--sky:#eaf7ff;--sky2:#f6fbff;--ink:#07111f;--muted:#64748b;--line:#d8ecff;--soft:#ffffff;--shadow:0 34px 90px rgba(20,110,245,.13),0 14px 38px rgba(15,23,42,.06)}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:Inter,-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:linear-gradient(180deg,#f3fbff 0,#fff 42%,#f5fbff 100%);}}body:before{{content:"";position:fixed;inset:0;pointer-events:none;background:radial-gradient(circle at 10% 4%,rgba(87,184,255,.28),transparent 32%),radial-gradient(circle at 88% 0,rgba(20,110,245,.16),transparent 30%)}}a{{color:inherit;text-decoration:none}}.wrap{{width:min(1180px,calc(100% - 44px));margin:auto;position:relative}}header{{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.78);backdrop-filter:blur(18px);border-bottom:1px solid rgba(216,236,255,.8)}}.nav{{height:72px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.brand{{display:flex;align-items:center;gap:12px;font-weight:900;letter-spacing:-.04em}}.mark{{width:38px;height:38px;border-radius:12px;background:var(--blue);color:white;display:grid;place-items:center;box-shadow:0 16px 35px rgba(20,110,245,.25)}}.navlinks{{display:flex;gap:22px;color:#516174;font-size:14px;font-weight:600}}.navlinks a:hover{{color:var(--blue)}}.cta{{display:inline-flex;height:46px;padding:0 18px;align-items:center;border-radius:8px;background:var(--blue);color:white;font-weight:800;box-shadow:0 18px 34px rgba(20,110,245,.22);transition:.2s}}.cta:hover{{transform:translateY(-2px);background:#075ee0}}.hero{{padding:86px 0 48px;display:grid;grid-template-columns:1.05fr .95fr;gap:54px;align-items:end}}.tag{{display:inline-flex;gap:8px;align-items:center;padding:8px 11px;border:1px solid var(--line);border-radius:999px;background:white;color:var(--blue);font-size:13px;font-weight:800;box-shadow:0 10px 30px rgba(20,110,245,.06)}}h1{{font-size:clamp(46px,7vw,86px);line-height:.95;letter-spacing:-.075em;margin:22px 0 22px;max-width:780px}}.lead{{font-size:clamp(18px,2vw,22px);line-height:1.7;color:#536477;max-width:680px;margin:0 0 30px}}.hero-actions{{display:flex;gap:12px;flex-wrap:wrap}}.ghost{{display:inline-flex;height:46px;padding:0 18px;align-items:center;border-radius:8px;background:white;border:1px solid var(--line);color:var(--blue);font-weight:800}}.panel{{background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:18px;box-shadow:var(--shadow);overflow:hidden}}.panel-top{{padding:18px 18px 0}}.browserbar{{height:40px;border-radius:10px;background:#f3f9ff;border:1px solid var(--line);display:flex;align-items:center;gap:8px;padding:0 12px;color:#4f6d86;font-size:12px;font-weight:700}}.dot{{width:9px;height:9px;border-radius:50%;background:#9bd7ff}}.preview{{padding:22px;display:grid;gap:14px}}.preview-main{{padding:22px;border-radius:14px;background:linear-gradient(135deg,#eaf7ff,#fff);border:1px solid var(--line)}}.preview-main b{{display:block;font-size:28px;letter-spacing:-.05em;margin-bottom:12px}}.line{{height:9px;border-radius:99px;background:#cfeeff;margin:8px 0}}.line:nth-child(3){{width:78%}}.line:nth-child(4){{width:58%}}.mini-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}}.mini{{height:78px;border-radius:12px;background:white;border:1px solid var(--line);padding:12px;color:var(--blue);font-weight:900}}.strip{{padding:28px 0 12px}}.strip-inner{{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:18px;overflow:hidden;box-shadow:0 18px 44px rgba(20,110,245,.08)}}.metric{{background:white;padding:22px}}.metric b{{display:block;font-size:30px;color:var(--blue);letter-spacing:-.04em}}.metric span{{color:var(--muted);font-size:13px;font-weight:700}}.section-title{{padding:70px 0 26px;display:flex;align-items:end;justify-content:space-between;gap:30px}}.section-title h2{{font-size:clamp(32px,4vw,54px);letter-spacing:-.06em;line-height:1;margin:0}}.section-title p{{margin:0;color:var(--muted);line-height:1.65;max-width:520px}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}}.chapter-card{{min-height:230px;background:white;border:1px solid var(--line);border-radius:18px;padding:22px;box-shadow:0 20px 55px rgba(15,23,42,.055);display:flex;flex-direction:column;transition:.2s}}.chapter-card:hover{{transform:translateY(-4px);box-shadow:var(--shadow);border-color:#aadfff;text-decoration:none}}.card-index{{font-size:12px;color:var(--blue);font-weight:900;letter-spacing:.08em}}.chapter-card h3{{font-size:23px;line-height:1.18;letter-spacing:-.04em;margin:16px 0 10px}}.chapter-card p{{color:var(--muted);line-height:1.65;margin:0;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}}.card-link{{margin-top:auto;padding-top:18px;color:var(--blue);font-weight:900}}.content-layout{{display:grid;grid-template-columns:260px 1fr;gap:28px;padding:50px 0 90px}}.toc{{position:sticky;top:96px;align-self:start;background:white;border:1px solid var(--line);border-radius:18px;padding:16px;box-shadow:0 18px 48px rgba(15,23,42,.055);max-height:calc(100vh - 120px);overflow:auto}}.toc strong{{display:block;color:var(--blue);margin:4px 10px 12px}}.toc a{{display:block;padding:10px;border-radius:10px;color:#526579;font-size:13px;line-height:1.35;font-weight:650}}.toc a:hover{{background:var(--sky);color:var(--blue)}}.chapter{{background:white;border:1px solid var(--line);border-radius:20px;margin-bottom:18px;box-shadow:0 16px 42px rgba(15,23,42,.045);overflow:hidden}}.chapter-head{{padding:26px;display:grid;grid-template-columns:54px 1fr;gap:18px;align-items:start;background:linear-gradient(180deg,#fff,#fbfdff)}}.chapter-head>span{{height:48px;border-radius:12px;background:var(--blue);color:white;display:grid;place-items:center;font-weight:900}}.chapter-head h2{{font-size:32px;letter-spacing:-.055em;line-height:1.1;margin:0 0 8px}}.chapter-head p{{color:var(--muted);line-height:1.6;margin:0}}.chapter-body{{border-top:1px solid var(--line)}}.chapter-body>summary{{list-style:none;cursor:pointer;padding:16px 26px;color:var(--blue);font-weight:900;background:#f7fcff}}.chapter-body>summary::-webkit-details-marker{{display:none}}.article{{padding:8px 30px 32px;max-width:820px}}.article h2{{font-size:34px;letter-spacing:-.055em;margin:34px 0 14px}}.article h3{{font-size:25px;letter-spacing:-.04em;color:#075985;margin:30px 0 12px}}.article h4{{font-size:19px;color:#0d4264;margin:24px 0 8px}}.article p,.article li{{font-size:16px;line-height:1.9;color:#334155}}.article ul,.article ol{{padding-left:1.3em}}.article hr{{border:0;border-top:1px solid var(--line);margin:28px 0}}.article figure{{margin:24px 0;border-radius:16px;overflow:hidden;border:1px solid var(--line);background:#f7fcff}}.article img{{display:block;max-width:100%;height:auto;margin:auto}}figcaption{{padding:10px 14px;color:var(--muted);font-size:13px}}.check{{display:flex;gap:12px;padding:12px 14px;border-radius:12px;background:#f3faff;border:1px solid var(--line);margin:10px 0}}.check span{{width:22px;height:22px;border-radius:6px;border:1px solid #9bd7ff;background:white;color:var(--blue);display:grid;place-items:center;font-weight:900;flex:0 0 auto}}.check p{{margin:0!important}}.inner-toggle{{border:1px solid var(--line);border-radius:14px;background:#f7fcff;padding:14px 16px;margin:12px 0}}.inner-toggle summary{{font-weight:850;color:#075985;cursor:pointer}}pre{{white-space:pre-wrap;background:#061d33;color:#e6f7ff;border-radius:14px;padding:18px;overflow:auto}}code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#e8f5ff;color:#075985;border-radius:5px;padding:2px 5px}}pre code{{background:transparent;color:inherit;padding:0}}.columns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}}.community{{margin-top:18px;background:linear-gradient(135deg,#eaf7ff,#fff);border:1px solid var(--line);border-radius:20px;box-shadow:var(--shadow)}}footer{{padding:34px 0 56px;color:var(--muted)}}.foot{{border-top:1px solid var(--line);padding-top:22px;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap}}@media(max-width:920px){{.hero,.content-layout{{grid-template-columns:1fr}}.cards{{grid-template-columns:1fr 1fr}}.toc{{position:static;max-height:none}}.navlinks{{display:none}}.strip-inner{{grid-template-columns:repeat(2,1fr)}}}}@media(max-width:620px){{.wrap{{width:min(100% - 28px,1180px)}}.cards,.mini-grid,.strip-inner{{grid-template-columns:1fr}}.hero{{padding-top:56px}}.chapter-head{{grid-template-columns:1fr}}.article{{padding:4px 20px 26px}}}}
</style></head><body>
<header><div class="wrap nav"><a class="brand" href="#top"><span class="mark">NZ</span><span>Ertland</span></a><nav class="navlinks"><a href="#chapters">章节</a><a href="#read">正文</a><a href="#community">社群</a></nav><a class="cta" href="#chapters">开始阅读</a></div></header>
<main id="top"><section class="wrap hero"><div><span class="tag">🇳🇿 新西兰 WHV 打工度假</span><h1>一页看懂新西兰 WHV 申请攻略</h1><p class="lead">从资格自查、申请流程、抢名额到递签材料，把 Ertland Notion 内容整理成更清爽、更适合阅读的网页。</p><div class="hero-actions"><a class="cta" href="#chapters">查看攻略目录</a><a class="ghost" href="#community">加入社群</a></div></div><div class="panel"><div class="panel-top"><div class="browserbar"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span>ertland.ai.com</span></div></div><div class="preview"><div class="preview-main"><b>NZ WHV Guide</b><div class="line"></div><div class="line"></div><div class="line"></div></div><div class="mini-grid"><div class="mini">资格</div><div class="mini">抢名额</div><div class="mini">递签</div></div></div></div></section>
<section class="wrap strip"><div class="strip-inner"><div class="metric"><b>{len(chapters)}</b><span>完整章节</span></div><div class="metric"><b>2026</b><span>递签攻略更新</span></div><div class="metric"><b>NZ</b><span>新西兰 WHV</span></div><div class="metric"><b>ertland</b><span>社群支持</span></div></div></section>
<section class="wrap" id="chapters"><div class="section-title"><h2>攻略目录</h2><p>先用卡片快速了解每个主题。正文默认收起，页面不会一上来堆满长文本；需要时再展开阅读。</p></div><div class="cards">{cards}</div></section>
<section class="wrap content-layout" id="read"><aside class="toc"><strong>页面导航</strong>{nav}<a href="#community">社群与联系方式</a></aside><div>{chapter_html}<section class="chapter community" id="community"><div class="chapter-head"><span>社</span><div><h2>社群与联系方式</h2><p>来自原 Notion 页面的社群信息与图片。</p></div></div><details class="chapter-body" open><summary>查看社群信息</summary><div class="article">{community}</div></details></section></div></section></main>
<footer><div class="wrap foot"><div><strong>Ertland</strong><br>新西兰 WHV 打工度假攻略 · ertland.ai.com</div><div>Sky blue × white redesign</div></div></footer>
<script>document.querySelectorAll('.chapter-card').forEach(a=>a.addEventListener('click',()=>{{const el=document.querySelector(a.getAttribute('href')+' .chapter-body'); if(el) el.open=true;}}));</script>
</body></html>'''
Path('index.html').write_text(DOC,encoding='utf-8')
print('wrote',len(DOC),'chapters',len(chapters))
