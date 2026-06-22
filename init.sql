-- Создание базы данных
CREATE DATABASE medical_exam_db;

\c medical_exam_db;

-- Таблица пользователей (1-я нормальная форма)
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    user_name VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL,
    full_name VARCHAR(200),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица сотрудников (2-я нормальная форма - зависимость от первичного ключа)
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    position VARCHAR(100) NOT NULL,
    department VARCHAR(100) NOT NULL,
    hire_date DATE NOT NULL,
    birth_date DATE,
    phone VARCHAR(20)
);

-- Таблица медицинских обследований (3-я нормальная форма - нет транзитивных зависимостей)
CREATE TABLE examinations (
    exam_id SERIAL PRIMARY KEY,
    employee_id INTEGER REFERENCES employees(employee_id) ON DELETE CASCADE,
    exam_date DATE NOT NULL,
    exam_type VARCHAR(100) NOT NULL, -- Ежегодный, Профосмотр, Дополнительный
    doctor_name VARCHAR(200),
    result TEXT,
    is_passed BOOLEAN DEFAULT FALSE,
    next_exam_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации
CREATE INDEX idx_exam_employee ON examinations(employee_id);
CREATE INDEX idx_exam_date ON examinations(exam_date);
CREATE INDEX idx_users_username ON users(user_name);

-- Вставка тестовых данных
INSERT INTO users (user_name, password_hash, email, full_name) VALUES
('admin', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'admin@clinic.com', 'Администратор'),
('ivanov_ii', '5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8', 'ivanov@company.com', 'Иванов Иван Иванович');

INSERT INTO employees (user_id, position, department, hire_date, birth_date, phone) VALUES
(2, 'Инженер-программист', 'IT отдел', '2020-03-15', '1985-05-20', '+7(999)123-45-67');

INSERT INTO examinations (employee_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date) VALUES
(1, '2024-01-15', 'Ежегодный профосмотр', 'Петрова А.С.', 'Здоров', TRUE, '2025-01-15'),
(1, '2024-06-10', 'Дополнительный', 'Сидоров В.П.', 'Требуется контроль', FALSE, '2024-09-10');
