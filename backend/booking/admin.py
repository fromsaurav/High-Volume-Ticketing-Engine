"""
Admin configuration for the Ticketing Engine.
Provides a nice interface to manage venues, halls, movies, shows, and bookings.
"""

from django.contrib import admin
from .models import Venue, Hall, Seat, Movie, Show, Booking


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'created_at']
    search_fields = ['name', 'city']
    list_filter = ['city']


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ['name', 'venue', 'hall_type', 'total_rows', 'seats_per_row', 'capacity']
    list_filter = ['hall_type', 'venue']
    search_fields = ['name', 'venue__name']


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ['id', 'hall', 'row', 'number', 'seat_type', 'is_active']
    list_filter = ['seat_type', 'is_active', 'hall']
    search_fields = ['hall__name', 'row']


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ['title', 'duration_minutes', 'genre', 'rating', 'release_date', 'is_active']
    list_filter = ['rating', 'genre', 'is_active']
    search_fields = ['title']
    date_hierarchy = 'release_date'


@admin.register(Show)
class ShowAdmin(admin.ModelAdmin):
    list_display = ['movie', 'hall', 'start_time', 'price', 'is_active']
    list_filter = ['is_active', 'hall__venue', 'movie']
    search_fields = ['movie__title', 'hall__name']
    date_hierarchy = 'start_time'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['id', 'show', 'seat', 'user', 'status', 'locked_until', 'created_at']
    list_filter = ['status', 'show__movie']
    search_fields = ['show__movie__title', 'seat__row']
    raw_id_fields = ['show', 'seat', 'user']
