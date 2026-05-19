"""Стрельников Максим (ИСТ04/25б). Проект ЯиМП"""
## *ПРОЕКТНАЯ РАБОТА*
## 9. Модель социальной сети. Пользователи, друзья, сообщения, публикации, поддержка работы с файлами профилей.

import json
import datetime
import uuid
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class Content(ABC):
    def __init__(self, text: str, author_id: str):
        self._id = str(uuid.uuid4())
        self._text = text
        self._author_id = author_id
        self._timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @abstractmethod
    def render(self) -> str: pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]: pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Content': pass

    @property
    def id(self): return self._id
    @property
    def author_id(self): return self._author_id
    @property
    def timestamp(self): return self._timestamp
    @property
    def text(self): return self._text


class Post(Content):
    def __init__(self, text: str, author_id: str, likes: int = 0):
        super().__init__(text, author_id)
        self._likes = likes
        self._liked_by: List[str] = []

    def render(self) -> str:
        return f"[ПУБЛИКАЦИЯ] ({self._timestamp})\nТекст: {self._text}\nЛайки: {self._likes}"

    def like(self, user_id: str) -> bool:
        if user_id in self._liked_by:
            return False
        self._liked_by.append(user_id)
        self._likes += 1
        return True

    def unlike(self, user_id: str) -> bool:
        if user_id not in self._liked_by:
            return False
        self._liked_by.remove(user_id)
        self._likes = max(0, self._likes - 1)
        return True

    @property
    def likes(self): return self._likes
    @property
    def liked_by(self): return self._liked_by.copy()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Post",
            "id": self._id,
            "text": self._text,
            "author_id": self._author_id,
            "timestamp": self._timestamp,
            "likes": self._likes,
            "liked_by": self._liked_by
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        post = cls(data['text'], data['author_id'], data.get('likes', 0))
        post._id = data['id']
        post._timestamp = data['timestamp']
        post._liked_by = data.get('liked_by', [])
        return post


class Message(Content):
    def __init__(self, text: str, author_id: str, receiver_id: str):
        super().__init__(text, author_id)
        self._receiver_id = receiver_id
        self._is_read = False

    def render(self) -> str:
        status = "Прочитано" if self._is_read else "Новое"
        return f"[СООБЩЕНИЕ] ({self._timestamp}) [{status}]\nОт: {self._author_id}\n{self._text}"

    def mark_as_read(self):
        self._is_read = True

    @property
    def receiver_id(self): return self._receiver_id
    @property
    def is_read(self): return self._is_read

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Message",
            "id": self._id,
            "text": self._text,
            "author_id": self._author_id,
            "receiver_id": self._receiver_id,
            "timestamp": self._timestamp,
            "is_read": self._is_read
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        msg = cls(data['text'], data['author_id'], data['receiver_id'])
        msg._id = data['id']
        msg._timestamp = data['timestamp']
        msg._is_read = data.get('is_read', False)
        return msg


class User:
    def __init__(self, username: str, password: str):
        self._id = str(uuid.uuid4())
        self._username = username
        self.__password = password
        self._friends_ids: List[str] = []
        self._posts: List[Post] = []
        self._inbox: List[Message] = []
        self._outbox: List[Message] = []

    @property
    def id(self): return self._id
    @property
    def username(self): return self._username

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

    def find_post(self, post_id: str) -> Optional[Post]:
        for p in self._posts:
            if p.id == post_id:
                return p
        return None

    def receive_message(self, message: Message):
        self._inbox.append(message)

    def send_message(self, message: Message):
        self._outbox.append(message)

    def get_inbox(self, mark_read: bool = True) -> List[Message]:
        if mark_read:
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
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
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
    DB_FILE = "network_db.json"

    def __init__(self):
        self._users: Dict[str, User] = {}
        self._load_db()

    def _load_db(self):
        if not os.path.exists(self.DB_FILE):
            return
        try:
            with open(self.DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            temp_users = {}
            for u_data in data:  # ИСПРАВЛЕНО: было temp_users
                user = User.from_dict(u_data)
                temp_users[user.id] = user
            self._users = temp_users
            print(f"[СИСТЕМА] Загружено пользователей: {len(self._users)}")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось загрузить БД: {e}")
            self._users = {}

    def save_db(self):
        try:
            data = [u.to_dict() for u in self._users.values()]
            with open(self.DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ОШИБКА] Сохранение: {e}")

    def register(self, username: str, password: str) -> Optional[User]:
        if any(u.username == username for u in self._users.values()):
            return None
        new_user = User(username, password)
        self._users[new_user.id] = new_user
        self.save_db()
        return new_user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username and user.check_password(password):
                return user
        return None

    def find_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def all_users(self) -> List[User]:
        return list(self._users.values())
