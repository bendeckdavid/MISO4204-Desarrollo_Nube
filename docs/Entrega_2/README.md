# Entrega 2 - Despliegue en AWS

Documentación completa del despliegue de la aplicación ANB Rising Stars Showcase en Amazon Web Services.

## Contenido de la Entrega

Esta entrega incluye la migración de la aplicación desde un entorno de contenedores Docker local a una arquitectura de nube pública en AWS, utilizando múltiples instancias EC2 y servicios administrados.

## Documentos Disponibles

| Documento | Descripción | Enlace |
|-----------|-------------|--------|
| **Arquitectura AWS** | Descripción completa de la arquitectura de la solución en AWS, incluyendo diagramas de despliegue, componentes, servicios utilizados, y cambios respecto a la Entrega 1 | [ARQUITECTURA_AWS.md](ARQUITECTURA_AWS.md) |
| **Guía de Despliegue** | Guía paso a paso para desplegar manualmente toda la infraestructura en AWS, incluyendo VPC, Security Groups, EC2, RDS, y configuración de servicios | [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md) |
| **Análisis de Capacidad** | Resultados de pruebas de carga (Escenario 1 y 2), métricas de rendimiento, cuellos de botella identificados, y recomendaciones de escalabilidad | [../../capacity-planning/pruebas_de_carga_entrega2.md](../../capacity-planning/pruebas_de_carga_entrega2.md) |

## Scripts de Despliegue Automatizado

Los scripts de automatización para configurar cada componente están disponibles en:

```
deployment/ec2-setup/
├── 01-fileserver-setup.sh    # Configuración del File Server (NFS)
├── 02-webserver-setup.sh     # Configuración del Web Server (FastAPI + Nginx + Redis)
└── 03-worker-setup.sh        # Configuración del Worker (Celery + FFmpeg)
```

Cada script es idempotente y puede re-ejecutarse en caso de fallo.

## Arquitectura Desplegada

### Componentes Principales

```
Internet → Web Server (EC2) → Amazon RDS (PostgreSQL)
              ↓
         NFS Server (EC2)
              ↓
         Worker (EC2)
```

### Recursos de AWS

- **3 Instancias EC2 t3.small** (Web Server, Worker, File Server)
- **1 Instancia RDS db.t3.micro** (PostgreSQL 16)
- **1 VPC personalizada** con 2 subnets públicas
- **4 Security Groups** configurados con mínimo privilegio
- **1 Internet Gateway** para acceso público

### Especificaciones

| Componente | Instancia | vCPUs | RAM | Storage |
|------------|-----------|-------|-----|---------|
| Web Server | EC2 t3.small | 2 | 2 GiB | 50 GiB gp3 |
| Worker | EC2 t3.small | 2 | 2 GiB | 50 GiB gp3 |
| File Server | EC2 t3.small | 2 | 2 GiB | 50 GiB gp3 |
| Database | RDS db.t3.micro | 2 | 1 GiB | 20 GiB gp3 |

## Orden de Lectura Recomendado

Para entender completamente la solución, se recomienda leer los documentos en el siguiente orden:

1. **[ARQUITECTURA_AWS.md](ARQUITECTURA_AWS.md)** - Comenzar aquí
   - Entender la arquitectura de alto nivel
   - Ver diagramas de despliegue y componentes
   - Conocer las decisiones de diseño
   - Identificar cambios respecto a Entrega 1

2. **[AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md)** - Guía práctica
   - Seguir paso a paso para recrear la infraestructura
   - Entender la configuración de cada servicio
   - Aprender sobre Security Groups y networking
   - Troubleshooting de problemas comunes

3. **[pruebas_de_carga_entrega2.md](../../capacity-planning/pruebas_de_carga_entrega2.md)** - Análisis de performance
   - Ver resultados de pruebas de carga
   - Entender límites de capacidad actuales
   - Revisar recomendaciones de escalabilidad
   - Planear mejoras futuras

## Requisitos Cumplidos

### ✅ Despliegue de Componentes (50%)

- [x] Web Server configurado en EC2 con FastAPI, Gunicorn, Nginx, Redis
- [x] Worker configurado en EC2 con Celery y FFmpeg
- [x] File Server configurado en EC2 con NFS
- [x] Comunicación entre componentes mediante Security Groups
- [x] Scripts de automatización para cada componente

### ✅ Base de Datos (10%)

- [x] Amazon RDS PostgreSQL 16 configurado
- [x] Conectividad desde Web Server y Worker
- [x] Migraciones de base de datos aplicadas
- [x] Datos persistentes en RDS

