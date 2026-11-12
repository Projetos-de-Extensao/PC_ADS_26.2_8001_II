"""Render the versioned Mermaid sources locally, with no external diagram service.

Install the optional tool: python -m pip install playwright==1.65.0
Usage: python scripts/render_mermaid.py --library /path/to/mermaid.min.js
       [--browser /path/to/chromium]
"""
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--library',required=True,type=Path)
parser.add_argument('--browser')
args=parser.parse_args()
directory=Path(__file__).resolve().parents[1]/'docs/assets/diagramas'
sources=sorted(directory.glob('*.mmd'))
assert args.library.is_file() and sources,'Informe a biblioteca Mermaid e fontes locais.'
with sync_playwright() as playwright:
    options={'headless':True}
    if args.browser: options['executable_path']=args.browser
    browser=playwright.chromium.launch(**options)
    page=browser.new_page()
    page.set_content('<html><body></body></html>')
    page.add_script_tag(path=str(args.library.resolve()))
    page.evaluate("mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'neutral',fontFamily:'Arial'})")
    for index,source in enumerate(sources):
        svg=page.evaluate("""async ({id,code}) => {
            const rendered=await mermaid.render(id,code);
            const host=document.createElement('div');
            host.innerHTML=rendered.svg;
            return new XMLSerializer().serializeToString(host.querySelector('svg'));
        }""",
            {'id':'raizes_diagrama_'+str(index),'code':source.read_text(encoding='utf-8')})
        source.with_suffix('.svg').write_text(svg,encoding='utf-8')
    browser.close()
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
manifest={p.name:{'source':digest(p),'svg':digest(p.with_suffix('.svg'))} for p in sources}
(directory/'mermaid-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(f'{len(sources)} diagramas Mermaid renderizados localmente.')
