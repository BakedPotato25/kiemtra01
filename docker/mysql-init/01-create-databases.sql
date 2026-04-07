CREATE DATABASE IF NOT EXISTS customer_db;
CREATE DATABASE IF NOT EXISTS staff_db;

CREATE USER IF NOT EXISTS 'customer_user'@'%' IDENTIFIED BY 'customer_password';
CREATE USER IF NOT EXISTS 'staff_user'@'%' IDENTIFIED BY 'staff_password';

GRANT ALL PRIVILEGES ON customer_db.* TO 'customer_user'@'%';
GRANT ALL PRIVILEGES ON staff_db.* TO 'staff_user'@'%';
FLUSH PRIVILEGES;
