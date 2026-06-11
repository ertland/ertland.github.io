from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Tag
import re, shutil, html

site=Path('/Users/yun/ertland.ai.com')
html_path=site/'index.html'
vault=Path('/Users/yun/Documents/文稿 - SZ’s MacBook Pro/Obsidian Vault')
out_dir=vault/'02 项目'/'ertland'
assets_dir=out_dir/'assets'
out_dir.mkdir(parents=True, exist_ok=True)
assets_dir.mkdir(parents=True, exist_ok=True)

for f in (site/'assets').iterdir():
    if f.is_file():
        shutil.copy2(f, assets_dir/f.name)

s=html_path.read_text()
soup=BeautifulSoup(s, 'html.parser')

def clean_text(x):
    return re.sub(r'\s+', ' ', x or '').strip()

def img_src(src):
    if not src: return ''
    if src.startswith('assets/'):
        return 'assets/' + Path(src).name
    return src

def md_children(node):
    return ''.join(md_node(child) for child in node.children)

def md_node(node):
    if isinstance(node, NavigableString):
        return str(node)
    if not isinstance(node, Tag):
        return ''
    name=node.name.lower()
    if name in ['style','script','svg']:
        return ''
    if name in ['h1','h2','h3','h4','h5','h6']:
        level=int(name[1])
        return '\n' + '#' * min(level+1,6) + ' ' + clean_text(node.get_text(' ')) + '\n\n'
    if name=='p':
        txt=md_children(node).strip()
        return (txt+'\n\n') if txt else ''
    if name in ['strong','b']:
        return '**'+md_children(node).strip()+'**'
    if name in ['em','i']:
        return '*'+md_children(node).strip()+'*'
    if name=='br':
        return '\n'
    if name=='hr':
        return '\n---\n\n'
    if name=='a':
        text=clean_text(node.get_text(' ')) or node.get('href','')
        href=node.get('href','')
        return f'[{text}]({href})' if href else text
    if name=='img':
        alt=node.get('alt') or 'image'
        src=img_src(node.get('src',''))
        return f'![{alt}]({src})\n\n' if src else ''
    if name=='pre':
        txt=node.get_text('\n').strip()
        return f'```\n{txt}\n```\n\n' if txt else ''
    if name=='code':
        txt=node.get_text().strip()
        if '\n' in txt:
            return f'```\n{txt}\n```'
        return '`'+txt+'`'
    if name=='ul':
        out=[]
        for li in node.find_all('li', recursive=False):
            item=md_children(li).strip().replace('\n','\n  ')
            out.append(f'- {item}')
        return '\n'.join(out)+'\n\n'
    if name=='ol':
        out=[]
        for idx,li in enumerate(node.find_all('li', recursive=False),1):
            item=md_children(li).strip().replace('\n','\n  ')
            out.append(f'{idx}. {item}')
        return '\n'.join(out)+'\n\n'
    if name=='li':
        return md_children(node)
    if 'check' in node.get('class',[]):
        txt=clean_text(node.get_text(' '))
        return f'- {txt}\n' if txt else ''
    if name=='summary':
        return ''
    return md_children(node)

title=clean_text(soup.select_one('h1').get_text(' ')) if soup.select_one('h1') else 'ertland 新西兰 WHV 申请攻略'
lead=clean_text(soup.select_one('.lead').get_text(' ')) if soup.select_one('.lead') else ''
tag=clean_text(soup.select_one('.tag').get_text(' ')) if soup.select_one('.tag') else ''
countdown=soup.select_one('.countdown')
deadline=countdown.get('data-deadline') if countdown else ''
count_text=clean_text(countdown.get_text(' ')) if countdown else ''

nav_links=[]
for a in soup.select('header nav a'):
    nav_links.append((clean_text(a.get_text(' ')), a.get('href','')))

questions=[]
for m in re.finditer(r"\['([^']+)'\s*,\s*'([^']+)'\]", s):
    questions.append((html.unescape(m.group(1)), html.unescape(m.group(2))))

chapters=[]
for sec in soup.select('section.chapter'):
    if sec.get('id')=='community':
        continue
    h2=sec.select_one('.chapter-head h2')
    if not h2: continue
    num=clean_text(sec.select_one('.chapter-head > span').get_text(' ')) if sec.select_one('.chapter-head > span') else ''
    title_ch=clean_text(h2.get_text(' '))
    body=sec.select_one('.article') or sec
    md=md_children(body)
    md=re.sub(r'\n{3,}', '\n\n', md).strip()
    chapters.append((num,title_ch,md))

community=[]
for card in soup.select('#community .qr-card'):
    h3=clean_text(card.select_one('h3').get_text(' ')) if card.select_one('h3') else ''
    sub=clean_text(card.select_one('.qr-subtitle').get_text(' ')) if card.select_one('.qr-subtitle') else ''
    imgs=card.select('img')
    qr=''
    for im in imgs[::-1]:
        src=im.get('src','')
        if src.startswith('assets/'):
            qr=img_src(src); break
    desc=clean_text(card.find_all('p')[-1].get_text(' ')) if card.find_all('p') else ''
    community.append((h3,sub,qr,desc))

lines=[]
lines.append('---')
lines.append('title: ertland.ai.com 页面内容')
lines.append('source: https://ertland.ai.com/')
lines.append('local_source: /Users/yun/ertland.ai.com/index.html')
lines.append('created: 2026-06-08 20:09:25 CST')
lines.append('tags: [ertland, WHV, 新西兰打工度假, website]')
lines.append('---\n')
lines.append(f'# {title}\n')
if tag: lines.append(f'**页面标签：** {tag}\n')
if lead: lines.append(f'**页面简介：** {lead}\n')
lines.append('**网站域名：** https://ertland.ai.com/\n')
if deadline:
    lines.append(f'**倒计时截止时间：** `{deadline}`\n')
if count_text:
    lines.append(f'**倒计时模块文案：** {count_text}\n')

lines.append('## 顶部导航\n')
for text,href in nav_links:
    lines.append(f'- [{text}]({href})')
lines.append('')

if questions:
    lines.append('## 资格自查（9 个问题）\n')
    for i,(q,note) in enumerate(questions,1):
        lines.append(f'{i}. **{q}**')
        lines.append(f'   - {note}')
    lines.append('')

lines.append('## 攻略正文\n')
for num,title_ch,md in chapters:
    prefix=f'{num}. ' if num else ''
    lines.append(f'### {prefix}{title_ch}\n')
    lines.append(md if md else '_（暂无内容，可后续补充。）_')
    lines.append('')

if community:
    lines.append('## 关注 ertland / 社群入口\n')
    for h3,sub,qr,desc in community:
        lines.append(f'### {h3}｜{sub}\n')
        if desc: lines.append(f'{desc}\n')
        if qr: lines.append(f'![{h3} {sub}]({qr})\n')

lines.append('## 页脚\n')
lines.append('ertland.ai.com\n')

content='\n'.join(lines)
out=out_dir/'ertland.ai.com 页面内容.md'
out.write_text(content)
print('NOTE_PATH='+str(out))
print('ASSETS_DIR='+str(assets_dir))
print('CHAPTERS='+str(len(chapters)))
print('QUESTIONS='+str(len(questions)))
print('COMMUNITY_CARDS='+str(len(community)))
print('NOTE_SIZE='+str(out.stat().st_size))
print('ASSETS_COPIED='+str(len(list(assets_dir.iterdir()))))
