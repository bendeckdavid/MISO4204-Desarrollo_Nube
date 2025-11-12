# Postman Collection - Entrega 4 (SQS + Worker Auto Scaling)

Esta colección permite probar la plataforma de videos ANB con procesamiento asíncrono mediante SQS y auto-scaling de workers.

## 📦 Archivos

- `entrega4_postman_collection.json` - Colección de requests
- `entrega4_environment.json` - Variables de entorno

## 🚀 Cómo Usar

### 1. Importar en Postman

1. Abre Postman
2. Click en "Import"
3. Selecciona ambos archivos:
   - `entrega4_postman_collection.json`
   - `entrega4_environment.json`
4. Selecciona el environment "ANB Video Platform - Entrega 4 Environment"

### 2. Verificar URLs

Las URLs ya están configuradas con el ALB desplegado:
- **BASE_URL**: `http://anb-video-alb-1931734891.us-east-1.elb.amazonaws.com`
- **SQS_QUEUE_URL**: Cola principal de procesamiento
- **SQS_DLQ_URL**: Dead Letter Queue para mensajes fallidos

### 3. Ejecutar Requests en Orden

#### ✅ Health Check
Verifica que la API esté funcionando:
```
GET /health
```

#### 1️⃣ Signup User
Registra un nuevo usuario:
```
POST /api/auth/signup
Body:
{
  "email": "test.entrega4@example.com",
  "password": "SecurePassword123!",
  "confirm_password": "SecurePassword123!"
}
```
**Resultado**: Guarda el `USER_ID` automáticamente

#### 2️⃣ Login User
Obtiene el token de autenticación:
```
POST /api/auth/login
Body:
{
  "username": "test.entrega4@example.com",
  "password": "SecurePassword123!"
}
```
**Resultado**: Guarda el `ACCESS_TOKEN` automáticamente

#### 3️⃣ Upload Video (Queues to SQS)
Sube un video y lo envía a la cola SQS:
```
POST /api/videos/upload
Headers: Authorization: Bearer {{ACCESS_TOKEN}}
Body: multipart/form-data
  - title: "Test Video Entrega 4"
  - file: [Selecciona un archivo .mp4]
```
**Importante**:
- Selecciona un video MP4 desde tu computadora
- El video se guarda en S3
- Se envía un mensaje a SQS con el video_id
- El worker procesará el video asíncronamente

**Resultado**: Guarda el `VIDEO_ID` automáticamente

#### 4️⃣ Check Video Status
Verifica el estado del procesamiento:
```
GET /api/videos/{{VIDEO_ID}}
```
**Estados posibles**:
- `pending` - En cola SQS esperando worker
- `processing` - Worker está procesando
- `processed` - ✅ Completado exitosamente
- `failed` - ❌ Error (revisar DLQ)

**Tip**: Ejecuta este request múltiples veces para ver el progreso

#### 5️⃣ List My Videos
Lista todos tus videos:
```
GET /api/videos/my-videos
```

#### 6️⃣ List Public Videos
Lista videos procesados (sin autenticación):
```
GET /api/public/videos
```

#### 7️⃣ Vote for Video
Vota por un video procesado:
```
POST /api/public/videos/{{VIDEO_ID}}/vote
```

#### 8️⃣ Get Ranking
Obtiene el ranking por votos:
```
GET /api/public/ranking
```

## 🔍 Monitorear SQS y Workers

### Ver Cola SQS en AWS Console

1. Ve a AWS Console > SQS
2. Selecciona la cola: `anb-video-processing-queue`
3. Click en "Send and receive messages" > "Poll for messages"
4. Verás los mensajes en la cola

### Ver Workers en Auto Scaling

1. Ve a AWS Console > EC2 > Auto Scaling Groups
2. Selecciona: `anb-video-worker-asg`
3. Verás:
   - Desired capacity (1-3 instancias)
   - Current instances running
   - Scaling activities

