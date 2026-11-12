# CI e publicação da documentação

O workflow `.github/workflows/mkdocs.yml` instala as dependências do arquivo `requirements.txt`, executa `mkdocs build --strict` e publica `gh-pages` somente após sucesso na branch main. Pull requests validam o site. O código da aplicação é atualizado na EC2 pelo script de deploy; publicar o MkDocs não atualiza os containers.


## Diagramas locais

Os diagramas PlantUML ficam em `docs/assets/diagramas/*.puml`, acompanhados dos SVGs renderizados. O site usa esses SVGs e o CI verifica os hashes com `python scripts/render_diagrams.py --check`, sem enviar a arquitetura para um serviço externo. Para regenerar: `python scripts/render_diagrams.py --java java --jar caminho/plantuml.jar`. O Java e o JAR são ferramentas locais; não entram no repositório.

Os sete diagramas Mermaid também possuem fonte `.mmd`, SVG e manifesto de hashes. Para regenerar, instale a ferramenta opcional Playwright e execute `python scripts/render_mermaid.py --library caminho/mermaid.min.js --browser caminho/chromium`. A validação desta revisão usou Mermaid 10.9.5 localmente; as páginas finais não dependem de executar Mermaid no navegador.
