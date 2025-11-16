/**
 * Escenario 1: Prueba de Capacidad de la Capa Web - Entrega 4
 *
 * Objetivo: Determinar el número máximo de usuarios concurrentes
 * que puede soportar la capa web (ALB + ASG + EC2) con la nueva
 * arquitectura SQS (sin Celery/Redis).
 *
 * Estrategia: Solo endpoints ligeros (GET/POST), sin uploads pesados
 *
 * Cambios vs Entrega 3:
 * - Backend ahora usa SQS en lugar de Celery/Redis
 * - Workers escalan automáticamente (1-3 instancias)
 * - Validación de que SQS funciona correctamente bajo carga
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Métricas personalizadas
const errorRate = new Rate('errors');
const latencyTrend = new Trend('latency');
const successfulRequests = new Counter('successful_requests');

// Configuración base - CAMBIAR ESTE URL POR TU ALB DNS
const BASE_URL = __ENV.BASE_URL || 'http://anb-video-alb-1505800447.us-east-1.elb.amazonaws.com';

// Configuración de las pruebas progresivas
export const options = {
  scenarios: {
    // Prueba 1: Smoke Test (5 usuarios)
    smoke_test: {
      executor: 'constant-vus',
      vus: 5,
      duration: '2m',
      startTime: '0s',
      tags: { test_type: 'smoke' },
    },

    // Prueba 2: Carga Moderada (50 usuarios)
    moderate_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 50 },  // Ramp up to 50 users
        { duration: '3m', target: 50 },  // Stay at 50 for 3 minutes
        { duration: '1m', target: 0 },   // Ramp down to 0
      ],
      startTime: '2m',
      tags: { test_type: 'moderate' },
    },

    // Prueba 3: Carga Alta (100 usuarios)
    high_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 100 },
        { duration: '3m', target: 100 },
        { duration: '1m', target: 0 },
      ],
      startTime: '7m',
      tags: { test_type: 'high' },
    },

    // Prueba 4: Estrés (150 usuarios)
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 150 },
        { duration: '3m', target: 150 },
        { duration: '1m', target: 0 },
      ],
      startTime: '12m',
      tags: { test_type: 'stress' },
    },
  },

  thresholds: {
    'http_req_duration': ['p(95)<1000'], // 95% of requests should be below 1s
    'errors': ['rate<0.05'],              // Error rate should be below 5%
    'http_req_failed': ['rate<0.05'],     // Failed requests should be below 5%
  },
};

// Usuarios de prueba (deben ser creados previamente con el script de setup)
const TEST_USERS = [
  { email: 'test1@anb.com', password: 'Test123!' },
  { email: 'test2@anb.com', password: 'Test123!' },
  { email: 'test3@anb.com', password: 'Test123!' },
  { email: 'test4@anb.com', password: 'Test123!' },
  { email: 'test5@anb.com', password: 'Test123!' },
];

// Función auxiliar para obtener un usuario aleatorio
function getRandomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

// Función para hacer login y obtener token
function login() {
  const user = getRandomUser();
  const payload = JSON.stringify({
    email: user.email,
    password: user.password,
  });

  const params = {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',
  };

  const res = http.post(`${BASE_URL}/api/auth/login`, payload, params);

  const success = check(res, {
    'login successful': (r) => r.status === 200,
    'has access token': (r) => r.json('access_token') !== undefined,
  });

  errorRate.add(!success);

  return success ? res.json('access_token') : null;
}

// Función principal de prueba
export default function () {
  // Simulación de diferentes tipos de requests
  const requestType = Math.random();

  if (requestType < 0.1) {
    // 10% - Health Check
    const res = http.get(`${BASE_URL}/health`, { timeout: '10s' });
    const success = check(res, {
      'health check OK': (r) => r.status === 200,
    });
    errorRate.add(!success);
    latencyTrend.add(res.timings.duration);
    if (success) successfulRequests.add(1);

  } else if (requestType < 0.4) {
    // 30% - Listar Videos Públicos
    const res = http.get(`${BASE_URL}/api/public/videos`, { timeout: '30s' });
    const success = check(res, {
      'list videos OK': (r) => r.status === 200,
    });
    errorRate.add(!success);
    latencyTrend.add(res.timings.duration);
    if (success) successfulRequests.add(1);

  } else if (requestType < 0.7) {
    // 30% - Ver Ranking
    const res = http.get(`${BASE_URL}/api/public/rankings`, { timeout: '30s' });
    const success = check(res, {
      'ranking OK': (r) => r.status === 200,
    });
    errorRate.add(!success);
    latencyTrend.add(res.timings.duration);
    if (success) successfulRequests.add(1);

  } else {
    // 30% - Login + Ver Mis Videos
    const token = login();

    if (token) {
      const params = {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        timeout: '30s',
      };

      const res = http.get(`${BASE_URL}/api/videos`, params);
      const success = check(res, {
        'my videos OK': (r) => r.status === 200,
      });
      errorRate.add(!success);
      latencyTrend.add(res.timings.duration);
      if (success) successfulRequests.add(1);
    }
  }

  // Pausa aleatoria entre requests (simular comportamiento humano)
  sleep(Math.random() * 2 + 1); // Entre 1 y 3 segundos
}

// Función que se ejecuta al final de todas las pruebas
export function handleSummary(data) {
  return {
    'capacity-planning/results-entrega4/escenario1_summary.json': JSON.stringify(data),
    stdout: textSummary(data, { indent: '  ', enableColors: true }),
  };
}

// Función auxiliar para crear el resumen de texto
function textSummary(data, options) {
  let output = '\n';
  output += '================================================================================\n';
  output += '  ESCENARIO 1: CAPA WEB - ENTREGA 4 (SQS) - RESULTADOS FINALES\n';
  output += '================================================================================\n\n';

  // Mostrar resumen de métricas clave
  const metrics = data.metrics;

  if (metrics.http_reqs) {
    output += `Total HTTP Requests: ${metrics.http_reqs.values.count}\n`;
  }

  if (metrics.http_req_duration) {
    output += `\nLatency:\n`;
    output += `  Min: ${metrics.http_req_duration.values.min.toFixed(2)} ms\n`;
    output += `  Avg: ${metrics.http_req_duration.values.avg.toFixed(2)} ms\n`;
    output += `  p50: ${metrics.http_req_duration.values.med.toFixed(2)} ms\n`;
    output += `  p90: ${metrics.http_req_duration.values['p(90)'].toFixed(2)} ms\n`;
    output += `  p95: ${metrics.http_req_duration.values['p(95)'].toFixed(2)} ms\n`;
    output += `  Max: ${metrics.http_req_duration.values.max.toFixed(2)} ms\n`;
  }

  if (metrics.http_req_failed) {
    const failRate = (metrics.http_req_failed.values.rate * 100).toFixed(2);
    output += `\nHTTP Request Failure Rate: ${failRate}%\n`;
  }

  if (metrics.errors) {
    const errRate = (metrics.errors.values.rate * 100).toFixed(2);
    output += `Custom Error Rate: ${errRate}%\n`;
  }

  output += '\n';
  output += '================================================================================\n';
  output += '  Nota: Esta prueba valida la capa web con la nueva arquitectura SQS.\n';
  output += '  Los workers ahora escalan automáticamente basados en la profundidad de cola.\n';
  output += '================================================================================\n';

  return output;
}
