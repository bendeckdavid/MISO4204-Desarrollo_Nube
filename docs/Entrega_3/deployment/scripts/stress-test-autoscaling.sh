#!/bin/bash

###############################################################################
# Prueba de Estrés Agresiva para Auto Scaling
# Envía múltiples oleadas de tráfico para mantener CPU > 70% por varios minutos
###############################################################################

ALB_URL="http://anb-video-alb-1422609277.us-east-1.elb.amazonaws.com"
TOTAL_REQUESTS=50000
CONCURRENT=200
DURATION=180  # 3 minutos de prueba continua

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║   🔥 PRUEBA DE ESTRÉS AGRESIVA - AUTO SCALING TEST 🔥    ║${NC}"
echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}CONFIGURACIÓN:${NC}"
echo -e "  Endpoint:      ${BLUE}${ALB_URL}/health${NC}"
echo -e "  Requests:      ${BLUE}${TOTAL_REQUESTS} (distribuidos en múltiples oleadas)${NC}"
echo -e "  Concurrencia:  ${BLUE}${CONCURRENT} conexiones simultáneas${NC}"
echo -e "  Duración:      ${BLUE}~${DURATION} segundos (3 minutos)${NC}"
echo ""
echo -e "${YELLOW}OBJETIVO:${NC}"
echo -e "  ${GREEN}✓${NC} Mantener CPU > 70% por más de 60 segundos"
echo -e "  ${GREEN}✓${NC} Activar Auto Scaling Policy"
echo -e "  ${GREEN}✓${NC} Escalar de 1 a 2-3 instancias"
echo ""
echo -e "${RED}⚠️  IMPORTANTE: MONITOREA AWS CONSOLE EN TIEMPO REAL${NC}"
echo -e "  1. CloudWatch → Metrics → CPUUtilization (refresh cada 10s)"
echo -e "  2. Auto Scaling Group → Activity"
echo -e "  3. Load Balancer → Target Groups → Targets"
echo ""
echo -e "${YELLOW}Presiona Ctrl+C para cancelar, o espera 10 segundos...${NC}"
sleep 10

echo ""
echo -e "${GREEN}🚀 INICIANDO PRUEBA AGRESIVA...${NC}"
echo ""

# Función para ejecutar una oleada
run_wave() {
    local wave_num=$1
    local requests=$2
    echo -e "${BLUE}[Oleada $wave_num]${NC} Enviando $requests requests con $CONCURRENT conexiones..."
    ab -n $requests -c $CONCURRENT -q "${ALB_URL}/health" 2>&1 | grep -E "(Requests per second|Time per request|Complete requests|Failed requests)" || true
    echo ""
}

# Registrar hora de inicio
START_TIME=$(date +%s)
echo -e "${YELLOW}⏱️  Inicio: $(date '+%H:%M:%S')${NC}"
echo ""

# Oleada 1: Calentamiento
run_wave 1 5000

# Oleada 2: Subir la carga
run_wave 2 10000

# Oleada 3: Máxima presión
run_wave 3 15000

# Oleada 4: Mantener presión
run_wave 4 10000

# Oleada 5: Última embestida
run_wave 5 10000

# Calcular duración
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  ✅ PRUEBA COMPLETADA                      ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}📊 RESUMEN:${NC}"
echo -e "  Total requests:  ${BLUE}${TOTAL_REQUESTS}${NC}"
echo -e "  Duración:        ${BLUE}${DURATION} segundos${NC}"
echo -e "  Finalizado:      ${BLUE}$(date '+%H:%M:%S')${NC}"
echo ""
echo -e "${YELLOW}🔍 VERIFICANDO ESTADO DEL AUTO SCALING...${NC}"
sleep 5

# Verificar estado del Auto Scaling Group
ASG_STATUS=$(aws autoscaling describe-auto-scaling-groups \
    --auto-scaling-group-names anb-video-web-asg \
    --region us-east-1 \
    --query 'AutoScalingGroups[0].{Desired: DesiredCapacity, Current: length(Instances)}' \
    2>/dev/null)

if [ $? -eq 0 ]; then
    echo "$ASG_STATUS" | python3 -c "
import sys, json
data = json.load(sys.stdin)
desired = data.get('Desired', 1)
current = data.get('Current', 1)

print(f'\n  Desired Capacity: \033[1;33m{desired}\033[0m')
print(f'  Instancias Activas: \033[1;33m{current}\033[0m')

if desired > 1:
    print(f'\n\033[1;32m  🎉 ¡AUTO SCALING ACTIVADO! Se escaló a {desired} instancias\033[0m')
else:
    print(f'\n\033[1;33m  ⏳ Auto Scaling aún no activado (puede tardar 1-2 minutos)\033[0m')
    print(f'     Revisa AWS Console para ver si está en proceso...')
"
fi

echo ""
echo -e "${YELLOW}📜 Últimas actividades del Auto Scaling:${NC}"
aws autoscaling describe-scaling-activities \
    --auto-scaling-group-name anb-video-web-asg \
    --region us-east-1 \
    --max-records 3 \
    --query 'Activities[*].{Time: StartTime, Status: StatusCode, Desc: Description}' \
    --output table 2>/dev/null || echo "  (Error al obtener actividades)"

echo ""
echo -e "${GREEN}✅ Script completado.${NC} Sigue monitoreando AWS Console por 2-3 minutos más."
echo -e "   Las instancias nuevas pueden tardar ~2 minutos en estar 'InService'."
echo ""
