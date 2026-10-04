from pathlib import Path
from html import escape
import zipfile, uuid, re, json, difflib
from xml.etree import ElementTree as ET
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from pypdf import PdfReader
import pypdfium2 as pdfium
from PIL import Image, ImageOps, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / 'trabalho_editorial'
OUT = ROOT / 'entregaveis'
OUT.mkdir(exist_ok=True)
title = 'O espelho de lama, sangue e lã'
source = (WORK / 'manuscrito-final.md').read_text(encoding='utf-8')
blocks = source.strip().split('\n\n')
sections = []
current = {'title': title, 'paras': []}
for block in blocks[1:]:
    if block.startswith('## '):
        sections.append(current)
        current = {'title': block[3:], 'paras': []}
    else:
        current['paras'].append(block)
sections.append(current)

pdfmetrics.registerFont(TTFont('GeorgiaBook', 'C:/Windows/Fonts/georgia.ttf'))
pdfmetrics.registerFont(TTFont('GeorgiaBookBold', 'C:/Windows/Fonts/georgiab.ttf'))
body = ParagraphStyle('body', fontName='GeorgiaBook', fontSize=11, leading=16,
                      alignment=TA_JUSTIFY, firstLineIndent=5*mm, spaceAfter=5,
                      allowWidows=0, allowOrphans=0)
dialogue = ParagraphStyle('dialogue', parent=body, firstLineIndent=0, spaceAfter=7)
heading = ParagraphStyle('heading', fontName='GeorgiaBookBold', fontSize=17,
                         leading=23, alignment=TA_CENTER, spaceAfter=22,
                         keepWithNext=True)
cover_title = ParagraphStyle('cover_title', parent=heading, fontSize=25, leading=33)
pdf_path = OUT / 'o-espelho-de-lama-sangue-e-la.pdf'
doc = SimpleDocTemplate(str(pdf_path), pagesize=(148*mm,210*mm),
                        leftMargin=19*mm, rightMargin=19*mm,
                        topMargin=20*mm, bottomMargin=20*mm,
                        title=title, author='')
story = [Spacer(1,45*mm), Paragraph(escape(title), cover_title), PageBreak()]
for i,section in enumerate(sections):
    if i:
        story.append(PageBreak())
        story.append(Paragraph(escape(section['title']), heading))
    for para in section['paras']:
        story.append(Paragraph(escape(para), dialogue if para.startswith('—') else body))
def footer(canvas, doc):
    if doc.page > 1:
        canvas.setFont('GeorgiaBook', 9)
        canvas.drawCentredString(74*mm, 12*mm, str(doc.page-1))
doc.build(story, onFirstPage=footer, onLaterPages=footer)

css = '''body{font-family:serif;line-height:1.5;margin:1.2em;}h1,h2{text-align:center;line-height:1.25;margin:2em 0 1.5em;}p{text-indent:1.5em;margin:0 0 .6em;}p.dialogue{text-indent:0;margin-bottom:.8em;}'''
pages = []
for i,section in enumerate(sections):
    paras = '\n'.join('<p'+(' class="dialogue"' if p.startswith('—') else '')+'>'+escape(p)+'</p>' for p in section['paras'])
    level = 'h1' if i==0 else 'h2'
    pages.append(f'''<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR" xml:lang="pt-BR"><head><title>{escape(section['title'])}</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body><section epub:type="{'bodymatter' if i==0 else 'chapter'}"><{level}>{escape(section['title'])}</{level}>{paras}</section></body></html>''')
uid = 'urn:uuid:'+str(uuid.uuid5(uuid.NAMESPACE_URL,'https://github.com/vorneermel/o-espelho-de-lama-sangue-e-la/revisao-2026-10-04'))
nav_links = ''.join(f'<li><a href="texto-{i+1}.xhtml">{escape(s["title"])}</a></li>' for i,s in enumerate(sections))
nav = f'''<?xml version="1.0" encoding="utf-8"?><html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="pt-BR" xml:lang="pt-BR"><head><title>Sumário</title><link rel="stylesheet" type="text/css" href="style.css"/></head><body><nav epub:type="toc" id="toc"><h1>Sumário</h1><ol>{nav_links}</ol></nav></body></html>'''
manifest = ''.join(f'<item id="texto{i+1}" href="texto-{i+1}.xhtml" media-type="application/xhtml+xml"/>' for i in range(len(pages)))
spine = ''.join(f'<itemref idref="texto{i+1}"/>' for i in range(len(pages)))
opf = f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id" xml:lang="pt-BR"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="book-id">{uid}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:language>pt-BR</dc:language><meta property="dcterms:modified">2026-10-04T03:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" properties="nav" media-type="application/xhtml+xml"/><item id="css" href="style.css" media-type="text/css"/>{manifest}</manifest><spine>{spine}</spine></package>'''
container = '''<?xml version="1.0" encoding="utf-8"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
epub_path = OUT / 'o-espelho-de-lama-sangue-e-la.epub'
with zipfile.ZipFile(epub_path,'w') as z:
    z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED)
    for name,data in [('META-INF/container.xml',container),('OEBPS/content.opf',opf),('OEBPS/nav.xhtml',nav),('OEBPS/style.css',css)]+[(f'OEBPS/texto-{i+1}.xhtml',p) for i,p in enumerate(pages)]:
        z.writestr(name,data,compress_type=zipfile.ZIP_DEFLATED)

