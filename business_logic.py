from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


# ─── AUTH ───────────────────────────────────────────────────────

def register_user(db, username, password, security_question, security_answer):
    """Returns error message or None if successful."""
    if not username or not password:
        return 'Username and password are required.'
    if len(password) < 6:
        return 'Password must be at least 6 characters.'
    if not security_question or not security_answer:
        return 'Security question and answer are required.'
    existing = db.execute(
        'SELECT id FROM users WHERE username = ?', (username,)
    ).fetchone()
    if existing:
        return 'Username already exists.'
    password_hash = generate_password_hash(password)
    security_answer_hash = generate_password_hash(security_answer.lower().strip())
    db.execute(
        '''INSERT INTO users (username, password_hash, security_question, security_answer)
           VALUES (?, ?, ?, ?)''',
        (username, password_hash, security_question, security_answer_hash)
    )
    db.commit()
    return None


def reset_password(db, username, security_answer, new_password):
    """Returns error message or None if successful."""
    if len(new_password) < 6:
        return 'Password must be at least 6 characters.'
    user = db.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    if not user:
        return 'Username not found.'
    if not check_password_hash(user['security_answer'], security_answer.lower().strip()):
        return 'Incorrect answer to security question.'
    new_hash = generate_password_hash(new_password)
    db.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (new_hash, user['id'])
    )
    db.commit()
    return None

def authenticate_user(db, username, password):
    """Returns user row or None."""
    user = db.execute(
        'SELECT * FROM users WHERE username = ?', (username,)
    ).fetchone()
    if user and check_password_hash(user['password_hash'], password):
        return user
    return None


# ─── MOVIES ─────────────────────────────────────────────────────

def get_all_movies(db):
    return db.execute('SELECT * FROM movies ORDER BY created_at DESC').fetchall()


def get_movie_by_id(db, movie_id):
    return db.execute('SELECT * FROM movies WHERE id = ?', (movie_id,)).fetchone()


def create_movie(db, title, description, genre, duration_minutes, poster_url):
    """Returns error message or None if successful."""
    if not title or not genre or not duration_minutes:
        return 'Title, genre and duration are required.'
    if int(duration_minutes) <= 0:
        return 'Duration must be a positive number.'
    db.execute(
        'INSERT INTO movies (title, description, genre, duration_minutes, poster_url) VALUES (?, ?, ?, ?, ?)',
        (title, description, genre, duration_minutes, poster_url)
    )
    db.commit()
    return None


def update_movie(db, movie_id, title, description, genre, duration_minutes, poster_url):
    """Returns error message or None if successful."""
    if not title or not genre or not duration_minutes:
        return 'Title, genre and duration are required.'
    if int(duration_minutes) <= 0:
        return 'Duration must be a positive number.'
    db.execute(
        '''UPDATE movies SET title=?, description=?, genre=?, duration_minutes=?, poster_url=?
           WHERE id=?''',
        (title, description, genre, duration_minutes, poster_url, movie_id)
    )
    db.commit()
    return None


def delete_movie(db, movie_id):
    """Returns error message or None if successful."""
    active = db.execute(
        '''SELECT r.id FROM reservations r
           JOIN showtimes s ON r.showtime_id = s.id
           WHERE s.movie_id = ? AND r.status = "active"''',
        (movie_id,)
    ).fetchone()
    if active:
        return 'Cannot delete movie with active reservations.'
    
    # First delete seats, then showtimes, then movie
    showtimes = db.execute(
        'SELECT id FROM showtimes WHERE movie_id = ?', (movie_id,)
    ).fetchall()
    for showtime in showtimes:
        db.execute('DELETE FROM seats WHERE showtime_id = ?', (showtime['id'],))
    
    db.execute('DELETE FROM showtimes WHERE movie_id = ?', (movie_id,))
    db.execute('DELETE FROM movies WHERE id = ?', (movie_id,))
    db.commit()
    return None


# ─── SHOWTIMES ──────────────────────────────────────────────────

def get_showtimes_by_movie(db, movie_id):
    return db.execute(
        'SELECT * FROM showtimes WHERE movie_id = ? ORDER BY start_time',
        (movie_id,)
    ).fetchall()


def create_showtime(db, movie_id, hall_name, start_time, total_seats):
    """Returns error message or None if successful."""
    if not hall_name or not start_time or not total_seats:
        return 'All fields are required.'
    if int(total_seats) <= 0:
        return 'Total seats must be a positive number.'
    cursor = db.execute(
        'INSERT INTO showtimes (movie_id, hall_name, start_time, total_seats) VALUES (?, ?, ?, ?)',
        (movie_id, hall_name, start_time, total_seats)
    )
    showtime_id = cursor.lastrowid
    # Auto-generate seats
    for i in range(1, int(total_seats) + 1):
        seat_number = f'{"ABCDEFGHIJ"[(i-1) // 10]}{(i-1) % 10 + 1}'
        db.execute(
            'INSERT INTO seats (showtime_id, seat_number) VALUES (?, ?)',
            (showtime_id, seat_number)
        )
    db.commit()
    return None


