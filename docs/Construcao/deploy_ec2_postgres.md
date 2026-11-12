# Deploy da Raízes: EC2 + PostgreSQL

Esta é a implantação da AP2: projeto Django `raizes_config`, app `lavouraInteligente`, PostgreSQL 16 e Gunicorn, em Amazon Linux 2023/us-east-2.

## 1. Preparação e validação no Windows

Na cópia local do repositório, com Docker Desktop disponível:

```powershell
cd src
Copy-Item .env.example .env
# Edite .env com segredos próprios e ALLOWED_HOSTS=localhost,127.0.0.1.
docker compose up -d --build
docker compose exec web python manage.py test lavouraInteligente
docker compose exec web python manage.py makemigrations --check --dry-run
```

O `.env` fica fora do Git. Os recursos são `/api/produtores/`, `/api/fazendas/`, `/api/talhoes/`, `/api/lotes/` e `/api/lote-itens/`. O endpoint transacional é `POST /api/lotes/receber/`.

## 2. Versionamento

```powershell
git status --short
git add src docs scripts README.md mkdocs.yml
git commit -m "feat: valida entrega AP2 Raízes"
git push origin main
```

Confira que nenhuma senha, chave privada, dump ou `.env` foi incluído. As mudanças de código são preparadas no Windows; a EC2 recebe o código pelo Git.

## 3. Instância e rede

Instância t3.small, Amazon Linux 2023, região us-east-2. O roteiro pede entrada TCP 22 restrita ao IP de administração e TCP 8000 para a API. Não publique 5432. A leitura das regras reais do Security Group depende de uma sessão AWS com permissão; não substitua essa evidência por um diagrama.

## 4. Deploy na EC2

O repositório ativo é `~/PC_ADS_26.2_8001_II`; a cópia antiga em `~/lavouraInteligente/PC_ADS_26.2_8001_II` contém o protótipo SQLite e não é o deploy em execução.

```bash
cd ~/PC_ADS_26.2_8001_II
bash scripts/backup_db.sh
bash scripts/deploy_ec2.sh
cd src
docker compose ps
docker compose exec -T web python manage.py test lavouraInteligente
docker compose exec -T web python manage.py showmigrations
curl -f http://127.0.0.1:8000/api/
```

No primeiro uso, o script cria `.env` privado com segredos aleatórios; em atualizações preserva os segredos e inclui o IP público atual nos hosts/CSRF. O bootstrap executa collectstatic, migrate, criação do Admin e seed opcional. Ele não redefine a senha de um administrador existente.

Se a instância mudar de IP depois de parar/iniciar, execute o deploy novamente e atualize os links do README. Em 11/11/2026 o endereço verificado é `http://18.117.197.72:8000/api/`.

## 5. Persistência e backup

```bash
# Primeiro crie um registro de demonstração identificável pela API.
docker compose down
docker compose up -d
# Aguarde /api/ responder e consulte o mesmo ID/código.
bash ../scripts/backup_db.sh
crontab -l
```

Nunca use `down -v` no deploy: o `pgdata` guarda o banco. Backup local não protege contra perda da instância. Copie o dump para armazenamento externo autorizado e teste a [restauração em banco separado](../Elaboracao/dimrbd.md#52-restauracao-em-banco-separado-validacao-sem-sobrescrever-producao).

## 6. Verificação e reversão

Use os logs, testes e capturas em [Validação da AP2](../Transicao/validacao_ap2.md). Preserve uma imagem estável antes do build. O plano de [rollback](../Transicao/ativ_deploy.md#7-plano-de-rollback) distingue falha de build, falha da aplicação e recuperação do banco.
