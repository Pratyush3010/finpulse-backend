# FinPulse — Smart Expense Tracker


## Tech Stack

| Layer    | Technology                              |
|----------|-----------------------------------------|
| Backend  | Python 3.11, FastAPI, SQLAlchemy async  |
| Database | PostgreSQL (Neon.tech free tier)        |
| Auth     | JWT (access + refresh tokens)           |
| AI       | Google Gemini 1.5 Flash (free tier)     |
| Mobile   | Flutter 3.x, Riverpod, Dio, fl_chart    |
| Hosting  | Render.com (free tier)                  |

---

## Features

- JWT authentication (register / login / refresh)
- 12 default categories auto-created on registration
- Full CRUD for transactions, categories, budgets
- Analytics: summary, category breakdown, monthly trends
- AI-powered spending insights via Google Gemini
- Beautiful Flutter UI with charts

---

## Project Structure

```
finpulse/
├── finpulse-backend/        # FastAPI backend
│   ├── app/
│   │   ├── main.py          # FastAPI app entry
│   │   ├── config.py        # Settings from .env
│   │   ├── database.py      # Async SQLAlchemy engine
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── routers/         # API route handlers
│   │   ├── middleware/      # JWT auth middleware
│   │   └── utils/           # Security utilities
│   └── requirements.txt
│
└── finpulse-mobile/         # Flutter app
    └── lib/
        ├── main.dart
        ├── app/             # Router + App widget
        ├── core/            # Theme, network, constants
        ├── features/        # auth, dashboard, transactions, analytics, ai
        └── shared/          # models, widgets
```

---

## Backend Setup

### 1. Prerequisites
- Python 3.11+
- PostgreSQL (local) or [Neon.tech](https://neon.tech) free account

### 2. Install dependencies
```bash
cd finpulse-backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
```
Edit `.env`:
```
DATABASE_URL=postgresql+asyncpg://user:password@host/finpulse
SECRET_KEY=your-random-secret-key-here
GEMINI_API_KEY=your-gemini-key   # Get free at https://aistudio.google.com
```

### 4. Run the server
```bash
uvicorn app.main:app --reload --port 8000
```

### 5. API Docs
Visit `http://localhost:8000/docs` for interactive Swagger UI.

---

## Flutter Setup

### 1. Prerequisites
- Flutter SDK 3.x
- Android Studio / VS Code

### 2. Install dependencies
```bash
cd finpulse-mobile
flutter pub get
```

### 3. Configure API URL
Edit `lib/core/constants/app_constants.dart`:
- Android emulator: `http://10.0.2.2:8000` (default)
- Physical device: `http://YOUR_LOCAL_IP:8000`
- Production: your Render.com URL

### 4. Run the app
```bash
flutter run
```

---

## API Endpoints

| Method | Endpoint                  | Description               |
|--------|---------------------------|---------------------------|
| POST   | /auth/register            | Create account            |
| POST   | /auth/login               | Login                     |
| POST   | /auth/refresh             | Refresh token             |
| GET    | /auth/me                  | Current user profile      |
| GET    | /transactions             | List transactions         |
| POST   | /transactions             | Add transaction           |
| DELETE | /transactions/{id}        | Delete transaction        |
| GET    | /categories               | List categories           |
| POST   | /categories               | Create category           |
| GET    | /budgets                  | List budgets with usage   |
| POST   | /budgets                  | Create budget             |
| GET    | /analytics/summary        | Month income/expense      |
| GET    | /analytics/by-category    | Spending by category      |
| GET    | /analytics/monthly-trends | 6-month bar chart data    |
| GET    | /ai/insights              | Gemini AI spending tips   |

---

## Free Hosting (Deploy)

### Backend → Render.com
1. Push `finpulse-backend` to GitHub
2. Create new Web Service on render.com
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env`

### Database → Neon.tech
1. Create free PostgreSQL at [neon.tech](https://neon.tech)
2. Copy connection string → paste in Render environment variables

### AI → Google AI Studio
1. Visit [aistudio.google.com](https://aistudio.google.com)
2. Get free API key → add to environment

---

## Portfolio Highlights

- **Clean Architecture**: routers → services → models
- **Async FastAPI**: non-blocking DB queries with SQLAlchemy async
- **JWT Auth**: access + refresh token rotation
- **Real AI Integration**: Gemini 1.5 Flash with structured prompting
- **Flutter Feature-Based Structure**: clean, scalable organization
- **Riverpod State Management**: reactive, testable state
- **fl_chart Integration**: pie charts + bar charts from real data
