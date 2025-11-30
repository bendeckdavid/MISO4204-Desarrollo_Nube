#!/bin/bash

##############################################################################
# Escenario 2: Worker Auto Scaling basado en profundidad de cola SQS
#
# Objetivo: Demostrar que el Worker escala automáticamente de 1 a 3
# instancias basándose en la profundidad de la cola SQS.
#
# Estrategia:
# 1. Subir 12 videos rápidamente para llenar la cola SQS
# 2. Monitorear la profundidad de cola usando la consola de AWS
# 3. Observar el escalado automático del Worker ASG (1 → 2 → 3 workers)
##############################################################################

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuración
ALB_DNS="${ALB_DNS:-http://anb-video-alb-1059958631.us-east-1.elb.amazonaws.com}"
SQS_QUEUE_URL="${SQS_QUEUE_URL:-https://sqs.us-east-1.amazonaws.com/240377264548/anb-video-processing-queue}"
WORKER_ASG_NAME="${WORKER_ASG_NAME:-anb-video-worker-asg}"
NUM_VIDEOS=12  # Suficientes para trigger scaling (5 msgs/worker = target)
VIDEO_FILE="/home/juan-perdomo/Descargas/video_example.mp4"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Escenario 2: Worker Auto Scaling con SQS - Entrega 4${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📋 Configuración:${NC}"
echo "   ALB DNS: $ALB_DNS"
echo "   SQS Queue: $SQS_QUEUE_URL"
echo "   Worker ASG: $WORKER_ASG_NAME"
echo "   Videos a subir: $NUM_VIDEOS"
echo ""

# Función para obtener profundidad de cola SQS
get_queue_depth() {
    aws sqs get-queue-attributes \
        --queue-url "$SQS_QUEUE_URL" \
        --attribute-names ApproximateNumberOfMessagesVisible \
        --query 'Attributes.ApproximateNumberOfMessagesVisible' \
        --output text 2>/dev/null || echo "0"
}

# Función para obtener número de workers activos
get_worker_count() {
    aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names "$WORKER_ASG_NAME" \
        --query 'AutoScalingGroups[0].DesiredCapacity' \
        --output text 2>/dev/null || echo "0"
}

# Función para obtener capacidad deseada del ASG
get_asg_status() {
    aws autoscaling describe-auto-scaling-groups \
        --auto-scaling-group-names "$WORKER_ASG_NAME" \
        --query 'AutoScalingGroups[0].[DesiredCapacity,MinSize,MaxSize,length(Instances)]' \
        --output text 2>/dev/null
}

# Paso 1: Crear video de prueba si no existe
echo -e "${YELLOW}📹 Paso 1: Preparando video de prueba...${NC}"
if [ ! -f "$VIDEO_FILE" ]; then
    # Crear un video de prueba simple (5 segundos, 640x480)
    if command -v ffmpeg &> /dev/null; then
        ffmpeg -f lavfi -i testsrc=duration=5:size=640x480:rate=30 \
            -pix_fmt yuv420p "$VIDEO_FILE" -y &>/dev/null
        echo -e "${GREEN}   ✓ Video de prueba creado ($(du -h $VIDEO_FILE | cut -f1))${NC}"
    else
        echo -e "${RED}   ✗ ffmpeg no está instalado. Por favor instálalo o proporciona un video.${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}   ✓ Video de prueba ya existe ($(du -h $VIDEO_FILE | cut -f1))${NC}"
fi
echo ""

# Paso 2: Login y obtener token
echo -e "${YELLOW}🔐 Paso 2: Autenticando...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$ALB_DNS/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test1@anb.com","password":"Test123!"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

if [ -z "$TOKEN" ]; then
    echo -e "${RED}   ✗ Error al obtener token de autenticación${NC}"
    echo "   Respuesta: $LOGIN_RESPONSE"
    exit 1
fi
echo -e "${GREEN}   ✓ Token obtenido exitosamente${NC}"
echo ""

# Paso 3: Verificar estado inicial de la cola y workers
echo -e "${YELLOW}📊 Paso 3: Estado inicial del sistema...${NC}"
INITIAL_QUEUE_DEPTH=$(get_queue_depth)
INITIAL_WORKER_COUNT=$(get_worker_count)
echo "   Mensajes en cola: $INITIAL_QUEUE_DEPTH"
echo "   Workers activos: $INITIAL_WORKER_COUNT"
echo ""

# Paso 4: Subir múltiples videos rápidamente
echo -e "${YELLOW}📤 Paso 4: Subiendo $NUM_VIDEOS videos...${NC}"
echo "   (Esto llenará la cola SQS y debería triggear el auto scaling)"
echo ""

START_TIME=$(date +%s)
SUCCESS_COUNT=0
FAILED_COUNT=0

for i in $(seq 1 $NUM_VIDEOS); do
    printf "   [%2d/%2d] Subiendo video... " "$i" "$NUM_VIDEOS"

    RESPONSE=$(curl -s -w "\n%{http_code}" "$ALB_DNS/api/videos/upload" \
        -H "Authorization: Bearer $TOKEN" \
        -F "file=@$VIDEO_FILE;type=video/mp4;filename=test_video_$i.mp4" \
        -F "title=Test Video $i - Auto Scaling" \
        -F "description=Worker Auto Scaling Test - Entrega 4")

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)

    if [ "$HTTP_CODE" = "201" ] || [ "$HTTP_CODE" = "200" ]; then
        echo -e "${GREEN}✓${NC}"
        ((SUCCESS_COUNT++))
    else
        echo -e "${RED}✗ (HTTP $HTTP_CODE)${NC}"
        ((FAILED_COUNT++))
    fi

    # Pequeña pausa para no saturar (0.5 segundos)
    sleep 0.5
