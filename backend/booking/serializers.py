"""
Serializers for the Ticketing API.

These handle data validation and JSON formatting for API responses.
"""

from rest_framework import serializers
from .models import Venue, Hall, Seat, Movie, Show, Booking


class VenueSerializer(serializers.ModelSerializer):
    """Serializer for Venue model."""
    class Meta:
        model = Venue
        fields = ['id', 'name', 'address', 'city']


class SeatSerializer(serializers.ModelSerializer):
    """Serializer for individual Seat."""
    status = serializers.SerializerMethodField()

    class Meta:
        model = Seat
        fields = ['id', 'row', 'number', 'seat_type', 'status']

    def get_status(self, obj):
        """
        Get seat status for the current show.
        Status is determined by checking bookings for this show.
        """
        show_id = self.context.get('show_id')
        if not show_id:
            return 'AVAILABLE'
        return Booking.get_seat_status(show_id, obj.id)


class HallSerializer(serializers.ModelSerializer):
    """Serializer for Hall with venue info."""
    venue_name = serializers.CharField(source='venue.name', read_only=True)

    class Meta:
        model = Hall
        fields = ['id', 'name', 'hall_type', 'venue_name', 'total_rows', 'seats_per_row']


class MovieSerializer(serializers.ModelSerializer):
    """Serializer for Movie details."""
    class Meta:
        model = Movie
        fields = ['id', 'title', 'description', 'duration_minutes', 'genre', 'rating', 'poster_url']


class ShowSerializer(serializers.ModelSerializer):
    """Serializer for Show with nested movie and hall info."""
    movie = MovieSerializer(read_only=True)
    hall = HallSerializer(read_only=True)

    class Meta:
        model = Show
        fields = ['id', 'movie', 'hall', 'start_time', 'end_time', 'price']


class HallLayoutSerializer(serializers.Serializer):
    """
    Serializer for the hall layout response.
    Returns seat grid with real-time availability.
    """
    show_id = serializers.IntegerField()
    movie_title = serializers.CharField()
    hall_name = serializers.CharField()
    venue_name = serializers.CharField()
    start_time = serializers.DateTimeField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_rows = serializers.IntegerField()
    seats_per_row = serializers.IntegerField()
    seats = SeatSerializer(many=True)


class BookingRequestSerializer(serializers.Serializer):
    """
    Serializer for booking request validation.
    Used for POST /book-seat/
    """
    seat_id = serializers.IntegerField()
    show_id = serializers.IntegerField()
    user_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, data):
        """Validate that seat and show exist."""
        from .models import Seat, Show
        
        try:
            Seat.objects.get(id=data['seat_id'])
        except Seat.DoesNotExist:
            raise serializers.ValidationError({"seat_id": "Seat not found"})

        try:
            Show.objects.get(id=data['show_id'])
        except Show.DoesNotExist:
            raise serializers.ValidationError({"show_id": "Show not found"})

        return data


class BookingResponseSerializer(serializers.ModelSerializer):
    """Serializer for booking response."""
    seat_info = serializers.SerializerMethodField()
    show_info = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'status', 'seat_info', 'show_info', 'created_at']

    def get_seat_info(self, obj):
        return f"{obj.seat.row}{obj.seat.number}"

    def get_show_info(self, obj):
        return f"{obj.show.movie.title} at {obj.show.start_time.strftime('%H:%M')}"


class BookingSummarySerializer(serializers.Serializer):
    """Serializer for booking success/failure response."""
    status = serializers.CharField()
    message = serializers.CharField()
    booking_id = serializers.IntegerField(required=False)
    seat = serializers.CharField(required=False)
