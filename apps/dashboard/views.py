import json
import logging
import os
import re
import time

import requests
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from .services import (
    city_summary,
    bootstrap_data,
    get_weather,
    calculate_delay_risk,
    calculate_route_risk,
    COMUNAS_PRINCIPALES,
    COMUNAS_COORDS,
    route_options,
    _translate_maneuver,
)
from apps.routes.services import _geocode_nominatim, _get_osrm_route, _enrich_with_real_data, _haversine_km

logger = logging.getLogger(__name__)

MOVIBOT_SYSTEM_PROMPT_TEMPLATE = """Eres MóviBot, el asistente virtual de MoviliData OS, una plataforma web de movilidad urbana para Medellín, Colombia. Tu rol es ayudar a los usuarios a entender la información de la plataforma: riesgos de retrasos, riesgos en ruta, congestión, alertas, rutas seguras, zonas de riesgo, predicciones y clima.

La plataforma tiene estas secciones:
- Dashboard: indicadores en tiempo real: ⏱️ Riesgo de retrasos y 🛣️ Riesgo en ruta, más zona de riesgo en el mapa.
- Tráfico: registros por zona con nivel de congestión (0–100), velocidad promedio y fuente del dato.
- Mapas y Zonas de Riesgo: visualización geográfica de zonas críticas con puntaje de riesgo y motivo. Los incidentes aparecen marcados en el mapa cuando sus coordenadas caen dentro de un radio de 15 km del centroide de cada comuna.
- Alertas: incidentes viales activos clasificados por nivel (alta, media, baja) con zona y descripción.
- Rutas Seguras: rutas con origen, destino, distancia en km, tiempo estimado y puntaje de riesgo.
- Predicciones: estimaciones de congestión futura por zona, probabilidad de lluvia y confianza del modelo (incluidas abajo si el usuario pregunta).
- Clima: condiciones meteorológicas integradas con el análisis de tráfico.

DATOS ACTUALES DE LA PLATAFORMA (generados {generated_at}):
{live_data}

Reglas de respuesta:
- Responde siempre en español, de forma clara y directa.
- USA los DATOS ACTUALES arriba para responder con cifras reales. Los indicadores principales son ⏱️ Riesgo de retrasos y 🛣️ Riesgo en ruta. Si preguntan por el estado general de la ciudad, menciona ambos con su valor y nivel (Bajo/Medio/Alto).
- Si preguntan "¿cómo está el tráfico?", responde con el Riesgo de retrasos y el Riesgo en ruta, y menciona el detalle de vías cerradas y obras si aplica.
- Si preguntan por congestión en una zona específica, busca su nombre en los datos de zonas y da su congestión, velocidad y riesgo.
- Si preguntan por congestión general, usa el valor de Riesgo de retrasos y el promedio de congestión de los datos.
- Si preguntan por incidentes activos, usa el desglose de incidentes TomTom (congestión, vías cerradas, obras).
- Si preguntan qué pasará más tarde o mañana, usa los DATOS PREDICCIONES incluidos abajo para dar una respuesta con cifras concretas por zona. Si el usuario especifica una hora exacta, responde con los datos de esa hora. Si no hay predicciones disponibles, menciona que no hay datos de pronóstico ahora.
- Si preguntan por el clima de una zona específica, aclara que el dato de clima disponible es a nivel de toda Medellín, no desglosado por zona, y da ese dato general.
- Si algo no está en los DATOS ACTUALES, dilo claramente y dirige a la sección correspondiente.
- No inventes datos concretos (velocidades, porcentajes, nombres de calles) que no estén en los DATOS ACTUALES.
- Si hay una RUTA CALCULADA en los datos (origen → destino), responde directamente con los pasos de navegación en orden, la distancia, el tiempo estimado y el nivel de riesgo. Sé directo como un GPS: sin rodeos, máximo 5 pasos. Si no hay pasos listados, no los inventes; menciona solo distancia, tiempo y riesgo. No repitas la sugerencia de "ir a Rutas Seguras".
- Sé conciso: máximo 3 a 4 oraciones salvo que pidan más detalle.
- Tono profesional pero cercano. Nunca alarmista."""


