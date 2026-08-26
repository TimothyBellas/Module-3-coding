# Library Management System

A command-line library application built with Python, SQLite, and SQLAlchemy 2.0. It manages books, authors, members, and borrowing records.

## Features

* Add books and members
* Search by title or author
* Check out and return books
* View a member’s active borrowings
* View overdue books
* Prevent unavailable books from being borrowed
* Prevent books or members with active borrowings from being deleted
* Load sample data

## Database Design

The application includes:

* `books` — title, ISBN, publication year, and available copies
* `authors` — name and optional biography
* `members` — name, unique email, and membership date
* `borrowings` — book, member, checkout date, and return date
* `book_authors` — connects books and authors

Books and authors have a many-to-many relationship. Books and members are connected through borrowing records.

## Setup

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the dependency:

```powershell
python -m pip install -r requirements.txt
```

The `requirements.txt` file contains:

```text
SQLAlchemy==2.0.52
```

## Run the Application

Load the sample data once:

```powershell
python .\database.py --seed
```

Start the menu:

```powershell
python .\database.py
```

## Project Files

```text
project/
├── database.py
├── README.md
├── requirements.txt
└── .gitignore
```

The program creates `library.db` automatically.

## Author

Created by **YOUR NAME** for the Coding Temple Module 3 database project.
