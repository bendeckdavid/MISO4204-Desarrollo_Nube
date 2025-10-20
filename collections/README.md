# Colección de Postman - ANB Rising Stars Showcase API

Esta colección incluye todos los endpoints de la API para gestión de videos de artistas emergentes.

## Contenido

- `postman_collection.json` - Colección completa con los 9 endpoints de la API
- `postman_environment.json` - Variables de entorno para local y producción
- Este README con instrucciones de uso

## Endpoints Incluidos

### 1. Authentication (2 endpoints)
- **POST** `/api/auth/signup` - Registro de nuevo usuario
- **POST** `/api/auth/login` - Autenticación y obtención de token JWT

### 2. Video Management (4 endpoints - requieren JWT)
- **POST** `/api/videos/upload` - Subir video para procesamiento
- **GET** `/api/videos` - Listar mis videos
- **GET** `/api/videos/{video_id}` - Obtener detalles de un video
- **DELETE** `/api/videos/{video_id}` - Eliminar un video

### 3. Public Endpoints (3 endpoints)
- **GET** `/api/public/videos` - Listar videos públicos (sin auth)
- **POST** `/api/public/videos/{video_id}/vote` - Votar por un video (requiere JWT)
- **GET** `/api/public/rankings` - Obtener ranking de videos (sin auth)

### 4. Health Check (1 endpoint)
- **GET** `/health` - Verificar estado del servicio

## Uso con Postman (GUI)

### 1. Importar la Colección

1. Abre Postman Desktop o Web
2. Click en **Import** en la esquina superior izquierda
3. Selecciona los archivos:
   - `postman_collection.json`
   - `postman_environment.json`
4. Click en **Import**

### 2. Configurar el Entorno

1. En la esquina superior derecha, selecciona el dropdown de entornos
2. Selecciona **ANB Rising Stars Environment**
3. Click en el ícono de ojo (👁️) para ver las variables
4. La variable `base_url` debe estar configurada como:
   - **Local**: `http://localhost:8080` (habilitado por defecto)
   - **Producción**: Cambia `deploy_url` según tu dominio

### 3. Flujo de Pruebas Recomendado

#### Paso 1: Registro de Usuario
1. Abre la carpeta **Authentication**
2. Ejecuta **Signup - Register new user**
3. Los tests automáticamente guardarán el `user_id` en las variables de colección

#### Paso 2: Autenticación
1. Actualiza el `username` y `password` en el body de **Login - Get access token**
2. Ejecuta el request
3. El token JWT se guardará automáticamente en la variable `access_token`
4. Los siguientes requests usarán este token automáticamente

#### Paso 3: Subir un Video
1. Abre la carpeta **Video Management**
2. En **Upload Video**, selecciona un archivo de video en el campo `file`
3. Actualiza `title` y `description`
4. Ejecuta el request
5. El `video_id` se guardará automáticamente

#### Paso 4: Gestionar Videos
- **List My Videos**: Ver todos tus videos
- **Get Video Details**: Ver detalles de un video específico (usa la variable `{{video_id}}`)
- **Delete Video**: Eliminar un video (usa la variable `{{video_id}}`)

#### Paso 5: Endpoints Públicos
- **List Public Videos**: Ver videos publicados (con paginación y filtros)
- **Vote for Video**: Votar por un video público
- **Get Rankings**: Ver el ranking de videos más votados

### 4. Tests Automáticos

Cada endpoint incluye tests automáticos que validan:
- ✅ Código de estado HTTP correcto
- ✅ Estructura de respuesta esperada
- ✅ Tipos de datos correctos
- ✅ Valores de campos requeridos
- ✅ Lógica de negocio (ej: videos ordenados por votos)

Para ver los resultados de los tests:
1. Ejecuta un request
2. Ve a la pestaña **Test Results** en la respuesta
3. Verás un resumen con tests pasados/fallidos

### 5. Ejecutar Toda la Colección

1. Click derecho en la colección **ANB Rising Stars Showcase API**
2. Selecciona **Run collection**
3. Configura las opciones:
   - Selecciona los requests a ejecutar
   - Configura delay entre requests (recomendado: 500ms)
4. Click en **Run ANB Rising Stars Showcase API**
5. Revisa el resumen de tests al finalizar

**Nota**: Algunos requests dependen de otros (ej: necesitas login antes de upload video). Ejecuta en orden o usa variables pre-configuradas.

## Uso con Newman (CLI)

Newman es el runner de línea de comandos para colecciones de Postman, ideal para CI/CD.

### 1. Instalación

```bash
# Instalar newman globalmente
npm install -g newman

# Verificar instalación
newman --version
```

### 2. Ejecutar la Colección Completa

```bash
# Ejecutar con el entorno local
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --delay-request 500

# Ejecutar con verbose output
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --verbose

# Generar reporte HTML
npm install -g newman-reporter-html

newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  -r html \
  --reporter-html-export newman-report.html
```

### 3. Ejecutar Carpeta Específica

```bash
# Solo endpoints de Authentication
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --folder "Authentication"

# Solo Video Management
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --folder "Video Management"

# Solo Public Endpoints
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --folder "Public Endpoints"
```

### 4. Ejecutar Request Individual

```bash
# Ejecutar solo un request específico por nombre
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --folder "Authentication" \
  --bail

# --bail detiene la ejecución en el primer error
```

### 5. Configurar Variables de Entorno via CLI