# Alias comunes para nombrar zonas/comunas en lenguaje natural
ZONE_ALIASES = {
    "poblado": "El Poblado",
    "el poblado": "El Poblado",
    "laureles": "Laureles",
    "belen": "Belen",
    "belén": "Belen",
    "centro": "Centro",
    "la candelaria": "Centro",
    "robledo": "Robledo",
    "guayabal": "Guayabal",
    "castilla": "Castilla",
    "manrique": "Manrique",
    "aranjuez": "Aranjuez",
    "buenos aires": "Buenos Aires",
    "villa hermosa": "Villa Hermosa",
    "san javier": "San Javier",
    "la america": "La América",
    "la américa": "La América",
    "doce de octubre": "Doce de Octubre",
    "santa cruz": "Santa Cruz",
    "popular": "Popular",
}


def _detect_hour_in_text(text):
    """Extrae una hora (0-23) mencionada en el texto del usuario, o None."""
    if not text:
        return None
    import re
    lowered = text.lower()
    # Patrones: "a las 6pm", "a las 18:00", "6 pm", "18 horas", "a las 5"
    m = re.search(r'(?:a\s*las?\s*)?(\d{1,2})\s*(?::(\d{2}))?\s*(pm|p\.?m\.?|am|a\.?m\.?|horas?)?', lowered)
    if not m:
        return None
    hour = int(m.group(1))
    meridian = (m.group(3) or "").replace(".", "").lower()
    if meridian in ("pm", "p m") and hour < 12:
        hour += 12
    elif meridian in ("am", "a m") and hour == 12:
        hour = 0
    if hour < 0 or hour > 23:
        return None
    return hour


def _detect_zones_in_text(text):
    """Busca nombres de comunas/zonas mencionados en el texto del usuario."""
    if not text:
        return []
    lowered = text.lower()
    found = []
    # Ordenar por longitud descendente para priorizar coincidencias más específicas
    for alias in sorted(ZONE_ALIASES.keys(), key=len, reverse=True):
        if alias in lowered:
            zone = ZONE_ALIASES[alias]
            if zone not in found:
                found.append(zone)
    return found


def _extract_route_entities(text):
    """Extrae origen y destino del texto libre usando patrones de ruta."""
    if not text:
        return None, None
    lowered = text.lower().strip()

    patterns = [
        r'(?:de\s*)(.+?)(?:\s*a\s+|\s+hasta\s+)(.+)',
        r'(?:desde\s*)(.+?)(?:\s*a\s+|\s+hasta\s+)(.+)',
        r'(?:c[oó]mo\s+(?:llego|ir|voy|llegar)\s*(?:(?:desde\s*)(.+?))?\s*a\s+)(.+)',
        r'(?:ruta\s+(?:de\s*)?|camino\s+(?:de\s*)?|trayecto\s+(?:de\s*)?)(.+?)(?:\s+a\s+|\s+hasta\s+)(.+)',
        r'(?:ir\s+(?:de\s*)?)(.+?)(?:\s+a\s+|\s+hasta\s+)(.+)',
        r'(?:para\s+ir\s+(?:de\s*)?)(.+?)(?:\s+a\s+|\s+hasta\s+)(.+)',
    ]
    for pattern in patterns:
        m = re.search(pattern, lowered)
        if m:
            origin = m.group(1).strip()
            dest = m.group(2).strip()
            # Limpiar artículos/conectores al final
            for word in [" por", " en", " y", " pasando"]:
                idx = origin.find(word)
                if idx > 0:
                    origin = origin[:idx]
                idx = dest.find(word)
                if idx > 0:
                    dest = dest[:idx]
            if origin and dest and origin != dest:
                return origin, dest
    return None, None


