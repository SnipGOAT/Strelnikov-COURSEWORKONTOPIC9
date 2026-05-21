let currentContactId = null;
let currentContactName = '';
let messagePollTimer = null;
let contactsCache = [];
let uploadedAttachmentUrl = null;

document.addEventListener('DOMContentLoaded', () => {
    loadContacts().then(() => {
        handleUrlParams();
    });

    if ('Notification' in window && Notification.permission !== 'granted' && Notification.permission !== 'denied') {
        Notification.requestPermission();
    }
    startCheckingNewMessages();
    setInterval(loadContacts, 10000);

    const fileLabel = document.getElementById('file-label');
    const fileInput = document.getElementById('attachment-input');
    if (fileLabel && fileInput) {
        fileLabel.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileSelect);
    }

    const removeBtn = document.getElementById('attachment-remove-btn');
    if (removeBtn) {
        removeBtn.addEventListener('click', clearAttachment);
    }

    const mobileBackBtn = document.getElementById('mobileBackBtn');
    if (mobileBackBtn) {
        mobileBackBtn.addEventListener('click', closeChatMobile);
    }
});

function isMobile() {
    return window.innerWidth <= 768;
}

function openChat(contactId, contactName) {
    currentContactId = contactId;
    currentContactName = contactName;
    document.getElementById('chatHeaderTitle').textContent = `Чат с ${contactName}`;
    document.getElementById('chat-input-area').style.display = 'flex';
    clearAttachment();
    loadMessages(contactId);
    if (isMobile()) {
        document.getElementById('chatWrapper').classList.add('chat-active');
    }
    renderContacts(contactsCache);
}

function closeChatMobile() {
    document.getElementById('chatWrapper').classList.remove('chat-active');
}

async function loadContacts() {
    try {
        const resp = await fetch('/api/contacts');
        const data = await resp.json();
        contactsCache = data.contacts;
        renderContacts(contactsCache);
    } catch(e) {
        console.error('Ошибка загрузки контактов', e);
    }
}

