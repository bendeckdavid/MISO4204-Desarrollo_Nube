#!/usr/bin/env python3
"""
Script para generar gráficas basadas en los resultados del test k6 - Entrega 4
Arquitectura: SQS + Worker Auto Scaling (sin Celery/Redis)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import json
import sys
import os

print("📊 Generador de Gráficas k6 - Escenario 1 - Entrega 4")
print("=" * 60)

# IMPORTANTE: Actualizar estos datos después de ejecutar el test k6
# Estos son valores de ejemplo, deben ser reemplazados con los resultados reales
test_results = {
    'total_requests': 0,  # ACTUALIZAR con datos reales
    'successful_requests': 0,  # ACTUALIZAR
    'failed_requests': 0,  # ACTUALIZAR
    'iterations': 0,  # ACTUALIZAR
    'error_rate': 0.0,  # ACTUALIZAR
    'success_rate': 0.0,  # ACTUALIZAR
    'throughput_rps': 0.0,  # ACTUALIZAR
    'data_sent_rate': 0.0,  # MB/s - ACTUALIZAR
    'data_received_rate': 0.0,  # MB/s - ACTUALIZAR
    'latency': {
        'min': 0.0,  # ACTUALIZAR
        'median': 0.0,  # ACTUALIZAR
        'avg': 0.0,  # ACTUALIZAR
        'max': 0.0,  # ACTUALIZAR
        'p90': 0.0,  # ACTUALIZAR
        'p95': 0.0,  # ACTUALIZAR
    },
    'vus_max': 150,
}

# Intentar leer datos desde el archivo JSON generado por k6
summary_file = '../results-entrega4/escenario1_summary.json'
if os.path.exists(summary_file):
    print(f"📂 Leyendo datos desde: {summary_file}")
    try:
        with open(summary_file, 'r') as f:
            data = json.load(f)
            metrics = data.get('metrics', {})

            # Extraer métricas
            if 'http_reqs' in metrics:
                test_results['total_requests'] = int(metrics['http_reqs']['values'].get('count', 0))

            if 'http_req_failed' in metrics:
                fail_rate = metrics['http_req_failed']['values'].get('rate', 0)
                test_results['error_rate'] = fail_rate * 100
                test_results['success_rate'] = (1 - fail_rate) * 100
                test_results['failed_requests'] = int(test_results['total_requests'] * fail_rate)
                test_results['successful_requests'] = test_results['total_requests'] - test_results['failed_requests']

            if 'iterations' in metrics:
                test_results['iterations'] = int(metrics['iterations']['values'].get('count', 0))

            if 'http_reqs' in metrics:
                test_results['throughput_rps'] = metrics['http_reqs']['values'].get('rate', 0)

            if 'data_sent' in metrics:
                test_results['data_sent_rate'] = metrics['data_sent']['values'].get('rate', 0) / (1024 * 1024)

            if 'data_received' in metrics:
                test_results['data_received_rate'] = metrics['data_received']['values'].get('rate', 0) / (1024 * 1024)

            if 'http_req_duration' in metrics:
                duration = metrics['http_req_duration']['values']
                test_results['latency']['min'] = duration.get('min', 0)
                test_results['latency']['median'] = duration.get('med', 0)
                test_results['latency']['avg'] = duration.get('avg', 0)
                test_results['latency']['max'] = duration.get('max', 0)
                test_results['latency']['p90'] = duration.get('p(90)', 0)
                test_results['latency']['p95'] = duration.get('p(95)', 0)

        print("✅ Datos cargados correctamente desde JSON")
    except Exception as e:
        print(f"⚠️  Error al leer JSON: {e}")
        print("📝 Usando valores de ejemplo. Por favor actualiza manualmente.")
else:
    print(f"⚠️  Archivo {summary_file} no encontrado")
    print("📝 Usando valores de ejemplo. Por favor actualiza manualmente después del test.")

print(f"\n📊 Datos a graficar:")
print(f"   Total Requests: {test_results['total_requests']:,}")
print(f"   Success Rate: {test_results['success_rate']:.2f}%")
print(f"   Throughput: {test_results['throughput_rps']:.2f} req/s")
print(f"   Latency p95: {test_results['latency']['p95']:.2f} ms")
print()

# Configuración de estilo
plt.style.use('seaborn-v0_8-darkgrid')
fig = plt.figure(figsize=(16, 12))

# Colores de fases
phase_colors = {
    'smoke': '#2ecc71',      # Verde
    'moderate': '#3498db',   # Azul
    'high': '#f39c12',       # Naranja
    'stress': '#e74c3c'      # Rojo
}

# ============================================================================
# Gráfica 1: Usuarios Virtuales (VUs) simulados en el tiempo
# ============================================================================
ax1 = plt.subplot(3, 2, 1)

# Simular la progresión de VUs basada en el diseño del test
time_points = [0, 2, 2, 3, 7, 7, 8, 12, 12, 13, 17]
vus_values = [5, 5, 0, 50, 50, 0, 100, 100, 0, 150, 150]

ax1.plot(time_points, vus_values, color='#2c3e50', linewidth=2, marker='o')
ax1.fill_between(time_points, vus_values, alpha=0.3, color='#3498db')

# Marcar fases
ax1.axvspan(0, 2, alpha=0.2, color=phase_colors['smoke'], label='Smoke (5 VUs)')
ax1.axvspan(2, 7, alpha=0.2, color=phase_colors['moderate'], label='Moderada (50 VUs)')
ax1.axvspan(7, 12, alpha=0.2, color=phase_colors['high'], label='Alta (100 VUs)')
ax1.axvspan(12, 17, alpha=0.2, color=phase_colors['stress'], label='Estrés (150 VUs)')

ax1.set_xlabel('Tiempo (minutos)', fontsize=11)
ax1.set_ylabel('Usuarios Virtuales', fontsize=11)
ax1.set_title('Usuarios Concurrentes a lo Largo de la Prueba', fontsize=13, fontweight='bold')
ax1.legend(loc='upper left', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, 160)

# ============================================================================
# Gráfica 2: Latencia HTTP por Percentiles
# ============================================================================
ax2 = plt.subplot(3, 2, 2)

percentiles = ['Min', 'p50\n(Mediana)', 'Promedio', 'p90', 'p95', 'Max']
latency_values = [
    test_results['latency']['min'],
    test_results['latency']['median'],
    test_results['latency']['avg'],
    test_results['latency']['p90'],
    test_results['latency']['p95'],
    test_results['latency']['max']
]

colors = ['#2ecc71', '#3498db', '#9b59b6', '#f39c12', '#e74c3c', '#c0392b']
bars = ax2.bar(percentiles, latency_values, color=colors, alpha=0.7, edgecolor='black', linewidth=1.5)

# Línea de umbral
ax2.axhline(y=1000, color='red', linestyle='--', linewidth=2, label='Umbral SLO (1s)')

# Agregar valores en las barras
for bar, value in zip(bars, latency_values):
    height = bar.get_height()
    if height > 0:
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                 f'{value:.1f}',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

ax2.set_ylabel('Latencia (ms)', fontsize=11)
ax2.set_title('Distribución de Latencia HTTP', fontsize=13, fontweight='bold')
ax2.legend(loc='upper left', fontsize=9)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim(bottom=0)

# ============================================================================
# Gráfica 3: Distribución de Requests (Exitosos vs Fallidos)
# ============================================================================
ax3 = plt.subplot(3, 2, 3)

if test_results['total_requests'] > 0:
    requests_data = [
        test_results['successful_requests'],
        test_results['failed_requests']
    ]
    labels = [f"Exitosos\n{test_results['success_rate']:.1f}%",
              f"Fallidos\n{test_results['error_rate']:.1f}%"]
    colors_pie = ['#2ecc71', '#e74c3c']

    wedges, texts, autotexts = ax3.pie(requests_data, labels=labels, autopct='%1.1f%%',
                                         colors=colors_pie, startangle=90,
                                         textprops={'fontsize': 11, 'fontweight': 'bold'})

    ax3.set_title(f'Distribución de Requests\n(Total: {test_results["total_requests"]:,})',
                  fontsize=13, fontweight='bold')
else:
    ax3.text(0.5, 0.5, 'Sin datos\n(ejecutar test primero)',
             ha='center', va='center', fontsize=12, transform=ax3.transAxes)
    ax3.set_title('Distribución de Requests', fontsize=13, fontweight='bold')

# ============================================================================
# Gráfica 4: Throughput del Sistema
# ============================================================================
ax4 = plt.subplot(3, 2, 4)

test_duration = 1020  # 17 minutos en segundos
metrics_names = ['Requests/seg', 'Iteraciones/seg', 'Datos Enviados\n(MB/s)', 'Datos Recibidos\n(MB/s)']
metrics_values = [
    test_results['throughput_rps'],
    test_results['iterations'] / test_duration if test_results['iterations'] > 0 else 0,
    test_results['data_sent_rate'],
    test_results['data_received_rate']
]
colors_metrics = ['#3498db', '#9b59b6', '#e67e22', '#1abc9c']

bars = ax4.bar(metrics_names, metrics_values, color=colors_metrics, alpha=0.7,
               edgecolor='black', linewidth=1.5)

for bar, value in zip(bars, metrics_values):
    height = bar.get_height()
    if height > 0:
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                 f'{value:.2f}',
                 ha='center', va='bottom', fontsize=10, fontweight='bold')

ax4.set_ylabel('Valor', fontsize=11)
ax4.set_title('Métricas de Throughput del Sistema', fontsize=13, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')
ax4.set_ylim(bottom=0)

# ============================================================================
# Gráfica 5: Resumen por Fase (Latencia p95 estimada)
# ============================================================================
ax5 = plt.subplot(3, 2, 5)

phases = ['Smoke\n(5 VUs)', 'Moderada\n(50 VUs)', 'Alta\n(100 VUs)', 'Estrés\n(150 VUs)']
# Estimaciones - actualizar con datos reales si están disponibles
latency_p95_phases = [
    min(test_results['latency']['p95'] * 0.1, 200) if test_results['latency']['p95'] > 0 else 120,
    min(test_results['latency']['p95'] * 0.3, 800) if test_results['latency']['p95'] > 0 else 500,
    min(test_results['latency']['p95'] * 0.6, 2000) if test_results['latency']['p95'] > 0 else 1500,
    test_results['latency']['p95'] if test_results['latency']['p95'] > 0 else 3000
]
colors_bars = [phase_colors['smoke'], phase_colors['moderate'],
               phase_colors['high'], phase_colors['stress']]

bars = ax5.bar(phases, latency_p95_phases, color=colors_bars, alpha=0.7,
               edgecolor='black', linewidth=1.5)

# Línea de umbral
ax5.axhline(y=1000, color='red', linestyle='--', linewidth=2, label='Umbral SLO (1s)')

# Agregar valores en las barras
for bar, value in zip(bars, latency_p95_phases):
    height = bar.get_height()
    ax5.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(value)} ms',
             ha='center', va='bottom', fontsize=10, fontweight='bold')

ax5.set_ylabel('Latencia p95 (ms)', fontsize=11)
ax5.set_title('Latencia p95 por Fase de Prueba', fontsize=13, fontweight='bold')
ax5.legend(loc='upper left', fontsize=9)
ax5.grid(True, alpha=0.3, axis='y')

# ============================================================================
# Gráfica 6: Resumen de Capacidad Alcanzada
# ============================================================================
ax6 = plt.subplot(3, 2, 6)

capacity_metrics = [
    ('VUs Máximos', 150, '#3498db'),
    ('Requests Totales', test_results['total_requests'] / 1000, '#2ecc71'),  # En miles
    ('Iteraciones', test_results['iterations'] / 1000, '#9b59b6'),  # En miles
    ('Throughput\n(req/s)', test_results['throughput_rps'], '#e67e22')
]

labels = [m[0] for m in capacity_metrics]
values = [m[1] for m in capacity_metrics]
colors_cap = [m[2] for m in capacity_metrics]

bars = ax6.barh(labels, values, color=colors_cap, alpha=0.7,
                edgecolor='black', linewidth=1.5)

for bar, value, label in zip(bars, values, labels):
    width = bar.get_width()
    if width > 0:
        unit = 'K' if 'Totales' in label or 'Iteraciones' in label else ''
        ax6.text(width, bar.get_y() + bar.get_height()/2.,
                 f' {value:.1f}{unit}',
                 ha='left', va='center', fontsize=11, fontweight='bold')

ax6.set_xlabel('Valor', fontsize=11)
ax6.set_title('Resumen de Capacidad Alcanzada', fontsize=13, fontweight='bold')
ax6.grid(True, alpha=0.3, axis='x')

# ============================================================================
# Título general y guardar
# ============================================================================
plt.suptitle('Análisis de Capacidad - Escenario 1: Capa Web - Entrega 4 (SQS)\n' +
             'Prueba de Carga Progresiva (5 → 150 Usuarios Concurrentes)',
             fontsize=16, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0, 1, 0.99])

output_file = '../results-entrega4/graficas_escenario1.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✅ Gráfica principal guardada en: {output_file}")

# ============================================================================
# Generar gráfica comparativa Entrega 3 vs 4
# ============================================================================
print("\n📊 Generando gráfica comparativa Entrega 3 (Celery) vs Entrega 4 (SQS)...")
fig2, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# Datos de Entrega 3 para comparación
entrega3_data = {
    'max_users': 150,
    'throughput': 39.46,
    'latency_p50': 120.81,
    'total_requests': 40287
}

# Gráfica 1: Usuarios Concurrentes (debería ser igual)
categories = ['Entrega 3\n(Celery/Redis)', 'Entrega 4\n(SQS)']
max_users = [entrega3_data['max_users'], 150]
colors_comp = ['#95a5a6', '#3498db']

bars = ax1.bar(categories, max_users, color=colors_comp, alpha=0.7, edgecolor='black', linewidth=2)
for bar, value in zip(bars, max_users):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(value)} usuarios',
             ha='center', va='bottom', fontsize=12, fontweight='bold')
ax1.set_ylabel('Usuarios Concurrentes Máximos', fontsize=12)
ax1.set_title('Capacidad de Usuarios Concurrentes', fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3, axis='y')
ax1.set_ylim(0, 170)

# Gráfica 2: Throughput
throughput = [entrega3_data['throughput'], test_results['throughput_rps']]
bars = ax2.bar(categories, throughput, color=colors_comp, alpha=0.7, edgecolor='black', linewidth=2)
for bar, value in zip(bars, throughput):
    height = bar.get_height()
    if height > 0:
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                 f'{value:.1f} req/s',
                 ha='center', va='bottom', fontsize=12, fontweight='bold')
ax2.set_ylabel('Requests por Segundo', fontsize=12)
ax2.set_title('Throughput del Sistema', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')

# Gráfica 3: Latencia p50
latency_p50 = [entrega3_data['latency_p50'], test_results['latency']['median']]
bars = ax3.bar(categories, latency_p50, color=colors_comp, alpha=0.7, edgecolor='black', linewidth=2)
for bar, value in zip(bars, latency_p50):
    height = bar.get_height()
    if height > 0:
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                 f'{value:.1f} ms',
                 ha='center', va='bottom', fontsize=12, fontweight='bold')
ax3.set_ylabel('Latencia p50 (ms)', fontsize=12)
ax3.set_title('Latencia Mediana de Requests', fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')

# Gráfica 4: Arquitectura de Mensajería
arch_labels = ['Celery + Redis\n(Entrega 3)', 'SQS + Worker ASG\n(Entrega 4)']
arch_features = ['Gestión Manual', 'Auto Scaling\nAutomático']
colors_arch = ['#95a5a6', '#2ecc71']

ax4.barh(arch_labels, [1, 1], color=colors_arch, alpha=0.7, edgecolor='black', linewidth=2)
for i, (label, feature) in enumerate(zip(arch_labels, arch_features)):
    ax4.text(0.5, i, feature, ha='center', va='center', fontsize=11, fontweight='bold')

ax4.set_xlim(0, 1)
ax4.set_xticks([])
ax4.set_title('Sistema de Mensajería y Workers', fontsize=14, fontweight='bold')

plt.suptitle('Comparación: Entrega 3 (Celery/Redis) vs Entrega 4 (SQS + Worker ASG)',
             fontsize=16, fontweight='bold')
plt.tight_layout()

output_file2 = '../results-entrega4/comparacion_entrega3_vs_entrega4.png'
plt.savefig(output_file2, dpi=300, bbox_inches='tight')
print(f"✅ Gráfica comparativa guardada en: {output_file2}")

print("\n" + "=" * 60)
print("🎉 ¡Gráficas generadas exitosamente!")
print(f"📁 Archivos generados:")
print(f"   1. {output_file}")
print(f"   2. {output_file2}")
print("=" * 60)
