# Manual Tecnico

## Requisitos

- Python 3.11+
- MySQL Server 8+
- MySQL Workbench opcional
- Navegador moderno

## Ejecucion

1. Instalar dependencias desde `requirements.txt`.
2. Ejecutar `database/movilidata_os.sql` en MySQL Workbench o con `mysql -u root -p < database/movilidata_os.sql`.
3. Ejecutar migraciones Django.
4. Levantar el servidor con `python manage.py runserver`.

## Responsive

Todas las media queries viven exclusivamente en `static/css/responsive.css`.

## PWA

El manifest y service worker estan en `pwa/`. Django sirve estos archivos desde `/pwa/`.

## Predicciones

`apps/predictions/services.py` construye un modelo `LinearRegression` usando variables de hora, lluvia y riesgo urbano.
