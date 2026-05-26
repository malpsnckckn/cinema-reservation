from flask import Flask, render_template, request, redirect, url_for, session, flash
from database import get_db, init_db, close_db
from auth import login_required, admin_required
import business_logic as bl

app = Flask(__name__)
app.secret_key = 'cinema_secret_key_2026'


@app.teardown_appcontext
def teardown_db(exception):
    close_db()


# ─── AUTH ROUTES ────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        security_question = request.form['security_question'].strip()
        security_answer = request.form['security_answer'].strip()
        db = get_db()
        error = bl.register_user(db, username, password, security_question, security_answer)
        if error:
            flash(error, 'error')
        else:
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        db = get_db()
        user = bl.authenticate_user(db, username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])
            if user['is_admin']:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('movies'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    user = None
    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username', '').strip()
        db = get_db()

        if action == 'find_user':
            user_row = db.execute(
                'SELECT username, security_question FROM users WHERE username = ?',
                (username,)
            ).fetchone()
            if user_row:
                return render_template('forgot_password.html',
                                       username=user_row['username'],
                                       security_question=user_row['security_question'])
            else:
                flash('Username not found.', 'error')

        elif action == 'reset_password':
            security_answer = request.form.get('security_answer', '').strip()
            new_password = request.form.get('new_password', '').strip()
            error = bl.reset_password(db, username, security_answer, new_password)
            if error:
                flash(error, 'error')
                user_row = db.execute(
                    'SELECT username, security_question FROM users WHERE username = ?',
                    (username,)
                ).fetchone()
                return render_template('forgot_password.html',
                                       username=user_row['username'],
                                       security_question=user_row['security_question'])
            else:
                flash('Password reset successful! Please log in.', 'success')
                return redirect(url_for('login'))

    return render_template('forgot_password.html', username=None, security_question=None)


# ─── USER ROUTES ────────────────────────────────────────────────

@app.route('/movies')
@login_required
def movies():
    db = get_db()
    movies_list = bl.get_all_movies(db)
    return render_template('movies.html', movies=movies_list)


@app.route('/movies/<int:movie_id>/showtimes')
@login_required
def showtimes(movie_id):
    db = get_db()
    movie = bl.get_movie_by_id(db, movie_id)
    if not movie:
        flash('Movie not found.', 'error')
        return redirect(url_for('movies'))
    showtimes_list = bl.get_showtimes_by_movie(db, movie_id)
    return render_template('showtimes.html', movie=movie, showtimes=showtimes_list)


@app.route('/showtimes/<int:showtime_id>/seats')
@login_required
def seats(showtime_id):
    db = get_db()
    seats_list = bl.get_seats_by_showtime(db, showtime_id)
    showtime = db.execute(
        '''SELECT s.*, m.title as movie_title FROM showtimes s
           JOIN movies m ON s.movie_id = m.id
           WHERE s.id = ?''', (showtime_id,)
    ).fetchone()
    if not showtime:
        flash('Showtime not found.', 'error')
        return redirect(url_for('movies'))
    return render_template('seats.html', seats=seats_list, showtime=showtime)


@app.route('/reserve', methods=['POST'])
@login_required
def reserve():
    db = get_db()
    showtime_id = int(request.form['showtime_id'])
    seat_id = int(request.form['seat_id'])
    session['pending_reservation'] = {
        'showtime_id': showtime_id,
        'seat_id': seat_id
    }
    snacks_list = bl.get_all_snacks(db)
    return render_template('snacks.html', snacks=snacks_list,
                           showtime_id=showtime_id, seat_id=seat_id)


@app.route('/reserve/confirm', methods=['POST'])
@login_required
def confirm_reservation():
    db = get_db()
    showtime_id = int(request.form['showtime_id'])
    seat_id = int(request.form['seat_id'])

    snack_orders = {}
    for key, value in request.form.items():
        if key.startswith('snack_') and int(value) > 0:
            snack_id = int(key.replace('snack_', ''))
            snack_orders[snack_id] = int(value)

    error = bl.create_reservation(db, session['user_id'], showtime_id, seat_id, snack_orders)
    if error:
        flash(error, 'error')
        return redirect(url_for('seats', showtime_id=showtime_id))

    flash('Reservation confirmed successfully!', 'success')
    return redirect(url_for('reservations'))


@app.route('/reservations')
@login_required
def reservations():
    db = get_db()
    reservations_list = bl.get_user_reservations(db, session['user_id'])
    reservation_details = {}
    for res in reservations_list:
        snacks = bl.get_reservation_snacks(db, res['id'])
        reservation_details[res['id']] = snacks
    return render_template('reservations.html',
                           reservations=reservations_list,
                           reservation_details=reservation_details)


@app.route('/reservations/<int:reservation_id>/cancel', methods=['POST'])
@login_required
def cancel_reservation(reservation_id):
    db = get_db()
    refund, error = bl.cancel_reservation(db, reservation_id, session['user_id'])
    if error:
        flash(error, 'error')
    else:
        flash(f'Reservation cancelled. Refund amount: ${refund:.2f}', 'success')
    return redirect(url_for('reservations'))


# ─── ADMIN ROUTES ───────────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    db = get_db()
    movies_list = bl.get_all_movies(db)
    total_reservations = db.execute(
        'SELECT COUNT(*) as count FROM reservations WHERE status = "active"'
    ).fetchone()['count']
    total_users = db.execute(
        'SELECT COUNT(*) as count FROM users WHERE is_admin = 0'
    ).fetchone()['count']
    return render_template('admin/dashboard.html',
                           movies=movies_list,
                           total_reservations=total_reservations,
                           total_users=total_users)


@app.route('/admin/movies/create', methods=['GET', 'POST'])
@admin_required
def admin_create_movie():
    if request.method == 'POST':
        db = get_db()
        error = bl.create_movie(
            db,
            request.form['title'],
            request.form['description'],
            request.form['genre'],
            request.form['duration_minutes'],
            request.form['poster_url']
        )
        if error:
            flash(error, 'error')
        else:
            flash('Movie created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/movies.html', movie=None)


@app.route('/admin/movies/<int:movie_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_movie(movie_id):
    db = get_db()
    movie = bl.get_movie_by_id(db, movie_id)
    if request.method == 'POST':
        error = bl.update_movie(
            db,
            movie_id,
            request.form['title'],
            request.form['description'],
            request.form['genre'],
            request.form['duration_minutes'],
            request.form['poster_url']
        )
        if error:
            flash(error, 'error')
        else:
            flash('Movie updated successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/movies.html', movie=movie)


@app.route('/admin/movies/<int:movie_id>/delete', methods=['POST'])
@admin_required
def admin_delete_movie(movie_id):
    db = get_db()
    error = bl.delete_movie(db, movie_id)
    if error:
        flash(error, 'error')
    else:
        flash('Movie deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/movies/<int:movie_id>/showtimes/create', methods=['GET', 'POST'])
@admin_required
def admin_create_showtime(movie_id):
    db = get_db()
    movie = bl.get_movie_by_id(db, movie_id)
    if request.method == 'POST':
        error = bl.create_showtime(
            db,
            movie_id,
            request.form['hall_name'],
            request.form['start_time'],
            request.form['total_seats']
        )
        if error:
            flash(error, 'error')
        else:
            flash('Showtime created successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/showtimes.html', movie=movie)


@app.route('/admin/showtimes/<int:showtime_id>/delete', methods=['POST'])
@admin_required
def admin_delete_showtime(showtime_id):
    db = get_db()
    error = bl.delete_showtime(db, showtime_id)
    if error:
        flash(error, 'error')
    else:
        flash('Showtime deleted successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/snacks')
@admin_required
def admin_snacks():
    db = get_db()
    snacks = bl.get_all_snacks(db)
    return render_template('admin/snacks.html', snacks=snacks)


@app.route('/admin/snacks/create', methods=['POST'])
@admin_required
def admin_create_snack():
    db = get_db()
    name = request.form['name'].strip()
    price = request.form['price'].strip()
    category = request.form['category'].strip()
    if not name or not price or not category:
        flash('All fields are required.', 'error')
    else:
        db.execute(
            'INSERT INTO snacks (name, price, category) VALUES (?, ?, ?)',
            (name, float(price), category)
        )
        db.commit()
        flash('Snack created successfully!', 'success')
    return redirect(url_for('admin_snacks'))


@app.route('/admin/snacks/<int:snack_id>/delete', methods=['POST'])
@admin_required
def admin_delete_snack(snack_id):
    db = get_db()
    db.execute('DELETE FROM snacks WHERE id = ?', (snack_id,))
    db.commit()
    flash('Snack deleted successfully!', 'success')
    return redirect(url_for('admin_snacks'))
# ─── MAIN ───────────────────────────────────────────────────────

if __name__ == '__main__':
    with app.app_context():
        init_db(app)
    app.run(debug=True)