function renderContacts(contacts) {
    const list = document.getElementById('contacts-list');
    if (!list) return;
    if (contacts.length === 0 && !currentContactId) {
        list.innerHTML = '<div class="no-contacts">Нет чатов</div>';
        return;
    }
    if (currentContactId && !contacts.some(c => c.user_id === currentContactId)) {
        contacts = [...contacts, {
            user_id: currentContactId,
            username: currentContactName,
            last_msg_time: '',
            unread: 0
        }];
    }
    list.innerHTML = contacts.map(c => {
        const unreadBadge = c.unread > 0 ? `<span class="unread-badge">${c.unread}</span>` : '';
        const activeClass = (currentContactId === c.user_id) ? 'active' : '';
        return `
            <div class="contact-item ${activeClass}" data-contact-id="${c.user_id}" data-contact-name="${c.username}">
                <div class="contact-avatar">${c.username[0].toUpperCase()}</div>
                <div class="contact-info">
                    <div class="contact-name">${c.username} ${unreadBadge}</div>
                    <div class="contact-time">${formatTime(c.last_msg_time)}</div>
                </div>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.contact-item').forEach(item => {
        item.addEventListener('click', () => {
            const id = item.dataset.contactId;
            const name = item.dataset.contactName;
            openChat(id, name);
        });
    });
}

async function loadMessages(contactId) {
    try {
        const resp = await fetch(`/api/messages/${contactId}`);
        const data = await resp.json();
        renderMessages(data.messages);
        scrollToBottom();
    } catch(e) {
        console.error('Ошибка загрузки сообщений', e);
    }
}

function renderMessages(messages) {
    const box = document.getElementById('messages-box');
    if (messages.length === 0) {
        box.innerHTML = '<div class="no-messages">Нет сообщений</div>';
        return;
    }
    box.innerHTML = messages.map(m => {
        const side = m.direction === 'out' ? 'outgoing' : 'incoming';
        const time = m.time ? m.time.split(' ')[1]?.substring(0,5) : '';
        const isOutgoing = m.direction === 'out';
        let content = '';
        if (m.text) {
            content += `<div class="bubble-text">${escapeHtml(m.text)}${m.edited ? ' <span class="edited-label">(изм.)</span>' : ''}</div>`;
        }
        if (m.attachment) {
            const fileUrl = `/static/${m.attachment}`;
            const isImage = /\.(gif|jpe?g|png|webp|bmp)$/i.test(m.attachment);
            if (isImage) {
                content += `<div class="bubble-attachment"><img src="${fileUrl}" alt="image" class="chat-image"></div>`;
            } else {
                const fileName = m.attachment.split('/').pop();
                content += `<div class="bubble-attachment"><a href="${fileUrl}" target="_blank" class="file-link">📎 ${fileName}</a></div>`;
            }
        }
        const controls = isOutgoing ? `
            <div class="message-controls">
                <button class="msg-edit-btn" data-msg-id="${m.id}" data-text="${escapeHtml(m.text || '')}">✎</button>
                <button class="msg-delete-btn" data-msg-id="${m.id}">🗑</button>
            </div>` : '';
        return `
            <div class="message-bubble ${side}">
                ${controls}
                ${content}
                <div class="bubble-time">${time}</div>
            </div>
        `;
    }).join('');

    document.querySelectorAll('.msg-edit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const msgId = btn.dataset.msgId;
            const currentText = btn.dataset.text;
            startEditMessage(msgId, currentText);
        });
    });
    document.querySelectorAll('.msg-delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const msgId = btn.dataset.msgId;
            showDeleteMenu(btn, msgId);
        });
    });
}

function showDeleteMenu(anchor, msgId) {
    const existing = document.querySelector('.delete-menu');
    if (existing) existing.remove();
    const menu = document.createElement('div');
    menu.className = 'delete-menu';
    menu.innerHTML = `
        <button data-action="me">Удалить у меня</button>
        <button data-action="all">Удалить для всех</button>
    `;
    anchor.parentNode.appendChild(menu);
    const rect = anchor.getBoundingClientRect();
    menu.style.top = rect.top + 'px';
    menu.style.left = (rect.right + 10) + 'px';
    menu.querySelectorAll('button').forEach(b => {
        b.addEventListener('click', () => {
            const scope = b.dataset.action;
            deleteMessage(msgId, scope);
            menu.remove();
        });
    });
    setTimeout(() => menu.remove(), 5000);
}

async function deleteMessage(msgId, scope) {
    // Используем FormData, чтобы передать _method=DELETE и scope
    const formData = new FormData();
    formData.append('_method', 'DELETE');
    formData.append('scope', scope);

    try {
        const resp = await fetch(`/api/messages/${msgId}/delete`, {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (data.success) {
            loadMessages(currentContactId);
            loadContacts();
        } else {
            alert(data.error || 'Не удалось удалить сообщение');
        }
    } catch(e) {
        console.error(e);
        alert('Ошибка сети');
    }
}

function startEditMessage(msgId, oldText) {
    const newText = prompt('Введите новый текст:', oldText);
    if (newText !== null && newText.trim() !== '') {
        editMessage(msgId, newText.trim());
    }
}

async function editMessage(msgId, newText) {
    const formData = new FormData();
    formData.append('_method', 'PUT');
    formData.append('text', newText);

    try {
        const resp = await fetch(`/api/messages/${msgId}/edit`, {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        if (data.success) {
            loadMessages(currentContactId);
        } else {
            alert(data.error || 'Не удалось отредактировать сообщение');
        }
    } catch(e) {
        console.error(e);
    }
}

// --- работа с файлом ---
function handleFileSelect() {
    const fileInput = document.getElementById('attachment-input');
    const file = fileInput.files[0];
    if (!file) {
        clearAttachment();
        return;
    }
    fileInput.value = '';
    showLocalPreview(file);
    uploadFile(file);
}

function showLocalPreview(file) {
    const previewArea = document.getElementById('attachment-preview');
    const previewImg = document.getElementById('attachment-preview-img');
    const previewName = document.getElementById('attachment-preview-name');

    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            previewImg.src = e.target.result;
            previewImg.style.display = 'block';
        };
        reader.readAsDataURL(file);
        previewName.textContent = 'Загрузка...';
    } else {
        previewImg.style.display = 'none';
        previewName.textContent = `${file.name} (загрузка...)`;
    }
    previewArea.style.display = 'flex';
}

async function uploadFile(file) {
    const formData = new FormData();
    formData.append('attachment', file);
    try {
        const resp = await fetch('/api/upload', { method: 'POST', body: formData });
        if (!resp.ok) throw new Error('Ошибка загрузки');
        const data = await resp.json();
        uploadedAttachmentUrl = data.attachment;
        const previewImg = document.getElementById('attachment-preview-img');
        const previewName = document.getElementById('attachment-preview-name');
        if (file.type.startsWith('image/')) {
            previewImg.src = `/static/${data.attachment}`;
            previewName.textContent = '';
        } else {
            previewImg.style.display = 'none';
            previewName.textContent = file.name;
        }
    } catch(e) {
        console.error(e);
        const previewName = document.getElementById('attachment-preview-name');
        previewName.textContent = 'Ошибка загрузки!';
        uploadedAttachmentUrl = null;
    }
}

function clearAttachment() {
    uploadedAttachmentUrl = null;
    const fileInput = document.getElementById('attachment-input');
    if (fileInput) fileInput.value = '';
    const previewArea = document.getElementById('attachment-preview');
    if (previewArea) previewArea.style.display = 'none';
    const previewImg = document.getElementById('attachment-preview-img');
    if (previewImg) previewImg.src = '';
    const previewName = document.getElementById('attachment-preview-name');
    if (previewName) previewName.textContent = '';
}

// --- отправка сообщения ---
document.getElementById('send-button')?.addEventListener('click', sendMessage);
document.getElementById('message-input')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

async function sendMessage() {
    const input = document.getElementById('message-input');
    const text = input.value.trim();
    if (!text && !uploadedAttachmentUrl) return;
    if (!currentContactId) return;

    const sendBtn = document.getElementById('send-button');
    sendBtn.disabled = true;

    const payload = {
        contact_id: currentContactId,
        text: text,
        attachment: uploadedAttachmentUrl
    };

    try {
        const resp = await fetch('/api/send', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.success) {
            input.value = '';
            clearAttachment();
            const box = document.getElementById('messages-box');
            const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
            let content = '';
            if (text) content += `<div class="bubble-text">${escapeHtml(text)}</div>`;
            if (payload.attachment) {
                const fileUrl = `/static/${payload.attachment}`;
                const isImage = /\.(gif|jpe?g|png|webp|bmp)$/i.test(payload.attachment);
                if (isImage) {
                    content += `<div class="bubble-attachment"><img src="${fileUrl}" alt="preview" class="chat-image"></div>`;
                } else {
                    const fileName = payload.attachment.split('/').pop();
                    content += `<div class="bubble-attachment"><a href="${fileUrl}" target="_blank" class="file-link">📎 ${fileName}</a></div>`;
                }
            }
            box.insertAdjacentHTML('beforeend', `
                <div class="message-bubble outgoing">
                    ${content}
                    <div class="bubble-time">${time}</div>
                </div>
            `);
            scrollToBottom();
            loadContacts();
        } else {
            alert('Ошибка отправки');
        }
    } catch(e) {
        console.error(e);
    } finally {
        sendBtn.disabled = false;
    }
}

// Проверка новых сообщений
async function checkNewMessages() {
    try {
        const resp = await fetch('/api/check_new');
        const data = await resp.json();
        const badge = document.querySelector('.nav-right .badge');
        if (badge) {
            if (data.unread_count > 0) {
                badge.textContent = data.unread_count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
        for (let msg of data.new_messages) {
            if (document.hidden || (currentContactId !== msg.from_id)) {
                showNotification(msg.from_name, msg.text);
            }
        }
        if (currentContactId && data.new_messages.some(m => m.from_id === currentContactId)) {
            loadMessages(currentContactId);
        }
    } catch(e) {
        console.error(e);
    }
}

function startCheckingNewMessages() {
    checkNewMessages();
    messagePollTimer = setInterval(checkNewMessages, 5000);
}

function showNotification(title, body) {
    if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(title, {body: body, icon: '/static/icon-192.png'});
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    if (!timestamp) return '';
    const t = timestamp.split(' ')[1];
    return t ? t.substring(0,5) : '';
}

function handleUrlParams() {
    const params = new URLSearchParams(window.location.search);
    const contactId = params.get('contact');
    if (contactId) {
        fetch(`/api/messages/${contactId}`)
            .then(resp => resp.json())
            .then(data => {
                openChat(contactId, data.contact_name);
            })
            .catch(err => console.error('Не удалось открыть чат', err));
    }
}

function scrollToBottom() {
    const box = document.getElementById('messages-box');
    box.scrollTop = box.scrollHeight;
}