def _resolve_location(name):
    """Resuelve un nombre de lugar a (display_name, lat, lng) usando ZONE_ALIASES o Nominatim."""
    if not name:
        return None, None, None
    # Intentar alias primero
    lowered = name.lower()
    for alias, zone in sorted(ZONE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        if alias in lowered:
            coords = COMUNAS_COORDS.get(zone)
            if coords:
                return zone, coords[0], coords[1]
    # Fallback a Nominatim
    try:
        lat, lng = _geocode_nominatim(name)
        if lat is not None and lng is not None:
            return name, lat, lng
    except Exception:
        logger.exception("Error geocodificando: %s", name)
    return None, None, None


def _build_route_context(user_text):
    """Si el usuario menciona origen y destino, calcula la ruta real con OSRM."""
    if not user_text:
        return None

    # 1. Detectar si hay patrón de ruta en el texto
    origin_raw, dest_raw = _extract_route_entities(user_text)
    has_route_pattern = origin_raw is not None

    if not has_route_pattern:
        # Fallback: detectar dos zonas conocidas en el texto
        zones = _detect_zones_in_text(user_text)
        if len(zones) < 2:
            return None
        origin_raw, dest_raw = zones[0], zones[1]

    # 2. Resolver coordenadas de origen y destino
    origin_name, origin_lat, origin_lng = _resolve_location(origin_raw)
    dest_name, dest_lat, dest_lng = _resolve_location(dest_raw)

    if not origin_name or not dest_name:
        return None

    # 3. Respetar orden "desde X → hasta Y" si el patrón lo indica
    if has_route_pattern:
        lowered = user_text.lower()
        idx_o = lowered.find(origin_raw.lower())
        idx_d = lowered.find(dest_raw.lower())
        if idx_d != -1 and idx_o != -1 and idx_d < idx_o:
            origin_name, dest_name = dest_name, origin_name
            origin_lat, dest_lat = dest_lat, origin_lat
            origin_lng, dest_lng = dest_lng, origin_lng
            origin_raw, dest_raw = dest_raw, origin_raw

    # 4. Calcular ruta con OSRM
    try:
        osrm_result = _get_osrm_route([(origin_lat, origin_lng), (dest_lat, dest_lng)], mode="driving")
    except Exception:
        logger.exception("Error en OSRM para MóviBot")
        osrm_result = None

    if osrm_result:
        polyline, dist_km, time_min = osrm_result
        enriched = _enrich_with_real_data(origin_name, dest_name, dist_km, time_min, polyline, "driving")
        dist_km = enriched.get("distance", dist_km)
        time_min = enriched.get("time", time_min)
        risk = enriched.get("risk")
    else:
        # Fallback con Haversine
        dist_km = _haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
        time_min = max(1, round(dist_km / 30 * 60))
        risk = None

    # 5. Obtener pasos de OSRM con steps=true
    steps_txt = ""
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{origin_lng},{origin_lat};{dest_lng},{dest_lat}"
            f"?overview=false&steps=true"
        )
        resp = requests.get(url, timeout=5)
        if resp.ok:
            data = resp.json()
            route = data.get("routes", [{}])[0]
            steps_info = []
            for leg in route.get("legs", []):
                for step in leg.get("steps", []):
                    name = (step.get("name") or "").strip()
                    maneuver = step.get("maneuver", {}) or {}
                    mtype = maneuver.get("type")
                    modifier = maneuver.get("modifier")
                    instruction = _translate_maneuver(mtype, modifier)
                    if not name and not instruction:
                        continue
                    steps_info.append({"street": name, "instruction": instruction})
            if steps_info:
                parts = []
                for i, s in enumerate(steps_info[:5]):
                    instr = s.get("instruction") or ""
                    street = s.get("street") or ""
                    if instr and street:
                        parts.append(f"{i+1}) {instr} hacia/por {street}")
                    elif instr:
                        parts.append(f"{i+1}) {instr}")
                    elif street:
                        parts.append(f"{i+1}) Continúa por {street}")
                if parts:
                    steps_txt = " Pasos: " + "; ".join(parts) + "."
    except Exception:
        pass

    # 6. Detectar zonas con alta congestión en el trayecto
    congestion_txt = ""
    try:
        from .services import current_points
        pts = current_points()
        high_congestion = [p for p in pts if p.get("congestion") and p["congestion"] >= 60]
        if high_congestion:
            zones_nearby = []
            for p in high_congestion[:3]:
                zones_nearby.append(f"{p['name']} ({p['congestion']}%)")
            if zones_nearby:
                congestion_txt = f" Zonas con alta congestión en el trayecto: {', '.join(zones_nearby)}."
    except Exception:
        pass

    risk_txt = f" | Riesgo: {risk}%" if risk is not None else ""
    return (
        f"RUTA CALCULADA: {origin_name} → {dest_name}\n"
        f"Distancia: {dist_km} km | Tiempo estimado: {time_min} min{risk_txt}"
        f"{steps_txt}{congestion_txt}"
    )


