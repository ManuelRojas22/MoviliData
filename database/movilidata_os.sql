CREATE DATABASE IF NOT EXISTS movilidata_os CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE movilidata_os;

CREATE TABLE IF NOT EXISTS users_demo (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(80) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL,
  role VARCHAR(80) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS traffic_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone VARCHAR(100) NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  congestion_level TINYINT UNSIGNED NOT NULL,
  average_speed DECIMAL(5,2) NOT NULL,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_traffic_congestion CHECK (congestion_level <= 100),
  INDEX idx_traffic_zone_time (zone, recorded_at)
);

CREATE TABLE IF NOT EXISTS accidents (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone VARCHAR(100) NOT NULL,
  severity ENUM('baja','media','alta','critica') NOT NULL,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  occurred_at DATETIME NOT NULL,
  INDEX idx_accidents_zone_time (zone, occurred_at)
);

CREATE TABLE IF NOT EXISTS weather_records (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone VARCHAR(100) NOT NULL,
  rain_mm DECIMAL(6,2) NOT NULL,
  temperature DECIMAL(4,1) NOT NULL,
  recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS risk_zones (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL UNIQUE,
  latitude DECIMAL(9,6) NOT NULL,
  longitude DECIMAL(9,6) NOT NULL,
  risk_score TINYINT UNSIGNED NOT NULL,
  reason VARCHAR(180) NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT chk_risk_score CHECK (risk_score <= 100)
);

CREATE TABLE IF NOT EXISTS mobility_alerts (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  risk_zone_id BIGINT NULL,
  title VARCHAR(140) NOT NULL,
  level ENUM('baja','media','alta') NOT NULL,
  description TEXT NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_alert_zone FOREIGN KEY (risk_zone_id) REFERENCES risk_zones(id)
);

CREATE TABLE IF NOT EXISTS safe_routes (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(120) NOT NULL,
  origin VARCHAR(120) NOT NULL,
  destination VARCHAR(120) NOT NULL,
  distance_km DECIMAL(6,2) NOT NULL,
  estimated_minutes SMALLINT UNSIGNED NOT NULL,
  risk_score TINYINT UNSIGNED NOT NULL,
  active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS traffic_predictions (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  zone VARCHAR(100) NOT NULL,
  predicted_congestion TINYINT UNSIGNED NOT NULL,
  rain_probability TINYINT UNSIGNED NOT NULL,
  confidence DECIMAL(5,2) NOT NULL,
  predicted_for DATETIME NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_prediction_zone_time (zone, predicted_for)
);

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE mobility_alerts;
TRUNCATE TABLE traffic_predictions;
TRUNCATE TABLE safe_routes;
TRUNCATE TABLE weather_records;
TRUNCATE TABLE accidents;
TRUNCATE TABLE traffic_records;
TRUNCATE TABLE risk_zones;
TRUNCATE TABLE users_demo;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO users_demo (username, email, role) VALUES
('admin','admin@movilidata.local','Administrador'),
('analista','analista@movilidata.local','Analista de movilidad');

INSERT INTO risk_zones (id, name, latitude, longitude, risk_score, reason) VALUES
(1,'El Poblado',6.208800,-75.567800,52,'Alto flujo y lluvias localizadas'),
(2,'Laureles',6.245900,-75.596400,61,'Congestion recurrente en hora pico'),
(3,'Centro',6.251800,-75.563600,82,'Alta accidentalidad y saturacion vial'),
(4,'Belen',6.231100,-75.603800,67,'Intersecciones criticas'),
(5,'Robledo',6.277500,-75.590900,72,'Pendientes, lluvia y velocidad baja'),
(6,'Manrique',6.274600,-75.552300,78,'Riesgo por lluvia y congestion'),
(7,'Guayabal',6.210700,-75.588800,58,'Corredor industrial con carga pesada'),
(8,'Castilla',6.292300,-75.570700,69,'Flujo denso y eventos viales');

INSERT INTO traffic_records (zone, latitude, longitude, congestion_level, average_speed) VALUES
('El Poblado',6.208800,-75.567800,45,29.4),
('Laureles',6.245900,-75.596400,54,26.9),
('Centro',6.251800,-75.563600,63,24.3),
('Belen',6.231100,-75.603800,72,21.8),
('Robledo',6.277500,-75.590900,81,19.3),
('Manrique',6.274600,-75.552300,76,20.5),
('Guayabal',6.210700,-75.588800,58,25.8),
('Castilla',6.292300,-75.570700,69,22.6);

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

INSERT INTO mobility_alerts (risk_zone_id, title, level, description) VALUES
(3,'Centro con riesgo critico','alta','Congestion y accidentalidad superiores al promedio.'),
(5,'Robledo bajo lluvia intensa','alta','Recomendar desvio por corredores alternos.'),
(2,'Laureles en hora pico','media','Velocidad promedio inferior a 27 km/h.'),
(6,'Manrique con riesgo preventivo','alta','Lluvia y pendiente aumentan el riesgo vial.');

INSERT INTO safe_routes (name, origin, destination, distance_km, estimated_minutes, risk_score) VALUES
('Ruta Rio Medellin','El Poblado','Centro',8.60,22,34),
('Ruta Laureles segura','Laureles','Belen',9.80,28,22),
('Ruta Nororiental preventiva','Manrique','Centro',11.20,35,48);

INSERT INTO traffic_predictions (zone, predicted_congestion, rain_probability, confidence, predicted_for) VALUES
('Centro',84,45,0.88,NOW() + INTERVAL 1 HOUR),
('Robledo',79,68,0.84,NOW() + INTERVAL 1 HOUR),
('Laureles',63,31,0.86,NOW() + INTERVAL 1 HOUR),
('Manrique',81,59,0.83,NOW() + INTERVAL 1 HOUR);

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
  FROM traffic_records;
END //

CREATE PROCEDURE sp_high_risk_zones(IN min_score INT)
BEGIN
  SELECT name, latitude, longitude, risk_score, reason
  FROM risk_zones
  WHERE risk_score >= min_score
  ORDER BY risk_score DESC;
END //

CREATE PROCEDURE sp_rain_traffic_correlation()
BEGIN
  SELECT t.zone, AVG(t.congestion_level) AS avg_congestion, AVG(w.rain_mm) AS avg_rain
  FROM traffic_records t
  JOIN weather_records w ON w.zone = t.zone
  GROUP BY t.zone
  ORDER BY avg_congestion DESC;
END //

CREATE PROCEDURE sp_active_alert_report()
BEGIN
  SELECT a.title, a.level, rz.name AS zone, rz.risk_score, a.created_at
  FROM mobility_alerts a
  LEFT JOIN risk_zones rz ON rz.id = a.risk_zone_id
  WHERE a.active = TRUE
  ORDER BY FIELD(a.level, 'alta','media','baja'), a.created_at DESC;
END //

DELIMITER ;
