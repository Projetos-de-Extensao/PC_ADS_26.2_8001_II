"""Render PlantUML locally; --check verifies the versioned SVG/source pairs.

Usage: python scripts/render_diagrams.py --java java --jar /path/to/plantuml.jar
       python scripts/render_diagrams.py --check
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
directory=root/'docs/assets/diagramas'
manifest_path=directory/'manifest.json'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check',action='store_true')
parser.add_argument('--java',default='java')
parser.add_argument('--jar',type=Path)
args=parser.parse_args()
sources=sorted(directory.glob('*.puml'))
assert sources,'Nenhuma fonte PlantUML encontrada.'
def digest(path): return hashlib.sha256(path.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
if args.check:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    assert set(manifest)=={p.name for p in sources},'Manifesto de diagramas incompleto.'
    for source in sources:
        svg=source.with_suffix('.svg')
        assert manifest[source.name]=={'source':digest(source),'svg':digest(svg)},source.name
    mermaid_sources=sorted(directory.glob('*.mmd'))
    if mermaid_sources:
        mermaid_manifest=json.loads((directory/'mermaid-manifest.json').read_text(encoding='utf-8'))
        assert set(mermaid_manifest)=={p.name for p in mermaid_sources},'Manifesto Mermaid incompleto.'
        for source in mermaid_sources:
            assert mermaid_manifest[source.name]=={'source':digest(source),'svg':digest(source.with_suffix('.svg'))},source.name
        print(f'{len(mermaid_sources)} pares Mermaid/SVG conferidos localmente.')
    print(f'{len(sources)} pares PlantUML/SVG conferidos localmente.')
else:
    assert args.jar and args.jar.is_file(),'Informe --jar com a distribuição oficial PlantUML.'
    command=[args.java,'-Djava.awt.headless=true','-jar',str(args.jar.resolve()),
             '-charset','UTF-8','-tsvg','-failfast2']+[str(p) for p in sources]
    subprocess.run(command,check=True)
    manifest={p.name:{'source':digest(p),'svg':digest(p.with_suffix('.svg'))} for p in sources}
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{len(sources)} diagramas renderizados localmente; nenhum envio externo.')