def _build_live_data_context(user_text=None):
    """Genera un resumen en texto plano de los datos actuales para el prompt."""
    try:
        summary = city_summary()
    except Exception:
        logger.exception("No se pudo obtener city_summary para MóviBot")
        return "No hay datos en tiempo real disponibles en este momento."

    lines = []

    delay = summary.get("delay_risk") or {}
    route = summary.get("route_risk") or {}
    if delay.get("value") is not None:
        lines.append(f"- ⏱️ Riesgo de retrasos: {delay['value']}% — Nivel {delay['level']}")
    if route.get("value") is not None:
        lines.append(f"- 🛣️ Riesgo en ruta: {route['value']}% — Nivel {route['level']}")

    for m in summary.get("metrics", []):
        lines.append(f"- {m['label']}: {m['value']}{m['unit']}")

    zones = sorted(
        summary.get("zones", []),
        key=lambda z: (z.get("congestion") or 0),
        reverse=True,
    )
    if zones:
        lines.append("\nZonas (ordenadas de mayor a menor congestión):")
        for z in zones:
            risk_txt = f", riesgo {z['risk']}%" if z.get("risk") is not None else ""
            speed_txt = f", velocidad {z['speed']} km/h" if z.get("speed") is not None else ""
            incidents_txt = f", {z['incidents']} incidente(s)" if z.get("incidents") else ""
            lines.append(
                f"- {z['name']}: congestión {z['congestion']}%{speed_txt}{risk_txt}{incidents_txt}"
            )

    weather = summary.get("weather") or {}
    if weather:
        lines.append(
            f"\nClima (a nivel de toda la ciudad, no por zona individual): "
            f"{weather.get('description', 'N/D')}, "
            f"temperatura {weather.get('temperature', 'N/D')}°C, "
            f"probabilidad de lluvia {weather.get('precipitation_probability', 'N/D')}%"
        )

    incidents = summary.get("incidents") or []
    if incidents:
        lines.append(f"\nIncidencias viales reportadas: {len(incidents)}")
        jams = sum(1 for i in incidents if i.get("icon_category") == 6)
        closed = sum(1 for i in incidents if i.get("icon_category") == 8)
        works = sum(1 for i in incidents if i.get("icon_category") == 9)
        lines.append(f"Desglose: {jams} congestiones, {closed} vías cerradas, {works} obras")

    # Predicciones: incluir si el usuario pregunta por futuro
    if user_text and any(w in user_text.lower() for w in ["predec", "pronostic", "más tarde", "mas tarde", "mañana", "proxima hora", "siguiente hora", "a las", "a las ", "pm", "en la noche", "en la tarde", "en la mañana", "más temprano", "más tarde"]):
        pred_hour = _detect_hour_in_text(user_text)
        try:
            from apps.predictions.services import predicted_congestion
            pred_output, _, model_type, _, _ = predicted_congestion(hour=pred_hour)
            from apps.dashboard.services import COMUNAS_PRINCIPALES
            pred_output = [p for p in pred_output if p["zone"] in COMUNAS_PRINCIPALES]
            if pred_output:
                lines.append(f"\nPredicciones de congestión ({'ML' if model_type=='ml' else 'Tiempo real'}):")
                for p in pred_output:
                    zone = p["zone"]
                    forecasts = p.get("forecast", [])
                    f_strs = [f"{f['hour']:02d}:00 → {f['predicted_congestion']}% cong, lluvia {f['rain_probability']}%, confianza {f['confidence']:.0%}" for f in forecasts]
                    lines.append(f"- {zone}: {' | '.join(f_strs)}")
        except Exception:
            lines.append("\nPredicciones: no disponibles en este momento.")

    route_ctx = _build_route_context(user_text)
    if route_ctx:
        lines.append(f"\n{route_ctx}")

    return "\n".join(lines) if lines else "No hay datos en tiempo real disponibles en este momento."


def _build_system_prompt(user_text=None):
    summary = {}
    try:
        summary = city_summary()
    except Exception:
        pass
    return MOVIBOT_SYSTEM_PROMPT_TEMPLATE.format(
        generated_at=summary.get("generated_at", "N/D"),
        live_data=_build_live_data_context(user_text),
    )

