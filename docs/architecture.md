# Arquitectura

MoviliData OS usa una Arquitectura Monolitica Modular en Capas.

## Capas

- Presentacion: templates HTML5, Bootstrap 5.3.0, CSS3 y JavaScript Vanilla.
- Logica de negocio: `services.py` por app.
- Servicios externos: clientes HTTP para ArcGIS Medellin y Open-Meteo.
- Persistencia: Django ORM con MySQL y scripts SQL en `database/`.
- Procesamiento: Pandas, NumPy y Scikit-learn para predicciones.
- APIs internas: vistas Django que retornan JSON.

## Modulos

- `dashboard`: resumen ejecutivo, metricas y landing.
- `traffic`: trafico y velocidades por zona.
- `routes`: rutas seguras recomendadas.
- `predictions`: prediccion de congestion.
- `alerts`: alertas preventivas.
- `maps`: zonas de riesgo y heatmaps.
- `users`: acceso demo y perfil.

## Datos externos

La capa de servicios consulta fuentes publicas cuando estan disponibles y mantiene fallback local para demos offline o entornos sin red.
