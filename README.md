# MoviliData OS

MoviliData OS es una plataforma full stack de movilidad inteligente para Medellin construida con Django, Bootstrap 5.3.0, JavaScript Vanilla, MySQL, Leaflet.js, Chart.js, Pandas, NumPy y Scikit-learn.

## Capacidades

- Dashboard operativo con metricas urbanas, mapa, heatmap y alertas.
- APIs internas funcionales: `/api/traffic`, `/api/routes`, `/api/alerts`, `/api/predictions`, `/api/maps`.
- Prediccion simple de congestion con Scikit-learn correlacionando hora, lluvia y riesgo.
- Base de datos MySQL centralizada en `movilidata_os`.
- PWA con cache parcial y pantalla offline.
- Integracion comercial opcional con TomTom Traffic API para velocidades y congestion por segmento.
- Cliente para fuentes publicas: ArcGIS de Alcaldia de Medellin para incidentes y Open-Meteo para clima, con fallback demo.

## Instalacion

Instalacion automatica en Windows:

```bat
install.bat
```

El instalador crea `.venv`, genera `.env`, instala dependencias, carga `database/movilidata_os.sql`, ejecuta migraciones, crea `admin/admin123`, abre el navegador y levanta el servidor.

Instalacion manual:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
mysql -u root -p < database/movilidata_os.sql
python manage.py migrate
python manage.py runserver
```

Usuario demo:

```text
admin / admin123
```

El superusuario se crea automaticamente al abrir `/users/login/` si la base ya fue migrada.

## Configuracion MySQL

La aplicacion usa una sola base:

```text
movilidata_os
localhost:3306
usuario root
password vacio
```

Las variables estan en `.env`.

Para activar datos comerciales de trafico en tiempo real, agrega una clave de TomTom:

```env
TOMTOM_API_KEY=tu_clave_tomtom
```

Sin esa clave, el sistema usa estimaciones locales cacheadas para cargar rapido.

## Estructura

El proyecto sigue una arquitectura monolitica modular en capas: apps Django por dominio, servicios de negocio, endpoints API, templates de presentacion, assets estaticos, SQL centralizado en `database/movilidata_os.sql`, datos, documentacion y PWA.
