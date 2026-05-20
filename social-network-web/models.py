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
    def render(self) -> str:
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Content':
        pass

    @property
    def id(self):
        return self._id

    @property
    def author_id(self):
        return self._author_id

    @property
    def timestamp(self):
        return self._timestamp


class Post(Content):
    def __init__(self, text: str, author_id: str, liked_by: List[str] = None):
        super().__init__(text, author_id)
        self._liked_by = liked_by if liked_by is not None else []

    def render(self) -> str:
        return f"[ПУБЛИКАЦИЯ] ({self._timestamp})\nТекст: {self._text}\nЛайки: {len(self._liked_by)}"

    def toggle_like(self, user_id: str):
        """Добавляет или убирает лайк пользователя. Возвращает (количество лайков, True если теперь лайкнуто)."""
        if user_id in self._liked_by:
            self._liked_by.remove(user_id)
            liked = False
        else:
            self._liked_by.append(user_id)
            liked = True
        return len(self._liked_by), liked

    @property
    def likes(self):
        return len(self._liked_by)

    @property
    def liked_by_ids(self):
        return self._liked_by.copy()

    @property
    def text(self):
        return self._text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Post",
            "id": self._id,
            "text": self._text,
            "author_id": self._author_id,
            "timestamp": self._timestamp,
            "liked_by": self._liked_by
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        # поддержка старых данных, где было поле 'likes'
        liked_by = data.get('liked_by', [])
        if not liked_by and 'likes' in data:
            liked_by = []
        post = cls(data['text'], data['author_id'], liked_by)
        post._id = data['id']
        post._timestamp = data['timestamp']
        return post


class Message(Content):
    def __init__(self, text: str, author_id: str, receiver_id: str):
        super().__init__(text, author_id)
        self._receiver_id = receiver_id
        self._is_read = False

    def render(self) -> str:
        status = "Прочитано" if self._is_read else "Новое"
        return f"[СООБЩЕНИЕ] ({self._timestamp}) [{status}]\nОт кого: {self._author_id}\nТекст: {self._text}"

    def mark_as_read(self):
        self._is_read = True

    @property
    def is_read(self):
        return self._is_read

    @property
    def receiver_id(self):
        return self._receiver_id

    @property
    def text(self):
        return self._text

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

    def get_post_by_id(self, post_id: str) -> Optional[Post]:
        for p in self._posts:
            if p.id == post_id:
                return p
        return None

    def delete_post(self, post_id: str) -> bool:
        for i, post in enumerate(self._posts):
            if post.id == post_id:
                del self._posts[i]
                return True
        return False

    def receive_message(self, message: Message):
        self._inbox.append(message)

    def send_message(self, message: Message):
        self._outbox.append(message)

    def get_inbox(self) -> List[Message]:
        return self._inbox.copy()

    def get_outbox(self) -> List[Message]:
        return self._outbox.copy()

    def get_unread_messages_count(self) -> int:
        return sum(1 for msg in self._inbox if not msg.is_read)

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
            for u_data in data:
                user = User.from_dict(u_data)
                self._users[user.id] = user
        except Exception as e:
            print(f"[ОШИБКА] {e}")

    def save_db(self):
        try:
            data = [u.to_dict() for u in self._users.values()]
            with open(self.DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ОШИБКА] {e}")

    def register(self, username: str, password: str) -> Optional[User]:
        if any(u.username == username for u in self._users.values()):
            return None
        user = User(username, password)
        self._users[user.id] = user
        self.save_db()
        return user

    def login(self, username: str, password: str) -> Optional[User]:
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

    def get_all_users(self):
        return list(self._users.values())

    def find_post_global(self, post_id: str) -> Optional[Post]:
        for user in self._users.values():
            post = user.get_post_by_id(post_id)
            if post:
                return post
        return None