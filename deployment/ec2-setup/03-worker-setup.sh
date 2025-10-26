#!/bin/bash
################################################################################
# Script de Configuración: Worker (Celery + FFmpeg)
# Descripción: Configura el worker de Celery para procesamiento de videos
# Autor: MISO4204 - Desarrollo en la Nube
# Uso: ./03-worker-setup.sh
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
WEBSERVER_PRIVATE_IP=""            # Ejemplo: 172.31.10.100 (para Redis)
RDS_ENDPOINT=""                    # Ejemplo: anb-db.xxxxx.us-east-1.rds.amazonaws.com
RDS_PASSWORD=""                    # Password del RDS
SECRET_KEY=""                      # MISMO secret key del Web Server
GITHUB_REPO="https://github.com/bendeckdavid/MISO4204-Desarrollo_Nube.git"
GITHUB_BRANCH="feature/Implement-aws-infra"  # Rama con cambios para AWS

################################################################################
# VALIDACIONES
################################################################################

print_message "================================"
print_message "Worker Setup"
print_message "Celery + FFmpeg"
print_message "================================"
echo ""

# Validar variables
if [ -z "$FILESERVER_PRIVATE_IP" ]; then
    print_error "FILESERVER_PRIVATE_IP no está configurada"
    exit 1
fi

if [ -z "$WEBSERVER_PRIVATE_IP" ]; then
    print_error "WEBSERVER_PRIVATE_IP no está configurada"
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
    print_error "SECRET_KEY no está configurado"
    echo "Usa el mismo SECRET_KEY del Web Server"
    exit 1
fi

print_info "Configuración:"
echo "  File Server: $FILESERVER_PRIVATE_IP"
echo "  Web Server (Redis): $WEBSERVER_PRIVATE_IP"
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
print_message "[1/9] Actualizando sistema operativo..."
sudo apt update -qq
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -yq
print_message "Sistema actualizado ✓"
echo ""

# 2. Instalar dependencias
print_message "[2/9] Instalando dependencias del sistema..."
sudo DEBIAN_FRONTEND=noninteractive apt install -yq \
    python3.11 \
    python3.11-venv \
    python3-pip \
    nfs-common \
    ffmpeg \
    git \
    curl \
    wget \
    tree \
    htop \
    redis-tools \
    postgresql-client

print_message "Dependencias instaladas ✓"
echo ""

# 3. Verificar FFmpeg
print_message "[3/9] Verificando FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -n1)
    print_message "FFmpeg instalado: $FFMPEG_VERSION ✓"
else
    print_error "FFmpeg no está instalado correctamente"
    exit 1
fi
echo ""

# 4. Preparar directorio para NFS (montar más tarde)
print_message "[4/9] Preparando directorio para NFS..."
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

# 5. Crear usuario
print_message "[5/9] Creando usuario appuser..."
if ! id -u appuser > /dev/null 2>&1; then
    sudo useradd -m -s /bin/bash appuser
    print_message "Usuario appuser creado ✓"
else
    print_info "Usuario appuser ya existe"
fi
echo ""

# 6. Clonar repositorio
print_message "[6/9] Clonando repositorio desde GitHub..."

if sudo test -d "/home/appuser/MISO4204-Desarrollo_Nube"; then
    print_info "Repositorio ya existe, actualizando..."
    sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && git fetch origin && git checkout $GITHUB_BRANCH && git pull origin $GITHUB_BRANCH"
else
    sudo -u appuser bash -c "cd /home/appuser && git clone -b $GITHUB_BRANCH $GITHUB_REPO"
fi

print_message "Repositorio clonado/actualizado ✓"
echo ""

# 7. Configurar entorno Python
print_message "[7/9] Configurando entorno Python..."

print_info "Creando entorno virtual..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && python3.11 -m venv .venv"

print_info "Actualizando pip..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/pip install --upgrade pip -q"

print_info "Instalando poetry..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/pip install poetry -q"

print_info "Configurando poetry..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/poetry config virtualenvs.create false"

print_info "Regenerando poetry.lock..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/poetry lock --no-update"

print_info "Instalando dependencias (esto puede tomar varios minutos)..."
sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && .venv/bin/poetry install --only main"

print_message "Entorno Python configurado ✓"
echo ""

# 8. Crear archivo .env
print_message "[8/9] Creando archivo de configuración .env..."
sudo -u appuser bash -c "cat > /home/appuser/MISO4204-Desarrollo_Nube/.env <<EOF
# Database Configuration
DATABASE_URL=postgresql://fastapi_user:${RDS_PASSWORD}@${RDS_ENDPOINT}:5432/fastapi_db

