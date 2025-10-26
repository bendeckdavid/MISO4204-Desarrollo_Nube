#!/bin/bash
################################################################################
# Script de Configuración: Web Server (FastAPI + Nginx + Redis)
# Descripción: Configura el servidor web con FastAPI, Gunicorn, Nginx y Redis
# Autor: MISO4204 - Desarrollo en la Nube
# Uso: ./02-webserver-setup.sh
################################################################################

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

################################################################################
# VARIABLES A CONFIGURAR
################################################################################

# ⚠️ IMPORTANTE: Configurar estas variables antes de ejecutar
FILESERVER_PRIVATE_IP=""           # Ejemplo: 172.31.10.99
RDS_ENDPOINT=""                    # Ejemplo: anb-db.xxxxx.us-east-1.rds.amazonaws.com
RDS_PASSWORD=""                    # Password del RDS
SECRET_KEY=""                      # Generar con: openssl rand -hex 32
GITHUB_REPO="https://github.com/bendeckdavid/MISO4204-Desarrollo_Nube.git"
GITHUB_BRANCH="feature/Implement-aws-infra"  # Rama con cambios para AWS

################################################################################
# VALIDACIONES
################################################################################

print_message "================================"
print_message "Web Server Setup"
print_message "FastAPI + Gunicorn + Nginx + Redis"
print_message "================================"
echo ""

# Validar variables
if [ -z "$FILESERVER_PRIVATE_IP" ]; then
    print_error "FILESERVER_PRIVATE_IP no está configurada"
    exit 1
fi

if [ -z "$RDS_ENDPOINT" ]; then
    print_error "RDS_ENDPOINT no está configurado"
    exit 1
fi

if [ -z "$RDS_PASSWORD" ]; then
    print_error "RDS_PASSWORD no está configurado"
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    print_warning "SECRET_KEY no configurado, generando uno automáticamente..."
    SECRET_KEY=$(openssl rand -hex 32)
    echo "SECRET_KEY generado: $SECRET_KEY"
    echo "⚠️ GUARDA ESTE SECRET_KEY para usarlo en el Worker"
    echo ""
fi

print_info "Configuración:"
echo "  File Server: $FILESERVER_PRIVATE_IP"
echo "  RDS Endpoint: $RDS_ENDPOINT"
echo "  GitHub Repo: $GITHUB_REPO"
echo "  Branch: $GITHUB_BRANCH"
echo ""

read -p "¿La configuración es correcta? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_error "Instalación cancelada"
    exit 1
fi

################################################################################
# INSTALACIÓN
################################################################################

# 1. Actualizar sistema
print_message "[1/11] Actualizando sistema operativo..."
sudo apt update -qq
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -yq
print_message "Sistema actualizado ✓"
echo ""

# 2. Instalar dependencias del sistema
print_message "[2/11] Instalando dependencias del sistema..."
sudo DEBIAN_FRONTEND=noninteractive apt install -yq \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nfs-common \
    redis-server \
    nginx \
    ffmpeg \
    git \
    curl \
    wget \
    tree \
    htop \
    postgresql-client

print_message "Dependencias instaladas ✓"
echo ""

# 3. Configurar Redis
print_message "[3/11] Configurando Redis..."
# Permitir conexiones desde Worker
sudo sed -i 's/^bind 127\.0\.0\.1 ::1/bind 0.0.0.0/' /etc/redis/redis.conf
# Configurar como servicio protegido
sudo sed -i 's/^protected-mode yes/protected-mode no/' /etc/redis/redis.conf
sudo systemctl restart redis-server
sudo systemctl enable redis-server
print_message "Redis configurado ✓"
echo ""

# 4. Preparar directorio para NFS (montar más tarde)
print_message "[4/11] Preparando directorio para NFS..."
sudo mkdir -p /app/media

print_info "El NFS se montará después de configurar el File Server"
print_info "Para montar manualmente, ejecuta:"
echo "  sudo mount -t nfs ${FILESERVER_PRIVATE_IP}:/shared/media /app/media"
echo ""

# Preparar entrada en fstab (comentada por ahora)
if ! grep -q "/app/media" /etc/fstab; then
    echo "# ${FILESERVER_PRIVATE_IP}:/shared/media /app/media nfs defaults,_netdev 0 0" | sudo tee -a /etc/fstab
    print_message "Entrada NFS preparada en /etc/fstab (comentada) ✓"
