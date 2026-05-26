import pytest
from datetime import datetime, timedelta
from business_logic import (
    calculate_refund,
    register_user,
    authenticate_user,
    create_movie,
    create_showtime,
    delete_movie,
    is_showtime_full
)


# ─── FIXTURES ───────────────────────────────────────────────────

class MockRow(dict):
    """Mimics sqlite3.Row behavior."""
    def __getitem__(self, key):
        return super().__getitem__(key)


class MockDB:
    """Mock database for testing."""
    def __init__(self):
        self.users = {}
        self.movies = {}
        self.showtimes = {}
        self.seats = {}
        self.reservations = {}
        self._last_id = 0

    def _next_id(self):
        self._last_id += 1
        return self._last_id

    def execute(self, query, params=()):
        return MockCursor(self, query, params)

    def commit(self):
        pass


class MockCursor:
    def __init__(self, db, query, params):
        self.db = db
        self.query = query.strip().lower()
        self.params = params
        self.lastrowid = db._next_id()
        self._result = None
        self._process()

    def _process(self):
        db = self.db
        q = self.query
        p = self.params

        if 'select id from users where username' in q:
            username = p[0]
            match = next(
                (MockRow(u) for u in db.users.values() if u['username'] == username),
                None
            )
            self._result = match

        elif 'select * from users where username' in q:
            username = p[0]
            match = next(
                (MockRow(u) for u in db.users.values() if u['username'] == username),
                None
            )
            self._result = match

        elif 'insert into users' in q:
            uid = self.lastrowid
            db.users[uid] = {
                'id': uid,
                'username': p[0],
                'password_hash': p[1],
                'is_admin': 0
            }

        elif 'insert into movies' in q:
            mid = self.lastrowid
            db.movies[mid] = {
                'id': mid,
                'title': p[0],
                'description': p[1],
                'genre': p[2],
                'duration_minutes': p[3],
                'poster_url': p[4]
            }

        elif 'insert into showtimes' in q:
            sid = self.lastrowid
            db.showtimes[sid] = {
                'id': sid,
                'movie_id': p[0],
                'hall_name': p[1],
                'start_time': p[2],
                'total_seats': p[3]
            }

        elif 'insert into seats' in q:
            seat_id = self.lastrowid
            db.seats[seat_id] = {
                'id': seat_id,
                'showtime_id': p[0],
                'seat_number': p[1],
                'is_reserved': 0
            }

        elif 'select id from reservations where showtime_id' in q:
            self._result = None

        elif 'select * from movies where id' in q:
            mid = p[0]
            self._result = MockRow(db.movies[mid]) if mid in db.movies else None

        elif 'select total_seats from showtimes where id' in q:
            sid = p[0]
            st = db.showtimes.get(sid)
            self._result = MockRow({'total_seats': st['total_seats']}) if st else None

        elif 'select count(*) as count from seats where showtime_id' in q:
            sid = p[0]
            count = sum(
                1 for s in db.seats.values()
                if s['showtime_id'] == sid and s['is_reserved'] == 1
            )
            self._result = MockRow({'count': count})

        elif 'select id from reservations' in q:
            self._result = None

    def fetchone(self):
        return self._result

    def fetchall(self):
        return self._result or []


# ─── CALCULATE REFUND TESTS ─────────────────────────────────────

def test_refund_more_than_48_hours():
    """100% refund when cancelled more than 48 hours before showtime."""
    future_time = datetime.now() + timedelta(hours=72)
    refund = calculate_refund(100.0, future_time)
    assert refund == 100.0


def test_refund_between_24_and_48_hours():
    """50% refund when cancelled between 24 and 48 hours before showtime."""
    future_time = datetime.now() + timedelta(hours=36)
    refund = calculate_refund(100.0, future_time)
    assert refund == 50.0


def test_refund_less_than_24_hours():
    """No refund when cancelled less than 24 hours before showtime."""
    future_time = datetime.now() + timedelta(hours=10)
    refund = calculate_refund(100.0, future_time)
    assert refund == 0.0


def test_refund_exactly_48_hours():
    """Exactly 48 hours should give 50% refund."""
    future_time = datetime.now() + timedelta(hours=48)
    refund = calculate_refund(100.0, future_time)
    assert refund == 50.0


def test_refund_with_string_datetime():
    """calculate_refund should handle string datetime format."""
    future_time = (datetime.now() + timedelta(hours=72)).strftime('%Y-%m-%d %H:%M:%S')
    refund = calculate_refund(100.0, future_time)
    assert refund == 100.0


# ─── REGISTER USER TESTS ────────────────────────────────────────

def test_register_user_success():
    """Successful registration returns None."""
    db = MockDB()
    error = register_user(db, 'testuser', 'password123')
    assert error is None


def test_register_user_empty_username():
    """Empty username returns error."""
    db = MockDB()
    error = register_user(db, '', 'password123')
    assert error is not None


def test_register_user_short_password():
    """Password shorter than 6 characters returns error."""
    db = MockDB()
    error = register_user(db, 'testuser', '123')
    assert error is not None


def test_register_user_duplicate_username():
    """Duplicate username returns error."""
    db = MockDB()
    register_user(db, 'testuser', 'password123')
    error = register_user(db, 'testuser', 'password456')
    assert error is not None


# ─── CREATE MOVIE TESTS ─────────────────────────────────────────

def test_create_movie_success():
    """Valid movie creation returns None."""
    db = MockDB()
    error = create_movie(db, 'Inception', 'A dream movie', 'Sci-Fi', 148, '')
    assert error is None


def test_create_movie_missing_title():
    """Missing title returns error."""
    db = MockDB()
    error = create_movie(db, '', 'A dream movie', 'Sci-Fi', 148, '')
    assert error is not None


def test_create_movie_invalid_duration():
    """Negative duration returns error."""
    db = MockDB()
    error = create_movie(db, 'Inception', 'A dream movie', 'Sci-Fi', -10, '')
    assert error is not None


def test_create_movie_missing_genre():
    """Missing genre returns error."""
    db = MockDB()
    error = create_movie(db, 'Inception', 'A dream movie', '', 148, '')
    assert error is not None


# ─── CREATE SHOWTIME TESTS ──────────────────────────────────────

def test_create_showtime_success():
    """Valid showtime creation returns None and generates seats."""
    db = MockDB()
    error = create_showtime(db, 1, 'Hall A', '2026-06-01 20:00:00', 10)
    assert error is None
    assert len(db.seats) == 10


def test_create_showtime_missing_hall():
    """Missing hall name returns error."""
    db = MockDB()
    error = create_showtime(db, 1, '', '2026-06-01 20:00:00', 10)
    assert error is not None


def test_create_showtime_invalid_seats():
    """Zero seats returns error."""
    db = MockDB()
    error = create_showtime(db, 1, 'Hall A', '2026-06-01 20:00:00', 0)
    assert error is not None


# ─── IS SHOWTIME FULL TESTS ─────────────────────────────────────

def test_showtime_not_full():
    """Showtime with available seats is not full."""
    db = MockDB()
    create_showtime(db, 1, 'Hall A', '2026-06-01 20:00:00', 10)
    showtime_id = list(db.showtimes.keys())[0]
    assert is_showtime_full(db, showtime_id) is False


def test_showtime_is_full():
    """Showtime with all seats reserved is full."""
    db = MockDB()
    create_showtime(db, 1, 'Hall A', '2026-06-01 20:00:00', 2)
    showtime_id = list(db.showtimes.keys())[0]
    for seat in db.seats.values():
        seat['is_reserved'] = 1
    assert is_showtime_full(db, showtime_id) is True