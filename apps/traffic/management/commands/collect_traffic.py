import time
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import connection
from apps.dashboard.services import demo_points, get_weather, get_external_accidents
from apps.traffic.models import TrafficRecord


class Command(BaseCommand):
    help = "Collects current traffic, weather, and accident data into historical tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop",
            action="store_true",
            help="Run in an infinite loop every 10 minutes within the same process",
        )

    def handle(self, *args, **options):
        if options["loop"]:
            self._run_loop()
        else:
            self._collect()

    def _run_loop(self):
        self.stdout.write(
            self.style.WARNING(
                f"[{timezone.now():%Y-%m-%d %H:%M:%S}] "
                "Collector loop started — will collect every 600s. Press Ctrl+C to stop."
            )
        )
        while True:
            try:
                self._collect()
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f"[{timezone.now():%Y-%m-%d %H:%M:%S}] "
                        f"Iteration failed: {exc}"
                    )
                )
            time.sleep(600)

    def _collect(self):
        ts = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_traffic()
        self.save_weather()
        self.save_accidents()
        self.stdout.write(self.style.SUCCESS(f"[{ts}] Data collection complete"))

    def save_traffic(self):
        points = demo_points()
        records = []
        now = timezone.now()
        for p in points:
            records.append(TrafficRecord(
                zone=p["name"],
                latitude=p["lat"],
                longitude=p["lng"],
                congestion_level=p["congestion"],
                average_speed=p["speed"],
                recorded_at=now,
            ))
        TrafficRecord.objects.bulk_create(records)
        self.stdout.write(f"Saved {len(records)} traffic records")

    def save_weather(self):
        weather = get_weather()
        now = timezone.now()
        rain_mm = float(weather.get("rain", 0) or weather.get("precipitation", 0) or 0)
        temperature = float(weather.get("temperature", 23))
        zones = [
            "El Poblado", "Laureles", "Centro", "Belen",
            "Robledo", "Manrique", "Guayabal", "Castilla",
        ]
        with connection.cursor() as cursor:
            for zone in zones:
                cursor.execute(
                    "INSERT INTO weather_records (zone, rain_mm, temperature, recorded_at) VALUES (%s, %s, %s, %s)",
                    [zone, rain_mm, temperature, now],
                )
        self.stdout.write(f"Saved {len(zones)} weather records")

    def save_accidents(self):
        accidents = get_external_accidents(limit=30)
        now = timezone.now()
        saved = 0
        with connection.cursor() as cursor:
            for a in accidents:
                lat = a.get("lat")
                lng = a.get("lng")
                if lat is None or lng is None:
                    continue
                zone_name = "Centro"
                cursor.execute(
                    "INSERT INTO accidents (zone, severity, latitude, longitude, occurred_at) VALUES (%s, %s, %s, %s, %s)",
                    [zone_name, "media", lat, lng, now],
                )
                saved += 1
        self.stdout.write(f"Saved {saved} accident records")
