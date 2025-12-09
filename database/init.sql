-- БД userdb создаётся автоматически через переменную POSTGRES_DB

-- Создание таблицы пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Создание индексов для быстрого поиска
CREATE INDEX idx_username ON users(username);
CREATE INDEX idx_email ON users(email);

-- Вставка тестового администратора (пароль: admin123)
-- Хеш сгенерирован с помощью bcrypt через backend API
INSERT INTO users (username, email, password_hash, role) 
VALUES ('admin', 'admin@example.com', '$2b$12$vbOLlLIlv0RYvuetkK.Gce0Bhi0vf91RS2/Vji42yG1tse.mNZyqi', 'admin')
ON CONFLICT (username) DO NOTHING;

-- Создание функции для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Создание триггера для автоматического обновления времени
CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
