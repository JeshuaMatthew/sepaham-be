import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.core.broadcaster import broadcaster
from src.app.core.config import settings
from src.app.shared.Services.storage import save_uploaded_file
from src.app.modules.auth.entity import User
from src.app.modules.profile.entity import Profile
from src.app.modules.community.entity import (
    Server,
    Channel,
    ServerMember,
    CommunityInvite,
    DirectConversation,
    Message,
)
from src.app.modules.community.schemas import (
    ServerObj,
    ChannelObj,
    ChatAttachmentResponse,
    CommunityMineItem,
    CommunityMineResponse,
    DiscoverServerItem,
    DiscoverServersResponse,
    JoinServerResponse,
    CreateInviteResponse,
    MessageResponse,
    MessageCode,
    MessageAttachment,
    PostMessageRequest,
    DMItem,
    DMsResponse,
)

DM_ROOM_PREFIX = "dm:"

MAX_CHAT_ATTACHMENT_BYTES = 10 * 1024 * 1024
CHAT_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"})


async def upload_chat_attachment(file: UploadFile) -> ChatAttachmentResponse:
    """Simpan lampiran chat dan kembalikan metadata + URL yang bisa dibuka.

    Sebelumnya frontend memakai konstanta `screenshot.png` 128 KB yang dikirim
    sebagai attachment ke server lalu tampil sebagai lampiran asli di sisi
    penerima — tanpa pernah ada berkas yang diunggah.
    """
    from pathlib import Path as _Path

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Berkas kosong.",
        )
    if len(content) > MAX_CHAT_ATTACHMENT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Berkas maksimal 10 MB.",
        )

    original_name = (file.filename or "file").strip() or "file"
    ext = _Path(original_name).suffix.lower()
    kind = "image" if ext in CHAT_IMAGE_EXTENSIONS else "file"

    await file.seek(0)
    saved_name = await save_uploaded_file(file)

    size_kb = max(1, len(content) // 1024)
    size = f"{size_kb} KB" if size_kb < 1024 else f"{size_kb / 1024:.1f} MB"
    url = f"{settings.PUBLIC_BASE_URL.rstrip('/')}/uploads/{saved_name}"

    return ChatAttachmentResponse(name=original_name, kind=kind, size=size, url=url)


def dm_room(dm_id: str) -> str:
    """Nama room websocket untuk sebuah DM.

    Channel dan DM memakai id yang sama-sama string, jadi diberi awalan berbeda
    supaya satu tidak bisa mengunci langganan yang lain.
    """
    return f"{DM_ROOM_PREFIX}{dm_id}"


async def _require_channel(db: AsyncSession, channel_id: str) -> Channel:
    """Ambil channel atau 404."""
    res = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = res.scalar_one_or_none()
    if channel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel tidak ditemukan")
    return channel


async def _require_channel_membership(db: AsyncSession, user_id: uuid.UUID, server_id: str) -> None:
    """Pengguna harus anggota server induk channel.

    Sebelumnya `get_channel_messages` dipanggil tanpa `CurrentUser` sama sekali
    dan `post_channel_message` hanya memastikan channel-nya ada. Akibatnya siapa
    pun yang tahu id channel (yang di-seed singkat, misalnya "general" atau
    "tanya-anonim") bisa membaca dan menulis pesan, termasuk channel anonim yang
    tujuannya justru menyembunyikan identitas.
    """
    res = await db.execute(
        select(ServerMember).where(
            ServerMember.server_id == server_id,
            ServerMember.user_id == user_id,
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda bukan anggota dari server ini",
        )


def _format_message_response(msg: Message) -> MessageResponse:
    author_id = "anon" if msg.anonymous or not msg.author_id else str(msg.author_id)
    author_name = "Anonymous" if msg.anonymous else msg.author_name
    author_avatar = "" if msg.anonymous else msg.author_avatar

    code = None
    if msg.code_content:
        code = MessageCode(language=msg.code_language or "", content=msg.code_content)

    attachment = None
    if msg.attachment_name:
        attachment = MessageAttachment(
            name=msg.attachment_name,
            kind=msg.attachment_kind or "",
            size=msg.attachment_size or "",
            url=msg.attachment_url or None,
        )

    ts = msg.created_at.strftime("%H:%M") if msg.created_at else ""

    return MessageResponse(
        id=str(msg.id),
        author_id=author_id,
        author_name=author_name,
        author_avatar=author_avatar,
        timestamp=ts,
        text=msg.body,
        code=code,
        attachment=attachment,
        anonymous=msg.anonymous,
        replies=[],
    )

async def get_my_communities(db: AsyncSession, user_id: uuid.UUID) -> CommunityMineResponse:
    stmt = (
        select(Server)
        .join(ServerMember, ServerMember.server_id == Server.id)
        .where(ServerMember.user_id == user_id, Server.banned.is_(False))
        .order_by(ServerMember.joined_at.desc())
    )
    result = await db.execute(stmt)
    servers = result.scalars().all()

    if not servers:
        return CommunityMineResponse(communities=[])

    server_ids = [s.id for s in servers]
    ch_stmt = (
        select(Channel)
        .where(Channel.server_id.in_(server_ids))
        .order_by(Channel.server_id, Channel.sort_order)
    )
    ch_result = await db.execute(ch_stmt)
    channels = ch_result.scalars().all()

    ch_by_server: dict[str, list[ChannelObj]] = {s.id: [] for s in servers}
    for ch in channels:
        ch_by_server.setdefault(ch.server_id, []).append(
            ChannelObj(
                id=ch.id,
                server_id=ch.server_id,
                name=ch.name,
                topic=ch.topic,
                kind=ch.kind.value if hasattr(ch.kind, "value") else str(ch.kind),
            )
        )

    communities = [
        CommunityMineItem(
            server=ServerObj(
                id=s.id,
                name=s.name,
                initial=s.initial,
                color=s.color,
            ),
            channels=ch_by_server.get(s.id, []),
        )
        for s in servers
    ]
    return CommunityMineResponse(communities=communities)

async def discover_servers(db: AsyncSession, user_id: uuid.UUID) -> DiscoverServersResponse:
    """
    Daftar SEMUA server yang tidak di-ban, lengkap dengan channel, jumlah anggota,
    dan apakah user saat ini sudah jadi anggota.

    Tanpa endpoint ini user baru yang belum punya satu pun server tidak punya
    jalan masuk ke fitur chat: endpoint `join` hanya dipanggil dari invite link.
    """
    s_stmt = select(Server).where(Server.banned.is_(False)).order_by(Server.name)
    s_result = await db.execute(s_stmt)
    servers = s_result.scalars().all()

    if not servers:
        return DiscoverServersResponse(servers=[])

    server_ids = [s.id for s in servers]

    ch_stmt = (
        select(Channel)
        .where(Channel.server_id.in_(server_ids))
        .order_by(Channel.server_id, Channel.sort_order)
    )
    ch_result = await db.execute(ch_stmt)
    ch_by_server: dict[str, list[ChannelObj]] = {i: [] for i in server_ids}
    for ch in ch_result.scalars().all():
        ch_by_server.setdefault(ch.server_id, []).append(
            ChannelObj(
                id=ch.id,
                server_id=ch.server_id,
                name=ch.name,
                topic=ch.topic,
                kind=ch.kind.value if hasattr(ch.kind, "value") else str(ch.kind),
            )
        )

    cnt_stmt = (
        select(ServerMember.server_id, func.count(ServerMember.user_id))
        .where(ServerMember.server_id.in_(server_ids))
        .group_by(ServerMember.server_id)
    )
    counts: dict[str, int] = {sid: 0 for sid in server_ids}
    for sid, n in (await db.execute(cnt_stmt)).all():
        counts[sid] = n

    mine_stmt = select(ServerMember.server_id).where(ServerMember.user_id == user_id)
    mine = set((await db.execute(mine_stmt)).scalars().all())

    return DiscoverServersResponse(
        servers=[
            DiscoverServerItem(
                server=ServerObj(id=s.id, name=s.name, initial=s.initial, color=s.color),
                channels=ch_by_server.get(s.id, []),
                member_count=counts.get(s.id, 0),
                joined=s.id in mine,
            )
            for s in servers
        ]
    )


async def join_server(db: AsyncSession, user_id: uuid.UUID, server_id: str) -> JoinServerResponse:
    s_stmt = select(Server).where(Server.id == server_id)
    s_result = await db.execute(s_stmt)
    server = s_result.scalar_one_or_none()

    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server tidak ditemukan")
    if server.banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Server sedang di-ban")

    m_stmt = select(ServerMember).where(
        ServerMember.server_id == server_id,
        ServerMember.user_id == user_id,
    )
    m_result = await db.execute(m_stmt)
    member = m_result.scalar_one_or_none()

    if not member:
        new_member = ServerMember(server_id=server_id, user_id=user_id)
        db.add(new_member)
        await db.commit()

    ch_stmt = select(Channel).where(Channel.server_id == server_id).order_by(Channel.sort_order)
    ch_result = await db.execute(ch_stmt)
    channels = ch_result.scalars().all()

    return JoinServerResponse(
        server=ServerObj(
            id=server.id,
            name=server.name,
            initial=server.initial,
            color=server.color,
        ),
        channels=[
            ChannelObj(
                id=ch.id,
                server_id=ch.server_id,
                name=ch.name,
                topic=ch.topic,
                kind=ch.kind.value if hasattr(ch.kind, "value") else str(ch.kind),
            )
            for ch in channels
        ],
    )

async def create_invite(db: AsyncSession, user_id: uuid.UUID, server_id: str) -> CreateInviteResponse:
    m_stmt = select(ServerMember).where(
        ServerMember.server_id == server_id,
        ServerMember.user_id == user_id,
    )
    m_result = await db.execute(m_stmt)
    if not m_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda bukan anggota dari server ini",
        )

    invite = CommunityInvite(server_id=server_id, created_by=user_id)
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return CreateInviteResponse(token=str(invite.token), server_id=server_id)

async def accept_invite(db: AsyncSession, user_id: uuid.UUID, token: uuid.UUID) -> JoinServerResponse:
    now = datetime.now(timezone.utc)
    stmt = select(CommunityInvite).where(
        CommunityInvite.token == token,
        or_(CommunityInvite.expires_at.is_(None), CommunityInvite.expires_at > now),
    )
    result = await db.execute(stmt)
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite token tidak ditemukan atau sudah kadaluarsa",
        )

    return await join_server(db, user_id, invite.server_id)

