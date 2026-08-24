import sqlite3


def print_results(title, cursor):
    """Print a query title, its column headings, and every returned row."""
    # A blank line separates each report from the previous report.
    print(f"\n{title}")
    print("-" * len(title))

    # cursor.description contains information about every selected column.
    # The first item in each description is the column name or SQL alias.
    column_names = [column[0] for column in cursor.description]
    print(" | ".join(column_names))
    print("-" * 60)

    # fetchall() returns the remaining query results as a list of tuples.
    rows = cursor.fetchall()
    if not rows:
        print("No results found.")
        return

    # Convert every value to text before joining the values for display.
    for row in rows:
        print(" | ".join("NULL" if value is None else str(value) for value in row))


def main():
    # The database is created in memory and lasts only while the script runs.
    connection = sqlite3.connect(":memory:")

    # SQLite does not enforce foreign keys by default, so enable that feature.
    # This prevents a checkout from referring to a nonexistent member or book.
    connection.execute("PRAGMA foreign_keys = ON")

    # The cursor sends SQL statements to the database and stores query results.
    cursor = connection.cursor()

    # executescript() can run several SQL statements at once. The members and
    # books tables are the parent tables. The checkouts table connects them by
    # storing member_id and book_id as foreign keys.
    cursor.executescript(
        """
        CREATE TABLE members (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            join_date TEXT NOT NULL
        );

        CREATE TABLE books (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            genre TEXT NOT NULL,
            year_published INTEGER NOT NULL
        );

        CREATE TABLE checkouts (
            id INTEGER PRIMARY KEY,
            member_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            checkout_date TEXT NOT NULL,
            return_date TEXT,
            FOREIGN KEY (member_id) REFERENCES members(id),
            FOREIGN KEY (book_id) REFERENCES books(id)
        );
        """
    )

    # Each member tuple follows this order: id, name, join_date.
    # Dates use the ISO YYYY-MM-DD format, which sorts correctly as text.
    members = [
        (1, "Alice Carter", "2023-01-15"),
        (2, "Ben Turner", "2023-03-02"),
        (3, "Carla Ruiz", "2023-06-18"),
        (4, "Daniel Kim", "2024-02-09"),
        (5, "Elena Brooks", "2024-05-21"),
        (6, "Frank Lewis", "2025-01-10"),  # No checkouts yet.
    ]

    # The books span four genres. Book 9 intentionally has no checkout record
    # so Query 5 has an example of a book that has never been borrowed.
    books = [
        (1, "The Silent Patient", "Mystery", 2019),
        (2, "Gone Girl", "Mystery", 2012),
        (3, "Dune", "Science Fiction", 1965),
        (4, "Project Hail Mary", "Science Fiction", 2021),
        (5, "Pride and Prejudice", "Romance", 1813),
        (6, "The Notebook", "Romance", 1996),
        (7, "Educated", "Memoir", 2018),
        (8, "Becoming", "Memoir", 2018),
        (9, "The Martian", "Science Fiction", 2011),  # Never checked out.
    ]

    # Each checkout connects one member to one book. A None value becomes SQL
    # NULL and means that the book has not been returned yet.
    # There are 18 checkout records, which exceeds the required minimum of 15.
    checkouts = [
        (1, 1, 1, "2024-01-05", "2024-01-19"),
        (2, 1, 3, "2024-02-01", "2024-02-15"),
        (3, 1, 5, "2024-03-10", "2024-03-24"),
        (4, 1, 7, "2024-04-08", "2024-04-22"),
        (5, 1, 2, "2024-05-11", "2024-05-25"),
        (6, 2, 2, "2024-01-12", "2024-01-26"),
        (7, 2, 4, "2024-02-20", "2024-03-05"),
        (8, 2, 6, "2024-04-01", "2024-04-15"),
        (9, 2, 1, "2024-06-03", "2024-06-17"),
        (10, 3, 3, "2024-01-18", "2024-02-01"),
        (11, 3, 4, "2024-03-03", "2024-03-17"),
        (12, 3, 8, "2024-05-07", "2024-05-21"),
        (13, 4, 5, "2024-02-14", "2024-02-28"),
        (14, 4, 6, "2024-04-19", "2024-05-03"),
        (15, 4, 1, "2024-07-02", None),
        (16, 5, 7, "2024-03-16", "2024-03-30"),
        (17, 5, 3, "2024-06-10", None),
        (18, 1, 4, "2024-08-01", None),
    ]

    # executemany() runs the same parameterized INSERT once for every tuple.
    # Question-mark placeholders keep the SQL separate from the data values.
    cursor.executemany(
        "INSERT INTO members (id, name, join_date) VALUES (?, ?, ?)", members
    )
    cursor.executemany(
        """
        INSERT INTO books (id, title, genre, year_published)
        VALUES (?, ?, ?, ?)
        """,
        books,
    )
    cursor.executemany(
        """
        INSERT INTO checkouts
            (id, member_id, book_id, checkout_date, return_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        checkouts,
    )
    # Save all inserted records before running the reports.
    connection.commit()

    # Query 1: Count how many books belong to each genre.
    # GROUP BY creates one group for every unique genre. COUNT(*) then counts
    # all book rows inside each group.
    cursor.execute(
        """
        SELECT genre, COUNT(*) AS number_of_books
        FROM books
        GROUP BY genre
        ORDER BY genre;
        """
    )
    print_results("QUERY 1: Number of books in each genre", cursor)

    # Query 2: Find the member with the greatest number of checkouts.
    # The INNER JOIN excludes members without checkouts. Results are grouped by
    # member, sorted from highest count to lowest, and limited to the top row.
    cursor.execute(
        """
        SELECT m.name AS member, COUNT(c.id) AS checkout_count
        FROM members AS m
        INNER JOIN checkouts AS c ON m.id = c.member_id
        GROUP BY m.id, m.name
        ORDER BY checkout_count DESC, m.name
        LIMIT 1;
        """
    )
    print_results("QUERY 2: Member with the most checkouts", cursor)

    # Query 3: Average the per-member checkout totals. The LEFT JOIN ensures
    # members with no checkouts are included with a total of zero.
    # The inner query produces one checkout count per member. The outer query
    # applies AVG() to those counts, and ROUND() displays two decimal places.
    cursor.execute(
        """
        SELECT ROUND(AVG(member_checkout_count), 2) AS average_checkouts_per_member
        FROM (
            SELECT m.id, COUNT(c.id) AS member_checkout_count
            FROM members AS m
            LEFT JOIN checkouts AS c ON m.id = c.member_id
            GROUP BY m.id
        ) AS checkout_totals;
        """
    )
    print_results("QUERY 3: Average number of checkouts per member", cursor)

    # Query 4: Show only genres that have more than three checkout records.
    # WHERE filters individual rows before grouping, while HAVING filters whole
    # groups after aggregation. Therefore, the COUNT condition belongs in HAVING.
    cursor.execute(
        """
        SELECT b.genre, COUNT(c.id) AS checkout_count
        FROM books AS b
        INNER JOIN checkouts AS c ON b.id = c.book_id
        GROUP BY b.genre
        HAVING COUNT(c.id) > 3
        ORDER BY checkout_count DESC, b.genre;
        """
    )
    print_results("QUERY 4: Genres with more than 3 checkouts", cursor)

    # Query 5: Find books whose IDs never appear in the checkouts table.
    # The subquery returns every checked-out book ID. NOT IN keeps book rows
    # whose IDs are absent from that result.
    cursor.execute(
        """
        SELECT title, genre, year_published
        FROM books
        WHERE id NOT IN (
            SELECT book_id
            FROM checkouts
        )
        ORDER BY title;
        """
    )
    print_results("QUERY 5: Books that have never been checked out", cursor)

    # Close the connection after every report has finished.
    connection.close()


if __name__ == "__main__":
    # This guard runs main() only when this file is executed directly.
    main()
