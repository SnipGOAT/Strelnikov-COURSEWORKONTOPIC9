from flask import Flask, render_template, request, redirect, url_for, session
from models import SocialNetwork, Post, Message
import os

app = Flask(__name__)
app.secret_key = 'supersecretkey'
network = SocialNetwork()

def current_user():
    if 'user_id' in session:
        return network.find_user_by_id(session['user_id'])
    return None

def login_required(view):
    def wrapper(*args, **kwargs):
        if not current_user():
            return redirect(url_for('index'))
        return view(*args, **kwargs)
    wrapper.__name__ = view.__name__
    return wrapper

@app.context_processor
def inject_user():
    user = current_user()
    unread_count = 0
    if user:
        unread_count = user.get_unread_messages_count()
    return dict(user=user, unread_count=unread_count)

# Главная
@app.route('/')
def index():
    user = current_user()
    if not user:
        return render_template('index.html', landing=True)
    all_users = network.get_all_users()
    feed = []
    for u in all_users:
        for post in u.get_posts():
            feed.append({
                'post': post,
                'author': u.username,
                'author_id': u.id,
                'user_liked': user.id in post.liked_by_ids
            })
    feed.sort(key=lambda x: x['post'].timestamp, reverse=True)
    return render_template('index.html', feed=feed)

# Аутентификация
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = network.login(username, password)
        if user:
            session['user_id'] = user.id
            return redirect(url_for('index'))
        return render_template('login.html', error='Неверные логин или пароль')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if not username or not password:
            return render_template('register.html', error='Все поля обязательны')
        new_user = network.register(username, password)
        if new_user:
            session['user_id'] = new_user.id
            return redirect(url_for('index'))
        return render_template('register.html', error='Пользователь уже существует')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# Публикации
@app.route('/posts')
@login_required
def posts_page():
    user = current_user()
    all_users = network.get_all_users()
    feed = []
    for u in all_users:
        for post in u.get_posts():
            feed.append({
                'post': post,
                'author': u.username,
                'author_id': u.id,
                'user_liked': user.id in post.liked_by_ids
            })
    feed.sort(key=lambda x: x['post'].timestamp, reverse=True)
    return render_template('posts.html', feed=feed)

@app.route('/post/create', methods=['POST'])
@login_required
def create_post():
    user = current_user()
    text = request.form.get('text', '').strip()
    if text:
        user.create_post(text)
        network.save_db()
    return redirect(url_for('posts_page'))

@app.route('/post/like/<post_id>', methods=['POST'])
@login_required
def like_post(post_id):
    user = current_user()
    post = network.find_post_global(post_id)
    if post:
        post.toggle_like(user.id)
        network.save_db()
    return redirect(request.referrer or url_for('index'))

@app.route('/post/delete/<post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    user = current_user()
    if user.delete_post(post_id):
        network.save_db()
    return redirect(request.referrer or url_for('posts_page'))

@app.route('/post/<post_id>')
def public_post(post_id):
    post = network.find_post_global(post_id)
    if not post:
        return "Пост не найден", 404
    author = network.find_user_by_id(post.author_id)
    author_name = author.username if author else "Неизвестный"
    return render_template('post_public.html', post=post, author_name=author_name)

# Друзья
@app.route('/friends')
@login_required
def friends_page():
    user = current_user()
    friends = []
    for fid in user.get_friends_ids():
        f = network.find_user_by_id(fid)
        if f:
            friends.append(f)
    return render_template('friends.html', user=user, friends=friends)

@app.route('/friends/add', methods=['POST'])
@login_required
def add_friend():
    user = current_user()
    target_name = request.form.get('username', '').strip()
    target = network.find_user_by_username(target_name)
    if target and target.id != user.id:
        user.add_friend(target.id)
        target.add_friend(user.id)
        network.save_db()
    return redirect(url_for('friends_page'))

@app.route('/friends/remove/<friend_id>', methods=['POST'])
@login_required
def remove_friend(friend_id):
    user = current_user()
    user.remove_friend(friend_id)
    friend = network.find_user_by_id(friend_id)
    if friend:
        friend.remove_friend(user.id)
    network.save_db()
    return redirect(url_for('friends_page'))

# Сообщения
@app.route('/messages')
@login_required
def messages_page():
    user = current_user()
    inbox = user.get_inbox()
    outbox = user.get_outbox()
    def enrich(msgs):
        res = []
        for m in msgs:
            sender = network.find_user_by_id(m.author_id)
            receiver = network.find_user_by_id(m.receiver_id)
            res.append({
                'message': m,
                'sender_name': sender.username if sender else '?',
                'receiver_name': receiver.username if receiver else '?'
            })
        return res
    return render_template('messages.html', user=user,
                           inbox=enrich(inbox), outbox=enrich(outbox))

@app.route('/messages/send', methods=['POST'])
@login_required
def send_message():
    user = current_user()
    target_name = request.form.get('username', '').strip()
    text = request.form.get('text', '').strip()
    target = network.find_user_by_username(target_name)
    if target and target.id != user.id and text:
        msg = Message(text, user.id, target.id)
        user.send_message(msg)
        target.receive_message(msg)
        network.save_db()
    return redirect(url_for('messages_page'))

@app.route('/messages/read/<message_id>', methods=['POST'])
@login_required
def mark_message_read(message_id):
    user = current_user()
    for msg in user.get_inbox():
        if msg.id == message_id and not msg.is_read:
            msg.mark_as_read()
            network.save_db()
            break
    return redirect(url_for('messages_page'))

# Профиль
@app.route('/user/<user_id>')
@login_required
def user_profile(user_id):
    profile = network.find_user_by_id(user_id)
    if not profile:
        return "Пользователь не найден", 404
    return render_template('user_profile.html', profile=profile)

if __name__ == '__main__':
    app.run(debug=False, port=5000)