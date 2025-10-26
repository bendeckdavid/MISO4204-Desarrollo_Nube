# Guía de Despliegue en AWS - Entrega 2

Guía paso a paso para desplegar la aplicación ANB Rising Stars Showcase en AWS, creando y configurando cada componente de forma incremental.

## Índice
- [Arquitectura Objetivo](#arquitectura-objetivo)
- [Prerrequisitos](#prerrequisitos)
- [Paso 1: Preparación Inicial](#paso-1-preparación-inicial)
- [Paso 2: File Server (NFS)](#paso-2-file-server-nfs)
- [Paso 3: Amazon RDS](#paso-3-amazon-rds)
- [Paso 4: Web Server](#paso-4-web-server)
- [Paso 5: Worker](#paso-5-worker)
- [Paso 6: Verificación Final](#paso-6-verificación-final)
- [Troubleshooting](#troubleshooting)

---

## Arquitectura Objetivo

```
                                    ┌─────────────────┐
                                    │   Internet      │
                                    └────────┬────────┘
                                             │
                                             │ HTTP:8080
                                             ▼
                        ┌────────────────────────────────────┐
                        │      EC2 Web Server (t3.small)     │
                        │  - FastAPI + Gunicorn (4 workers)  │
                        │  - Nginx (Reverse Proxy)           │
                        │  - Redis (Broker)                  │
                        │  - NFS Client (mount /app/media)   │
                        └───────────┬────────────────────────┘
                                    │
                ┌───────────────────┼───────────────────┐
                │                   │                   │
                ▼                   ▼                   ▼
    ┌───────────────────┐  ┌──────────────────┐  ┌──────────────────┐
    │ EC2 File Server   │  │  Amazon RDS      │  │  EC2 Worker      │
    │   (t3.small)      │  │  (PostgreSQL)    │  │  (t3.small)      │
    │ - NFS Server      │  │                  │  │ - Celery Worker  │
    │ - /shared/media   │  │                  │  │ - FFmpeg         │
    │   ├─ uploads/     │  │                  │  │ - NFS Client     │
    │   └─ processed/   │  │                  │  │                  │
    └───────────────────┘  └──────────────────┘  └──────────────────┘
```

### Componentes
- **3 Instancias EC2** (t3.small: 2 vCPU, 2 GiB RAM, 50 GiB storage)
- **Amazon RDS**: PostgreSQL 16
- **NFS**: Sistema de archivos compartido

**Tiempo total estimado: 60-90 minutos**

---

## Prerrequisitos

### En tu máquina local
- Cuenta de AWS con créditos educativos
- SSH client instalado
- Git con el repositorio actualizado

### Configuración Local Inicial

**ANTES de empezar con AWS**, prepara tu entorno local:

1. **Clonar/actualizar el repositorio**:
   ```bash
   # Si no lo tienes, clonarlo
   git clone https://github.com/tu-usuario/MISO4204-Desarrollo_Nube.git
   cd MISO4204-Desarrollo_Nube

   # Si ya lo tienes, actualizarlo
   git pull origin main
   ```

2. **Verificar que tienes los scripts**:
   ```bash
   ls -lh deployment/ec2-setup/
   # Deberías ver:
   # 01-fileserver-setup.sh
   # 02-webserver-setup.sh
   # 03-worker-setup.sh
   ```

3. **Anotar la ruta completa del proyecto**:
   ```bash
   pwd
   # Ejemplo: /home/usuario/MISO4204-Desarrollo_Nube
   ```
   📝 **Guarda esta ruta**, la usarás para los comandos `scp`

### Preparar antes de empezar AWS

1. **Obtener tu IP pública** (para SSH):
   ```bash
   curl https://checkip.amazonaws.com
   ```
   Anota tu IP: `_______________`

2. **Generar SECRET_KEY**:
   ```bash
   openssl rand -hex 32
   ```
   Anota tu SECRET_KEY: `_______________`

3. **Crear archivo local para anotar información**:
   ```txt
   # aws-info.txt (NO SUBIR A GIT)

   ## Rutas Locales
   Proyecto: /home/juan-perdomo/Documentos/workspaces/miso/MISO4204-Desarrollo_Nube
   Key Pair: /home/juan-perdomo/Downloads/anb-key-pair.pem

   ## Información AWS
   Mi IP Pública: _______________
   SECRET_KEY: _______________
   GitHub Repo: https://github.com/_______________

   VPC ID: _______________
   Subnet ID: _______________

   File Server Public IP: _______________
   File Server Private IP: _______________

   Web Server Public IP: _______________
   Web Server Private IP: _______________

   Worker Public IP: _______________
   Worker Private IP: _______________

   RDS Endpoint: _______________
   RDS Password: _______________
   ```

   📝 **Ejemplo de comandos con rutas reales**:
   ```bash
   # Copiar script al File Server
   cd /home/juan-perdomo/Documentos/workspaces/miso/MISO4204-Desarrollo_Nube
   scp -i ~/Downloads/anb-key-pair.pem \
       deployment/ec2-setup/01-fileserver-setup.sh \
       ubuntu@54.165.186.145:~
   ```

---

## Paso 1: Preparación Inicial

### 1.1 Crear Key Pair

1. Ir a **AWS Console** → **EC2** → **Key Pairs** → **Create key pair**
2. Configurar:
   - **Name**: `anb-key-pair`
   - **Key pair type**: RSA
   - **File format**: `.pem`
3. Descargar `anb-key-pair.pem`
4. Dar permisos:
   ```bash
   chmod 400 anb-key-pair.pem
   ```

### 1.2 Crear VPC y Subnets

Vamos a crear una VPC dedicada para el proyecto con sus subnets públicas.

#### 1.2.1 Crear VPC

1. Ir a **VPC Dashboard** → **Your VPCs** → **Create VPC**
2. Configurar:
   - **VPC settings**: `VPC only`
   - **Name tag**: `ANB-VPC`
   - **IPv4 CIDR block**: `10.0.0.0/16`
   - **IPv6 CIDR block**: `No IPv6 CIDR block`
   - **Tenancy**: `Default`
3. Clic en **Create VPC**
4. 📝 **Anotar VPC ID**: `vpc-xxxxx`

#### 1.2.2 Crear Internet Gateway

1. **VPC** → **Internet Gateways** → **Create internet gateway**
2. Configurar:
   - **Name tag**: `ANB-IGW`
3. Clic en **Create internet gateway**
4. Seleccionar el IGW recién creado → **Actions** → **Attach to VPC**
5. Seleccionar `ANB-VPC` → **Attach internet gateway**

#### 1.2.3 Crear Subnets Públicas

RDS requiere al menos 2 subnets en diferentes zonas de disponibilidad. Vamos a crear 2:

**Subnet 1:**
1. **VPC** → **Subnets** → **Create subnet**
2. Configurar:
   - **VPC ID**: Seleccionar `ANB-VPC`
   - **Subnet name**: `ANB-Public-Subnet-1`
   - **Availability Zone**: Seleccionar la primera disponible (ej: `us-east-1a`)
   - **IPv4 CIDR block**: `10.0.1.0/24`
3. Clic en **Create subnet**
4. 📝 **Anotar Subnet ID**: `subnet-xxxxx`

**Subnet 2 (para RDS):**
1. **VPC** → **Subnets** → **Create subnet**
2. Configurar:
   - **VPC ID**: Seleccionar `ANB-VPC`
   - **Subnet name**: `ANB-Public-Subnet-2`
   - **Availability Zone**: Seleccionar **OTRA ZONA** diferente (ej: `us-east-1b`)
   - **IPv4 CIDR block**: `10.0.2.0/24`
3. Clic en **Create subnet**

#### 1.2.4 Crear Route Table y Asociarla

1. **VPC** → **Route Tables** → **Create route table**
2. Configurar:
   - **Name**: `ANB-Public-RT`
   - **VPC**: `ANB-VPC`
3. Clic en **Create route table**

4. Seleccionar `ANB-Public-RT` → **Routes** → **Edit routes**
5. **Add route**:
   - **Destination**: `0.0.0.0/0`
   - **Target**: `Internet Gateway` → Seleccionar `ANB-IGW`
6. **Save changes**

7. En la misma route table → **Subnet associations** → **Edit subnet associations**
8. Seleccionar **ambas subnets**: `ANB-Public-Subnet-1` y `ANB-Public-Subnet-2`
9. **Save associations**

#### 1.2.5 Habilitar Auto-assign Public IP

Hacer esto para **ambas subnets**:

**Para Subnet 1:**
1. **VPC** → **Subnets** → Seleccionar `ANB-Public-Subnet-1`
2. **Actions** → **Edit subnet settings**
3. ✅ Marcar **Enable auto-assign public IPv4 address**
4. **Save**

**Para Subnet 2:**
1. Seleccionar `ANB-Public-Subnet-2`
2. **Actions** → **Edit subnet settings**
3. ✅ Marcar **Enable auto-assign public IPv4 address**
4. **Save**

✅ **VPC configurada correctamente!**

**Resumen de la configuración:**
- VPC: `10.0.0.0/16`
- Subnet pública 1: `10.0.1.0/24` (AZ a)
- Subnet pública 2: `10.0.2.0/24` (AZ b)
- Internet Gateway: Asociado
- Route table: Configurada con ruta a internet
- Auto-assign public IP: Habilitado en ambas subnets

**Usarás estos valores en los siguientes pasos:**
- Al crear Security Groups: Seleccionar `ANB-VPC`
- Al lanzar EC2: Seleccionar `ANB-Public-Subnet-1`
- Al crear RDS: Usará ambas subnets automáticamente

---

## Paso 2: File Server (NFS)

**Tiempo estimado: 15 minutos**

### 2.1 Crear Security Group para File Server

1. Ir a **EC2** → **Security Groups** → **Create security group**
2. Configurar:
   - **Name**: `ANB-FileServer-SG`
   - **Description**: `Security group for NFS File Server`
   - **VPC**: Seleccionar `ANB-VPC` (la que creaste en el paso anterior)

3. **Inbound rules**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | SSH | 22 | Mi IP/32 | SSH access |
   | Custom TCP | 2049 | 0.0.0.0/0 | NFS (temporal - ajustaremos después) |

   ⚠️ **Nota**: Dejamos NFS abierto temporalmente. Lo restringiremos después de crear el Web Server y Worker.

4. **Outbound rules**: Dejar "All traffic" por defecto

5. Clic en **Create security group**

### 2.2 Lanzar EC2 para File Server

1. Ir a **EC2** → **Instances** → **Launch instances**

2. **Configuración**:
   - **Name**: `ANB-FileServer`
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance type**: `t3.small`
   - **Key pair**: `anb-key-pair`
   - **Network settings**:
     - **VPC**: Seleccionar `ANB-VPC`
     - **Subnet**: Seleccionar `ANB-Public-Subnet-1`
     - **Auto-assign public IP**: Enable (debería estar habilitado por defecto)
     - **Firewall (security groups)**: Select existing → `ANB-FileServer-SG`
   - **Storage**: 50 GiB gp3

3. Clic en **Launch instance**

4. Esperar ~2 minutos a que la instancia esté "Running"

5. **Anotar las IPs**:
   - Public IPv4: 54.165.186.145
   - Private IPv4: 10.0.1.75

### 2.3 Conectarse al File Server

```bash
ssh -i anb-key-pair.pem ubuntu@<FILE_SERVER_PUBLIC_IP>
```

Si te pide confirmación, escribe `yes`.

### 2.4 Nota Importante

⚠️ **NO CONFIGURES el File Server todavía**. Solo lo creamos para tener la instancia lista.

**Configuraremos el File Server después de crear y configurar el Web Server y Worker**, porque necesitamos sus IPs privadas para configurar las exportaciones NFS.

**El orden de configuración será**:
1. ✅ Crear File Server (acabas de hacerlo)
2. ⏭️ Crear RDS (siguiente paso)
3. ⏭️ Crear y configurar Web Server
4. ⏭️ Crear y configurar Worker
5. ⏭️ **Entonces configurar File Server** con las IPs del Web Server y Worker

---

## Paso 3: Amazon RDS

**Tiempo estimado: 20 minutos (incluye tiempo de espera)**

### 3.1 Crear Security Group para RDS

1. **EC2** → **Security Groups** → **Create security group**
2. Configurar:
   - **Name**: `ANB-RDS-SG`
   - **Description**: `Security group for PostgreSQL RDS`
   - **VPC**: Seleccionar `ANB-VPC`

3. **Inbound rules**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | PostgreSQL | 5432 | 0.0.0.0/0 | PostgreSQL (temporal) |

   ⚠️ **Nota**: Dejamos abierto temporalmente. Lo restringiremos después.

4. **Outbound rules**: All traffic (por defecto)

5. Clic en **Create security group**

### 3.2 Crear Instancia RDS

1. Ir a **RDS** → **Databases** → **Create database**

2. **Configuración básica**:
   - **Engine type**: PostgreSQL
   - **Version**: PostgreSQL 16.x (última disponible)
   - **Templates**: `Free tier` (o `Dev/Test`)

3. **Settings**:
   - **DB instance identifier**: `anb-postgres-db`
   - **Master username**: `fastapi_user`
   - **Master password**: **(crear una segura)**
   - **Confirm password**: **(repetir)**

   📝 **Anota el password**: `_______________`

4. **Instance configuration**:
   - **DB instance class**: `db.t3.micro` (o `db.t4g.micro`)

5. **Storage**:
   - **Storage type**: `gp3`
   - **Allocated storage**: `20 GiB`
   - ❌ **Desmarcar** "Enable storage autoscaling"

6. **Connectivity**:
   - **VPC**: Seleccionar `ANB-VPC`
   - **DB Subnet group**: `Create new DB subnet group` (se creará automáticamente con ambas subnets)
     - O si prefieres crearlo manualmente: **RDS** → **Subnet groups** → **Create DB subnet group**:
       - **Name**: `anb-db-subnet-group`
       - **Description**: `Subnet group for ANB project`
       - **VPC**: `ANB-VPC`
       - **Add subnets**: Seleccionar `ANB-Public-Subnet-1` (us-east-1a) y `ANB-Public-Subnet-2` (us-east-1b)
   - **Public access**: `No`
   - **VPC security group**: `Choose existing` → `ANB-RDS-SG`
   - **Availability Zone**: `No preference`

7. **Database authentication**:
   - `Password authentication`

8. **Additional configuration** (expandir):
   - **Initial database name**: `fastapi_db` ⚠️ **IMPORTANTE**
   - ❌ **Desmarcar** "Enable automated backups"
   - ❌ **Desmarcar** "Enable encryption" (opcional)

9. Clic en **Create database**

10. **Esperar ~10-15 minutos** mientras se crea

### 3.3 Obtener Endpoint de RDS

1. Una vez que el estado sea "Available", ir a la instancia `anb-postgres-db`
2. En la pestaña **Connectivity & security**, copiar el **Endpoint**
3. Ejemplo: `anb-postgres-db.xxxxxx.us-east-1.rds.amazonaws.com`
4. 📝 **Anotar el endpoint**: `_______________`

---

## Paso 4: Web Server

**Tiempo estimado: 25 minutos**

### 4.1 Crear Security Group para Web Server

1. **EC2** → **Security Groups** → **Create security group**
2. Configurar:
   - **Name**: `ANB-WebServer-SG`
   - **Description**: `Security group for Web Server`
   - **VPC**: Seleccionar `ANB-VPC`

3. **Inbound rules**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | Custom TCP | 8080 | 0.0.0.0/0 | HTTP API public |
   | SSH | 22 | Mi IP/32 | SSH access |
   | Custom TCP | 6379 | 0.0.0.0/0 | Redis (temporal) |

   ⚠️ **Nota**: Redis abierto temporalmente. Lo restringiremos después.

4. **Outbound rules**: All traffic (por defecto)

5. Clic en **Create security group**

### 4.2 Lanzar EC2 para Web Server

1. **EC2** → **Instances** → **Launch instances**

2. **Configuración**:
   - **Name**: `ANB-WebServer`
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance type**: `t3.small`
   - **Key pair**: `anb-key-pair`
   - **Network settings**:
     - **VPC**: `ANB-VPC`
     - **Subnet**: `ANB-Public-Subnet-1`
     - **Auto-assign public IP**: Enable
     - **Firewall (security groups)**: Select existing → `ANB-WebServer-SG`
   - **Storage**: 50 GiB gp3

3. Clic en **Launch instance**

4. Esperar a que esté "Running"

5. **📝 Anotar las IPs**:
   - Public IPv4: `_______________`
   - Private IPv4: `_______________`

### 4.3 Nota Importante

⚠️ **NO CONFIGURES el Web Server todavía**. Solo lo creamos para tener la instancia y su IP privada.

**Lo configuraremos en el Paso 5 después de configurar el File Server**, cuando tengamos el NFS listo.

---

## Paso 5: Configuración de Servicios

**Tiempo estimado: 60 minutos**

En este paso configuraremos todos los servicios en el orden correcto:
1. Crear instancia Worker
2. Actualizar Security Groups
3. Configurar File Server (NFS)
4. **Configurar Web Server** (ahora que NFS está listo)
5. **Configurar Worker**
6. Montar NFS en ambos servidores

### 5.1 Crear Security Group para Worker

1. **EC2** → **Security Groups** → **Create security group**
2. Configurar:
   - **Name**: `ANB-Worker-SG`
   - **Description**: `Security group for Celery Worker`
   - **VPC**: Seleccionar `ANB-VPC`

3. **Inbound rules**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | SSH | 22 | Mi IP/32 | SSH access |

4. **Outbound rules**: All traffic (por defecto)

5. Clic en **Create security group**

### 5.2 Lanzar EC2 para Worker

1. **EC2** → **Instances** → **Launch instances**

2. **Configuración**:
   - **Name**: `ANB-Worker`
   - **AMI**: Ubuntu Server 22.04 LTS (64-bit x86)
   - **Instance type**: `t3.small`
   - **Key pair**: `anb-key-pair`
   - **Network settings**:
     - **VPC**: `ANB-VPC`
     - **Subnet**: `ANB-Public-Subnet-1`
     - **Auto-assign public IP**: Enable
     - **Firewall (security groups)**: Select existing → `ANB-Worker-SG`
   - **Storage**: 50 GiB gp3

3. Clic en **Launch instance**

4. Esperar a que esté "Running"

5. **📝 Anotar las IPs**:
   - Public IPv4: `_______________`
   - Private IPv4: `_______________`

### 5.3 Actualizar Security Groups (IMPORTANTE)

Ahora que tenemos todas las IPs, vamos a restringir el acceso:

#### Actualizar `ANB-FileServer-SG`:

1. **EC2** → **Security Groups** → Seleccionar `ANB-FileServer-SG` → **Edit inbound rules**
2. **Eliminar** la regla de NFS 0.0.0.0/0
3. **Agregar**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | NFS | 2049 | ANB-WebServer-SG | NFS from Web Server |
   | NFS | 2049 | ANB-Worker-SG | NFS from Worker |

4. **Save rules**

#### Actualizar `ANB-WebServer-SG`:

1. Seleccionar `ANB-WebServer-SG` → **Edit inbound rules**
2. **Eliminar** la regla existente de Redis (puerto 6379 con source 0.0.0.0/0)
3. **Agregar nueva regla**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | Custom TCP | 6379 | ANB-Worker-SG | Redis from Worker |

4. **Save rules**

   ⚠️ **Nota**: No puedes modificar el source de CIDR a Security Group, debes eliminar y recrear la regla.

#### Actualizar `ANB-RDS-SG`:

1. Seleccionar `ANB-RDS-SG` → **Edit inbound rules**
2. **Eliminar** la regla PostgreSQL 0.0.0.0/0
3. **Agregar**:

   | Type | Port | Source | Description |
   |------|------|--------|-------------|
   | PostgreSQL | 5432 | ANB-WebServer-SG | From Web Server |
   | PostgreSQL | 5432 | ANB-Worker-SG | From Worker |

4. **Save rules**

### 5.4 Configurar File Server (Ahora que tenemos todas las IPs)

⚠️ **IMPORTANTE**: Ahora sí vamos a configurar el File Server porque ya tenemos todas las IPs.

**Copiar el script al File Server** (desde tu máquina local):
```bash
cd /ruta/a/MISO4204-Desarrollo_Nube
scp -i /ruta/a/anb-key-pair.pem \
    deployment/ec2-setup/01-fileserver-setup.sh \
    ubuntu@<FILE_SERVER_PUBLIC_IP>:~
```

**Conectarse al File Server**:
```bash
ssh -i /ruta/a/anb-key-pair.pem ubuntu@<FILE_SERVER_PUBLIC_IP>
```

**Editar el script**:
```bash
nano 01-fileserver-setup.sh
```

**Configurar las IPs privadas**:
```bash
WEBSERVER_PRIVATE_IP="<IP_PRIVADA_WEB_SERVER>"
WORKER_PRIVATE_IP="<IP_PRIVADA_WORKER>"
```

**Guardar** (Ctrl+O, Enter, Ctrl+X)

**Ejecutar el script**:
```bash
chmod +x 01-fileserver-setup.sh
./01-fileserver-setup.sh
```

⏳ **Esperar a que termine la configuración del NFS...**

---

### 5.5 Configurar Web Server (Ahora con NFS listo)

✅ **Ahora sí podemos configurar el Web Server** porque el File Server ya está exportando NFS.

**Copiar el script al Web Server** (desde tu máquina local):

```bash
# Asegúrate de estar en el directorio del proyecto
cd /ruta/a/MISO4204-Desarrollo_Nube

# Ejemplo con tus rutas reales:
# cd /home/juan-perdomo/Documentos/workspaces/miso/MISO4204-Desarrollo_Nube

# Copiar el script
scp -i /ruta/a/anb-key-pair.pem \
    deployment/ec2-setup/02-webserver-setup.sh \
    ubuntu@<WEB_SERVER_PUBLIC_IP>:~
```

**Conectarse al Web Server**:

```bash
ssh -i /ruta/a/anb-key-pair.pem ubuntu@<WEB_SERVER_PUBLIC_IP>
```

**Editar el script para configurar las variables**:
## QUEDE ACA SE CAYO EL ENTORNO DE PYTHON
```bash
nano 02-webserver-setup.sh
```

**Buscar la sección de variables (líneas 36-44) y configurar**:
```bash
FILESERVER_PRIVATE_IP="<IP_PRIVADA_FILE_SERVER>"      # Ejemplo: 10.0.1.139
RDS_ENDPOINT="<RDS_ENDPOINT>"                          # Ejemplo: anb-db.xxxxx.us-east-1.rds.amazonaws.com (SIN puerto, SIN postgresql://)
RDS_PASSWORD="<TU_RDS_PASSWORD>"                       # El password que configuraste en RDS
SECRET_KEY=""                                           # Dejar vacío, se generará automáticamente
GITHUB_REPO="https://github.com/tu-usuario/MISO4204-Desarrollo_Nube.git"
GITHUB_BRANCH="feature/Implement-aws-infra"            # Rama con los cambios para AWS (usa Python 3.11)
```

💡 **Tip sobre SECRET_KEY**: El script generará uno automáticamente y lo mostrará al final. **Debes guardarlo** para usarlo en el Worker.

**Guardar** (Ctrl+O, Enter, Ctrl+X)

**Ejecutar el script** (tomará ~15 minutos):
```bash
chmod +x 02-webserver-setup.sh
./02-webserver-setup.sh
```

⏳ **Esperar a que termine la instalación...**

**Al finalizar, el script mostrará**:
- ⚠️ Aviso de que NFS no está montado (esto es normal)
- ✅ Confirmación de servicios activos (FastAPI, Nginx, Redis)
- 🔑 Un SECRET_KEY generado - **GUÁRDALO** para el paso del Worker
- 🌐 La IP pública para acceder a la API

📝 **IMPORTANTE**: Anota el SECRET_KEY que se muestra, lo necesitarás para configurar el Worker.

---

### 5.6 Configurar Worker

**En tu máquina local**, copiar el script al Worker:

```bash
# Asegúrate de estar en el directorio del proyecto
cd /ruta/a/MISO4204-Desarrollo_Nube

# Copiar el script
scp -i /ruta/a/anb-key-pair.pem \
    deployment/ec2-setup/03-worker-setup.sh \
    ubuntu@<WORKER_PUBLIC_IP>:~
```

**En el Worker** (vía SSH):

```bash
# Editar el script
nano 03-worker-setup.sh
```

**Configurar estas variables**:
```bash
FILESERVER_PRIVATE_IP="<IP_PRIVADA_FILE_SERVER>"
WEBSERVER_PRIVATE_IP="<IP_PRIVADA_WEB_SERVER>"  # Para Redis
RDS_ENDPOINT="<RDS_ENDPOINT>"
RDS_PASSWORD="<TU_RDS_PASSWORD>"
SECRET_KEY="<MISMO_SECRET_KEY_DEL_WEB_SERVER>"  # ⚠️ DEBE SER EL MISMO
GITHUB_REPO="https://github.com/tu-usuario/MISO4204-Desarrollo_Nube.git"
GITHUB_BRANCH="main"
```

**Guardar** (Ctrl+O, Enter, Ctrl+X)

**Ejecutar el script** (tomará ~15 minutos):
```bash
chmod +x 03-worker-setup.sh
./03-worker-setup.sh
```

⏳ **Esperar a que termine...**

### 5.7 Montar NFS en Web Server y Worker

✅ Ahora que el File Server está configurado y exportando NFS, podemos montar el sistema de archivos compartido.

**En el Web Server**:
```bash
# Conectarse al Web Server
ssh -i /ruta/a/anb-key-pair.pem ubuntu@<WEB_SERVER_PUBLIC_IP>

# Montar NFS desde File Server
sudo mount -t nfs <FILESERVER_PRIVATE_IP>:/shared/media /app/media

# Verificar que el montaje fue exitoso
df -h | grep /app/media
# Deberías ver algo como:
# 10.0.1.139:/shared/media   50G  1.8G   46G   4% /app/media

# Descomentar la línea en fstab para montaje permanente al reiniciar
sudo sed -i 's/^# \(.*\/app\/media.*\)/\1/' /etc/fstab

# Verificar que fstab quedó bien configurado
cat /etc/fstab | grep /app/media

# Crear directorios necesarios en el NFS compartido (si no existen)
sudo mkdir -p /app/media/uploads
sudo mkdir -p /app/media/processed
sudo chown -R appuser:appuser /app/media

# Reiniciar servicio FastAPI para que use el NFS
sudo systemctl restart fastapi

# Verificar que FastAPI está corriendo correctamente
sudo systemctl status fastapi

# Verificar que la API responde
curl http://localhost:8080/health
```

**En el Worker**:
```bash
# Conectarse al Worker
ssh -i /ruta/a/anb-key-pair.pem ubuntu@<WORKER_PUBLIC_IP>

# Montar NFS desde File Server
sudo mount -t nfs <FILESERVER_PRIVATE_IP>:/shared/media /app/media

# Verificar que el montaje fue exitoso
df -h | grep /app/media
# Deberías ver el mismo sistema de archivos que en el Web Server

# Descomentar la línea en fstab para montaje permanente
sudo sed -i 's/^# \(.*\/app\/media.*\)/\1/' /etc/fstab

# Verificar que fstab quedó bien configurado
cat /etc/fstab | grep /app/media

# Verificar que los directorios existen y tienen permisos correctos
ls -la /app/media/
# Deberías ver: uploads/ y processed/

# Reiniciar servicio Celery para que use el NFS
sudo systemctl restart celery

# Verificar que Celery está corriendo correctamente
sudo systemctl status celery

# Verificar logs de Celery
sudo journalctl -u celery -n 20 --no-pager
```

### 5.8 Verificar Worker

```bash
# Verificar servicio Celery
sudo systemctl status celery

# Verificar montaje NFS (debería mostrar el montaje ahora)
df -h | grep /app/media

# Verificar conexión a Redis
redis-cli -h <WEBSERVER_PRIVATE_IP> ping
# Debería responder: PONG

# Ver logs de Celery
sudo journalctl -u celery -n 20
```

---

## Paso 6: Verificación Final

**Tiempo estimado: 10 minutos**

### 6.1 Verificar Arquitectura Completa

**Checklist:**

- [ ] **File Server**: NFS corriendo y exportando `/shared/media`
  ```bash
  ssh -i anb-key-pair.pem ubuntu@<FILE_SERVER_IP>
  sudo systemctl status nfs-kernel-server
  sudo exportfs -v
  ```

- [ ] **Web Server**: Todos los servicios activos
  ```bash
  ssh -i anb-key-pair.pem ubuntu@<WEB_SERVER_IP>
  sudo systemctl status fastapi nginx redis-server
  df -h | grep /app/media
  ```

- [ ] **Worker**: Celery activo y conectado
  ```bash
  ssh -i anb-key-pair.pem ubuntu@<WORKER_IP>
  sudo systemctl status celery
  df -h | grep /app/media
  ```

- [ ] **RDS**: Accesible desde Web Server y Worker

### 6.2 Pruebas Funcionales

**Desde tu máquina local**, configurar variable de entorno:

```bash
export API_URL=http://<WEB_SERVER_PUBLIC_IP>:8080
```

#### 1. Health Check
```bash
curl $API_URL/health
```

#### 2. Registrar Usuario
```bash
curl -X POST $API_URL/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password1": "Test123!@#",
    "password2": "Test123!@#",
    "first_name": "Test",
    "last_name": "User",
    "city": "Bogota",
    "country": "Colombia"
  }'
```

#### 3. Login
```bash
curl -X POST $API_URL/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "Test123!@#"
  }'
```

📝 **Guardar el token**:
```bash
export TOKEN="<tu_access_token>"
```

#### 4. Subir Video de Prueba

**Descargar un video de prueba**:
```bash
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4
```

**Subir el video**:
```bash
curl -X POST $API_URL/api/videos/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@big_buck_bunny_720p_1mb.mp4" \
  -F "title=Video Prueba AWS" \
  -F "description=Prueba de procesamiento"
```

#### 5. Verificar Procesamiento

**Listar videos**:
```bash
curl -X GET $API_URL/api/videos/ \
  -H "Authorization: Bearer $TOKEN"
```

**Monitorear logs del Worker** (en otra terminal):
```bash
ssh -i anb-key-pair.pem ubuntu@<WORKER_IP>
sudo journalctl -u celery -f
```

**Ver archivos en File Server**:
```bash
ssh -i anb-key-pair.pem ubuntu@<FILE_SERVER_IP>
watch -n 2 'ls -lh /shared/media/uploads/ && echo && ls -lh /shared/media/processed/'
```

#### 6. Verificar Video Procesado

Espera ~30-60 segundos y lista de nuevo:
```bash
curl -X GET $API_URL/api/videos/ \
  -H "Authorization: Bearer $TOKEN"
```

Deberías ver el video con `status: "processed"`.

---

## Troubleshooting

### NFS no monta

**Síntomas**: Error al ejecutar script o `df -h` no muestra `/app/media`

**Solución**:
```bash
# Verificar conectividad
ping <FILESERVER_PRIVATE_IP>

# Verificar exports en File Server
ssh -i anb-key-pair.pem ubuntu@<FILE_SERVER_IP>
sudo exportfs -v
showmount -e localhost

# Verificar que el cliente puede ver los exports
showmount -e <FILESERVER_PRIVATE_IP>

# Intentar montar manualmente
sudo mount -t nfs <FILESERVER_PRIVATE_IP>:/shared/media /app/media -v

# Verificar Security Group permite NFS (puerto 2049)
```

### FastAPI no inicia

**Síntomas**: `systemctl status fastapi` muestra "failed"

**Solución**:
```bash
# Ver logs completos
sudo journalctl -u fastapi -n 100 --no-pager

# Verificar conexión a RDS
psql -h <RDS_ENDPOINT> -U fastapi_user -d fastapi_db
# (ingresar password)

# Verificar variables de entorno
sudo cat /home/appuser/MISO4204-Desarrollo_Nube/.env

# Iniciar manualmente para ver errores
cd /home/appuser/MISO4204-Desarrollo_Nube
source .venv/bin/activate
gunicorn app.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 127.0.0.1:8000
```

### Worker no procesa videos

**Síntomas**: Videos quedan en estado "processing"

**Solución**:
```bash
# Ver logs de Celery
sudo journalctl -u celery -n 100 --no-pager

# Verificar conexión a Redis
redis-cli -h <WEBSERVER_PRIVATE_IP> ping

# Verificar FFmpeg
which ffmpeg
ffmpeg -version

# Iniciar worker manualmente
cd /home/appuser/MISO4204-Desarrollo_Nube
source .venv/bin/activate
celery -A app.worker.celery_app worker --loglevel=debug

# Verificar Security Group permite Redis (puerto 6379)
```

### Nginx 502 Bad Gateway

**Síntomas**: `curl` al puerto 8080 retorna 502

**Solución**:
```bash
# Verificar que FastAPI está corriendo
sudo systemctl status fastapi

# Ver logs de Nginx
sudo tail -f /var/log/nginx/error.log

# Verificar configuración
sudo nginx -t

# Probar FastAPI directamente
curl http://localhost:8000/health

# Reiniciar servicios
sudo systemctl restart fastapi
sudo systemctl restart nginx
```

### No puedo conectarme por SSH

**Solución**:
1. Verificar Security Group permite SSH desde tu IP
2. Verificar que tu IP no cambió:
   ```bash
   curl https://checkip.amazonaws.com
   ```
3. Verificar permisos de la key:
   ```bash
   chmod 400 anb-key-pair.pem
   ```
4. Usar modo verbose:
   ```bash
   ssh -v -i anb-key-pair.pem ubuntu@<IP>
   ```

### Errores de conexión entre instancias

**Síntomas**: Worker no puede conectarse a Redis, o no puede montar NFS

**Solución**:
1. Verificar que todas las instancias están en la misma VPC
2. Verificar Security Groups permiten el tráfico necesario
3. Verificar IPs privadas son correctas
4. Usar `ping` para verificar conectividad:
   ```bash
   ping <IP_PRIVADA_DESTINO>
   ```

---

## Control de Costos

### Durante Desarrollo

**Detener instancias cuando no las uses** (NO terminar):
```bash
# AWS Console: EC2 → Instances → Select → Instance State → Stop
```

O con AWS CLI:
```bash
aws ec2 stop-instances --instance-ids \
  i-fileserver \
  i-webserver \
  i-worker
```

### Después de la Entrega

⚠️ **IMPORTANTE**: **Eliminar Amazon RDS** porque es el servicio más costoso.

**Pasos para eliminar RDS**:
1. AWS Console → RDS → Databases
2. Seleccionar `anb-postgres-db`
3. Actions → Delete
4. ❌ Desmarcar "Create final snapshot"
5. ✅ Marcar "I acknowledge..."
6. Escribir: `delete me`
7. Delete

**Opcional**: Terminar instancias EC2 si no las vas a usar más:
```bash
# AWS Console: EC2 → Instances → Select → Instance State → Terminate
```

---

## Próximos Pasos

Después de completar el despliegue:

1. [ ] Ejecutar pruebas de carga (K6, Newman, etc.)
2. [ ] Documentar resultados en `/docs/Entrega_2/`
3. [ ] Crear diagramas de arquitectura
4. [ ] Actualizar reporte de SonarQube
5. [ ] Grabar video de sustentación (15-20 min)
6. [ ] Crear release en GitHub
7. [ ] ⚠️ **ELIMINAR RDS** para ahorrar costos

---

## Comandos Útiles

### Ver logs en tiempo real
```bash
# FastAPI (Web Server)
sudo journalctl -u fastapi -f

# Celery (Worker)
sudo journalctl -u celery -f

# Nginx (Web Server)
sudo tail -f /var/log/nginx/fastapi-error.log

# NFS (File Server)
sudo journalctl -u nfs-kernel-server -f
```

### Reiniciar servicios
```bash
# Web Server
sudo systemctl restart fastapi nginx redis-server

# Worker
sudo systemctl restart celery

# File Server
sudo systemctl restart nfs-kernel-server
```

### Ver estado de servicios
```bash
sudo systemctl status <servicio>
```

### Ver uso de recursos
```bash
htop
df -h
free -h
```

---

**¡Despliegue completado! 🎉**

Si tienes problemas, revisa la sección de [Troubleshooting](#troubleshooting) o los logs de los servicios.
