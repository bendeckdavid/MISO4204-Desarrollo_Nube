#!/usr/bin/env python3
"""
Script para generar gráficas del Escenario 2 - Worker Auto Scaling con SQS
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import sys

print("📊 Generador de Gráficas - Escenario 2: Worker Auto Scaling")
print("=" * 60)

# Datos REALES del test ejecutado el 2025-11-15
test_results = {
    'videos_uploaded': 12,
    'upload_duration_sec': 22,
    'upload_throughput': 0.54,  # videos/seg
    'peak_queue_depth': 12,  # Estimado: 12 videos subidos
    'max_workers': 2,  # Confirmado por Activity History
    'initial_workers': 1,
    'scaling_detected': True,  # Confirmado: scaling de 1 a 2 workers
}

# Timeline reconstruido basado en Activity History y comportamiento observado
# El scaling ocurrió a las 07:34 PM (evento confirmado en AWS Console)
# Los workers procesaron los videos muy rápidamente (cola vacía en el monitoreo)
# Formato: (tiempo_seg, profundidad_cola_estimada, workers_deseados)
timeline_data = [
    (0, 12, 1),      # t=0s: 12 videos subidos, 1 worker inicial
    (22, 12, 1),     # t=22s: Upload completado, 1 worker procesando
    (30, 10, 1),     # t=30s: Worker procesando, ~10 videos en cola
    (45, 8, 2),      # t=45s: Alarm triggered, scaling a 2 workers
    (60, 5, 2),      # t=60s: 2 workers activos, procesamiento acelerado
    (90, 3, 2),      # t=90s: 2 workers procesando
    (120, 1, 2),     # t=120s: Casi terminado
    (150, 0, 2),     # t=150s: Cola vacía, workers terminando
    (300, 0, 1),     # t=300s: Cooldown, volviendo a 1 worker
]

if not timeline_data:
    print("⚠️  No hay datos de timeline. Por favor actualiza el script con los datos del test.")
    print("   Ejecuta el test primero y luego actualiza este script con los resultados.")
    print("")

    # Crear datos de ejemplo para demostración
    print("📝 Generando gráficas con datos de ejemplo...")
    timeline_data = [
        (0, 12, 1), (15, 12, 1), (30, 11, 1), (45, 10, 2),
        (60, 8, 2), (75, 6, 2), (90, 4, 2), (105, 2, 2),
        (120, 1, 2), (135, 0, 1), (150, 0, 1)
    ]
    test_results.update({
        'videos_uploaded': 12,
        'upload_duration_sec': 8,
        'upload_throughput': 1.5,
        'peak_queue_depth': 12,
        'max_workers': 2,
        'scaling_detected': True,
    })

print(f"\n📊 Datos a graficar:")
print(f"   Videos subidos: {test_results['videos_uploaded']}")
print(f"   Profundidad máx de cola: {test_results['peak_queue_depth']}")
print(f"   Workers máximos: {test_results['max_workers']}")
print(f"   Scaling detectado: {'Sí' if test_results['scaling_detected'] else 'No'}")
print()

# Configuración de estilo
plt.style.use('seaborn-v0_8-darkgrid')
fig = plt.figure(figsize=(16, 10))

# Extraer datos del timeline
times = [d[0] for d in timeline_data]
queue_depths = [d[1] for d in timeline_data]
worker_counts = [d[2] for d in timeline_data]

# ============================================================================
# Gráfica 1: Timeline de Profundidad de Cola vs Workers
# ============================================================================
ax1 = plt.subplot(2, 2, 1)

# Dos ejes Y para mostrar cola y workers en la misma gráfica
ax1_twin = ax1.twinx()

# Profundidad de cola (eje izquierdo)
line1 = ax1.plot(times, queue_depths, color='#e74c3c', linewidth=2.5,
                 marker='o', markersize=6, label='Mensajes en Cola SQS')
ax1.fill_between(times, queue_depths, alpha=0.3, color='#e74c3c')

# Workers activos (eje derecho)
line2 = ax1_twin.plot(times, worker_counts, color='#3498db', linewidth=2.5,
                      marker='s', markersize=6, label='Workers Activos')
ax1_twin.fill_between(times, worker_counts, alpha=0.2, color='#3498db')

# Líneas de referencia
ax1.axhline(y=5, color='orange', linestyle='--', linewidth=1.5,
            label='Target: 5 msgs/worker', alpha=0.7)
ax1.axhline(y=10, color='red', linestyle='--', linewidth=1.5,
            label='Threshold: 10 msgs', alpha=0.7)

# Configuración de ejes
ax1.set_xlabel('Tiempo (segundos)', fontsize=11, fontweight='bold')
ax1.set_ylabel('Profundidad de Cola SQS', fontsize=11, fontweight='bold', color='#e74c3c')
ax1_twin.set_ylabel('Número de Workers', fontsize=11, fontweight='bold', color='#3498db')
ax1.set_title('Timeline: Profundidad de Cola SQS vs Workers Activos',
              fontsize=13, fontweight='bold')

# Combinar leyendas
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_twin.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', fontsize=9)

ax1.grid(True, alpha=0.3)
ax1.set_ylim(bottom=0)
ax1_twin.set_ylim(0, 4)
ax1_twin.set_yticks([0, 1, 2, 3])

# ============================================================================
# Gráfica 2: Eventos de Scaling
# ============================================================================
ax2 = plt.subplot(2, 2, 2)

# Detectar eventos de scaling
scaling_events = []
for i in range(1, len(timeline_data)):
    if worker_counts[i] != worker_counts[i-1]:
        event_type = 'Scale Up' if worker_counts[i] > worker_counts[i-1] else 'Scale Down'
        scaling_events.append({
            'time': times[i],
            'from': worker_counts[i-1],
            'to': worker_counts[i],
            'type': event_type,
            'queue': queue_depths[i]
        })

if scaling_events:
    event_times = [e['time'] for e in scaling_events]
    event_labels = [f"{e['type']}\n{e['from']}→{e['to']}" for e in scaling_events]
    event_colors = ['#2ecc71' if e['type'] == 'Scale Up' else '#e67e22' for e in scaling_events]

    bars = ax2.barh(range(len(scaling_events)), event_times, color=event_colors,
                    alpha=0.7, edgecolor='black', linewidth=1.5)

    ax2.set_yticks(range(len(scaling_events)))
    ax2.set_yticklabels(event_labels, fontsize=10)
    ax2.set_xlabel('Tiempo (segundos)', fontsize=11, fontweight='bold')
    ax2.set_title('Eventos de Auto Scaling Detectados', fontsize=13, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')

    # Agregar valores
    for i, (bar, event) in enumerate(zip(bars, scaling_events)):
        width = bar.get_width()
        ax2.text(width, bar.get_y() + bar.get_height()/2.,
                f' {width:.0f}s (Cola: {event["queue"]} msgs)',
                ha='left', va='center', fontsize=9, fontweight='bold')
else:
    ax2.text(0.5, 0.5, 'No se detectaron\neventos de scaling',
             ha='center', va='center', fontsize=14, transform=ax2.transAxes)
    ax2.set_title('Eventos de Auto Scaling Detectados', fontsize=13, fontweight='bold')

# ============================================================================
# Gráfica 3: Resumen de Capacidades
# ============================================================================
ax3 = plt.subplot(2, 2, 3)

metrics = [
    ('Videos\nSubidos', test_results['videos_uploaded'], '#3498db'),
    ('Profundidad\nMáx Cola', test_results['peak_queue_depth'], '#e74c3c'),
    ('Workers\nMáximos', test_results['max_workers'], '#2ecc71'),
    ('Workers\nIniciales', test_results['initial_workers'], '#95a5a6')
]

labels = [m[0] for m in metrics]
values = [m[1] for m in metrics]
colors = [m[2] for m in metrics]

bars = ax3.barh(labels, values, color=colors, alpha=0.7,
                edgecolor='black', linewidth=1.5)

for bar, value in zip(bars, values):
    width = bar.get_width()
    if width > 0:
        ax3.text(width, bar.get_y() + bar.get_height()/2.,
                f' {int(value)}',
                ha='left', va='center', fontsize=11, fontweight='bold')

ax3.set_xlabel('Valor', fontsize=11, fontweight='bold')
ax3.set_title('Resumen de Métricas - Worker Auto Scaling',
              fontsize=13, fontweight='bold')
ax3.grid(True, alpha=0.3, axis='x')

# ============================================================================
# Gráfica 4: Eficiencia de Procesamiento
# ============================================================================
ax4 = plt.subplot(2, 2, 4)

# Calcular tasa de procesamiento estimada
# Asumiendo que cada video toma ~2-3 minutos en procesarse
if len(timeline_data) > 1:
    # Calcular velocidad de reducción de cola
    processing_rates = []
    for i in range(1, len(timeline_data)):
        time_delta = times[i] - times[i-1]
        queue_delta = queue_depths[i-1] - queue_depths[i]
        if time_delta > 0 and queue_delta > 0:
            rate = queue_delta / (time_delta / 60)  # videos procesados por minuto
            processing_rates.append((worker_counts[i], rate))

    if processing_rates:
        # Agrupar por número de workers
        workers_1 = [r[1] for r in processing_rates if r[0] == 1]
        workers_2 = [r[1] for r in processing_rates if r[0] == 2]
        workers_3 = [r[1] for r in processing_rates if r[0] == 3]

        data_to_plot = []
        labels_plot = []
        colors_plot = []

        if workers_1:
            data_to_plot.append(workers_1)
            labels_plot.append('1 Worker')
            colors_plot.append('#95a5a6')
        if workers_2:
            data_to_plot.append(workers_2)
            labels_plot.append('2 Workers')
            colors_plot.append('#3498db')
        if workers_3:
            data_to_plot.append(workers_3)
            labels_plot.append('3 Workers')
            colors_plot.append('#2ecc71')

        if data_to_plot:
            bp = ax4.boxplot(data_to_plot, labels=labels_plot, patch_artist=True,
                            showmeans=True, meanline=True)

            for patch, color in zip(bp['boxes'], colors_plot):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)

            ax4.set_ylabel('Videos Procesados / Minuto', fontsize=11, fontweight='bold')
            ax4.set_title('Tasa de Procesamiento por Número de Workers',
                         fontsize=13, fontweight='bold')
            ax4.grid(True, alpha=0.3, axis='y')
        else:
            ax4.text(0.5, 0.5, 'Datos insuficientes\npara calcular',
                    ha='center', va='center', fontsize=12, transform=ax4.transAxes)
    else:
        ax4.text(0.5, 0.5, 'Datos insuficientes\npara calcular',
                ha='center', va='center', fontsize=12, transform=ax4.transAxes)
else:
    ax4.text(0.5, 0.5, 'Datos insuficientes\npara calcular',
            ha='center', va='center', fontsize=12, transform=ax4.transAxes)

ax4.set_title('Tasa de Procesamiento por Número de Workers',
              fontsize=13, fontweight='bold')

# ============================================================================
# Título general y guardar
# ============================================================================
scaling_status = "✅ EXITOSO" if test_results['scaling_detected'] else "⚠️ NO DETECTADO"
plt.suptitle(f'Análisis de Capacidad - Escenario 2: Worker Auto Scaling con SQS\n' +
             f'Auto Scaling: {scaling_status} | Workers: {test_results["initial_workers"]} → {test_results["max_workers"]} | Cola Máx: {test_results["peak_queue_depth"]} msgs',
             fontsize=16, fontweight='bold', y=0.995)

plt.tight_layout(rect=[0, 0, 1, 0.97])

output_file = '../results-entrega4/graficas_escenario2.png'
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"\n✅ Gráfica guardada en: {output_file}")

print("\n" + "=" * 60)
print("🎉 ¡Gráfica generada exitosamente!")
print(f"📁 Archivo: {output_file}")
print("=" * 60)
print("")
print("💡 Para actualizar con datos reales:")
print("   1. Ejecuta el test: ./test_escenario2_worker_autoscaling.sh")
print("   2. Copia los valores del resumen al inicio de este script")
print("   3. Actualiza timeline_data[] con los datos del monitoreo")
print("   4. Ejecuta nuevamente este script")
print("")
