import sqlite3


def print_results(title, cursor):
    """Print a query's column names and rows in a readable format."""
    print(f"\n{title}")
    print("-" * len(title))

    column_names = [description[0] for description in cursor.description]
    print(" | ".join(column_names))
    print("-" * 70)

    rows = cursor.fetchall()
    if not rows:
        print("No results found.")
        return

    for row in rows:
        print(" | ".join("None" if value is None else str(value) for value in row))


def main():
    # An in-memory database exists only while this program is running.
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    cursor.executescript(
        """
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            location TEXT NOT NULL
        );

        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            salary REAL NOT NULL,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        );

        CREATE TABLE projects (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            employee_id INTEGER NOT NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        );
        """
    )

    departments = [
        (1, "Engineering", "Chicago"),
        (2, "Marketing", "New York"),
        (3, "Human Resources", "Dallas"),
        (4, "Research", "Seattle"),  # This department has no employees.
    ]

    employees = [
        (1, "Ava Johnson", "Software Engineer", 92000, 1),
        (2, "Liam Smith", "Senior Developer", 110000, 1),
        (3, "Noah Williams", "QA Engineer", 78000, 1),
        (4, "Emma Brown", "Marketing Manager", 88000, 2),
        (5, "Olivia Davis", "Content Specialist", 67000, 2),
        (6, "Ethan Miller", "HR Manager", 85000, 3),
        (7, "Sophia Wilson", "Recruiter", 65000, 3),
        (8, "Mason Moore", "DevOps Engineer", 97000, 1),
    ]

    projects = [
        (1, "Customer Portal", 1),
        (2, "Cloud Migration", 2),
        (3, "Holiday Campaign", 4),
        (4, "Employee Onboarding", 6),
        (5, "Automated Testing", 1),
    ]

    cursor.executemany(
        "INSERT INTO departments (id, name, location) VALUES (?, ?, ?)",
        departments,
    )
    cursor.executemany(
        """
        INSERT INTO employees (id, name, role, salary, department_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        employees,
    )
    cursor.executemany(
        "INSERT INTO projects (id, title, employee_id) VALUES (?, ?, ?)",
        projects,
    )
    connection.commit()

    # Query 1: All employees with their department name (INNER JOIN).
    cursor.execute(
        """
        SELECT e.name AS employee, e.role, d.name AS department
        FROM employees AS e
        INNER JOIN departments AS d ON e.department_id = d.id
        ORDER BY e.name;
        """
    )
    print_results("QUERY 1: Employees and their departments", cursor)

    # Query 2: All departments, including departments with no employees.
    cursor.execute(
        """
        SELECT d.name AS department, d.location, e.name AS employee
        FROM departments AS d
        LEFT JOIN employees AS e ON d.id = e.department_id
        ORDER BY d.name, e.name;
        """
    )
    print_results("QUERY 2: All departments and their employees", cursor)

    # Query 3: All employees and any projects they lead.
    cursor.execute(
        """
        SELECT e.name AS employee, e.role, p.title AS project
        FROM employees AS e
        LEFT JOIN projects AS p ON e.id = p.employee_id
        ORDER BY e.name, p.title;
        """
    )
    print_results("QUERY 3: All employees and projects they lead", cursor)

    # Query 4: Employees who do not lead a project.
    cursor.execute(
        """
        SELECT e.name AS employee, e.role
        FROM employees AS e
        LEFT JOIN projects AS p ON e.id = p.employee_id
        WHERE p.id IS NULL
        ORDER BY e.name;
        """
    )
    print_results("QUERY 4: Employees who do not lead a project", cursor)

    # Query 5: Projects with each lead's name and department (three tables).
    cursor.execute(
        """
        SELECT p.title AS project,
               e.name AS project_lead,
               d.name AS department
        FROM projects AS p
        INNER JOIN employees AS e ON p.employee_id = e.id
        INNER JOIN departments AS d ON e.department_id = d.id
        ORDER BY p.title;
        """
    )
    print_results("QUERY 5: Projects, leads, and departments", cursor)

    connection.close()


if __name__ == "__main__":
    main()
