"""
Management command to seed the database with sample data.

Usage:
    python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from booking.models import Venue, Hall, Seat, Movie, Show, Booking


class Command(BaseCommand):
    help = 'Seed database with sample venue, hall, seats, movie, and shows'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

        # Delete old shows and bookings (start fresh each time)
        old_shows = Show.objects.count()
        old_bookings = Booking.objects.count()
        Booking.objects.all().delete()
        Show.objects.all().delete()
        self.stdout.write(f'Cleared {old_shows} old shows and {old_bookings} bookings')

        # Create Venue
        venue, created = Venue.objects.get_or_create(
            name='PVR Phoenix',
            defaults={
                'address': 'Phoenix Mall, Lower Parel',
                'city': 'Mumbai'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created venue: {venue.name}'))
        else:
            self.stdout.write(f'Venue already exists: {venue.name}')

        # Create Hall
        hall, created = Hall.objects.get_or_create(
            venue=venue,
            name='Screen 1',
            defaults={
                'hall_type': 'REGULAR',
                'total_rows': 8,
                'seats_per_row': 12
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created hall: {hall.name}'))
        else:
            self.stdout.write(f'Hall already exists: {hall.name}')

        # Create Seats (8 rows x 12 seats)
        rows = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        seats_created = 0
        
        for row in rows:
            for num in range(1, 13):  # 12 seats per row
                # Last 2 rows are premium
                seat_type = 'PREMIUM' if row in ['G', 'H'] else 'REGULAR'
                
                seat, created = Seat.objects.get_or_create(
                    hall=hall,
                    row=row,
                    number=num,
                    defaults={'seat_type': seat_type}
                )
                if created:
                    seats_created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {seats_created} seats'))

        # Create Movies (5 movies)
        movies_data = [
            {
                'title': 'Avengers: Endgame',
                'description': 'The epic conclusion to the Infinity Saga.',
                'duration_minutes': 181,
                'genre': 'Action/Sci-Fi',
                'rating': 'UA',
                'release_date': '2024-01-15'
            },
            {
                'title': 'Dune: Part Two',
                'description': 'Paul Atreides unites with Chani and the Fremen.',
                'duration_minutes': 166,
                'genre': 'Sci-Fi/Adventure',
                'rating': 'UA',
                'release_date': '2024-02-01'
            },
            {
                'title': 'Oppenheimer',
                'description': 'The story of J. Robert Oppenheimer and the atomic bomb.',
                'duration_minutes': 180,
                'genre': 'Biography/Drama',
                'rating': 'A',
                'release_date': '2023-07-21'
            },
            {
                'title': 'Spider-Man: No Way Home',
                'description': 'Peter Parker seeks Doctor Strange\'s help to restore his secret identity.',
                'duration_minutes': 148,
                'genre': 'Action/Adventure',
                'rating': 'UA',
                'release_date': '2021-12-17'
            },
            {
                'title': 'Interstellar',
                'description': 'A team of explorers travel through a wormhole in space.',
                'duration_minutes': 169,
                'genre': 'Sci-Fi/Drama',
                'rating': 'UA',
                'release_date': '2014-11-07'
            },
        ]

        movies = []
        for movie_data in movies_data:
            movie, created = Movie.objects.get_or_create(
                title=movie_data['title'],
                defaults=movie_data
            )
            movies.append(movie)
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created movie: {movie.title}'))
            else:
                self.stdout.write(f'Movie already exists: {movie.title}')

        # Create Shows - different times and prices for each movie
        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Show schedule with varied times and prices
        show_schedule = [
            # Avengers shows
            {'movie': movies[0], 'time': today + timedelta(hours=21, minutes=0), 'price': 350.00},   # 9:00 PM
            {'movie': movies[0], 'time': today + timedelta(hours=23, minutes=30), 'price': 300.00},  # 11:30 PM
            # Dune shows  
            {'movie': movies[1], 'time': today + timedelta(hours=21, minutes=30), 'price': 320.00},  # 9:30 PM
            {'movie': movies[1], 'time': today + timedelta(hours=23, minutes=0), 'price': 280.00},   # 11:00 PM
            # Oppenheimer shows
            {'movie': movies[2], 'time': today + timedelta(hours=22, minutes=0), 'price': 400.00},   # 10:00 PM
            # Spider-Man shows
            {'movie': movies[3], 'time': today + timedelta(hours=21, minutes=15), 'price': 300.00},  # 9:15 PM
            {'movie': movies[3], 'time': today + timedelta(hours=23, minutes=45), 'price': 250.00},  # 11:45 PM
            # Interstellar shows
            {'movie': movies[4], 'time': today + timedelta(hours=22, minutes=30), 'price': 350.00},  # 10:30 PM
        ]

        shows_created = 0
        for schedule in show_schedule:
            show = Show.objects.create(
                movie=schedule['movie'],
                hall=hall,
                start_time=schedule['time'],
                price=schedule['price']
            )
            shows_created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {shows_created} shows'))
        self.stdout.write(self.style.SUCCESS('Database seeding complete!'))
        
        # Print summary
        self.stdout.write('\n--- SUMMARY ---')
        self.stdout.write(f'Venues: {Venue.objects.count()}')
        self.stdout.write(f'Halls: {Hall.objects.count()}')
        self.stdout.write(f'Seats: {Seat.objects.count()}')
        self.stdout.write(f'Movies: {Movie.objects.count()}')
        self.stdout.write(f'Shows: {Show.objects.count()}')
        
        # Print show IDs for testing
        self.stdout.write('\n--- SHOWS FOR TESTING ---')
        for show in Show.objects.all().order_by('start_time'):
            self.stdout.write(f'  Show ID {show.id}: {show.movie.title} at {show.start_time.strftime("%H:%M")} - ₹{show.price}')