async def get_channel_messages(
    db: AsyncSession, user_id: uuid.UUID, channel_id: str
) -> list[MessageResponse]:
    channel = await _require_channel(db, channel_id)
    await _require_channel_membership(db, user_id, channel.server_id)

    stmt = select(Message).where(Message.channel_id == channel_id).order_by(Message.created_at)
    result = await db.execute(stmt)
    messages = result.scalars().all()

    top_level: list[MessageResponse] = []
    by_id: dict[str, MessageResponse] = {}

    for msg in messages:
        resp = _format_message_response(msg)
        by_id[resp.id] = resp
        if msg.parent_id is None:
            top_level.append(resp)
        else:
            parent = by_id.get(str(msg.parent_id))
            if parent is not None:
                parent.replies.append(resp)
            else:
                top_level.append(resp)

    return top_level

async def post_channel_message(
    db: AsyncSession,
    user_id: uuid.UUID,
    channel_id: str,
    req: PostMessageRequest,
) -> MessageResponse:
    channel = await _require_channel(db, channel_id)
    await _require_channel_membership(db, user_id, channel.server_id)

    u_stmt = select(User, Profile).outerjoin(Profile, Profile.user_id == User.id).where(User.id == user_id)
    u_res = await db.execute(u_stmt)
    user_row = u_res.first()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan")

    user, profile = user_row

    if req.anonymous:
        author_id = None
        author_name = "Anonymous"
        author_avatar = ""
    else:
        author_id = user.id
        author_name = user.name
        author_avatar = profile.avatar_url if profile and profile.avatar_url else ""

    parent_uuid = None
    if req.parent_id:
        try:
            parent_uuid = uuid.UUID(req.parent_id)
        except ValueError:
            pass

    msg = Message(
        channel_id=channel_id,
        dm_id=None,
        parent_id=parent_uuid,
        author_id=author_id,
        author_name=author_name,
        author_avatar=author_avatar,
        body=req.text,
        code_language=req.code.language if req.code else None,
        code_content=req.code.content if req.code else None,
        attachment_name=req.attachment.name if req.attachment else None,
        attachment_kind=req.attachment.kind if req.attachment else None,
        attachment_size=req.attachment.size if req.attachment else None,
        attachment_url=req.attachment.url if req.attachment else None,
        anonymous=req.anonymous,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    resp = _format_message_response(msg)

    try:
        from src.app.modules.badges.service import award_badges_for_user

        await award_badges_for_user(db, user_id)
    except Exception:
        pass

    # Hanya anggota channel itu yang menerima. `broadcast` lama mengirim ke
    # semua socket yang terhubung, termasuk DM pribadi orang lain.
    await broadcaster.broadcast(
        {
            "type": "channel_message",
            "channelId": channel_id,
            "parentId": str(req.parent_id) if req.parent_id else None,
            "message": resp.model_dump(by_alias=True),
        },
        room=channel_id,
    )

    return resp

async def get_dms(db: AsyncSession, user_id: uuid.UUID) -> DMsResponse:
    stmt = (
        select(
            DirectConversation.id,
            DirectConversation.user_low,
            DirectConversation.user_high,
            DirectConversation.created_at,
        )
        .where(
            or_(
                DirectConversation.user_low == user_id,
                DirectConversation.user_high == user_id,
            )
        )
        .order_by(DirectConversation.created_at.desc())
    )
    result = await db.execute(stmt)
    convs = result.all()

    if not convs:
        return DMsResponse(dms=[])

    items: list[DMItem] = []
    for conv in convs:
        other_id = conv.user_high if conv.user_low == user_id else conv.user_low
        u_stmt = select(User, Profile).outerjoin(Profile, Profile.user_id == User.id).where(User.id == other_id)
        u_res = await db.execute(u_stmt)
        u_row = u_res.first()

        user_name = u_row[0].name if u_row and u_row[0] else "User"
        avatar = u_row[1].avatar_url if u_row and u_row[1] and u_row[1].avatar_url else ""
        role = u_row[1].role_title if u_row and u_row[1] and u_row[1].role_title else ""

        m_stmt = select(Message).where(Message.dm_id == conv.id).order_by(Message.created_at)
        m_res = await db.execute(m_stmt)
        msgs = m_res.scalars().all()
        msg_responses = [_format_message_response(m) for m in msgs]

        items.append(
            DMItem(
                id=str(conv.id),
                user_id=str(other_id),
                user_name=user_name,
                avatar=avatar,
                role=role,
                messages=msg_responses,
            )
        )

    return DMsResponse(dms=items)

async def create_or_get_dm(db: AsyncSession, user_id: uuid.UUID, target_user_id: uuid.UUID) -> DMItem:
    if user_id == target_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tidak dapat membuka DM dengan diri sendiri",
        )

    t_stmt = select(User, Profile).outerjoin(Profile, Profile.user_id == User.id).where(User.id == target_user_id)
    t_res = await db.execute(t_stmt)
    t_row = t_res.first()
    if not t_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tujuan tidak ditemukan",
        )

    user_name = t_row[0].name
    avatar = t_row[1].avatar_url if t_row[1] and t_row[1].avatar_url else ""
    role = t_row[1].role_title if t_row[1] and t_row[1].role_title else ""

    low, high = (user_id, target_user_id) if user_id < target_user_id else (target_user_id, user_id)

    stmt = select(DirectConversation).where(
        DirectConversation.user_low == low,
        DirectConversation.user_high == high,
    )
    res = await db.execute(stmt)
    conv = res.scalar_one_or_none()

    if not conv:
        conv = DirectConversation(user_low=low, user_high=high)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)

    m_stmt = select(Message).where(Message.dm_id == conv.id).order_by(Message.created_at)
    m_res = await db.execute(m_stmt)
    msgs = m_res.scalars().all()
    msg_responses = [_format_message_response(m) for m in msgs]

    return DMItem(
        id=str(conv.id),
        user_id=str(target_user_id),
        user_name=user_name,
        avatar=avatar,
        role=role,
        messages=msg_responses,
    )