```bash
# Sobrescribir base_url para apuntar a producción
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --env-var "base_url=https://your-production-domain.com"

# Configurar múltiples variables
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --env-var "base_url=https://api.example.com" \
  --env-var "access_token=your-jwt-token"
```

### 6. Opciones Útiles de Newman

```bash
# Ejecutar con timeout personalizado (en ms)
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --timeout-request 30000

# Ejecutar sin verificar certificados SSL (solo desarrollo)
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --insecure

# Exportar variables de entorno después de la ejecución
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  --export-environment updated-environment.json

# Generar múltiples reportes
newman run collections/postman_collection.json \
  -e collections/postman_environment.json \
  -r cli,json,html \
  --reporter-json-export newman-report.json \
  --reporter-html-export newman-report.html
```

### 7. Ejemplo de Salida de Newman

```
ANB Rising Stars Showcase API

→ Authentication / Signup - Register new user
  POST http://localhost:8080/api/auth/signup [201 Created, 523B, 245ms]
  ✓ Status code is 201
  ✓ Response has user data
  ✓ Response should not include password

→ Authentication / Login - Get access token
  POST http://localhost:8080/api/auth/login [200 OK, 412B, 189ms]
  ✓ Status code is 200
  ✓ Response has access token
  ✓ Token is a valid JWT

→ Video Management / Upload Video
  POST http://localhost:8080/api/videos/upload [202 Accepted, 678B, 1.2s]
  ✓ Status code is 202 (Accepted)
  ✓ Response has video data
  ✓ Video status is 'processing' or 'pending'

┌─────────────────────────┬────────────────────┬───────────────────┐
│                         │           executed │            failed │
├─────────────────────────┼────────────────────┼───────────────────┤
│              iterations │                  1 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│                requests │                  9 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│            test-scripts │                 18 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│      prerequest-scripts │                  0 │                 0 │
├─────────────────────────┼────────────────────┼───────────────────┤
│              assertions │                 45 │                 0 │
├─────────────────────────┴────────────────────┴───────────────────┤
│ total run duration: 6.2s                                         │
├──────────────────────────────────────────────────────────────────┤
│ total data received: 3.14kB (approx)                             │
├──────────────────────────────────────────────────────────────────┤
│ average response time: 412ms [min: 189ms, max: 1.2s, s.d.: 312] │
└──────────────────────────────────────────────────────────────────┘
```

### 8. Integración con CI/CD (GitHub Actions)

Ejemplo de workflow para ejecutar tests de Postman:

```yaml
name: API Tests

on: [push, pull_request]

jobs:
  api-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install Newman
        run: npm install -g newman newman-reporter-html

      - name: Start API services
        run: docker compose up -d

      - name: Wait for services to be ready
        run: sleep 30

      - name: Run Postman collection
        run: |
          newman run collections/postman_collection.json \
            -e collections/postman_environment.json \
            -r cli,html \
            --reporter-html-export newman-report.html \
            --delay-request 500

      - name: Upload test report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: newman-report
          path: newman-report.html

      - name: Stop services
        if: always()
        run: docker compose down
```

## Variables de Colección

Las siguientes variables se configuran automáticamente al ejecutar los requests:

| Variable | Descripción | Se actualiza en |
|----------|-------------|-----------------|
| `access_token` | Token JWT para autenticación | Login request |
| `user_id` | ID del usuario registrado | Signup request |
| `video_id` | ID del último video subido | Upload Video request |

## Validación de Respuestas

Cada endpoint incluye validaciones automáticas:

### Authentication
- ✅ Usuario creado con todos los campos requeridos
- ✅ Token JWT válido con formato correcto
- ✅ Contraseña no incluida en respuestas

### Video Management
- ✅ Video aceptado para procesamiento (202)
- ✅ Estado inicial correcto (processing/pending)
- ✅ Lista de videos devuelve array
- ✅ Eliminación exitosa (204 No Content)

### Public Endpoints
- ✅ Paginación correcta en listados
- ✅ Videos filtrados por estado publicado
- ✅ Votos registrados correctamente
- ✅ Rankings ordenados por cantidad de votos
- ✅ Posiciones secuenciales en ranking

## Troubleshooting

### Error: "getaddrinfo ENOTFOUND localhost"
**Solución**: Verifica que los servicios estén corriendo con `docker compose ps`

### Error: "401 Unauthorized"
**Solución**:
1. Ejecuta el request de Login primero
2. Verifica que la variable `access_token` esté configurada
3. El token puede haber expirado, vuelve a hacer login

### Error: "400 Bad Request - Invalid file type"
**Solución**: Asegúrate de subir un archivo de video válido (MP4, AVI, MOV)

### Error: "404 Not Found" en video específico
**Solución**:
1. Verifica que la variable `video_id` esté configurada
2. Ejecuta "List My Videos" para obtener IDs válidos

### Error: "422 Unprocessable Entity"
**Solución**: Revisa que todos los campos requeridos estén presentes en el body

## Recursos Adicionales

- [Documentación de Postman](https://learning.postman.com/)
- [Newman Documentation](https://learning.postman.com/docs/running-collections/using-newman-cli/command-line-integration-with-newman/)
- [API Documentation](../docs/Entrega_1/arquitectura.md)
- [Repository README](../README.md)

## Contacto y Soporte

Para problemas o preguntas sobre la API, consulta la documentación completa en `docs/Entrega_1/arquitectura.md`
