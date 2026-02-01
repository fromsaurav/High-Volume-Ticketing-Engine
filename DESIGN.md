# Design Document

## ER Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   VENUE     │       │    HALL     │       │    SEAT     │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │──1:N──│ id (PK)     │──1:N──│ id (PK)     │
│ name        │       │ venue_id(FK)│       │ hall_id (FK)│
│ address     │       │ name        │       │ row         │
│ city        │       │ capacity    │       │ number      │
└─────────────┘       │ total_rows  │       │ seat_type   │
                      │ seats_per_row│       └──────┬──────┘
                      └──────┬──────┘              │
                             │                     │
                             │ 1:N                 │ N:1
                             ▼                     │
┌─────────────┐       ┌─────────────┐              │
│   MOVIE     │       │    SHOW     │              │
├─────────────┤       ├─────────────┤              │
│ id (PK)     │──1:N──│ id (PK)     │              │
│ title       │       │ movie_id(FK)│              │
│ duration    │       │ hall_id (FK)│              │
│ genre       │       │ start_time  │              │
│ rating      │       │ price       │              │
└─────────────┘       └──────┬──────┘              │
                             │                     │
                             │ N:1                 │
                             ▼                     ▼
                      ┌────────────────────────────────┐
                      │           BOOKING              │
                      ├────────────────────────────────┤
                      │ id (PK)                        │
                      │ show_id (FK)                   │
                      │ seat_id (FK)                   │
                      │ user_id (FK, optional)         │
                      │ status (LOCKED/BOOKED)         │
                      │ locked_until (timestamp)       │
                      │ created_at                     │
                      │                                │
                      │ UNIQUE(show_id, seat_id) ←     │
                      │ Prevents double booking!       │
                      └────────────────────────────────┘
```

### Table Relationships

| Parent | Child | Relationship |
|--------|-------|--------------|
| Venue | Hall | 1:N (venue has many halls) |
| Hall | Seat | 1:N (hall has many seats) |
| Hall | Show | 1:N (hall hosts many shows) |
| Movie | Show | 1:N (movie has many shows) |
| Show + Seat | Booking | N:1 (unique per show-seat pair) |

---

## Decision Log

### Why Pessimistic Locking?

I chose **Pessimistic Locking** (`SELECT FOR UPDATE`) because:

1. **High contention scenario**: Movie bookings have many users competing for the same popular seats, especially during releases. Pessimistic locking prevents conflicts before they happen.

2. **Simplicity**: Django provides built-in `select_for_update()` which makes implementation straightforward. No need for version fields or retry logic.

3. **Guaranteed consistency**: The database handles all waiting and conflict resolution. It's impossible for two users to book the same seat.

4. **Better UX**: Users either get the seat or immediately see an error. No silent failures or "your booking was overwritten" scenarios.

### Trade-off Considered

Optimistic locking would be better for low-contention scenarios (like editing user profiles) where conflicts are rare. But for ticket booking where 100+ users might click on the same seat at the same time, pessimistic locking is the safer choice.

---

## Seat State Machine

```
    ┌─────────────┐
    │  AVAILABLE  │ ← No booking record exists
    └──────┬──────┘
           │ User selects seat
           ▼
    ┌─────────────┐
    │   LOCKED    │ ← status='LOCKED', locked_until set
    │  (5 mins)   │
    └──────┬──────┘
           │
    ┌──────┴──────┐
    │             │
Payment OK    Cancel/Timeout
    │             │
    ▼             ▼
┌─────────┐  ┌─────────────┐
│ BOOKED  │  │  AVAILABLE  │
│(final)  │  │(lock deleted)│
└─────────┘  └─────────────┘
```
