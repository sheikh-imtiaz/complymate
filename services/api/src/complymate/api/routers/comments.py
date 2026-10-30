from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from complymate.api.deps import Ctx, require
from complymate.application.notify import notify
from complymate.db.models import Comment, Mention, User
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.collaboration import comments as rules
from complymate.domain.collaboration.mentions import extract_emails, extract_user_ids
from complymate.domain.errors import Forbidden, NotFound
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import scope_for
from complymate.schemas.comments import CommentIn, CommentOut, CommentUpdate
from complymate.schemas.common import Ok

router = APIRouter(prefix="/comments", tags=["comments"])

LINKS = {
    "client": "/clients/{id}",
    "smr_case": "/smr/{id}",
    "program_section": "/program",
    "program_version": "/program/{id}",
    "task": "/tasks",
}


def _check_resource_access(ctx: Ctx, resource_type: str) -> None:
    if scope_for(ctx.principal, rules.required_read_permission(resource_type)) is None:
        raise Forbidden("you cannot comment on this item")


@router.get("", response_model=list[CommentOut])
async def list_comments(
    resource_type: str, resource_id: str, ctx: Ctx = Depends(require(P.COMMENT_READ))
) -> list[CommentOut]:
    _check_resource_access(ctx, resource_type)
    stmt = (
        select(Comment, User.full_name)
        .join(User, User.id == Comment.author_id)
        .where(Comment.resource_type == resource_type, Comment.resource_id == resource_id, Comment.deleted_at.is_(None))
        .order_by(Comment.created_at)
    )
    return [
        CommentOut.model_validate(c).model_copy(update={"author_name": name})
        for c, name in (await ctx.session.execute(stmt)).all()
    ]


@router.post("", response_model=CommentOut, status_code=201)
async def add_comment(body: CommentIn, ctx: Ctx = Depends(require(P.COMMENT_CREATE))) -> CommentOut:
    _check_resource_access(ctx, body.resource_type)
    text = rules.validate(body.resource_type, body.body)
    comment = Comment(
        tenant_id=ctx.tenant_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        author_id=ctx.user_id,
        body=text,
    )
    ctx.session.add(comment)
    await ctx.session.flush()
    users = UserRepo(ctx.session)
    member_ids = {m["user_id"] for m in await users.members(ctx.tenant_id) if m["status"] == "active"}
    mentioned = extract_user_ids(text) & member_ids
    for email in extract_emails(text):
        u = await users.by_email(email)
        if u and u.id in member_ids:
            mentioned.add(u.id)
    mentioned.discard(ctx.user_id)
    if body.resource_type == "smr_case":  # strict SMR access: never notify people who cannot see SMRs
        allowed = {u.id for u in await users.users_with_role(ctx.tenant_id, ("owner", "amlco", "senior_manager"))}
        mentioned &= allowed
    for uid in mentioned:
        ctx.session.add(Mention(tenant_id=ctx.tenant_id, comment_id=comment.id, user_id=uid))
    if mentioned:
        await notify(
            ctx.session,
            ctx.container,
            tenant_id=ctx.tenant_id,
            user_ids=list(mentioned),
            kind="mention",
            title=f"{ctx.principal.email} mentioned you",
            link=LINKS.get(body.resource_type, "/").format(id=body.resource_id),
        )
    await ctx.record(
        Action.CREATE,
        "comment",
        comment.id,
        after={"resource_type": body.resource_type, "resource_id": body.resource_id, "mentions": len(mentioned)},
    )
    return CommentOut.model_validate(comment).model_copy(
        update={"author_name": ctx.user.full_name if ctx.user else None}
    )


@router.patch("/{comment_id}", response_model=CommentOut)
async def edit_comment(
    comment_id: UUID, body: CommentUpdate, ctx: Ctx = Depends(require(P.COMMENT_CREATE))
) -> CommentOut:
    comment = await ctx.session.get(Comment, comment_id)
    if comment is None or comment.deleted_at:
        raise NotFound("comment not found")
    rules.assert_can_edit(str(comment.author_id), str(ctx.user_id))
    comment.body = rules.validate(comment.resource_type, body.body)
    comment.edited_at = datetime.now(UTC)
    await ctx.record(Action.UPDATE, "comment", comment.id)
    return CommentOut.model_validate(comment)


@router.delete("/{comment_id}", response_model=Ok)
async def delete_comment(comment_id: UUID, ctx: Ctx = Depends(require(P.COMMENT_CREATE))) -> Ok:
    comment = await ctx.session.get(Comment, comment_id)
    if comment is None or comment.deleted_at:
        raise NotFound("comment not found")
    rules.assert_can_edit(str(comment.author_id), str(ctx.user_id))
    comment.deleted_at = datetime.now(UTC)
    await ctx.record(Action.DELETE, "comment", comment.id)
    return Ok()
