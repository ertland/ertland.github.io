import json, html, re, urllib.parse
from pathlib import Path

DATA=json.load(open('notion_pages.json'))

def norm_id(x): return x.replace('-','')

def get_blocks(data):
    return {k:v['value']['value'] for k,v in data.get('recordMap',{}).get('block',{}).items() if v.get('value',{}).get('value')}

ALL_BLOCKS={}
for data in DATA.values():
    ALL_BLOCKS.update(get_blocks(data))

def rich(prop):
    if not prop: return ''
    out=[]
    for seg in prop:
        text=html.escape(seg[0])
        ann=seg[1] if len(seg)>1 else []
        href=None
        for a in ann:
            if a[0]=='a': href=a[1]
        if any(a[0]=='b' for a in ann): text=f'<strong>{text}</strong>'
        if any(a[0]=='i' for a in ann): text=f'<em>{text}</em>'
        if any(a[0]=='c' for a in ann): text=f'<code>{text}</code>'
        if any(a[0]=='s' for a in ann): text=f'<s>{text}</s>'
        if href: text=f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{text}</a>'
        out.append(text)
    return ''.join(out).replace('\n','<br>')

def title(b): return rich(b.get('properties',{}).get('title'))

def plain_title(b):
    prop=b.get('properties',{}).get('title') or []
    return ''.join(seg[0] for seg in prop)

def slug(s):
    s=re.sub(r'\s+','-',s.strip().lower())
    s=re.sub(r'[^\w\u4e00-\u9fff-]+','',s)
    return s[:80] or 'section'

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

def render_children(parent_id, depth=0):
    b=ALL_BLOCKS.get(parent_id,{})
    ids=b.get('content') or []
    parts=[]
    i=0
    while i < len(ids):
        bid=ids[i]; cb=ALL_BLOCKS.get(bid)
        if not cb:
            i+=1; continue
        t=cb.get('type')
        if t in ('bulleted_list','numbered_list'):
            tag='ul' if t=='bulleted_list' else 'ol'
            items=[]
            while i < len(ids) and ALL_BLOCKS.get(ids[i],{}).get('type')==t:
                ib=ALL_BLOCKS[ids[i]]
                nested=render_children(ids[i],depth+1)
                items.append(f'<li>{title(ib)}{nested}</li>')
                i+=1
            parts.append(f'<{tag}>'+''.join(items)+f'</{tag}>')
            continue
        parts.append(render_block(bid, cb, depth))
        i+=1
    return ''.join(parts)

def render_block(bid,b,depth=0):
    t=b.get('type')
    txt=title(b)
    children=render_children(bid,depth+1) if b.get('content') and t not in ('page',) else ''
    if t=='text':
        return f'<p>{txt}</p>{children}' if txt else children
    if t=='header': return f'<h2>{txt}</h2>{children}'
    if t=='sub_header': return f'<h3>{txt}</h3>{children}'
    if t=='sub_sub_header': return f'<h4>{txt}</h4>{children}'
    if t=='divider': return '<hr>'
    if t=='to_do':
        checked=b.get('properties',{}).get('checked',[["No"]])[0][0]=='Yes'
        return f'<div class="todo"><span>{"✓" if checked else ""}</span><div>{txt}</div></div>{children}'
    if t=='toggle':
        return f'<details><summary>{txt}</summary>{children}</details>'
    if t=='code':
        lang=html.escape((b.get('properties',{}).get('language') or [['']])[0][0])
        raw=''.join(seg[0] for seg in (b.get('properties',{}).get('title') or []))
        return f'<pre><code data-lang="{lang}">{html.escape(raw)}</code></pre>'
    if t=='image':
        src=image_url(bid,b)
        cap=rich(b.get('properties',{}).get('caption'))
        return f'<figure><img loading="lazy" src="{html.escape(src)}" alt="{html.escape(cap or "Ertland image")}">{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>'
    if t=='file':
        src=image_url(bid,b); label=txt or '下载文件'
        return f'<p><a class="file-link" href="{html.escape(src)}" target="_blank" rel="noopener">{label}</a></p>'
    if t in ('column_list','column'):
        return f'<div class="columns">{children}</div>' if t=='column_list' else f'<div class="column">{children}</div>'
    if t=='page':
        return ''
    return f'<p>{txt}</p>{children}' if txt else children

root='c7fede65-1a85-4126-899c-d21599479714'
rootb=ALL_BLOCKS[root]

def collect_pages(pid, out):
    for cid in ALL_BLOCKS.get(pid,{}).get('content') or []:
        cb=ALL_BLOCKS.get(cid,{})
        if cb.get('type')=='page':
            out.append(cid)
        else:
            collect_pages(cid,out)
subpage_ids=[]
collect_pages(root, subpage_ids)
root_titles=[]
for cid in rootb.get('content',[]):
    b=ALL_BLOCKS.get(cid,{})
    if b.get('type')=='sub_header': root_titles.append(plain_title(b))
