// ============================================================
// WhatsApp Clone - Chat UI Logic
// ============================================================

const token = localStorage.getItem('token');
const me = JSON.parse(localStorage.getItem('user') || 'null');

if (!token || !me) {
      window.location.href = '/login';
}

const DEFAULT_AVATAR = '/static/img/default-avatar.svg';

const state = {
      chats: [],
      users: [],
      currentChat: null,
      ws: null,
      typingTimer: null,
      activeTab: 'chats',
};

// ---------- Helpers ----------
function authHeaders(extra = {}) {
      return { ...extra, 'Authorization': `Bearer ${token}` };
}

async function api(path, opts = {}) {
      const res = await fetch(path, { ...opts, headers: authHeaders(opts.headers || {}) });
      if (res.status === 401) { logout(); throw new Error('unauthorized'); }
      if (res.status === 204) return null;
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(extractError(data, `خطای ${res.status}`));
      return data;
}

function timeStr(iso) {
      if (!iso) return '';
      const d = new Date(iso);
      return d.toLocaleTimeString('fa-IR', { hour: '2-digit', minute: '2-digit' });
}

function escapeHtml(s) {
      return String(s ?? '').replace(/[&<>"']/g, c => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[c]));
}

function extractError(data, fallback = 'خطای نامشخص') {
      if (!data) return fallback;
      const d = data.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d)) {
            return d.map(e => {
                  const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : '';
                  return `${field ? field + ': ' : ''}${e.msg || JSON.stringify(e)}`;
            }).join(' | ');
      }
      if (typeof d === 'object') return JSON.stringify(d);
      return fallback;
}

// پیش‌نمایش عکس
window.__previewImage = function (url) {
      const overlay = document.createElement('div');
      overlay.className = 'img-preview-overlay';
      overlay.innerHTML = `<img src="${url}">`;
      overlay.addEventListener('click', () => overlay.remove());
      document.body.appendChild(overlay);
};

// ---------- Profile ----------
async function loadMe() {
      try {
            const u = await api('/auth/me');
            document.getElementById('myName').textContent = u.name || '';
            document.getElementById('myBio').textContent = u.bio || '';
            document.getElementById('myAvatar').src = u.avatar || DEFAULT_AVATAR;
            localStorage.setItem('user', JSON.stringify(u));
      } catch (e) { console.error(e); }
}

// ---------- Chats ----------
async function loadChats() {
      try {
            state.chats = await api('/chats');
            if (state.activeTab === 'chats') renderChats();
      } catch (e) { console.error(e); }
}

function chatDisplayInfo(c) {
      const isPrivate = c.type === 'private';
      const other = isPrivate ? c.members.find(m => m.user_id !== me.id) : null;
      const title = isPrivate ? (other?.user?.name || 'کاربر') : (c.name || 'بدون نام');
      const avatar = isPrivate
            ? (other?.user?.avatar || DEFAULT_AVATAR)
            : (c.avatar || DEFAULT_AVATAR);
      let last = 'بدون پیام';
      if (c.last_message) {
            const lm = c.last_message;
            if (lm.is_deleted) last = 'پیام حذف شد';
            else if (lm.type === 'system') last = lm.content || '';
            else if (lm.type === 'image') last = '📷 عکس';
            else if (lm.type === 'video') last = '🎬 فیلم';
            else if (lm.type === 'audio') last = '🎤 صدا';
            else if (lm.type === 'file') last = '📎 فایل';
            else last = lm.content || '';
      }
      return { title, avatar, last, isPrivate, other };
}

function renderChats() {
      const list = document.getElementById('chatList');
      const q = (document.getElementById('searchChats').value || '').toLowerCase();
      const filtered = state.chats.filter(c => {
            const { title } = chatDisplayInfo(c);
            return title.toLowerCase().includes(q);
      });
      if (!filtered.length) {
            list.innerHTML = `<div class="text-center text-muted p-3 small">چتی نیست</div>`;
            return;
      }
      list.innerHTML = filtered.map(c => {
            const { title, avatar, last } = chatDisplayInfo(c);
            const active = state.currentChat?.id === c.id ? 'active' : '';
            return `
      <div class="chat-item ${active}" data-chat-id="${c.id}">
        <img class="avatar" src="${avatar}" onerror="this.src='${DEFAULT_AVATAR}'">
        <div class="info">
          <div class="title">${escapeHtml(title)}</div>
          <div class="last">${escapeHtml(last)}</div>
        </div>
        <div class="meta">
          <div>${timeStr(c.last_message?.created_at)}</div>
          ${c.unread_count ? `<span class="badge-unread">${c.unread_count}</span>` : ''}
        </div>
      </div>`;
      }).join('');

      list.querySelectorAll('.chat-item').forEach(el => {
            el.addEventListener('click', () => openChat(Number(el.dataset.chatId)));
      });
}

