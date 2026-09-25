import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.billing import PACKAGES, add_credits
from app.config import get_settings
from app.database import get_db
from app.models import CreditTransaction, PaymentOrder, User
from app.schemas import (
    CreditTransactionOut,
    OrderCreate,
    OrderOut,
    PackageOut,
    PaymentConfigOut,
    PaymentConfirm,
    PaymentResult,
)
from app.security import get_current_user

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/config", response_model=PaymentConfigOut)
def payment_config():
    """프론트엔드에서 결제창을 열 때 필요한 정보 (클라이언트 키는 공개해도 되는 값)"""
    s = get_settings()
    return PaymentConfigOut(
        client_key=s.toss_client_key,
        price_per_second=s.price_per_second,
        default_duration=s.default_duration,
        packages=[PackageOut(id=k, **v) for k, v in PACKAGES.items()],
    )


@router.post("/orders", response_model=OrderOut)
def create_order(
    body: OrderCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    pkg = PACKAGES.get(body.package_id)
    if pkg is None:
        raise HTTPException(status_code=400, detail="Unknown package")

    order = PaymentOrder(
        order_id=f"loomcut_{uuid.uuid4().hex}",
        user_id=user.id,
        package_id=body.package_id,
        amount=pkg["amount"],
        credits=pkg["credits"],
    )
    db.add(order)
    db.commit()
    return OrderOut(
        order_id=order.order_id,
        order_name=f"loomcut 크레딧 {pkg['name']}",
        amount=order.amount,
        credits=order.credits,
        customer_email=user.email,
    )


@router.post("/confirm", response_model=PaymentResult)
async def confirm_payment(
    body: PaymentConfirm,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """토스 결제창 성공 후 리다이렉트로 받은 paymentKey/orderId/amount로 최종 승인"""
    s = get_settings()
    order = db.scalar(select(PaymentOrder).where(PaymentOrder.order_id == body.order_id))
    if order is None or order.user_id != user.id:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status == "paid":  # 중복 승인 요청은 결과만 반환
        db.refresh(user)
        return PaymentResult(
            order_id=order.order_id, status="paid", credits_added=0, balance=user.credits
        )
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order is {order.status}")
    # 클라이언트가 보낸 금액이 주문 금액과 다르면 위변조 가능성 → 거부
    if body.amount != order.amount:
        raise HTTPException(status_code=400, detail="Amount mismatch")
    if not s.toss_secret_key:
        raise HTTPException(status_code=500, detail="TOSS_SECRET_KEY is not set")

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            f"{s.toss_base_url}/v1/payments/confirm",
            json={
                "paymentKey": body.payment_key,
                "orderId": order.order_id,
                "amount": order.amount,
            },
            auth=(s.toss_secret_key, ""),  # Basic base64("시크릿키:")
        )

    data = r.json() if r.content else {}
    if r.status_code >= 400 or data.get("status") != "DONE":
        order.status = "failed"
        order.fail_reason = data.get("message") or r.text[:500]
        db.commit()
        raise HTTPException(
            status_code=400,
            detail={"code": data.get("code"), "message": data.get("message", "Payment failed")},
        )

    # pending → paid 전환에 성공한 요청만 크레딧 지급 (중복 지급 방지)
    claimed = db.execute(
        update(PaymentOrder)
        .where(PaymentOrder.id == order.id, PaymentOrder.status == "pending")
        .values(
            status="paid",
            payment_key=body.payment_key,
            paid_at=datetime.now(timezone.utc),
        )
    )
    credits_added = 0
    if claimed.rowcount == 1:
        add_credits(db, user.id, order.credits, "topup", order.order_id)
        credits_added = order.credits
    db.commit()
    db.refresh(user)
    return PaymentResult(
        order_id=order.order_id,
        status="paid",
        credits_added=credits_added,
        balance=user.credits,
    )


@router.get("/transactions", response_model=list[CreditTransactionOut])
def list_transactions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(
        select(CreditTransaction)
        .where(CreditTransaction.user_id == user.id)
        .order_by(CreditTransaction.id.desc())
        .limit(100)
    ).all()
