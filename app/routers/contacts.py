from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.models.user import User
from app.models.contact import Contact
from app.schemas.contact import ContactCreate, ContactWithChat
from app.utils.deps import get_current_user
from app.services.chat_service import find_private_chat_id, get_or_create_private_chat


router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactWithChat])
async def list_contacts(
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    stmt = (
        select(Contact)
        .where(Contact.owner_id == current.id)
        .options(selectinload(Contact.contact))
        .order_by(Contact.created_at.desc())
    )
    result = await db.execute(stmt)
    contacts = result.scalars().all()

    out: list[ContactWithChat] = []
    for c in contacts:
        chat_id = await find_private_chat_id(db, current.id, c.contact_id)
        out.append(
            ContactWithChat(
                id=c.id,
                alias=c.alias,
                created_at=c.created_at,
                contact=c.contact,
                chat_id=chat_id,
            )
        )
    return out


@router.post("", response_model=ContactWithChat, status_code=status.HTTP_201_CREATED)
async def add_contact(
    payload: ContactCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    # پیدا کردن کاربر با شماره
    result = await db.execute(select(User).where(User.phone == payload.phone))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "کاربری با این شماره یافت نشد")
    if target.id == current.id:
        raise HTTPException(400, "نمیتونی خودت رو اضافه کنی")

    # چک تکراری
    dup = await db.execute(
        select(Contact).where(Contact.owner_id == current.id, Contact.contact_id == target.id)
    )
    if dup.scalar_one_or_none():
        raise HTTPException(400, "این کاربر قبلاً در مخاطبین شماست")

    contact = Contact(owner_id=current.id, contact_id=target.id, alias=payload.alias)
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    contact.contact = target  # برای serialize

    # ساخت یا پیدا کردن چت خصوصی
    chat = await get_or_create_private_chat(db, current.id, target.id)

    return ContactWithChat(
        id=contact.id,
        alias=contact.alias,
        created_at=contact.created_at,
        contact=target,
        chat_id=chat.id,
    )


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.owner_id == current.id)
    )
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(404, "مخاطب یافت نشد")
    await db.delete(contact)
    await db.commit()
    return None