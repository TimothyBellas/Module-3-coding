from typing import List

from sqlalchemy import Column, ForeignKey, Integer, String, Table, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship


engine = create_engine("sqlite:///:memory:", echo=False)


class Base(DeclarativeBase):
    pass


# This table links students to courses (many-to-many). Each pair of IDs is
# unique because both foreign-key columns form the composite primary key.
student_courses = Table(
    "student_courses",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id"), primary_key=True),
    Column("course_id", Integer, ForeignKey("courses.id"), primary_key=True),
)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    teachers: Mapped[List["Teacher"]] = relationship(back_populates="department")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id"), nullable=False
    )

    department: Mapped["Department"] = relationship(back_populates="teachers")
    courses: Mapped[List["Course"]] = relationship(back_populates="teacher")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)

    teacher: Mapped["Teacher"] = relationship(back_populates="courses")
    students: Mapped[List["Student"]] = relationship(
        secondary=student_courses,
        back_populates="courses",
    )


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    courses: Mapped[List["Course"]] = relationship(
        secondary=student_courses,
        back_populates="students",
    )


if __name__ == "__main__":
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        # Seed: 2 departments, 4 teachers, and 5 courses.
        cs = Department(name="Computer Science")
        math = Department(name="Mathematics")
        session.add_all([cs, math])
        session.flush()

        t1 = Teacher(name="Dr. Alice Park", department_id=cs.id)
        t2 = Teacher(name="Prof. Bob Chen", department_id=cs.id)
        t3 = Teacher(name="Dr. Carol White", department_id=math.id)
        t4 = Teacher(name="Prof. Dan Rivera", department_id=math.id)
        session.add_all([t1, t2, t3, t4])
        session.flush()

        c1 = Course(title="Intro to Python", teacher_id=t1.id)
        c2 = Course(title="Data Structures", teacher_id=t1.id)
        c3 = Course(title="Web Development", teacher_id=t2.id)
        c4 = Course(title="Calculus I", teacher_id=t3.id)
        c5 = Course(title="Linear Algebra", teacher_id=t4.id)
        session.add_all([c1, c2, c3, c4, c5])
        session.flush()

        # Seed: 6 students with various enrollments.
        s1 = Student(name="Zoe Adams", email="zoe@school.edu")
        s2 = Student(name="Raj Patel", email="raj@school.edu")
        s3 = Student(name="Nina Brown", email="nina@school.edu")
        s4 = Student(name="Marco Diaz", email="marco@school.edu")
        s5 = Student(name="Yuki Tanaka", email="yuki@school.edu")
        s6 = Student(name="Olu Okafor", email="olu@school.edu")
        session.add_all([s1, s2, s3, s4, s5, s6])

        # Enroll through the Student.courses relationship. back_populates keeps
        # the corresponding Course.students collections synchronized.
        s1.courses.extend([c1, c2, c4])
        s2.courses.extend([c1, c2, c3])
        s3.courses.extend([c1, c3])
        s4.courses.extend([c1, c4, c5])
        s5.courses.extend([c1, c2, c5])
        s6.courses.extend([c3, c4])
        session.commit()

    with Session(engine) as session:
        # Demo 1: traverse Department -> Teacher.
        print("=== Departments and Teachers ===")
        departments = session.scalars(select(Department).order_by(Department.name))
        for department in departments:
            teacher_names = ", ".join(
                teacher.name for teacher in sorted(department.teachers, key=lambda t: t.name)
            )
            print(f"{department.name}: {teacher_names}")
        print()

        # Demo 2: traverse Teacher -> Course.
        print("=== Teachers and Their Courses ===")
        teachers = session.scalars(select(Teacher).order_by(Teacher.name))
        for teacher in teachers:
            course_titles = ", ".join(
                course.title for course in sorted(teacher.courses, key=lambda c: c.title)
            )
            print(f"{teacher.name}: {course_titles}")
        print()

        # Demo 3: traverse Course -> Student across the association table.
        print("=== Courses and Enrolled Students ===")
        courses = session.scalars(select(Course).order_by(Course.title))
        for course in courses:
            student_names = ", ".join(
                student.name for student in sorted(course.students, key=lambda s: s.name)
            )
            print(f"{course.title}: {student_names}")
        print()

        # Demo 4: traverse Student -> Course in the reverse direction.
        print("=== Students and Their Courses ===")
        students = session.scalars(select(Student).order_by(Student.name))
        for student in students:
            course_titles = ", ".join(
                course.title for course in sorted(student.courses, key=lambda c: c.title)
            )
            print(f"{student.name}: {course_titles}")
        print()

        # Demo 5: filter the loaded relationship collections in Python.
        print("=== Courses With More Than 3 Students ===")
        courses = session.scalars(select(Course).order_by(Course.title))
        for course in courses:
            if len(course.students) > 3:
                print(f"{course.title}: {len(course.students)} students")
        print()
