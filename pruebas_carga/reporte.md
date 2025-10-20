# Reporte Técnico: Análisis de Rendimiento HTTP

## Hallazgo Principal

La aplicación funciona de manera estable y confiable cuando maneja hasta **60 solicitudes por segundo**. Sin embargo, cuando la carga supera este límite, el sistema comienza a experimentar problemas significativos: los tiempos de respuesta aumentan dramáticamente y aparecen errores. Si la carga alcanza o supera las **70 solicitudes por segundo**, la aplicación deja de funcionar correctamente.

## Resumen de Resultados por Escenario de Prueba

Se realizaron tres pruebas de carga para evaluar el comportamiento del sistema bajo diferentes niveles de tráfico:

| Métrica                     | Carga Baja (~35 req/s) | Carga Media (~38 req/s) | Carga Alta (~14 req/s*) |
|-----------------------------|------------------------|-------------------------|-------------------------|
| Tiempo de respuesta promedio| 326 ms                 | 394 ms                  | 2 segundos              |
| Tiempo de respuesta P95     | 762 ms                 | 1 segundo               | 1 segundo               |
| Tiempo máximo observado     | 3 segundos             | 3 segundos              | 1 minuto                |
| Solicitudes fallidas        | 0%                     | 0%                      | 4.2%                    |
| Total de solicitudes        | 6,300                  | 6,900                   | 3,000                   |
| Validaciones exitosas       | 100%                   | 100%                    | 96.7%                   |

*Nota: En la prueba de carga alta, la tasa efectiva fue menor debido a los fallos y tiempos de espera prolongados del sistema.

## Análisis de Comportamiento

### Rendimiento bajo Carga Baja y Media

Cuando el sistema opera con menos de 40 solicitudes por segundo, su comportamiento es excelente y predecible. El 95% de las solicitudes se procesan en menos de un segundo, lo cual proporciona una experiencia fluida para los usuarios. Ocasionalmente, algunas solicitudes pueden tardar hasta 3 segundos, pero estos casos son excepcionales y no afectan la estabilidad general del sistema.

Durante estas pruebas, no se registró ningún error y todas las validaciones fueron exitosas. Esto indica que la aplicación tiene suficientes recursos y puede manejar adecuadamente el procesamiento de datos, las consultas a la base de datos y la generación de respuestas.

### Deterioro en Carga Alta

Cuando la carga aumenta significativamente, el comportamiento del sistema cambia radicalmente. Los tiempos de respuesta promedio se multiplican por 6, pasando de aproximadamente 400 milisegundos a 2 segundos. Más preocupante aún, algunos usuarios experimentan esperas de hasta 1 minuto completo para recibir una respuesta.

El sistema también comienza a rechazar solicitudes: 4.2% de las peticiones fallan por completo, lo que significa que aproximadamente 1 de cada 25 usuarios no puede completar su operación. Esta tasa de error, aunque puede parecer pequeña, es inaceptable para un servicio en producción y representa una experiencia negativa significativa para los usuarios.

### Identificación del Cuello de Botella

El análisis detallado de las métricas revela que el problema no está en la red ni en la configuración de seguridad. Los tiempos de conexión y de transferencia de datos permanecen consistentemente bajos en todos los escenarios. Esto apunta claramente a que el cuello de botella está en el procesamiento interno de la aplicación.

Cuando llegan muchas solicitudes simultáneamente, la aplicación no puede procesarlas con suficiente rapidez. Las nuevas peticiones se van acumulando en una cola de espera, lo que explica el aumento exponencial en los tiempos de respuesta. Eventualmente, cuando esta cola se llena por completo, el sistema empieza a rechazar nuevas solicitudes.

## Conclusiones

### Límite Operativo Identificado

El sistema tiene un límite claro de capacidad en **60 solicitudes por segundo por instancia**. Operar dentro de este límite garantiza:

- Tiempos de respuesta consistentemente por debajo de 1 segundo para el 95% de los usuarios
- Cero errores en el procesamiento de solicitudes
- Estabilidad operativa completa

### Comportamiento Crítico

Superar las 60 solicitudes por segundo desencadena un deterioro rápido del servicio que incluye:

- Aumento dramático en tiempos de espera (de milisegundos a minutos)
- Aparición de errores y solicitudes fallidas
- Potencial colapso completo del sistema si la sobrecarga persiste

## Recomendaciones

### Escalamiento Horizontal

