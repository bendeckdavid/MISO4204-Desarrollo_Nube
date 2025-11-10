# Scripts de Pruebas de Carga - Entrega 3

Scripts utilizados para las pruebas de capacidad de la infraestructura en AWS con ALB, ASG y S3.

## 📁 Estructura de Archivos

```
scripts-entrega3/
├── test_escenario1_capa_web.js          # Test k6 - Escenario 1 (capa web)
├── test_escenario2_upload_videos.js     # Test k6 - Escenario 2 (upload videos)
├── graficas_escenario1.py               # Generación de gráficas Escenario 1
├── generar_graficas_escenario2.py       # Generación de gráficas Escenario 2
└── setup_crear_usuarios_prueba.sh       # Setup inicial de usuarios de prueba
```

## 🧪 Escenario 1: Prueba de Capacidad de la Capa Web

**Archivo**: `test_escenario1_capa_web.js`

### Descripción
Prueba progresiva de carga sobre la capa web con 4 fases: Smoke (5 VUs) → Moderada (50 VUs) → Alta (100 VUs) → Estrés (150 VUs).

### Uso
```bash
cd /path/to/capacity-planning/scripts-entrega3
k6 run test_escenario1_capa_web.js
```

### Duración
17 minutos

### Métricas
- Usuarios concurrentes máximos
- Throughput (req/s)
- Latencia (p50, p90, p95)
- Tasa de error

## 📤 Escenario 2: Upload y Cola de Procesamiento

**Archivo**: `test_escenario2_upload_videos.js`

### Descripción
Test mínimo para validar uploads de videos a S3 y entrada en cola de procesamiento con Celery.

### Uso
```bash
cd /path/to/capacity-planning/scripts-entrega3
k6 run test_escenario2_upload_videos.js
```

### Duración
3 minutos

### Métricas
- Tasa de éxito de uploads
- Tiempo de upload (promedio, p95)
- Videos en cola de procesamiento

## 📊 Generación de Gráficas

### Escenario 1
**Archivo**: `graficas_escenario1.py`

```bash
cd /path/to/capacity-planning/scripts-entrega3
python3 graficas_escenario1.py
```

**Salida**: `../results-entrega3/graficas_escenario1.png`

### Escenario 2
**Archivo**: `generar_graficas_escenario2.py`

```bash
cd /path/to/capacity-planning/scripts-entrega3
python3 generar_graficas_escenario2.py
```

**Salida**: `../results-entrega3/graficas_escenario2.png`

## 🔧 Setup Inicial

**Archivo**: `setup_crear_usuarios_prueba.sh`

### Descripción
Script para crear 5 usuarios de prueba en el sistema antes de ejecutar las pruebas.

### Uso
```bash
./setup_crear_usuarios_prueba.sh <ALB_URL>
```

**Ejemplo**:
```bash
./setup_crear_usuarios_prueba.sh http://anb-video-alb-760991728.us-east-1.elb.amazonaws.com
```

### Usuarios Creados
- test1@anb.com / Test123!
- test2@anb.com / Test123!
- test3@anb.com / Test123!
- test4@anb.com / Test123!
- test5@anb.com / Test123!

## 📋 Requisitos

### Para ejecutar tests k6
```bash
# Ubuntu/Debian
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### Para generar gráficas
```bash
pip3 install matplotlib numpy
```

## 🚀 Flujo de Trabajo Completo

1. **Setup inicial** (una vez):
   ```bash
   ./setup_crear_usuarios_prueba.sh <ALB_URL>
   ```

2. **Ejecutar Escenario 1**:
   ```bash
   k6 run test_escenario1_capa_web.js 2>&1 | tee ../results-entrega3/escenario1.log
   python3 graficas_escenario1.py
   ```

3. **Ejecutar Escenario 2**:
   ```bash
   k6 run test_escenario2_upload_videos.js 2>&1 | tee ../results-entrega3/escenario2.log
   python3 generar_graficas_escenario2.py
   ```

## 📖 Documentación

Ver documento completo de resultados: [pruebas_de_carga_entrega3.md](../pruebas_de_carga_entrega3.md)

## ⚙️ Configuración

Los tests están configurados para usar:
- **ALB URL**: `http://anb-video-alb-760991728.us-east-1.elb.amazonaws.com`
- **Región AWS**: us-east-1
- **Timeout de requests**: Variable según escenario

Para cambiar la URL base, editar la constante `BASE_URL` en los archivos `.js`.
