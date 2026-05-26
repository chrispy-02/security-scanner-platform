-- Vulnerability Detect and Analysis — database schema
-- Recreates the application tables so the app runs from a fresh MySQL instance
-- without the private development dump. Safe to run repeatedly (IF NOT EXISTS).

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS users (
  user_id  INT AUTO_INCREMENT PRIMARY KEY,
  role     ENUM('owner','admin','employee','reader') DEFAULT NULL,
  email    VARCHAR(100) NOT NULL,
  password VARCHAR(256) NOT NULL,
  api_key  VARCHAR(256) DEFAULT NULL,
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS domains (
  domain_id INT AUTO_INCREMENT PRIMARY KEY,
  domain    VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_domains_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS websites (
  website_id   INT AUTO_INCREMENT PRIMARY KEY,
  owner_id     INT NOT NULL,
  website_name VARCHAR(500) NOT NULL,
  website_url  VARCHAR(255) DEFAULT NULL,
  KEY idx_websites_owner (owner_id),
  UNIQUE KEY uq_websites_url (website_url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS website_auth (
  auth_id      INT AUTO_INCREMENT PRIMARY KEY,
  website_id   INT NOT NULL,
  user_id      INT NOT NULL,
  role         VARCHAR(10) NOT NULL,
  website_name VARCHAR(500) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS scans (
  scan_id             INT AUTO_INCREMENT PRIMARY KEY,
  user_id             INT NOT NULL,
  scan_name           VARCHAR(255) NOT NULL,
  website_url         VARCHAR(255) NOT NULL,
  scan_date           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  status              VARCHAR(50) NOT NULL,
  high_risks          INT NOT NULL DEFAULT 0,
  medium_risks        INT NOT NULL DEFAULT 0,
  low_risks           INT NOT NULL DEFAULT 0,
  informational_risks INT NOT NULL DEFAULT 0,
  report_url          VARCHAR(255) DEFAULT NULL,
  -- Holds the GitHub Actions run id (was the GitLab pipeline id). BIGINT: GitHub run ids exceed INT.
  pipeline_id         BIGINT DEFAULT NULL,
  host                VARCHAR(255) DEFAULT NULL,
  website_id          INT NOT NULL DEFAULT -1,
  KEY idx_scans_user (user_id),
  KEY idx_scans_website (website_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS scanned_websites (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  scan_id     INT NOT NULL,
  website_url VARCHAR(255) NOT NULL,
  KEY idx_scanned_scan (scan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS vulnerabilities (
  vulnerability_id   INT AUTO_INCREMENT PRIMARY KEY,
  scan_id            INT NOT NULL,
  vulnerability_name VARCHAR(255) DEFAULT NULL,
  severity           VARCHAR(50)  DEFAULT NULL,
  description        TEXT,
  solution           TEXT,
  count              INT NOT NULL,
  instance_url       VARCHAR(255) DEFAULT 'N/A',
  KEY idx_vuln_scan (scan_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS schedules (
  schedule_id   INT AUTO_INCREMENT PRIMARY KEY,
  website_id    INT NOT NULL,
  scan_url      VARCHAR(500) NOT NULL,
  next_run      DATETIME DEFAULT NULL,
  description   VARCHAR(500) NOT NULL,
  time_interval VARCHAR(255) DEFAULT NULL,
  KEY idx_sched_website (website_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS hourly_frequency (
  hourly_frequency_id INT AUTO_INCREMENT PRIMARY KEY,
  schedule_id         INT DEFAULT NULL,
  hourly_frequency    INT DEFAULT NULL,
  KEY idx_hourly_sched (schedule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS monthly_date (
  monthly_date INT AUTO_INCREMENT PRIMARY KEY,
  schedule_id  INT DEFAULT NULL,
  day_of_month INT DEFAULT NULL,
  KEY idx_monthly_sched (schedule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS scan_times (
  scan_time_id INT AUTO_INCREMENT PRIMARY KEY,
  schedule_id  INT NOT NULL,
  scan_time    TIME NOT NULL,
  KEY idx_scantime_sched (schedule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS valid_days (
  valid_day_id INT AUTO_INCREMENT PRIMARY KEY,
  schedule_id  INT NOT NULL,
  day          VARCHAR(500) NOT NULL,
  KEY idx_validday_sched (schedule_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
