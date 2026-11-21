```markdown
# WhatsApp Clone

کلون واتساپ با FastAPI، WebSocket و Bootstrap.

## قابلیت‌ها

- احراز هویت با شماره تماس و JWT
- پروفایل کاربر (عکس، نام، بیو)
- چت خصوصی دوطرفه با WebSocket (realtime)
- گروه‌ها (ساخت، افزودن/حذف عضو، نقش admin/owner)
- کانال‌ها (فقط ادمین/مالک پست می‌ذاره)
- ارسال متن، عکس، فیلم، صدا و فایل
- پیش‌نمایش عکس با کلیک
- لیست کاربران و شروع چت با هر کاربر
- جستجوی چت و کاربر
- خوانده‌شده، تایپینگ، ویرایش و حذف پیام
- رابط کاربری ریسپانسیو شبیه واتساپ

## پیش‌نیازها

- Python 3.10+
- pip

## نصب

```bash
# 1) ساخت محیط مجازی
python -m venv venv

# ویندوز
venv\Scripts\activate

# لینوکس / مک
source venv/bin/activate

# 2) نصب پکیج‌ها
pip install -r requirements.txt

# 3) ساخت فایل .env
cp .env.example .env
# سپس SECRET_KEY را با یک رشته رندوم عوض کنید:
# python -c "import secrets; print(secrets.token_hex(32))"

# 4) اجرا
uvicorn app.main:app --reload
```

سپس مرورگر: `http://127.0.0.1:8000/login`

## ساختار پروژه

```
whatsapp-clone/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/          # User, Chat, ChatMember, Message, Contact
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # auth, users, contacts, chats, groups, channels, ws, pages
│   ├── services/        # upload, chat_service, message_service, group_service, channel_service, ws_manager
│   ├── utils/           # security, deps
│   ├── templates/       # base.html, login.html, chat.html
│   └── static/          # css, js, img, uploads
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## API

### احراز هویت

- `POST /auth/register` — ثبت‌نام
- `POST /auth/login` — ورود
- `GET /auth/me` — پروفایل من
- `PATCH /auth/me` — ویرایش پروفایل
- `POST /auth/me/avatar` — آپلود عکس پروفایل

### کاربران

- `GET /users` — لیست کاربران
- `GET /users/search?q=` — جستجو
- `GET /users/{id}` — پروفایل کاربر

### مخاطبین

- `GET /contacts`
- `POST /contacts`
- `DELETE /contacts/{id}`

### چت‌ها

- `GET /chats` — لیست چت‌ها
- `POST /chats/private/{user_id}` — باز کردن/ساخت چت خصوصی
- `GET /chats/{id}` — اطلاعات چت
- `GET /chats/{id}/messages` — تاریخچه پیام‌ها
- `POST /chats/{id}/upload` — آپلود فایل/عکس/فیلم
- `POST /chats/{id}/read` — علامت خوانده‌شده
- `PATCH /chats/messages/{id}` — ویرایش پیام
- `DELETE /chats/messages/{id}` — حذف پیام

### گروه‌ها

- `POST /groups`
- `GET /groups/{id}`
- `PATCH /groups/{id}`
- `POST /groups/{id}/avatar`
- `POST /groups/{id}/members`
- `DELETE /groups/{id}/members/{user_id}`
- `POST /groups/{id}/leave`
- `PATCH /groups/{id}/members/{user_id}/role`

### کانال‌ها

- `POST /channels`
- `GET /channels/public`
- `GET /channels/{id}`
- `PATCH /channels/{id}`
- `POST /channels/{id}/avatar`
- `POST /channels/{id}/subscribe`
- `POST /channels/{id}/unsubscribe`
- `POST /channels/{id}/admins`
- `DELETE /channels/{id}/admins/{user_id}`

### WebSocket

- `WS /ws/chat/{chat_id}?token=<JWT>`

پیام‌های ارسالی (JSON):

```json
{"action": "send_message", "content": "سلام", "type": "text"}
{"action": "typing"}
{"action": "read"}
{"action": "edit_message", "message_id": 1, "content": "متن جدید"}
{"action": "delete_message", "message_id": 1}
```

رویدادهای دریافتی (JSON):

```json
{"event": "connected", "chat_id": 1, "user_id": 1}
{"event": "new_message", "message": {...}}
{"event": "message_edited", "message": {...}}
{"event": "message_deleted", "message": {...}}
{"event": "typing", "user_id": 2, "chat_id": 1}
{"event": "read", "user_id": 2, "chat_id": 1}
{"event": "error", "detail": "..."}
```

## تنظیمات (.env)

```env
APP_NAME=WhatsApp Clone
SECRET_KEY=your-super-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
DATABASE_URL=sqlite+aiosqlite:///./whatsapp.db
UPLOAD_DIR=app/static/uploads
MAX_UPLOAD_SIZE=5242880
```

## محدودیت‌ها

- عکس پروفایل: حداکثر ۵ مگابایت (jpeg/png/webp)
- فایل پیام: حداکثر ۲۰ مگابایت
- انواع مجاز: image/*, video/*, audio/*, pdf, zip, doc(x), xls(x), txt

## مستندات API

پس از اجرا: `http://127.0.0.1:8000/docs`

## مجوز

MIT
```