done

UPLOAD_END_TIME=$(date +%s)
UPLOAD_DURATION=$((UPLOAD_END_TIME - START_TIME))

echo ""
echo -e "${GREEN}✓ Uploads completados en ${UPLOAD_DURATION}s${NC}"
echo "   Exitosos: $SUCCESS_COUNT"
echo "   Fallidos: $FAILED_COUNT"
echo ""

# Paso 5: Monitorear profundidad de cola y escalado de workers
echo -e "${YELLOW}📈 Paso 5: Monitoreando Auto Scaling (próximos 10 minutos)...${NC}"
echo "   Configuración: Target 5 mensajes/worker, Min 1, Max 3"
echo ""
echo "   Comportamiento esperado:"
echo "   - 0-5 mensajes  → 1 worker"
echo "   - 6-10 mensajes → 2 workers"
echo "   - 11+ mensajes  → 3 workers"
echo ""

# Header de la tabla
printf "%-8s %-12s %-20s %-25s %-15s\n" "Tiempo" "Cola SQS" "Workers (Desired)" "Estado ASG" "Observación"
echo "─────────────────────────────────────────────────────────────────────────────────────────────────"

MONITORING_START=$(date +%s)
MAX_MONITORING_TIME=600  # 10 minutos
CHECK_INTERVAL=15        # Cada 15 segundos

PEAK_QUEUE_DEPTH=0
MAX_WORKERS_REACHED=0
SCALE_UP_DETECTED=0

