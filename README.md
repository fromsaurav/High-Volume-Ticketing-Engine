# High-Volume Ticketing Engine

A movie seat booking system built to handle high concurrency using **Pessimistic Locking** to prevent double-bookings.

## Problem Statement

Build a high-volume ticketing engine that allows multiple users to book movie seats simultaneously without race conditions. The system must:

- Display real-time seat availability
- Handle concurrent booking attempts gracefully
- Provide a 5-minute seat hold during payment
- Prevent double-booking under any circumstances

## Solution

A full-stack application using Django REST Framework + PostgreSQL with **Pessimistic Locking** (`SELECT FOR UPDATE`) to ensure data consistency. When a user books a seat, the database row is locked until the transaction completes, preventing other users from booking the same seat.

**Key Features:**
- Real-time seat map with color-coded status (Available/On Hold/Booked)
- 5-minute temporary seat hold during payment
- Immediate seat release on payment cancellation
- Graceful error handling on booking conflicts

## Project Structure

```
├── backend/                   # Django REST API
│   ├── booking/              # Core booking app
│   │   ├── models.py         # Venue, Hall, Seat, Movie, Show, Booking
│   │   ├── views.py          # API endpoints with pessimistic locking
│   │   ├── migrations/       # SQL schema evolution (0001_initial.py)
│   │   └── ...
│   └── config/               # Django settings
├── frontend/                  # React + Vite
│   └── src/
│       ├── App.jsx           # Main application
│       └── App.css           # Styling
├── DESIGN.md                  # Architecture decisions & ER diagram
├── System_Architecture.md     # Concurrency strategy & API flow
└── README.md                  # This file
```

## Setup Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 16+

### Quick Start (If Already Set Up)

```bash
# Terminal 1 - Backend
source venv/bin/activate
cd backend && python manage.py runserver 0.0.0.0:8000

# Terminal 2 - Frontend
cd frontend && npm run dev -- --port 3000
```
Open http://localhost:3000

---

### First Time Setup

### 1. Clone & Setup Backend

```bash
# From project root directory (FIRST TIME ONLY)
python3 -m venv venv
source venv/bin/activate        # Run every time you open terminal
pip install -r backend/requirements.txt  # FIRST TIME ONLY
```

### 2. Setup PostgreSQL (FIRST TIME ONLY)

```bash
# Connect to PostgreSQL and create database
sudo -u postgres psql
CREATE DATABASE ticketing_db;
CREATE USER ticketing_user WITH PASSWORD 'ticketing_secure_123';
GRANT ALL PRIVILEGES ON DATABASE ticketing_db TO ticketing_user;
\c ticketing_db
GRANT ALL ON SCHEMA public TO ticketing_user;
\q
```

### 3. Configure Environment (FIRST TIME ONLY)

Create `backend/.env`:
```
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://ticketing_user:ticketing_secure_123@localhost:5432/ticketing_db
USE_SQLITE=False
```

### 4. Run Migrations & Seed Data

```bash
cd backend
source ../venv/bin/activate     # Activate venv if not already
python manage.py migrate        # Run every time after model changes
python manage.py seed_data      # FIRST TIME ONLY - populates sample data
```

### 5. Setup Frontend (FIRST TIME ONLY)

```bash
cd frontend
npm install
```

### 6. Run the Application

```bash
# Terminal 1 - Backend
cd backend && python manage.py runserver 0.0.0.0:8000

# Terminal 2 - Frontend
cd frontend && npm run dev -- --port 3000
```

Open http://localhost:3000

### View PostgreSQL Schema

```bash
psql -U ticketing_user -d ticketing_db -h localhost
# Password: ticketing_secure_123

\dt                    # List all tables
\d booking_booking     # View booking table schema
\d booking_seat        # View seat table schema
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18, Vite |
| Backend | Django 6.0, Django REST Framework |
| Database | PostgreSQL 16 |
| Concurrency | Pessimistic Locking (`SELECT FOR UPDATE`) |

## License

MIT License

---

**Built with ❤️ by Saurav**
