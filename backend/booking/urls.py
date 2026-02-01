"""
URL configuration for booking app.
API endpoints for the ticketing system.
"""
from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Seat layout API - GET /api/hall-layout/{show_id}/
    path('hall-layout/<int:show_id>/', views.hall_layout, name='hall-layout'),
    
    # Booking API - POST /api/book-seat/
    path('book-seat/', views.book_seat, name='book-seat'),
    
    # Lock seat API - POST /api/lock-seat/
    path('lock-seat/', views.lock_seat, name='lock-seat'),
    
    # Release lock API - POST /api/release-lock/
    path('release-lock/', views.release_lock, name='release-lock'),
    
    # List shows - GET /api/shows/
    path('shows/', views.shows_list, name='shows-list'),
]