while true; do
    CURRENT_TIME=$(date +%s)
    ELAPSED=$((CURRENT_TIME - MONITORING_START))

    if [ $ELAPSED -gt $MAX_MONITORING_TIME ]; then
        echo ""
        echo -e "${BLUE}⏰ Tiempo máximo de monitoreo alcanzado (10 minutos)${NC}"
        break
    fi

    # Obtener métricas actuales
    QUEUE_DEPTH=$(get_queue_depth)
    ASG_STATUS=$(get_asg_status)
    DESIRED_CAPACITY=$(echo "$ASG_STATUS" | awk '{print $1}')
    CURRENT_INSTANCES=$(echo "$ASG_STATUS" | awk '{print $4}')

    # Track peak queue depth
    if [ "$QUEUE_DEPTH" -gt "$PEAK_QUEUE_DEPTH" ]; then
        PEAK_QUEUE_DEPTH=$QUEUE_DEPTH
    fi

    # Track max workers
    if [ "$DESIRED_CAPACITY" -gt "$MAX_WORKERS_REACHED" ]; then
        MAX_WORKERS_REACHED=$DESIRED_CAPACITY
        if [ "$DESIRED_CAPACITY" -gt 1 ]; then
            SCALE_UP_DETECTED=1
        fi
    fi

    # Determinar observación
    OBSERVATION=""
    if [ "$QUEUE_DEPTH" -eq 0 ]; then
        OBSERVATION="Cola vacía"
        if [ "$DESIRED_CAPACITY" -eq 1 ]; then
            echo ""
            echo -e "${GREEN}✓ Test completado: Cola procesada, workers volviendo a mínimo${NC}"
            break
        fi
    elif [ "$QUEUE_DEPTH" -gt 10 ]; then
        OBSERVATION="⚠️ Carga alta"
    elif [ "$QUEUE_DEPTH" -gt 5 ]; then
        OBSERVATION="Scaling esperado"
    else
        OBSERVATION="Procesando"
    fi

    # Si cambió la capacidad deseada, destacarlo
    if [ "$DESIRED_CAPACITY" -ne "$INITIAL_WORKER_COUNT" ]; then
        OBSERVATION="🔥 $OBSERVATION"
    fi

    # Mostrar fila
    printf "%-8s %-12s %-20s %-25s %-15s\n" \
        "${ELAPSED}s" \
        "$QUEUE_DEPTH msgs" \
        "$DESIRED_CAPACITY (de $CURRENT_INSTANCES)" \
        "Min:1 Max:3" \
        "$OBSERVATION"

    sleep $CHECK_INTERVAL
done

echo ""

# Paso 6: Resumen de resultados
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}  Resumen del Test - Escenario 2${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}📊 Métricas de Upload:${NC}"
echo "   Videos subidos exitosamente: $SUCCESS_COUNT / $NUM_VIDEOS"
echo "   Tiempo total de uploads: ${UPLOAD_DURATION}s"
echo "   Throughput: $(echo "scale=2; $SUCCESS_COUNT / $UPLOAD_DURATION" | bc) videos/seg"
echo ""
echo -e "${YELLOW}📈 Métricas de Auto Scaling:${NC}"
echo "   Profundidad máxima de cola: $PEAK_QUEUE_DEPTH mensajes"
echo "   Máximo de workers alcanzado: $MAX_WORKERS_REACHED"
echo "   Workers inicial: $INITIAL_WORKER_COUNT"
echo ""

if [ "$SCALE_UP_DETECTED" -eq 1 ]; then
    echo -e "${GREEN}✅ Auto Scaling EXITOSO:${NC} Workers escalaron de $INITIAL_WORKER_COUNT a $MAX_WORKERS_REACHED"
else
    echo -e "${YELLOW}⚠️  Auto Scaling NO detectado${NC}"
    echo "   Posibles razones:"
    echo "   - Cooldown period activo (300s)"
    echo "   - Workers procesaron muy rápido"
    echo "   - No se alcanzó el threshold de 5 msgs/worker"
fi
echo ""

# Paso 7: Estado final
echo -e "${YELLOW}🏁 Estado final del sistema:${NC}"
FINAL_QUEUE_DEPTH=$(get_queue_depth)
FINAL_WORKER_COUNT=$(get_worker_count)
echo "   Mensajes en cola: $FINAL_QUEUE_DEPTH"
echo "   Workers activos: $FINAL_WORKER_COUNT"
echo ""

echo -e "${GREEN}✓ Test completado${NC}"
echo ""
echo -e "${BLUE}💡 Recomendaciones:${NC}"
echo "   1. Revisa AWS Console → EC2 Auto Scaling Groups → $WORKER_ASG_NAME"
echo "   2. Verifica CloudWatch Metrics para profundidad de cola SQS"
echo "   3. Revisa Activity History del ASG para ver eventos de scaling"
echo ""