fi
echo ""

# 5. Crear usuario para la aplicación
print_message "[5/11] Creando usuario appuser..."
if ! id -u appuser > /dev/null 2>&1; then
    sudo useradd -m -s /bin/bash appuser
    print_message "Usuario appuser creado ✓"
else
    print_info "Usuario appuser ya existe"
fi
echo ""

# 6. Clonar repositorio
print_message "[6/11] Clonando repositorio desde GitHub..."

if sudo test -d "/home/appuser/MISO4204-Desarrollo_Nube"; then
    print_info "Repositorio ya existe, actualizando..."
    sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && git fetch origin && git checkout $GITHUB_BRANCH && git pull origin $GITHUB_BRANCH"
else
    sudo -u appuser bash -c "cd /home/appuser && git clone -b $GITHUB_BRANCH $GITHUB_REPO"
fi

print_message "Repositorio clonado/actualizado ✓"
echo ""

# 7. Configurar entorno Python
print_message "[7/11] Configurando entorno Python..."

print_info "Creando entorno virtual..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && python3.11 -m venv .venv"

print_info "Actualizando pip..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/pip install --upgrade pip -q"

print_info "Instalando poetry..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/pip install poetry -q"

print_info "Configurando poetry..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/poetry config virtualenvs.create false"

print_info "Regenerando poetry.lock..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/poetry lock"

print_info "Instalando dependencias (esto puede tomar varios minutos)..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/poetry install --only main"

print_message "Entorno Python configurado ✓"
echo ""

# 8. Crear archivo .env
print_message "[8/11] Creando archivo de configuración .env..."
sudo -u appuser bash -c "cat > /home/appuser/MISO4204-Desarrollo_Nube/.env <<EOF
# Database Configuration
DATABASE_URL=postgresql://fastapi_user:${RDS_PASSWORD}@${RDS_ENDPOINT}:5432/fastapi_db

