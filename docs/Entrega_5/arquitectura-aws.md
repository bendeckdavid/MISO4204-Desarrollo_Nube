# Arquitectura AWS – Entrega 5 (ECS Fargate)

La Entrega 5 migra la plataforma de muestra de videos a contenedores gestionados en AWS ECS Fargate con autoescalado. Se mantiene el procesamiento asíncrono vía SQS y el almacenamiento en S3, con RDS PostgreSQL como base de datos administrada y un Application Load Balancer para tráfico HTTP.

```mermaid
flowchart LR
  subgraph Clients
    U["Usuarios"]
  end

  subgraph Network["VPC (Subnets públicas)"]
    ALB[("Application Load Balancer")]

    subgraph ECS["ECS Fargate Cluster"]
      WEB["Servicio Web (FastAPI)"]
      WORKER["Servicio Worker (SQS)"]
    end

    RDS[("RDS PostgreSQL")]
    S3[("S3 Bucket: uploads/processed")]
    SQS["SQS Queue"]
    DLQ["SQS DLQ"]
  end

  U --> ALB
  ALB --> WEB

  WEB --> RDS
  WEB --> S3
  WEB --> SQS
  SQS -. retries .-> DLQ

  WORKER --> SQS
  WORKER --> S3
  WORKER --> RDS
```

## Cambios desde la entrega 4

- **ECS Fargate (en lugar de EC2/ASG):**
  - Web y Worker ahora son servicios ECS Fargate. No se administran instancias EC2.
  - Se definen `TaskDefinition` por servicio y se despliegan como `Service` con `desiredCount` dinámico.
- **Auto-Scaling por servicio:**
  - Web: autoescalado basado en métrica de CPU del servicio (target ~70%).
  - Worker: autoescalado basado en profundidad de la cola SQS (ej. 5 mensajes por tarea).
- **Imágenes multi-arquitectura corregidas:**
  - Construcción y push a ECR especificando `--platform linux/amd64` para compatibilidad con Fargate.
- **CloudFormation unificado (Fargate):**
  - Nueva plantilla `docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml` que provisiona red, ALB, ECR, ECS Cluster, Services, Auto Scaling Policies, RDS, S3, SQS y logs.
- **Observabilidad:**
  - Métricas de servicio ECS (CPUUtilization) y logs en CloudWatch por cada tarea (`/ecs/anb-video-web`, `/ecs/anb-video-worker`).

## Topología

- **Clientes** → **ALB** → **Servicio Web (ECS Fargate)** → **RDS PostgreSQL**
- **Servicio Web** → **S3 (uploads/processed)**
- **Servicio Web** → **SQS (VideoProcessingQueue / DLQ)**
- **Servicio Worker (ECS Fargate)**: consume SQS, procesa con MoviePy, escribe a S3 y actualiza RDS.

## Componentes

- **Networking**
  - VPC con subnets públicas multi-AZ, IGW, rutas y SGs: ALB (80), Web (desde ALB), RDS (desde Web/Worker), Worker (sin inbound público).
- **Balanceo de carga**
  - Application Load Balancer con Target Group HTTP a puerto del contenedor (`8000`). Health checks `/health`.
- **Contenedores y orquestación**
  - ECS Cluster `anb-video-cluster`.
  - Servicios:
    - `anb-video-web-service` (FastAPI, CPU target tracking).
    - `anb-video-worker-service` (worker SQS, scaling por cola).
  - Task Definitions con variables de entorno y secretos (DB URL, `SECRET_KEY`, endpoints S3/SQS).
- **Datos**
  - RDS PostgreSQL `db.t3.micro` multi-AZ (según límites del laboratorio).
  - S3 bucket para archivos de entrada/salida (presigned URLs para descargas).
  - SQS con DLQ (reintentos automáticos, máximo 3).
- **Imagen y registro**
  - ECR: repos `anb-web`, `anb-worker`. Imágenes construidas en macOS con `--platform linux/amd64`.
- **Observabilidad**
  - CloudWatch Logs por servicio/tarea.
  - Métricas de CPU de ECS y alarma para escalado.

## Flujo asíncrono (sin cambios)

1. Upload de video → guardar en S3, registro en DB `status=pending`.
2. Envío de mensaje a SQS con `video_id`.
3. Worker recibe mensajes (long polling 20s), descarga de S3.
4. Procesa (trim, resize, watermark) y sube resultado.
5. Actualiza DB `status=completed` y borra mensaje. DLQ en errores.

## Seguridad y acceso

- **IAM:** se utiliza `LabRole`. No se crean roles adicionales.
- **Seguridad de red:** SGs limitan tráfico: ALB→Web, Web/Worker→RDS, sin acceso público directo a Worker/RDS.
- **Secretos:** parámetros en CloudFormation (`DBPassword`, `SecretKey`), evitando credenciales embebidas en imágenes de Docker.

## Despliegue y operación

- Ver archivo de instrucciones de despliegue (docs/Entrega_5/deployment/deployment-instructions.md)

## Referencias

- Archivo de despliegue: `docs/Entrega_5/deployment/deployment-instructions.md`.
- Plantilla CloudFormation: `docs/Entrega_5/deployment/cloudformation/infrastructure-fargate.yaml`.

## Comparativa Entrega 4 vs Entrega 5

La siguiente tabla resume diferencias operativas observadas bajo carga.

| Métrica                      | Entrega 4 (Web+Workers fijos)        | Entrega 5 (ECS Fargate + Target Tracking)       |
| ---------------------------- | ------------------------------------ | ----------------------------------------------- |
| Tareas Web (desiredCount)    | Fijo 1                               | 1–2 según CPU 70%                               |
| Tareas Worker (desiredCount) | Fijo 1                               | 1–3 según profundidad SQS (target 5)            |
| Cola SQS visible (pico)      | Mayor permanencia en cola            | Picos ~37 mensajes; drenaje rápido tras escalar |
| Edad del mensaje más antiguo | Puede crecer sostenidamente          | Aumenta en pico y colapsa tras drenaje          |
| Latencia API (percepción)    | Más sensible a ráfagas               | Estable por ajuste de tareas web                |

Se puede concluir que la arquitectura de esta entrega mejora la resiliencia y tiempo de procesamiento del sistema, manteniendo disponible la API y drenando la cola más rápidamente gracias al autoescalado.

## Comportamiento bajo carga (Evidencia)

Las capturas de pantalla que evidencian la operación se encuentran en la carpeta docs/Entrega_5/images.

**Resumen operacional**

- La política de CPU del servicio web mantiene latencia estable ajustando tareas entre 1–2.
- La política de profundidad de SQS en el Worker Service escala de 1 a 3 tareas, drenando la cola de mensajes eficientemente.
- Las métricas de SQS y los artefactos en S3 prueban procesamiento correcto sin bloqueos en la API.
- El clúster ECS muestra servicios activos, despliegues en `Completed` y tareas corriendo de acuerdo con las políticas de escalemiento establecidas en la configuración de AWS Clodformation.

**Conclusiones**

- El autoescalado (web por CPU, worker por cola) opera correctamente para absorber picos de carga.
- El tiempo de reacción del worker ante aumentos de cola y la posterior reducción (`desiredCount=1`) optimiza el costo y mantiene siempre disponible el servicio.
- La combinación SQS + DLQ asegura robustez ante fallos; no se evidenciaron mensajes perdidos durante las pruebas.