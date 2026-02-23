CREATE DATABASE IF NOT EXISTS fest_management;
USE fest_management;

-- =====================
-- ADMIN TABLE
-- =====================
CREATE TABLE admin (
    admin_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);

-- Default Admin
INSERT INTO admin (username, password)
VALUES ('admin', 'admin123');

-- =====================
-- VOLUNTEER TABLE
-- =====================
CREATE TABLE volunteer (
    volunteer_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50),
    last_name VARCHAR(50),
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    gender ENUM('Male','Female','Other'),
    phone VARCHAR(15),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    skills VARCHAR(255) DEFAULT '',
    profile_picture VARCHAR(255) DEFAULT NULL
);

-- =====================
-- ORGANIZATION TABLE
-- =====================
CREATE TABLE organization (
    org_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    phone VARCHAR(15),
    address TEXT,
    representative VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================
-- ACTIVITY TABLE
-- =====================
CREATE TABLE activity (
    activity_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100),
    type VARCHAR(50),
    place VARCHAR(100),
    start_date DATE,
    end_date DATE,
    org_id INT,
    required_skills VARCHAR(255) DEFAULT '',
    description TEXT,
    reg_open DATETIME,
    reg_close DATETIME,
    FOREIGN KEY (org_id)
        REFERENCES organization(org_id)
        ON DELETE CASCADE
);

-- =====================
-- ACTIVITY POSITIONS TABLE
-- =====================
CREATE TABLE activity_position (
    position_id INT AUTO_INCREMENT PRIMARY KEY,
    activity_id INT,
    title VARCHAR(100),
    required_skills VARCHAR(255),
    slots INT,
    FOREIGN KEY (activity_id)
        REFERENCES activity(activity_id)
        ON DELETE CASCADE
);

-- =====================
-- VOLUNTEER_ACTIVITY (Many-to-Many)
-- =====================
CREATE TABLE volunteer_activity (
    id INT AUTO_INCREMENT PRIMARY KEY,
    volunteer_id INT,
    activity_id INT,
    position_id INT,
    role VARCHAR(50),
    attendance BOOLEAN DEFAULT FALSE,
    performance_rating INT,
    status ENUM('pending','approved','rejected') DEFAULT 'pending',
    FOREIGN KEY (volunteer_id)
        REFERENCES volunteer(volunteer_id)
        ON DELETE CASCADE,
    FOREIGN KEY (activity_id)
        REFERENCES activity(activity_id)
        ON DELETE CASCADE,
    FOREIGN KEY (position_id)
        REFERENCES activity_position(position_id)
        ON DELETE CASCADE,
    UNIQUE(volunteer_id, activity_id, position_id)
);

-- =====================
-- NOTIFICATIONS TABLE
-- =====================
CREATE TABLE notification (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    volunteer_id INT,
    activity_id INT,
    position_id INT,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (volunteer_id)
        REFERENCES volunteer(volunteer_id)
        ON DELETE CASCADE,
    FOREIGN KEY (activity_id)
        REFERENCES activity(activity_id)
        ON DELETE CASCADE,
    FOREIGN KEY (position_id)
        REFERENCES activity_position(position_id)
        ON DELETE CASCADE
);