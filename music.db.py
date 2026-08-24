import sqlite3


# Connect to the SQLite database.
# SQLite creates music.db automatically if it does not exist.
connection = sqlite3.connect("music.db")

# Create a cursor for running SQL commands.
cursor = connection.cursor()


# Enable foreign key support.
cursor.execute("PRAGMA foreign_keys = ON;")


# Create the artists table.
# The artist name is UNIQUE so the same artist
# cannot be inserted more than once.
cursor.execute("""
CREATE TABLE IF NOT EXISTS artists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    genre TEXT
)
""")


# Create the albums table.
# The combination of title and artist_id must be unique,
# which prevents the same album from being added twice
# for the same artist.
cursor.execute("""
CREATE TABLE IF NOT EXISTS albums (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    artist_id INTEGER,
    FOREIGN KEY (artist_id) REFERENCES artists(id),
    UNIQUE (title, artist_id)
)
""")


# -----------------------------
# Insert artists
# -----------------------------

artists = [
    ("Michael Jackson", "Pop"),
    ("Kendrick Lamar", "Hip-Hop"),
    ("Adele", "Pop")
]


# INSERT OR IGNORE means:
# If the artist already exists, SQLite skips that row
# instead of creating a duplicate.
cursor.executemany("""
INSERT OR IGNORE INTO artists (name, genre)
VALUES (?, ?)
""", artists)


# -----------------------------
# Get artist IDs
# -----------------------------

# We look up the IDs instead of assuming that
# Michael Jackson is always ID 1, Kendrick is ID 2, etc.
cursor.execute("""
SELECT id, name
FROM artists
""")


# Create a dictionary such as:
# {
#     "Michael Jackson": 1,
#     "Kendrick Lamar": 2,
#     "Adele": 3
# }
artist_ids = {
    name: artist_id
    for artist_id, name in cursor.fetchall()
}


# -----------------------------
# Insert albums
# -----------------------------

albums = [
    ("Thriller", 1982, artist_ids["Michael Jackson"]),
    ("Bad", 1987, artist_ids["Michael Jackson"]),
    (
        "good kid, m.A.A.d city",
        2012,
        artist_ids["Kendrick Lamar"]
    ),
    ("DAMN.", 2017, artist_ids["Kendrick Lamar"]),
    ("21", 2011, artist_ids["Adele"])
]


# Ignore an album if that title already exists
# for the same artist.
cursor.executemany("""
INSERT OR IGNORE INTO albums (title, year, artist_id)
VALUES (?, ?, ?)
""", albums)


# Save the changes.
connection.commit()


# -----------------------------
# Query the music collection
# -----------------------------

# JOIN connects each album to its artist
# using albums.artist_id and artists.id.
cursor.execute("""
SELECT albums.title, albums.year, artists.name
FROM albums
JOIN artists
ON albums.artist_id = artists.id
ORDER BY artists.name, albums.year
""")


results = cursor.fetchall()


# -----------------------------
# Print the results neatly
# -----------------------------

print("\n" + "=" * 60)
print("                 MUSIC COLLECTION")
print("=" * 60)

# Print column headers
print(f"{'Artist':<20} {'Album':<30} {'Year':>6}")
print("-" * 60)

# Print each album in aligned columns
for title, year, artist in results:
    print(f"{artist:<20} {title:<30} {year:>6}")

print("=" * 60)

# Close the database connection
connection.close()

print("Database connection closed.")
