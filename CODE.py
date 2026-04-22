"""Стрельников Максим (ИСТ04/25б). Проект ЯиМП"""
## *ПРОЕКТНАЯ РАБОТА*
## 9. Модель социальной сети. Пользователи, друзья, сообщения, публикации, поддержка работы с файлами профилей.

import json
import datetime
import uuid
import os
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any

# БАЗОВЫЕ КЛАССЫ И ИНФРАСТРУКТУРА

class Content(ABC):
    """Абстрактный базовый класс для любого контента в социальной сети. Реализует принцип наследования и полиморфизма."""
    def __init__(self, text: str, author_id: str):
        self._id = str(uuid.uuid4())
        self._text = text
        self._author_id = author_id
        self._timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @abstractmethod
    def render(self) -> str:
        """Метод для отображения контента (полиморфизм)."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Метод для сериализации объекта в словарь."""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data:  Dict[str, Any]) -> 'Content':
        """Метод для десериализации объекта из словаря."""
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
    """Класс Публикации (лента новостей)."""
    def __init__(self, text: str, author_id: str, likes: int = 0):
        super().__init__(text, author_id)
        self._likes = likes

    def render(self) -> str:
        return f"[ПУБЛИКАЦИЯ] ({self._timestamp})\nТекст: {self._text}\nЛайки: {self._likes}"

    def like(self):
        self._likes += 1

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict() if hasattr(super(), 'to_dict') else {}
        # Переопределяем логику для JSON
        return {
            "type": "Post",
            "id": self._id,
            "text": self._text,
            "author_id": self._author_id,
            "timestamp": self._timestamp,
            "likes": self._likes
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Post':
        post = cls(data['text'], data['author_id'], data.get('likes', 0))
        post._id = data['id']
        post._timestamp = data['timestamp']
        return post


class Message(Content):
    """Класс Личного сообщения."""
    def __init__(self, text: str, author_id: str, receiver_id: str):
        super().__init__(text, author_id)
        self._receiver_id = receiver_id
        self._is_read = False

    def render(self) -> str:
        status = "Прочитано" if self._is_read else "Новое"
        return f"[СООБЩЕНИЕ] ({self._timestamp}) [{status}]\nОт кого: {self._author_id}\nТекст: {self._text}"

    def mark_as_read(self):
        self._is_read = True

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


# ПОЛЬЗОВАТЕЛЬ

class User:
    """Класс Пользователя. Реализует принцип инкапсуляции (скрытие пароля и внутренних списков)."""
    def __init__(self, username: str, password: str):
        self._id = str(uuid.uuid4())
        self._username = username
        self.__password = password  # Приватный атрибут
        self._friends_ids: List[str] = []
        self._posts: List[Post] = []
        self._inbox: List[Message] = []
        self._outbox: List[Message] = []

    # Геттеры и сеттеры 
    @property
    def id(self):
        return self._id

    @property
    def username(self):
        return self._username

    def check_password(self, password: str) -> bool:
        """Проверка пароля без его возврата."""
        return self.__password == password

    def change_password(self, old_pass: str, new_pass: str) -> bool:
        if self.check_password(old_pass):
            self.__password = new_pass
            return True
        return False

    # Логика друзей
    def add_friend(self, friend_id: str):
        if friend_id not in self._friends_ids and friend_id != self._id:
            self._friends_ids.append(friend_id)

    def remove_friend(self, friend_id: str):
        if friend_id in self._friends_ids:
            self._friends_ids.remove(friend_id)

    def get_friends_ids(self) -> List[str]:
        return self._friends_ids.copy()

    # Логика публикаций
    def create_post(self, text: str) -> Post:
        post = Post(text, self._id)
        self._posts.append(post)
        return post

    def get_posts(self) -> List[Post]:
        return self._posts.copy()

    # Логика сообщений
    def receive_message(self, message: Message):
        self._inbox.append(message)

    def send_message(self, message: Message):
        self._outbox.append(message)

    def get_inbox(self) -> List[Message]:
        # Помечаем сообщения как прочитанные при получении списка
        for msg in self._inbox:
            msg.mark_as_read()
        return self._inbox.copy()

    def get_outbox(self) -> List[Message]:
        return self._outbox.copy()

    # Сериализация
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self._id,
            "username": self._username,
            "password": self.__password, # В реальном проекте пароль хешируют!
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
        
        # Восстанавливаем объекты контента
        for p_data in data.get('posts', []):
            user._posts.append(Post.from_dict(p_data))
        for m_data in data.get('inbox', []):
            user._inbox.append(Message.from_dict(m_data))
        for m_data in data.get('outbox', []):
            user._outbox.append(Message.from_dict(m_data))
        return user

    def export_profile_to_file(self, filename: str = None):
        """Сохранение профиля в отдельный текстовый файл."""
        if not filename:
            filename = f"{self._username}_profile.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ: {self._username} ===\n\n")
            f.write(f"ID: {self._id}\n")
            f.write(f"Друзей (ID): {len(self._friends_ids)}\n")
            f.write(f"Всего публикаций: {len(self._posts)}\n\n")
            
            f.write("--- ПОСЛЕДНИЕ ПУБЛИКАЦИИ ---\n")
            for post in self._posts[-5:]: # Последние 5
                f.write(f"{post.render()}\n\n")
            
            f.write("--- ВХОДЯЩИЕ СООБЩЕНИЯ ---\n")
            for msg in self._inbox[-5:]:
                f.write(f"{msg.render()}\n\n")
        
        print(f"[СИСТЕМА] Профиль успешно сохранен в файл: {filename}")