html = f'<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>{escape(title)}</title><style>body{{max-width:42em;margin:3em auto;padding:0 1.5em;font-size:19px;}}{css}</style><body>'
for section in sections:
    html += '<h2>'+escape(section['title'])+'</h2>'
    html += ''.join('<p'+(' class="dialogue"' if p.startswith('—') else '')+'>'+escape(p)+'</p>' for p in section['paras'])
html += '</body></html>'
(OUT/'o-espelho-de-lama-sangue-e-la.html').write_text(html,encoding='utf-8')
(OUT/'o-espelho-de-lama-sangue-e-la.md').write_text(source,encoding='utf-8')
parts = WORK/'secoes-editaveis'; parts.mkdir(exist_ok=True)
for i,s in enumerate(sections):
    (parts/f'{i+1:02d}-secao.md').write_text('# '+s['title']+'\n\n'+'\n\n'.join(s['paras'])+'\n',encoding='utf-8')
old = (WORK/'manuscrito-continuidade-v0.md').read_text(encoding='utf-8')
(WORK/'comparacao-revisao.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),source.splitlines(True),fromfile='manuscrito-continuidade-v0.md',tofile='manuscrito-final.md')),encoding='utf-8')

# Verificação independente dos arquivos reabertos.
plain = ' '.join(p for s in sections for p in s['paras'])
norm = lambda t: re.sub(r'\s+','',t)
r = PdfReader(pdf_path)
pdf_body = ''
for page in r.pages[1:]:
    text = page.extract_text() or ''
    text = re.sub(r'^\d+\s*\n','',text)
    text = text.replace('Eco do chiqueiro e da alcateia','')
    pdf_body += text
assert norm(pdf_body)==norm(plain), 'Texto do PDF diverge da fonte'
font_checks=[]
for page in r.pages:
    for _,ref in page['/Resources']['/Font'].items():
        font=ref.get_object(); descriptor=font.get('/FontDescriptor')
        if descriptor:
            fd=descriptor.get_object(); font_checks.append(any(k in fd for k in ['/FontFile','/FontFile2','/FontFile3']))
assert font_checks and all(font_checks)
with zipfile.ZipFile(epub_path) as z:
    assert z.infolist()[0].filename=='mimetype' and z.infolist()[0].compress_type==0
    assert z.read('mimetype')==b'application/epub+zip'
    for name in z.namelist():
        if name.endswith(('.xml','.opf','.xhtml')): ET.fromstring(z.read(name))
    ns={'x':'http://www.w3.org/1999/xhtml','o':'http://www.idpf.org/2007/opf'}
    collected=[]
    for i in range(len(sections)):
        tree=ET.fromstring(z.read(f'OEBPS/texto-{i+1}.xhtml'))
        collected += [''.join(el.itertext()) for el in tree.findall('.//x:p',ns)]
    assert collected==[p for s in sections for p in s['paras']]
    package=ET.fromstring(z.read('OEBPS/content.opf'))
    items={x.attrib['id']:x.attrib['href'] for x in package.findall('.//o:manifest/o:item',ns)}
    for href in items.values(): assert 'OEBPS/'+href in z.namelist()
    for item in package.findall('.//o:spine/o:itemref',ns): assert item.attrib['idref'] in items
    navtree=ET.fromstring(z.read('OEBPS/nav.xhtml'))
    for a in navtree.findall('.//x:a',ns): assert 'OEBPS/'+a.attrib['href'] in z.namelist()
preview=WORK/'previas-finais'; preview.mkdir(exist_ok=True)
pd=pdfium.PdfDocument(str(pdf_path)); thumbs=[]
for i in range(len(pd)):
    im=pd[i].render(scale=1.25).to_pil().convert('RGB'); im.save(preview/f'pagina-{i+1:02d}.png')
    thumb=ImageOps.contain(im,(300,426)); tile=Image.new('RGB',(320,456),'#dddddd'); tile.paste(thumb,((320-thumb.width)//2,10)); ImageDraw.Draw(tile).text((10,438),f'Página {i+1}',fill='black'); thumbs.append(tile)
for start in range(0,len(thumbs),6):
    canvas=Image.new('RGB',(960,912),'white')
    for j,im in enumerate(thumbs[start:start+6]): canvas.paste(im,((j%3)*320,(j//3)*456))
    canvas.save(preview/f'contato-{start//6+1}.png')
result={'paginas_pdf':len(r.pages),'palavras_texto':len(plain.split()),'integridade_pdf':'corpo idêntico à fonte após normalização de espaços','fontes':'Georgia incorporada','epub':'ZIP, XML, manifesto, spine, links de sumário e texto conferidos','epubcheck':'não executado','kindle_previewer':'não executado','autoria':'omitida; não informada','nome_taberna':'Pouso di Vaca — leitura provisória'}
(WORK/'validacao-formatos.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
