-- ============================================================
-- БД для В3 ПУ — магазин стройматериалов.
-- Та же структура, что и для обуви, но другие данные.
-- ============================================================

DROP DATABASE IF EXISTS materials_db;
CREATE DATABASE materials_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE materials_db;

-- Роли
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE
);
INSERT INTO roles (role_name) VALUES ('client'), ('manager'), ('admin');

-- Пользователи
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    login VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    middle_name VARCHAR(100),
    role INT NOT NULL,
    FOREIGN KEY (role) REFERENCES roles(id)
);
INSERT INTO users (login, password, last_name, name, middle_name, role) VALUES
    ('client1',  '123', 'Иванов',  'Иван',  'Иванович',   1),
    ('manager1', '123', 'Петрова', 'Анна',  'Сергеевна',  2),
    ('admin1',   '123', 'Сидоров', 'Пётр',  'Алексеевич', 3);

-- Справочники
CREATE TABLE manufacturers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    manufacturer_name VARCHAR(100) NOT NULL UNIQUE
);
INSERT INTO manufacturers (manufacturer_name) VALUES
    ('Knauf'), ('Ceresit'), ('Tikkurila'), ('Bosch'), ('Makita');

CREATE TABLE suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    supplier_name VARCHAR(150) NOT NULL UNIQUE
);
INSERT INTO suppliers (supplier_name) VALUES
    ('ООО СтройОпт'),
    ('ООО МастерТорг'),
    ('ООО ПроСтрой'),
    ('ООО Инструмент-Сервис');

CREATE TABLE product_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
);
INSERT INTO product_categories (category_name) VALUES
    ('Сухие смеси'), ('Краски'), ('Инструменты'), ('Крепёж'), ('Электрика');

-- Товары
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_article VARCHAR(50) UNIQUE,
    product_name VARCHAR(200) NOT NULL,
    product_description TEXT,
    product_category INT NOT NULL,
    product_manufacturer INT NOT NULL,
    product_supplier INT NOT NULL,
    product_price DECIMAL(10,2) NOT NULL,
    current_discount INT NOT NULL DEFAULT 0,
    unit VARCHAR(20) NOT NULL DEFAULT 'шт',
    quantity INT NOT NULL DEFAULT 0,
    image VARCHAR(255),
    FOREIGN KEY (product_category) REFERENCES product_categories(id),
    FOREIGN KEY (product_manufacturer) REFERENCES manufacturers(id),
    FOREIGN KEY (product_supplier) REFERENCES suppliers(id)
);
INSERT INTO products
    (product_article, product_name, product_description, product_category,
     product_manufacturer, product_supplier, product_price, current_discount,
     unit, quantity, image)
VALUES
    ('M-001', 'Шпатлёвка финишная',  'мелкозернистая',         1, 1, 1, 890.00,  5,  'кг', 120, NULL),
    ('M-002', 'Грунтовка глубокого', 'для впитывающих основ',  2, 2, 2, 1250.00, 15, 'л',   50, NULL),
    ('M-003', 'Краска интерьерная',  'белая матовая',          2, 3, 2, 2400.00, 20, 'л',   30, NULL),  -- > 12% → оранжевый
    ('M-004', 'Дрель ударная',       'мощность 750 Вт',        3, 4, 4, 5600.00, 0,  'шт',   0, NULL),  -- 0 → голубой
    ('M-005', 'Саморезы 4x60',       'оцинкованные',           4, 5, 1, 320.00,  8,  'уп',  200, NULL),
    ('M-006', 'Кабель ВВГнг 3x2.5',  'медный, негорючий',      5, 1, 3, 95.00,   25, 'м',  500, NULL);  -- > 12% → оранжевый

-- Заказы
CREATE TABLE order_statuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    status_name VARCHAR(50) NOT NULL UNIQUE
);
INSERT INTO order_statuses (status_name) VALUES
    ('Новый'), ('В обработке'), ('Готов к выдаче'), ('Выдан'), ('Отменён');

CREATE TABLE orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_article VARCHAR(50) NOT NULL UNIQUE,
    status INT NOT NULL,
    pickup_address VARCHAR(255) NOT NULL,
    order_date DATE NOT NULL,
    delivery_date DATE,
    FOREIGN KEY (status) REFERENCES order_statuses(id)
);

CREATE TABLE order_items (
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    PRIMARY KEY (order_id, product_id),
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO orders (order_article, status, pickup_address, order_date, delivery_date) VALUES
    ('ORD-001', 1, 'г. Москва, ул. Строителей, 12',  '2026-05-25', '2026-05-30'),
    ('ORD-002', 3, 'г. Казань, пр. Победы, 45',      '2026-05-26', '2026-05-29');

INSERT INTO order_items (order_id, product_id, quantity) VALUES
    (1, 1, 10),
    (1, 5, 100),
    (2, 3, 5);
