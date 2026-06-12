CREATE DATABASE IF NOT EXISTS movilidata_os CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE movilidata_os;

-- Tables without Django models (raw SQL only)
CREATE TABLE IF NOT EXISTS users_demo (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL,
  role VARCHAR(80) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accidents (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone VARCHAR(100) NOT NULL,
  severity ENUM('baja','media','alta','critica') NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  occurred_at DATETIME NOT NULL,
  INDEX idx_accidents_zone_time (zone, occurred_at),
  INDEX idx_accidents_occurred_at (occurred_at)
);

CREATE TABLE IF NOT EXISTS weather_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone VARCHAR(100) NOT NULL,
  rain_mm DECIMAL(6,2) NOT NULL,
  temperature DECIMAL(4,1) NOT NULL,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_weather_recorded_at (recorded_at)
);

-- Tables managed by Django (CREATE IF NOT EXISTS = no-op when migrate already ran)
CREATE TABLE IF NOT EXISTS traffic_trafficrecord (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  zone VARCHAR(100) NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  congestion_level SMALLINT UNSIGNED NOT NULL,
  average_speed DECIMAL(5,2) NOT NULL,
  recorded_at DATETIME(6) NOT NULL
);

CREATE TABLE IF NOT EXISTS maps_riskzone (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  risk_score SMALLINT UNSIGNED NOT NULL,
  reason VARCHAR(180) NOT NULL,
  updated_at DATETIME(6) NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts_mobilityalert (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(140) NOT NULL,
  zone VARCHAR(100) NOT NULL,
  level VARCHAR(10) NOT NULL,
  description LONGTEXT NOT NULL,
  active BOOL NOT NULL,
  created_at DATETIME(6) NOT NULL
);

CREATE TABLE IF NOT EXISTS routes_saferoute (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  origin VARCHAR(120) NOT NULL,
  destination VARCHAR(120) NOT NULL,
  distance_km DECIMAL(6,2) NOT NULL,
  estimated_minutes SMALLINT UNSIGNED NOT NULL,
  risk_score SMALLINT UNSIGNED NOT NULL,
  active BOOL NOT NULL
);

CREATE TABLE IF NOT EXISTS predictions_trafficprediction (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  zone VARCHAR(100) NOT NULL,
  predicted_congestion SMALLINT UNSIGNED NOT NULL,
  rain_probability SMALLINT UNSIGNED NOT NULL,
  confidence DECIMAL(5,2) NOT NULL,
  predicted_for DATETIME(6) NOT NULL,
  created_at DATETIME(6) NOT NULL
);

-- Drop old-style table names that conflict
DROP TABLE IF EXISTS mobility_alerts;
DROP TABLE IF EXISTS risk_zones;
DROP TABLE IF EXISTS traffic_records;
DROP TABLE IF EXISTS safe_routes;
DROP TABLE IF EXISTS traffic_predictions;

-- ⚠️ DATOS DE DEMOSTRACIÓN INICIAL — No representan eventos reales
-- Estos datos se reemplazarán cuando el colector (collect_traffic) acumule historia real

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE alerts_mobilityalert;
TRUNCATE TABLE predictions_trafficprediction;
TRUNCATE TABLE routes_saferoute;
TRUNCATE TABLE weather_records;
TRUNCATE TABLE accidents;
TRUNCATE TABLE traffic_trafficrecord;
TRUNCATE TABLE maps_riskzone;
TRUNCATE TABLE users_demo;
SET FOREIGN_KEY_CHECKS = 1;

-- Crear usuarios reales con: python manage.py createsuperuser
-- No insertar usuarios demo con credenciales hardcodeadas

INSERT INTO maps_riskzone (id, name, latitude, longitude, risk_score, reason, updated_at) VALUES
(1,'El Poblado',6.208800,-75.567800,52,'Alto flujo y lluvias localizadas',NOW()),
(2,'Laureles',6.245900,-75.596400,61,'Congestion recurrente en hora pico',NOW()),
(3,'Centro',6.251800,-75.563600,82,'Alta accidentalidad y saturacion vial',NOW()),
(4,'Belen',6.231100,-75.603800,67,'Intersecciones criticas',NOW()),
(5,'Robledo',6.277500,-75.590900,72,'Pendientes, lluvia y velocidad baja',NOW()),
(6,'Manrique',6.274600,-75.552300,78,'Riesgo por lluvia y congestion',NOW()),
(7,'Guayabal',6.210700,-75.588800,58,'Corredor industrial con carga pesada',NOW()),
(8,'Castilla',6.292300,-75.570700,69,'Flujo denso y eventos viales',NOW());

INSERT INTO traffic_trafficrecord (zone, latitude, longitude, congestion_level, average_speed, recorded_at, source) VALUES
('El Poblado',6.208800,-75.567800,45,29.4,NOW(),'desconocido'),
('Laureles',6.245900,-75.596400,54,26.9,NOW(),'desconocido'),
('Centro',6.251800,-75.563600,63,24.3,NOW(),'desconocido'),
('Belen',6.231100,-75.603800,72,21.8,NOW(),'desconocido'),
('Robledo',6.277500,-75.590900,81,19.3,NOW(),'desconocido'),
('Manrique',6.274600,-75.552300,76,20.5,NOW(),'desconocido'),
('Guayabal',6.210700,-75.588800,58,25.8,NOW(),'desconocido'),
('Castilla',6.292300,-75.570700,69,22.6,NOW(),'desconocido');

INSERT INTO accidents (zone, severity, latitude, longitude, occurred_at) VALUES
('Centro','alta',6.251800,-75.563600,NOW() - INTERVAL 3 HOUR),
('Manrique','media',6.274600,-75.552300,NOW() - INTERVAL 5 HOUR),
('Robledo','alta',6.277500,-75.590900,NOW() - INTERVAL 1 DAY),
('Belen','media',6.231100,-75.603800,NOW() - INTERVAL 8 HOUR);

INSERT INTO weather_records (zone, rain_mm, temperature) VALUES
('Centro',3.40,23.1),
('Robledo',4.80,22.4),
('El Poblado',1.20,24.3),
('Manrique',3.90,22.8),
('Belen',2.10,23.7);

INSERT INTO alerts_mobilityalert (zone, title, level, description, active, created_at) VALUES
('Centro','Centro con riesgo critico','alta','Congestion y accidentalidad superiores al promedio.',TRUE,NOW()),
('Robledo','Robledo bajo lluvia intensa','alta','Recomendar desvio por corredores alternos.',TRUE,NOW()),
('Laureles','Laureles en hora pico','media','Velocidad promedio inferior a 27 km/h.',TRUE,NOW()),
('Manrique','Manrique con riesgo preventivo','alta','Lluvia y pendiente aumentan el riesgo vial.',TRUE,NOW());

INSERT INTO routes_saferoute (name, origin, destination, distance_km, estimated_minutes, risk_score, active) VALUES
('Ruta Rio Medellin','El Poblado','Centro',8.60,22,34,TRUE),
('Ruta Laureles segura','Laureles','Belen',9.80,28,22,TRUE),
('Ruta Nororiental preventiva','Manrique','Centro',11.20,35,48,TRUE);

INSERT INTO predictions_trafficprediction (zone, predicted_congestion, rain_probability, confidence, predicted_for, created_at) VALUES
('Centro',84,45,0.88,NOW() + INTERVAL 1 HOUR,NOW()),
('Robledo',79,68,0.84,NOW() + INTERVAL 1 HOUR,NOW()),
('Laureles',63,31,0.86,NOW() + INTERVAL 1 HOUR,NOW()),
('Manrique',81,59,0.83,NOW() + INTERVAL 1 HOUR,NOW());

DROP PROCEDURE IF EXISTS sp_city_mobility_summary;
DROP PROCEDURE IF EXISTS sp_high_risk_zones;
DROP PROCEDURE IF EXISTS sp_rain_traffic_correlation;
DROP PROCEDURE IF EXISTS sp_active_alert_report;

DELIMITER //

CREATE PROCEDURE sp_city_mobility_summary()
BEGIN
  SELECT
    ROUND(AVG(congestion_level), 2) AS avg_congestion,
    ROUND(AVG(average_speed), 2) AS avg_speed,
    COUNT(*) AS samples
  FROM traffic_trafficrecord;
END //

CREATE PROCEDURE sp_high_risk_zones(IN min_score INT)
BEGIN
  SELECT name, latitude, longitude, risk_score, reason
  FROM maps_riskzone
  WHERE risk_score >= min_score
  ORDER BY risk_score DESC;
END //

CREATE PROCEDURE sp_rain_traffic_correlation()
BEGIN
  SELECT t.zone, AVG(t.congestion_level) AS avg_congestion, AVG(w.rain_mm) AS avg_rain
  FROM traffic_trafficrecord t
  JOIN weather_records w ON w.zone = t.zone
  GROUP BY t.zone
  ORDER BY avg_congestion DESC;
END //

CREATE PROCEDURE sp_active_alert_report()
BEGIN
  SELECT a.title, a.level, a.zone, a.created_at
  FROM alerts_mobilityalert a
  WHERE a.active = TRUE
  ORDER BY FIELD(a.level, 'alta','media','baja'), a.created_at DESC;
END //

DELIMITER ;
