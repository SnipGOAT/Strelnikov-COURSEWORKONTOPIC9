import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.utils import secure_filename
from models import SocialNetwork, Post, Message
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

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

# ---------- Главная ----------
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

# ---------- Аутентификация ----------
@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user = network.login(username, password)
        if user:
            session['user_id'] = user.id
            session.permanent = True
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
            session.permanent = True
            return redirect(url_for('index'))
        return render_template('register.html', error='Пользователь уже существует')
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

# ---------- Публикации ----------
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

# ---------- Друзья ----------
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

# ---------- Сообщения и чат API ----------
@app.route('/messages')
@login_required
def messages_page():
    return render_template('messages.html')

@app.route('/api/upload', methods=['POST'])
@login_required
def api_upload():
    file = request.files.get('attachment')
    if not file or not file.filename:
        return jsonify({'error': 'No file'}), 400
    original_filename = secure_filename(file.filename)
    unique_name = f"{uuid.uuid4().hex}_{original_filename}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
    file.save(file_path)
    attachment_url = f"uploads/{unique_name}"
    return jsonify({'attachment': attachment_url})

@app.route('/api/contacts')
@login_required
def api_contacts():
    user = current_user()
    contacts = user.get_contacts()
    result = []
    for c in contacts:
        contact_user = network.find_user_by_id(c['user_id'])
        if contact_user:
            result.append({
                'user_id': c['user_id'],
                'username': contact_user.username,
                'last_msg_time': c['last_msg_time'],
                'unread': c['unread']
            })
    return jsonify({'contacts': result})

@app.route('/api/messages/<contact_id>')
@login_required
def api_messages(contact_id):
    user = current_user()
    messages = user.get_conversation_with(contact_id, mark_read=True)
    network.save_db()
    contact_user = network.find_user_by_id(contact_id)
    contact_name = contact_user.username if contact_user else "Unknown"
    current_name = user.username
    enriched = []
    for m in messages:
        enriched.append({
            **m,
            'sender_name': contact_name if m['direction'] == 'in' else current_name,
            'receiver_name': current_name if m['direction'] == 'in' else contact_name
        })
    return jsonify({'messages': enriched, 'contact_name': contact_name})

@app.route('/api/send', methods=['POST'])
@login_required
def api_send():
    user = current_user()
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
    contact_id = data.get('contact_id')
    text = data.get('text', '').strip()
    attachment = data.get('attachment')

    if not contact_id:
        return jsonify({'error': 'Missing contact_id'}), 400
    if not text and not attachment:
        return jsonify({'error': 'Empty message'}), 400

    target = network.find_user_by_id(contact_id)
    if not target:
        return jsonify({'error': 'User not found'}), 404

    msg = Message(text, user.id, target.id, attachment)
    user.send_message(msg)
    target.receive_message(msg)
    network.save_db()

    return jsonify({
        'success': True,
        'message': {
            'id': msg.id,
            'text': msg.text,
            'from': user.id,
            'to': target.id,
            'time': msg.timestamp,
            'direction': 'out',
            'is_read': False,
            'attachment': msg.attachment
        }
    })

@app.route('/api/check_new')
@login_required
def api_check_new():
    user = current_user()
    unread_count = user.get_unread_messages_count()
    new_messages = []
    for msg in user.get_inbox():
        if not msg.is_read:
            sender = network.find_user_by_id(msg.author_id)
            new_messages.append({
                'from_id': msg.author_id,
                'from_name': sender.username if sender else '?',
                'text': msg.text[:50],
                'time': msg.timestamp
            })
    return jsonify({'unread_count': unread_count, 'new_messages': new_messages})

# Редактирование и удаление через POST с _method
@app.route('/api/messages/<message_id>/edit', methods=['POST'])
@login_required
def api_edit_message(message_id):
    if request.form.get('_method') != 'PUT':
        return jsonify({'error': 'Method not allowed'}), 405
    user = current_user()
    new_text = request.form.get('text', '').strip()
    if not new_text:
        return jsonify({'error': 'Text cannot be empty'}), 400
    success = network.edit_message_text(message_id, user.id, new_text)
    if success:
        network.save_db()
        return jsonify({'success': True})
    return jsonify({'error': 'Message not found or not yours'}), 403

@app.route('/api/messages/<message_id>/delete', methods=['POST'])
@login_required
def api_delete_message(message_id):
    if request.form.get('_method') != 'DELETE':
        return jsonify({'error': 'Method not allowed'}), 405
    user = current_user()
    scope = request.form.get('scope', 'me')
    success = network.delete_message_for_user(message_id, user.id, scope)
    if success:
        network.save_db()
        return jsonify({'success': True})
    return jsonify({'error': 'Could not delete message'}), 403

# ---------- Профиль ----------
@app.route('/user/<user_id>')
@login_required
def user_profile(user_id):
    profile = network.find_user_by_id(user_id)
    if not profile:
        return "Пользователь не найден", 404
    return render_template('user_profile.html', profile=profile)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
