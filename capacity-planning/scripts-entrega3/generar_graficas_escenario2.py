#!/usr/bin/env python3
"""
Script para generar gráficas del Escenario 2 - Upload de Videos
"""

import matplotlib.pyplot as plt
import numpy as np

print("📊 Generador de Gráficas - Escenario 2")
print("=" * 60)

# Datos del test completado
test_results = {
    'upload_success_rate': 100.0,
    'upload_time_p95': 1022.80,  # ms
    'upload_time_avg': 994.00,   # ms
    'videos_uploaded': 2,
    'test_duration': 3,  # minutos
    'concurrent_users': 2,
}

# Configuración de estilo
plt.style.use('seaborn-v0_8-darkgrid')
fig = plt.figure(figsize=(14, 10))

# ============================================================================
# Gráfica 1: Tasa de Éxito de Upload
# ============================================================================
ax1 = plt.subplot(2, 2, 1)

categories = ['Uploads\nExitosos', 'Uploads\nFallidos']
values = [test_results['upload_success_rate'], 100 - test_results['upload_success_rate']]
colors = ['#2ecc71', '#e74c3c']

wedges, texts, autotexts = ax1.pie(values, labels=categories, autopct='%1.1f%%',
                                     colors=colors, startangle=90,
                                     textprops={'fontsize': 12, 'fontweight': 'bold'})

ax1.set_title(f'Tasa de Éxito de Uploads\n({test_results["videos_uploaded"]} videos totales)',
              fontsize=13, fontweight='bold')

# ============================================================================
# Gráfica 2: Tiempo de Upload
# ============================================================================
ax2 = plt.subplot(2, 2, 2)

metrics = ['Promedio', 'p95']
times = [test_results['upload_time_avg'], test_results['upload_time_p95']]
colors_bars = ['#3498db', '#e67e22']

bars = ax2.bar(metrics, times, color=colors_bars, alpha=0.7,
               edgecolor='black', linewidth=1.5)

# Agregar valores en las barras
for bar, value in zip(bars, times):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height,
             f'{value:.1f} ms',
             ha='center', va='bottom', fontsize=11, fontweight='bold')

ax2.set_ylabel('Tiempo (ms)', fontsize=11)
ax2.set_title('Tiempo de Upload de Videos', fontsize=13, fontweight='bold')
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim(bottom=0)

# ============================================================================
# Gráfica 3: Configuración del Test
# ============================================================================
ax3 = plt.subplot(2, 2, 3)

config_metrics = ['Usuarios\nConcurrentes', 'Duración\n(minutos)', 'Videos\nSubidos']
config_values = [test_results['concurrent_users'],
                 test_results['test_duration'],
                 test_results['videos_uploaded']]
colors_config = ['#9b59b6', '#1abc9c', '#f39c12']

bars = ax3.bar(config_metrics, config_values, color=colors_config, alpha=0.7,
               edgecolor='black', linewidth=1.5)

for bar, value in zip(bars, config_values):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height,
             f'{int(value)}',
             ha='center', va='bottom', fontsize=12, fontweight='bold')

ax3.set_ylabel('Valor', fontsize=11)
ax3.set_title('Configuración del Test', fontsize=13, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_ylim(bottom=0)

# ============================================================================
# Gráfica 4: Throughput de Upload
# ============================================================================
ax4 = plt.subplot(2, 2, 4)

# Calcular throughput
videos_per_minute = test_results['videos_uploaded'] / test_results['test_duration']
avg_upload_seconds = test_results['upload_time_avg'] / 1000

throughput_data = [
    ('Videos/minuto', videos_per_minute),
    ('Tiempo Upload\nPromedio (s)', avg_upload_seconds),
]

labels = [x[0] for x in throughput_data]
values = [x[1] for x in throughput_data]
colors_th = ['#3498db', '#e67e22']

bars = ax4.barh(labels, values, color=colors_th, alpha=0.7,
                edgecolor='black', linewidth=1.5)

for bar, value in zip(bars, values):
    width = bar.get_width()
    ax4.text(width, bar.get_y() + bar.get_height()/2.,
             f' {value:.2f}',
             ha='left', va='center', fontsize=12, fontweight='bold')

ax4.set_xlabel('Valor', fontsize=11)
ax4.set_title('Métricas de Throughput', fontsize=13, fontweight='bold')
ax4.grid(True, alpha=0.3, axis='x')

# ============================================================================
# Título general y guardar
# ============================================================================
plt.suptitle('Análisis de Capacidad - Escenario 2: Upload y Cola de Procesamiento\nTest de 3 minutos (2 usuarios concurrentes)',
             fontsize=16, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0, 1, 0.99])

output_file = '../results-entrega3/graficas_escenario2.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✅ Gráfica guardada en: {output_file}")

print("\n" + "=" * 60)
print("🎉 ¡Gráficas generadas exitosamente!")
print("=" * 60)