### ✅ Requisitos Funcionales (10%)

- [x] Todos los endpoints funcionando en AWS
- [x] Autenticación JWT operativa
- [x] Upload y procesamiento de videos
- [x] Sistema de votación y rankings
- [x] Validación con Postman/Newman

### 📋 Documentación de Arquitectura (10%)

- [x] Modelo de despliegue (diagramas de infraestructura)
- [x] Modelo de componentes (diagramas de aplicación)
- [x] Explicación de servicios AWS utilizados
- [x] Cambios respecto a Entrega 1
- [x] Decisiones de diseño justificadas

### 📊 Análisis de Capacidad (20%)

- [ ] Escenario 1: Pruebas de estrés ejecutadas (10%)
- [ ] Escenario 2: Pruebas de estrés ejecutadas (10%)
- [ ] Análisis comparativo con Entrega 1
- [ ] Identificación de cuellos de botella
- [ ] Recomendaciones de escalabilidad

**Nota**: Los escenarios de pruebas de carga deben ser completados y documentados en [pruebas_de_carga_entrega2.md](../../capacity-planning/pruebas_de_carga_entrega2.md).

## Cambios Principales Respecto a Entrega 1

| Aspecto | Entrega 1 | Entrega 2 |
|---------|-----------|-----------|
| **Infraestructura** | Docker Compose local | AWS EC2 + RDS |
| **Networking** | Bridge network | VPC con Security Groups |
| **Base de datos** | PostgreSQL en contenedor | Amazon RDS PostgreSQL |
| **Almacenamiento** | Volumen Docker | NFS en EC2 dedicado |
| **Orquestación** | docker-compose.yml | Scripts bash + systemd |
| **Escalabilidad** | Limitada por hardware local | Escalable horizontalmente |
| **Acceso** | localhost:8080 | IP pública AWS |
| **Costo** | $0 (recursos locales) | ~$50-80/mes |

## Próximos Pasos

### Tareas Pendientes

1. **Ejecutar Pruebas de Carga**
   - Configurar K6 o herramienta similar
   - Ejecutar Escenario 1 (lecturas)
   - Ejecutar Escenario 2 (escrituras + procesamiento)
   - Documentar resultados en `pruebas_de_carga_entrega2.md`

2. **Monitoreo**
   - Configurar CloudWatch Dashboards
   - Crear alarmas para métricas críticas
   - Habilitar logs de aplicación en CloudWatch

3. **Seguridad**
   - Habilitar backups automáticos de RDS
   - Configurar AWS Budget y alarmas de costo
   - Rotar credenciales de RDS
   - Revisar Security Groups regularmente

4. **Optimización**
   - Implementar recomendaciones del análisis de capacidad
   - Ajustar configuración de Gunicorn/Celery según resultados
   - Considerar caching con Redis para consultas frecuentes

## Video de Sustentación

> **Enlace**: [Aquí se colocará el enlace al video de sustentación]
>
> _Duración máxima: 20 minutos_

**Contenido del video debe incluir:**
- Demostración de la aplicación corriendo en AWS
- Explicación de la arquitectura desplegada
- Pruebas de cada endpoint con diferentes parámetros
- Demostración de procesamiento de videos con diferentes características
- Revisión de logs y monitoreo
- Explicación de pruebas de carga (si ya se ejecutaron)

## Recursos Adicionales

### Documentación de AWS Consultada

- [Amazon EC2 User Guide](https://docs.aws.amazon.com/ec2/)
- [Amazon RDS User Guide](https://docs.aws.amazon.com/rds/)
- [Amazon VPC User Guide](https://docs.aws.amazon.com/vpc/)
- [Security Groups for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html)

### Herramientas Utilizadas

- **AWS Console**: Configuración manual de infraestructura
- **SSH**: Acceso a instancias EC2
- **systemd**: Gestión de servicios (FastAPI, Celery)
- **Poetry**: Gestión de dependencias Python
- **K6/Newman**: Pruebas de carga (por ejecutar)

## Contacto y Soporte

Para preguntas sobre esta entrega, consultar:
- **Guía de despliegue**: [AWS_DEPLOYMENT.md](AWS_DEPLOYMENT.md#troubleshooting)
- **Issues de GitHub**: [Repositorio del proyecto](https://github.com/bendeckdavid/MISO4204-Desarrollo_Nube/issues)

---

**Última actualización**: 2025-10-26
**Versión**: 1.0
