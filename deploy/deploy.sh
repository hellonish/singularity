#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# Singularity — first-time deployment script for AWS EC2 (Ubuntu 24.04)
# Run on the server: bash deploy/deploy.sh
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Preflight checks ─────────────────────────────────────────────────────────
info "Running preflight checks..."

[ -f .env ] || error ".env file not found. Copy .env.production to .env and fill in values."
grep -q 'YOUR_DOMAIN' .env 2>/dev/null && error "Replace YOUR_DOMAIN in .env with your actual domain."
grep -qE '^POSTGRES_PASSWORD=\S' .env || error "POSTGRES_PASSWORD must be set in .env."
grep -qE '^JWT_SECRET=\S' .env || error "JWT_SECRET must be set in .env."
grep -qE '^NEXTAUTH_SECRET=\S' .env || error "NEXTAUTH_SECRET must be set in .env."
grep -qE '^NEXTAUTH_URL=\S' .env || error "NEXTAUTH_URL must be set in .env."
grep -qE '^GROK_API_KEY=\S' .env || warn "GROK_API_KEY not set — you need at least one LLM provider key."

info "All checks passed."

# ── Install Docker if missing ────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
    info "Installing Docker..."
    curl -fsSL https://get.docker.com | bash
    sudo usermod -aG docker "$USER"
    info "Docker installed. You may need to log out and back in for group changes."
    info "Then re-run this script."
    exit 0
fi

# ── Install docker-compose plugin if missing ─────────────────────────────────
if ! docker compose version &>/dev/null; then
    info "Installing Docker Compose plugin..."
    sudo apt-get update -qq
    sudo apt-get install -y -qq docker-compose-plugin
fi

# ── Add swap for t3.micro (1GB RAM) ─────────────────────────────────────────
if [ "$(free -m | awk '/^Swap:/{print $2}')" -lt 1000 ]; then
    info "Adding 2GB swap file (needed for t3.micro)..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    sudo sysctl vm.swappiness=10
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf
    info "Swap configured."
fi

# ── Configure firewall ───────────────────────────────────────────────────────
info "Configuring firewall..."
sudo ufw --force enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
info "Firewall configured (22, 80, 443 open)."

# ── Build and start ──────────────────────────────────────────────────────────
info "Building containers (this takes a few minutes on first run)..."
docker compose -f docker-compose.prod.yml build

info "Starting services..."
docker compose -f docker-compose.prod.yml up -d

# ── Wait for health checks ──────────────────────────────────────────────────
info "Waiting for services to become healthy..."
sleep 15

if docker compose -f docker-compose.prod.yml ps | grep -q "unhealthy"; then
    error "Some services are unhealthy. Check: docker compose -f docker-compose.prod.yml ps"
fi

info "Running database migrations..."
docker compose -f docker-compose.prod.yml exec api alembic upgrade head || \
    warn "Migration failed or alembic not configured. Check manually."

# ── Done ─────────────────────────────────────────────────────────────────────
DOMAIN=$(grep -E '^DOMAIN=' .env | cut -d= -f2)
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
info "Deployment complete!"
info "App: https://${DOMAIN}"
info ""
info "Useful commands:"
info "  View logs:      docker compose -f docker-compose.prod.yml logs -f"
info "  Restart:        docker compose -f docker-compose.prod.yml restart"
info "  Stop:           docker compose -f docker-compose.prod.yml down"
info "  Update & redeploy:"
info "    git pull && docker compose -f docker-compose.prod.yml build"
info "    docker compose -f docker-compose.prod.yml up -d"
info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