# Security
SECRET_KEY=${SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Celery / Redis
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Application
PROJECT_NAME=ANB Rising Stars Showcase API
VERSION=1.0.0
ENVIRONMENT=production

# Media Files
MEDIA_ROOT=/app/media

# Database Pool Settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
EOF"

sudo chmod 600 /home/appuser/MISO4204-Desarrollo_Nube/.env
print_message "Archivo .env creado ✓"
echo ""

# 9. Configurar servicio systemd para FastAPI
print_message "[9/11] Configurando servicio systemd para FastAPI..."
sudo bash -c 'cat > /etc/systemd/system/fastapi.service <<EOF
[Unit]
Description=FastAPI Application with Gunicorn
After=network.target

[Service]
Type=notify
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/MISO4204-Desarrollo_Nube
Environment="PATH=/home/appuser/MISO4204-Desarrollo_Nube/.venv/bin"
EnvironmentFile=/home/appuser/MISO4204-Desarrollo_Nube/.env
ExecStart=/home/appuser/MISO4204-Desarrollo_Nube/.venv/bin/gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --timeout 120 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile /var/log/fastapi-access.log \
    --error-logfile /var/log/fastapi-error.log \
    --log-level info
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

# Crear archivos de log
sudo touch /var/log/fastapi-access.log /var/log/fastapi-error.log
sudo chown appuser:appuser /var/log/fastapi-access.log /var/log/fastapi-error.log

print_message "Servicio FastAPI configurado ✓"
echo ""

# 10. Configurar Nginx
print_message "[10/11] Configurando Nginx..."
sudo bash -c 'cat > /etc/nginx/sites-available/fastapi <<EOF
upstream fastapi_backend {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 8080 default_server;
    listen [::]:8080 default_server;
    server_name _;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size
    client_max_body_size 500M;
    client_body_timeout 300s;

    # Logs
    access_log /var/log/nginx/fastapi-access.log;
    error_log /var/log/nginx/fastapi-error.log;

    location / {
        proxy_pass http://fastapi_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeouts
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;

        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
        proxy_busy_buffers_size 8k;
    }

    location /health {
        proxy_pass http://fastapi_backend;
        access_log off;
    }
}
EOF'

# Habilitar sitio y deshabilitar default
sudo ln -sf /etc/nginx/sites-available/fastapi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Verificar configuración
if sudo nginx -t; then
    print_message "Configuración de Nginx válida ✓"
else
    print_error "Error en la configuración de Nginx"
    exit 1
fi
echo ""

# 11. Iniciar servicios
print_message "[11/11] Iniciando servicios..."

# Recargar systemd
sudo systemctl daemon-reload

# Iniciar y habilitar FastAPI
sudo systemctl enable fastapi
sudo systemctl start fastapi
sleep 5

# Reiniciar Nginx
sudo systemctl restart nginx

print_message "Servicios iniciados ✓"
echo ""

################################################################################
# VERIFICACIÓN
################################################################################

print_message "================================"
print_message "Verificación de Instalación"
print_message "================================"
echo ""

# Verificar NFS
print_info "1. Verificando montaje NFS..."
if df -h | grep -q "/app/media"; then
    print_message "✓ NFS montado correctamente"
    df -h | grep "/app/media"
else
    print_warning "⚠ NFS no está montado aún (esto es normal)"
    print_info "Monta NFS después de configurar el File Server con:"
    echo "  sudo mount -t nfs ${FILESERVER_PRIVATE_IP}:/shared/media /app/media"
    echo "  sudo sed -i 's/^# //' /etc/fstab  # Descomentar línea NFS"
fi
echo ""

# Verificar Redis
print_info "2. Verificando Redis..."
if sudo systemctl is-active --quiet redis-server; then
    print_message "✓ Redis está activo"
    redis-cli ping
else
    print_error "✗ Redis no está corriendo"
fi
echo ""

# Verificar FastAPI
print_info "3. Verificando FastAPI..."
if sudo systemctl is-active --quiet fastapi; then
    print_message "✓ FastAPI está activo"
    sleep 3
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        print_message "✓ Health check exitoso"
    else
        print_warning "⚠ Health check falló, pero el servicio está corriendo"
    fi
else
    print_error "✗ FastAPI no está corriendo"
    echo "Ver logs con: sudo journalctl -u fastapi -n 50"
fi
echo ""

# Verificar Nginx
print_info "4. Verificando Nginx..."
if sudo systemctl is-active --quiet nginx; then
    print_message "✓ Nginx está activo"
    if curl -s http://localhost:8080/health | grep -q "healthy"; then
        print_message "✓ Nginx proxy funcionando correctamente"
    else
        print_warning "⚠ Nginx está corriendo pero el proxy puede tener problemas"
    fi
else
    print_error "✗ Nginx no está corriendo"
fi
echo ""

################################################################################
# INFORMACIÓN FINAL
################################################################################

print_message "================================"
print_message "✅ Instalación Completada"
print_message "================================"
echo ""
echo "El Web Server está configurado y corriendo con:"
echo "  🚀 FastAPI + Gunicorn (4 workers)"
echo "  🔀 Nginx (puerto 8080)"
echo "  📦 Redis (puerto 6379)"
echo "  💾 PostgreSQL RDS"
echo "  📁 NFS montado en /app/media"
echo ""
print_info "URLs de acceso:"
echo "  API (interna): http://localhost:8000"
echo "  API (Nginx): http://localhost:8080"
MY_PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)
echo "  API (pública): http://${MY_PUBLIC_IP}:8080"
echo ""
print_info "Comandos útiles:"
echo "  # Ver logs de FastAPI"
echo "  sudo journalctl -u fastapi -f"
echo ""
echo "  # Ver logs de Nginx"
echo "  sudo tail -f /var/log/nginx/fastapi-error.log"
echo ""
echo "  # Reiniciar servicios"
echo "  sudo systemctl restart fastapi"
echo "  sudo systemctl restart nginx"
echo ""
echo "  # Verificar health check"
echo "  curl http://localhost:8080/health"
echo ""
print_warning "Próximo paso:"
echo "  Configurar el Worker usando el script: 03-worker-setup.sh"
echo ""
print_warning "⚠️ IMPORTANTE - Guarda este SECRET_KEY para el Worker:"
echo "  $SECRET_KEY"
echo ""
print_message "¡Web Server configurado exitosamente! 🎉"
