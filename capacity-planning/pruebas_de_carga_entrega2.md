# Análisis de Capacidad - Entrega 2

## Información General

- **Proyecto**: ANB Rising Stars Showcase API
- **Entrega**: 2 - Despliegue en AWS
- **Fecha**: [Completar con fecha de ejecución]
- **Responsable**: [Nombre del equipo]

---

## Tabla de Contenidos

- [Resumen Ejecutivo](#resumen-ejecutivo)
- [Infraestructura de Pruebas](#infraestructura-de-pruebas)
- [Herramientas Utilizadas](#herramientas-utilizadas)
- [Escenario 1: [Nombre del Escenario]](#escenario-1-nombre-del-escenario)
- [Escenario 2: [Nombre del Escenario]](#escenario-2-nombre-del-escenario)
- [Análisis Comparativo](#análisis-comparativo)
- [Conclusiones](#conclusiones)
- [Recomendaciones de Escalabilidad](#recomendaciones-de-escalabilidad)

---

## Resumen Ejecutivo

[Completar con un resumen de 2-3 párrafos que incluya:]
- Objetivo de las pruebas de carga
- Infraestructura evaluada (AWS con 3 EC2 + RDS)
- Principales hallazgos
- Conclusión general sobre capacidad actual

**Resultados Rápidos:**

| Métrica | Escenario 1 | Escenario 2 | Objetivo |
|---------|-------------|-------------|----------|
| Throughput (req/s) | [Completar] | [Completar] | [Completar] |
| Tiempo de respuesta P95 | [Completar] | [Completar] | < 500ms |
| Tasa de error | [Completar] | [Completar] | < 1% |
| CPU Web Server | [Completar] | [Completar] | < 80% |
| Usuarios concurrentes soportados | [Completar] | [Completar] | [Completar] |

---

## Infraestructura de Pruebas

### Arquitectura AWS Evaluada

```
                    ┌──────────────┐
                    │  Internet    │
                    └──────┬───────┘
                           │
                           ▼
             ┌─────────────────────────┐
             │  EC2 Web Server         │
             │  - FastAPI + Gunicorn   │
             │  - Nginx (puerto 8080)  │
             │  - Redis                │
             │  t3.small: 2vCPU, 2GB   │
             └─────────┬───────────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
         ▼             ▼             ▼
    ┌────────┐   ┌─────────┐   ┌──────────┐
    │  NFS   │   │   RDS   │   │  Worker  │
    │ Server │   │ Postgres│   │  Celery  │
    │t3.small│   │ t3.micro│   │ t3.small │
    └────────┘   └─────────┘   └──────────┘
```

### Especificaciones de Instancias

| Componente | Tipo | vCPUs | RAM | Storage | Ubicación |
|------------|------|-------|-----|---------|-----------|
| **Web Server** | EC2 t3.small | 2 | 2 GiB | 50 GiB gp3 | us-east-1a |
| **Worker** | EC2 t3.small | 2 | 2 GiB | 50 GiB gp3 | us-east-1a |
| **File Server** | EC2 t3.small | 2 | 2 GiB | 50 GiB gp3 | us-east-1a |
| **Database** | RDS db.t3.micro | 2 | 1 GiB | 20 GiB gp3 | us-east-1 (Multi-subnet) |

### Configuración de la Aplicación

```bash
# Gunicorn Workers
WORKERS=4
WORKER_CLASS=uvicorn.workers.UvicornWorker
WORKER_CONNECTIONS=1000

# PostgreSQL Connection Pool (por worker)
POOL_SIZE=10
MAX_OVERFLOW=20
POOL_TIMEOUT=30

# Celery Worker
CELERY_CONCURRENCY=2
MAX_TASKS_PER_CHILD=50
TASK_TIME_LIMIT=600
```

### Red y Seguridad

- **VPC**: 10.0.0.0/16
- **Subnet**: ANB-Public-Subnet-1 (10.0.1.0/24)
- **Security Groups**: Configurados según [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)
- **Acceso**: IP pública del Web Server en puerto 8080

---

## Herramientas Utilizadas

### K6 (Grafana)

**Versión**: [Especificar versión]

**Justificación**: Herramienta moderna de testing de performance, escrita en Go, con scripting en JavaScript. Ideal para APIs REST.

**Características utilizadas:**
- Virtual Users (VUs) para simular usuarios concurrentes
- Stages para ramping up/down de carga
- Thresholds para definir SLOs
- Checks para validar respuestas
- Métricas personalizadas

### Newman (Postman CLI)

**Versión**: [Especificar versión]

**Uso**: Validación funcional de endpoints antes de pruebas de carga

```bash
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --delay-request 500
```

### Monitoreo durante Pruebas

**CloudWatch Metrics:**
- CPU Utilization (EC2 y RDS)
- Network In/Out
- Disk I/O
- Memory utilization (con CloudWatch Agent)

**Logs:**
```bash
# Logs de aplicación
ssh -i anb-key-pair.pem ubuntu@<WEB_SERVER_IP>
sudo journalctl -u fastapi -f

# Logs de Celery
ssh -i anb-key-pair.pem ubuntu@<WORKER_IP>
sudo journalctl -u celery -f

# Logs de PostgreSQL
# Desde AWS Console → RDS → Logs
```

---

## Escenario 1: [Nombre del Escenario]

> **Ejemplo de nombre**: "Carga Sostenida de Consultas de Lectura"

### Descripción

[Describir el escenario, por ejemplo:]
- Simular usuarios consultando rankings y videos públicos
- Patrón de carga constante durante 10 minutos
- No incluye uploads de videos (solo lectura)

### Objetivos

- **Objetivo 1**: Determinar el throughput máximo de lecturas sostenido
- **Objetivo 2**: Identificar el número de usuarios concurrentes antes de degradación
- **Objetivo 3**: Medir latencia percentil 95 y 99

### Configuración del Test

#### Endpoints Evaluados

| Endpoint | Método | Operación | Peso |
|----------|--------|-----------|------|
| `/api/public/videos` | GET | Listar videos públicos | 40% |
| `/api/public/rankings` | GET | Ver rankings | 30% |
| `/api/videos/` | GET | Listar mis videos (auth) | 20% |
| `/api/videos/{id}` | GET | Ver detalle de video | 10% |

#### Script K6

```javascript
// escenario1.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
  stages: [
    { duration: '2m', target: 20 },   // Ramp-up a 20 usuarios
    { duration: '5m', target: 20 },   // Mantener 20 usuarios
    { duration: '2m', target: 50 },   // Ramp-up a 50 usuarios
    { duration: '5m', target: 50 },   // Mantener 50 usuarios
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<1000'],
    http_req_failed: ['rate<0.01'],  // < 1% de errores
  },
};

const BASE_URL = 'http://<WEB_SERVER_IP>:8080';

export default function () {
  // 40% - Listar videos públicos
  if (Math.random() < 0.4) {
    let res = http.get(`${BASE_URL}/api/public/videos?page=1&page_size=10`);
    check(res, {
      'videos status 200': (r) => r.status === 200,
      'videos response time OK': (r) => r.timings.duration < 500,
    });
  }

  // 30% - Ver rankings
  else if (Math.random() < 0.7) {
    let res = http.get(`${BASE_URL}/api/public/rankings?page=1&page_size=20`);
    check(res, {
      'rankings status 200': (r) => r.status === 200,
    });
  }

  // 20% - Listar mis videos (con auth)
  else if (Math.random() < 0.9) {
    let token = '<TOKEN>';  // Obtener de login previo
    let res = http.get(`${BASE_URL}/api/videos/`, {
      headers: { 'Authorization': `Bearer ${token}` },
    });
    check(res, {
      'my videos status 200': (r) => r.status === 200,
    });
  }

  // 10% - Ver detalle de video
  else {
    let videoId = '<VIDEO_ID>';  // ID de video existente
    let res = http.get(`${BASE_URL}/api/videos/${videoId}`);
    check(res, {
      'video detail status 200': (r) => r.status === 200,
    });
  }

  sleep(1);  // Think time de 1 segundo
}
```

#### Ejecución

```bash
# Instalar K6
curl https://github.com/grafana/k6/releases/download/v0.47.0/k6-v0.47.0-linux-amd64.tar.gz -L | tar xvz
sudo mv k6-v0.47.0-linux-amd64/k6 /usr/local/bin/

# Ejecutar test
k6 run --out json=results-escenario1.json escenario1.js

# Generar reporte HTML
k6 run --out json=results-escenario1.json escenario1.js | \
  k6-reporter --output escenario1-report.html
```

### Resultados

#### Métricas Generales

| Métrica | Valor | Objetivo | Estado |
|---------|-------|----------|--------|
| **Requests totales** | [Completar] | - | - |
| **Throughput promedio** | [X] req/s | > 100 req/s | [✅/❌] |
| **Throughput máximo** | [X] req/s | - | - |
| **Duración total** | [X] minutos | 16 min | - |
| **Datos transferidos** | [X] MB | - | - |

#### Tiempos de Respuesta

| Percentil | Valor | Objetivo | Estado |
|-----------|-------|----------|--------|
| **P50 (mediana)** | [X] ms | < 200 ms | [✅/❌] |
| **P90** | [X] ms | < 400 ms | [✅/❌] |
| **P95** | [X] ms | < 500 ms | [✅/❌] |
| **P99** | [X] ms | < 1000 ms | [✅/❌] |
| **Máximo** | [X] ms | - | - |

#### Tasa de Errores

| Tipo de Error | Cantidad | Porcentaje |
|---------------|----------|------------|
| **HTTP 5xx** | [X] | [X]% |
| **HTTP 4xx** | [X] | [X]% |
| **Timeouts** | [X] | [X]% |
| **Conexiones fallidas** | [X] | [X]% |
| **Total exitosos** | [X] | [X]% |

#### Utilización de Recursos

##### Web Server (EC2)

| Recurso | Promedio | Pico | Límite | Utilización |
|---------|----------|------|--------|-------------|
| **CPU** | [X]% | [X]% | 100% | [X]% |
| **Memoria** | [X] MB | [X] MB | 2048 MB | [X]% |
| **Network In** | [X] Mbps | [X] Mbps | ~5 Gbps | [X]% |
| **Network Out** | [X] Mbps | [X] Mbps | ~5 Gbps | [X]% |
| **Disk I/O** | [X] IOPS | [X] IOPS | 3000 IOPS | [X]% |

##### RDS PostgreSQL

| Métrica | Promedio | Pico | Observaciones |
|---------|----------|------|---------------|
| **CPU** | [X]% | [X]% | [Comentarios] |
| **Conexiones** | [X] | [X] | Max: ~100 |
| **Read IOPS** | [X] | [X] | [Comentarios] |
| **Write IOPS** | [X] | [X] | [Comentarios] |
| **Read Latency** | [X] ms | [X] ms | [Comentarios] |
| **Write Latency** | [X] ms | [X] ms | [Comentarios] |

#### Gráficas

[Insertar capturas de pantalla o gráficas de:]
1. **Throughput a lo largo del tiempo**
2. **Tiempo de respuesta (P50, P95, P99)**
3. **Utilización de CPU (Web Server y RDS)**
4. **Tasa de errores**
5. **Usuarios virtuales a lo largo del test**

### Análisis

#### Observaciones Clave

1. [Observación 1, ejemplo:]
   - El throughput se mantuvo estable en ~150 req/s con 20 usuarios
   - Con 50 usuarios, el throughput solo aumentó a ~180 req/s

2. [Observación 2, ejemplo:]
   - La latencia P95 se mantuvo bajo 300ms hasta 40 usuarios concurrentes
   - A partir de 45 usuarios, la latencia P95 superó los 500ms

3. [Observación 3, ejemplo:]
   - CPU del Web Server alcanzó 85% con 50 usuarios
   - CPU de RDS se mantuvo bajo 40% en todo momento

#### Cuellos de Botella Identificados

1. **[Nombre del cuello de botella]**
   - **Componente afectado**: [Web Server / RDS / Network / etc.]
   - **Síntoma**: [Descripción]
   - **Evidencia**: [Métricas que lo demuestran]
   - **Impacto**: [Cómo afecta al rendimiento general]

2. **[Otro cuello de botella]**
   - ...

### Conclusiones del Escenario 1

[Redactar conclusiones específicas de este escenario:]
- Capacidad máxima identificada
- Componente limitante
- Comportamiento bajo carga sostenida
- Cumplimiento de objetivos

**Capacidad recomendada para producción**: [X] usuarios concurrentes con margen de [X]%

---

## Escenario 2: [Nombre del Escenario]

> **Ejemplo de nombre**: "Upload y Procesamiento Concurrente de Videos"

### Descripción

[Describir el escenario, por ejemplo:]
- Simular usuarios subiendo videos para procesamiento
- Incluye operaciones de escritura pesadas (archivos, DB, NFS)
- Evaluar capacidad del Worker para procesar videos en paralelo
- Patrón de carga incremental con picos

### Objetivos

- **Objetivo 1**: Determinar cuántos videos se pueden procesar por hora
- **Objetivo 2**: Medir tiempo de procesamiento end-to-end
- **Objetivo 3**: Identificar límites del Worker y NFS

### Configuración del Test

#### Endpoints Evaluados

| Endpoint | Método | Operación | Peso |
|----------|--------|-----------|------|
| `/api/videos/upload` | POST | Upload de video | 60% |
| `/api/videos/` | GET | Verificar estado | 30% |
| `/api/videos/{id}` | GET | Ver video procesado | 10% |

#### Video de Prueba

- **Formato**: MP4 (H.264)
- **Tamaño**: [X] MB
- **Duración**: [X] segundos
- **Resolución**: [X]x[X]

#### Script K6

```javascript
// escenario2.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';

export let options = {
  stages: [
    { duration: '1m', target: 5 },    // Warm-up
    { duration: '5m', target: 10 },   // Carga moderada
    { duration: '2m', target: 20 },   // Pico de carga
    { duration: '5m', target: 10 },   // Bajar a carga moderada
    { duration: '1m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    'http_req_duration{endpoint:upload}': ['p(95)<3000'],
    'http_req_duration{endpoint:status}': ['p(95)<500'],
    http_req_failed: ['rate<0.05'],  // < 5% de errores
  },
};

const BASE_URL = 'http://<WEB_SERVER_IP>:8080';
const VIDEO_FILE = open('./test-video.mp4', 'b');

export default function () {
  let token = '<TOKEN>';  // Token de autenticación

  // 60% - Upload de video
  if (Math.random() < 0.6) {
    const formData = {
      file: http.file(VIDEO_FILE, 'test-video.mp4', 'video/mp4'),
      title: `Video Test ${__VU}-${__ITER}`,
      description: 'Video de prueba de carga',
    };

    let res = http.post(`${BASE_URL}/api/videos/upload`, formData, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      tags: { endpoint: 'upload' },
    });

    check(res, {
      'upload status 202': (r) => r.status === 202,
      'upload has video_id': (r) => r.json('id') !== undefined,
    });

    sleep(3);  // Esperar antes de siguiente acción
  }

  // 30% - Verificar estado de videos
  else if (Math.random() < 0.9) {
    let res = http.get(`${BASE_URL}/api/videos/`, {
      headers: { 'Authorization': `Bearer ${token}` },
      tags: { endpoint: 'status' },
    });
    check(res, { 'list videos status 200': (r) => r.status === 200 });
    sleep(2);
  }

  // 10% - Ver video específico
  else {
    let videoId = '<EXISTING_VIDEO_ID>';
    let res = http.get(`${BASE_URL}/api/videos/${videoId}`, {
      headers: { 'Authorization': `Bearer ${token}` },
      tags: { endpoint: 'detail' },
    });
    check(res, { 'video detail status 200': (r) => r.status === 200 });
    sleep(2);
  }
}
```

#### Ejecución

```bash
# Preparar video de prueba
wget https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_1mb.mp4 \
  -O test-video.mp4

# Ejecutar test
k6 run --out json=results-escenario2.json escenario2.js
```

### Resultados

[Similar estructura al Escenario 1, completar con:]

#### Métricas Generales

| Métrica | Valor | Objetivo | Estado |
|---------|-------|----------|--------|
| **Videos subidos totales** | [X] | - | - |
| **Videos procesados** | [X] | - | - |
| **Videos fallidos** | [X] | < 5% | [✅/❌] |
| **Throughput de uploads** | [X] videos/min | > 10/min | [✅/❌] |
| **Tiempo promedio de procesamiento** | [X] segundos | < 60s | [✅/❌] |

#### Tiempos de Respuesta por Endpoint

| Endpoint | P50 | P95 | P99 | Max |
|----------|-----|-----|-----|-----|
| **POST /upload** | [X]ms | [X]ms | [X]ms | [X]ms |
| **GET /videos/** | [X]ms | [X]ms | [X]ms | [X]ms |
| **GET /videos/{id}** | [X]ms | [X]ms | [X]ms | [X]ms |

#### Utilización de Recursos

##### Worker (EC2)

| Recurso | Promedio | Pico | Observaciones |
|---------|----------|------|---------------|
| **CPU** | [X]% | [X]% | [Comentarios sobre FFmpeg] |
| **Memoria** | [X] MB | [X] MB | [Comentarios] |
| **Disk Read** | [X] MB/s | [X] MB/s | Leyendo desde NFS |
| **Disk Write** | [X] MB/s | [X] MB/s | Escribiendo a NFS |

##### File Server (NFS)

| Métrica | Promedio | Pico | Observaciones |
|---------|----------|------|---------------|
| **CPU** | [X]% | [X]% | [Comentarios] |
| **Network In** | [X] MB/s | [X] MB/s | Escritura de uploads |
| **Network Out** | [X] MB/s | [X] MB/s | Lectura para procesamiento |
| **Disk I/O** | [X] IOPS | [X] IOPS | [Comentarios] |

#### Cola de Celery

| Métrica | Valor | Observaciones |
|---------|-------|---------------|
| **Tareas encoladas (pico)** | [X] | [Comentarios] |
| **Tiempo promedio en cola** | [X] segundos | [Comentarios] |
| **Tareas completadas** | [X] | [Comentarios] |
| **Tareas fallidas** | [X] | [Comentarios] |

#### Gráficas

[Insertar capturas de pantalla de:]
1. **Velocidad de procesamiento (videos/min)**
2. **Cola de Celery a lo largo del tiempo**
3. **CPU del Worker durante procesamiento**
4. **Throughput de NFS (lectura/escritura)**
5. **Tiempo de procesamiento por video**

### Análisis

[Similar al Escenario 1, enfocándose en:]
- Capacidad de procesamiento del Worker
- Comportamiento de la cola de Celery
- Performance de NFS bajo escritura/lectura concurrente
- Cuellos de botella en FFmpeg

### Conclusiones del Escenario 2

[Conclusiones específicas sobre:]
- Videos por hora que se pueden procesar
- Limitaciones del Worker actual
- Impacto del NFS en el performance
- Recomendaciones para aumentar capacidad de procesamiento

---

## Análisis Comparativo

### Comparación con Entrega 1 (Docker Local)

| Aspecto | Entrega 1 (Local) | Entrega 2 (AWS) | Cambio |
|---------|-------------------|-----------------|--------|
| **Throughput lecturas** | [X] req/s | [X] req/s | [+X%] |
| **Latencia P95 lecturas** | [X] ms | [X] ms | [+X%] |
| **Videos procesados/hora** | [X] | [X] | [+X%] |
| **Tiempo procesamiento** | [X]s | [X]s | [+X%] |
| **Usuarios concurrentes** | [X] | [X] | [+X%] |
| **CPU usage bajo carga** | [X]% | [X]% | [+X%] |

### Análisis de Cambios

#### Mejoras Observadas

1. **[Aspecto mejorado]**
   - **Razón**: [Explicación técnica]
   - **Impacto cuantitativo**: [Datos]

2. **[Otro aspecto mejorado]**
   - ...

#### Degradaciones Observadas

1. **[Aspecto degradado]**
   - **Razón**: [Explicación técnica]
   - **Impacto cuantitativo**: [Datos]
   - **Plan de mitigación**: [Qué hacer al respecto]

### Impacto de la Arquitectura AWS

#### Beneficios

- ✅ [Beneficio 1]: [Explicación]
- ✅ [Beneficio 2]: [Explicación]

#### Limitaciones

- ⚠️ [Limitación 1]: [Explicación]
- ⚠️ [Limitación 2]: [Explicación]

---

## Conclusiones

### Capacidad Actual

#### Lecturas (Escenario 1)

- **Usuarios concurrentes**: [X] usuarios con latencia P95 < 500ms
- **Throughput máximo**: [X] req/s
- **Cuello de botella primario**: [Componente y razón]
- **Margen de crecimiento**: [X]% antes de degradación significativa

#### Escrituras y Procesamiento (Escenario 2)

- **Videos por hora**: [X] con un Worker
- **Tiempo de procesamiento**: [X] segundos en promedio
- **Cuello de botella primario**: [Componente y razón]
- **Capacidad máxima de cola**: [X] tareas antes de saturación

### Componente Limitante

El componente que primero alcanza su límite es: **[Nombre del componente]**

**Evidencia:**
- [Métrica 1]: [Valor y por qué es limitante]
- [Métrica 2]: [Valor y por qué es limitante]

**Impacto en arquitectura:**
[Explicar cómo este componente limita la capacidad general del sistema]

### Cumplimiento de Requisitos Funcionales

| Requisito | Escenario | Resultado | Estado |
|-----------|-----------|-----------|--------|
| Autenticación funciona bajo carga | 1 | [X]% éxito | [✅/❌] |
| Upload de videos concurrente | 2 | [X]% éxito | [✅/❌] |
| Procesamiento de videos | 2 | [X]% éxito | [✅/❌] |
| Consultas públicas sin degradación | 1 | P95 < 500ms | [✅/❌] |
| Rankings accesibles | 1 | [X]% éxito | [✅/❌] |

---

## Recomendaciones de Escalabilidad

### Corto Plazo (1-3 meses)

#### Recomendación 1: [Título]

**Problema**: [Descripción del problema actual]

**Solución propuesta**: [Descripción de la solución]

**Componentes afectados**:
- [Componente 1]
- [Componente 2]

**Implementación**:
```bash
# Ejemplo de comandos o configuración
```

**Impacto esperado**:
- Incremento de capacidad: [X]%
- Costo adicional: $[X]/mes
- Tiempo de implementación: [X] horas/días

**Prioridad**: [Alta / Media / Baja]

#### Recomendación 2: [Título]

[Similar estructura...]

### Mediano Plazo (3-6 meses)

#### Recomendación 3: Implementar Auto Scaling

**Problema**: Capacidad fija no se ajusta a demanda variable

**Solución propuesta**:
1. Configurar Auto Scaling Group para Web Servers
   - Min: 2, Max: 6, Desired: 2
   - Scale-out cuando CPU > 70% por 5 minutos
   - Scale-in cuando CPU < 30% por 10 minutos

2. Separar Redis a ElastiCache
   - cache.t3.small con modo cluster
   - Automatic failover habilitado

3. Agregar Application Load Balancer
   - Distribuir tráfico entre Web Servers
   - Health checks cada 30 segundos

**Costo adicional**: ~$150/mes
**Capacidad adicional**: +200% (hasta 6 Web Servers)
**Implementación**: 2-3 días

#### Recomendación 4: Migrar almacenamiento a S3

**Problema**: NFS es single point of failure y limita escalabilidad

**Solución propuesta**:
1. Almacenar uploads en S3 bucket
2. Procesados en S3 con versionado
3. CloudFront CDN para servir videos
4. Eliminar File Server EC2

**Beneficios**:
- Almacenamiento ilimitado
- CDN global (baja latencia)
- Alta disponibilidad (99.99%)
- Costo-efectivo para archivos

**Costo**: Variable según uso, estimado $30-50/mes inicialmente
**Ahorro**: -$25/mes (eliminar File Server EC2)

### Largo Plazo (6-12 meses)

#### Recomendación 5: Multi-Region Deployment

[Descripción de arquitectura multi-región...]

#### Recomendación 6: Migrar a contenedores (ECS/EKS)

[Descripción de migración a Kubernetes...]

### Priorización de Recomendaciones

| Recomendación | Impacto en Capacidad | Costo | Complejidad | Prioridad |
|---------------|----------------------|-------|-------------|-----------|
| 1. [Nombre] | +[X]% | $[X]/mes | Baja | **Alta** |
| 2. [Nombre] | +[X]% | $[X]/mes | Media | **Alta** |
| 3. Auto Scaling | +200% | $150/mes | Media | Media |
| 4. S3 + CDN | Ilimitado | $50/mes | Media | Media |
| 5. Multi-Region | +300% | $400/mes | Alta | Baja |
| 6. EKS | Variable | $200+/mes | Alta | Baja |

### Roadmap Sugerido

```
Mes 1-3:  [Recomendaciones de alta prioridad]
Mes 3-6:  [Auto Scaling + S3]
Mes 6-12: [Multi-Region si el volumen lo justifica]
```

### Métricas para Decidir Escalar

**Indicadores de que es momento de escalar:**
- CPU del Web Server > 70% sostenido por > 1 hora
- Latencia P95 > 500ms de forma consistente
- Cola de Celery > 20 tareas por > 30 minutos
- Usuarios concurrentes > [X] de forma regular
- Tasa de error > 1%

**Herramientas de monitoreo recomendadas:**
- CloudWatch Dashboards con métricas clave
- CloudWatch Alarms para umbrales críticos
- Application Performance Monitoring (APM): New Relic, Datadog, o similar

---

## Anexos

### A. Configuración Completa de K6

[Incluir scripts completos si no fueron incluidos arriba]

### B. Capturas de CloudWatch

[Incluir screenshots de métricas relevantes durante las pruebas]

### C. Logs Relevantes

[Incluir extractos de logs que muestren errores o comportamientos interesantes]

### D. Comandos de Ejecución

```bash
# Preparación
[Comandos usados para preparar el entorno]

# Ejecución de pruebas
[Comandos exactos usados]

# Recolección de resultados
[Comandos para extraer métricas]
```

---

**Documento generado**: [Fecha]
**Responsable**: [Nombre]
**Versión**: 1.0
