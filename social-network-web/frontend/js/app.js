// ==============================================================================
// КОНФИГУРАЦИЯ
// ==============================================================================

const API_URL = window.API_URL || 
                'https://social-network-backend.onrender.com/api';

// ==============================================================================
// АВТОРИЗАЦИЯ
// ==============================================================================

function getToken() {
    return localStorage.getItem('user_token');
}

function setToken(token) {
    localStorage.setItem('user_token', token);
}

function removeToken() {
    localStorage.removeItem('user_token');
}

function isAuthenticated() {
    return !!getToken();
}

// ==============================================================================
// API ЗАПРОСЫ
// ==============================================================================

async function apiRequest(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
        }
    };

    const token = getToken();
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    if (data) {
        options.body = JSON.stringify(data);
    }

    const response = await fetch(`${API_URL}${endpoint}`, options);
    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.detail || 'Ошибка запроса');
    }

    return result;
}

// ==============================================================================
// РЕГИСТРАЦИЯ И ВХОД
// ==============================================================================

async function register(username, password) {
    try {
        const data = await apiRequest('/register', 'POST', { username, password });
        setToken(data.id);
        window.location.href = 'dashboard.html';
    } catch (error) {
        showError(error.message);
    }
}

async function login(username, password) {
    try {
        const data = await apiRequest('/login', 'POST', { username, password });
        setToken(data.id);
        window.location.href = 'dashboard.html';
    } catch (error) {
        showError(error.message);
    }
}

async function logout() {
    try {
        await apiRequest('/logout', 'POST');
    } catch (error) {
        console.error(error);
    }
    removeToken();
    window.location.href = 'index.html';
}

// ==============================================================================
// ПРОФИЛЬ
// ==============================================================================

async function loadProfile() {
    try {
        const data = await apiRequest('/profile');
        document.getElementById('user-name').textContent = data.username;
        document.getElementById('profile-id').textContent = data.id;
        document.getElementById('profile-username').textContent = data.username;
    } catch (error) {
        console.error(error);
        window.location.href = 'login.html';
    }
}

async function changePassword(oldPassword, newPassword) {
    try {
        await apiRequest('/profile/password', 'PUT', {
            old_password: oldPassword,
            new_password: newPassword
        });
        showSuccess('Пароль изменен!');
    } catch (error) {
        showError(error.message);
    }
}

// ==============================================================================
// ДРУЗЬЯ
// ==============================================================================

async function loadFriends() {
    try {
        const data = await apiRequest('/friends');
        const list = document.getElementById('friends-list');
        list.innerHTML = '';
        
        if (data.friends.length === 0) {
            list.innerHTML = '<p>Список друзей пуст</p>';
            return;
        }

        data.friends.forEach(friend => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <h3>${friend.username}</h3>
                <p>ID: ${friend.id}</p>
                <button onclick="removeFriend('${friend.id}')" class="btn btn-secondary">Удалить</button>
            `;
            list.appendChild(card);
        });

        document.getElementById('profile-friends-count').textContent = data.friends.length;
    } catch (error) {
        console.error(error);
    }
}

async function addFriend() {
    const username = document.getElementById('friend-username').value;
    if (!username) return;

    try {
        await apiRequest(`/friends/${username}`, 'POST');
        showSuccess('Друг добавлен!');
        document.getElementById('friend-username').value = '';
        loadFriends();
    } catch (error) {
        showError(error.message);
    }
}

async function removeFriend(userId) {
    try {
        await apiRequest(`/friends/${userId}`, 'DELETE');
        showSuccess('Друг удален!');
        loadFriends();
    } catch (error) {
        showError(error.message);
    }
}

// ==============================================================================
// ПУБЛИКАЦИИ
// ==============================================================================

async function loadPosts() {
    try {
        const data = await apiRequest('/posts');
        const list = document.getElementById('posts-list');
        list.innerHTML = '';

        if (data.posts.length === 0) {
            list.innerHTML = '<p class="empty-message">Публикаций нет</p>';
            return;
        }

        data.posts.reverse().forEach(post => {
            // Проверяем можно ли редактировать (30 минут)
            const postTime = new Date(post.timestamp.replace(' ', 'T'));
            const now = new Date();
            const minutesDiff = (now - postTime) / 1000 / 60;
            const canEdit = minutesDiff <= 30;
            const timeLeft = Math.round(30 - minutesDiff);

            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="post-header">
                    <div class="avatar">${post.author_id.slice(0, 2).toUpperCase()}</div>
                    <div>
                        <div class="post-author">Вы</div>
                        <div class="timestamp">${post.timestamp}</div>
                    </div>
                </div>
                <p class="post-content" id="post-text-${post.id}">${post.text}</p>
                <div class="post-footer">
                    <span>❤️ ${post.likes}</span>
                    ${canEdit ? `<span class="edit-time-warning">✏️ можно редактировать ещё ${timeLeft} мин</span>` : ''}
                </div>
                <div class="post-actions">
                    <button onclick="editPost('${post.id}', ${JSON.stringify(post.text).replace(/'/g, "\\'")})" 
                            class="action-btn edit" 
                            ${!canEdit ? 'disabled title="Время редактирования истекло"' : ''}>
                        ✏️ Изменить
                    </button>
                    <button onclick="deletePost('${post.id}')" class="action-btn delete">
                        🗑️ Удалить
                    </button>
                </div>
            `;
            list.appendChild(card);
        });

        document.getElementById('profile-posts-count').textContent = data.posts.length;
    } catch (error) {
        console.error(error);
        list.innerHTML = '<p class="error">Ошибка загрузки публикаций</p>';
    }
}

