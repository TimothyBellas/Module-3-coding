from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    ForeignKey,
    Integer,
    String,
    Table,
    create_engine,
    event,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    joinedload,
    mapped_column,
    relationship,
    selectinload,
    sessionmaker,
)


# ---------------------------------------------------------------------------
# DATABASE AND MODELS
# ---------------------------------------------------------------------------

# Build an absolute path beside this script. This makes the database location
# predictable even if the program is launched from a different working folder.
DATABASE_PATH = Path(__file__).with_name("library.db")

# echo=False keeps SQL statements out of the normal CLI output. Change it to
# True while debugging if you want to see every statement SQLAlchemy executes.
engine = create_engine(f"sqlite:///{DATABASE_PATH}", echo=False)

# expire_on_commit=False lets CRUD functions safely return objects whose simple
# attributes can still be read after the session context manager closes.
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


@event.listens_for(Engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """Enable SQLite foreign-key constraints on every connection."""
    # SQLite supports foreign keys but does not enforce them by default.
    # Running this PRAGMA for every connection protects referential integrity.
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# A plain association table is appropriate here because the Book/Author link
# has no extra data of its own. The pair of foreign keys is also the composite
# primary key, which prevents the same author being linked to a book twice.
book_authors = Table(
    "book_authors",
    Base.metadata,
    Column("book_id", ForeignKey("books.id", ondelete="CASCADE"), primary_key=True),
    Column("author_id", ForeignKey("authors.id", ondelete="CASCADE"), primary_key=True),
)


class Author(Base):
    """An author who may write many books."""

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    bio: Mapped[str | None] = mapped_column(String(2000), nullable=True)

    books: Mapped[list["Book"]] = relationship(
        # secondary tells SQLAlchemy to join through book_authors.
        # back_populates keeps Author.books and Book.authors synchronized.
        secondary=book_authors, back_populates="authors"
    )

    def __repr__(self) -> str:
        return f"Author(id={self.id!r}, name={self.name!r})"


class Member(Base):
    """A registered library member."""

    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    membership_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)

    borrowings: Mapped[list["Borrowing"]] = relationship(
        # Deleting an allowed Member also deletes that member's historical
        # borrowing rows. The CRUD layer first blocks deletion of active loans.
        back_populates="member", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Member(id={self.id!r}, name={self.name!r}, email={self.email!r})"


class Book(Base):
    """A cataloged book and its currently available copy count."""

    __tablename__ = "books"
    # This database constraint provides a final safety net in addition to the
    # availability check performed by checkout_book().
    __table_args__ = (
        CheckConstraint("available_copies >= 0", name="ck_books_available_copies"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    isbn: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    year_published: Mapped[int | None] = mapped_column(Integer, nullable=True)
    available_copies: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    authors: Mapped[list[Author]] = relationship(
        # This is the other side of the bidirectional many-to-many relationship.
        secondary=book_authors, back_populates="books"
    )
    borrowings: Mapped[list["Borrowing"]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Book(id={self.id!r}, title={self.title!r}, isbn={self.isbn!r})"


class Borrowing(Base):
    """A checkout transaction between a book and a member."""

    __tablename__ = "borrowings"
    # NULL return_date means the loan is still active. If a return date exists,
    # the database guarantees that it is not earlier than checkout_date.
    __table_args__ = (
        CheckConstraint(
            "return_date IS NULL OR return_date >= checkout_date",
            name="ck_borrowings_valid_dates",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checkout_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # These two many-to-one relationships make navigation work in both
    # directions: borrowing.book, borrowing.member, and their collection sides.
    book: Mapped[Book] = relationship(back_populates="borrowings")
    member: Mapped[Member] = relationship(back_populates="borrowings")

    def __repr__(self) -> str:
        return (
            f"Borrowing(id={self.id!r}, book_id={self.book_id!r}, "
            f"member_id={self.member_id!r}, return_date={self.return_date!r})"
        )


def init_db() -> None:
    """Create all database tables that do not already exist."""
    # create_all is idempotent: existing tables and data are left untouched.
    Base.metadata.create_all(engine)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

def clean_required(value: str, field: str) -> str:
    """Strip a required value or raise a clear validation error."""
    value = value.strip()
    if not value:
        raise ValueError(f"{field} is required.")
    return value


def valid_email(value: str) -> str:
    """Normalize and perform basic validation on an email address."""
    email = clean_required(value, "Email").lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("Enter a valid email address.")
    return email


def commit_or_rollback(session, message: str) -> None:
    """Commit a transaction or roll it back and translate integrity errors."""
    try:
        session.commit()
    except IntegrityError as exc:
        # A failed SQLAlchemy session cannot be reused until it is rolled back.
        # The friendly ValueError is easier for CLI handlers to display.
        session.rollback()
        raise ValueError(message) from exc


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def add_author(name: str, bio: str | None = None) -> Author:
    """Add and return an author."""
    # A context-managed session always closes, even if validation/commit fails.
    with SessionLocal() as session:
        author = Author(name=clean_required(name, "Author name"), bio=bio or None)
        session.add(author)
        commit_or_rollback(session, "Could not add the author.")
        return author


def add_book(
    title: str,
    isbn: str,
    year_published: int | None = None,
    available_copies: int = 1,
    author_names: list[str] | None = None,
) -> Book:
    """Add a book and optionally link or create authors by name."""
    title = clean_required(title, "Title")
    isbn = clean_required(isbn, "ISBN")
    if available_copies < 0:
        raise ValueError("Available copies cannot be negative.")

    with SessionLocal() as session:
        # Build the Book first, then attach Author ORM objects. SQLAlchemy will
        # insert the necessary rows into book_authors when the session commits.
        book = Book(
            title=title,
            isbn=isbn,
            year_published=year_published,
            available_copies=available_copies,
        )
        # dict.fromkeys removes duplicate author names while preserving order.
        for raw_name in dict.fromkeys(author_names or []):
            name = clean_required(raw_name, "Author name")
            author = session.scalar(select(Author).where(Author.name == name))
            if author is None:
                # Allow the add-book workflow to create an author automatically.
                author = Author(name=name)
            book.authors.append(author)
        session.add(book)
        # The unique ISBN constraint is translated into a clear CLI error here.
        commit_or_rollback(session, f"A book with ISBN {isbn} already exists.")
        return book


def add_member(name: str, email: str) -> Member:
    """Register a member with today's membership date."""
    with SessionLocal() as session:
        member = Member(
            name=clean_required(name, "Member name"),
            email=valid_email(email),
            membership_date=date.today(),
        )
        session.add(member)
        commit_or_rollback(
            session, f"A member with email {member.email} already exists."
        )
        return member
def checkout_book(
    book_id: int, member_id: int, checkout_date: date | None = None
) -> Borrowing:
    """Check out an available copy to an existing member."""
    with SessionLocal() as session:
        # session.get performs a primary-key lookup and returns None when absent.
        book = session.get(Book, book_id)
        member = session.get(Member, member_id)
        if book is None:
            raise ValueError("Book not found.")
        if member is None:
            raise ValueError("Member not found.")
        if book.available_copies <= 0:
            raise ValueError("No copies of this book are currently available.")

        # The copy decrement and Borrowing insert occur in one transaction. If
        # either operation fails, the rollback prevents a partial checkout.
        book.available_copies -= 1
        borrowing = Borrowing(
            book=book,
            member=member,
            checkout_date=checkout_date or date.today(),
        )
        session.add(borrowing)
        commit_or_rollback(session, "The checkout could not be completed.")
        return borrowing


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

def list_books() -> list[Book]:
    """Return all books in title order with their authors loaded."""
    with SessionLocal() as session:
        # Eager-load authors before closing the session so display_books can
        # safely access book.authors on the returned objects.
        statement = select(Book).options(selectinload(Book.authors)).order_by(Book.title)
        return list(session.scalars(statement).all())


def search_books_by_title(title: str) -> list[Book]:
    """Return books containing a case-insensitive title term."""
    term = clean_required(title, "Search term")
    with SessionLocal() as session:
        statement = (
            select(Book)
            # ilike plus surrounding % wildcards performs contains matching.
            .where(Book.title.ilike(f"%{term}%"))
            .options(selectinload(Book.authors))
            .order_by(Book.title)
        )
        return list(session.scalars(statement).all())


def find_books_by_author(author_name: str) -> list[Book]:
    """Return books written by matching authors."""
    term = clean_required(author_name, "Author name")
    with SessionLocal() as session:
        statement = (
            select(Book)
            # Join through the many-to-many relationship instead of manually
            # joining the association table.
            .join(Book.authors)
            .where(Author.name.ilike(f"%{term}%"))
            .options(selectinload(Book.authors))
            # A book with multiple matching authors should appear only once.
            .distinct()
            .order_by(Book.title)
        )
        return list(session.scalars(statement).all())


def list_member_borrowings(member_id: int) -> list[Borrowing]:
    """Return a member's active borrowings."""
    with SessionLocal() as session:
        if session.get(Member, member_id) is None:
            raise ValueError("Member not found.")
        statement = (
            select(Borrowing)
            # NULL return_date is the application's definition of an active loan.
            .where(Borrowing.member_id == member_id, Borrowing.return_date.is_(None))
            # joinedload fetches the small related Book/Member rows in this query.
            .options(joinedload(Borrowing.book), joinedload(Borrowing.member))
            .order_by(Borrowing.checkout_date)
        )
        return list(session.scalars(statement).all())


def list_overdue_books(days: int = 14, as_of: date | None = None) -> list[Borrowing]:
    """Return active borrowings older than the configured loan period."""
    if days < 1:
        raise ValueError("Loan period must be at least one day.")
    # The optional as_of value makes this function deterministic in tests.
    cutoff = (as_of or date.today()) - timedelta(days=days)
    with SessionLocal() as session:
        statement = (
            select(Borrowing)
            .where(Borrowing.return_date.is_(None), Borrowing.checkout_date < cutoff)
            .options(joinedload(Borrowing.book), joinedload(Borrowing.member))
            .order_by(Borrowing.checkout_date)
        )
        return list(session.scalars(statement).all())


# ---------------------------------------------------------------------------
# UPDATE
# ---------------------------------------------------------------------------

def return_book(borrowing_id: int, return_date: date | None = None) -> Borrowing:
    """Return a borrowed book and restore one available copy."""
    with SessionLocal() as session:
        borrowing = session.get(
            Borrowing,
            borrowing_id,
            # The CLI prints the book title after the session closes, so load the
            # related objects while the session is still active.
            options=(joinedload(Borrowing.book), joinedload(Borrowing.member)),
        )
        if borrowing is None:
            raise ValueError("Borrowing not found.")
        if borrowing.return_date is not None:
            raise ValueError("This book has already been returned.")
        returned_on = return_date or date.today()
        if returned_on < borrowing.checkout_date:
            raise ValueError("Return date cannot be before checkout date.")

        # Both changes commit together, keeping loan state and inventory aligned.
        borrowing.return_date = returned_on
        borrowing.book.available_copies += 1
        commit_or_rollback(session, "The return could not be completed.")
        return borrowing


def update_member_email(member_id: int, new_email: str) -> Member:
    """Update and return a member's email."""
    with SessionLocal() as session:
        member = session.get(Member, member_id)
        if member is None:
            raise ValueError("Member not found.")
        member.email = valid_email(new_email)
        # The database unique constraint catches an address used by another member.
        commit_or_rollback(
            session, f"A member with email {member.email} already exists."
        )
        return member


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_book(book_id: int) -> None:
    """Delete a book only when it has no active borrowings."""
    with SessionLocal() as session:
        book = session.get(Book, book_id)
        if book is None:
            raise ValueError("Book not found.")
        # We only need to know whether one active row exists; selecting an ID
        # with LIMIT 1 is cheaper than loading every historical borrowing.
        active_id = session.scalar(
            select(Borrowing.id)
            .where(Borrowing.book_id == book_id, Borrowing.return_date.is_(None))
            .limit(1)
        )
        if active_id is not None:
            raise ValueError("Cannot delete a book that is currently borrowed.")
        session.delete(book)
        commit_or_rollback(session, "The book could not be deleted.")


def delete_member(member_id: int) -> None:
    """Delete a member only when they have no active borrowings."""
    with SessionLocal() as session:
        member = session.get(Member, member_id)
        if member is None:
            raise ValueError("Member not found.")
        # Historical returned loans do not block deletion; active loans do.
        active_id = session.scalar(
            select(Borrowing.id)
            .where(Borrowing.member_id == member_id, Borrowing.return_date.is_(None))
            .limit(1)
        )
        if active_id is not None:
            raise ValueError("Cannot delete a member with active borrowings.")
        session.delete(member)
        commit_or_rollback(session, "The member could not be deleted.")


# ---------------------------------------------------------------------------
# BUILT-IN SAMPLE DATA
# ---------------------------------------------------------------------------

SAMPLE_AUTHORS = [
    ("J.R.R. Tolkien", "English author and professor known for Middle-earth."),
    ("George Orwell", "English novelist and essayist known for 1984."),
    ("Jane Austen", "English novelist known for romantic fiction."),
]

SAMPLE_BOOKS = [
    ("The Hobbit", "978-0618260300", 1937, 3, ["J.R.R. Tolkien"]),
    ("1984", "978-0451524935", 1949, 2, ["George Orwell"]),
    ("Animal Farm", "978-0451526342", 1945, 2, ["George Orwell"]),
    ("Pride and Prejudice", "978-0141439518", 1813, 2, ["Jane Austen"]),
    ("Sense and Sensibility", "978-0141439662", 1811, 1, ["Jane Austen"]),
]

SAMPLE_MEMBERS = [
    ("Alice Chen", "alice@example.com"),
    ("Bob Martinez", "bob@example.com"),
    ("Clara Okafor", "clara@example.com"),
    ("David Kim", "david@example.com"),
]

SAMPLE_BORROWINGS = [
    ("978-0618260300", "alice@example.com", "2026-05-01", "2026-05-10"),
    ("978-0451524935", "bob@example.com", "2026-05-15", "2026-05-28"),
    ("978-0141439518", "clara@example.com", "2026-05-20", None),
    ("978-0451526342", "alice@example.com", "2026-05-22", None),
    ("978-0618260300", "david@example.com", "2026-05-25", None),
    ("978-0141439662", "bob@example.com", "2026-05-10", "2026-05-20"),
]


def seed_database() -> None:
    """Insert the built-in sample data once, including six dated borrowings."""
    init_db()
    with SessionLocal() as session:
        # Make seeding repeatable instead of inserting duplicate sample records.
        if session.scalar(select(func.count(Book.id))):
            print("Seed skipped: the database already contains books.")
            return

    # Insert parent records before child/association records so all referenced
    # authors, books, and members exist before borrowings are created.
    for name, bio in SAMPLE_AUTHORS:
        add_author(name, bio)
    for title, isbn, year, copies, authors in SAMPLE_BOOKS:
        add_book(title, isbn, year, copies, authors)
    for name, email in SAMPLE_MEMBERS:
        add_member(name, email)

    with SessionLocal() as session:
        # The sample loans identify records by stable ISBN/email values. Convert
        # those values to database IDs expected by checkout_book().
        book_ids = dict(session.execute(select(Book.isbn, Book.id)).all())
        member_ids = dict(session.execute(select(Member.email, Member.id)).all())

    for isbn, email, checked_out, returned in SAMPLE_BORROWINGS:
        # Use the same public CRUD functions as the CLI, but preserve the dates
        # from the sample records so overdue reporting has useful demo results.
        borrowing = checkout_book(
            book_ids[isbn], member_ids[email], date.fromisoformat(checked_out)
        )
        if returned:
            return_book(borrowing.id, date.fromisoformat(returned))

    print("Seed complete: 3 authors, 5 books, 4 members, and 6 borrowings added.")


# ---------------------------------------------------------------------------
# COMMAND-LINE INTERFACE
# ---------------------------------------------------------------------------

def optional_int(prompt: str) -> int | None:
    """Read an optional integer from input."""
    raw = input(prompt).strip()
    # Returning None lets the caller distinguish blank input from zero.
    return None if not raw else int(raw)


def display_books(books: list[Book]) -> None:
    """Print books in a compact, readable format."""
    if not books:
        print("No books found.")
        return
    for book in books:
        authors = ", ".join(author.name for author in book.authors) or "Unknown author"
        print(
            f"[{book.id}] {book.title} — {authors} | ISBN: {book.isbn} | "
            f"Available: {book.available_copies}"
        )


def handle_add_book() -> None:
    """Collect book details and create a book."""
    try:
        title = input("Title: ")
        isbn = input("ISBN: ")
        year = optional_int("Year published (optional): ")
        copies = optional_int("Available copies [1]: ")
        raw_authors = input("Author name(s), comma-separated (optional): ")
        authors = [item.strip() for item in raw_authors.split(",") if item.strip()]
        book = add_book(title, isbn, year, 1 if copies is None else copies, authors)
        print(f"Added '{book.title}' with book ID {book.id}.")
    # int() conversion and CRUD validation both raise ValueError, so one handler
    # can turn every invalid input into a readable message without ending the app.
    except ValueError as exc:
        print(f"Could not add book: {exc}")


def handle_add_member() -> None:
    """Collect member details and register a member."""
    try:
        member = add_member(input("Name: "), input("Email: "))
        print(f"Registered {member.name} with member ID {member.id}.")
    except ValueError as exc:
        print(f"Could not add member: {exc}")


def handle_search_books() -> None:
    """Search by title or author."""
    try:
        method = input("Search by (1) title or (2) author? [1]: ").strip() or "1"
        if method == "2":
            results = find_books_by_author(input("Author keyword: "))
        else:
            results = search_books_by_title(input("Title keyword: "))
        display_books(results)
    except ValueError as exc:
        print(f"Search error: {exc}")


def handle_checkout() -> None:
    """Check out a selected book to a member."""
    try:
        display_books(list_books())
        borrowing = checkout_book(
            int(input("Book ID: ").strip()), int(input("Member ID: ").strip())
        )
        print(f"Checkout complete. Borrowing ID: {borrowing.id}.")
    except ValueError as exc:
        print(f"Could not check out book: {exc}")


def handle_return() -> None:
    """Return a book using its borrowing ID."""
    try:
        borrowing = return_book(int(input("Borrowing ID: ").strip()))
        print(f"Returned '{borrowing.book.title}' successfully.")
    except ValueError as exc:
        print(f"Could not return book: {exc}")


def handle_member_borrowings() -> None:
    """Display all active borrowings for one member."""
    try:
        loans = list_member_borrowings(int(input("Member ID: ").strip()))
        if not loans:
            print("This member has no active borrowings.")
        for loan in loans:
            print(f"[{loan.id}] {loan.book.title} — checked out {loan.checkout_date}")
    except ValueError as exc:
        print(f"Could not list borrowings: {exc}")


def handle_overdue() -> None:
    """Display all active loans older than a chosen loan period."""
    try:
        days = optional_int("Loan period in days [14]: ")
        loans = list_overdue_books(14 if days is None else days)
        if not loans:
            print("No overdue books.")
        for loan in loans:
            print(
                f"[{loan.id}] {loan.book.title} — {loan.member.name} "
                f"({loan.member.email}), checked out {loan.checkout_date}"
            )
    except ValueError as exc:
        print(f"Could not list overdue books: {exc}")


def main() -> None:
    """Initialize the database and run the menu until exit."""
    init_db()
    # Mapping choices to functions keeps the loop shorter and avoids a long
    # if/elif chain. Exit remains separate because it breaks the loop.
    handlers = {
        "1": handle_add_book,
        "2": handle_add_member,
        "3": handle_search_books,
        "4": handle_checkout,
        "5": handle_return,
        "6": handle_member_borrowings,
        "7": handle_overdue,
    }

    while True:
        print("\n📚 Library Management System")
        print("1. Add a book")
        print("2. Add a member")
        print("3. Search books")
        print("4. Check out a book")
        print("5. Return a book")
        print("6. View member's borrowings")
        print("7. View overdue books")
        print("8. Exit")

        choice = input("\nChoose an option (1-8): ").strip()
        if choice == "8":
            print("Goodbye!")
            break
        handler = handlers.get(choice)
        if handler is None:
            print("Invalid choice. Please enter 1-8.")
        else:
            # Each handler owns its prompts, CRUD call, and user-facing errors.
            handler()


if __name__ == "__main__":
    # --seed provides sample data without changing the required 1–8 menu.
    if "--seed" in sys.argv:
        seed_database()
    else:
        main()
