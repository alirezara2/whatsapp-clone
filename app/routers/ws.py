import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.chat import Chat, ChatType, ChatMemberRole
from app.models.message import Message, MessageType
from app.utils.security import decode_token
from app.services.ws_manager import manager
from app.services import message_service
from app.schemas.message import MessagePublic


router = APIRouter(tags=["websocket"])


async def _get_user_from_token(token: str) -> User | None:
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        uid = int(payload["sub"])
    except (ValueError, TypeError):
        return None
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == uid))
        return result.scalar_one_or_none()


@router.websocket("/ws/chat/{chat_id}")
async def ws_chat(websocket: WebSocket, chat_id: int, token: str = Query(...)):
    # 1) احراز هویت
    user = await _get_user_from_token(token)
    if not user:
        await websocket.close(code=4001)
        return

    # 2) چک عضویت + نوع چت
    async with AsyncSessionLocal() as db:
        if not await message_service.is_member(db, chat_id, user.id):
            await websocket.close(code=4003)
            return

        chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
        chat = chat_result.scalar_one_or_none()
        if not chat:
            await websocket.close(code=4004)
            return

        # اگه کاناله، فقط admin/owner میتونن وصل بشن (برای ارسال پیام)
        if chat.type == ChatType.CHANNEL:
            member = await message_service.get_chat_member(db, chat_id, user.id)
            if not member or member.role not in (ChatMemberRole.ADMIN, ChatMemberRole.OWNER):
                await websocket.close(code=4003)
                return

    # 3) اتصال
    await manager.connect(chat_id, user.id, websocket)
    try:
        await websocket.send_json(
            {"event": "connected", "chat_id": chat_id, "user_id": user.id}
        )

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"event": "error", "detail": "JSON نامعتبر"})
                continue

            action = data.get("action")

            # ---------- ارسال پیام جدید ----------
            if action == "send_message":
                content = (data.get("content") or "").strip()
                msg_type = data.get("type", "text")
                reply_to = data.get("reply_to_id")
                if not content and msg_type == "text":
                    await websocket.send_json({"event": "error", "detail": "متن خالی"})
                    continue

                async with AsyncSessionLocal() as db:
                    # چک مجوز برای کانال (دوباره، چون ممکنه نقشش عوض شده باشه)
                    chat_result = await db.execute(select(Chat).where(Chat.id == chat_id))
                    chat = chat_result.scalar_one_or_none()
                    if chat and chat.type == ChatType.CHANNEL:
                        member = await message_service.get_chat_member(db, chat_id, user.id)
                        if not member or member.role not in (
                            ChatMemberRole.ADMIN,
                            ChatMemberRole.OWNER,
                        ):
                            await websocket.send_json(
                                {"event": "error", "detail": "فقط ادمین/مالک میتونه پست بذاره"}
                            )
                            continue

                    try:
                        msg = await message_service.create_message(
                            db,
                            chat_id=chat_id,
                            sender_id=user.id,
                            content=content,
                            msg_type=MessageType(msg_type),
                            reply_to_id=reply_to,
                        )
                        payload = MessagePublic.model_validate(msg).model_dump(mode="json")
                    except Exception as e:
                        await websocket.send_json(
                            {"event": "error", "detail": f"خطا در ذخیره پیام: {e}"}
                        )
                        continue

                await manager.broadcast(chat_id, {"event": "new_message", "message": payload})

            # ---------- ویرایش پیام ----------
            elif action == "edit_message":
                msg_id = data.get("message_id")
                new_content = (data.get("content") or "").strip()
                if not msg_id or not new_content:
                    await websocket.send_json({"event": "error", "detail": "پارامتر ناقص"})
                    continue

                async with AsyncSessionLocal() as db:
                    result = await db.execute(
                        select(Message)
                        .where(Message.id == msg_id)
                        .options(selectinload(Message.sender))
                    )
                    msg = result.scalar_one_or_none()
                    if not msg or msg.chat_id != chat_id or msg.sender_id != user.id:
                        await websocket.send_json({"event": "error", "detail": "اجازه نداری"})
                        continue
                    msg.content = new_content
                    msg.is_edited = True
                    await db.commit()
                    await db.refresh(msg)
                    payload = MessagePublic.model_validate(msg).model_dump(mode="json")

                await manager.broadcast(chat_id, {"event": "message_edited", "message": payload})

            # ---------- حذف پیام ----------
            elif action == "delete_message":
                msg_id = data.get("message_id")
                if not msg_id:
                    continue

                async with AsyncSessionLocal() as db:
                    result = await db.execute(select(Message).where(Message.id == msg_id))
                    msg = result.scalar_one_or_none()
                    if not msg or msg.chat_id != chat_id or msg.sender_id != user.id:
                        await websocket.send_json({"event": "error", "detail": "اجازه نداری"})
                        continue
                    msg.is_deleted = True
                    msg.content = None
                    msg.file_url = None
                    msg.file_name = None
                    await db.commit()
                    await db.refresh(msg)
                    payload = MessagePublic.model_validate(msg).model_dump(mode="json")

                await manager.broadcast(chat_id, {"event": "message_deleted", "message": payload})

            # ---------- typing ----------
            elif action == "typing":
                await manager.broadcast(
                    chat_id,
                    {"event": "typing", "user_id": user.id, "chat_id": chat_id},
                    exclude_ws=websocket,
                )

            # ---------- read receipt ----------
            elif action == "read":
                async with AsyncSessionLocal() as db:
                    member = await message_service.get_chat_member(db, chat_id, user.id)
                    last = await message_service.get_last_message(db, chat_id)
                    if member and last:
                        member.last_read_message_id = last.id
                        await db.commit()
                await manager.broadcast(
                    chat_id,
                    {"event": "read", "user_id": user.id, "chat_id": chat_id},
                    exclude_ws=websocket,
                )

            else:
                await websocket.send_json(
                    {"event": "error", "detail": f"action نامعتبر: {action}"}
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"❌ WS error: {e}")
    finally:
        await manager.disconnect(chat_id, user.id, websocket)