async def post_dm_message(
    db: AsyncSession,
    user_id: uuid.UUID,
    dm_id: uuid.UUID,
    req: PostMessageRequest,
) -> MessageResponse:
    c_stmt = select(DirectConversation).where(
        DirectConversation.id == dm_id,
        or_(
            DirectConversation.user_low == user_id,
            DirectConversation.user_high == user_id,
        ),
    )
    c_res = await db.execute(c_stmt)
    conv = c_res.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda bukan partisipan dalam percakapan DM ini",
        )

    u_stmt = select(User, Profile).outerjoin(Profile, Profile.user_id == User.id).where(User.id == user_id)
    u_res = await db.execute(u_stmt)
    user_row = u_res.first()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User tidak ditemukan")

    user, profile = user_row
    author_name = user.name
    author_avatar = profile.avatar_url if profile and profile.avatar_url else ""

    msg = Message(
        channel_id=None,
        dm_id=dm_id,
        parent_id=None,
        author_id=user.id,
        author_name=author_name,
        author_avatar=author_avatar,
        body=req.text,
        code_language=req.code.language if req.code else None,
        code_content=req.code.content if req.code else None,
        attachment_name=req.attachment.name if req.attachment else None,
        attachment_kind=req.attachment.kind if req.attachment else None,
        attachment_size=req.attachment.size if req.attachment else None,
        attachment_url=req.attachment.url if req.attachment else None,
        anonymous=False,
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    resp = _format_message_response(msg)

    try:
        from src.app.modules.badges.service import award_badges_for_user

        await award_badges_for_user(db, user_id)
    except Exception:
        pass

    # Hanya dua partisipan percakapan ini yang boleh melihat pesan DM-nya.
    await broadcaster.broadcast(
        {
            "type": "dm_message",
            "dmId": str(dm_id),
            "message": resp.model_dump(by_alias=True),
        },
        room=dm_room(str(dm_id)),
    )

    return resp
