# Reporte SonarQube - Entrega 3

## Información General

- **Proyecto**: ANB Rising Stars Showcase API
- **Versión**: 3.0 (AWS con S3 Storage y Auto Scaling)
- **Fecha de análisis**: 09 de Noviembre de 2025
- **SonarQube Version**: SonarCloud
- **Branch**: main

---

## Resumen Ejecutivo

El proyecto logra un **Quality Gate en estado PASSED** con mejoras significativas en la cobertura de código. Esta entrega se enfocó en mejorar la calidad del código existente mediante la adición de tests para cubrir casos de borde y manejo de excepciones que no estaban siendo probados.

**Aspectos destacados:**
- ✅ Quality Gate mantiene estado PASSED
- ✅ Cobertura de código nuevo: 100%
- ✅ Cobertura general mejorada: 98.8% (desde 78.4%)
- ✅ Cero duplicación de código (0.0%)
- ✅ Sin vulnerabilidades de seguridad (Rating A)
- ✅ Cero Security Hotspots detectados
- ✅ Integración exitosa de AWS S3 para almacenamiento
- ✅ Implementación de capa de abstracción de storage con tests completos

---

## Métricas Principales

### Comparación Entrega 2 vs Entrega 3

| Métrica | Entrega 2 | Entrega 3 | Cambio |
|---------|-----------|-----------|--------|
| **Quality Gate** | ✅ PASSED | ✅ PASSED | ✅ Mantenido |
| **Bugs (Reliability)** | 3 | 3 | Sin cambio |
| **Vulnerabilities** | 0 | 0 | ✅ Mantenido |
| **Code Smells** | 2 | 2 | Sin cambio |
| **Security Hotspots** | 0 | 0 | ✅ Mantenido |
| **Coverage** | 78.4% | 98.8% | ✅ +20.4% |
| **Coverage on New Code** | 90% | 100% | ✅ +10% |
| **Duplications** | 0.0% | 0.0% | ✅ Mantenido |
| **Lines of Code** | 782 | ~950 | +~170 líneas |
| **Technical Debt** | 15min | 15min | Mantenido |

---

## Quality Gate

**Estado**: ✅ PASSED

### Condiciones evaluadas:

| Condición | Threshold | Valor Actual | Estado |
|-----------|-----------|--------------|--------|
| Coverage on New Code | >= 80% | 90.0% | ✅ |
| Duplicated Lines on New Code | <= 3% | 0.0% | ✅ |
| Maintainability Rating on New Code | >= A | A | ✅ |
| Reliability Rating on New Code | >= A | A | ✅ |
| Security Rating on New Code | >= A | A | ✅ |

**Análisis**: El proyecto cumple con todas las condiciones del Quality Gate. El código nuevo añadido para la integración con S3 y mejoras en la capa de almacenamiento alcanza 100% de cobertura, sin duplicaciones, y ratings A en todas las categorías. Se logró un aumento significativo en la cobertura general del proyecto.

---

## Desglose por Categoría

### 1. Reliability (Bugs)

**Rating**: B (con 3 bugs identificados)
**Total de Bugs**: 3

#### Bugs Identificados

| Severidad | Cantidad | Ubicación | Descripción |
|-----------|----------|-----------|-------------|
| High | 1 | app/api/routes/videos.py:77 | Use an asynchronous file API instead of synchronous open() |
| High | 2 | app/core/security.py:38, 40 | Don't use `datetime.datetime.utcnow` (deprecated since Python 3.12) |

**Detalle de los bugs:**

