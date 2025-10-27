#!/bin/bash
################################################################################
# Script de Configuración: NFS File Server
# Descripción: Configura un servidor NFS en EC2 para compartir archivos
#              entre Web Server y Worker
# Autor: MISO4204 - Desarrollo en la Nube
# Uso: ./01-fileserver-setup.sh
################################################################################

set -e  # Salir si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_message() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

################################################################################
# VARIABLES A CONFIGURAR
################################################################################

# ⚠️ IMPORTANTE: Configurar estas variables antes de ejecutar el script
WEBSERVER_PRIVATE_IP=""    # Ejemplo: 172.31.10.100
WORKER_PRIVATE_IP=""       # Ejemplo: 172.31.10.101

################################################################################
# VALIDACIONES
################################################################################

print_message "================================"
print_message "NFS File Server Setup"
print_message "================================"
echo ""

# Validar que se configuraron las IPs
if [ -z "$WEBSERVER_PRIVATE_IP" ] || [ -z "$WORKER_PRIVATE_IP" ]; then
    print_error "Las IPs privadas no están configuradas"
    echo ""
    echo "Edita este script y configura las siguientes variables:"
    echo "  WEBSERVER_PRIVATE_IP=<ip-privada-web-server>"
    echo "  WORKER_PRIVATE_IP=<ip-privada-worker>"
    echo ""
    echo "Para obtener las IPs privadas:"
    echo "  AWS Console → EC2 → Instances → Seleccionar instancia → Ver 'Private IPv4 addresses'"
    exit 1
fi

# Validar formato de IP (básico)
if ! [[ $WEBSERVER_PRIVATE_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    print_error "WEBSERVER_PRIVATE_IP no tiene formato válido: $WEBSERVER_PRIVATE_IP"
    exit 1
fi

if ! [[ $WORKER_PRIVATE_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    print_error "WORKER_PRIVATE_IP no tiene formato válido: $WORKER_PRIVATE_IP"
    exit 1
fi

print_message "Configuración:"
echo "  Web Server IP: $WEBSERVER_PRIVATE_IP"
echo "  Worker IP: $WORKER_PRIVATE_IP"
echo ""

################################################################################
# INSTALACIÓN
################################################################################

# 1. Actualizar sistema
print_message "[1/6] Actualizando sistema operativo..."
sudo apt update -qq
sudo DEBIAN_FRONTEND=noninteractive apt upgrade -yq
print_message "Sistema actualizado ✓"
echo ""

# 2. Instalar NFS Server
print_message "[2/6] Instalando NFS Server..."
sudo DEBIAN_FRONTEND=noninteractive apt install -yq nfs-kernel-server
print_message "NFS Server instalado ✓"
echo ""

# 3. Crear estructura de directorios
print_message "[3/6] Creando estructura de directorios..."
sudo mkdir -p /shared/media/uploads
sudo mkdir -p /shared/media/processed
print_message "Directorios creados:"
echo "  /shared/media/uploads"
echo "  /shared/media/processed"
echo ""

# 4. Configurar permisos
print_message "[4/6] Configurando permisos..."
sudo chown -R nobody:nogroup /shared/media
sudo chmod -R 777 /shared/media
print_message "Permisos configurados ✓"
echo ""

# 5. Configurar exports de NFS
print_message "[5/6] Configurando NFS exports..."

# Backup del archivo original si existe
if [ -f /etc/exports ]; then
    sudo cp /etc/exports /etc/exports.backup.$(date +%Y%m%d_%H%M%S)
fi

# Crear configuración de exports
sudo bash -c "cat > /etc/exports <<EOF
# NFS exports for ANB Rising Stars Showcase
# Configured on: $(date)

# Web Server access
/shared/media ${WEBSERVER_PRIVATE_IP}/32(rw,sync,no_subtree_check,no_root_squash)

# Worker access
/shared/media ${WORKER_PRIVATE_IP}/32(rw,sync,no_subtree_check,no_root_squash)
EOF"

print_message "Archivo /etc/exports configurado ✓"
echo ""

# 6. Aplicar configuración y iniciar servicios
print_message "[6/6] Iniciando servicios NFS..."
sudo exportfs -ra
sudo systemctl restart nfs-kernel-server
sudo systemctl enable nfs-kernel-server
print_message "Servicios NFS iniciados ✓"
echo ""

################################################################################
# VERIFICACIÓN
################################################################################

print_message "================================"
print_message "Verificación de Instalación"
print_message "================================"
echo ""

# Verificar estado del servicio
if sudo systemctl is-active --quiet nfs-kernel-server; then
    print_message "✓ NFS Server está activo y corriendo"
else
    print_error "✗ NFS Server NO está corriendo"
    exit 1
fi

# Verificar exports
print_message "Exports configurados:"
sudo exportfs -v
echo ""

# Verificar directorios
print_message "Estructura de directorios:"
tree -L 3 /shared/ 2>/dev/null || ls -lR /shared/
echo ""

################################################################################
# INFORMACIÓN FINAL
################################################################################

print_message "================================"
print_message "✅ Instalación Completada"
print_message "================================"
echo ""
echo "El NFS File Server está listo y compartiendo:"
echo "  📁 Directorio: /shared/media"
echo ""
echo "Clientes autorizados:"
echo "  🖥️  Web Server: ${WEBSERVER_PRIVATE_IP}"
echo "  ⚙️  Worker: ${WORKER_PRIVATE_IP}"
echo ""
echo "Permisos configurados:"
echo "  - Read/Write (rw)"
echo "  - Sync writes (sync)"
echo "  - No root squash (no_root_squash)"
echo ""
print_warning "Próximos pasos:"
echo "  1. Configurar Web Server (usar script 02-webserver-setup.sh)"
echo "  2. Configurar Worker (usar script 03-worker-setup.sh)"
echo ""
echo "Para verificar que los clientes pueden conectarse:"
echo "  showmount -e $(hostname -I | awk '{print $1}')"
echo ""
print_message "¡File Server configurado exitosamente! 🎉"