def delete_showtime(db, showtime_id):
    """Returns error message or None if successful."""
    active = db.execute(
        'SELECT id FROM reservations WHERE showtime_id = ? AND status = "active"',
        (showtime_id,)
    ).fetchone()
    if active:
        return 'Cannot delete showtime with active reservations.'
    db.execute('DELETE FROM seats WHERE showtime_id = ?', (showtime_id,))
    db.execute('DELETE FROM showtimes WHERE id = ?', (showtime_id,))
    db.commit()
    return None


# ─── SEATS ──────────────────────────────────────────────────────

def get_seats_by_showtime(db, showtime_id):
    return db.execute(
        'SELECT * FROM seats WHERE showtime_id = ? ORDER BY seat_number',
        (showtime_id,)
    ).fetchall()


def is_showtime_full(db, showtime_id):
    showtime = db.execute(
        'SELECT total_seats FROM showtimes WHERE id = ?', (showtime_id,)
    ).fetchone()
    reserved = db.execute(
        'SELECT COUNT(*) as count FROM seats WHERE showtime_id = ? AND is_reserved = 1',
        (showtime_id,)
    ).fetchone()
    return reserved['count'] >= showtime['total_seats']


# ─── SNACKS ─────────────────────────────────────────────────────

def get_all_snacks(db):
    return db.execute('SELECT * FROM snacks ORDER BY category, name').fetchall()


# ─── RESERVATIONS ───────────────────────────────────────────────

def create_reservation(db, user_id, showtime_id, seat_id, snack_orders, ticket_price=50.0):
    """Returns error message or None if successful."""
    seat = db.execute(
        'SELECT * FROM seats WHERE id = ? AND showtime_id = ?', (seat_id, showtime_id)
    ).fetchone()
    if not seat:
        return 'Invalid seat.'
    if seat['is_reserved']:
        return 'This seat is already reserved.'

    total_price = ticket_price
    for snack_id, quantity in snack_orders.items():
        snack = db.execute('SELECT price FROM snacks WHERE id = ?', (snack_id,)).fetchone()
        if snack:
            total_price += snack['price'] * quantity

    cursor = db.execute(
        'INSERT INTO reservations (user_id, showtime_id, seat_id, total_price) VALUES (?, ?, ?, ?)',
        (user_id, showtime_id, seat_id, total_price)
    )
    reservation_id = cursor.lastrowid

    db.execute('UPDATE seats SET is_reserved = 1 WHERE id = ?', (seat_id,))

    for snack_id, quantity in snack_orders.items():
        db.execute(
            'INSERT INTO reservation_snacks (reservation_id, snack_id, quantity) VALUES (?, ?, ?)',
            (reservation_id, snack_id, quantity)
        )

    db.commit()
    return None


def get_user_reservations(db, user_id):
    return db.execute(
        '''SELECT r.*, s.start_time, s.hall_name, m.title as movie_title, 
                  se.seat_number, r.total_price
           FROM reservations r
           JOIN showtimes s ON r.showtime_id = s.id
           JOIN movies m ON s.movie_id = m.id
           JOIN seats se ON r.seat_id = se.id
           WHERE r.user_id = ?
           ORDER BY r.created_at DESC''',
        (user_id,)
    ).fetchall()


def calculate_refund(total_price, start_time):
    if isinstance(start_time, str):
        # Handle both formats
        try:
            start_time = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
    now = datetime.now()
    hours_until_showtime = (start_time - now).total_seconds() / 3600

    if hours_until_showtime > 48:
        return round(total_price, 2)
    elif hours_until_showtime > 24:
        return round(total_price * 0.5, 2)
    else:
        return 0.0


def cancel_reservation(db, reservation_id, user_id):
    """Returns (refund_amount, error_message)."""
    reservation = db.execute(
        '''SELECT r.*, s.start_time FROM reservations r
           JOIN showtimes s ON r.showtime_id = s.id
           WHERE r.id = ? AND r.user_id = ?''',
        (reservation_id, user_id)
    ).fetchone()

    if not reservation:
        return 0, 'Reservation not found.'
    if reservation['status'] != 'active':
        return 0, 'Only active reservations can be cancelled.'

    refund = calculate_refund(reservation['total_price'], reservation['start_time'])

    db.execute(
        'UPDATE reservations SET status = "cancelled" WHERE id = ?', (reservation_id,)
    )
    db.execute(
        'UPDATE seats SET is_reserved = 0 WHERE id = ?', (reservation['seat_id'],)
    )
    db.commit()
    return refund, None


def get_reservation_snacks(db, reservation_id):
    return db.execute(
        '''SELECT s.name, s.price, rs.quantity
           FROM reservation_snacks rs
           JOIN snacks s ON rs.snack_id = s.id
           WHERE rs.reservation_id = ?''',
        (reservation_id,)
    ).fetchall()