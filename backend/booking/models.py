"""
Models for the High-Volume Ticketing Engine.

Entities:
- Venue: Theatre building (e.g., "PVR Phoenix Mall")
- Hall: Individual screen (e.g., "Screen 1", "IMAX")
- Seat: Physical seat in a hall
- Movie: Film information
- Show: A specific screening (movie + hall + time)
- Booking: User's seat reservation for a show
"""

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class Venue(models.Model):
    """Theatre building that contains multiple halls."""
    name = models.CharField(max_length=200)
    address = models.TextField()
    city = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.city}"


class Hall(models.Model):
    """Individual screen/room within a venue."""
    HALL_TYPES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('IMAX', 'IMAX'),
        ('4DX', '4DX'),
    ]

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name='halls')
    name = models.CharField(max_length=100)  # e.g., "Screen 1", "IMAX Hall"
    hall_type = models.CharField(max_length=20, choices=HALL_TYPES, default='REGULAR')
    total_rows = models.PositiveIntegerField(default=10)
    seats_per_row = models.PositiveIntegerField(default=15)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['venue', 'name']
        ordering = ['venue', 'name']

    def __str__(self):
        return f"{self.name} at {self.venue.name}"

    @property
    def capacity(self):
        return self.seats.count()


class Seat(models.Model):
    """Physical seat in a hall."""
    SEAT_TYPES = [
        ('REGULAR', 'Regular'),
        ('PREMIUM', 'Premium'),
        ('RECLINER', 'Recliner'),
        ('WHEELCHAIR', 'Wheelchair Accessible'),
    ]

    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='seats')
    row = models.CharField(max_length=5)  # A, B, C, ... or AA, AB
    number = models.PositiveIntegerField()  # 1, 2, 3, ...
    seat_type = models.CharField(max_length=20, choices=SEAT_TYPES, default='REGULAR')
    is_active = models.BooleanField(default=True)  # Can disable broken seats

    class Meta:
        unique_together = ['hall', 'row', 'number']
        ordering = ['row', 'number']
        indexes = [
            models.Index(fields=['hall', 'row', 'number']),
        ]

    def __str__(self):
        return f"{self.row}{self.number} ({self.hall.name})"


class Movie(models.Model):
    """Film information."""
    RATINGS = [
        ('U', 'U - Universal'),
        ('UA', 'UA - Parental Guidance'),
        ('A', 'A - Adults Only'),
    ]

    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    duration_minutes = models.PositiveIntegerField()  # Runtime in minutes
    genre = models.CharField(max_length=100)
    rating = models.CharField(max_length=5, choices=RATINGS, default='UA')
    poster_url = models.URLField(blank=True, null=True)
    release_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-release_date', 'title']

    def __str__(self):
        return f"{self.title} ({self.release_date.year})"


class Show(models.Model):
    """A specific screening - links Movie to Hall at a specific time."""
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name='shows')
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name='shows')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_time']
        indexes = [
            models.Index(fields=['start_time']),
            models.Index(fields=['hall', 'start_time']),
        ]

    def save(self, *args, **kwargs):
        # Auto-calculate end time based on movie duration
        if not self.end_time and self.movie:
            self.end_time = self.start_time + timedelta(minutes=self.movie.duration_minutes)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.movie.title} at {self.hall.name} - {self.start_time.strftime('%Y-%m-%d %H:%M')}"


class Booking(models.Model):
    """
    User's seat reservation for a show.
    
    This is where seat status per show lives!
    A seat can be:
    - AVAILABLE: No booking record exists
    - LOCKED: status='LOCKED' and locked_until > now()
    - BOOKED: status='BOOKED'
    """
    STATUS_CHOICES = [
        ('LOCKED', 'Locked'),    # Temporary hold during payment
        ('BOOKED', 'Booked'),    # Confirmed booking
        ('CANCELLED', 'Cancelled'),
    ]

    # Core relationships
    show = models.ForeignKey(Show, on_delete=models.CASCADE, related_name='bookings')
    seat = models.ForeignKey(Seat, on_delete=models.CASCADE, related_name='bookings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings', null=True, blank=True)

    # Status and locking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='LOCKED')
    locked_until = models.DateTimeField(null=True, blank=True)  # For temporary holds

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # CRITICAL: Ensures one booking per seat per show
        unique_together = ['show', 'seat']
        indexes = [
            models.Index(fields=['show', 'seat']),
            models.Index(fields=['status']),
            models.Index(fields=['locked_until']),
        ]

    def __str__(self):
        return f"{self.seat} for {self.show} - {self.status}"

    def is_lock_expired(self):
        """Check if the lock has expired."""
        if self.status != 'LOCKED':
            return False
        if self.locked_until is None:
            return True
        return timezone.now() > self.locked_until

    def is_available(self):
        """Check if this booking slot is effectively available."""
        if self.status == 'CANCELLED':
            return True
        if self.status == 'LOCKED' and self.is_lock_expired():
            return True
        return False

    @classmethod
    def get_seat_status(cls, show_id, seat_id):
        """
        Get the effective status of a seat for a show.
        Returns: 'AVAILABLE', 'LOCKED', or 'BOOKED'
        """
        try:
            booking = cls.objects.get(show_id=show_id, seat_id=seat_id)
            if booking.status == 'BOOKED':
                return 'BOOKED'
            if booking.status == 'LOCKED' and not booking.is_lock_expired():
                return 'LOCKED'
            return 'AVAILABLE'
        except cls.DoesNotExist:
            return 'AVAILABLE'

    @classmethod  
    def lock_seat(cls, show_id, seat_id, user=None, lock_duration_minutes=5):
        """
        Attempt to lock a seat for payment.
        Returns the booking if successful, None if seat is not available.
        """
        locked_until = timezone.now() + timedelta(minutes=lock_duration_minutes)
        
        # Check for existing booking
        existing = cls.objects.filter(show_id=show_id, seat_id=seat_id).first()
        
        if existing:
            if existing.status == 'BOOKED':
                return None  # Already booked
            if existing.status == 'LOCKED' and not existing.is_lock_expired():
                return None  # Locked by someone else
            # Lock expired or cancelled - update it
            existing.status = 'LOCKED'
            existing.user = user
            existing.locked_until = locked_until
            existing.save()
            return existing
        
        # Create new lock
        return cls.objects.create(
            show_id=show_id,
            seat_id=seat_id,
            user=user,
            status='LOCKED',
            locked_until=locked_until
        )

    def confirm_booking(self):
        """Convert a locked seat to a confirmed booking."""
        if self.status != 'LOCKED':
            return False
        self.status = 'BOOKED'
        self.locked_until = None
        self.save()
        return True
