#!/bin/bash

# Script para crear usuarios de prueba para las pruebas de carga - Entrega 4
# Este script crea los usuarios que serán utilizados por k6 para las pruebas

# IMPORTANTE: Cambiar esta URL por el DNS de tu ALB
BASE_URL="${BASE_URL:-http://anb-video-alb-1059958631.us-east-1.elb.amazonaws.com}"

echo "🚀 Creando usuarios de prueba para Entrega 4 (SQS Architecture)..."
echo "📍 Base URL: $BASE_URL"
echo ""

# Array de usuarios
declare -a usuarios=(
  "test1@anb.com:Test123!:Test:User1:Bogota:Colombia"
  "test2@anb.com:Test123!:Test:User2:Medellin:Colombia"
  "test3@anb.com:Test123!:Test:User3:Cali:Colombia"
  "test4@anb.com:Test123!:Test:User4:Barranquilla:Colombia"
  "test5@anb.com:Test123!:Test:User5:Cartagena:Colombia"
)

# Contador de éxitos
success_count=0
existing_count=0
error_count=0

# Crear cada usuario
for user_data in "${usuarios[@]}"; do
  IFS=':' read -r email password first_name last_name city country <<< "$user_data"

  echo "📝 Creando usuario: $email"

  response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/signup" \
    -H "Content-Type: application/json" \
    -d "{
      \"email\": \"$email\",
      \"password1\": \"$password\",
      \"password2\": \"$password\",
      \"first_name\": \"$first_name\",
      \"last_name\": \"$last_name\",
      \"city\": \"$city\",
      \"country\": \"$country\"
    }")

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [ "$http_code" = "201" ]; then
    echo "   ✅ Usuario creado exitosamente"
    ((success_count++))
  elif [ "$http_code" = "400" ] && echo "$body" | grep -q "already registered"; then
    echo "   ⚠️  Usuario ya existe (OK)"
    ((existing_count++))
  else
    echo "   ❌ Error al crear usuario (HTTP $http_code)"
    echo "   Respuesta: $body"
    ((error_count++))
  fi
  echo ""
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Proceso completado!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Resumen:"
echo "   ✅ Usuarios nuevos creados: $success_count"
echo "   ⚠️  Usuarios existentes: $existing_count"
echo "   ❌ Errores: $error_count"
echo ""
echo "📋 Usuarios disponibles para pruebas:"
for user_data in "${usuarios[@]}"; do
  IFS=':' read -r email password _ _ _ _ <<< "$user_data"
  echo "   - $email / $password"
done
echo ""
echo "🧪 Para ejecutar el test de k6:"
echo "   BASE_URL=\"$BASE_URL\" k6 run capacity-planning/scripts-entrega4/test_escenario1_capa_web.js"
echo ""
