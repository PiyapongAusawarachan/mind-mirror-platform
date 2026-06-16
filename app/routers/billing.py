"""Demo subscription/billing.

No real payment happens. The mock checkout instantly grants the Pro plan so
every gated feature can be demonstrated. The flow (pricing -> checkout ->
confirmation) mirrors a real one for presentation purposes.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import plans
from app.auth import require_user
from app.database import get_db
from app.models import User
from app.templating import render

router = APIRouter()


@router.get("/pricing")
def pricing(request: Request, user: User = Depends(require_user)):
    return render(
        request,
        "billing/pricing.html",
        {
            "user": user,
            "limits": plans.LIMITS,
            "plan_info": plans.PLAN_INFO,
            "feature_keys": plans.FEATURE_KEYS,
            "current_plan": plans.normalize_plan(user.plan),
        },
    )


@router.get("/billing/checkout")
def checkout(request: Request, user: User = Depends(require_user)):
    return render(
        request,
        "billing/checkout.html",
        {"user": user, "plan_info": plans.PLAN_INFO},
    )


@router.post("/billing/upgrade")
def upgrade(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    user.plan = plans.PRO
    db.commit()
    request.session["plan"] = plans.PRO
    return RedirectResponse("/pricing?notice=upgraded", status_code=303)


@router.post("/billing/downgrade")
def downgrade(
    request: Request,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    user.plan = plans.FREE
    db.commit()
    request.session["plan"] = plans.FREE
    return RedirectResponse("/pricing?notice=downgraded", status_code=303)
