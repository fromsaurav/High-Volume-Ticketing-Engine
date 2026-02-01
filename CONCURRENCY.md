# Concurrency Test Results

## 🎉 Test PASSED!

Sent 5 simultaneous requests to book the same seat. Only 1 succeeded, 4 were rejected.

```
============================================================
CONCURRENCY TEST: 5 Simultaneous Booking Requests
============================================================

Target: POST http://localhost:8000/api/book-seat/
Payload: seat_id=10, show_id=1

Sending 5 requests simultaneously...

------------------------------------------------------------
RESULTS:
------------------------------------------------------------
  Request #1: ❌ CONFLICT (63.51ms) - Seat is already booked by another user
  Request #2: ❌ CONFLICT (57.91ms) - Seat is already booked by another user
  Request #3: ✅ SUCCESS (51.47ms) - Seat booked successfully
  Request #4: ❌ CONFLICT (62.17ms) - Seat is already booked by another user
  Request #5: ❌ CONFLICT (60.22ms) - Seat is already booked by another user
------------------------------------------------------------

SUMMARY:
  ✅ Successful bookings: 1
  ❌ Rejected (conflict): 4
  Total requests: 5

🎉 TEST PASSED! Pessimistic locking is working correctly.
   Only 1 request succeeded, 4 were properly rejected.
============================================================
```

---

## Why 0 successes on re-run?

Once a seat is **BOOKED**, it stays booked forever (just like a real theatre!).

```
Run 1: Seat is AVAILABLE → 1 person books it → Now BOOKED
Run 2: Seat is BOOKED → Nobody can book it → 0 success
```

---

## Run Test Yourself

**Step 1: Reset the seat** (delete existing booking)
```bash
cd backend && source ../venv/bin/activate
python manage.py shell -c "from booking.models import Booking; Booking.objects.filter(seat_id=10, show_id=1).delete(); print('Seat 10 reset')"
```

**Step 2: Run the test**
```bash
python ../test_concurrency.py
```

**To test again:** Just repeat Step 1 and Step 2.

---

## Postman Testing

1. Reset seat using Django shell command above
2. Open 5 Postman tabs
3. Set all to `POST http://localhost:8000/api/book-seat/`
4. Body (raw JSON): `{"seat_id": 10, "show_id": 1}`
5. Click **Send All** at once
6. Only 1 should return `200 OK`, others get `409 Conflict`
