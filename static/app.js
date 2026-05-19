const API = '/api';
let currentUser = null;

// ---------- Утилиты ----------
async function api(path, method = 'GET', body = null) {
  const opts = { method, headers: { 'Content-Type': 'application/json' }, credentials: 'same-origin' };
  if (body) opts.body = JSON.stringify(body);
  const r = await fetch(API + path, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || 'Ошибка');
  return data;
}

function showMessage(text, type = 'error') {
  const el = document.getElementById('auth-message');
  el.textContent = text;
  el.className = 'message ' + type;
  setTimeout(() => el.textContent = '', 4000);
}

function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ---------- Аутентификация ----------
document.querySelectorAll('.tab').forEach(t => {
  t.onclick = () => {
    document.querySelectorAll('.tab').forEach(x => x.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(x => x.classList.remove('active'));
    t.classList.add('active');
    document.getElementById(t.dataset.tab + '-form').classList.add('active');
  };
});

async function doLogin() {
  try {
    const data = await api('/login', 'POST', {
      username: document.getElementById('login-username').value,
      password: document.getElementById('login-password').value
    });
    currentUser = data.user;
    enterApp();
  } catch (e) { showMessage(e.message); }
}

async function doRegister() {
  try {
    await api('/register', 'POST', {
      username: document.getElementById('reg-username').value,
      password: document.getElementById('reg-password').value
    });
    showMessage('Регистрация успешна! Войдите.', 'success');
  } catch (e) { showMessage(e.message); }
}

async function doLogout() {
  await api('/logout', 'POST');
  currentUser = null;
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app-screen').classList.add('hidden');
}

function enterApp() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app-screen').classList.remove('hidden');
  document.getElementById('current-username').textContent = '👤 ' + currentUser.username;
  loadPage('feed');
}

// ---------- Навигация ----------
document.querySelectorAll('.nav-btn').forEach(b => {
  b.onclick = () => {
    document.querySelectorAll('.nav-btn').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    loadPage(b.dataset.page);
  };
});

async function loadPage(page) {
  const content = document.getElementById('content');
  content.innerHTML = '<div class="empty">Загрузка...</div>';
  try {
    if (page === 'feed') await renderFeed();
    else if (page === 'my-posts') await renderMyPosts();
    else if (page === 'friends') await renderFriends();
    else if (page === 'messages') await renderMessages();
    else if (page === 'profile') await renderProfile();
  } catch (e) {
    content.innerHTML = `<div class="empty">Ошибка: ${e.message}</div>`;
  }
}

// ---------- Лента ----------
async function renderFeed() {
  const posts = await api('/feed');
  const content = document.getElementById('content');
  content.innerHTML = `
    <div class="post composer">
      <textarea id="new-post" placeholder="Что у вас нового?"></textarea>
      <button onclick="createPost()">Опубликовать</button>
    </div>
    <h3 class="section-title">Лента (вы и друзья)</h3>
    <div id="feed-list">${renderPosts(posts)}</div>
  `;
}

function renderPosts(posts) {
  if (!posts.length) return '<div class="empty">Постов нет</div>';
  return posts.map(p => `
    <div class="post">
      <div class="post-header">
        <span class="post-author">${escapeHtml(p.author.username)}</span>
        <span class="post-time">${p.timestamp}</span>
      </div>
      <div class="post-text">${escapeHtml(p.text)}</div>
      <div class="post-actions">
        <button class="like-btn ${p.liked_by_me ? 'liked' : ''}" onclick="toggleLike('${p.id}', this)">
          ❤️ <span>${p.likes}</span>
        </button>
      </div>
    </div>
  `).join('');
}

async function createPost() {
  const ta = document.getElementById('new-post');
  if (!ta.value.trim()) return;
  try {
    await api('/posts', 'POST', { text: ta.value });
    ta.value = '';
    renderFeed();
  } catch (e) { alert(e.message); }
}

async function toggleLike(postId, btn) {
  try {
    const r = await api(`/posts/${postId}/like`, 'POST');
    btn.querySelector('span').textContent = r.likes;
    btn.classList.toggle('liked', r.action === 'liked');
  } catch (e) { alert(e.message); }
}

// ---------- Мои посты ----------
async function renderMyPosts() {
  const posts = await api('/posts/my');
  document.getElementById('content').innerHTML = `
    <h3 class="section-title">Мои публикации</h3>
    ${renderPosts(posts)}
  `;
}

