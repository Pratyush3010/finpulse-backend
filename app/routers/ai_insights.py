from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract
from app.database import get_db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.category import Category
from app.middleware.auth import get_current_user
from app.config import settings
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel
import google.generativeai as genai

router = APIRouter(prefix="/ai", tags=["AI Insights"])


class InsightResponse(BaseModel):
    insights: list[str]
    summary: str
    tips: list[str]


@router.get("/insights", response_model=InsightResponse)
async def get_ai_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    now = datetime.now()
    month, year = now.month, now.year

    result = await db.execute(
        select(
            Category.name,
            Transaction.type,
            func.sum(Transaction.amount).label("total"),
        )
        .join(Transaction, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == current_user.id,
            extract("month", Transaction.date) == month,
            extract("year", Transaction.date) == year,
        )
        .group_by(Category.name, Transaction.type)
        .order_by(func.sum(Transaction.amount).desc())
    )

    rows = result.all()
    if not rows:
        return InsightResponse(
            insights=["No transactions found for this month."],
            summary="Start adding transactions to get AI-powered insights!",
            tips=["Add your daily expenses", "Set up budget goals", "Track your income sources"],
        )

    breakdown = "\n".join([f"- {r.name} ({r.type}): ${r.total:.2f}" for r in rows])

    prompt = f"""You are a personal finance advisor. Analyze this user's spending for {now.strftime('%B %Y')}:

{breakdown}

Provide a JSON response with exactly these keys:
- "insights": list of 3 key observations about their spending patterns
- "summary": one sentence overall financial health summary
- "tips": list of 3 actionable tips to improve their finances

Keep each insight and tip under 20 words. Be specific to the data above. Return valid JSON only."""

    try:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        import json
        data = json.loads(text)
        return InsightResponse(**data)

    except Exception:
        return InsightResponse(
            insights=[
                f"You spent most on {rows[0].name} this month.",
                "Track daily expenses to identify saving opportunities.",
                "Compare this month to last month for trends.",
            ],
            summary="Keep tracking your finances consistently for better insights.",
            tips=[
                "Set a monthly budget for your top spending category.",
                "Try to save at least 20% of your income.",
                "Review subscriptions and cancel unused ones.",
            ],
        )
