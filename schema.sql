CREATE DATABASE IF NOT EXISTS tour_travel_booking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE tour_travel_booking;

CREATE TABLE IF NOT EXISTS users (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, full_name VARCHAR(120) NOT NULL, email VARCHAR(190) NOT NULL UNIQUE,
 phone VARCHAR(30) NOT NULL, password_hash VARCHAR(255) NOT NULL, role ENUM('customer','admin') NOT NULL DEFAULT 'customer',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, is_active BOOLEAN NOT NULL DEFAULT TRUE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS travellers (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, customer_id BIGINT UNSIGNED NOT NULL, full_name VARCHAR(120) NOT NULL,
 date_of_birth DATE NULL, phone VARCHAR(30) NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE, INDEX(customer_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS destinations (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL, region VARCHAR(120), country VARCHAR(100) NOT NULL DEFAULT 'India',
 description TEXT, image_url VARCHAR(500), is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE KEY(name,country)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS tour_packages (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, destination_id BIGINT UNSIGNED NOT NULL, title VARCHAR(180) NOT NULL, description TEXT,
 duration_days SMALLINT UNSIGNED NOT NULL, duration_nights SMALLINT UNSIGNED NOT NULL, price_per_person DECIMAL(12,2) NOT NULL,
 maximum_capacity INT UNSIGNED NOT NULL, available_seats INT UNSIGNED NOT NULL, inclusions TEXT, exclusions TEXT, accommodation_details TEXT,
 transport_details TEXT, status ENUM('active','inactive') NOT NULL DEFAULT 'active', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, CHECK(price_per_person>=0), CHECK(available_seats<=maximum_capacity),
 FOREIGN KEY(destination_id) REFERENCES destinations(id), INDEX(status), INDEX(destination_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS custom_tours (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, unique_reference VARCHAR(32) NOT NULL UNIQUE, customer_id BIGINT UNSIGNED NOT NULL,
 departure_city VARCHAR(120), start_date DATE NOT NULL, end_date DATE NOT NULL, traveller_count SMALLINT UNSIGNED NOT NULL,
 budget DECIMAL(12,2) NOT NULL DEFAULT 0, accommodation_preference VARCHAR(30), room_count SMALLINT UNSIGNED DEFAULT 1,
 transport_preference VARCHAR(40), travel_style VARCHAR(40), dietary_preferences TEXT, special_requests TEXT,
 estimated_total DECIMAL(12,2) NOT NULL DEFAULT 0, quoted_total DECIMAL(12,2), status ENUM('draft','submitted','under_review','awaiting_customer_approval','modification_requested','approved_for_booking','confirmed','cancelled','completed','rejected') NOT NULL DEFAULT 'draft',
 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
 FOREIGN KEY(customer_id) REFERENCES users(id), CHECK(end_date>=start_date), CHECK(budget>=0), INDEX(customer_id), INDEX(status), INDEX(start_date,end_date)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS bookings (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, booking_reference VARCHAR(32) NOT NULL UNIQUE, customer_id BIGINT UNSIGNED NOT NULL,
 package_id BIGINT UNSIGNED NULL, custom_tour_id BIGINT UNSIGNED NULL, travel_start_date DATE NOT NULL, travel_end_date DATE NOT NULL,
 traveller_count SMALLINT UNSIGNED NOT NULL, amount_before_adjustments DECIMAL(12,2) NOT NULL, discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
 tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0, final_amount DECIMAL(12,2) NOT NULL, booking_status ENUM('pending','awaiting_payment','confirmed','cancelled','completed') NOT NULL DEFAULT 'pending',
 payment_status ENUM('unpaid','paid','failed','refunded') NOT NULL DEFAULT 'unpaid', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, FOREIGN KEY(customer_id) REFERENCES users(id),
 FOREIGN KEY(package_id) REFERENCES tour_packages(id), FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id),
 CHECK((package_id IS NULL) <> (custom_tour_id IS NULL)), INDEX(customer_id), INDEX(package_id), INDEX(booking_status), INDEX(travel_start_date)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS booking_travellers (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, booking_id BIGINT UNSIGNED NOT NULL, traveller_id BIGINT UNSIGNED NULL,
 traveller_name VARCHAR(120) NOT NULL, date_of_birth DATE NULL, phone VARCHAR(30) NULL,
 FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE, FOREIGN KEY(traveller_id) REFERENCES travellers(id), INDEX(booking_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS payments (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, booking_id BIGINT UNSIGNED NOT NULL, transaction_reference VARCHAR(60) NOT NULL UNIQUE,
 payment_method VARCHAR(40) NOT NULL, amount DECIMAL(12,2) NOT NULL, payment_status ENUM('pending','success','failed','refund_pending','refunded') NOT NULL,
 payment_mode ENUM('simulated','provider') NOT NULL DEFAULT 'simulated', paid_at DATETIME NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(booking_id) REFERENCES bookings(id), INDEX(booking_id), INDEX(payment_status)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS custom_tour_destinations (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, custom_tour_id BIGINT UNSIGNED NOT NULL, destination_id BIGINT UNSIGNED NOT NULL,
 sequence_number SMALLINT UNSIGNED NOT NULL, planned_arrival_date DATE NULL, planned_departure_date DATE NULL,
 FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id) ON DELETE CASCADE, FOREIGN KEY(destination_id) REFERENCES destinations(id), UNIQUE(custom_tour_id,sequence_number)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS custom_tour_activities (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, custom_tour_id BIGINT UNSIGNED NOT NULL, destination_id BIGINT UNSIGNED NULL,
 activity_name VARCHAR(180) NOT NULL, activity_date DATE NULL, start_time TIME NULL, end_time TIME NULL, estimated_cost DECIMAL(12,2) NULL,
 description TEXT, sequence_number SMALLINT UNSIGNED NOT NULL DEFAULT 1, FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id) ON DELETE CASCADE,
 FOREIGN KEY(destination_id) REFERENCES destinations(id), INDEX(custom_tour_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS custom_tour_costs (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, custom_tour_id BIGINT UNSIGNED NOT NULL, cost_category VARCHAR(60) NOT NULL,
 description VARCHAR(255), quantity DECIMAL(10,2) NOT NULL DEFAULT 1, estimated_unit_price DECIMAL(12,2) NOT NULL DEFAULT 0,
 estimated_total DECIMAL(12,2) NOT NULL DEFAULT 0, FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id) ON DELETE CASCADE
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS custom_tour_quotations (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, custom_tour_id BIGINT UNSIGNED NOT NULL, admin_id BIGINT UNSIGNED NOT NULL,
 quotation_amount DECIMAL(12,2) NOT NULL, quotation_notes TEXT, quotation_status VARCHAR(30) NOT NULL DEFAULT 'sent',
 customer_response VARCHAR(30), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, responded_at DATETIME NULL,
 FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id), FOREIGN KEY(admin_id) REFERENCES users(id), INDEX(custom_tour_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS custom_tour_status_history (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, custom_tour_id BIGINT UNSIGNED NOT NULL, previous_status VARCHAR(40), new_status VARCHAR(40) NOT NULL,
 changed_by BIGINT UNSIGNED NULL, change_reason TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id), FOREIGN KEY(changed_by) REFERENCES users(id), INDEX(custom_tour_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS itineraries (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, package_id BIGINT UNSIGNED NULL, custom_tour_id BIGINT UNSIGNED NULL, booking_id BIGINT UNSIGNED NULL,
 day_number SMALLINT UNSIGNED NOT NULL, destination_id BIGINT UNSIGNED NULL, activity_name VARCHAR(180) NOT NULL, description TEXT,
 activity_date DATE NULL, start_time TIME NULL, end_time TIME NULL, estimated_cost DECIMAL(12,2) NULL, sequence_number SMALLINT UNSIGNED NOT NULL DEFAULT 1,
 confirmation_status ENUM('suggested','confirmed') NOT NULL DEFAULT 'suggested', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, FOREIGN KEY(package_id) REFERENCES tour_packages(id),
 FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id), FOREIGN KEY(booking_id) REFERENCES bookings(id), FOREIGN KEY(destination_id) REFERENCES destinations(id), INDEX(custom_tour_id), INDEX(booking_id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS reviews (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, customer_id BIGINT UNSIGNED NOT NULL, booking_id BIGINT UNSIGNED NOT NULL,
 package_id BIGINT UNSIGNED NULL, custom_tour_id BIGINT UNSIGNED NULL, rating TINYINT UNSIGNED NOT NULL, comment TEXT NOT NULL,
 moderation_status ENUM('pending','approved','rejected') NOT NULL DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
 updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, UNIQUE(booking_id), CHECK(rating BETWEEN 1 AND 5),
 FOREIGN KEY(customer_id) REFERENCES users(id), FOREIGN KEY(booking_id) REFERENCES bookings(id), FOREIGN KEY(package_id) REFERENCES tour_packages(id), FOREIGN KEY(custom_tour_id) REFERENCES custom_tours(id)
) ENGINE=InnoDB;
