"""
API Views for the Ticketing Engine.

Implements:
- GET /api/hall-layout/{show_id}/ - Get seat map with real-time availability
- POST /api/book-seat/ - Book a seat with pessimistic locking
"""

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from .models import Show, Seat, Booking
from .serializers import (
    HallLayoutSerializer,
    SeatSerializer,
    BookingRequestSerializer,
    BookingSummarySerializer,
)


@api_view(['GET'])
def hall_layout(request, show_id):
    """
    GET /api/hall-layout/{show_id}/
    
    Returns the seat layout for a specific show with real-time seat status.
    Optimized to avoid N+1 queries.
    
    Response:
    {
        "show_id": 1,
        "movie_title": "Avengers: Endgame",
        "hall_name": "Screen 1",
        "venue_name": "PVR Phoenix",
        "start_time": "2024-02-01T19:00:00Z",
        "price": "350.00",
        "total_rows": 10,
        "seats_per_row": 15,
        "seats": [
            {"id": 1, "row": "A", "number": 1, "seat_type": "REGULAR", "status": "AVAILABLE"},
            {"id": 2, "row": "A", "number": 2, "seat_type": "REGULAR", "status": "BOOKED"},
            ...
        ]
    }
    """
    # Get show with related data in one query
    show = get_object_or_404(
        Show.objects.select_related('movie', 'hall', 'hall__venue'),
        id=show_id,
        is_active=True
    )
    
    # Get all seats for this hall
    seats = Seat.objects.filter(
        hall=show.hall,
        is_active=True
    ).order_by('row', 'number')
    
    # Get all bookings for this show (single query)
    bookings = {
        b.seat_id: b 
        for b in Booking.objects.filter(show=show)
    }
    
    # Build seat data with status
    seat_data = []
    now = timezone.now()
    
    for seat in seats:
        booking = bookings.get(seat.id)
        
        if booking is None:
            seat_status = 'AVAILABLE'
        elif booking.status == 'BOOKED':
            seat_status = 'BOOKED'
        elif booking.status == 'LOCKED':
            # Check if lock expired
            if booking.locked_until and booking.locked_until > now:
                seat_status = 'LOCKED'
            else:
                seat_status = 'AVAILABLE'
        elif booking.status == 'CANCELLED':
            seat_status = 'AVAILABLE'
        else:
            seat_status = 'AVAILABLE'
        
        seat_data.append({
            'id': seat.id,
            'row': seat.row,
            'number': seat.number,
            'seat_type': seat.seat_type,
            'status': seat_status,
        })
    
    response_data = {
        'show_id': show.id,
        'movie_title': show.movie.title,
        'hall_name': show.hall.name,
        'venue_name': show.hall.venue.name,
        'start_time': show.start_time,
        'price': str(show.price),
        'total_rows': show.hall.total_rows,
        'seats_per_row': show.hall.seats_per_row,
        'seats': seat_data,
    }
    
    return Response(response_data)