async function createPost() {
    const text = document.getElementById('post-text').value;
    if (!text) return;

    try {
        await apiRequest('/posts', 'POST', { text });
        showSuccess('Опубликовано!');
        document.getElementById('post-text').value = '';
        loadPosts();
    } catch (error) {
        showError(error.message);
    }
}

async function loadFeed() {
    try {
        const data = await apiRequest('/feed');
        const list = document.getElementById('feed-list');
        list.innerHTML = '';
        const currentUserId = getToken();  // Получаем ID текущего пользователя

        if (data.feed.length === 0) {
            list.innerHTML = '<p class="empty-message">Лента пуста</p>';
            return;
        }

        data.feed.forEach(post => {
            const isOwnPost = post.author_id === currentUserId;
            
            // Проверяем можно ли редактировать (только для своих постов)
            const postTime = new Date(post.timestamp.replace(' ', 'T'));
            const now = new Date();
            const minutesDiff = (now - postTime) / 1000 / 60;
            const canEdit = isOwnPost && minutesDiff <= 30;
            const timeLeft = Math.round(30 - minutesDiff);

            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <div class="post-header">
                    <div class="avatar">${post.author_name?.slice(0, 2).toUpperCase() || '??'}</div>
                    <div>
                        <div class="post-author">${post.author_name || 'Unknown'}</div>
                        <div class="timestamp">${post.timestamp}</div>
                    </div>
                </div>
                <p class="post-content">${post.text}</p>
                <div class="post-footer">
                    <span>❤️ ${post.likes}</span>
                    ${canEdit ? `<span class="edit-time-warning">✏️ можно редактировать ещё ${timeLeft} мин</span>` : ''}
                </div>
                ${isOwnPost ? `
                <div class="post-actions">
                    <button onclick="editPost('${post.id}', ${JSON.stringify(post.text).replace(/'/g, "\\'")})" 
                            class="action-btn edit"
                            ${!canEdit ? 'disabled title="Время редактирования истекло"' : ''}>
                        ✏️ Изменить
                    </button>
                    <button onclick="deletePost('${post.id}')" class="action-btn delete">
                        🗑️ Удалить
                    </button>
                </div>
                ` : ''}
            `;
            list.appendChild(card);
        });
    } catch (error) {
        console.error(error);
        list.innerHTML = '<p class="error">Ошибка загрузки ленты</p>';
    }
}


// ==============================================================================
// РЕДАКТИРОВАНИЕ И УДАЛЕНИЕ ПУБЛИКАЦИЙ
// ==============================================================================

async function editPost(postId, currentText) {
    // Создаём модальное окно для редактирования
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <h3>Редактировать публикацию</h3>
            <textarea id="edit-text" rows="4">${currentText}</textarea>
            <div class="modal-buttons">
                <button onclick="savePostEdit('${postId}')" class="btn btn-primary">Сохранить</button>
                <button onclick="closeModal(this)" class="btn btn-secondary">Отмена</button>
            </div>
            <p class="modal-hint">⏱ Редактирование доступно в течение 30 минут</p>
        </div>
    `;
    document.body.appendChild(modal);
}

async function savePostEdit(postId) {
    const newText = document.getElementById('edit-text').value;
    if (!newText) {
        showError('Текст не может быть пустым');
        return;
    }

    try {
        await apiRequest(`/posts/${postId}`, 'PUT', { text: newText });
        showSuccess('Публикация обновлена!');
        closeModal();
        loadPosts();  // Обновляем список
        loadFeed();   // Обновляем ленту
    } catch (error) {
        if (error.message.includes('30 минут')) {
            showError('Время для редактирования истекло (30 минут)');
        } else {
            showError(error.message);
        }
    }
}

async function deletePost(postId) {
    if (!confirm('Вы уверены что хотите удалить эту публикацию?')) {
        return;
    }

    try {
        await apiRequest(`/posts/${postId}`, 'DELETE');
        showSuccess('Публикация удалена!');
        loadPosts();  // Обновляем список
        loadFeed();   // Обновляем ленту
    } catch (error) {
        showError(error.message);
    }
}

function closeModal(element = null) {
    const modal = document.querySelector('.modal');
    if (modal) {
        modal.remove();
    }
}

// Закрытие модального окна по клику вне его
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        closeModal();
    }
});