# УПРАВЛЕНИЕ СЕТЬЮ (КОНТРОЛЛЕР)

class SocialNetwork:
    """Класс-менеджер социальной сети. Отвечает за регистрацию, вход, сохранение и загрузку базы данных."""
    DB_FILE = "network_db.json"

    def __init__(self):
        self._users: Dict[str, User] = {}  # Ключ: user_id
        self._current_user: Optional[User] = None
        self._load_db()

    def _load_db(self):
        """Загрузка данных из файла при старте."""
        if not os.path.exists(self.DB_FILE):
            print("[СИСТЕМА] База данных не найдена. Создается новая.")
            return

        try:
            with open(self.DB_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Сначала создаем всех пользователей
            temp_users = {}
            for u_data in temp_users:
                user = User.from_dict(u_data)
                temp_users[user.id] = user
            
            # Затем восстанавливаем связи (друзья)
            # В данном упрощенном варианте ID друзей хранятся как строки, 
            # поэтому дополнительная связка объектов не требуется, 
            # но если бы нужны были объекты друзей, здесь был бы второй проход.
            self._users = temp_users
            print(f"[СИСТЕМА] Загружено пользователей: {len(self._users)}")
        except Exception as e:
            print(f"[ОШИБКА] Не удалось загрузить базу данных: {e}")
            self._users = {}

    def _save_db(self):
        """Сохранение всех данных в файл."""
        try:
            data = [u.to_dict() for u in self._users.values()]
            with open(self.DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[ОШИБКА] Не удалось сохранить базу данных: {e}")

    def register(self, username: str, password: str) -> bool:
        if any(u.username == username for u in self._users.values()):
            print("[ОШИБКА] Пользователь с таким именем уже существует.")
            return False
        
        new_user = User(username, password)
        self._users[new_user.id] = new_user
        self._save_db()
        print(f"[УСПЕХ] Пользователь {username} зарегистрирован.")
        return True

    def login(self, username: str, password: str) -> bool:
        for user in self._users.values():
            if user.username == username:
                if user.check_password(password):
                    self._current_user = user
                    print(f"[УСПЕХ] Вход выполнен как {username}.")
                    return True
                else:
                    print("[ОШИБКА] Неверный пароль.")
                    return False
        print("[ОШИБКА] Пользователь не найден.")
        return False

    def logout(self):
        self._current_user = None
        print("[СИСТЕМА] Выход из аккаунта.")

    def find_user_by_username(self, username: str) -> Optional[User]:
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def find_user_by_id(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def get_current_user(self) -> Optional[User]:
        return self._current_user


# КОНСОЛЬНЫЙ ИНТЕРФЕЙС (UI)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title: str):
    print("\n" + "=" * 40)
    print(f" {title} ".center(40, "="))
    print("=" * 40)

def menu_auth(network: SocialNetwork):
    while True:
        print_header("АВТОРИЗАЦИЯ")
        print("1. Войти")
        print("2. Регистрация")
        print("3. Выход из программы")
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            username = input("Логин: ").strip()
            password = input("Пароль: ").strip()
            if network.login(username, password):
                menu_user(network)
        elif choice == '2':
            username = input("Придумайте логин: ").strip()
            if not username:
                print("Логин не может быть пустым.")
                continue
            password = input("Придумайте пароль: ").strip()
            if not password:
                print("Пароль не может быть пустым.")
                continue
            network.register(username, password)
        elif choice == '3':
            print("До свидания!")
            break
        else:
            print("Неверный выбор.")

def menu_user(network: SocialNetwork):
    user = network.get_current_user()
    if not user:
        return

    while True:
        print_header(f"МЕНЮ: {user.username}")
        print("1. Мой профиль")
        print("2. Друзья")
        print("3. Публикации (Лента)")
        print("4. Сообщения")
        print("5. Настройки")
        print("6. Выйти из аккаунта")
        
        choice = input("\nВыберите действие: ").strip()
        
        if choice == '1':
            show_profile(user, network)
        elif choice == '2':
            menu_friends(user, network)
        elif choice == '3':
            menu_posts(user, network)
        elif choice == '4':
            menu_messages(user, network)
        elif choice == '5':
            menu_settings(user, network)
        elif choice == '6':
            network.logout()
            break
        else:
            print("Неверный выбор.")

def show_profile(user: User, network: SocialNetwork):
    print_header("МОЙ ПРОФИЛЬ")
    print(f"ID: {user.id}")
    print(f"Имя: {user.username}")
    print(f"Друзей: {len(user.get_friends_ids())}")
    print(f"Публикаций: {len(user.get_posts())}")
    
    action = input("\n[1] Экспорт профиля в файл | [2] Назад: ").strip()
    if action == '1':
        user.export_profile_to_file()
        input("Нажмите Enter для продолжения...")

def menu_friends(user: User, network: SocialNetwork):
    while True:
        print_header("ДРУЗЬЯ")
        friends_ids = user.get_friends_ids()
        if not friends_ids:
            print("Список друзей пуст.")
        else:
            print("Ваши друзья:")
            for fid in friends_ids:
                f_user = network.find_user_by_id(fid)
                if f_user:
                    print(f"- {f_user.username} (ID: {fid})")
        
        print("\n1. Добавить друга (по логину)")
        print("2. Удалить друга (по ID)")
        print("3. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            target_name = input("Введите логин друга: ").strip()
            target_user = network.find_user_by_username(target_name)
            if target_user and target_user.id != user.id:
                if target_user.id not in friends_ids:
                    user.add_friend(target_user.id)
                    # В реальной сети нужно подтверждение, здесь упрощено
                    target_user.add_friend(user.id) 
                    network._save_db()
                    print("Друг добавлен!")
                else:
                    print("Уже в друзьях.")
            else:
                print("Пользователь не найден или это вы сами.")
        elif choice == '2':
            target_id = input("Введите ID друга для удаления: ").strip()
            if target_id in friends_ids:
                user.remove_friend(target_id)
                t_user = network.find_user_by_id(target_id)
                if t_user:
                    t_user.remove_friend(user.id)
                network._save_db()
                print("Друг удален.")
            else:
                print("Друг не найден в списке.")
        elif choice == '3':
            break

def menu_posts(user: User, network: SocialNetwork):
    while True:
        print_header("ПУБЛИКАЦИИ")
        print("1. Создать публикацию")
        print("2. Моя стена")
        print("3. Лента друзей")
        print("4. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            text = input("Текст публикации: ").strip()
            if text:
                user.create_post(text)
                network._save_db()
                print("Опубликовано!")
        elif choice == '2':
            posts = user.get_posts()
            if not posts:
                print("Публикаций нет.")
            else:
                for p in reversed(posts):
                    print(p.render())
                    print("-" * 30)
        elif choice == '3':
            print("Лента новостей (посты друзей):")
            friends_ids = user.get_friends_ids()
            found_posts = []
            for fid in friends_ids:
                f_user = network.find_user_by_id(fid)
                if f_user:
                    found_posts.extend(f_user.get_posts())
            
            # Сортировка по времени
            if not found_posts:
                print("Лента пуста.")
            else:
                for p in reversed(found_posts):
                    author = network.find_user_by_id(p.author_id)
                    name = author.username if author else "Unknown"
                    print(f"[Автор: {name}]")
                    print(p.render())
                    print("-" * 30)
        elif choice == '4':
            break

def menu_messages(user: User, network: SocialNetwork):
    while True:
        print_header("СООБЩЕНИЯ")
        print("1. Входящие")
        print("2. Исходящие")
        print("3. Отправить сообщение")
        print("4. Назад")
        
        choice = input("Выберите действие: ").strip()
        
        if choice == '1':
            inbox = user.get_inbox()
            if not inbox:
                print("Входящих нет.")
            else:
                for m in reversed(inbox):
                    print(m.render())
                    print("-" * 30)
        elif choice == '2':
            outbox = user.get_outbox()
            if not outbox:
                print("Исходящих нет.")
            else:
                for m in reversed(outbox):
                    print(m.render())
                    print("-" * 30)
        elif choice == '3':
            target_name = input("Логин получателя: ").strip()
            target = network.find_user_by_username(target_name)
            if target and target.id != user.id:
                text = input("Текст сообщения: ").strip()
                if text:
                    msg = Message(text, user.id, target.id)
                    user.send_message(msg)
                    target.receive_message(msg)
                    network._save_db()
                    print("Сообщение отправлено!")
            else:
                print("Пользователь не найден.")
        elif choice == '4':
            break

def menu_settings(user: User, network: SocialNetwork):
    print_header("НАСТРОЙКИ")
    print("1. Сменить пароль")
    print("2. Назад")
    
    choice = input("Выберите действие: ").strip()
    if choice == '1':
        old_p = input("Старый пароль: ").strip()
        if user.check_password(old_p):
            new_p = input("Новый пароль: ").strip()
            if user.change_password(old_p, new_p):
                network._save_db()
                print("Пароль изменен!")
            else:
                print("Ошибка изменения.")
        else:
            print("Неверный старый пароль.")

# РЕАЛИЗАЦИЯ

if __name__ == "__main__":
    # Инициализация сети
    network = SocialNetwork()
    
    # Запуск интерфейса
    try:
        menu_auth(network)
    except KeyboardInterrupt:
        print("\n[СИСТЕМА] Аварийное завершение работы. Данные сохранены.")
    finally:
        # Гарантированное сохранение при выходе
        network._save_db()
