# API Docs

Todas las respuestas son JSON.

## GET `/api/dashboard`

Retorna metricas ejecutivas, clima y zonas.

## GET `/api/traffic`

Retorna congestion, velocidad promedio, ubicacion y estado por zona.

## GET `/api/routes`

Retorna rutas seguras con tiempo, distancia, riesgo y puntos geograficos.

## GET `/api/alerts`

Retorna alertas activas con nivel, descripcion y coordenadas.

## GET `/api/predictions?hour=18`

Retorna prediccion de congestion por zona para la hora indicada.

## GET `/api/maps`

Retorna centro del mapa y zonas de riesgo para marcadores y heatmap.
