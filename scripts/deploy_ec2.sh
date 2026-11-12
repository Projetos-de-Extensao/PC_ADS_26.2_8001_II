#!/usr/bin/env bash
# Deploy completo da API Lavoura Inteligente numa EC2 Amazon Linux 2023.
# Idempotente: pode ser executado de novo a cada atualização do código.
#
# Uso na EC2:
#   curl -fsSL https://raw.githubusercontent.com/Projetos-de-Extensao/PC_ADS_26.2_8001_II/main/scripts/deploy_ec2.sh | bash
# ou, com o repositório já clonado:
#   bash ~/PC_ADS_26.2_8001_II/scripts/deploy_ec2.sh
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Projetos-de-Extensao/PC_ADS_26.2_8001_II.git}"
APP_DIR="${APP_DIR:-$HOME/PC_ADS_26.2_8001_II}"
COMPOSE_VERSION="${COMPOSE_VERSION:-v5.7.0}"
BUILDX_VERSION="${BUILDX_VERSION:-v0.38.2}"
PLUGIN_DIR=/usr/local/lib/docker/cli-plugins
USUARIO="${USER:-$(id -un)}"

passo() { printf '\n==> %s\n' "$*"; }

# IP público da instância pelo serviço de metadados da EC2 (IMDSv2); vazio fora da AWS.
ip_publico() {
  local token
  token=$(curl -fs -m 2 -X PUT http://169.254.169.254/latest/api/token \
    -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
  curl -fs -m 2 -H "X-aws-ec2-metadata-token: ${token}" \
    http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || true
}

passo "1/6 Docker e Git"
command -v docker >/dev/null 2>&1 || sudo dnf install -y docker
command -v git >/dev/null 2>&1 || sudo dnf install -y git
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl enable --now docker
fi
if ! id -nG "$USUARIO" | grep -qw docker; then
  sudo usermod -aG docker "$USUARIO" || true
fi

passo "2/6 Plugins Docker Compose (${COMPOSE_VERSION}) e Buildx (${BUILDX_VERSION})"
case "$(uname -m)" in
  x86_64)  COMPOSE_ARCH=x86_64;  BUILDX_ARCH=amd64 ;;
  aarch64) COMPOSE_ARCH=aarch64; BUILDX_ARCH=arm64 ;;
  *) echo "Arquitetura não suportada: $(uname -m)" >&2; exit 1 ;;
esac
sudo mkdir -p "$PLUGIN_DIR"
if [ ! -x "$PLUGIN_DIR/docker-compose" ]; then
  sudo curl -fsSL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-${COMPOSE_ARCH}" \
    -o "$PLUGIN_DIR/docker-compose"
  sudo chmod +x "$PLUGIN_DIR/docker-compose"
fi
if [ ! -x "$PLUGIN_DIR/docker-buildx" ]; then
  sudo curl -fsSL "https://github.com/docker/buildx/releases/download/${BUILDX_VERSION}/buildx-${BUILDX_VERSION}.linux-${BUILDX_ARCH}" \
    -o "$PLUGIN_DIR/docker-buildx"
  sudo chmod +x "$PLUGIN_DIR/docker-buildx"
fi

# Até reconectar o SSH depois do usermod, o usuário ainda não está no grupo docker.
if docker info >/dev/null 2>&1; then DOCKER="docker"; else DOCKER="sudo docker"; fi
$DOCKER compose version
$DOCKER buildx version

passo "3/6 Código (git clone / git pull)"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR/src"

passo "4/6 Arquivo .env (segredos fora do Git)"
if [ -f .env ]; then
  echo ".env já existe: mantido sem alterações."
else
  IP=$(ip_publico)
  aleatorio() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
  SECRET=$(aleatorio 50)
  PG_PASS=$(aleatorio 24)
  ADMIN_PASS=$(aleatorio 12)
  if [ -n "$IP" ]; then HOSTS="localhost,127.0.0.1,${IP}"; ORIGINS="http://${IP}:8000"; else HOSTS="*"; ORIGINS=""; fi
  sed -e "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" \
      -e "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=${HOSTS}|" \
      -e "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=${ORIGINS}|" \
      -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${PG_PASS}|" \
      -e "s|^DJANGO_SUPERUSER_PASSWORD=.*|DJANGO_SUPERUSER_PASSWORD=${ADMIN_PASS}|" \
      .env.example > .env
  chmod 600 .env
  echo ".env criado (permissão 600). Consulte a senha do Admin somente no arquivo privado."
  echo "Guarde essa senha; ela também fica em $APP_DIR/src/.env"
fi

# Uma EC2 sem Elastic IP pode mudar de endereço após parar/iniciar.
# Inclua o host atual e preserve os valores personalizados e os segredos existentes.
IP_ATUAL=$(ip_publico)
if [ -n "$IP_ATUAL" ]; then
  python3 - "$IP_ATUAL" <<'PYHOST'
from pathlib import Path
import sys
p = Path('.env')
lines = p.read_text().splitlines()
additions = {'ALLOWED_HOSTS': sys.argv[1], 'CSRF_TRUSTED_ORIGINS': 'http://' + sys.argv[1] + ':8000'}
for i, line in enumerate(lines):
    key, sep, value = line.partition('=')
    if key in additions and sep:
        values = [v.strip() for v in value.split(',') if v.strip()]
        item = additions.pop(key)
        if item not in values:
            values.append(item)
        lines[i] = key + '=' + ','.join(values)
lines.extend(key + '=' + value for key, value in additions.items())
p.write_text('\n'.join(lines) + '\n')
p.chmod(0o600)
PYHOST
fi

passo "5/6 Build e subida dos containers (web + db)"
$DOCKER compose up -d --build
$DOCKER compose ps

passo "6/6 Verificação"
for _ in $(seq 1 30); do
  if curl -fs -o /dev/null http://localhost:8000/api/; then break; fi
  sleep 2
done
if curl -fs -o /dev/null http://localhost:8000/api/; then
  IP_ATUAL=$(ip_publico)
  IP_ATUAL=${IP_ATUAL:-<IP_PUBLICO_EC2>}
  echo "API no ar:   http://${IP_ATUAL}:8000/api/"
  echo "Admin:       http://${IP_ATUAL}:8000/admin/"
  echo "Lembre de liberar a porta 8000 (TCP) no Security Group."
else
  echo "A API não respondeu. Veja os logs com: cd $APP_DIR/src && $DOCKER compose logs web" >&2
  exit 1
fi
