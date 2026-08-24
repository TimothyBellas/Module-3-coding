import sqlite3


DB_NAME = "school.db"


# -----------------------------
# Create the students table
# -----------------------------
def create_table():
    """Create the students table if it does not already exist."""

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        grade INTEGER NOT NULL,
        gpa REAL
    )
    """)

    connection.commit()
    connection.close()


# -----------------------------
# CREATE
# -----------------------------
def add_student(name, grade, gpa):
    """Insert a new student if that name does not already exist."""

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO students (name, grade, gpa)
    VALUES (?, ?, ?)
    """, (name, grade, gpa))

    connection.commit()
    connection.close()


# -----------------------------
# READ ALL
# -----------------------------
def get_all_students():
    """Return all students."""

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, name, grade, gpa
    FROM students
    ORDER BY id
    """)

    students = cursor.fetchall()

    connection.close()

    return students


# -----------------------------
# READ ONE
# -----------------------------
def get_student_by_id(student_id):
    """Return one student by ID."""

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    SELECT id, name, grade, gpa
    FROM students
    WHERE id = ?
    """, (student_id,))

    student = cursor.fetchone()

    connection.close()

    return student


# -----------------------------
# UPDATE
# -----------------------------
def update_student_gpa(student_id, new_gpa):
    """Update a student's GPA."""

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    UPDATE students
    SET gpa = ?
    WHERE id = ?
    """, (new_gpa, student_id))

    connection.commit()
    connection.close()


# -----------------------------
# DELETE
# -----------------------------
def delete_student(student_id):
    """Delete a student by ID."""

    connection = sqlite3.connect(DB_NAME)
    cursor = connection.cursor()

    cursor.execute("""
    DELETE FROM students
    WHERE id = ?
    """, (student_id,))

    connection.commit()
    connection.close()


# -----------------------------
# Print students neatly
# -----------------------------
def print_students(students):
    """Display students in a clean terminal table."""

    print("\n" + "=" * 55)
    print("                   STUDENT ROSTER")
    print("=" * 55)

    print(f"{'ID':<5} {'Name':<20} {'Grade':<10} {'GPA':>8}")
    print("-" * 55)

    for student_id, name, grade, gpa in students:
        print(
            f"{student_id:<5} "
            f"{name:<20} "
            f"{grade:<10} "
            f"{gpa:>8.2f}"
        )

    print("=" * 55)


# -----------------------------
# Main program
# -----------------------------
if __name__ == "__main__":

    # Create the database table
    create_table()

    # Add students
    # INSERT OR IGNORE prevents duplicates by name
    add_student("Alice Johnson", 10, 3.7)
    add_student("Marcus Lee", 11, 3.4)
    add_student("Sophia Brown", 12, 3.9)
    add_student("Daniel Smith", 10, 3.2)

    # Print all students
    print("\nInitial Student List:")
    students = get_all_students()
    print_students(students)

    # Read one student
    student = get_student_by_id(2)

    print("\nStudent with ID 2:")
    print(student)

    # Update GPA
    update_student_gpa(2, 3.8)

    print("\nUpdated student ID 2 GPA to 3.8.")

    # Delete one student
    delete_student(4)

    print("Deleted student ID 4.")

    # Print all students again
    print("\nUpdated Student List:")
    students = get_all_students()
    print_students(students)