sections=[]
for pid in subpage_ids:
    b=ALL_BLOCKS[pid]
    pt=plain_title(b)
    sid=slug(pt)
    body=render_children(pid)
    sections.append((sid,pt,body))

nav=''.join(f'<a href="#{sid}">{html.escape(pt)}</a>' for sid,pt,_ in sections)
section_html='\n'.join(f'<section class="content-section" id="{sid}"><div class="section-num">{i:02d}</div><article class="notion-article"><h2>{html.escape(pt)}</h2>{body}</article></section>' for i,(sid,pt,body) in enumerate(sections,1))
community=render_children(root)

html_doc=f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>新西兰 WHV 打工度假攻略 | Ertland</title>
<meta name="description" content="Ertland 新西兰 WHV 打工度假攻略：申请资格、流程、抢名额、递签、常见问题与社群信息。">
<meta property="og:title" content="新西兰 WHV 打工度假攻略 | Ertland">
<meta property="og:description" content="申请资格、流程、抢名额、递签攻略与社群信息。">
<meta property="og:url" content="https://ertland.ai.com/">
<style>
:root{{--sky-50:#f0f9ff;--sky-100:#e0f2fe;--sky-200:#bae6fd;--sky-300:#7dd3fc;--sky-400:#38bdf8;--sky-500:#0ea5e9;--sky-600:#0284c7;--sky-700:#0369a1;--ink:#0f172a;--muted:#516170;--line:rgba(14,165,233,.20);--white:#fff;--shadow:0 24px 80px rgba(2,132,199,.14);--radius:28px}}
*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;font-family:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,"Helvetica Neue",Arial,"PingFang SC","Microsoft YaHei",sans-serif;color:var(--ink);background:radial-gradient(circle at 12% 4%,rgba(125,211,252,.42),transparent 30%),radial-gradient(circle at 90% 2%,rgba(186,230,253,.62),transparent 28%),linear-gradient(180deg,var(--sky-50),#fff 36%,var(--sky-50));}}a{{color:var(--sky-700);text-decoration:none}}a:hover{{text-decoration:underline}}.shell{{width:min(1180px,calc(100% - 40px));margin:0 auto}}header{{position:sticky;top:0;z-index:20;backdrop-filter:blur(18px);background:rgba(255,255,255,.78);border-bottom:1px solid rgba(186,230,253,.72)}}.nav{{height:76px;display:flex;align-items:center;justify-content:space-between;gap:18px}}.brand{{display:flex;align-items:center;gap:12px;font-weight:900;letter-spacing:-.03em;color:var(--ink)}}.logo{{width:38px;height:38px;border-radius:14px;background:linear-gradient(135deg,var(--sky-300),var(--sky-600));box-shadow:0 10px 30px rgba(14,165,233,.28);display:grid;place-items:center;color:white}}.navlinks{{display:flex;gap:18px;align-items:center;color:var(--muted);font-size:14px}}.button{{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 18px;border-radius:999px;background:var(--sky-500);color:white;font-weight:800;box-shadow:0 14px 34px rgba(14,165,233,.28)}}.hero{{padding:86px 0 52px;display:grid;grid-template-columns:1.02fr .98fr;gap:46px;align-items:center}}.eyebrow{{display:inline-flex;padding:8px 12px;border-radius:999px;background:white;border:1px solid var(--line);color:var(--sky-700);font-weight:800;font-size:13px;box-shadow:0 8px 26px rgba(14,165,233,.08)}}h1{{font-size:clamp(42px,6.4vw,78px);line-height:.98;letter-spacing:-.07em;margin:20px 0 20px;color:#07182c;text-wrap:balance}}.lead{{font-size:clamp(18px,2vw,22px);line-height:1.75;color:var(--muted);margin:0 0 28px;max-width:680px}}.hero-card{{background:rgba(255,255,255,.84);border:1px solid var(--line);border-radius:var(--radius);padding:26px;box-shadow:var(--shadow)}}.hero-card h2{{font-size:28px;margin:0 0 16px;letter-spacing:-.04em}}.quick{{display:grid;gap:10px}}.quick a{{display:flex;justify-content:space-between;gap:14px;align-items:center;padding:13px 14px;border-radius:16px;background:var(--sky-50);border:1px solid var(--line);font-weight:700;color:#075985}}.stats{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px}}.stat{{padding:18px;border-radius:18px;background:white;border:1px solid var(--line)}}.stat b{{display:block;font-size:26px;color:var(--sky-700)}}.stat span{{color:var(--muted);font-size:13px}}.layout{{display:grid;grid-template-columns:280px 1fr;gap:26px;align-items:start;padding:40px 0 86px}}.toc{{position:sticky;top:96px;background:rgba(255,255,255,.86);border:1px solid var(--line);border-radius:24px;padding:18px;box-shadow:0 16px 46px rgba(2,132,199,.08);max-height:calc(100vh - 120px);overflow:auto}}.toc b{{display:block;margin:0 0 12px;color:var(--sky-700)}}.toc a{{display:block;padding:10px 12px;border-radius:12px;color:var(--muted);font-size:14px}}.toc a:hover{{background:var(--sky-50);color:var(--sky-700);text-decoration:none}}.content-section{{display:grid;grid-template-columns:62px 1fr;gap:18px;margin-bottom:26px}}.section-num{{height:54px;border-radius:18px;background:linear-gradient(135deg,var(--sky-200),white);border:1px solid var(--line);display:grid;place-items:center;color:var(--sky-700);font-weight:900}}.notion-article{{background:rgba(255,255,255,.9);border:1px solid var(--line);border-radius:28px;padding:30px;box-shadow:0 18px 58px rgba(2,132,199,.09)}}.notion-article h2{{font-size:clamp(30px,4vw,48px);line-height:1.08;letter-spacing:-.05em;margin:0 0 22px;color:#07182c}}.notion-article h3{{font-size:26px;margin:30px 0 12px;letter-spacing:-.035em;color:#075985}}.notion-article h4{{font-size:20px;margin:24px 0 10px;color:#0f3d5c}}.notion-article p,.notion-article li{{font-size:16px;line-height:1.86;color:#344454}}.notion-article p{{margin:12px 0}}.notion-article ul,.notion-article ol{{padding-left:1.35em;margin:12px 0}}.notion-article hr{{border:0;border-top:1px solid var(--line);margin:28px 0}}.notion-article figure{{margin:22px 0;border-radius:22px;overflow:hidden;border:1px solid var(--line);background:var(--sky-50)}}.notion-article img{{display:block;width:100%;height:auto}}figcaption{{padding:10px 14px;color:var(--muted);font-size:13px}}.todo{{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border:1px solid var(--line);background:var(--sky-50);border-radius:16px;margin:10px 0;color:#344454;line-height:1.7}}.todo span{{width:22px;height:22px;border-radius:7px;border:1px solid var(--sky-300);background:white;display:grid;place-items:center;color:var(--sky-600);font-weight:900;flex:0 0 auto}}details{{border:1px solid var(--line);border-radius:18px;background:var(--sky-50);padding:14px 16px;margin:12px 0}}summary{{font-weight:800;color:#075985;cursor:pointer}}pre{{white-space:pre-wrap;background:#082f49;color:#e0f2fe;border-radius:18px;padding:18px;overflow:auto}}code{{background:var(--sky-100);color:#075985;border-radius:6px;padding:2px 5px}}pre code{{background:transparent;color:inherit;padding:0}}.columns{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}.column{{min-width:0}}.community{{margin-top:26px;background:linear-gradient(135deg,var(--sky-100),white);border:1px solid var(--line);border-radius:28px;padding:28px;box-shadow:var(--shadow)}}footer{{padding:40px 0 60px;color:var(--muted)}}.footer-inner{{border-top:1px solid var(--line);padding-top:24px;display:flex;justify-content:space-between;gap:18px;flex-wrap:wrap}}@media(max-width:900px){{.navlinks{{display:none}}.hero,.layout{{grid-template-columns:1fr}}.toc{{position:static;max-height:none}}.content-section{{grid-template-columns:1fr}}.section-num{{width:54px}}.stats{{grid-template-columns:1fr}}.shell{{width:min(100% - 28px,1180px)}}}}
</style></head>
<body><header><div class="shell nav"><a class="brand" href="#top"><span class="logo">🇳🇿</span><span>Ertland</span></a><nav class="navlinks"><a href="#guide">攻略目录</a><a href="#community">社群</a><a href="https://ertland.ai.com/">ertland.ai.com</a></nav><a class="button" href="#guide">开始查看</a></div></header>
<main id="top"><div class="shell hero"><div><span class="eyebrow">新西兰 WHV · 打工度假攻略</span><h1>新西兰 WHV 打工度假攻略</h1><p class="lead">整理自 Ertland Notion 页面，涵盖 WHV 科普、申请资格、名额开抢、递签攻略、确认信示例与社群信息。整体采用你喜欢的天蓝色 + 白色配色。</p><a class="button" href="#guide">查看完整攻略</a></div><aside class="hero-card"><h2>快速入口</h2><div class="quick">{nav}</div><div class="stats"><div class="stat"><b>{len(sections)}</b><span>攻略章节</span></div><div class="stat"><b>2026</b><span>递签更新</span></div><div class="stat"><b>NZ</b><span>WHV</span></div></div></aside></div>
<div class="shell layout" id="guide"><aside class="toc"><b>目录</b>{nav}<a href="#community">社群与联系方式</a></aside><div>{section_html}<section class="community" id="community"><div class="section-num">社群</div><article class="notion-article"><h2>ertland 社群</h2>{community}</article></section></div></div></main>
<footer><div class="shell footer-inner"><div><b>Ertland</b><br>新西兰 WHV 打工度假攻略 · ertland.ai.com</div><div>© 2026 Ertland</div></div></footer></body></html>'''
Path('index.html').write_text(html_doc, encoding='utf-8')
print('written index.html', len(html_doc), 'sections', len(sections))
