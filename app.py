from flask import Flask, request, jsonify, session, send_from_directory
from functools import wraps
from models import SocialNetwork, Message

app = Flask(__name__, static_folder='static')
app.secret_key = 'super-secret-change-me'

network = SocialNetwork()


# ---------- Декоратор авторизации ----------
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        uid = session.get('user_id')
        if not uid:
            return jsonify({"error": "Не авторизован"}), 401
        user = network.find_user_by_id(uid)
        if not user:
            session.clear()
            return jsonify({"error": "Сессия недействительна"}), 401
        return f(user, *args, **kwargs)
    return wrapper


def user_brief(u):
    return {"id": u.id, "username": u.username}


# ---------- Статика (фронтенд) ----------
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ---------- Аутентификация ----------
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    if not username or not password:
        return jsonify({"error": "Логин и пароль обязательны"}), 400
    user = network.register(username, password)
    if not user:
        return jsonify({"error": "Имя пользователя занято"}), 409
    return jsonify({"message": "Регистрация успешна", "user": user_brief(user)})


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    user = network.authenticate(data.get('username', ''), data.get('password', ''))
    if not user:
        return jsonify({"error": "Неверные учётные данные"}), 401
    session['user_id'] = user.id
    return jsonify({"message": "Вход выполнен", "user": user_brief(user)})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"message": "Выход выполнен"})


@app.route('/api/me', methods=['GET'])
@login_required
def api_me(user):
    return jsonify({
        "id": user.id,
        "username": user.username,
        "friends_count": len(user.get_friends_ids()),
        "posts_count": len(user.get_posts())
    })


# ---------- Пользователи ----------
@app.route('/api/users', methods=['GET'])
@login_required
def api_users(user):
    return jsonify([user_brief(u) for u in network.all_users() if u.id != user.id])


# ---------- Друзья ----------
@app.route('/api/friends', methods=['GET'])
@login_required
def api_friends(user):
    friends = []
    for fid in user.get_friends_ids():
        f = network.find_user_by_id(fid)
        if f:
            friends.append(user_brief(f))
    return jsonify(friends)


@app.route('/api/friends/add', methods=['POST'])
@login_required
def api_friend_add(user):
    data = request.get_json() or {}
    target = network.find_user_by_username((data.get('username') or '').strip())
    if not target or target.id == user.id:
        return jsonify({"error": "Пользователь не найден"}), 404
    user.add_friend(target.id)
    target.add_friend(user.id)  # взаимная дружба
    network.save_db()
    return jsonify({"message": "Друг добавлен", "friend": user_brief(target)})


@app.route('/api/friends/remove', methods=['POST'])
@login_required
def api_friend_remove(user):
    data = request.get_json() or {}
    fid = data.get('friend_id')
    target = network.find_user_by_id(fid)
    if not target:
        return jsonify({"error": "Не найден"}), 404
    user.remove_friend(fid)
    target.remove_friend(user.id)
    network.save_db()
    return jsonify({"message": "Друг удалён"})


# ---------- Публикации ----------
@app.route('/api/posts', methods=['POST'])
@login_required
def api_create_post(user):
    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({"error": "Пустой текст"}), 400
    post = user.create_post(text)
    network.save_db()
    return jsonify(serialize_post(post, user))


@app.route('/api/posts/my', methods=['GET'])
@login_required
def api_my_posts(user):
    posts = sorted(user.get_posts(), key=lambda p: p.timestamp, reverse=True)
    return jsonify([serialize_post(p, user) for p in posts])


@app.route('/api/feed', methods=['GET'])
@login_required
def api_feed(user):
    all_posts = []
    # свои + друзей
    for p in user.get_posts():
        all_posts.append(p)
    for fid in user.get_friends_ids():
        f = network.find_user_by_id(fid)
        if f:
            all_posts.extend(f.get_posts())
    all_posts.sort(key=lambda p: p.timestamp, reverse=True)
    return jsonify([serialize_post(p, user) for p in all_posts])


@app.route('/api/posts/<post_id>/like', methods=['POST'])
@login_required
def api_like_post(user, post_id):
    # ищем пост среди всех пользователей
    for u in network.all_users():
        p = u.find_post(post_id)
        if p:
            if user.id in p.liked_by:
                p.unlike(user.id)
                action = "unliked"
            else:
                p.like(user.id)
                action = "liked"
            network.save_db()
            return jsonify({"action": action, "likes": p.likes})
    return jsonify({"error": "Пост не найден"}), 404


def serialize_post(post, current_user):
    author = network.find_user_by_id(post.author_id)
    return {
        "id": post.id,
        "text": post.text,
        "timestamp": post.timestamp,
        "likes": post.likes,
        "liked_by_me": current_user.id in post.liked_by,
        "author": user_brief(author) if author else {"id": post.author_id, "username": "Unknown"}
    }


# ---------- Сообщения ----------
@app.route('/api/messages/inbox', methods=['GET'])
@login_required
def api_inbox(user):
    msgs = user.get_inbox(mark_read=True)
    network.save_db()
    return jsonify([serialize_message(m) for m in reversed(msgs)])


@app.route('/api/messages/outbox', methods=['GET'])
@login_required
def api_outbox(user):
    msgs = user.get_outbox()
    return jsonify([serialize_message(m) for m in reversed(msgs)])


@app.route('/api/messages/send', methods=['POST'])
@login_required
def api_send_message(user):
    data = request.get_json() or {}
    target = network.find_user_by_username((data.get('to') or '').strip())
    text = (data.get('text') or '').strip()
    if not target or target.id == user.id:
        return jsonify({"error": "Получатель не найден"}), 404
    if not text:
        return jsonify({"error": "Пустое сообщение"}), 400
    msg = Message(text, user.id, target.id)
    user.send_message(msg)
    target.receive_message(msg)
    network.save_db()
    return jsonify({"message": "Отправлено", "data": serialize_message(msg)})


def serialize_message(m):
    sender = network.find_user_by_id(m.author_id)
    receiver = network.find_user_by_id(m.receiver_id)
    return {
        "id": m.id,
        "text": m.text,
        "timestamp": m.timestamp,
        "is_read": m.is_read,
        "from": user_brief(sender) if sender else {"username": "?"},
        "to": user_brief(receiver) if receiver else {"username": "?"}
    }


# ---------- Настройки ----------
@app.route('/api/settings/password', methods=['POST'])
@login_required
def api_change_password(user):
    data = request.get_json() or {}
    if user.change_password(data.get('old', ''), data.get('new', '')):
        network.save_db()
        return jsonify({"message": "Пароль изменён"})
    return jsonify({"error": "Неверный старый пароль"}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)