// ---------- Users ----------
async function loadUsers() {
      try {
            state.users = await api('/users');
            if (state.activeTab === 'users') renderUsers();
      } catch (e) { console.error(e); }
}

function renderUsers() {
      const list = document.getElementById('userList');
      const q = (document.getElementById('searchChats').value || '').toLowerCase();
      const filtered = state.users.filter(u =>
            (u.name || '').toLowerCase().includes(q) ||
            (u.phone || '').toLowerCase().includes(q) ||
            (u.username || '').toLowerCase().includes(q)
      );
      if (!filtered.length) {
            list.innerHTML = `<div class="text-center text-muted p-3 small">کاربری یافت نشد</div>`;
            return;
      }
      list.innerHTML = filtered.map(u => `
    <div class="chat-item user-item" data-user-id="${u.id}">
      <img class="avatar" src="${u.avatar || DEFAULT_AVATAR}" onerror="this.src='${DEFAULT_AVATAR}'">
      <div class="info">
        <div class="title">${escapeHtml(u.name || 'کاربر')}</div>
        <div class="last">${escapeHtml(u.bio || u.phone || '')}</div>
      </div>
      <div class="meta">
        <i class="bi bi-chat-dots" style="color:#25d366;font-size:1.2rem"></i>
      </div>
    </div>
  `).join('');

      list.querySelectorAll('.user-item').forEach(el => {
            el.addEventListener('click', () => openChatWithUser(Number(el.dataset.userId)));
      });
}

async function openChatWithUser(userId) {
      try {
            const chat = await api(`/chats/private/${userId}`, { method: 'POST' });
            const idx = state.chats.findIndex(c => c.id === chat.id);
            if (idx === -1) state.chats.unshift(chat);
            else state.chats[idx] = chat;
            await openChat(chat.id);
            switchTab('chats');
      } catch (e) {
            alert(e.message);
      }
}

// ---------- Open chat ----------
async function openChat(chatId) {
      closeWs();
      const chat = state.chats.find(c => c.id === chatId);
      if (!chat) return;
      state.currentChat = chat;

      document.getElementById('emptyChat').classList.add('d-none');
      document.getElementById('chatActive').classList.remove('d-none');
      document.getElementById('appContainer').classList.add('show-chat');

      const { title, avatar } = chatDisplayInfo(chat);
      document.getElementById('chatTitle').textContent = title;
      document.getElementById('chatAvatar').src = avatar;
      document.getElementById('chatAvatar').onerror = function () { this.src = DEFAULT_AVATAR; };
      document.getElementById('chatSubtitle').textContent =
            chat.type === 'group' ? `${chat.members.length} عضو` :
                  chat.type === 'channel' ? 'کانال' : '';

      try {
            const msgs = await api(`/chats/${chatId}/messages?limit=50`);
            renderMessages(msgs);
      } catch (e) {
            document.getElementById('messages').innerHTML =
                  `<div class="text-center text-muted p-3 small">خطا در بارگذاری پیام‌ها</div>`;
      }

      api(`/chats/${chatId}/read`, { method: 'POST' }).catch(() => { });
      connectWs(chatId);

      document.querySelectorAll('.chat-item').forEach(el =>
            el.classList.toggle('active', Number(el.dataset.chatId) === chatId)
      );

      setTimeout(() => document.getElementById('msgInput')?.focus(), 100);
}

function renderMessages(msgs) {
      const box = document.getElementById('messages');
      box.innerHTML = '';
      msgs.forEach(m => box.appendChild(buildMsgEl(m)));
      box.scrollTop = box.scrollHeight;
}

function buildMsgEl(m) {
      const div = document.createElement('div');
      div.className = 'msg';
      if (m.id) div.dataset.mid = m.id;

      if (m.type === 'system' || m.sender_id === null) {
            div.classList.add('system');
            div.textContent = m.content || 'پیام سیستمی';
            return div;
      }

      if (m.is_deleted) {
            div.classList.add('deleted');
            div.classList.add(m.sender_id === me.id ? 'mine' : 'other');
            div.textContent = 'این پیام حذف شد';
            return div;
      }

      div.classList.add(m.sender_id === me.id ? 'mine' : 'other');
      const showSender = state.currentChat?.type !== 'private' && m.sender_id !== me.id;

      let mediaHtml = '';
      if (m.file_url && m.type === 'image') {
            mediaHtml = `<img class="media image" src="${m.file_url}" alt="عکس"
                      onclick="window.__previewImage('${m.file_url}')">`;
      } else if (m.file_url && m.type === 'video') {
            mediaHtml = `<video class="media video" controls preload="metadata" src="${m.file_url}"></video>`;
      } else if (m.file_url && m.type === 'audio') {
            mediaHtml = `<audio controls src="${m.file_url}" style="width:100%;margin-bottom:4px"></audio>`;
      } else if (m.file_url && m.type === 'file') {
            const fname = m.file_name || 'فایل';
            mediaHtml = `
      <a class="file-link" href="${m.file_url}" download="${escapeHtml(fname)}" target="_blank">
        <i class="bi bi-file-earmark-arrow-down"></i>
        <div>
          <div class="fname">${escapeHtml(fname)}</div>
          <div class="fsize">دانلود فایل</div>
        </div>
      </a>`;
      }

      div.innerHTML = `
    ${showSender ? `<div class="sender">${escapeHtml(m.sender?.name || 'کاربر')}</div>` : ''}
    ${mediaHtml}
    ${m.content ? `<div class="caption">${escapeHtml(m.content)}</div>` : ''}
    <div class="time">${timeStr(m.created_at)} ${m.is_edited ? '· ویرایش شد' : ''}</div>
  `;
      return div;
}

