"""
Management command to seed the database with sample data.

Usage:
    python manage.py seed_data
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from booking.models import Venue, Hall, Seat, Movie, Show


class Command(BaseCommand):
    help = 'Seed database with sample venue, hall, seats, movie, and shows'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')

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

        # Create Movies
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

        # Create Shows for today and tomorrow
        now = timezone.now()
        today = now.replace(hour=19, minute=0, second=0, microsecond=0)
        
        show_times = [
            today,                                    # 7 PM today
            today + timedelta(hours=3),               # 10 PM today
            today + timedelta(days=1),                # 7 PM tomorrow
            today + timedelta(days=1, hours=3),       # 10 PM tomorrow
        ]

        shows_created = 0
        for movie in movies:
            for show_time in show_times[:2]:  # 2 shows per movie
                show, created = Show.objects.get_or_create(
                    movie=movie,
                    hall=hall,
                    start_time=show_time,
                    defaults={'price': 350.00}
                )
                if created:
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
        for show in Show.objects.all()[:4]:
            self.stdout.write(f'  Show ID {show.id}: {show.movie.title} at {show.start_time.strftime("%Y-%m-%d %H:%M")}')