// ---------- Друзья ----------
async function renderFriends() {
  const friends = await api('/friends');
  const users = await api('/users');
  const friendIds = new Set(friends.map(f => f.id));
  const others = users.filter(u => !friendIds.has(u.id));

  document.getElementById('content').innerHTML = `
    <h3 class="section-title">Мои друзья (${friends.length})</h3>
    <div>${friends.length ? friends.map(f => `
      <div class="friend-item">
        <span>👤 ${escapeHtml(f.username)}</span>
        <button class="danger" onclick="removeFriend('${f.id}')">Удалить</button>
      </div>
    `).join('') : '<div class="empty">Нет друзей</div>'}</div>

    <h3 class="section-title">Другие пользователи</h3>
    <div>${others.length ? others.map(u => `
      <div class="user-item">
        <span>👤 ${escapeHtml(u.username)}</span>
        <button onclick="addFriend('${escapeHtml(u.username)}')">Добавить</button>
      </div>
    `).join('') : '<div class="empty">Никого нет</div>'}</div>
  `;
}

async function addFriend(username) {
  try { await api('/friends/add', 'POST', { username }); renderFriends(); }
  catch (e) { alert(e.message); }
}

async function removeFriend(id) {
  try { await api('/friends/remove', 'POST', { friend_id: id }); renderFriends(); }
  catch (e) { alert(e.message); }
}

// ---------- Сообщения ----------
async function renderMessages() {
  const inbox = await api('/messages/inbox');
  const outbox = await api('/messages/outbox');

  document.getElementById('content').innerHTML = `
    <div class="post composer">
      <input id="msg-to" placeholder="Логин получателя">
      <textarea id="msg-text" placeholder="Текст сообщения"></textarea>
      <button onclick="sendMsg()">Отправить</button>
    </div>

    <h3 class="section-title">Входящие</h3>
    <div>${inbox.length ? inbox.map(m => `
      <div class="msg-item ${m.is_read ? '' : 'unread'}">
        <div class="msg-header">От: <b>${escapeHtml(m.from.username)}</b> · ${m.timestamp}</div>
        <div>${escapeHtml(m.text)}</div>
      </div>
    `).join('') : '<div class="empty">Нет сообщений</div>'}</div>

    <h3 class="section-title">Исходящие</h3>
    <div>${outbox.length ? outbox.map(m => `
      <div class="msg-item">
        <div class="msg-header">Кому: <b>${escapeHtml(m.to.username)}</b> · ${m.timestamp}</div>
        <div>${escapeHtml(m.text)}</div>
      </div>
    `).join('') : '<div class="empty">Нет сообщений</div>'}</div>
  `;
}

async function sendMsg() {
  const to = document.getElementById('msg-to').value.trim();
  const text = document.getElementById('msg-text').value.trim();
  if (!to || !text) return;
  try {
    await api('/messages/send', 'POST', { to, text });
    renderMessages();
  } catch (e) { alert(e.message); }
}

// ---------- Профиль ----------
async function renderProfile() {
  const me = await api('/me');
  document.getElementById('content').innerHTML = `
    <div class="post">
      <h3>👤 ${escapeHtml(me.username)}</h3>
      <p style="margin-top:10px;color:#65676b;">ID: ${me.id}</p>
      <p>Друзей: <b>${me.friends_count}</b></p>
      <p>Публикаций: <b>${me.posts_count}</b></p>
    </div>
    <div class="post composer">
      <h3 style="margin-bottom:12px;">Сменить пароль</h3>
      <input id="old-pwd" type="password" placeholder="Старый пароль">
      <input id="new-pwd" type="password" placeholder="Новый пароль">
      <button onclick="changePassword()">Сохранить</button>
    </div>
  `;
}

async function changePassword() {
  const old = document.getElementById('old-pwd').value;
  const newp = document.getElementById('new-pwd').value;
  try {
    const r = await api('/settings/password', 'POST', { old, new: newp });
    alert(r.message);
  } catch (e) { alert(e.message); }
}

// ---------- Автологин при загрузке ----------
(async () => {
  try {
    const me = await api('/me');
    currentUser = { id: me.id, username: me.username };
    enterApp();
  } catch { /* не залогинен */ }
})();