// ---------- WebSocket ----------
function connectWs(chatId) {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${proto}://${location.host}/ws/chat/${chatId}?token=${token}`;
      state.ws = new WebSocket(url);

      state.ws.onopen = () => { };
      state.ws.onmessage = (ev) => {
            let data;
            try { data = JSON.parse(ev.data); } catch { return; }

            if (data.event === 'new_message') {
                  if (state.currentChat?.id === chatId) {
                        const box = document.getElementById('messages');
                        // چک تکراری
                        if (data.message?.id && box.querySelector(`[data-mid="${data.message.id}"]`)) {
                              // قبلاً اضافه شده
                        } else {
                              const el = buildMsgEl(data.message);
                              box.appendChild(el);
                              box.scrollTop = box.scrollHeight;
                        }
                  }
                  loadChats();
            } else if (data.event === 'message_edited' || data.event === 'message_deleted') {
                  if (state.currentChat?.id === chatId) {
                        api(`/chats/${chatId}/messages?limit=50`).then(renderMessages).catch(() => { });
                  }
            } else if (data.event === 'typing') {
                  const t = document.getElementById('typingIndicator');
                  t.classList.remove('d-none');
                  clearTimeout(state.typingTimer);
                  state.typingTimer = setTimeout(() => t.classList.add('d-none'), 2000);
            } else if (data.event === 'error') {
                  console.warn('WS error:', data.detail);
            }
      };
      state.ws.onclose = () => { state.ws = null; };
      state.ws.onerror = () => { };
}

function closeWs() {
      if (state.ws) {
            try { state.ws.close(); } catch { }
            state.ws = null;
      }
}

// ---------- Send text ----------
function sendMessage() {
      const input = document.getElementById('msgInput');
      const text = input.value.trim();
      if (!text || !state.ws || state.ws.readyState !== WebSocket.OPEN) return;
      state.ws.send(JSON.stringify({ action: 'send_message', content: text }));
      input.value = '';
      input.focus();
}

document.getElementById('btnSend').addEventListener('click', sendMessage);
document.getElementById('msgInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
      } else if (state.ws && state.ws.readyState === WebSocket.OPEN) {
            state.ws.send(JSON.stringify({ action: 'typing' }));
      }
});

// ---------- File upload ----------
document.getElementById('btnAttach').addEventListener('click', () => {
      document.getElementById('fileInput').click();
});

document.getElementById('fileInput').addEventListener('change', async (e) => {
      const f = e.target.files[0];
      if (!f || !state.currentChat) return;

      const maxSize = 20 * 1024 * 1024;
      if (f.size > maxSize) {
            alert('حجم فایل بیش از ۲۰ مگابایت است');
            e.target.value = '';
            return;
      }

      const prog = document.createElement('div');
      prog.className = 'upload-progress';
      prog.innerHTML = `<i class="bi bi-arrow-up-circle"></i> در حال آپلود...`;
      document.body.appendChild(prog);

      try {
            const fd = new FormData();
            fd.append('file', f);
            const res = await fetch(`/chats/${state.currentChat.id}/upload`, {
                  method: 'POST',
                  headers: { 'Authorization': `Bearer ${token}` },
                  body: fd,
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(extractError(data, `خطای ${res.status}`));

            // WebSocket هم broadcast میکنه، ولی برای اطمینان چک تکراری میکنیم
            if (state.currentChat?.id === data.chat_id) {
                  const box = document.getElementById('messages');
                  if (!box.querySelector(`[data-mid="${data.id}"]`)) {
                        const el = buildMsgEl(data);
                        box.appendChild(el);
                        box.scrollTop = box.scrollHeight;
                  }
            }
            loadChats();
      } catch (err) {
            alert(err.message);
      } finally {
            prog.remove();
            e.target.value = '';
      }
});

// ---------- Sidebar tabs ----------
function switchTab(tab) {
      state.activeTab = tab;
      document.querySelectorAll('#sidebarTabs .nav-link').forEach(b => {
            b.classList.toggle('active', b.dataset.tab === tab);
      });
      const chatList = document.getElementById('chatList');
      const userList = document.getElementById('userList');
      const search = document.getElementById('searchChats');

      if (tab === 'chats') {
            chatList.classList.remove('d-none');
            userList.classList.add('d-none');
            search.placeholder = 'جستجوی چت...';
            renderChats();
      } else {
            chatList.classList.add('d-none');
            userList.classList.remove('d-none');
            search.placeholder = 'جستجوی کاربر...';
            if (!state.users.length) loadUsers();
            else renderUsers();
      }
      search.value = '';
}

document.querySelectorAll('#sidebarTabs .nav-link').forEach(btn => {
      btn.addEventListener('click', () => switchTab(btn.dataset.tab));
});

document.getElementById('searchChats').addEventListener('input', () => {
      if (state.activeTab === 'chats') renderChats();
      else renderUsers();
});

// ---------- Create group ----------
document.getElementById('btnNewGroup').addEventListener('click', (e) => {
      e.preventDefault();
      new bootstrap.Modal('#groupModal').show();
});
document.getElementById('btnCreateGroup').addEventListener('click', async () => {
      const name = document.getElementById('groupName').value.trim();
      const desc = document.getElementById('groupDesc').value.trim();
      const ids = document.getElementById('groupMembers').value
            .split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));
      const errEl = document.getElementById('groupError');
      errEl.textContent = '';
      if (!name) { errEl.textContent = 'نام گروه الزامی است'; return; }
      try {
            await api('/groups', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ name, description: desc || null, member_ids: ids })
            });
            bootstrap.Modal.getInstance('#groupModal')?.hide();
            document.getElementById('groupName').value = '';
            document.getElementById('groupDesc').value = '';
            document.getElementById('groupMembers').value = '';
            await loadChats();
      } catch (e) {
            errEl.textContent = e.message;
      }
});

// ---------- Create channel ----------
document.getElementById('btnNewChannel').addEventListener('click', (e) => {
      e.preventDefault();
      new bootstrap.Modal('#channelModal').show();
});
document.getElementById('btnCreateChannel').addEventListener('click', async () => {
      const name = document.getElementById('channelName').value.trim();
      const desc = document.getElementById('channelDesc').value.trim();
      const isPublic = document.getElementById('channelPublic').checked;
      const errEl = document.getElementById('channelError');
      errEl.textContent = '';
      if (!name) { errEl.textContent = 'نام کانال الزامی است'; return; }
      try {
            await api('/channels', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ name, description: desc || null, is_public: isPublic })
            });
            bootstrap.Modal.getInstance('#channelModal')?.hide();
            document.getElementById('channelName').value = '';
            document.getElementById('channelDesc').value = '';
            await loadChats();
      } catch (e) {
            errEl.textContent = e.message;
      }
});

// ---------- Profile ----------
document.getElementById('btnProfile').addEventListener('click', async (e) => {
      e.preventDefault();
      try {
            const u = await api('/auth/me');
            document.getElementById('profileName').value = u.name || '';
            document.getElementById('profileBio').value = u.bio || '';
            document.getElementById('profileAvatar').src = u.avatar || DEFAULT_AVATAR;
            document.getElementById('profileError').textContent = '';
            document.getElementById('avatarInput').value = '';
            new bootstrap.Modal('#profileModal').show();
      } catch (e) {
            alert(e.message);
      }
});

document.getElementById('btnSaveProfile').addEventListener('click', async () => {
      const name = document.getElementById('profileName').value.trim();
      const bio = document.getElementById('profileBio').value.trim();
      const errEl = document.getElementById('profileError');
      errEl.textContent = '';
      try {
            await api('/auth/me', {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ name, bio })
            });
            const f = document.getElementById('avatarInput').files[0];
            if (f) {
                  const fd = new FormData(); fd.append('file', f);
                  await api('/auth/me/avatar', { method: 'POST', body: fd });
            }
            bootstrap.Modal.getInstance('#profileModal')?.hide();
            await loadMe();
            await loadChats();
      } catch (e) {
            errEl.textContent = e.message;
      }
});

// ---------- Logout ----------
document.getElementById('btnLogout').addEventListener('click', (e) => {
      e.preventDefault();
      logout();
});

function logout() {
      closeWs();
      localStorage.clear();
      window.location.href = '/login';
}

document.getElementById('btnBack')?.addEventListener('click', () => {
      document.getElementById('appContainer').classList.remove('show-chat');
      closeWs();
});

// ---------- Init ----------
loadMe();
loadChats();
loadUsers();
setInterval(() => {
      loadChats();
      if (state.activeTab === 'users') loadUsers();
}, 10000);