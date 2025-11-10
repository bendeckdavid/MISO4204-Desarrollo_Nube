#!/bin/bash

# Script para crear usuarios de prueba para las pruebas de carga
BASE_URL="http://anb-video-alb-760991728.us-east-1.elb.amazonaws.com"

echo "🚀 Creando usuarios de prueba para Entrega 3..."
echo ""

# Array de usuarios
declare -a usuarios=(
  "test1@anb.com:Test123!:Test:User1:Bogota:Colombia"
  "test2@anb.com:Test123!:Test:User2:Medellin:Colombia"
  "test3@anb.com:Test123!:Test:User3:Cali:Colombia"
  "test4@anb.com:Test123!:Test:User4:Barranquilla:Colombia"
  "test5@anb.com:Test123!:Test:User5:Cartagena:Colombia"
)

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
  elif [ "$http_code" = "400" ] && echo "$body" | grep -q "already registered"; then
    echo "   ⚠️  Usuario ya existe (OK)"
  else
    echo "   ❌ Error al crear usuario (HTTP $http_code)"
    echo "   Respuesta: $body"
  fi
  echo ""
done

echo "✅ Proceso completado!"
echo ""
echo "📋 Usuarios disponibles para pruebas:"
for user_data in "${usuarios[@]}"; do
  IFS=':' read -r email password _ _ _ _ <<< "$user_data"
  echo "   - $email / $password"
done