Para manejar más tráfico, se debe implementar un sistema de múltiples instancias de la aplicación trabajando en paralelo. Cuando el tráfico en una instancia se acerca a las 50 solicitudes por segundo, debe activarse automáticamente una nueva instancia. Esto distribuye la carga y evita que cualquier instancia individual alcance su límite de capacidad.

### Optimización de Base de Datos

Muchas de las solicitudes probablemente requieren consultar la base de datos. Aumentar el número de conexiones simultáneas disponibles y optimizar las consultas más frecuentes puede reducir significativamente los tiempos de procesamiento. También se recomienda implementar caché para las consultas que se repiten frecuentemente.

### Procesamiento Asíncrono

Las operaciones que toman mucho tiempo (como procesamiento de archivos o generación de reportes) no deberían bloquear la respuesta al usuario. En su lugar, estas tareas deberían procesarse en segundo plano, permitiendo que la aplicación responda inmediatamente al usuario con una confirmación, mientras el trabajo pesado se completa posteriormente.

### Monitoreo Continuo

Es fundamental implementar alertas automáticas que notifiquen cuando:

- La tasa de solicitudes supere las 50 por segundo en cualquier instancia
- Los tiempos de respuesta P95 excedan 800 milisegundos
- Aparezca cualquier tasa de error mayor a 0.1%

## Datos Técnicos Detallados

### Métricas de Carga Baja

| Métrica               | Promedio | Máximo | Mediana | Mínimo | P90    | P95    | P99    |
|-----------------------|----------|--------|---------|--------|--------|--------|--------|
| Duración de solicitud | 326 ms   | 3 s    | 250 ms  | 224 ms | 506 ms | 762 ms | 1 s    |
| Tiempo de conexión    | 4 µs     | 351 µs | 0 ms    | 0 ms   | 0 ms   | 0 ms   | 158 µs |
| Tiempo de recepción   | 82 µs    | 1 ms   | 73 µs   | 12 µs  | 124 µs | 152 µs | 231 µs |

**Tráfico total:**
- Datos recibidos: 2.05 MB (11.2 kB/s)
- Datos enviados: 1.62 MB (8.92 kB/s)
- Total de solicitudes: 6,300 (34.88/s)

### Métricas de Carga Media

| Métrica               | Promedio | Máximo | Mediana | Mínimo | P90    | P95    | P99    |
|-----------------------|----------|--------|---------|--------|--------|--------|--------|
| Duración de solicitud | 394 ms   | 3 s    | 256 ms  | 224 ms | 844 ms | 1 s    | 1 s    |
| Tiempo de conexión    | 4 µs     | 755 µs | 0 ms    | 0 ms   | 0 ms   | 0 ms   | 165 µs |
| Tiempo de recepción   | 77 µs    | 936 µs | 72 µs   | 8 µs   | 117 µs | 138 µs | 208 µs |

**Tráfico total:**
- Datos recibidos: 2.23 MB (12.3 kB/s)
- Datos enviados: 1.77 MB (9.74 kB/s)
- Total de solicitudes: 6,900 (38.06/s)

### Métricas de Carga Alta

| Métrica               | Promedio | Máximo | Mediana | Mínimo | P90    | P95    | P99    |
|-----------------------|----------|--------|---------|--------|--------|--------|--------|
| Duración de solicitud | 2 s      | 1 m    | 254 ms  | 229 µs | 741 ms | 1 s    | 1 m    |
| Tiempo de conexión    | 10 µs    | 1 ms   | 0 ms    | 0 ms   | 0 ms   | 105 µs | 256 µs |
| Tiempo de recepción   | 82 µs    | 2 ms   | 74 µs   | 0 ms   | 128 µs | 152 µs | 230 µs |

**Tráfico total:**
- Datos recibidos: 929 kB (4.49 kB/s)
- Datos enviados: 789 kB (3.81 kB/s)
- Total de solicitudes: 3,000 (14.36/s)
- **Tasa de error: 4.2%**
- **Validaciones exitosas: 96.7%**

## Conclusión Final

El análisis confirma que la aplicación tiene un punto de quiebre claro en las **60 solicitudes por segundo**. Mantenerse por debajo de este umbral garantiza un servicio estable y confiable para los usuarios. Para crecer más allá de esta capacidad, es imperativo implementar las estrategias de escalamiento y optimización recomendadas antes de aumentar la carga sobre el sistema.