def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _check_rate_limit(ip: str):
    """
    Returns (allowed: bool, retry_after: int).
    Uses Django's cache as a sliding-window counter.
    Works with any cache backend (LocMemCache, Redis, Memcached…).
    """
    RATE_LIMIT_REQUESTS = int(os.getenv("MOVIBOT_RATE_LIMIT", "30"))
    RATE_LIMIT_WINDOW   = int(os.getenv("MOVIBOT_RATE_WINDOW", "60"))
    key = f"movibot_rl:{ip}"
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Retrieve existing timestamps list
    hits = cache.get(key, [])

    # Drop timestamps outside the current window
    hits = [t for t in hits if t > window_start]

    if len(hits) >= RATE_LIMIT_REQUESTS:
        oldest = hits[0]
        retry_after = int(RATE_LIMIT_WINDOW - (now - oldest)) + 1
        return False, retry_after

    hits.append(now)
    cache.set(key, hits, timeout=RATE_LIMIT_WINDOW)
    return True, 0


def landing(request):
    return render(request, "landing/index.html")


def dashboard(request):
    boot = bootstrap_data()
    comunas = COMUNAS_PRINCIPALES
    if "alerts" in boot:
        boot["alerts"] = [a for a in boot["alerts"] if a.get("zone") in comunas]
    return render(request, "dashboard/dashboard.html", {"boot": boot})


def statistics(request):
    return render(request, "dashboard/statistics.html", {"boot": bootstrap_data()})


def weather(request):
    return render(request, "dashboard/weather.html", {"boot": bootstrap_data()})


def api_dashboard(request):
    return JsonResponse(city_summary())


def api_bootstrap(request):
    return JsonResponse(bootstrap_data())


def api_weather(request):
    return JsonResponse(get_weather())


@csrf_exempt
@require_POST
def api_movibot(request):
    # ── Rate limiting ────────────────────────────────────────────────────────
    ip = _get_client_ip(request)
    allowed, retry_after = _check_rate_limit(ip)
    if not allowed:
        response = JsonResponse(
            {"error": f"Demasiadas solicitudes. Intenta de nuevo en {retry_after} segundos."},
            status=429,
        )
        response["Retry-After"] = str(retry_after)
        return response

    # ── API key check ────────────────────────────────────────────────────────
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip() or "llama-3.3-70b-versatile"
    if not api_key or api_key == "TU_API_KEY_AQUI":
        return JsonResponse({"error": "GROQ_API_KEY no configurada"}, status=503)

    # ── Parse body ───────────────────────────────────────────────────────────
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "JSON inválido"}, status=400)

    contents = payload.get("contents", [])
    if not isinstance(contents, list):
        return JsonResponse({"error": "contents debe ser una lista"}, status=400)

    # ── Convertir formato Gemini (contents/parts) a formato OpenAI (messages) ──
    converted = []
    last_user_text = ""
    for item in contents:
        if not isinstance(item, dict):
            continue
        role = item.get("role", "user")
        role = "assistant" if role in ("model", "assistant") else "user"
        parts = item.get("parts", [])
        text = " ".join(
            p.get("text", "") for p in parts if isinstance(p, dict) and p.get("text")
        ).strip()
        if text:
            converted.append({"role": role, "content": text})
            if role == "user":
                last_user_text = text

    if not converted:
        return JsonResponse({"error": "contents no contiene mensajes válidos"}, status=400)

    messages = [{"role": "system", "content": _build_system_prompt(last_user_text)}] + converted

    # ── Call Groq (with retry on 429) ─────────────────────────────────────
    groq_payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 600,
    }
    max_retries = 3
    for attempt in range(max_retries):
        try:
            groq_response = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json=groq_payload,
                timeout=20,
            )
            if groq_response.status_code == 429 and attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.info("Groq 429, reintentando en %ds (intento %d/%d)", wait, attempt + 1, max_retries)
                time.sleep(wait)
                continue
            groq_response.raise_for_status()
            groq_data = groq_response.json()
            text = (
                groq_data.get("choices", [{}])[0]
                .get("message", {})
                .get("content")
            )
            return JsonResponse({"text": text or "No pude generar una respuesta en este momento."})
        except requests.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.info("Groq 429 (exception), reintentando en %ds (intento %d/%d)", wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue
                return JsonResponse(
                    {"error": "El asistente está temporalmente ocupado. Intenta de nuevo en unos segundos."},
                    status=429,
                )
            logger.error("Error de Groq: %s", e.response.text if e.response is not None else e)
            return JsonResponse({"error": "Error conectando con el asistente"}, status=502)
        except requests.RequestException:
            return JsonResponse({"error": "Error conectando con el asistente"}, status=502)