#!/bin/bash
# ⛵ Email Sail Agent — Deploy Script
# Run on a fresh Ubuntu 24.04 DigitalOcean droplet
#
# Usage: ./deploy.sh
#   or:  curl -sSL https://raw.githubusercontent.com/TheInnerI/email-sail-agent/main/scripts/deploy.sh | bash

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────
EMAIL_SAIL_DIR="/opt/email-sail-agent"
EMAIL_SAIL_REPO="https://github.com/TheInnerI/email-sail-agent.git"
EMAIL_SAIL_DOMAIN="${EMAIL_SAIL_DOMAIN:-email-sail.innerinetcompany.com}"

YESHUA_DIR="/opt/yeshua-architect-platform"
YESHUA_REPO="https://github.com/TheInnerI/yeshua-architect-platform.git"
YESHUA_DOMAIN="${YESHUA_DOMAIN:-architect.innerinetcompany.com}"

# ── Colors ─────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ── Pre-flight ─────────────────────────────────────────────────
echo ""
echo "⛵ Email Sail Agent — Deployment Script"
echo "======================================"
echo ""

if [[ $EUID -ne 0 ]]; then
    error "This script must be run as root (use sudo)"
fi

# ── Install Docker ──────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    apt-get update -qq
    apt-get install -y -qq ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
    ok "Docker installed"
else
    ok "Docker already installed"
fi

# ── Clone / Update repos ───────────────────────────────────────
info "Cloning repositories..."

if [[ -d "$EMAIL_SAIL_DIR/.git" ]]; then
    cd "$EMAIL_SAIL_DIR" && git pull
    ok "Email Sail updated"
else
    git clone "$EMAIL_SAIL_DIR" "$EMAIL_SAIL_DIR"
    ok "Email Sail cloned"
fi

if [[ -d "$YESHUA_DIR/.git" ]]; then
    cd "$YESHUA_DIR" && git pull
    ok "Yeshua Architect updated"
else
    git clone "$YESHUA_REPO" "$YESHUA_DIR"
    ok "Yeshua Architect cloned"
fi

# ── Environment files ──────────────────────────────────────────
echo ""
info "Setting up environment files..."

if [[ ! -f "$EMAIL_SAIL_DIR/.env" ]]; then
    cp "$EMAIL_SAIL_DIR/.env.example" "$EMAIL_SAIL_DIR/.env"
    warn "Created $EMAIL_SAIL_DIR/.env — you MUST edit it with your credentials"
else
    ok "Email Sail .env already exists"
fi

if [[ ! -f "$YESHUA_DIR/.env" ]]; then
    cp "$YESHUA_DIR/.env.example" "$YESHUA_DIR/.env" 2>/dev/null || warn "No .env.example for Yeshua Architect"
else
    ok "Yeshua Architect .env already exists"
fi

# ── Caddy config ───────────────────────────────────────────────
info "Configuring Caddy..."

cat > "$EMAIL_SAIL_DIR/Caddyfile" << EOF
# Email Sail Agent
$EMAIL_SAIL_DOMAIN {
    reverse_proxy email-sail:8090
}

# Yeshua Architect Platform
$YESHUA_DOMAIN {
    reverse_proxy yeshua-architect:8080
}
EOF

ok "Caddyfile configured for both domains"

# ── Docker Compose ─────────────────────────────────────────────
echo ""
info "Building and starting services..."

cd "$EMAIL_SAIL_DIR"

# Create a combined docker-compose that runs both apps
cat > docker-compose.prod.yml << 'COMPOSE'
version: "3.8"

services:
  email-sail:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: email-sail-agent
    expose:
      - "8090"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    environment:
      - APP_HOST=0.0.0.0
      - APP_PORT=8090
      - APP_DEBUG=false
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8090/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  yeshua-architect:
    build:
      context: ../yeshua-architect-platform
      dockerfile: Dockerfile
    container_name: yeshua-architect-platform
    expose:
      - "8080"
    volumes:
      - ./data:/app/data
      - ./.env:/app/.env:ro
    environment:
      - APP_HOST=0.0.0.0
      - APP_PORT=8080
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  caddy:
    image: caddy:2-alpine
    container_name: caddy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      email-sail:
        condition: service_healthy
      yeshua-architect:
        condition: service_healthy
    restart: unless-stopped

volumes:
  caddy_data:
  caddy_config:
COMPOSE

ok "Production docker-compose.yml created"

# ── Start ──────────────────────────────────────────────────────
echo ""
info "Starting all services..."

docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "======================================"
echo "⛵ Deployment Complete!"
echo "======================================"
echo ""
echo "Services:"
echo "  Email Sail Agent:     https://$EMAIL_SAIL_DOMAIN"
echo "  Yeshua Architect:     https://$YESHUA_DOMAIN"
echo ""
echo "⚠️  IMPORTANT: Edit your .env files with real credentials:"
echo "    nano $EMAIL_SAIL_DIR/.env"
echo ""
echo "Then restart:"
echo "    cd $EMAIL_SAIL_DIR && docker compose -f docker-compose.prod.yml restart"
echo ""
echo "View logs:"
echo "    docker compose -f docker-compose.prod.yml logs -f"
echo ""
