# System Architecture

---

## Database Schema (PostgreSQL)

Our schema handles Venues, Halls, Movies, Showtimes, and Seats with a robust relational design.

### Tables Overview

| Table | Purpose |
|-------|---------|
| `venue` | Movie theatre locations (name, address, city) |
| `hall` | Screening rooms within venues (capacity, rows, seats per row) |
| `seat` | Individual seats in each hall (row letter, seat number, type) |
| `movie` | Film details (title, duration, genre, rating) |
| `show` | Scheduled screenings (movie + hall + time + price) |
| `booking` | Seat reservations with status tracking |

### Seat State Tracking

We track seat availability through the `booking` table with a `status` field:

| Status | Meaning | Database State |
|--------|---------|----------------|
| **AVAILABLE** | Seat can be booked | No booking record exists |
| **LOCKED** | Held during payment | `status='LOCKED'`, `locked_until > now()` |
| **BOOKED** | Permanently purchased | `status='BOOKED'` |

### Temporary Hold Implementation

When a user selects a seat for payment, we create a booking record with:

```sql
INSERT INTO booking (show_id, seat_id, status, locked_until)
VALUES (1, 42, 'LOCKED', NOW() + INTERVAL '5 minutes');
```

**Hold Logic:**
- If user pays within 5 minutes → status changes to `BOOKED`
- If user cancels → booking record is deleted immediately
- If timer expires → record is ignored (treated as AVAILABLE) and cleaned up on next access

**Query to check availability:**
```sql
SELECT * FROM booking 
WHERE show_id = 1 AND seat_id = 42
  AND (status = 'BOOKED' 
       OR (status = 'LOCKED' AND locked_until > NOW()));
-- If no rows returned, seat is available
```

### Unique Constraint

```sql
-- Prevents double-booking at database level
ALTER TABLE booking ADD CONSTRAINT unique_seat_per_show 
    UNIQUE (show_id, seat_id);
```

---


## Concurrency Strategy: Pessimistic Locking

We use **Pessimistic Locking** with PostgreSQL's `SELECT FOR UPDATE` to handle race conditions.

### How It Works

When a user tries to book a seat:

1. **Lock the row**: `SELECT ... FOR UPDATE` acquires an exclusive lock on the seat row
2. **Check availability**: While locked, verify no one else has booked it
3. **Book or reject**: Either create the booking or return an error
4. **Release lock**: Transaction commits, lock is released

```
User A                              User B
──────                              ──────
BEGIN TRANSACTION
SELECT seat FOR UPDATE (LOCKED)
                                    BEGIN TRANSACTION
                                    SELECT seat FOR UPDATE → WAITING...
Check: Available? → YES
INSERT booking
COMMIT → LOCK RELEASED
                                    → LOCK ACQUIRED
                                    Check: Available? → NO
                                    ROLLBACK → "Seat taken"
```

### Why Pessimistic Over Optimistic?

- **High contention**: Movie bookings have many users competing for same seats
- **Simple implementation**: Django's `select_for_update()` handles everything
- **No retry logic needed**: Database handles waiting automatically
- **Guaranteed consistency**: Impossible to double-book

---

## API Flow

### Booking Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React     │     │   Django    │     │ PostgreSQL  │
│  Frontend   │     │   Backend   │     │  Database   │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │ GET /api/shows/   │                   │
       │──────────────────>│                   │
       │                   │ SELECT shows      │
       │                   │──────────────────>│
       │    shows list     │                   │
       │<──────────────────│                   │
       │                   │                   │
       │ GET /hall-layout/ │                   │
       │──────────────────>│                   │
       │                   │ SELECT seats,     │
       │                   │ bookings          │
       │──────────────────>│──────────────────>│
       │   seat grid       │                   │
       │<──────────────────│                   │
       │                   │                   │
       │ POST /lock-seat/  │                   │
       │──────────────────>│                   │
       │                   │ BEGIN TRANSACTION │
       │                   │ SELECT FOR UPDATE │
       │                   │ INSERT (LOCKED)   │
       │                   │ COMMIT            │
       │   locked (5 min)  │──────────────────>│
       │<──────────────────│                   │
       │                   │                   │
       │ POST /book-seat/  │                   │
       │──────────────────>│                   │
       │                   │ BEGIN TRANSACTION │
       │                   │ SELECT FOR UPDATE │
       │                   │ UPDATE (BOOKED)   │
       │                   │ COMMIT            │
       │   success         │──────────────────>│
       │<──────────────────│                   │
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/shows/` | GET | List available shows |
| `/api/hall-layout/{id}/` | GET | Get seat map for a show |
| `/api/lock-seat/` | POST | Hold seat for 5 minutes |
| `/api/book-seat/` | POST | Confirm booking |
| `/api/release-lock/` | POST | Release held seat |

---

## Database Connection Flow

```
Frontend (React) 
    ↓ HTTP Request
Backend (Django REST Framework)
    ↓ ORM Query with select_for_update()
PostgreSQL (Pessimistic Locking)
    ↓ Row-level lock acquired
Backend processes booking
    ↓ Commit transaction
Lock released, response sent to Frontend
```
