"""Модели данных для социальной сети"""
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import json
import os

# ==============================================================================
# PYDANTIC МОДЕЛИ ДЛЯ API
# ==============================================================================

class UserCreate(BaseModel):
    username: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: str
    username: str

class PostCreate(BaseModel):
    text: str

class PostResponse(BaseModel):
    id: str
    text: str
    author_id: str
    timestamp: str
    likes: int

class MessageCreate(BaseModel):
    text: str
    receiver_id: str

class MessageResponse(BaseModel):
    id: str
    text: str
    author_id: str
    receiver_id: str
    timestamp: str
    is_read: bool

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# ==============================================================================
# ОРИГИНАЛЬНЫЕ КЛАССЫ (адаптированные для веба)
# ==============================================================================

class Content:
    """Базовый класс для контента"""
    def __init__(self, text: str, author_id: str):
        self._id = str(uuid.uuid4())
        self._text = text
        self._author_id = author_id
        self._timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def id(self):
        return self._id

    @property
    def author_id(self):
        return self._author_id

    @property
    def timestamp(self):
        return self._timestamp

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "text": self._text,
            "author_id": self._author_id,
            "timestamp": self._timestamp
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Content':  # ✅ ИСПРАВЛЕНО: добавлено 'data:'
        content = cls(data['text'], data['author_id'])
        content._id = data['id']
        content._timestamp = data['timestamp']
        return content


class Post(Content):
    """Класс публикации"""
    def __init__(self, text: str, author_id: str, likes: int = 0):
        super().__init__(text, author_id)
        self._likes = likes

    def like(self):
        self._likes += 1

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["type"] = "Post"
        data["likes"] = self._likes
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':  # ✅ ИСПРАВЛЕНО: добавлено 'data:'
        post = cls(data['text'], data['author_id'], data.get('likes', 0))
        post._id = data['id']
        post._timestamp = data['timestamp']
        return post


class Message(Content):
    """Класс сообщения"""
    def __init__(self, text: str, author_id: str, receiver_id: str):
        super().__init__(text, author_id)
        self._receiver_id = receiver_id
        self._is_read = False

    def mark_as_read(self):
        self._is_read = True

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data["type"] = "Message"
        data["receiver_id"] = self._receiver_id
        data["is_read"] = self._is_read
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':  # ✅ ИСПРАВЛЕНО: добавлено 'data:'
        msg = cls(data['text'], data['author_id'], data['receiver_id'])
        msg._id = data['id']
        msg._timestamp = data['timestamp']
        msg._is_read = data.get('is_read', False)
        return msg


class User:
    """Класс пользователя"""
    def __init__(self, username: str, password: str):
        self._id = str(uuid.uuid4())
        self._username = username
        self.__password = password
        self._friends_ids: List[str] = []
        self._posts: List[Post] = []
        self._inbox: List[Message] = []
        self._outbox: List[Message] = []

    @property
    def id(self):
        return self._id

    @property
    def username(self):
        return self._username

    def check_password(self, password: str) -> bool:
        return self.__password == password

    def change_password(self, old_pass: str, new_pass: str) -> bool:
        if self.check_password(old_pass):
            self.__password = new_pass
            return True
        return False

    def add_friend(self, friend_id: str):
        if friend_id not in self._friends_ids and friend_id != self._id:
            self._friends_ids.append(friend_id)

    def remove_friend(self, friend_id: str):
        if friend_id in self._friends_ids:
            self._friends_ids.remove(friend_id)

    def get_friends_ids(self) -> List[str]:
        return self._friends_ids.copy()

    def create_post(self, text: str) -> Post:
        post = Post(text, self._id)
        self._posts.append(post)
        return post

    def get_posts(self) -> List[Post]:
        return self._posts.copy()

    def receive_message(self, message: Message):
        self._inbox.append(message)

    def send_message(self, message: Message):
        self._outbox.append(message)

    def get_inbox(self) -> List[Message]:
        for msg in self._inbox:
            msg.mark_as_read()
        return self._inbox.copy()

    def get_outbox(self) -> List[Message]:
        return self._outbox.copy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "username": self._username,
            "password": self.__password,
            "friends_ids": self._friends_ids,
            "posts": [p.to_dict() for p in self._posts],
            "inbox": [m.to_dict() for m in self._inbox],
            "outbox": [m.to_dict() for m in self._outbox]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':  # ✅ ИСПРАВЛЕНО: добавлено 'data:'
        user = cls(data['username'], data['password'])
        user._id = data['id']
        user._friends_ids = data.get('friends_ids', [])
        for p_data in data.get('posts', []):
            user._posts.append(Post.from_dict(p_data))
        for m_data in data.get('inbox', []):
            user._inbox.append(Message.from_dict(m_data))
        for m_data in data.get('outbox', []):
            user._outbox.append(Message.from_dict(m_data))
        return user


class SocialNetwork:
    """Менеджер социальной сети"""
    DB_FILE = "network_db.json"

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._current_user: Optional[User] = None
        self._load_db()

    def _load_db(self):
        if not os.path.exists(self.DB_FILE):
            return
        try:
            with open(self.DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            temp_users = {}
            for u_data in data:  # ✅ ИСПРАВЛЕНО: добавлено 'data'
                user = User.from_dict(u_data)
                temp_users[user.id] = user
            self._users = temp_users
        except Exception as e:
            print(f"Ошибка загрузки БД: {e}")
            self._users = {}

    def _save_db(self):
        try:
            data = [u.to_dict() for u in self._users.values()]
            with open(self.DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Ошибка сохранения БД: {e}")

    def register(self, username: str, password: str) -> Optional[User]:
        if any(u.username == username for u in self._users.values()):
            return None
        new_user = User(username, password)
        self._users[new_user.id] = new_user
        self._save_db()
        return new_user

    def login(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username and user.check_password(password):
                self._current_user = user
                return user
        return None

    def logout(self):
        self._current_user = None

    def find_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_current_user(self) -> Optional[User]:
        return self._current_user

    def set_current_user(self, user: User):
        self._current_user = user

# Глобальный экземпляр
network = SocialNetwork()