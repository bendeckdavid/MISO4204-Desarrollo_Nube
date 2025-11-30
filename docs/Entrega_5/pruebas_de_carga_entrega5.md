## Pruebas de carga. Verificación del comportamiento de auto escalado.

### 1. Crear usuarios de prueba

```bash
# Usar script existente para crear usuarios de prueba
bash capacity-planning/scripts-entrega5/setup_crear_usuarios_prueba.sh
```

Esto crea `test1@anb.com` hasta `test5@anb.com` con contraseña `Test1234!`

### 1. Probar escalado por CPU del servicio web

Usa la herramienta de pruebas de carga k6:

```bash
# Instalar k6 si no está instalado (macOS)
brew install k6

# Actualizar la URL del ALB en el script de prueba
export ALB_URL="http://anb-video-alb-1627965266.us-east-1.elb.amazonaws.com"

# Ejecutar pruebas de carga
k6 run capacity-planning/scripts-entrega5/test_escenario1_web.js \
  --vus 50 \
  --duration 5m

bash capacity-planning/scripts-entrega5/test_escenario2_worker.sh
```

### 1. Probar escalado por SQS del servicio worker

```bash
# Subir múltiples videos para llenar la cola SQS
python3 capacity-planning/scripts-entrega5/upload_videos_python.py \
  --url ${ALB_URL} \
  --user test1@anb.com \
  --password Test1234! \
  --count 20
```

---

## Estimación de costos (AWS Academy - Free Tier)

AWS Academy proporciona créditos, pero ten en cuenta el uso de recursos:

| Recurso              | Cantidad         | Uso                  | Costo estimado  |
| -------------------- | ---------------- | -------------------- | --------------- |
| ECS Fargate (Web)    | 1-3 tareas       | 0.5 vCPU, 1 GB       | $15-45/mes      |
| ECS Fargate (Worker) | 1-3 tareas       | 1 vCPU, 3 GB         | $36-108/mes     |
| RDS PostgreSQL       | 1 instancia      | db.t3.micro          | $12/mes         |
| ALB                  | 1                | Estándar             | $16/mes         |
| S3                   | 1 bucket         | Almacenamiento + req | $1-5/mes        |
| SQS                  | 2 colas          | Solicitudes          | $0.40/mes       |
| ECR                  | 2 repos          | Almacenamiento       | $1/mes          |
| CloudWatch Logs      | Múltiples flujos | Almacenamiento + ing | $5-10/mes       |
| **Total**            |                  |                      | **$86-197/mes** |

---
