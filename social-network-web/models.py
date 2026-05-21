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
        liked_by = data.get('liked_by', [])
        if not liked_by and 'likes' in data:
            liked_by = []
        post = cls(data['text'], data['author_id'], liked_by)
        post._id = data['id']
        post._timestamp = data['timestamp']
        return post


class Message(Content):
    def __init__(self, text: str, author_id: str, receiver_id: str, attachment: str = None, edited: bool = False):
        super().__init__(text, author_id)
        self._receiver_id = receiver_id
        self._is_read = False
        self._attachment = attachment
        self._edited = edited

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

    @property
    def attachment(self):
        return self._attachment

    @property
    def edited(self):
        return self._edited

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "Message",
            "id": self._id,
            "text": self._text,
            "author_id": self._author_id,
            "receiver_id": self._receiver_id,
            "timestamp": self._timestamp,
            "is_read": self._is_read,
            "attachment": self._attachment,
            "edited": self._edited
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        msg = cls(data['text'], data['author_id'], data['receiver_id'], data.get('attachment'), data.get('edited', False))
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

    def get_contacts(self) -> List[Dict[str, Any]]:
        contacts = {}
        for msg in self._inbox:
            contact_id = msg.author_id
            if contact_id not in contacts:
                contacts[contact_id] = {
                    'user_id': contact_id,
                    'last_msg_time': msg.timestamp,
                    'unread': 0 if msg.is_read else 1
                }
            else:
                if msg.timestamp > contacts[contact_id]['last_msg_time']:
                    contacts[contact_id]['last_msg_time'] = msg.timestamp
                if not msg.is_read:
                    contacts[contact_id]['unread'] += 1

        for msg in self._outbox:
            contact_id = msg.receiver_id
            if contact_id not in contacts:
                contacts[contact_id] = {
                    'user_id': contact_id,
                    'last_msg_time': msg.timestamp,
                    'unread': 0
                }
            else:
                if msg.timestamp > contacts[contact_id]['last_msg_time']:
                    contacts[contact_id]['last_msg_time'] = msg.timestamp

        sorted_contacts = sorted(contacts.values(), key=lambda x: x['last_msg_time'], reverse=True)
        return sorted_contacts

    def get_conversation_with(self, contact_id: str, mark_read: bool = True) -> List[Dict[str, Any]]:
        messages = []
        for msg in self._inbox:
            if msg.author_id == contact_id:
                if mark_read and not msg.is_read:
                    msg.mark_as_read()
                messages.append({
                    'id': msg.id,
                    'text': msg.text,
                    'from': msg.author_id,
                    'to': msg.receiver_id,
                    'time': msg.timestamp,
                    'direction': 'in',
                    'is_read': msg.is_read,
                    'attachment': msg.attachment,
                    'edited': msg.edited
                })
        for msg in self._outbox:
            if msg.receiver_id == contact_id:
                messages.append({
                    'id': msg.id,
                    'text': msg.text,
                    'from': msg.author_id,
                    'to': msg.receiver_id,
                    'time': msg.timestamp,
                    'direction': 'out',
                    'is_read': msg.is_read,
                    'attachment': msg.attachment,
                    'edited': msg.edited
                })
        messages.sort(key=lambda x: x['time'])
        return messages

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

    # ---------- Новые методы для сообщений ----------
    def find_message_global(self, message_id: str) -> Optional[Message]:
        """Найти сообщение по id среди всех пользователей."""
        for user in self._users.values():
            for msg in user._inbox + user._outbox:
                if msg.id == message_id:
                    return msg
        return None

    def delete_message_for_user(self, message_id: str, user_id: str, scope: str) -> bool:
        """
        Удалить сообщение: scope='me' — удалить только у себя (из своих списков),
        scope='all' — удалить у всех (только если пользователь отправитель).
        Возвращает True, если удаление выполнено.
        """
        user = self.find_user_by_id(user_id)
        if not user:
            return False

        # Ищем сообщение в inbox или outbox пользователя
        target_msg = None
        for msg in user._inbox + user._outbox:
            if msg.id == message_id:
                target_msg = msg
                break

        if not target_msg:
            return False

        if scope == 'all':
            # Удалить для всех может только отправитель
            if target_msg.author_id != user_id:
                return False
            # Удаляем у получателя
            receiver = self.find_user_by_id(target_msg.receiver_id)
            if receiver:
                self._remove_message_from_lists(receiver, message_id)
            # Удаляем у отправителя
            self._remove_message_from_lists(user, message_id)
            return True
        else:  # scope == 'me'
            self._remove_message_from_lists(user, message_id)
            return True

    def _remove_message_from_lists(self, user: 'User', message_id: str):
        """Удалить сообщение из inbox и outbox конкретного пользователя (по id)."""
        for lst in (user._inbox, user._outbox):
            for i, msg in enumerate(lst):
                if msg.id == message_id:
                    del lst[i]
                    return

    def edit_message_text(self, message_id: str, user_id: str, new_text: str) -> bool:
        """Редактировать текст своего сообщения (обновляет копии у отправителя и получателя)."""
        user = self.find_user_by_id(user_id)
        if not user:
            return False
        # Ищем сообщение в outbox пользователя (только отправитель может редактировать)
        for msg in user._outbox:
            if msg.id == message_id:
                msg._text = new_text
                msg._edited = True
                # Обновляем копию у получателя
                receiver = self.find_user_by_id(msg.receiver_id)
                if receiver:
                    for rmsg in receiver._inbox:
                        if rmsg.id == message_id:
                            rmsg._text = new_text
                            rmsg._edited = True
                            break
                return True
        return False