1. **Bug 1 - Uso de API síncrona de archivos**
   - **Ubicación**: [app/api/routes/videos.py:77](app/api/routes/videos.py#L77)
   - **Severidad**: High (Reliability)
   - **Descripción**: Se está utilizando `open()` síncrono en una función asíncrona de FastAPI, lo cual puede bloquear el event loop y reducir el rendimiento
   - **Recomendación**: Usar `aiofiles` para operaciones de I/O asíncronas

2. **Bug 2 - datetime.utcnow() deprecado (Línea 38)**
   - **Ubicación**: [app/core/security.py:38](app/core/security.py#L38)
   - **Severidad**: High (Reliability)
   - **Descripción**: `datetime.datetime.utcnow()` está deprecado desde Python 3.12. Se recomienda usar `datetime.datetime.now(datetime.UTC)`
   - **Recomendación**: Actualizar a la API moderna de timezone-aware datetime

3. **Bug 3 - datetime.utcnow() deprecado (Línea 40)**
   - **Ubicación**: [app/core/security.py:40](app/core/security.py#L40)
   - **Severidad**: High (Reliability)
   - **Descripción**: Similar al Bug 2, uso de API deprecada
   - **Recomendación**: Actualizar a `datetime.datetime.now(datetime.UTC)`

#### Acciones Tomadas

No se corrigieron bugs entre Entrega 1 y Entrega 2. Los 3 bugs identificados permanecen sin cambios. La decisión fue priorizar el despliegue exitoso en AWS y documentación antes que correcciones menores que no afectan la funcionalidad actual del sistema.

---

### 2. Security (Vulnerabilidades)

**Rating**: A
**Total de Vulnerabilidades**: 0

#### Vulnerabilidades Identificadas

No se identificaron vulnerabilidades de seguridad en el código.

| Severidad | Cantidad | Tipo | Ubicación |
|-----------|----------|------|-----------|
| Critical | 0 | N/A | N/A |
| High | 0 | N/A | N/A |
| Medium | 0 | N/A | N/A |
| Low | 0 | N/A | N/A |

#### Security Hotspots

**Total**: 0

No se detectaron security hotspots que requieran revisión.

| Prioridad | Cantidad | Descripción |
|-----------|----------|-------------|
| High | 0 | N/A |
| Medium | 0 | N/A |
| Low | 0 | N/A |

#### Mejoras de Seguridad Implementadas

El proyecto mantiene un excelente perfil de seguridad desde la Entrega 1. No hubo vulnerabilidades que corregir. Las medidas de seguridad implementadas incluyen:

1. **JWT Authentication**: Implementación robusta de autenticación con tokens JWT
2. **Password Hashing**: Uso de bcrypt para hash seguro de contraseñas
3. **SQL Injection Protection**: Uso de SQLAlchemy ORM con queries parametrizadas
4. **CORS Configuration**: Configuración adecuada de políticas de origen cruzado

**Nota**: El Rating A de seguridad se mantiene en ambas entregas, reflejando buenas prácticas de seguridad en el desarrollo.

---

### 3. Maintainability (Code Smells)

**Rating**: A (con 2 code smells menores)
**Total de Code Smells**: 2
**Technical Debt**: Mínimo

#### Code Smells por Severidad

| Severidad | Cantidad |
|-----------|----------|
| Critical | 0 |
| Major | 0 |
| Medium | 2 |
| Minor | 0 |

#### Code Smells Principales

Los 2 code smells identificados están relacionados con el uso de `datetime.utcnow()` deprecado:

| Tipo | Cantidad | Ubicación |
|------|----------|-----------|
| Deprecated API Usage | 2 | app/core/security.py:38, 40 |
| Cognitive Complexity | 0 | N/A |
| Duplicated Blocks | 0 | N/A |
| Too Many Parameters | 0 | N/A |

**Detalle de los Code Smells:**

1. **datetime.utcnow() deprecado (Línea 38)**
   - **Ubicación**: [app/core/security.py:38](app/core/security.py#L38)
   - **Severidad**: Medium (Maintainability)
   - **Descripción**: Uso de API deprecada que será removida en versiones futuras de Python

2. **datetime.utcnow() deprecado (Línea 40)**
   - **Ubicación**: [app/core/security.py:40](app/core/security.py#L40)
   - **Severidad**: Medium (Maintainability)
   - **Descripción**: Uso de API deprecada que será removida en versiones futuras de Python

#### Refactorizaciones Realizadas

No se realizaron refactorizaciones entre Entrega 1 y Entrega 2. Los 2 code smells permanecen sin cambios. Sin embargo, **el código nuevo añadido para AWS tiene 0 code smells**, demostrando que se mantuvieron los estándares de calidad en las nuevas implementaciones.

---

## Cobertura de Código (Coverage)

### Métricas Generales

| Métrica | Valor |
|---------|-------|
| **Overall Coverage** | 98.8% |
| **Coverage on New Code** | 100% |
| **Lines of Code** | ~950 |
| **Lines to Cover** | ~920 |
| **Uncovered Lines** | ~11 |

### Análisis de Coverage

**Entrega 2**: 78.4% coverage (782 líneas)
**Entrega 3**: 98.8% coverage (~950 líneas, +~170 líneas nuevas)
**Cambio**: +20.4% (mejora significativa)

**Explicación de la mejora:**

El incremento sustancial en el coverage se logró mediante:

1. **Implementación completa de tests para la capa de storage**: Se desarrolló una suite completa de tests para `app/core/storage.py`, cubriendo tanto la implementación local como S3, incluyendo casos de éxito, errores y edge cases.

2. **Tests para funcionalidades del worker**: Se agregaron tests adicionales para el procesamiento de videos en `app/worker/videos.py`, incluyendo manejo de archivos temporales, resolución de rutas y limpieza de recursos.

3. **Cobertura de manejo de excepciones**: Se añadió un test específico para cubrir el camino de excepciones en `app/worker/tasks.py` que antes no estaba siendo probado, mejorando la cobertura de casos de error.

4. **Tests para nuevas rutas de API**: Las nuevas funcionalidades de videos con S3 fueron desarrolladas con tests desde el principio, siguiendo TDD.

**Lo destacable**: Todo el **código nuevo tiene 100% de cobertura**, demostrando un compromiso real con la calidad y la prevención de bugs mediante testing exhaustivo.

### Cobertura por Módulo (Entrega 3)

Los módulos principales ahora tienen cobertura casi completa:

| Módulo | Coverage |
|--------|----------|
| `app/api/routes/auth.py` | 100% |
| `app/api/routes/videos.py` | ~98% |
| `app/api/routes/public.py` | 100% |
| `app/core/security.py` | 100% |
| `app/core/storage.py` | 100% ✨ (nuevo) |
| `app/db/models.py` | ~95% |
| `app/worker/tasks.py` | ~85% (mejorado desde ~54%) |
| `app/worker/videos.py` | ~95% ✨ (ampliado) |

**Mejoras principales**:
- `app/core/storage.py`: Módulo nuevo con 100% de cobertura desde el inicio, incluyendo 40+ tests que cubren LocalStorage, S3Storage, manejo de errores, y casos edge
- `app/worker/tasks.py`: Mejorado de 54.5% a ~85% mediante la adición de tests de manejo de excepciones
- `app/worker/videos.py`: Expandido significativamente con tests para procesamiento de archivos, paths y cleanup

---

## Duplicaciones de Código

| Métrica | Valor |
|---------|-------|
| **Duplicated Lines** | 0 |
| **Duplicated Blocks** | 0 |
| **Duplicated Files** | 0 |
| **Duplication Density** | 0.0% |

### Bloques Duplicados Principales

No se detectaron bloques de código duplicados en el proyecto.

| Ubicación 1 | Ubicación 2 | Líneas |
|-------------|-------------|--------|
| N/A | N/A | 0 |

### Análisis

El proyecto mantiene **0% de duplicación** tanto en Entrega 1 como en Entrega 2. Esto indica:

1. **Código bien estructurado**: Se utilizan principios DRY (Don't Repeat Yourself)
2. **Reutilización adecuada**: Funciones y módulos son reutilizados en lugar de copiados
3. **Arquitectura limpia**: La separación en capas (routes, services, models) evita duplicaciones naturalmente

**No se requieren acciones**: Este es uno de los aspectos más fuertes del proyecto en términos de calidad de código.

---

## Complejidad del Código

### Complejidad Cognitiva

No se detectaron funciones con complejidad cognitiva excesiva. Todas las funciones mantienen complejidad por debajo del umbral recomendado.

| Función | Complejidad | Umbral | Estado |
|---------|-------------|--------|--------|
| Todas las funciones | < 10 | 15 | ✅ |

### Complejidad Ciclomática

El código mantiene baja complejidad ciclomática, indicando funciones bien estructuradas y fáciles de mantener.

| Módulo | Complejidad Promedio | Observaciones |
|--------|---------------------|---------------|
| `app/api/routes/` | Baja | Rutas bien estructuradas con validaciones claras |
| `app/worker/` | Baja | Tareas de Celery con lógica simple y directa |
| `app/core/security.py` | Baja | Funciones de seguridad concisas |

**Conclusión**: La complejidad del código no es un problema en este proyecto. El diseño modular y las funciones pequeñas mantienen la complejidad bajo control.

---

## Cambios Específicos Respecto a Entrega 2

### 1. Código Nuevo Añadido

Se agregaron aproximadamente 170 líneas de código relacionadas con la integración de S3 y mejora de la cobertura de tests.

- **Nuevos módulos implementados**:
  - `app/core/storage.py`: Capa de abstracción completa para storage (LocalStorage y S3Storage)
  - Integración de boto3 para AWS S3
  - Manejo de IAM Roles en lugar de credenciales hardcodeadas
  - Sistema de presigned URLs para acceso temporal a archivos

- **Tests añadidos**:
  - `tests/core/test_storage.py` (~440 líneas): Suite completa de 40+ tests para storage
  - `tests/worker/test_videos.py`: Expansión significativa con tests de procesamiento
  - `tests/worker/test_tasks.py`: Test adicional para manejo de excepciones
  - `tests/api/test_videos.py`: Ampliación para soportar S3

- **Líneas de código añadidas**: ~170 líneas de código productivo
- **Líneas de tests añadidas**: ~500+ líneas de tests

**Calidad del código nuevo**:
- Coverage: 100%
- Issues: 0
- Duplicación: 0%
- Ratings: A en todas las categorías
- Tests comprehensivos: Casos de éxito, errores, edge cases

### 2. Bugs Corregidos

No se corrigieron bugs entre Entrega 2 y Entrega 3.

| Bug | Ubicación | Solución |
|-----|-----------|----------|
| N/A | N/A | No se realizaron correcciones de bugs |

**Justificación**: Se priorizó la mejora de la cobertura de tests y la integración con S3. Los 3 bugs existentes (uso de API síncrona y datetime.utcnow deprecado) son mejoras técnicas que no afectan la funcionalidad actual del sistema en producción.

### 3. Vulnerabilidades Corregidas

No había vulnerabilidades que corregir.

| Vulnerabilidad | Ubicación | Solución |
|----------------|-----------|----------|
| N/A | N/A | El proyecto mantiene Rating A de seguridad |

### 4. Code Smells Corregidos

No se corrigieron code smells entre Entrega 2 y Entrega 3.

| Code Smell | Ubicación | Refactorización |
|------------|-----------|-----------------|
| N/A | N/A | No se realizaron refactorizaciones |

**Justificación**: Los 2 code smells existentes (uso de `datetime.utcnow()`) son mejoras menores que no afectan funcionalidad. Se priorizó la mejora de cobertura de tests y la integración con S3, que aportan más valor al proyecto.

### 5. Tests Añadidos

Se realizó un esfuerzo significativo en la adición de tests durante la Entrega 3:

**Tests completamente nuevos**:

1. **`tests/core/test_storage.py`** (~440 líneas, 40+ tests):
   - Tests para `LocalStorage`: upload, download, delete, file_exists, get_file_url
   - Tests para `S3Storage`: integración completa con boto3, presigned URLs, manejo de content types
   - Tests de excepciones: ClientError, StorageUploadError, StorageDownloadError, StorageURLError
   - Tests de la clase abstracta `StorageBackend`
   - Tests de la función factory `get_storage()`
   - Coverage: 100%

2. **`tests/worker/test_videos.py`** (expandido):
   - Tests de `resolve_container_path()` con fallback
   - Tests de `ensure_directory_exists()` con manejo de permisos
   - Tests de `_setup_file_paths()` para S3 y local storage
   - Tests de `_process_video_file()` con mocks de moviepy
   - Tests de `_cleanup_temp_files()` con manejo de errores
   - Tests del task completo `process_video()` con múltiples escenarios

3. **`tests/worker/test_tasks.py`** (mejorado):
   - Test adicional: `test_example_task_exception_with_retry()`
   - Cubre el camino de excepciones que antes no estaba probado
   - Mejora la cobertura de `app/worker/tasks.py` de 54.5% a ~85%

**Resultado**: +500 líneas de tests, mejorando la cobertura general de 78.4% a 98.8%.

---

## Issues Pendientes

### Bugs Pendientes (3 total)

Los siguientes 3 bugs permanecen sin corregir desde la Entrega 1:

| Severidad | Descripción | Ubicación | Plan de corrección |
|-----------|-------------|-----------|-------------------|
| High | Uso de API síncrona `open()` en función async | [app/api/routes/videos.py:77](app/api/routes/videos.py#L77) | Migrar a `aiofiles` en siguiente iteración |
| High | Uso de `datetime.utcnow()` deprecado | [app/core/security.py:38](app/core/security.py#L38) | Actualizar a `datetime.now(datetime.UTC)` |
| High | Uso de `datetime.utcnow()` deprecado | [app/core/security.py:40](app/core/security.py#L40) | Actualizar a `datetime.now(datetime.UTC)` |

**Impacto**: Ninguno de estos bugs afecta la funcionalidad actual del sistema en producción:
- El uso de `open()` síncrono puede reducir ligeramente el rendimiento, pero no causa errores
- Los `datetime.utcnow()` están deprecados pero aún funcionan correctamente en Python 3.11

**Prioridad para próxima entrega**: Media - son mejoras técnicas que pueden abordarse en una iteración futura sin urgencia.

### Code Smells Pendientes (2 total)

| Tipo | Descripción | Ubicación | Razón de no corrección |
|------|-------------|-----------|------------------------|
| Deprecated API | `datetime.utcnow()` (1) | [app/core/security.py:38](app/core/security.py#L38) | Prioridad en despliegue AWS exitoso |
| Deprecated API | `datetime.utcnow()` (2) | [app/core/security.py:40](app/core/security.py#L40) | Prioridad en despliegue AWS exitoso |

**Razón de no corrección**: Se priorizó:
1. Completar el despliegue funcional en AWS
2. Documentar exhaustivamente la arquitectura y el proceso
3. Mantener el Quality Gate en PASSED
4. Asegurar que el código nuevo tenga 0 issues (logrado: 90% coverage, 0 issues)

---

## Conclusiones

### Evolución del Proyecto

Entre la Entrega 2 y la Entrega 3, el proyecto ha experimentado un cambio de enfoque importante. Mientras que en la Entrega 2 nos concentramos en hacer que la infraestructura funcionara en AWS, en esta entrega nos dimos cuenta de que la calidad del código había quedado un poco relegada, con una cobertura de 78.4%.

Esta entrega fue diferente. Vimos las barras rojas en SonarQube señalando código sin probar y decidimos tomarnos en serio el testing. El resultado fue claro: pasamos de 78.4% a 98.8% de cobertura. Pero más allá de los números, lo importante fue el proceso. Al escribir tests para la capa de storage, descubrimos edge cases que no habíamos considerado. Al cubrir el manejo de excepciones en los workers, entendimos mejor cómo se comporta el código cuando las cosas fallan.

La integración con S3 fue desarrollada desde el inicio con tests, siguiendo algo más parecido a TDD. Esto nos ahorró tiempo de debugging y nos dio confianza para refactorizar. Los 40+ tests de la capa de storage no solo mejoraron el coverage, sino que también sirven como documentación viva de cómo debe comportarse el sistema.

### Logros Principales

1. **Mejora sustancial de cobertura**: De 78.4% a 98.8% (+20.4 puntos), alcanzando prácticamente el objetivo del 100%. El código nuevo tiene 100% de cobertura, demostrando que se puede mantener este estándar en nuevas features.

2. **Integración exitosa con S3**: Se implementó una capa completa de abstracción de storage que soporta tanto almacenamiento local como S3, con 100% de cobertura de tests desde el día uno. Esto incluye manejo robusto de errores, presigned URLs y detección automática de content types.

3. **Quality Gate mantenido**: A pesar de agregar ~170 líneas de código nuevo, el proyecto mantiene Quality Gate PASSED con ratings A en seguridad, mantenibilidad y confiabilidad. No se introdujeron nuevas vulnerabilidades ni code smells.

4. **Tests como primera clase**: Se agregaron más de 500 líneas de tests bien estructurados que cubren no solo los happy paths, sino también casos de error, edge cases y manejo de recursos temporales. Los tests ahora sirven como documentación y red de seguridad para refactoring futuro.

### Áreas de Mejora Futuras

1. **Completar cobertura del worker tasks**: El módulo `app/worker/tasks.py` está en ~85%. Falta cubrir el caso de excepción anidada (líneas 16-17). Aunque intentamos cubrirlo, la complejidad de mockear el comportamiento de Celery requiere más investigación. No es crítico, pero sería bueno alcanzar el 100%.

2. **Corregir bugs de reliability**: Los 3 bugs existentes (uso de API síncrona en async y datetime.utcnow deprecado) no afectan funcionalidad, pero deberían corregirse en la siguiente iteración. La migración a `aiofiles` y `datetime.now(UTC)` es directa y eliminaría todos los bugs pendientes.

3. **Refactorizar code smells**: Los 2 code smells restantes son los mismos bugs de datetime. Una vez corregidos, el proyecto quedaría sin code smells.

4. **Expandir tests de integración**: Aunque tenemos buena cobertura unitaria, sería valioso agregar tests de integración end-to-end que prueben flujos completos como: subir video → procesar → descargar desde S3.

### Reflexión Final

Esta entrega nos enseñó que la calidad del código no es algo que se logra una vez y se olvida. Requiere atención constante. Cuando en la Entrega 2 priorizamos el despliegue sobre los tests, el coverage bajó a 78.4%. En esta entrega, al priorizar la calidad, no solo recuperamos el coverage sino que lo mejoramos significativamente.

Lo más valioso no son los números (98.8%), sino el cambio de mentalidad: ahora escribimos tests desde el inicio, no como algo opcional. Esto hace que el código sea más robusto, más fácil de mantener y más seguro para refactorizar. SonarQube no es solo un checklist que hay que pasar, es una herramienta que nos ayuda a identificar deuda técnica antes de que se vuelva un problema real.
