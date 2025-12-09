from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
import os
from typing import Optional
import redis
import json

app = FastAPI(title="User Management API")

# CORS для взаимодействия с фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение к БД
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "postgres"),
        database=os.getenv("DB_NAME", "userdb"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "postgres"),
        cursor_factory=RealDictCursor
    )
    return conn

# Подключение к Redis
def get_redis_connection():
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )
        r.ping()
        return r
    except:
        return None

# Модели данных
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None

# Функции для работы с паролями
def hash_password(password: str) -> str:
    """Хеширование пароля с помощью bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Проверка пароля"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# API endpoints
@app.get("/")
async def root():
    return {"message": "User Management API", "status": "online"}

@app.get("/api/redis/stats")
async def redis_stats():
    """Получить статистику Redis (для демонстрации 5-го контейнера)"""
    redis_conn = get_redis_connection()
    if not redis_conn:
        return {"status": "Redis unavailable"}
    
    try:
        info = redis_conn.info()
        return {
            "status": "connected",
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "total_connections_received": info.get("total_connections_received"),
            "keyspace": redis_conn.dbsize()
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/api/users")
async def get_users():
    """Получить список всех пользователей (с кешированием в Redis)"""
    try:
        # Попытка получить из кеша
        redis_conn = get_redis_connection()
        if redis_conn:
            cached = redis_conn.get("users_list")
            if cached:
                return {"users": json.loads(cached), "source": "cache"}
        
        # Получение из БД
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id")
        users = cur.fetchall()
        cur.close()
        conn.close()
        
        # Сохранение в кеш на 30 секунд
        if redis_conn:
            redis_conn.setex("users_list", 30, json.dumps(users, default=str))
        
        return {"users": users, "source": "database"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """Получить информацию о пользователе"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, role, created_at FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/register", status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    """Регистрация нового пользователя"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверка существования пользователя
        cur.execute("SELECT id FROM users WHERE username = %s OR email = %s", 
                   (user.username, user.email))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Username or email already exists")
        
        # Хеширование пароля и создание пользователя
        hashed_password = hash_password(user.password)
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id, username, email, role, created_at",
            (user.username, user.email, hashed_password)
        )
        new_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        # Очистить кеш списка пользователей
        redis_conn = get_redis_connection()
        if redis_conn:
            redis_conn.delete("users_list")
        
        return {"message": "User created successfully", "user": new_user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/login")
async def login_user(credentials: UserLogin):
    """Вход пользователя (с защитой от брутфорса через Redis)"""
    try:
        # Проверка блокировки в Redis
        redis_conn = get_redis_connection()
        if redis_conn:
            login_attempts_key = f"login_attempts:{credentials.username}"
            attempts = redis_conn.get(login_attempts_key)
            if attempts and int(attempts) >= 5:
                raise HTTPException(
                    status_code=429, 
                    detail="Too many failed login attempts. Please try again in 5 minutes."
                )
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT id, username, email, password_hash, role FROM users WHERE username = %s", 
                   (credentials.username,))
        user = cur.fetchone()
        cur.close()
        conn.close()
        
        if not user or not verify_password(credentials.password, user['password_hash']):
            # Увеличить счётчик неудачных попыток
            if redis_conn:
                redis_conn.incr(login_attempts_key)
                redis_conn.expire(login_attempts_key, 300)  # 5 минут
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        # Успешный вход - сбросить счётчик
        if redis_conn:
            redis_conn.delete(login_attempts_key)
        
        return {
            "message": "Login successful",
            "user": {
                "id": user['id'],
                "username": user['username'],
                "email": user['email'],
                "role": user['role']
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, user_data: UserUpdate):
    """Обновление данных пользователя"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Проверка существования пользователя
        cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="User not found")
        
        # Формирование запроса на обновление
        updates = []
        params = []
        
        if user_data.email:
            updates.append("email = %s")
            params.append(user_data.email)
        
        if user_data.password:
            updates.append("password_hash = %s")
            params.append(hash_password(user_data.password))
        
        if user_data.role:
            updates.append("role = %s")
            params.append(user_data.role)
        
        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s RETURNING id, username, email, role, updated_at"
        
        cur.execute(query, params)
        updated_user = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        # Очистить кеш списка пользователей
        redis_conn = get_redis_connection()
        if redis_conn:
            redis_conn.delete("users_list")
        
        return {"message": "User updated successfully", "user": updated_user}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    """Удаление пользователя"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("DELETE FROM users WHERE id = %s RETURNING id", (user_id,))
        deleted = cur.fetchone()
        
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        
        conn.commit()
        cur.close()
        conn.close()
        
        # Очистить кеш списка пользователей
        redis_conn = get_redis_connection()
        if redis_conn:
            redis_conn.delete("users_list")
        
        return {"message": "User deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
