-- ============================================================
--  Eclix Royal Homes — Full Database Schema
--  Run this in phpMyAdmin or mysql CLI
-- ============================================================

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";

CREATE DATABASE IF NOT EXISTS `eclix_royal_homes` 
  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `eclix_royal_homes`;

-- ─── USERS ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `users_details` (
  `userid`       INT(11) NOT NULL AUTO_INCREMENT,
  `username`     VARCHAR(100) NOT NULL,
  `email`        VARCHAR(255) NOT NULL UNIQUE,
  `password`     VARCHAR(255) NOT NULL,   -- bcrypt hash
  `phone`        VARCHAR(30),
  `location`     TEXT,
  `home_address` TEXT,
  `created_at`   DATETIME DEFAULT NOW(),
  PRIMARY KEY (`userid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── PROPERTIES ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `property_details` (
  `property_id`          INT(11) NOT NULL AUTO_INCREMENT,
  `property_name`        VARCHAR(255) NOT NULL,
  `property_location`    VARCHAR(255) NOT NULL,
  `property_price`       BIGINT NOT NULL,
  `property_description` TEXT NOT NULL,
  `property_photo`       TEXT NOT NULL,
  `property_size`        INT(11),
  `property_featured`    TINYINT(1) DEFAULT 0,
  `property_for_sale`    TINYINT(1) DEFAULT 1,
  `property_bath`        INT(11) DEFAULT 0,
  `property_beds`        INT(11) DEFAULT 0,
  `created_at`           DATETIME DEFAULT NOW(),
  PRIMARY KEY (`property_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── FAVOURITES ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `user_favourites` (
  `id`          INT(11) NOT NULL AUTO_INCREMENT,
  `user_id`     INT(11) NOT NULL,
  `property_id` INT(11) NOT NULL,
  `saved_at`    DATETIME DEFAULT NOW(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `unique_fav` (`user_id`, `property_id`),
  FOREIGN KEY (`user_id`) REFERENCES `users_details`(`userid`) ON DELETE CASCADE,
  FOREIGN KEY (`property_id`) REFERENCES `property_details`(`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── BOOKINGS ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `bookings` (
  `booking_id`   INT(11) NOT NULL AUTO_INCREMENT,
  `user_id`      INT(11) NOT NULL,
  `property_id`  INT(11) NOT NULL,
  `booking_type` ENUM('viewing','purchase') DEFAULT 'viewing',
  `notes`        TEXT,
  `booking_date` DATE,
  `status`       ENUM('pending','confirmed','cancelled') DEFAULT 'pending',
  `created_at`   DATETIME DEFAULT NOW(),
  PRIMARY KEY (`booking_id`),
  FOREIGN KEY (`user_id`) REFERENCES `users_details`(`userid`) ON DELETE CASCADE,
  FOREIGN KEY (`property_id`) REFERENCES `property_details`(`property_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── NEWSLETTER ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS `newsletter_subscribers` (
  `id`            INT(11) NOT NULL AUTO_INCREMENT,
  `email`         VARCHAR(255) NOT NULL UNIQUE,
  `subscribed_at` DATETIME DEFAULT NOW(),
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─── SAMPLE PROPERTIES ─────────────────────────────────────
INSERT INTO `property_details`
  (property_name, property_location, property_price, property_description, property_photo, property_size, property_featured, property_for_sale, property_bath, property_beds)
VALUES
  ('Ocean View Villa',      'Mombasa, Kenya',       250000000, 'Breathtaking ocean views, infinity pool, private beach access. A crown jewel on the Kenyan coast.', 'https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=800', 520, 1, 1, 4, 5),
  ('City Penthouse',        'Nairobi, Kenya',       320000000, 'Sky-high living above Nairobi CBD. Floor-to-ceiling glass, rooftop terrace, concierge service.', 'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=800', 380, 1, 1, 3, 4),
  ('Private Luxury Mansion','Karen, Nairobi',       580000000, 'Gated 2-acre estate with guest house, cinema room, wine cellar, and manicured gardens.',         'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800', 950, 1, 1, 6, 7),
  ('Lakeside Retreat',      'Naivasha, Kenya',      180000000, 'Serene lakeside property with private jetty, flamingo views, and organic gardens.',               'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?w=800', 420, 0, 1, 3, 4),
  ('Hilltop Estate',        'Gigiri, Nairobi',      420000000, 'Architecturally stunning hilltop home with panoramic views of Nairobi National Park.',            'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=800', 680, 1, 1, 5, 6),
  ('Safari Lodge Villa',    'Laikipia, Kenya',      290000000, 'Luxury villa bordering a private conservancy. Wake up to wildlife at your doorstep.',             'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=800', 480, 0, 1, 4, 5),
  ('Coastal Bungalow',      'Diani Beach, Kenya',   150000000, 'Whitewashed beach bungalow steps from the Indian Ocean. Perfect investment or holiday home.',      'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800', 280, 0, 1, 2, 3),
  ('Modern Smart Home',     'Westlands, Nairobi',   220000000, 'Fully automated smart home with solar power, EV charging, and integrated security systems.',       'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800', 350, 0, 1, 3, 4);

COMMIT;
