from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.balance import (
    BalanceOut,
    TopupRequest,
    TransactionListResponse,
    TransactionOut,
)

router = APIRouter(prefix="/balance", tags=["balance"])


@router.get("", response_model=BalanceOut)
async def get_balance(user: User = Depends(get_current_user)):
    if user.role != "master" or not user.master_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Master only")
    mp = user.master_profile
    return BalanceOut(balance=mp.balance or 0, tier=mp.tier, commission_percent=mp.commission_percent)


@router.post("/topup", response_model=BalanceOut)
async def topup(
    req: TopupRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role != "master" or not user.master_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Master only")
    mp = user.master_profile
    mp.balance = (mp.balance or 0) + req.amount
    db.add(Transaction(
        user_id=user.id,
        type="topup",
        amount=req.amount,
        balance_after=mp.balance,
        description="Пополнение баланса",
    ))
    await db.flush()
    return BalanceOut(balance=mp.balance, tier=mp.tier, commission_percent=mp.commission_percent)


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return TransactionListResponse(
        transactions=[TransactionOut.model_validate(r, from_attributes=True) for r in rows]
    )
