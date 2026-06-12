import time
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import connection
from apps.dashboard.services import current_points, get_weather, get_all_incidents, calculate_delay_risk, calculate_route_risk, COMUNAS_PRINCIPALES
from apps.traffic.models import TrafficRecord

NEIGHBORHOODS = [
    ("Popular", 6.3085, -75.5579),
    ("Granizal", 6.3012, -75.5501),
    ("Santa Cruz", 6.2985, -75.5612),
    ("Villa del Socorro", 6.2930, -75.5534),
    ("Manrique", 6.2746, -75.5523),
    ("La Cruz", 6.2810, -75.5467),
    ("Aranjuez", 6.2860, -75.5650),
    ("Brasilia", 6.2795, -75.5712),
    ("Castilla", 6.2923, -75.5707),
    ("Florencia", 6.2975, -75.5780),
    ("Doce de Octubre", 6.2980, -75.5880),
    ("Pedregal", 6.2912, -75.5850),
    ("Robledo", 6.2775, -75.5909),
    ("Pajarito", 6.2840, -75.6012),
    ("Villa Hermosa", 6.2620, -75.5530),
    ("La Ladera", 6.2570, -75.5490),
    ("Buenos Aires", 6.2530, -75.5570),
    ("Miraflores", 6.2490, -75.5610),
    ("Centro", 6.2518, -75.5636),
    ("Prado", 6.2560, -75.5680),
    ("Laureles", 6.2459, -75.5964),
    ("Estadio", 6.2510, -75.5880),
    ("La América", 6.2420, -75.5880),
    ("Calasanz", 6.2380, -75.5950),
    ("San Javier", 6.2355, -75.6050),
    ("El Salado", 6.2290, -75.6120),
    ("El Poblado", 6.2088, -75.5678),
    ("Astorga", 6.2020, -75.5750),
    ("Guayabal", 6.2107, -75.5888),
    ("Tenche", 6.2050, -75.5830),
    ("Belen", 6.2311, -75.6038),
    ("Los Alpes", 6.2250, -75.6100),
]


class Command(BaseCommand):
    help = "Collects current traffic, weather, and accident data into historical tables"

    def add_arguments(self, parser):
        parser.add_argument("--loop", action="store_true",
                            help="Run in an infinite loop every 10 minutes")

    def handle(self, *args, **options):
        if options["loop"]:
            self._run_loop()
        else:
            self._collect()

    def _run_loop(self):
        self.stdout.write(self.style.WARNING(
            f"[{timezone.now():%Y-%m-%d %H:%M:%S}] Collector loop started — will collect every 600s."
        ))
        while True:
            try:
                self._collect()
            except Exception as exc:
                self.stderr.write(self.style.ERROR(
                    f"[{timezone.now():%Y-%m-%d %H:%M:%S}] Iteration failed: {exc}"
                ))
            time.sleep(600)

    def _collect(self):
        ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_traffic()
        self.save_weather()
        self.save_accidents()
        self.stdout.write(self.style.SUCCESS(f"[{ts}] Data collection complete"))

    def save_traffic(self):
        points = current_points()
        records = []
        now = timezone.now()
        for p in points:
            records.append(TrafficRecord(
                zone=p["name"], latitude=p["lat"], longitude=p["lng"],
                congestion_level=p.get("congestion") or 0,
                average_speed=p.get("speed") or 0,
                source=p.get("source", "desconocido"),
                recorded_at=now,
            ))
        TrafficRecord.objects.bulk_create(records)
        self.stdout.write(f"Saved {len(records)} traffic records")

    def save_weather(self):
        weather = get_weather()
        now = timezone.now()
        rain_mm = float(weather.get("rain", 0) or weather.get("precipitation", 0) or 0)
        temperature = float(weather.get("temperature", 23))
        with connection.cursor() as cursor:
            for zone in COMUNAS_PRINCIPALES:
                cursor.execute(
                    "INSERT INTO weather_records (zone, rain_mm, temperature, recorded_at) VALUES (%s, %s, %s, %s)",
                    [zone, rain_mm, temperature, now],
                )
        self.stdout.write(f"Saved {len(COMUNAS_PRINCIPALES)} weather records")

    def save_accidents(self):
        incidents, _ = get_all_incidents()
        points = current_points()
        delay_risk = calculate_delay_risk(incidents, points)
        route_risk = calculate_route_risk(incidents, points)
        now = timezone.now()
        saved = 0
        with connection.cursor() as cursor:
            for a in incidents:
                lat = a.get("lat")
                lng = a.get("lng")
                if lat is None or lng is None:
                    continue
                zone_name = _zone_from_coords(lat, lng, NEIGHBORHOODS)
                cursor.execute(
                    "INSERT INTO accidents (zone, severity, latitude, longitude, occurred_at) VALUES (%s, %s, %s, %s, %s)",
                    [zone_name, "media", lat, lng, now],
                )
                saved += 1
        if delay_risk.get("value") is not None:
            self.stdout.write(f"⏱️ Riesgo de retrasos: {delay_risk['value']}% ({delay_risk['level']})")
        if route_risk.get("value") is not None:
            self.stdout.write(f"🛣️ Riesgo en ruta: {route_risk['value']}% ({route_risk['level']})")
        self.stdout.write(f"Saved {saved} incident records")


def _zone_from_coords(lat, lng, neighborhoods):
    closest = min(neighborhoods, key=lambda n: abs(n[1] - lat) + abs(n[2] - lng))
    return closest[0]
