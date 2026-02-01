import { useState, useEffect, useCallback } from 'react'
import './App.css'

const API_BASE = 'http://localhost:8000/api';

function App() {
  const [shows, setShows] = useState([]);
  const [selectedShow, setSelectedShow] = useState(null);
  const [hallLayout, setHallLayout] = useState(null);
  const [selectedSeats, setSelectedSeats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [bookingInProgress, setBookingInProgress] = useState(false);

  // Payment flow state
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentStep, setPaymentStep] = useState('confirm'); // confirm, processing, success, failed
  const [lockedBookingIds, setLockedBookingIds] = useState([]);
  const [lockTimer, setLockTimer] = useState(300); // 5 minutes in seconds
  const [paymentSeats, setPaymentSeats] = useState([]); // Store seats during payment
  const [paymentAmount, setPaymentAmount] = useState(0); // Store amount during payment

  // Fetch shows list
  useEffect(() => {
    fetch(`${API_BASE}/shows/`)
      .then(res => res.json())
      .then(data => {
        setShows(data);
        if (data.length > 0) {
          setSelectedShow(data[0].id);
        }
      })
      .catch(err => console.error('Error fetching shows:', err));
  }, []);

  // Fetch hall layout when show is selected
  const fetchLayout = useCallback(() => {
    if (!selectedShow) return;

    setLoading(true);
    fetch(`${API_BASE}/hall-layout/${selectedShow}/`)
      .then(res => res.json())
      .then(data => {
        setHallLayout(data);
        // Only clear selection if not in payment modal
        if (!showPaymentModal) {
          setSelectedSeats([]);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error('Error fetching layout:', err);
        setLoading(false);
      });
  }, [selectedShow, showPaymentModal]);

  useEffect(() => {
    fetchLayout();
  }, [fetchLayout]);

  // Lock timer countdown
  useEffect(() => {
    let interval;
    if (showPaymentModal && paymentStep === 'confirm' && lockTimer > 0) {
      interval = setInterval(() => {
        setLockTimer(prev => {
          if (prev <= 1) {
            // Lock expired
            setMessage({ type: 'error', text: 'Payment time expired! Your seat hold has been released.' });
            setShowPaymentModal(false);
            setSelectedSeats([]);
            setPaymentSeats([]);
            fetchLayout();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [showPaymentModal, paymentStep, lockTimer, fetchLayout]);

  // Handle seat selection
  const handleSeatClick = (seat) => {
    if (seat.status === 'BOOKED') {
      setMessage({ type: 'error', text: 'This seat is already booked!' });
      return;
    }
    if (seat.status === 'LOCKED') {
      setMessage({ type: 'warning', text: 'This seat is on hold by another user. Please click Refresh to see the latest status.' });
      return;
    }

    setSelectedSeats(prev => {
      const isSelected = prev.find(s => s.id === seat.id);
      if (isSelected) {
        return prev.filter(s => s.id !== seat.id);
      }
      return [...prev, seat];
    });
    setMessage(null);
  };

  // Initiate payment - Lock seats first
  const handleProceedToPayment = async () => {
    if (selectedSeats.length === 0) {
      setMessage({ type: 'error', text: 'Please select at least one seat' });
      return;
    }

    setBookingInProgress(true);
    const lockResults = [];

    // Lock each seat
    for (const seat of selectedSeats) {
      try {
        const response = await fetch(`${API_BASE}/lock-seat/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            seat_id: seat.id,
            show_id: selectedShow
          })
        });
        const data = await response.json();
        lockResults.push({ seat, ...data });
      } catch (err) {
        lockResults.push({ seat, status: 'error', message: 'Network error' });
      }
    }

    const successful = lockResults.filter(r => r.status === 'success');
    const failed = lockResults.filter(r => r.status === 'error');

    if (failed.length > 0) {
      setMessage({
        type: 'error',
        text: `Could not hold seat(s): ${failed.map(f => `${f.seat.row}${f.seat.number}`).join(', ')}. ${failed[0].message}. Please refresh and try again.`
      });
      setBookingInProgress(false);
      fetchLayout();
      return;
    }

    // All seats locked successfully - store payment info BEFORE refreshing
    const seatsForPayment = [...selectedSeats];
    const amountForPayment = selectedSeats.length * (hallLayout ? parseFloat(hallLayout.price) : 0);

    setPaymentSeats(seatsForPayment);
    setPaymentAmount(amountForPayment);
    setLockedBookingIds(successful.map(s => s.booking_id));
    setLockTimer(300); // 5 minutes
    setPaymentStep('confirm');
    setShowPaymentModal(true);
    setBookingInProgress(false);

    // Refresh to show locked status
    fetchLayout();
  };

  // Simulate payment processing
  const handleConfirmPayment = async () => {
    setPaymentStep('processing');

    // Simulate payment processing (2 seconds)
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Now confirm the booking
    const bookResults = [];
    for (const seat of paymentSeats) {
      try {
        const response = await fetch(`${API_BASE}/book-seat/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            seat_id: seat.id,
            show_id: selectedShow
          })
        });
        const data = await response.json();
        bookResults.push({ seat: `${seat.row}${seat.number}`, ...data });
      } catch (err) {
        bookResults.push({ seat: `${seat.row}${seat.number}`, status: 'error', message: 'Network error' });
      }
    }

    const successful = bookResults.filter(r => r.status === 'success');
    const failed = bookResults.filter(r => r.status === 'error');

    if (failed.length > 0) {
      setPaymentStep('failed');
    } else {
      setPaymentStep('success');
    }

    // Close modal after delay and show result
    setTimeout(() => {
      setShowPaymentModal(false);

      if (failed.length > 0) {
        setMessage({
          type: 'error',
          text: `Booking failed for: ${failed.map(f => f.seat).join(', ')}. ${failed[0].message}`
        });
      } else {
        setMessage({
          type: 'success',
          text: `🎉 Payment successful! Booked: ${successful.map(s => s.seat).join(', ')}`
        });
      }

      setSelectedSeats([]);
      setPaymentSeats([]);
      setLockedBookingIds([]);
      fetchLayout();
    }, 2000);
  };

  // Cancel payment - release all locked seats immediately
  const handleCancelPayment = async () => {
    // Release all locked seats
    for (const seat of paymentSeats) {
      try {
        await fetch(`${API_BASE}/release-lock/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            seat_id: seat.id,
            show_id: selectedShow
          })
        });
      } catch (err) {
        console.error('Error releasing lock:', err);
      }
    }

    setShowPaymentModal(false);
    setSelectedSeats([]);
    setPaymentSeats([]);
    setLockedBookingIds([]);
    setMessage({ type: 'info', text: 'Payment cancelled. Seats have been released.' });
    fetchLayout();
  };

  // Format timer
  const formatTimer = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Group seats by row
  const getSeatsByRow = () => {
    if (!hallLayout?.seats) return {};
    return hallLayout.seats.reduce((acc, seat) => {
      if (!acc[seat.row]) acc[seat.row] = [];
      acc[seat.row].push(seat);
      return acc;
    }, {});
  };

  // Get seat class based on status
  const getSeatClass = (seat) => {
    const isSelected = selectedSeats.find(s => s.id === seat.id);
    if (isSelected) return 'seat selected';
    if (seat.status === 'BOOKED') return 'seat booked';
    if (seat.status === 'LOCKED') return 'seat locked';
    if (seat.seat_type === 'PREMIUM') return 'seat available premium';
    return 'seat available';
  };

  const seatsByRow = getSeatsByRow();
  const totalAmount = selectedSeats.length * (hallLayout ? parseFloat(hallLayout.price) : 0);

  return (
    <div className="app">
      <header className="header">
        <h1>🎬 High-Volume Ticketing Engine</h1>
        <p className="subtitle">Select your seats for an amazing movie experience</p>
      </header>

      {/* Message - AT TOP */}
      {message && (
        <div className={`message ${message.type}`}>
          {message.text}
          <button className="close-message" onClick={() => setMessage(null)}>×</button>
        </div>
      )}

      {/* Show Selection */}
      <div className="show-selector">
        <label htmlFor="show-select">Select Show:</label>
        <select
          id="show-select"
          value={selectedShow || ''}
          onChange={(e) => setSelectedShow(Number(e.target.value))}
        >
          <option value="">-- Select a show --</option>
          {shows.map(show => (
            <option key={show.id} value={show.id}>
              {show.movie_title} - {show.hall_name} - ₹{show.price}
            </option>
          ))}
        </select>
        <button className="refresh-btn" onClick={fetchLayout}>🔄 Refresh</button>
      </div>

      {/* Loading State */}
      {loading && <div className="loading">Loading seat layout...</div>}

      {/* Hall Layout */}
      {hallLayout && !loading && (
        <div className="hall-container">
          <div className="movie-info">
            <h2>{hallLayout.movie_title}</h2>
            <p>{hallLayout.venue_name} • {hallLayout.hall_name} • ₹{hallLayout.price}</p>
          </div>

          {/* Screen */}
          <div className="screen-container">
            <div className="screen">SCREEN</div>
          </div>

          {/* Seats Grid */}
          <div className="seats-container">
            {Object.entries(seatsByRow).map(([row, seats]) => (
              <div key={row} className="seat-row">
                <span className="row-label">{row}</span>
                <div className="seats">
                  {seats.map(seat => (
                    <button
                      key={seat.id}
                      className={getSeatClass(seat)}
                      onClick={() => handleSeatClick(seat)}
                      disabled={seat.status === 'BOOKED'}
                      title={`${seat.row}${seat.number} - ${seat.status}`}
                    >
                      {seat.number}
                    </button>
                  ))}
                </div>
                <span className="row-label">{row}</span>
              </div>
            ))}
          </div>

          {/* Legend */}
          <div className="legend">
            <div className="legend-item">
              <span className="seat-icon available"></span>
              <span>Available</span>
            </div>
            <div className="legend-item">
              <span className="seat-icon premium"></span>
              <span>Premium</span>
            </div>
            <div className="legend-item">
              <span className="seat-icon selected"></span>
              <span>Selected</span>
            </div>
            <div className="legend-item">
              <span className="seat-icon booked"></span>
              <span>Booked</span>
            </div>
            <div className="legend-item">
              <span className="seat-icon locked"></span>
              <span>On Hold</span>
            </div>
          </div>

          {/* Booking Summary */}
          {selectedSeats.length > 0 && !showPaymentModal && (
            <div className="booking-summary">
              <p>
                <strong>Selected:</strong> {selectedSeats.map(s => `${s.row}${s.number}`).join(', ')}
              </p>
              <p>
                <strong>Total:</strong> ₹{totalAmount.toFixed(2)}
              </p>
              <button
                className="book-button"
                onClick={handleProceedToPayment}
                disabled={bookingInProgress}
              >
                {bookingInProgress ? 'Locking seats...' : `Proceed to Pay ₹${totalAmount.toFixed(2)}`}
              </button>
            </div>
          )}
        </div>
      )}

      {!selectedShow && !loading && (
        <div className="no-show-message">
          <p>Please select a show to view the seat layout</p>
        </div>
      )}

      {/* Payment Modal */}
      {showPaymentModal && (
        <div className="modal-overlay">
          <div className="payment-modal">
            {paymentStep === 'confirm' && (
              <>
                <h2>💳 Complete Payment</h2>
                <div className="timer-warning">
                  <span className="timer">⏱️ {formatTimer(lockTimer)}</span>
                  <span>Seats held for you</span>
                </div>
                <div className="payment-details">
                  <p><strong>Seats:</strong> {paymentSeats.map(s => `${s.row}${s.number}`).join(', ')}</p>
                  <p><strong>Show:</strong> {hallLayout?.movie_title}</p>
                  <p className="payment-amount"><strong>Amount:</strong> ₹{paymentAmount.toFixed(2)}</p>
                </div>
                <div className="payment-actions">
                  <button className="pay-btn" onClick={handleConfirmPayment}>
                    Confirm Payment ₹{paymentAmount.toFixed(2)}
                  </button>
                  <button className="cancel-btn" onClick={handleCancelPayment}>
                    Cancel
                  </button>
                </div>
              </>
            )}

            {paymentStep === 'processing' && (
              <div className="payment-processing">
                <div className="spinner"></div>
                <h2>Processing Payment...</h2>
                <p>Please wait while we confirm your booking</p>
              </div>
            )}

            {paymentStep === 'success' && (
              <div className="payment-result success">
                <div className="success-icon">✓</div>
                <h2>Payment Successful!</h2>
                <p>Your seats have been booked: {paymentSeats.map(s => `${s.row}${s.number}`).join(', ')}</p>
              </div>
            )}

            {paymentStep === 'failed' && (
              <div className="payment-result failed">
                <div className="failed-icon">✗</div>
                <h2>Payment Failed</h2>
                <p>Please try again</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>Built with Django REST Framework + PostgreSQL | Concurrency: Pessimistic Locking</p>
      </footer>
    </div>
  )
}

export default App
