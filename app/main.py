from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import create_tables
from app.routers import auth, transactions, categories, budgets, analytics, ai_insights, recurring_transactions, savings_goals, groups


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title="FinPulse API",
    description="Smart Expense Tracker with AI Insights",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(transactions.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(analytics.router)
app.include_router(ai_insights.router)
app.include_router(recurring_transactions.router)
app.include_router(savings_goals.router)
app.include_router(groups.router)


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": "FinPulse API", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}
