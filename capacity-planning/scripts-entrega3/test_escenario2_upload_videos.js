/**
 * Escenario 2 MÍNIMO: Upload y Capacidad de Cola
 *
 * Test ultra-ligero para validar:
 * 1. Upload de videos funcional
 * 2. Videos entran en cola de procesamiento
 * 3. Worker puede recibir tareas
 *
 * NO espera procesamiento completo (demasiado tiempo)
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { SharedArray } from 'k6/data';

// Métricas
const uploadSuccessRate = new Rate('upload_success');
const uploadTimeMs = new Trend('upload_time_ms');
const videosUploaded = new Counter('videos_uploaded');
const videosPending = new Counter('videos_pending');

const BASE_URL = 'http://anb-video-alb-760991728.us-east-1.elb.amazonaws.com';

// Test MUY corto - solo 3 minutos total
export const options = {
  scenarios: {
    upload_only: {
      executor: 'constant-vus',
      vus: 2,  // Solo 2 usuarios
      duration: '3m',  // 3 minutos
      tags: { test_type: 'upload_minimal' },
    },
  },
  thresholds: {
    'upload_success': ['rate>0.70'],  // 70% uploads exitosos
    'upload_time_ms': ['p(95)<15000'],  // 95% en < 15 segundos
  },
};

// Usuarios
const TEST_USERS = new SharedArray('users', function () {
  return [
    { email: 'test1@anb.com', password: 'Test123!' },
    { email: 'test2@anb.com', password: 'Test123!' },
  ];
});

// Video pequeño ~500KB (más rápido de subir)
function generateSmallVideoData() {
  const size = 500 * 1024; // 500 KB
  const buffer = new Uint8Array(size);
  for (let i = 0; i < size; i++) {
    buffer[i] = (i * 17 + 42) % 256;
  }
  return buffer;
}

let cachedVideoData = null;
function getTestVideoData() {
  if (!cachedVideoData) {
    cachedVideoData = generateSmallVideoData();
  }
  return cachedVideoData;
}

function getRandomUser() {
  return TEST_USERS[Math.floor(Math.random() * TEST_USERS.length)];
}

function login() {
  const user = getRandomUser();
  const payload = JSON.stringify({
    email: user.email,
    password: user.password,
  });

  const res = http.post(`${BASE_URL}/api/auth/login`, payload, {
    headers: { 'Content-Type': 'application/json' },
    timeout: '20s',
  });

  const success = check(res, {
    'login successful': (r) => r.status === 200,
  });

  if (!success) {
    return null;
  }

  return res.json('access_token');
}

function uploadVideo(token) {
  const videoData = getTestVideoData();
  const timestamp = Date.now();
  const randomId = Math.floor(Math.random() * 10000);

  const boundary = '----WebKitFormBoundary' + randomId;
  const filename = `test-video-${timestamp}-${randomId}.mp4`;

  // Crear multipart body
  const lineBreak = '\r\n';
  let body = '';

  // Campo: title
  body += `--${boundary}${lineBreak}`;
  body += `Content-Disposition: form-data; name="title"${lineBreak}${lineBreak}`;
  body += `Load Test Video ${timestamp}${lineBreak}`;

  // Campo: file
  body += `--${boundary}${lineBreak}`;
  body += `Content-Disposition: form-data; name="file"; filename="${filename}"${lineBreak}`;
  body += `Content-Type: video/mp4${lineBreak}${lineBreak}`;

  let binaryString = '';
  for (let i = 0; i < videoData.length; i++) {
    binaryString += String.fromCharCode(videoData[i]);
  }
  body += binaryString;
  body += lineBreak;
  body += `--${boundary}--${lineBreak}`;

  const uploadStart = Date.now();
  const res = http.post(`${BASE_URL}/api/videos/upload`, body, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': `multipart/form-data; boundary=${boundary}`,
    },
    timeout: '30s',
  });
  const uploadDuration = Date.now() - uploadStart;

  const success = check(res, {
    'upload status is 201': (r) => r.status === 201,
    'response has video_id': (r) => {
      try {
        return r.json('video_id') !== undefined;
      } catch (e) {
        return false;
      }
    },
  });

  uploadSuccessRate.add(success);
  uploadTimeMs.add(uploadDuration);

  if (!success) {
    console.error(`Upload failed: ${res.status}`);
    return null;
  }

  const videoId = res.json('video_id');
  videosUploaded.add(1);
  console.log(`✅ Video uploaded: ${videoId} (${uploadDuration}ms)`);

  return videoId;
}

// Verificar que el video entró en pending
function checkVideoPending(token, videoId) {
  const res = http.get(`${BASE_URL}/api/videos/${videoId}`, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    timeout: '10s',
  });

  if (res.status === 200) {
    try {
      const video = res.json();
      if (video.status === 'pending' || video.status === 'processing') {
        videosPending.add(1);
        console.log(`📋 Video ${videoId} in queue: ${video.status}`);
      }
    } catch (e) {}
  }
}

// Test principal - SOLO upload y verificación de cola
export default function () {
  const token = login();
  if (!token) {
    sleep(3);
    return;
  }

  const videoId = uploadVideo(token);
  if (!videoId) {
    sleep(3);
    return;
  }

  // Solo verificar que entró en cola (rápido)
  sleep(2);
  checkVideoPending(token, videoId);

  // Pausa antes de siguiente iteración
  const pause = Math.random() * 5 + 5; // 5-10 segundos
  console.log(`💤 Waiting ${Math.round(pause)}s\n`);
  sleep(pause);
}

export function handleSummary(data) {
  return {
    'capacity-planning/results-entrega3/escenario2_minimo_summary.json': JSON.stringify(data),
    stdout: textSummary(data),
  };
}

function textSummary(data) {
  let output = '\n';
  output += '================================================================================\n';
  output += '  ESCENARIO 2 MÍNIMO: UPLOAD Y COLA DE PROCESAMIENTO\n';
  output += '================================================================================\n\n';

  const metrics = data.metrics;

  if (metrics.upload_success) {
    output += `Upload Success Rate: ${(metrics.upload_success.values.rate * 100).toFixed(2)}%\n`;
  }
  if (metrics.upload_time_ms) {
    output += `Upload Time (p95): ${metrics.upload_time_ms.values['p(95)'].toFixed(2)}ms\n`;
    output += `Upload Time (avg): ${metrics.upload_time_ms.values.avg.toFixed(2)}ms\n`;
  }
  if (metrics.videos_uploaded) {
    output += `Videos Uploaded: ${metrics.videos_uploaded.values.count}\n`;
  }
  if (metrics.videos_pending) {
    output += `Videos in Queue: ${metrics.videos_pending.values.count}\n`;
  }

  output += '\nNota: Este test solo valida upload y entrada en cola.\n';
  output += 'No espera procesamiento completo (requiere demasiado tiempo).\n';
  output += '\n';
  return output;
}
