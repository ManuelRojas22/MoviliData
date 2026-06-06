# 🚦 MoviliData OS

## Plataforma Inteligente de Movilidad Urbana

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-5.0-green)
![MySQL](https://img.shields.io/badge/MySQL-Database-orange)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5-purple)
![Machine Learning](https://img.shields.io/badge/Machine%20Learning-Random%20Forest-red)

---

## 📖 Descripción

MoviliData OS es una plataforma web inteligente diseñada para analizar, visualizar y predecir condiciones de movilidad urbana utilizando tecnologías de desarrollo web, bases de datos, geolocalización y aprendizaje automático.

La plataforma busca apoyar la toma de decisiones relacionadas con el tráfico vehicular mediante el análisis de datos en tiempo real y la generación de predicciones sobre posibles congestiones e incidentes viales.

Este proyecto fue desarrollado como una solución tecnológica enfocada en ciudades inteligentes, integrando múltiples fuentes de información para ofrecer una experiencia completa de monitoreo urbano.

---

# 🎯 Problema Identificado

Las ciudades modernas enfrentan diversos desafíos relacionados con la movilidad:

* Congestión vehicular en horas pico.
* Accidentes de tránsito frecuentes.
* Incremento de los tiempos de desplazamiento.
* Falta de herramientas predictivas.
* Escasa integración entre datos climáticos y tráfico.
* Dificultad para identificar rutas óptimas.

Estas situaciones afectan directamente la calidad de vida de los ciudadanos y generan pérdidas económicas y ambientales.

---

# 💡 Solución Propuesta

MoviliData OS centraliza información relacionada con:

* Tráfico urbano.
* Condiciones climáticas.
* Incidentes viales.
* Datos históricos.
* Predicciones inteligentes.

La plataforma procesa estos datos para generar información útil que permita anticipar problemas y optimizar la movilidad.

---

# 🎯 Objetivo General

Desarrollar una plataforma web inteligente capaz de analizar y predecir condiciones de movilidad urbana mediante el uso de tecnologías de análisis de datos, geolocalización y Machine Learning.

---

# 🎯 Objetivos Específicos

### 📊 Analizar datos de tráfico

Recopilar y procesar información relacionada con:

* Flujo vehicular.
* Velocidad promedio.
* Niveles de congestión.
* Historial de tráfico.

### 🧠 Implementar modelos predictivos

Aplicar algoritmos de Machine Learning para estimar:

* Congestión futura.
* Riesgo vial.
* Comportamiento del tráfico.

### 🗺️ Optimizar rutas

Generar rutas más eficientes considerando:

* Distancia.
* Tiempo estimado.
* Congestión.
* Riesgo vial.

### 🚨 Emitir alertas preventivas

Detectar eventos críticos para notificar oportunamente a los usuarios.

---

# ✨ Funcionalidades

## 📈 Dashboard Inteligente

Panel central que permite visualizar:

* Estado actual del tráfico.
* Indicadores de congestión.
* Alertas activas.
* Estadísticas urbanas.

---

## 🚗 Monitoreo de Tráfico

Permite observar:

* Velocidad promedio.
* Flujo vehicular.
* Congestión por sectores.
* Eventos recientes.

---

## 🧠 Predicción de Congestión

Utiliza Machine Learning para calcular:

* Congestión esperada.
* Riesgo de incidentes.
* Tendencias futuras.

---

## 🗺️ Mapas Interactivos

Visualización geográfica mediante:

* Marcadores dinámicos.
* Heatmaps.
* Rutas optimizadas.
* Zonas de riesgo.

---

## 🔥 Heatmaps

Representación visual de:

* Sectores con mayor tráfico.
* Concentración de incidentes.
* Áreas críticas.

---

## 🚨 Sistema de Alertas

Generación automática de alertas relacionadas con:

* Accidentes.
* Congestión severa.
* Eventos climáticos.
* Riesgos viales.

---

## 📊 Reportes Estadísticos

Permite consultar:

* Datos históricos.
* Tendencias semanales.
* Comparativas mensuales.
* Indicadores de rendimiento.

---

# 🔄 Flujo de Funcionamiento

## 1. Recolección de Datos

El sistema obtiene información desde múltiples fuentes.

### 🌦️ Datos Climáticos

* Temperatura.
* Humedad.
* Precipitación.
* Condiciones atmosféricas.

### 🚗 Datos de Tráfico

* Velocidad promedio.
* Flujo vehicular.
* Congestión.

### 🚨 Eventos

* Accidentes.
* Obras viales.
* Incidentes reportados.

---

## 2. Procesamiento

Los datos son procesados mediante:

* Pandas.
* NumPy.
* Limpieza de datos.
* Transformación de variables.

---

## 3. Predicción

El modelo de Machine Learning analiza:

* Hora.
* Día.
* Clima.
* Historial.

Y genera:

* Índice de congestión.
* Riesgo estimado.
* Predicción de tráfico.

---

## 4. Visualización

Los resultados son mostrados mediante:

* Gráficas dinámicas.
* Mapas interactivos.
* Indicadores KPI.
* Dashboards.

---

## 5. Toma de Decisiones

El usuario puede:

* Consultar el estado actual.
* Identificar riesgos.
* Optimizar rutas.
* Anticipar problemas.

---

# 🧠 Machine Learning

## Modelo Implementado

Random Forest Regressor

### Variables de Entrada

* Hora del día.
* Día de la semana.
* Temperatura.
* Precipitaciones.
* Incidentes recientes.
* Congestión histórica.

### Resultados

* Predicción de congestión.
* Índice de riesgo.
* Nivel de confianza.

---

# 🏗️ Arquitectura del Sistema

```text
┌─────────────────────┐
│      Frontend       │
│ HTML CSS Bootstrap  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│      Django         │
│ Backend + APIs      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│       MySQL         │
│ Base de Datos       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Machine Learning    │
│ Random Forest       │
└─────────────────────┘
```

---

# 🛠️ Tecnologías Utilizadas

## Backend

* Python 3.11
* Django 5
* MySQL

## Frontend

* HTML5
* CSS3
* Bootstrap 5
* JavaScript

## Ciencia de Datos

* Pandas
* NumPy
* Scikit-Learn

## Visualización

* Chart.js
* Leaflet.js
* Heatmaps

## APIs

* OpenStreetMap
* Open-Meteo
* OSRM
* TomTom Traffic

---

# 📂 Estructura del Proyecto

```text
MoviliData/
│
├── apps/
├── templates/
├── static/
├── media/
├── models/
├── predictions/
├── maps/
├── alerts/
├── requirements.txt
└── manage.py
```

---

# ⚙️ Instalación

## Clonar repositorio

```bash
git clone https://github.com/usuario/movilidata.git
cd movilidata
```

## Crear entorno virtual

```bash
python -m venv venv
```

### Windows

```bash
venv\Scripts\activate
```

### Linux/Mac

```bash
source venv/bin/activate
```

## Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# 🗄️ Configuración de Base de Datos

```sql
CREATE DATABASE movilidata_os;
```

Archivo `.env`

```env
SECRET_KEY=tu_clave
DEBUG=True

DB_NAME=movilidata_os
DB_USER=root
DB_PASSWORD=
DB_HOST=localhost
DB_PORT=3306
```

---

# 🚀 Ejecución

Migraciones:

```bash
python manage.py migrate
```

Crear administrador:

```bash
python manage.py createsuperuser
```

Iniciar servidor:

```bash
python manage.py runserver
```

Acceder:

```text
http://127.0.0.1:8000
```

---

# 🔒 Seguridad

La plataforma implementa:

* Autenticación de usuarios.
* Control de sesiones.
* Protección CSRF.
* Validación de formularios.
* Gestión segura de datos.

---

# 📈 Impacto Esperado

MoviliData OS busca contribuir a:

* Reducir tiempos de desplazamiento.
* Mejorar la movilidad urbana.
* Disminuir riesgos viales.
* Facilitar decisiones basadas en datos.
* Impulsar ciudades inteligentes.

---

# 👨‍💻 Autor

**Manuel Rojas**

Tecnólogo ADSO – SENA

Proyecto académico enfocado en:

* Desarrollo Full Stack.
* Ciencia de Datos.
* Machine Learning.
* Bases de Datos.
* Movilidad Inteligente.

---

# 📄 Licencia

Este proyecto fue desarrollado con fines educativos, académicos y de investigación.

© 2026 MoviliData OS - Todos los derechos reservados.