@api_view(['POST'])
def book_seat(request):
    """
    POST /api/book-seat/
    
    Book a seat with PESSIMISTIC LOCKING to prevent race conditions.
    
    Request Body:
    {
        "seat_id": 42,
        "show_id": 1,
        "user_id": 123  // optional
    }
    
    Success Response (200):
    {
        "status": "success",
        "message": "Seat booked successfully",
        "booking_id": 789,
        "seat": "A1"
    }
    
    Failure Response (409 Conflict):
    {
        "status": "error",
        "message": "Seat is already booked by another user"
    }
    
    CONCURRENCY STRATEGY:
    Uses Django's select_for_update() to acquire a row-level lock.
    This ensures only one transaction can modify the seat at a time.
    """
    # Validate input
    serializer = BookingRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {'status': 'error', 'message': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    seat_id = serializer.validated_data['seat_id']
    show_id = serializer.validated_data['show_id']
    user_id = serializer.validated_data.get('user_id')
    
    try:
        # CRITICAL: Use atomic transaction with row-level locking
        with transaction.atomic():
            # Lock the seat row to prevent concurrent modifications
            # This is the PESSIMISTIC LOCKING strategy
            seat = Seat.objects.select_for_update().get(id=seat_id)
            
            # Check for existing booking
            now = timezone.now()
            existing_booking = Booking.objects.filter(
                show_id=show_id,
                seat_id=seat_id
            ).first()
            
            if existing_booking:
                if existing_booking.status == 'BOOKED':
                    # Already booked - cannot proceed
                    return Response(
                        {
                            'status': 'error',
                            'message': 'Seat is already booked by another user'
                        },
                        status=status.HTTP_409_CONFLICT
                    )
                
                # If seat is LOCKED (on hold), allow converting to BOOKED
                # This handles the payment flow: lock -> pay -> book
                # The lock is converted to a confirmed booking
                existing_booking.status = 'BOOKED'
                existing_booking.user_id = user_id
                existing_booking.locked_until = None
                existing_booking.save()
                booking = existing_booking
            else:
                # Create new booking
                booking = Booking.objects.create(
                    show_id=show_id,
                    seat_id=seat_id,
                    user_id=user_id,
                    status='BOOKED',
                    locked_until=None
                )
            
            return Response({
                'status': 'success',
                'message': 'Seat booked successfully',
                'booking_id': booking.id,
                'seat': f"{seat.row}{seat.number}"
            })
            
    except Seat.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Seat not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def lock_seat(request):
    """
    POST /api/lock-seat/
    
    Temporarily lock a seat (5-minute hold during payment).
    This is called when user selects a seat before payment.
    
    Request Body:
    {
        "seat_id": 42,
        "show_id": 1
    }
    """
    seat_id = request.data.get('seat_id')
    show_id = request.data.get('show_id')
    
    if not seat_id or not show_id:
        return Response(
            {'status': 'error', 'message': 'seat_id and show_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            seat = Seat.objects.select_for_update().get(id=seat_id)
            
            now = timezone.now()
            lock_duration = timedelta(minutes=5)
            locked_until = now + lock_duration
            
            existing_booking = Booking.objects.filter(
                show_id=show_id,
                seat_id=seat_id
            ).first()
            
            if existing_booking:
                if existing_booking.status == 'BOOKED':
                    return Response(
                        {'status': 'error', 'message': 'Seat is already booked'},
                        status=status.HTTP_409_CONFLICT
                    )
                
                if (existing_booking.status == 'LOCKED' and 
                    existing_booking.locked_until and 
                    existing_booking.locked_until > now):
                    return Response(
                        {'status': 'error', 'message': 'Seat is held by another user'},
                        status=status.HTTP_409_CONFLICT
                    )
                
                # Take over expired lock
                existing_booking.status = 'LOCKED'
                existing_booking.locked_until = locked_until
                existing_booking.save()
                booking = existing_booking
            else:
                booking = Booking.objects.create(
                    show_id=show_id,
                    seat_id=seat_id,
                    status='LOCKED',
                    locked_until=locked_until
                )
            
            return Response({
                'status': 'success',
                'message': 'Seat locked for 5 minutes',
                'booking_id': booking.id,
                'locked_until': locked_until.isoformat()
            })
            
    except Seat.DoesNotExist:
        return Response(
            {'status': 'error', 'message': 'Seat not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['GET'])
def shows_list(request):
    """
    GET /api/shows/
    
    List all active shows.
    """
    shows = Show.objects.filter(
        is_active=True,
        start_time__gte=timezone.now()
    ).select_related('movie', 'hall', 'hall__venue').order_by('start_time')
    
    data = []
    for show in shows:
        data.append({
            'id': show.id,
            'movie_title': show.movie.title,
            'movie_poster': show.movie.poster_url,
            'hall_name': show.hall.name,
            'venue_name': show.hall.venue.name,
            'start_time': show.start_time,
            'price': str(show.price),
        })
    
    return Response(data)


@api_view(['POST'])
def release_lock(request):
    """
    POST /api/release-lock/
    
    Release a seat lock when user cancels payment.
    This immediately frees the seat for other users.
    
    Request Body:
    {
        "seat_id": 42,
        "show_id": 1
    }
    """
    seat_id = request.data.get('seat_id')
    show_id = request.data.get('show_id')
    
    if not seat_id or not show_id:
        return Response(
            {'status': 'error', 'message': 'seat_id and show_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        with transaction.atomic():
            booking = Booking.objects.filter(
                show_id=show_id,
                seat_id=seat_id,
                status='LOCKED'
            ).first()
            
            if booking:
                # Delete the lock record to make seat available
                booking.delete()
                return Response({
                    'status': 'success',
                    'message': 'Seat lock released'
                })
            else:
                return Response({
                    'status': 'success',
                    'message': 'No lock found to release'
                })
                
    except Exception as e:
        return Response(
            {'status': 'error', 'message': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