### Ver CloudWatch Metrics

1. Ve a AWS Console > CloudWatch > Metrics
2. Busca: `AWS/SQS`
3. Métricas importantes:
   - `ApproximateNumberOfMessagesVisible` - Mensajes en cola
   - `NumberOfMessagesSent` - Mensajes enviados
   - `NumberOfMessagesDeleted` - Mensajes procesados

### Ver Logs de Workers

1. Ve a AWS Console > CloudWatch > Log groups
2. Selecciona: `/aws/ec2/anb-video-worker`
3. Verás los logs del worker procesando videos

## 📊 Pruebas de Auto Scaling

### Prueba 1: Worker Único
1. Sube 1-2 videos
2. Verifica que se procesen correctamente
3. Debe haber solo 1 worker activo

### Prueba 2: Scale Out (Múltiples Workers)
1. Sube 10-15 videos rápidamente
2. Monitorea la cola SQS (debe llenarse)
3. Espera 2-3 minutos
4. Verifica Auto Scaling Group: deben crearse 2-3 workers
5. Los videos se procesan en paralelo

### Prueba 3: Scale In (Reducción)
1. Espera a que todos los videos se procesen
2. La cola SQS debe estar vacía
3. Después de 5-10 minutos, los workers extra se terminan
4. Queda solo 1 worker activo (mínimo)

## 🆘 Troubleshooting

### Video permanece en "pending"
- **Causa**: Worker no está funcionando
- **Solución**:
  1. Ve a EC2 > Instances, verifica que haya workers corriendo
  2. Revisa logs en CloudWatch: `/aws/ec2/anb-video-worker`
  3. Verifica que SQS_QUEUE_URL esté configurada correctamente

### Video en "failed"
- **Causa**: Error durante procesamiento
- **Solución**:
  1. Ve a SQS > Dead Letter Queue: `anb-video-processing-dlq`
  2. Poll messages para ver el error
  3. Revisa logs del worker

### No se crean workers adicionales
- **Causa**: Política de scaling no se activa
- **Solución**:
  1. Sube más videos (necesitas >5 mensajes en cola)
  2. Verifica CloudWatch alarm: `TargetTracking-anb-video-worker-asg`
  3. Espera 2-3 minutos para que se active

### 401 Unauthorized
- **Causa**: Token expirado
- **Solución**: Re-ejecuta "2. Login User"

### 404 Not Found
- **Causa**: API aún no está lista o URL incorrecta
- **Solución**:
  1. Verifica health endpoint primero
  2. Espera 5-10 minutos después del deployment
  3. Verifica que BASE_URL esté correcta

## 🎯 Diferencias vs Entrega 3

| Aspecto | Entrega 3 (Celery) | Entrega 4 (SQS) |
|---------|-------------------|-----------------|
| **Cola** | Redis | Amazon SQS |
| **Workers** | 1 fijo | 1-3 auto-scaling |
| **Dead Letter** | No | SQS DLQ |
| **Multi-AZ** | No | Sí (us-east-1a, us-east-1b) |
| **Polling** | Celery beat | Long polling (20s) |
| **Escalamiento** | Manual | Automático basado en cola |

## 📝 Notas Importantes

1. **Primer video puede tardar**: El worker necesita inicializarse (~2 min)
2. **S3 Storage**: Los videos se guardan en S3, no en disco local
3. **Auto Scaling Target**: 5 mensajes por worker
4. **Cool down**: 300 segundos entre scale operations
5. **Retention**: Mensajes en cola por 4 días, DLQ por 14 días

## 🔗 Enlaces Útiles

- **ALB Health**: http://anb-video-alb-1931734891.us-east-1.elb.amazonaws.com/health
- **AWS Console SQS**: https://console.aws.amazon.com/sqs/v2/home?region=us-east-1
- **AWS Console EC2**: https://console.aws.amazon.com/ec2/v2/home?region=us-east-1
- **CloudWatch Logs**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups
