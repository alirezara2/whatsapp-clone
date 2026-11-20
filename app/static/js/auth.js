const API = '';

function extractError(data, fallback = 'خطای نامشخص') {
      if (!data) return fallback;
      const d = data.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d)) {
            // خطای اعتبارسنجی Pydantic
            return d.map(e => {
                  const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : '';
                  return `${field ? field + ': ' : ''}${e.msg || JSON.stringify(e)}`;
            }).join(' | ');
      }
      if (typeof d === 'object') return JSON.stringify(d);
      return fallback;
}

document.getElementById('loginForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const f = new FormData(e.target);
      const body = { phone: f.get('phone'), password: f.get('password') };
      try {
            const res = await fetch('/auth/login', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(body)
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(extractError(data, `خطای ${res.status}`));
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = '/app';
      } catch (err) {
            showError(err.message);
      }
});

document.getElementById('registerForm').addEventListener('submit', async (e) => {
      e.preventDefault();
      const f = new FormData(e.target);
      const body = {
            phone: f.get('phone'), name: f.get('name'),
            password: f.get('password'), bio: f.get('bio') || null
      };
      try {
            const res = await fetch('/auth/register', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(body)
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(extractError(data, `خطای ${res.status}`));
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('user', JSON.stringify(data.user));
            window.location.href = '/app';
      } catch (err) {
            showError(err.message);
      }
});

function showError(msg) {
      const el = document.getElementById('authError');
      el.textContent = String(msg ?? 'خطای نامشخص');
      el.classList.remove('d-none');
}