# Security
SECRET_KEY=${SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Celery / Redis (apuntando al Web Server)
CELERY_BROKER_URL=redis://${WEBSERVER_PRIVATE_IP}:6379/0
CELERY_RESULT_BACKEND=redis://${WEBSERVER_PRIVATE_IP}:6379/0

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

# 9. Configurar servicio systemd para Celery
print_message "[9/9] Configurando servicio systemd para Celery..."
sudo bash -c 'cat > /etc/systemd/system/celery.service <<EOF
[Unit]
Description=Celery Worker for Video Processing
After=network.target

[Service]
Type=forking
User=appuser
Group=appuser
WorkingDirectory=/home/appuser/MISO4204-Desarrollo_Nube
Environment="PATH=/home/appuser/MISO4204-Desarrollo_Nube/.venv/bin"
EnvironmentFile=/home/appuser/MISO4204-Desarrollo_Nube/.env
ExecStart=/home/appuser/MISO4204-Desarrollo_Nube/.venv/bin/celery -A app.worker.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --max-tasks-per-child=50 \
    --time-limit=600 \
    --soft-time-limit=540 \
    --logfile=/var/log/celery.log \
    --pidfile=/var/run/celery.pid
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

# Crear archivo de log
sudo touch /var/log/celery.log
sudo chown appuser:appuser /var/log/celery.log

print_message "Servicio Celery configurado ✓"
echo ""

# Iniciar servicio
print_message "Iniciando servicio Celery..."
sudo systemctl daemon-reload
sudo systemctl enable celery
sudo systemctl start celery
sleep 5
print_message "Servicio Celery iniciado ✓"
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

# Verificar conectividad a Redis
print_info "2. Verificando conexión a Redis (Web Server)..."
if redis-cli -h ${WEBSERVER_PRIVATE_IP} ping &> /dev/null; then
    print_message "✓ Conectado a Redis en Web Server"
    redis-cli -h ${WEBSERVER_PRIVATE_IP} ping
else
    print_error "✗ No se puede conectar a Redis"
    echo "Verifica que:"
    echo "  1. Web Server está corriendo"
    echo "  2. Redis está configurado para escuchar en todas las interfaces"
    echo "  3. Security Group permite tráfico en puerto 6379"
fi
echo ""

# Verificar conectividad a RDS
print_info "3. Verificando conexión a PostgreSQL RDS..."
if PGPASSWORD=${RDS_PASSWORD} psql -h ${RDS_ENDPOINT} -U fastapi_user -d fastapi_db -c "SELECT version();" &> /dev/null; then
    print_message "✓ Conectado a PostgreSQL RDS"
else
    print_warning "⚠ No se puede conectar a RDS (puede ser normal si las tablas no están creadas)"
fi
echo ""

# Verificar FFmpeg
print_info "4. Verificando FFmpeg..."
if command -v ffmpeg &> /dev/null; then
    print_message "✓ FFmpeg disponible"
    ffmpeg -version | head -n1
else
    print_error "✗ FFmpeg no está disponible"
fi
echo ""

# Verificar Celery
print_info "5. Verificando Celery Worker..."
if sudo systemctl is-active --quiet celery; then
    print_message "✓ Celery está activo"
    sleep 2
    # Verificar que Celery puede ver las tareas
    if sudo -u appuser bash -c "cd /home/appuser/MISO4204-Desarrollo_Nube && source .venv/bin/activate && celery -A app.worker.celery_app inspect registered" &> /dev/null; then
        print_message "✓ Celery puede comunicarse con Redis"
    else
        print_warning "⚠ Celery está corriendo pero puede tener problemas de comunicación"
    fi
else
    print_error "✗ Celery no está corriendo"
    echo "Ver logs con: sudo journalctl -u celery -n 50"
fi
echo ""

################################################################################
# INFORMACIÓN FINAL
################################################################################

print_message "================================"
print_message "✅ Instalación Completada"
print_message "================================"
echo ""
echo "El Worker está configurado y corriendo con:"
echo "  ⚙️  Celery Worker (2 concurrent tasks)"
echo "  🎬 FFmpeg para procesamiento de video"
echo "  📦 Redis conectado a Web Server"
echo "  💾 PostgreSQL RDS"
echo "  📁 NFS montado en /app/media"
echo ""
print_info "Comandos útiles:"
echo "  # Ver logs de Celery"
echo "  sudo journalctl -u celery -f"
echo "  sudo tail -f /var/log/celery.log"
echo ""
echo "  # Ver tareas activas"
echo "  sudo -u appuser bash -c 'cd /home/appuser/MISO4204-Desarrollo_Nube && source .venv/bin/activate && celery -A app.worker.celery_app inspect active'"
echo ""
echo "  # Ver tareas registradas"
echo "  sudo -u appuser bash -c 'cd /home/appuser/MISO4204-Desarrollo_Nube && source .venv/bin/activate && celery -A app.worker.celery_app inspect registered'"
echo ""
echo "  # Reiniciar Celery"
echo "  sudo systemctl restart celery"
echo ""
echo "  # Ver estado del montaje NFS"
echo "  df -h | grep /app/media"
echo ""
print_info "Próximo paso:"
echo "  Prueba subir un video desde el Web Server y observa los logs aquí"
echo "  para ver el procesamiento en tiempo real."
echo ""
print_message "¡Worker configurado exitosamente! 🎉"
print_message "La arquitectura completa está lista para procesar videos! 🚀"
