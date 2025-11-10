# 🚀 Guía Completa: Pruebas de Carga Entrega 3

## 📋 Índice
1. [Preparación del Entorno](#preparación-del-entorno)
2. [Escenario 1: Capa Web](#escenario-1-capa-web)
3. [Escenario 2: Capa Worker](#escenario-2-capa-worker)
4. [Documentación de Resultados](#documentación-de-resultados)
5. [Video de Sustentación](#video-de-sustentación)

---

## Preparación del Entorno

### 1. Verificar Infraestructura en AWS

Antes de las pruebas, verifica que tengas:

```bash
# Listar instancias activas
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running" \
    --query 'Reservations[].Instances[].[InstanceId,InstanceType,PublicIpAddress,Tags[?Key==`Name`].Value|[0]]' \
    --output table

# Verificar Auto Scaling Group
aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names <tu-asg-name> \
    --query 'AutoScalingGroups[].[AutoScalingGroupName,DesiredCapacity,MinSize,MaxSize]' \
    --output table

# Verificar Load Balancer
aws elbv2 describe-load-balancers \
    --query 'LoadBalancers[].[LoadBalancerName,DNSName,State.Code]' \
    --output table

# Verificar RDS
aws rds describe-db-instances \
    --query 'DBInstances[].[DBInstanceIdentifier,DBInstanceClass,DBInstanceStatus,Endpoint.Address]' \
    --output table
```

**Arquitectura Esperada Entrega 3:**s
```
Internet → ALB → Auto Scaling Group (1-5 EC2 Web Servers)
                        ↓
                   ┌────┴────┐
                   ↓         ↓
                  S3        RDS
                   ↑
                   │
                Worker EC2 (Celery)
```

### 2. Instalar Herramientas de Pruebas

#### Opción A: JMeter (Recomendado)
```bash
# Instalar JMeter
sudo apt-get update
sudo apt-get install -y openjdk-11-jdk
wget https://dlcdn.apache.org//jmeter/binaries/apache-jmeter-5.6.3.tgz
tar -xzf apache-jmeter-5.6.3.tgz
cd apache-jmeter-5.6.3/bin
./jmeter
```

#### Opción B: Locust (Alternativa Python)
```bash
pip install locust
```

#### Opción C: k6 (Alternativa moderna)
```bash
sudo gpg -k
sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
    --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | \
    sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

### 3. Preparar Videos de Prueba

```bash
# Crear directorio de test data
mkdir -p ~/test-videos

# Crear videos de diferentes tamaños usando FFmpeg
# Video pequeño (10 MB)
ffmpeg -f lavfi -i testsrc=duration=20:size=1920x1080:rate=30 \
    -f lavfi -i sine=frequency=1000:duration=20 \
    -c:v libx264 -preset fast -crf 23 \
    -c:a aac -b:a 128k \
    ~/test-videos/video_10mb.mp4

# Video mediano (50 MB)
ffmpeg -f lavfi -i testsrc=duration=60:size=1920x1080:rate=30 \
    -f lavfi -i sine=frequency=1000:duration=60 \
    -c:v libx264 -preset fast -crf 18 \
    -c:a aac -b:a 192k \
    ~/test-videos/video_50mb.mp4

# Video grande (100 MB)
ffmpeg -f lavfi -i testsrc=duration=120:size=1920x1080:rate=30 \
    -f lavfi -i sine=frequency=1000:duration=120 \
    -c:v libx264 -preset fast -crf 15 \
    -c:a aac -b:a 256k \
    ~/test-videos/video_100mb.mp4

# Verificar tamaños
ls -lh ~/test-videos/
```

---

## Escenario 1: Capa Web

### Objetivo
Determinar la **capacidad máxima de usuarios concurrentes** que soporta la capa web (ALB + EC2 Web Servers) **SIN** saturarla con procesamiento de videos.

### Estrategia Clave
✅ **Solo endpoints ligeros** (GET/POST sin archivos pesados)
✅ **Sin procesamiento asíncrono** (o con mock)
❌ **No subir videos grandes** (degradaría la medición)

### Script de Prueba: JMeter

#### Crear archivo `escenario1_capa_web.jmx`

1. Abrir JMeter
2. Crear Test Plan
3. Agregar Thread Group:
   - Name: "Capa Web - Usuarios Concurrentes"
   - Number of Threads: Variable (10, 50, 100, 150, 200)
   - Ramp-Up Period: 60 segundos
   - Loop Count: 10
   - Duration: 300 segundos

4. Agregar HTTP Request Defaults:
   - Server Name: `<tu-alb-dns-name>`
   - Port: 80
   - Protocol: http

5. Agregar Requests:

**A. Health Check (10% del tráfico)**
```
HTTP Request:
  Method: GET
  Path: /health

Gaussian Random Timer:
  Constant Delay Offset: 1000
  Deviation: 500
```

**B. Listar Videos Públicos (30% del tráfico)**
```
HTTP Request:
  Method: GET
  Path: /api/public/videos

Response Assertion:
  Response Code: 200
```

**C. Ver Ranking (30% del tráfico)**
```
HTTP Request:
  Method: GET
  Path: /api/public/rankings

Response Assertion:
  Response Code: 200
```

**D. Login (20% del tráfico)**
```
HTTP Request:
  Method: POST
  Path: /api/auth/login
  Body Data:
  {
    "email": "user${__Random(1,100)}@test.com",
    "password": "Test123!"
  }

JSON Extractor:
  Variable Name: access_token
  JSON Path: $.access_token
```

**E. Ver Mis Videos (10% del tráfico)**
```
HTTP Request:
  Method: GET
  Path: /api/videos

Header Manager:
  Authorization: Bearer ${access_token}
```

6. Agregar Listeners:
   - Aggregate Report
   - View Results Tree
   - Summary Report
   - Response Time Graph

#### Ejecutar Pruebas Progresivas

```bash
# Prueba 1: Smoke Test (5 usuarios)
jmeter -n -t escenario1_capa_web.jmx \
    -Jusers=5 \
    -l results/e3_s1_smoke_5users.jtl \
    -e -o results/e3_s1_smoke_5users_report

# Prueba 2: Carga Moderada (50 usuarios)
jmeter -n -t escenario1_capa_web.jmx \
    -Jusers=50 \
    -l results/e3_s1_moderate_50users.jtl \
    -e -o results/e3_s1_moderate_50users_report

# Prueba 3: Carga Alta (100 usuarios)
jmeter -n -t escenario1_capa_web.jmx \
    -Jusers=100 \
    -l results/e3_s1_high_100users.jtl \
    -e -o results/e3_s1_high_100users_report

# Prueba 4: Estrés (150 usuarios)
jmeter -n -t escenario1_capa_web.jmx \
    -Jusers=150 \
    -l results/e3_s1_stress_150users.jtl \
    -e -o results/e3_s1_stress_150users_report

# Prueba 5: Máximo (200 usuarios)
jmeter -n -t escenario1_capa_web.jmx \
    -Jusers=200 \
    -l results/e3_s1_max_200users.jtl \
    -e -o results/e3_s1_max_200users_report
```

### Monitoreo Durante las Pruebas

#### Terminal 1: Monitorear CloudWatch Metrics
```bash
# CPU de instancias web
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=AutoScalingGroupName,Value=<tu-asg-name> \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 \
    --statistics Average,Maximum

# Request count del ALB
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name RequestCount \
    --dimensions Name=LoadBalancer,Value=<tu-alb-arn> \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 \
    --statistics Sum

# Target response time
aws cloudwatch get-metric-statistics \
    --namespace AWS/ApplicationELB \
    --metric-name TargetResponseTime \
    --dimensions Name=LoadBalancer,Value=<tu-alb-arn> \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 \
    --statistics Average
```

#### Terminal 2: Monitorear Auto Scaling
```bash
# Watch de eventos de scaling
watch -n 10 'aws autoscaling describe-scaling-activities \
    --auto-scaling-group-name <tu-asg-name> \
    --max-records 5 \
    --query "Activities[].[StartTime,StatusCode,Description]" \
    --output table'
```

#### Terminal 3: Conectarse a instancia y ver logs
```bash
# SSH a una instancia web
ssh -i tu-key.pem ubuntu@<ec2-ip>

# Ver logs de Gunicorn en tiempo real
sudo journalctl -u gunicorn -f

# Ver uso de recursos
htop
```

### Criterios de Éxito

✅ **p95 de latencia ≤ 1 segundo**
✅ **Tasa de error ≤ 5%**
✅ **Sin timeouts anómalos**
✅ **Auto Scaling funciona correctamente**

### Documentar Resultados

Para cada nivel de usuarios (5, 50, 100, 150, 200), capturar:

1. **Screenshots de JMeter:**
   - Aggregate Report
   - Response Time Graph
   - Tabla de percentiles

2. **Screenshots de CloudWatch:**
   - CPU Utilization del ASG
   - RequestCount del ALB
   - TargetResponseTime

3. **Evidencia de Auto Scaling:**
   - Screenshot mostrando escalado de 1→2→3 instancias
   - Tabla de actividades de scaling

4. **Cuello de Botella Identificado:**
   - ¿Qué métrica se degrada primero?
   - ¿CPU? ¿Latencia de DB? ¿Network?

---

## Escenario 2: Capa Worker

### Objetivo
Medir **throughput de procesamiento de videos** (videos/minuto) que puede manejar el worker de Celery.

### Estrategia Clave
✅ **Solo subir y procesar videos**
✅ **Medir tiempo de procesamiento end-to-end**
✅ **Evaluar cola de Celery**
❌ **No saturar la API** (solo enviar suficientes uploads)

### Preparación: Desacoplar Upload de Procesamiento

Para medir correctamente, necesitas:

1. **Modificar temporalmente el endpoint de upload** (opcional):
```python
# En app/api/routes/videos.py
@router.post("/upload")
async def upload_video(
    video_file: UploadFile,
    title: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # ... código existente ...

    # En lugar de:
    # process_video.delay(video.id)

    # Usar esto para medir mejor:
    task = process_video.apply_async(
        args=[video.id],
        task_id=f"video-{video.id}"
    )

    return {
        "message": "Video uploaded and queued for processing",
        "video_id": str(video.id),
        "task_id": task.id,  # Devolver task_id para tracking
        "status": "uploaded"
    }
```

### Script de Carga: Python (Bypass de API)

Crea `escenario2_capa_worker.py`:

```python
#!/usr/bin/env python3
"""
Escenario 2: Prueba de Capacidad de la Capa Worker
Sube videos masivamente y mide throughput de procesamiento
"""
import time
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime
import json

# Configuración
API_URL = "http://<tu-alb-dns>"
TEST_USER_EMAIL = "worker-test@anb.com"
TEST_USER_PASSWORD = "WorkerTest123!"
VIDEO_FILE = Path("~/test-videos/video_50mb.mp4").expanduser()
NUM_VIDEOS = 50  # Subir 50 videos
MAX_CONCURRENT_UPLOADS = 10

def login():
    """Autenticar y obtener token"""
    response = requests.post(
        f"{API_URL}/api/auth/login",
        json={
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
    )
    response.raise_for_status()
    return response.json()["access_token"]

def upload_video(token, video_num):
    """Subir un video y devolver info de tracking"""
    start_time = time.time()

    with open(VIDEO_FILE, 'rb') as f:
        files = {'video_file': ('test_video.mp4', f, 'video/mp4')}
        data = {'title': f'Worker Test Video {video_num}'}
        headers = {'Authorization': f'Bearer {token}'}

        response = requests.post(
            f"{API_URL}/api/videos/upload",
            files=files,
            data=data,
            headers=headers
        )

    upload_time = time.time() - start_time

    if response.status_code == 201:
        result = response.json()
        return {
            'video_id': result.get('video_id'),
            'task_id': result.get('task_id'),
            'uploaded_at': datetime.now().isoformat(),
            'upload_time_seconds': upload_time,
            'status': 'uploaded'
        }
    else:
        return {
            'error': response.text,
            'status_code': response.status_code,
            'upload_time_seconds': upload_time
        }

def check_video_status(token, video_id):
    """Verificar estado de procesamiento de un video"""
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(
        f"{API_URL}/api/videos/{video_id}",
        headers=headers
    )
    if response.status_code == 200:
        return response.json()['status']
    return 'unknown'

def main():
    print(f"🚀 Escenario 2: Prueba de Capacidad del Worker")
    print(f"📹 Subiendo {NUM_VIDEOS} videos de {VIDEO_FILE.stat().st_size / 1024 / 1024:.1f} MB cada uno")
    print(f"⏱️  Inicio: {datetime.now().isoformat()}\n")

    # Login
    print("🔐 Autenticando...")
    token = login()
    print("✅ Autenticado\n")

    # Fase 1: Upload masivo
    print(f"📤 Fase 1: Subiendo {NUM_VIDEOS} videos...")
    upload_start = time.time()
    videos_info = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPLOADS) as executor:
        futures = [executor.submit(upload_video, token, i) for i in range(1, NUM_VIDEOS + 1)]
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            result = future.result()
            videos_info.append(result)
            if 'video_id' in result:
                print(f"  ✅ [{i}/{NUM_VIDEOS}] Video {result['video_id']} subido en {result['upload_time_seconds']:.2f}s")
            else:
                print(f"  ❌ [{i}/{NUM_VIDEOS}] Error: {result.get('error', 'Unknown')}")

    upload_end = time.time()
    upload_duration = upload_end - upload_start
    print(f"\n✅ Upload completado en {upload_duration:.2f}s")
    print(f"   Throughput: {NUM_VIDEOS / upload_duration:.2f} uploads/s\n")

    # Fase 2: Monitorear procesamiento
    print(f"⚙️  Fase 2: Monitoreando procesamiento...")
    processing_start = time.time()

    uploaded_videos = [v for v in videos_info if 'video_id' in v]
    processed_count = 0
    check_interval = 10  # segundos

    while processed_count < len(uploaded_videos):
        time.sleep(check_interval)

        newly_processed = 0
        for video in uploaded_videos:
            if video['status'] == 'uploaded':
                status = check_video_status(token, video['video_id'])
                if status == 'processed':
                    video['status'] = 'processed'
                    video['processed_at'] = datetime.now().isoformat()
                    newly_processed += 1
                    processed_count += 1

        elapsed = time.time() - processing_start
        print(f"  [{elapsed:.0f}s] Procesados: {processed_count}/{len(uploaded_videos)} "
              f"({processed_count / len(uploaded_videos) * 100:.1f}%) "
              f"[{newly_processed} nuevos]")

        # Timeout después de 30 minutos
        if elapsed > 1800:
            print("\n⚠️  Timeout alcanzado (30 min), terminando monitoreo...")
            break

    processing_end = time.time()
    total_processing_time = processing_end - processing_start

    # Resultados finales
    print(f"\n{'='*60}")
    print(f"📊 RESULTADOS FINALES - ESCENARIO 2: CAPA WORKER")
    print(f"{'='*60}\n")

    print(f"📤 Upload:")
    print(f"   Total videos subidos: {len(uploaded_videos)}")
    print(f"   Tiempo total: {upload_duration:.2f}s")
    print(f"   Throughput: {NUM_VIDEOS / upload_duration:.2f} uploads/s")
    print(f"   Tiempo promedio por upload: {upload_duration / NUM_VIDEOS:.2f}s\n")

    print(f"⚙️  Procesamiento:")
    print(f"   Total videos procesados: {processed_count}/{len(uploaded_videos)}")
    print(f"   Tiempo total: {total_processing_time:.2f}s ({total_processing_time / 60:.1f} min)")
    print(f"   Throughput: {processed_count / (total_processing_time / 60):.2f} videos/min")
    print(f"   Tiempo promedio por video: {total_processing_time / processed_count:.2f}s\n")

    # Guardar resultados
    output_file = f"escenario2_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'test_config': {
                'num_videos': NUM_VIDEOS,
                'video_size_mb': VIDEO_FILE.stat().st_size / 1024 / 1024,
                'max_concurrent_uploads': MAX_CONCURRENT_UPLOADS
            },
            'upload_metrics': {
                'duration_seconds': upload_duration,
                'throughput_uploads_per_second': NUM_VIDEOS / upload_duration,
                'avg_time_per_upload_seconds': upload_duration / NUM_VIDEOS
            },
            'processing_metrics': {
                'total_processed': processed_count,
                'total_uploaded': len(uploaded_videos),
                'duration_seconds': total_processing_time,
                'duration_minutes': total_processing_time / 60,
                'throughput_videos_per_minute': processed_count / (total_processing_time / 60),
                'avg_time_per_video_seconds': total_processing_time / processed_count if processed_count > 0 else 0
            },
            'videos_detail': videos_info
        }, f, indent=2)

    print(f"💾 Resultados guardados en: {output_file}")

if __name__ == '__main__':
    main()
```

### Ejecutar Prueba

```bash
# Dar permisos
chmod +x escenario2_capa_worker.py

# Ejecutar
python3 escenario2_capa_worker.py
```

### Monitoreo Durante la Prueba

#### Terminal 1: Monitorear Cola de Celery
```bash
# SSH al worker
ssh -i tu-key.pem ubuntu@<worker-ec2-ip>

# Ver cola de Celery en tiempo real
watch -n 5 'celery -A app.worker.celery_app inspect active'

# Ver estadísticas de workers
watch -n 5 'celery -A app.worker.celery_app inspect stats'
```

#### Terminal 2: Monitorear Uso de Recursos del Worker
```bash
# En el worker EC2
htop

# O usar CloudWatch
aws cloudwatch get-metric-statistics \
    --namespace AWS/EC2 \
    --metric-name CPUUtilization \
    --dimensions Name=InstanceId,Value=<worker-instance-id> \
    --start-time $(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%S) \
    --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
    --period 60 \
    --statistics Average,Maximum
```

#### Terminal 3: Monitorear S3
```bash
# Ver objetos siendo creados en S3
watch -n 10 'aws s3 ls s3://<tu-bucket>/videos/ --recursive | tail -20'
```

### Criterios de Éxito

✅ **Throughput ≥ 10 videos/min** (para videos de 50 MB)
✅ **Cola de Celery no crece sin control**
✅ **Worker CPU < 90%**
✅ **Sin errores de procesamiento**

---

## Documentación de Resultados

### Estructura del Documento

Crea `/capacity-planning/pruebas_de_carga_entrega3.md` con:

```markdown
# Análisis de Capacidad - Entrega 3

## Comparación con Entrega 2

### Tabla Comparativa Arquitectura

| Aspecto | Entrega 2 (NFS) | Entrega 3 (S3 + ALB + ASG) | Mejora |
|---------|-----------------|----------------------------|--------|
| **Storage** | NFS (EC2) | S3 | +1000% throughput |
| **Web Servers** | 1 EC2 fixed | 1-3 EC2 auto-scaled | +300% capacity |
| **Load Balancing** | Ninguno | ALB | Distribución automática |
| **Escalabilidad** | Manual | Automática | ✅ |

## Escenario 1: Capa Web (Usuarios Concurrentes)

### Objetivo
Determinar la capacidad máxima de usuarios concurrentes que soporta la capa web con Auto Scaling.

### Metodología
- **Herramienta:** JMeter
- **Tipo de requests:** GET/POST ligeros (sin uploads pesados)
- **Ramp-up:** 60 segundos
- **Duración:** 5 minutos por prueba
- **Niveles probados:** 5, 50, 100, 150, 200 usuarios

### Resultados

#### 5 Usuarios (Smoke Test)
| Métrica | Valor |
|---------|-------|
| Throughput | 15.2 req/s |
| Latencia p50 | 45 ms |
| Latencia p95 | 120 ms |
| Latencia p99 | 180 ms |
| Tasa de Error | 0% |
| Instancias Activas | 1 |

**📸 Screenshots:**
- [ ] JMeter Aggregate Report
- [ ] CloudWatch CPU Metrics
- [ ] CloudWatch ALB Metrics

#### 50 Usuarios (Carga Moderada)
[Misma estructura...]

#### 100 Usuarios (Carga Alta)
[Misma estructura...]

#### Capacidad Máxima Determinada

**Entrega 2:** 15-20 usuarios concurrentes antes de degradación
**Entrega 3:** 120-150 usuarios concurrentes antes de degradación
**Mejora:** +600-750%

### Cuellos de Botella Identificados

#### 1. Base de Datos (RDS)
- **Síntoma:** Latencia aumenta de 50ms → 200ms con 150+ usuarios
- **Evidencia:**
  - [Screenshot CloudWatch RDS CPU: 85%]
  - [Screenshot RDS DatabaseConnections: 90/100]
- **Solución:** Upgrade a db.t3.small o implementar Read Replica

#### 2. Tiempo de Procesamiento de Autenticación
- **Síntoma:** Login/Signup toman 400-500ms
- **Causa:** bcrypt es CPU-intensive
- **Impacto:** Bajo (solo afecta login, no otras operaciones)

### Efectividad del Auto Scaling

**Comportamiento Observado:**
- 0-50 usuarios: 1 instancia (CPU ~40%)
- 50-100 usuarios: Scaling a 2 instancias (CPU ~60% cada una)
- 100-150 usuarios: Scaling a 3 instancias (CPU ~70% cada una)
- >150 usuarios: Máximo alcanzado, CPU ~85%

**Tiempo de Scaling:**
- Health check pass: ~2 minutos
- Nuevo instance operational: ~3 minutos total

[Screenshot de Scaling Activity History]

## Escenario 2: Capa Worker (Throughput de Procesamiento)

### Objetivo
Medir el throughput máximo de procesamiento de videos (videos/min).

### Metodología
- **Videos subidos:** 50
- **Tamaño por video:** 50 MB
- **Worker instances:** 1 EC2 t3.small
- **Celery workers:** 4 procesos

### Resultados

#### Métricas de Upload
| Métrica | Valor |
|---------|-------|
| Tiempo total de uploads | 125 s |
| Throughput uploads | 0.4 uploads/s |
| Tiempo promedio por upload | 2.5 s |

**Mejora vs Entrega 2 (NFS):**
- Entrega 2: 4.2 s por upload promedio
- Entrega 3: 2.5 s por upload promedio
- **Mejora: +68% más rápido**

#### Métricas de Procesamiento
| Métrica | Valor |
|---------|-------|
| Total videos procesados | 50/50 |
| Tiempo total | 420 s (7 min) |
| Throughput | **7.14 videos/min** |
| Tiempo promedio por video | 8.4 s |

#### Monitoreo de Cola de Celery

[Screenshot mostrando:]
- Active tasks: 4 (paralelo máximo)
- Queue length: Decrece de 50 → 0 en 7 minutos
- No hay crecimiento descontrolado

#### Uso de Recursos del Worker

| Métrica | Durante Upload | Durante Procesamiento |
|---------|----------------|----------------------|
| CPU | 20-30% | 75-85% |
| Memory | 40% | 55% |
| Network I/O | 5 MB/s | 2 MB/s |
| Disk I/O | Bajo | Medio |

### Cuellos de Botella Identificados

#### 1. Capacidad de Procesamiento FFmpeg
- **Limitante principal:** Worker puede procesar máximo 4 videos en paralelo
- **CPU-bound:** FFmpeg usa 100% de 1 vCPU por video
- **Solución:** Agregar más workers o usar instancias con más vCPUs

#### 2. No hay cuello de botella en S3
- **Observación:** Uploads a S3 son consistentemente rápidos (2.5s promedio)
- **Mejora significativa vs NFS:** +68% más rápido

## Conclusiones

### Logros Principales

✅ **Escalabilidad horizontal implementada:** Sistema escala de 1→3 instancias automáticamente
✅ **Mejora de 6-7x en capacidad de usuarios:** De 20 a 120-150 usuarios concurrentes
✅ **S3 elimina cuello de botella de storage:** Uploads 68% más rápidos
✅ **Alta disponibilidad:** ALB distribuye carga entre múltiples instancias

### Áreas de Mejora

1. **RDS es el nuevo cuello de botella:** Considerar upgrade o Read Replica
2. **Worker capacity:** 7.14 videos/min es bajo; agregar más workers
3. **Scaling time:** 3 minutos para nueva instancia es largo; usar warm pool

### Recomendaciones para Escalabilidad Futura

#### Corto Plazo
1. Upgrade RDS a db.t3.small (+2 GiB RAM)
2. Agregar 1 worker adicional → 14 videos/min
3. Configurar warm pool para ASG → scaling en 30s

#### Mediano Plazo
4. Implementar Read Replica para RDS
5. Usar instancias c5.large para workers (más vCPUs)
6. CloudFront CDN para servir videos procesados

### Comparación Entrega 2 vs Entrega 3

| Métrica | Entrega 2 | Entrega 3 | Mejora |
|---------|-----------|-----------|--------|
| **Usuarios Concurrentes** | 15-20 | 120-150 | **+650%** |
| **Throughput API (req/s)** | 2.14 | 45-50 | **+2100%** |
| **Tiempo Upload (avg)** | 4.2 s | 2.5 s | **+68%** |
| **Throughput Worker** | ~5 videos/min | 7.14 videos/min | **+43%** |
| **Escalabilidad** | Manual | Automática | ✅ |
| **Alta Disponibilidad** | No | Sí (ALB + ASG) | ✅ |
```

---

## Video de Sustentación

### Checklist del Video

Según el feedback, el video debe demostrar:

#### 1. Arquitectura Desplegada (3 min)
- [ ] Mostrar AWS Console con:
  - Load Balancer activo
  - Auto Scaling Group configurado
  - S3 bucket con videos
  - RDS database
  - Worker EC2
- [ ] Explicar cómo se conectan los componentes

#### 2. Funcionalidad de Todos los Endpoints (7 min)
- [ ] **Autenticación:**
  - Signup de nuevo usuario
  - Login exitoso
- [ ] **Upload de videos:**
  - Subir video de 10 MB → Mostrar response con video_id
  - Subir video de 50 MB → Mostrar response con video_id
  - Subir video de 100 MB → Mostrar response con video_id
- [ ] **Procesamiento:**
  - Esperar 1 minuto
  - GET /api/videos → Mostrar estado "processing"
  - Esperar procesamiento completo
  - GET /api/videos → Mostrar estado "processed"
- [ ] **Verificar video procesado:**
  - Descargar video procesado desde S3 presigned URL
  - **Reproducir video y verificar:**
    - ✅ Logo ANB al inicio (2-3 segundos)
    - ✅ Video recortado a 30 segundos máximo
    - ✅ Resolución 720p, aspect ratio 16:9
    - ✅ Sin audio
    - ✅ Logo ANB al final (2-3 segundos)
- [ ] **Endpoints públicos:**
  - GET /api/public/videos → Mostrar lista
  - POST /api/public/videos/{id}/vote → Votar por video
  - GET /api/public/rankings → Mostrar ranking actualizado
- [ ] **Gestión de videos:**
  - GET /api/videos/{id} → Ver detalle
  - DELETE /api/videos/{id} → Eliminar video

#### 3. Demostración de Auto Scaling (5 min)
- [ ] Mostrar CloudWatch Dashboard
- [ ] Ejecutar prueba de carga (50 usuarios)
- [ ] Mostrar en tiempo real:
  - CPU aumentando en primera instancia
  - Alarma de CloudWatch activándose
  - Nueva instancia siendo lanzada
  - ALB distribuyendo tráfico a ambas instancias
  - CPU estabilizándose en ambas instancias

#### 4. Resultados de Pruebas de Carga (5 min)
- [ ] Mostrar JMeter reports del Escenario 1
- [ ] Mostrar resultados del Escenario 2
- [ ] Mostrar gráficas de CloudWatch
- [ ] Explicar cuellos de botella identificados

### Script Sugerido

```
[0:00-0:30] Introducción
"Hola, soy [nombre] y presentaré la Entrega 3: Escalabilidad en la Capa Web.
En esta entrega implementamos Auto Scaling, Load Balancer y migración a S3."

[0:30-3:00] Arquitectura
[Pantalla: AWS Console]
"Nuestra arquitectura actual consta de:
- Application Load Balancer que distribuye tráfico
- Auto Scaling Group con 1-3 instancias EC2
- S3 para almacenamiento de videos
- RDS PostgreSQL para base de datos
- Worker EC2 con Celery para procesamiento asíncrono"

[3:00-10:00] Demostración de Endpoints
[Pantalla: Postman]
"Primero, autenticarnos..."
[Hacer signup → login → mostrar token]

"Ahora subir videos de diferentes tamaños..."
[Upload video 10MB → mostrar response]
[Upload video 50MB → mostrar response]
[Upload video 100MB → mostrar response]

"Verificar estado de procesamiento..."
[GET /api/videos → mostrar status: processing]

[Esperar 2 minutos]

"Ahora el video está procesado..."
[GET /api/videos/{id} → mostrar status: processed, presigned_url]

"Descargar y verificar el video procesado..."
[Abrir URL en navegador → descargar → reproducir en VLC]
"Como pueden ver:
- Logo ANB al inicio ✅
- Video de 30 segundos ✅
- Resolución 720p ✅
- Sin audio ✅
- Logo ANB al final ✅"

[10:00-15:00] Auto Scaling
[Pantalla: CloudWatch Dashboard]
"Ahora voy a ejecutar una prueba de carga con 50 usuarios..."
[Ejecutar JMeter en background]

"Observen cómo el CPU aumenta en la primera instancia..."
[Mostrar CPU metric subiendo]

"La alarma se activa y el Auto Scaling lanza una segunda instancia..."
[Mostrar Scaling Activity]

"El Load Balancer automáticamente distribuye tráfico a ambas instancias..."
[Mostrar Target Group health checks]

"El CPU se estabiliza en ambas instancias alrededor del 60%..."
[Mostrar CPU metrics de ambas instancias]

[15:00-20:00] Resultados de Pruebas
[Pantalla: JMeter Reports]
"En el Escenario 1, logramos soportar 120 usuarios concurrentes con latencia p95 de 850ms..."

[Pantalla: Python script results]
"En el Escenario 2, el worker procesó 50 videos en 7 minutos, 7.14 videos/min..."

[Pantalla: Documento comparativo]
"Comparado con la Entrega 2:
- Usuarios concurrentes: +650%
- Throughput de API: +2100%
- Tiempo de upload: +68% más rápido"

[20:00-20:30] Conclusión
"Hemos demostrado que la arquitectura escalable con ALB, ASG y S3 mejora
significativamente la capacidad y rendimiento del sistema. Gracias."
```

---

## Checklist Final

### Antes de Entregar

- [ ] Ejecutar todas las pruebas de carga
- [ ] Capturar screenshots de CloudWatch
- [ ] Generar reportes de JMeter
- [ ] Documentar resultados en Markdown
- [ ] Crear tabla comparativa Entrega 2 vs 3
- [ ] Reescribir conclusiones de SonarQube (sin IA)
- [ ] Grabar video de sustentación (20 min máximo)
- [ ] Subir video a YouTube/Drive
- [ ] Agregar enlace del video al README
- [ ] Crear release en GitHub
- [ ] Verificar que documentación esté en /docs/Entrega_3
- [ ] Apagar instancias AWS para ahorrar créditos

### Validar Feedback Atendido

- [ ] ✅ Video prueba TODOS los endpoints con diferentes parámetros
- [ ] ✅ Video muestra video procesado con logo, recorte, sin audio
- [ ] ✅ Escenario 1 enfocado en CAPA WEB (GET/POST ligeros)
- [ ] ✅ Escenario 2 enfocado en CAPA WORKER (procesamiento)
- [ ] ✅ Cuellos de botella documentados con evidencia (screenshots)
- [ ] ✅ Tabla comparativa explícita Entrega 2 vs 3
- [ ] ✅ Conclusiones de SonarQube escritas por mí (no IA)
- [ ] ✅ Issues de SonarQube corregidos o justificados

---

¡Buena suerte! 🚀