// ==============================================================================
// СООБЩЕНИЯ
// ==============================================================================

async function sendMessage() {
    const receiverId = document.getElementById('message-receiver').value;
    const text = document.getElementById('message-text').value;

    if (!receiverId || !text) return;

    try {
        await apiRequest('/messages', 'POST', {
            receiver_id: receiverId,
            text: text
        });
        showSuccess('Сообщение отправлено!');
        document.getElementById('message-receiver').value = '';
        document.getElementById('message-text').value = '';
    } catch (error) {
        showError(error.message);
    }
}

async function showInbox() {
    try {
        const data = await apiRequest('/messages/inbox');
        const list = document.getElementById('messages-list');
        list.innerHTML = '<h3>Входящие</h3>';

        if (data.messages.length === 0) {
            list.innerHTML += '<p>Входящих нет</p>';
            return;
        }

        data.messages.reverse().forEach(msg => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <p><strong>От:</strong> ${msg.author_id}</p>
                <p>${msg.text}</p>
                <p class="timestamp">${msg.timestamp}</p>
                <p>${msg.is_read ? '✅ Прочитано' : '📬 Новое'}</p>
            `;
            list.appendChild(card);
        });
    } catch (error) {
        console.error(error);
    }
}

async function showOutbox() {
    try {
        const data = await apiRequest('/messages/outbox');
        const list = document.getElementById('messages-list');
        list.innerHTML = '<h3>Исходящие</h3>';

        if (data.messages.length === 0) {
            list.innerHTML += '<p>Исходящих нет</p>';
            return;
        }

        data.messages.reverse().forEach(msg => {
            const card = document.createElement('div');
            card.className = 'card';
            card.innerHTML = `
                <p><strong>Кому:</strong> ${msg.receiver_id}</p>
                <p>${msg.text}</p>
                <p class="timestamp">${msg.timestamp}</p>
            `;
            list.appendChild(card);
        });
    } catch (error) {
        console.error(error);
    }
}

// ==============================================================================
// ТАБЫ
// ==============================================================================

function setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;

            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            document.getElementById(tabId).classList.add('active');

            // Загрузка данных для таба
            if (tabId === 'friends') loadFriends();
            if (tabId === 'posts') loadPosts();
            if (tabId === 'feed') loadFeed();
            if (tabId === 'messages') showInbox();
        });
    });
}

// ==============================================================================
// УТИЛИТЫ
// ==============================================================================

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        setTimeout(() => errorDiv.style.display = 'none', 5000);
    } else {
        alert('Ошибка: ' + message);
    }
}

function showSuccess(message) {
    alert(message);
}

// ==============================================================================
// ИНИЦИАЛИЗАЦИЯ
// ==============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Проверка авторизации
    const isAuthPage = window.location.pathname.includes('login.html') || 
                       window.location.pathname.includes('register.html');
    const isDashboard = window.location.pathname.includes('dashboard.html');

    if (isAuthenticated()) {
        if (isAuthPage) {
            window.location.href = 'dashboard.html';
        } else if (isDashboard) {
            loadProfile();
            setupTabs();
        }
    } else {
        if (isDashboard) {
            window.location.href = 'login.html';
        }
    }

    // Обработчики форм
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            login(username, password);
        });
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            const confirm = document.getElementById('confirm-password').value;

            if (password !== confirm) {
                showError('Пароли не совпадают');
                return;
            }

            register(username, password);
        });
    }

    const passwordForm = document.getElementById('password-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const oldPass = document.getElementById('old-password').value;
            const newPass = document.getElementById('new-password').value;
            changePassword(oldPass, newPass);
        });
    }
});
