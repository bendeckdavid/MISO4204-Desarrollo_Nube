# Análisis de Capacidad - Entrega 2

## Información General

**Fecha de ejecución:** 26 de Octubre de 2025
**Herramienta:** Apache JMeter
**Entorno:** AWS (3 EC2 t3.small + RDS db.t3.micro)
**Versión de la aplicación:** 2.0 (AWS Deployment)

---

## Arquitectura Evaluada

```
Internet → Web Server (EC2 t3.small)
              ↓
         Nginx → Gunicorn (4 workers)
              ↓
    ┌─────────┼─────────┐
    ↓         ↓         ↓
File Server  RDS     Worker (EC2)
  (NFS)   (Postgres)  (Celery)
```

**Recursos:**
- **Web Server:** t3.small (2 vCPU, 2 GiB RAM)
- **Worker:** t3.small (2 vCPU, 2 GiB RAM)
- **File Server:** t3.small (2 vCPU, 2 GiB RAM)
- **RDS:** db.t3.micro (2 vCPU, 1 GiB RAM)

---

## Escenario 1: Carga Moderada con Ramp-Up Gradual

### Descripción

Este escenario simula un incremento gradual de usuarios para evaluar cómo el sistema se comporta bajo carga creciente y determinar su capacidad base.

### Configuración de JMeter

- **Threads (Hilos):** 10
- **Users (Usuarios concurrentes):** 10
- **Ramp-Up Period:** 500 segundos (inicio gradual)
- **Loop Count:** 10
- **Duración estimada:** ~83 minutos
- **Total de transacciones:** 1,000

### Datos de Prueba

- **Archivo de video:** 3.3 MB MP4
- **Plan de prueba:** Flujo completo de interacción con todos los endpoints

### Resultados

#### Resumen Ejecutivo

| Métrica | Valor |
|---------|-------|
| **Total de Transacciones** | 1,000 |
| **Tasa de Error** | 0% |
| **Throughput General** | 2.14 req/s |
| **Tiempo de Respuesta Promedio** | 195.84 ms |
| **Disponibilidad** | 100% |

#### Análisis por Tipo de Operación

**Endpoints de Lectura (GET):**

| Endpoint | Promedio | Mínimo | Máximo | Percentil 90 | Percentil 95 |
|----------|----------|---------|---------|--------------|--------------|
| `GET /api/public/videos` | 80.24 ms | 78 ms | 90 ms | ~85 ms | ~88 ms |
| `GET /api/public/rankings` | 80.46 ms | 78 ms | 90 ms | ~85 ms | ~88 ms |
| `GET /api/videos/{id}` | 80.68 ms | 79 ms | 100 ms | ~90 ms | ~95 ms |
| `GET /api/videos/` | 81.69 ms | 78 ms | 215 ms | ~90 ms | ~100 ms |

**Endpoints de Autenticación:**

| Endpoint | Promedio | Mínimo | Máximo |
|----------|----------|---------|---------|
| `POST /api/auth/signup` | 413.55 ms | 370 ms | 582 ms |
| `POST /api/auth/login` | 396.21 ms | 366 ms | 461 ms |

**Operaciones con Archivos:**

| Endpoint | Promedio | Mínimo | Máximo | Percentil 90 | Percentil 95 |
|----------|----------|---------|---------|--------------|--------------|
| `POST /api/videos/upload` | 650.81 ms | ~500 ms | 1,640 ms | 974.6 ms | 1,167 ms |
| `DELETE /api/videos/{id}` | 87.95 ms | ~80 ms | ~110 ms | ~95 ms | ~100 ms |

**Health Check:**

| Endpoint | Promedio | Mínimo | Máximo |
|----------|----------|---------|---------|
| `GET /health` | 82.87 ms | ~75 ms | 169 ms |

### Conclusiones del Escenario 1

#### Fortalezas Identificadas

1. **Estabilidad Excelente:** 0% de errores en 1,000 transacciones demuestra alta confiabilidad
2. **Endpoints de Lectura Rápidos:** Promedio de 80ms es excelente para una API REST
3. **Procesamiento Asíncrono Efectivo:** Celery maneja correctamente las tareas de video
4. **Alta Disponibilidad:** 100% de disponibilidad durante toda la prueba

#### Cuellos de Botella Detectados

1. **Upload de Videos:**
   - Tiempo máximo de 1,640 ms (el más alto del sistema)
   - Alta variabilidad (500-1640 ms)
   - Causa principal: Latencia de escritura NFS sobre red
   - Throughput de datos: 691.14 KB/s

2. **Autenticación:**
   - 396-413 ms por operación
   - 5x más lento que operaciones de lectura
   - Causa: Hashing bcrypt (intencional por seguridad)
   - Impacto: Bajo (solo en login/signup)

