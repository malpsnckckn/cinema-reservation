-- Admin user (password: admin123)
INSERT OR IGNORE INTO users (username, password_hash, is_admin) VALUES (
    'admin',
    'scrypt:32768:8:1$hvV5zvtHOwFK2FKq$4a3db7bec280d1127c403f7a5a6e4a0beb44f37519584ed3dcc2ed58b93350b843d5f6d61374de9765324fb7b219471333f452a740f61d0806441400108e7a1a',
    1
);

-- Sample movies
INSERT OR IGNORE INTO movies (title, description, genre, duration_minutes, poster_url) VALUES
('The Dark Knight', 'When the menace known as the Joker wreaks havoc on Gotham City, Batman must accept one of the greatest psychological and physical tests of his ability to fight injustice.', 'Action', 152, 'https://upload.wikimedia.org/wikipedia/en/1/1c/The_Dark_Knight_%282008_film%29.jpg'),
('Inception', 'A thief who steals corporate secrets through the use of dream-sharing technology is given the inverse task of planting an idea into the mind of a C.E.O.', 'Sci-Fi', 148, 'https://upload.wikimedia.org/wikipedia/en/2/2e/Inception_%282010%29_theatrical_poster.jpg'),
('Interstellar', 'A team of explorers travel through a wormhole in space in an attempt to ensure humanity survival.', 'Sci-Fi', 169, 'https://upload.wikimedia.org/wikipedia/en/b/bc/Interstellar_film_poster.jpg');

-- Sample snacks
INSERT OR IGNORE INTO snacks (name, price, category) VALUES
('Popcorn', 4.00, 'food'),
('Nachos', 4.50, 'food'),
('Hot Dog', 5.00, 'food'),
('Cola', 3.00, 'drink'),
('Water', 1.50, 'drink'),
('Orange Juice', 3.00, 'drink');