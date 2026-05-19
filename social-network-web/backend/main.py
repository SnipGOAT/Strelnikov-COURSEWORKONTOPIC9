"""FastAPI Backend для социальной сети"""
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

from models import (
    network, User, UserCreate, UserLogin, UserResponse,
    PostCreate, PostResponse, MessageCreate, MessageResponse,
    PasswordChange
)

app = FastAPI(
    title="Social Network API",
    description="API для модели социальной сети",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Безопасность
security = HTTPBearer()

# ==============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==============================================================================

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Получение текущего пользователя из токена"""
    user_id = credentials.credentials
    user = network.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    network.set_current_user(user)
    return user

# ==============================================================================
# API ENDPOINTS - АУТЕНТИФИКАЦИЯ
# ==============================================================================

@app.post("/api/register", response_model=UserResponse)
async def register(user_data: UserCreate):
    """Регистрация нового пользователя"""
    user = network.register(user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")
    return UserResponse(id=user.id, username=user.username)

@app.post("/api/login", response_model=UserResponse)
async def login(user_data: UserLogin):
    """Вход в систему"""
    user = network.login(user_data.username, user_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return UserResponse(id=user.id, username=user.username)

@app.post("/api/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Выход из системы"""
    network.logout()
    return {"message": "Выход выполнен"}

# ==============================================================================
# API ENDPOINTS - ПРОФИЛЬ
# ==============================================================================

@app.get("/api/profile", response_model=UserResponse)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Получение профиля текущего пользователя"""
    return UserResponse(id=current_user.id, username=current_user.username)

@app.put("/api/profile/password")
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user)
):
    """Смена пароля"""
    if current_user.change_password(password_data.old_password, password_data.new_password):
        network._save_db()
        return {"message": "Пароль изменен"}
    raise HTTPException(status_code=400, detail="Неверный старый пароль")

# ==============================================================================
# API ENDPOINTS - ДРУЗЬЯ
# ==============================================================================

@app.get("/api/friends")
async def get_friends(current_user: User = Depends(get_current_user)):
    """Получение списка друзей"""
    friends_ids = current_user.get_friends_ids()
    friends = []
    for fid in friends_ids:
        friend = network.find_user_by_id(fid)
        if friend:
            friends.append({"id": friend.id, "username": friend.username})
    return {"friends": friends}

@app.post("/api/friends/{username}")
async def add_friend(
    username: str,
    current_user: User = Depends(get_current_user)
):
    """Добавление друга"""
    target_user = network.find_user_by_username(username)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя добавить себя в друзья")
    
    current_user.add_friend(target_user.id)
    target_user.add_friend(current_user.id)
    network._save_db()
    return {"message": "Друг добавлен"}

@app.delete("/api/friends/{user_id}")
async def remove_friend(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление друга"""
    if user_id not in current_user.get_friends_ids():
        raise HTTPException(status_code=404, detail="Друг не найден")
    
    current_user.remove_friend(user_id)
    target_user = network.find_user_by_id(user_id)
    if target_user:
        target_user.remove_friend(current_user.id)
    network._save_db()
    return {"message": "Друг удален"}

# ==============================================================================
# API ENDPOINTS - ПУБЛИКАЦИИ
# ==============================================================================

@app.post("/api/posts", response_model=PostResponse)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user)
):
    """Создание публикации"""
    post = current_user.create_post(post_data.text)
    network._save_db()
    return PostResponse(
        id=post.id,
        text=post.text,
        author_id=post.author_id,
        timestamp=post.timestamp,
        likes=post._likes
    )

@app.get("/api/posts")
async def get_posts(current_user: User = Depends(get_current_user)):
    """Получение своих публикаций"""
    posts = current_user.get_posts()
    return {
        "posts": [
            {
                "id": p.id,
                "text": p.text,
                "author_id": p.author_id,
                "timestamp": p.timestamp,
                "likes": p._likes
            }
            for p in posts
        ]
    }

@app.get("/api/feed")
async def get_feed(current_user: User = Depends(get_current_user)):
    """Получение ленты новостей (посты друзей)"""
    friends_ids = current_user.get_friends_ids()
    all_posts = []
    for fid in friends_ids:
        friend = network.find_user_by_id(fid)
        if friend:
            for post in friend.get_posts():
                all_posts.append({
                    "id": post.id,
                    "text": post.text,
                    "author_id": post.author_id,
                    "author_name": friend.username,
                    "timestamp": post.timestamp,
                    "likes": post._likes
                })
    
    # Сортировка по времени (новые сверху)
    all_posts.sort(key=lambda x: x['timestamp'], reverse=True)
    return {"feed": all_posts}

# ==============================================================================
# API ENDPOINTS - СООБЩЕНИЯ
# ==============================================================================

@app.post("/api/messages", response_model=MessageResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: User = Depends(get_current_user)
):
    """Отправка сообщения"""
    target_user = network.find_user_by_id(message_data.receiver_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    message = Message(message_data.text, current_user.id, target_user.id)
    current_user.send_message(message)
    target_user.receive_message(message)
    network._save_db()
    
    return MessageResponse(
        id=message.id,
        text=message.text,
        author_id=message.author_id,
        receiver_id=message.receiver_id,
        timestamp=message.timestamp,
        is_read=message._is_read
    )

@app.get("/api/messages/inbox")
async def get_inbox(current_user: User = Depends(get_current_user)):
    """Получение входящих сообщений"""
    inbox = current_user.get_inbox()
    return {
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "author_id": m.author_id,
                "timestamp": m.timestamp,
                "is_read": m._is_read
            }
            for m in inbox
        ]
    }

@app.get("/api/messages/outbox")
async def get_outbox(current_user: User = Depends(get_current_user)):
    """Получение исходящих сообщений"""
    outbox = current_user.get_outbox()
    return {
        "messages": [
            {
                "id": m.id,
                "text": m.text,
                "receiver_id": m.receiver_id,
                "timestamp": m.timestamp,
                "is_read": m._is_read
            }
            for m in outbox
        ]
    }


# ==============================================================================
# API ENDPOINTS - РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ ПУБЛИКАЦИЙ
# ==============================================================================

@app.put("/api/posts/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: str,
    post_data: PostCreate,
    current_user: User = Depends(get_current_user)
):
    """Редактирование публикации (только в течение 30 минут)"""
    post = current_user.find_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Публикация не найдена")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав на редактирование")
    if not current_user.can_edit_post(post):
        raise HTTPException(status_code=400, detail="Редактирование доступно только в течение 30 минут")
    
    post._text = post_data.text
    network._save_db()
    
    return PostResponse(
        id=post.id,
        text=post.text,
        author_id=post.author_id,
        timestamp=post.timestamp,
        likes=post._likes
    )

@app.delete("/api/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user)
):
    """Удаление публикации"""
    post = current_user.find_post_by_id(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Публикация не найдена")
    if post.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Нет прав на удаление")
    
    if current_user.delete_post(post_id):
        network._save_db()
        return {"message": "Публикация удалена"}
    raise HTTPException(status_code=500, detail="Ошибка при удалении")


# ==============================================================================
# ЗАПУСК
# ==============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)