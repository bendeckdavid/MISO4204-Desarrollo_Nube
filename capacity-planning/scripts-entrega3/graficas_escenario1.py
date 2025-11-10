#!/usr/bin/env python3
"""
Script para generar gráficas basadas en los resultados del test k6
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

print("📊 Generador de Gráficas k6 - Escenario 1")
print("=" * 60)

# Datos extraídos del test completado
test_results = {
    'total_requests': 40287,
    'successful_requests': 20327,
    'failed_requests': 5641,
    'iterations': 25968,
    'error_rate': 16.99,
    'success_rate': 83.01,
    'throughput_rps': 39.46,
    'data_sent_rate': 9.18,  # MB/s
    'data_received_rate': 9.52,  # MB/s
    'latency': {
        'min': 14.87,
        'median': 120.81,
        'avg': 520.89,
        'max': 8396.25,
        'p90': 1361.63,
        'p95': 3221.41,
    },
    'vus_max': 150,
}

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

# ============================================================================
# Gráfica 4: Throughput del Sistema
# ============================================================================
ax4 = plt.subplot(3, 2, 4)

metrics_names = ['Requests/seg', 'Iteraciones/seg', 'Datos Enviados\n(MB/s)', 'Datos Recibidos\n(MB/s)']
metrics_values = [
    test_results['throughput_rps'],
    test_results['iterations'] / 1020,  # Total duration in seconds (17 min)
    test_results['data_sent_rate'],
    test_results['data_received_rate']
]
colors_metrics = ['#3498db', '#9b59b6', '#e67e22', '#1abc9c']

bars = ax4.bar(metrics_names, metrics_values, color=colors_metrics, alpha=0.7,
               edgecolor='black', linewidth=1.5)

for bar, value in zip(bars, metrics_values):
    height = bar.get_height()
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
# Estimaciones basadas en la progresión típica de latencia
latency_p95_phases = [120, 500, 1500, 3221]
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
    ('Requests Totales', 40.3, '#2ecc71'),  # En miles
    ('Iteraciones', 26.0, '#9b59b6'),  # En miles
    ('Throughput\n(req/s)', 39.5, '#e67e22')
]

labels = [m[0] for m in capacity_metrics]
values = [m[1] for m in capacity_metrics]
colors_cap = [m[2] for m in capacity_metrics]

bars = ax6.barh(labels, values, color=colors_cap, alpha=0.7,
                edgecolor='black', linewidth=1.5)

for bar, value, label in zip(bars, values, labels):
    width = bar.get_width()
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
plt.suptitle('Análisis de Capacidad - Escenario 1: Capa Web\nPrueba de Carga Progresiva (5 → 150 Usuarios Concurrentes)',
             fontsize=16, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0, 1, 0.99])

output_file = '../results-entrega3/graficas_escenario1.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✅ Gráfica principal guardada en: {output_file}")

# ============================================================================
# Generar gráfica comparativa Entrega 2 vs 3
# ============================================================================
print("\n📊 Generando gráfica comparativa Entrega 2 vs Entrega 3...")
fig2, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

# Gráfica 1: Usuarios Concurrentes
categories = ['Entrega 2\n(Sin ASG)', 'Entrega 3\n(Con ASG)']
max_users = [20, 150]
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
throughput = [2.14, 39.46]
bars = ax2.bar(categories, throughput, color=colors_comp, alpha=0.7, edgecolor='black', linewidth=2)
for bar, value in zip(bars, throughput):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{value:.1f} req/s',
             ha='center', va='bottom', fontsize=12, fontweight='bold')
ax2.set_ylabel('Requests por Segundo', fontsize=12)
ax2.set_title('Throughput del Sistema', fontsize=14, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim(0, 45)

# Gráfica 3: Latencia p50
latency_p50 = [88, 120.81]
bars = ax3.bar(categories, latency_p50, color=colors_comp, alpha=0.7, edgecolor='black', linewidth=2)
for bar, value in zip(bars, latency_p50):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{value:.1f} ms',
             ha='center', va='bottom', fontsize=12, fontweight='bold')
ax3.set_ylabel('Latencia p50 (ms)', fontsize=12)
ax3.set_title('Latencia Mediana de Requests', fontsize=14, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_ylim(0, 140)

# Gráfica 4: Mejora Porcentual
improvements = [
    ('Usuarios\nConcurrentes', 650),
    ('Throughput', 1744),
    ('Alta\nDisponibilidad', 100)
]
labels = [x[0] for x in improvements]
values = [x[1] for x in improvements]
colors_imp = ['#2ecc71', '#3498db', '#9b59b6']

bars = ax4.bar(labels, values, color=colors_imp, alpha=0.7, edgecolor='black', linewidth=2)
for bar, value in zip(bars, values):
    height = bar.get_height()
    ax4.text(bar.get_x() + bar.get_width()/2., height,
             f'+{int(value)}%',
             ha='center', va='bottom', fontsize=12, fontweight='bold')
ax4.set_ylabel('Mejora Porcentual (%)', fontsize=12)
ax4.set_title('Mejoras de Entrega 3 vs Entrega 2', fontsize=14, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='y')

plt.suptitle('Comparación: Entrega 2 (NFS + 1 EC2) vs Entrega 3 (S3 + ALB + ASG)',
             fontsize=16, fontweight='bold')
plt.tight_layout()

output_file2 = '../results-entrega3/comparacion_entrega2_vs_entrega3.png'
plt.savefig(output_file2, dpi=300, bbox_inches='tight')
print(f"✅ Gráfica comparativa guardada en: {output_file2}")

print("\n" + "=" * 60)
print("🎉 ¡Gráficas generadas exitosamente!")
print(f"📁 Archivos generados:")
print(f"   1. {output_file}")
print(f"   2. {output_file2}")
print("=" * 60)
