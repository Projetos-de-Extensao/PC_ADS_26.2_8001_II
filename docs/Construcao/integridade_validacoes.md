# Integridade, constraints e máscaras

Revisão de 12/11/2026. As migrations `0005` e `0006` reforçam os modelos da AP2 sem
recriar tabelas nem apagar os vínculos existentes. Os testes executam operações por
API, Admin e SQL direto no PostgreSQL.

## Documento do produtor

O portal e o Admin pontuam automaticamente CPF (`529.982.247-25`) e CNPJ
(`11.222.333/0001-81`). A API aceita o documento com ou sem máscara e armazena o valor
canônico sem pontuação, em maiúsculas, preservando zeros à esquerda.

O campo aceita dois tipos: CPF com **11 dígitos** ou CNPJ com **14 caracteres**.
Por isso é `varchar(14)` com `CHECK` de formato, tamanho exato e dígitos verificadores,
em vez de um único `char(11)`, que não comportaria CNPJ. A representação pontuada
ocupa 14 posições para CPF e 18 para CNPJ, mas não é o valor armazenado.

`UNIQUE(documento)` impede o mesmo documento em dois produtores, inclusive quando
uma requisição usa máscara e outra não. O PostgreSQL executa a função imutável
`raizes_documento_valido(text)` dentro do `CHECK`; a validação não depende do JavaScript.
O teste verifica a concordância do algoritmo Python com o algoritmo PostgreSQL.

Também é aceito o CNPJ alfanumérico, com letras nas 12 primeiras posições e dois
dígitos verificadores finais, conforme a [documentação técnica da Receita Federal](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj).
O cálculo usa ASCII menos 48 e módulo 11. A máscara preserva letras: não remove tudo
que não for dígito. Validar formato/DV não comprova titularidade ou situação cadastral.

O identificador reservado `DEMO-RAIZES` pertence somente ao produtor do laboratório,
marcado `simulado=True`. O `CHECK` exige as duas condições juntas; o campo de marcação
é somente leitura na API e o identificador é bloqueado para edição no portal/Admin.
Ele não é apresentado como CPF de uma pessoa.

## Regras e camadas

| Regra | Banco PostgreSQL | API / interface |
| -- | -- | -- |
| Campos obrigatórios | `NOT NULL` e `CHECK` contra texto vazio ou só espaços | Campos obrigatórios e mensagens descritivas |
| CPF/CNPJ | `UNIQUE` + função em `CHECK`; tamanho/DV/formato exatos | Normalização antes da busca de duplicata; máscara automática |
| UF | `varchar(2)` + `CHECK` das 27 UFs | Lista de seleção e normalização em maiúsculas |
| Área de fazenda/talhão | `numeric(p,2)` + `CHECK` positivo e limite finito | Mínimo 0,01 e precisão de duas casas |
| Peso de lote e item | `numeric(12,2)` + `CHECK` positivo e limite finito | Mesmas regras nos serializers/formulários |
| Status e ações | `CHECK` dos domínios permitidos | Escolhas controladas; regras específicas por ação |
| Aceitar uma carga | `CHECK`: ação ACEITAR exige status consultado APROVADO | Revalida origens, validade ambiental e soma dos pesos |
| Relacionamentos | FKs, PKs e unicidade lote/talhão | Exclusão de produtor/fazenda com vínculos é protegida |
| Vistoria aberta | `UNIQUE` parcial por talhão | Reutiliza uma solicitação já aberta |
| JSONB | `CHECK jsonb_typeof(...) = 'object'` | GeoJSON/atributos precisam ser objetos; geometria é validada topologicamente |
| SHA-256 | `CHECK` de 64 caracteres hexadecimais | Hash calculado pelo servidor |
| Upload virtual | `CHECK` de domínio, tamanho e número positivo de partes | Partes idempotentes, cobertura/data/hash e retomada |

A migration `0006` acrescenta **53 CHECKs explícitos**, além das PKs, FKs, `UNIQUE`,
`NOT NULL`, limites dos tipos e verificações de campos inteiros positivos já existentes.
O catálogo da EC2 apresenta 58 CHECKs ao todo, incluindo os anteriores. O índice GIN de `Talhao.atributos` continua preservado. Os limites de texto também são refletidos em `maxlength` nos formulários.

Regras que consultam várias linhas — soma dos pesos, pior risco das origens, mistura
de laboratório/operação e validade de análises — permanecem nas transações da aplicação,
com bloqueios e rollback. Não são anunciadas como `CHECK` de uma única linha. O CRUD
permite montar um lote; a decisão de aceite verifica novamente sua consistência.
O Django Admin/SQL continuam sendo interfaces administrativas e não substituem o fluxo
operacional de revisão/decisão com autoria e justificativa.

## Migração e preservação

1. Backup local antes da atualização; nenhum novo envio de backup S3 é necessário.
2. Normalização dos documentos e detecção de duplicatas antes de reduzir o campo.
3. Correção somente dos dois seeds fictícios conhecidos. Documentos inválidos de outros
   cadastros fazem a migration abortar, indicando IDs sem expor o documento no erro.
4. O produtor fictício adicional de ID 6 teve substituição autorizada pelo responsável;
   a alteração é registrada separadamente, preservando fazendas/talhões e IDs.
5. Aplicação atômica das migrations. Os dados históricos das evidências não são reescritos.

O teste de migração parte da versão `0004`, comprova o bloqueio de documento inválido,
normaliza os documentos válidos e verifica que a FK da fazenda continua apontando para
o mesmo produtor. A suíte também tenta valores zero, negativos e `NaN` por SQL direto.

O Código CAR mantém o formato textual do domínio e dos exemplos acadêmicos. Não se
declara validada a inscrição real no SICAR nem se inventam CEP/telefone em cadastros
que não possuem esses campos.