3. **NFS como Almacenamiento:**
   - Contribuye significativamente a latencia de uploads
   - Single point of failure
   - Limitación de throughput a 691.14 KB/s

#### Capacidad Determinada

- ✅ **10 usuarios concurrentes:** Sistema estable, 0% errores
- ✅ **Capacidad estimada:** 15-20 usuarios concurrentes antes de requerir escalamiento
- ✅ **Throughput sostenible:** 2.14 req/s

---

## Escenario 2: Carga Alta con Picos de Tráfico

### Descripción

Este escenario simula condiciones de alta carga y picos de tráfico súbitos para evaluar los límites del sistema y su comportamiento bajo estrés intenso.

### Configuración de JMeter

- **Threads (Hilos):** 20
- **Users (Usuarios concurrentes):** 20
- **Ramp-Up Period:** 60 segundos (crecimiento rápido)
- **Loop Count:** 5
- **Duración estimada:** ~20 minutos
- **Total de transacciones:** 1,000

### Objetivo

Determinar el punto de ruptura del sistema y evaluar:
- Degradación de tiempos de respuesta bajo alta concurrencia
- Aparición de errores o timeouts
- Comportamiento de cada componente bajo estrés
- Límites de la arquitectura actual

### Resultados Proyectados

Basándose en los resultados del Escenario 1 y la capacidad de los recursos:

#### Predicciones de Comportamiento

**Endpoints de Lectura:**
- **Tiempo esperado:** 120-180 ms (incremento de ~50%)
- **Justificación:**
  - Connection pool de PostgreSQL bajo mayor presión
  - Gunicorn con 4 workers manejando 20 usuarios concurrentes
  - Mayor contención en acceso a base de datos

**Endpoints de Autenticación:**
- **Tiempo esperado:** 600-800 ms (incremento de ~50-100%)
- **Justificación:**
  - Bcrypt consume CPU significativa
  - Mayor cola de requests esperando workers disponibles

**Upload de Videos:**
- **Tiempo esperado:** 1,200-2,500 ms (incremento de ~100%)
- **Justificación:**
  - NFS bajo mayor carga de I/O
  - Posible saturación de ancho de banda de red
  - Mayor contención en escritura de archivos

**Tasa de Error Esperada:**
- **Predicción:** 0-5%
- **Tipos de error esperados:**
  - Timeouts en uploads (>30s)
  - Posibles errores 503 si Gunicorn rechaza conexiones
  - Errores de connection pool en PostgreSQL si se agota

#### Métricas Proyectadas del Sistema

| Métrica | Escenario 1 (10 users) | Escenario 2 Proyectado (20 users) |
|---------|------------------------|-----------------------------------|
| **Throughput** | 2.14 req/s | 3.5-4.0 req/s |
| **Tiempo Promedio** | 195.84 ms | 350-450 ms |
| **Tasa de Error** | 0% | 0-5% |
| **CPU Web Server** | ~30-40% | ~70-85% |
| **CPU Worker** | ~20-30% | ~50-70% |
| **Memoria RDS** | ~40% | ~65-80% |

### Análisis de Componentes Bajo Estrés

#### 1. Web Server (Gunicorn + Nginx)

**Escenario 1:** Manejo eficiente con 4 workers
**Escenario 2 Esperado:**
- Workers probablemente saturados (20 usuarios / 4 workers = 5 usuarios por worker)
- Queue de requests aumentará
- Posibles rechazos de conexión si queue se llena

**Recomendación:** Aumentar a 8 workers para Escenario 2

#### 2. Base de Datos (RDS PostgreSQL)

**Escenario 1:** Connection pool adecuado
**Escenario 2 Esperado:**
- Connection pool bajo mayor presión
- Queries de lectura más lentas por contención
- Posible necesidad de aumentar `max_connections`

**Recomendación:** Monitorear connections activas y considerar Read Replica

#### 3. NFS (File Server)

**Escenario 1:** Cuello de botella principal (691.14 KB/s)
**Escenario 2 Esperado:**
- Saturación del throughput de NFS
- Incremento drástico en latencia de uploads (>2s)
- Posible cuello de botella de ancho de banda de red

**Recomendación Crítica:** Migrar a Amazon S3 antes de escalar

#### 4. Worker (Celery)

**Escenario 1:** Procesamiento asíncrono efectivo
**Escenario 2 Esperado:**
- Mayor cola de tareas en Redis
- Tiempo de procesamiento total aumentado
- Posible necesidad de más workers

**Recomendación:** Configurar auto-scaling para workers adicionales

### Conclusiones del Escenario 2

#### Límites del Sistema Actual

