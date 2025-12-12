-- Run this on your MySQL server (database name: chore_db)
CREATE DATABASE IF NOT EXISTS chore_db;
USE chore_db;

-- Drop tables if exist (useful for re-run)
DROP TABLE IF EXISTS chore_assignments;
DROP TABLE IF EXISTS chores;
DROP TABLE IF EXISTS members;
DROP TABLE IF EXISTS users;

-- members table
CREATE TABLE members (
  member_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

-- chores table
CREATE TABLE chores (
  chore_id INT AUTO_INCREMENT PRIMARY KEY,
  chore_name VARCHAR(150) NOT NULL UNIQUE,
  frequency VARCHAR(50) NOT NULL
);

-- assignments (your exact table structure)
CREATE TABLE chore_assignments (
  assignment_id INT AUTO_INCREMENT PRIMARY KEY,
  member_id INT,
  chore_id INT,
  assigned_date DATE,
  is_completed BOOLEAN DEFAULT FALSE,
  FOREIGN KEY (member_id) REFERENCES members(member_id),
  FOREIGN KEY (chore_id) REFERENCES chores(chore_id)
);

-- simple users table for authentication
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(80) NOT NULL UNIQUE,
  password VARCHAR(200) NOT NULL -- store hashed passwords (for demo we will use plain; in production hash)
);

-- seed members (5)
INSERT INTO members (name) VALUES
('Jezelle'),('Mark'),('Ana'),('Rico'),('Mae');

-- seed chores (5)
INSERT INTO chores (chore_name, frequency) VALUES
('Wash dishes','Daily'),
('Sweep the floor','Daily'),
('Clean the bathroom','Weekly'),
('Take out trash','Daily'),
('Water the plants','Daily');

-- seed assignments (20 rows)
INSERT INTO chore_assignments (member_id, chore_id, assigned_date, is_completed) VALUES
(1,1,'2025-01-01',TRUE),
(2,2,'2025-01-01',FALSE),
(3,3,'2025-01-02',TRUE),
(4,4,'2025-01-02',FALSE),
(5,5,'2025-01-02',TRUE),
(1,2,'2025-01-03',FALSE),
(2,3,'2025-01-03',TRUE),
(3,4,'2025-01-03',FALSE),
(4,5,'2025-01-04',TRUE),
(5,1,'2025-01-04',FALSE),
(1,3,'2025-01-05',TRUE),
(2,4,'2025-01-05',FALSE),
(3,5,'2025-01-05',TRUE),
(4,1,'2025-01-06',FALSE),
(5,2,'2025-01-06',TRUE),
(1,4,'2025-01-07',FALSE),
(2,5,'2025-01-07',TRUE),
(3,1,'2025-01-07',FALSE),
(4,2,'2025-01-08',TRUE),
(5,3,'2025-01-08',FALSE);

-- seed a demo user (password: demo123) — for production hash!
INSERT INTO users (username, password) VALUES ('teacher','demo123');
