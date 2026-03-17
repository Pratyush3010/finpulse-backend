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
from pydantic import BaseModel
from google import genai
import json

router = APIRouter(prefix="/ai", tags=["AI Insights"])


class InsightResponse(BaseModel):
    insights: list[str]
    summary: str
    tips: list[str]


class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str


@router.get("/models")
async def list_models(current_user: User = Depends(get_current_user)):
    """Debug endpoint to list available Gemini models."""
    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        models = [m.name for m in client.models.list()]
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip()

        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]

        data = json.loads(text)
        return InsightResponse(**data)

    except Exception as e:
        print(f"Gemini error: {e}")
        top = rows[0]
        return InsightResponse(
            insights=[
                f"You spent most on {top.name} ({top.type}): ${top.total:.2f}.",
                f"You have {len(rows)} spending categories this month.",
                "Review your top categories to find saving opportunities.",
            ],
            summary=f"You have {len(rows)} active spending categories this month.",
            tips=[
                f"Try reducing spending in {top.name}.",
                "Set a monthly budget for your top category.",
                "Save at least 20% of your monthly income.",
            ],
        )

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="AI service not configured")

    result = await db.execute(
        select(Category.name, Transaction.type, Transaction.amount, Transaction.date)
        .join(Transaction, Transaction.category_id == Category.id)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc())
        .limit(20)
    )
    rows = result.all()
    context = "\n".join([f"- {r.name} ({r.type}): ${r.amount:.2f} on {r.date.strftime('%b %d')}" for r in rows]) if rows else "No transactions yet."

    prompt = f"""You are a helpful personal finance assistant.
User's recent transactions:
{context}

User question: {request.message}

Give a helpful, concise financial answer in 2-3 sentences. Be specific to their data if relevant."""

    try:
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return ChatResponse(reply=response.text.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI error: {str(e)}")