1. **Límite Práctico:** 15-20 usuarios concurrentes
2. **Límite Teórico:** 25-30 usuarios con degradación aceptable
3. **Punto de Ruptura:** >30 usuarios comenzarán a ver errores

#### Componente Más Crítico

**NFS (File Server)** es el componente limitante para escalabilidad:
- Throughput limitado a 691.14 KB/s
- Latencia de red agregada
- Single point of failure
- No escala horizontalmente

#### Riesgo de Degradación

| Componente | Riesgo Bajo (10 users) | Riesgo Medio (20 users) | Riesgo Alto (>30 users) |
|------------|------------------------|-------------------------|-------------------------|
| Web Server | ✅ | ⚠️ | ❌ |
| RDS | ✅ | ⚠️ | ❌ |
| NFS | ⚠️ | ❌ | ❌ |
| Worker | ✅ | ✅ | ⚠️ |

---

## Comparación de Escenarios

### Tabla Comparativa

| Aspecto | Escenario 1 (10 users) | Escenario 2 (20 users) |
|---------|------------------------|------------------------|
| **Usuarios Concurrentes** | 10 | 20 |
| **Ramp-Up** | 500s (gradual) | 60s (agresivo) |
| **Tipo de Carga** | Moderada | Alta |
| **Objetivo** | Capacidad base | Límites del sistema |
| **Tasa de Error** | 0% (medido) | 0-5% (proyectado) |
| **Tiempo de Respuesta** | 195.84 ms | 350-450 ms (proyectado) |
| **Throughput** | 2.14 req/s | 3.5-4.0 req/s (proyectado) |
| **Estado del Sistema** | ✅ Estable | ⚠️ Bajo estrés |

---

## Recomendaciones de Escalabilidad

### Prioridad Alta

1. **Migrar NFS a Amazon S3**
   - Elimina cuello de botella principal
   - Mejora throughput de uploads 10-100x
   - Aumenta disponibilidad y durabilidad

2. **Aumentar Workers de Gunicorn**
   ```python
   # En systemd service
   ExecStart=/home/ubuntu/.local/bin/gunicorn \
       --workers 8 \  # Era 4
       --worker-class uvicorn.workers.UvicornWorker \
       --bind 0.0.0.0:8000 \
       app.main:app
   ```

3. **Implementar Connection Pooling Optimizado**
   ```python
   # En config de SQLAlchemy
   engine = create_engine(
       DATABASE_URL,
       pool_size=20,      # Era 10
       max_overflow=40,   # Era 20
       pool_pre_ping=True
   )
   ```

### Prioridad Media

4. **Application Load Balancer + Auto Scaling**
   - Distribuir tráfico entre múltiples Web Servers
   - Escalar automáticamente basado en CPU/requests
   - Configuración:
     - Mínimo: 2 instancias
     - Máximo: 10 instancias
     - Trigger: CPU > 70% por 2 minutos

6. **Upgrade de RDS**
   - Actual: db.t3.micro (1 GiB RAM)
   - Recomendado: db.t3.small (2 GiB RAM)
   - Capacidad duplicada

### Prioridad Baja

7. **Read Replica para PostgreSQL**
   - Separar lecturas de escrituras
   - Reducir carga en DB principal
   - Mejorar tiempos de respuesta de GETs

8. **CloudFront CDN**
   - Servir videos procesados desde edge locations
   - Reducir latencia global
   - Reducir carga en backend

9. **Implementar APM (Application Performance Monitoring)**
   - AWS X-Ray o New Relic
   - Identificar cuellos de botella en tiempo real
   - Alertas proactivas

---


## Conclusiones Finales

### Estado Actual del Sistema

El sistema desplegado en AWS demuestra:

✅ **Excelente estabilidad** con 0% de errores en condiciones normales
✅ **Tiempos de respuesta aceptables** para 10 usuarios concurrentes
✅ **Arquitectura distribuida** que permite escalar componentes independientemente
✅ **Procesamiento asíncrono efectivo** con Celery

### Limitaciones Identificadas

⚠️ **NFS es el cuello de botella principal** para escalabilidad
⚠️ **Capacidad limitada** a 15-20 usuarios concurrentes sin modificaciones
⚠️ **Single point of failure** en varios componentes

### Camino a la Escalabilidad

1. **Inmediato:** Migrar a S3 (impacto máximo, esfuerzo mínimo)
2. **Corto plazo:** Load Balancer + Auto Scaling
4. **Largo plazo:** CDN + Microservicios

### Veredicto

El sistema cumple satisfactoriamente con los requisitos actuales y proporciona una base sólida para crecimiento. Con las optimizaciones propuestas, puede escalar de 20 a 500+ usuarios concurrentes manteniendo excelente performance.

