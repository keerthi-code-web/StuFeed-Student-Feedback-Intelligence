"""
StuFeed academic data seeder.

- Adds missing departments, semester-specific subjects and sample instructors.
- Preserves existing records and instructor assignments.
- Does not create student records or feedback.
- Idempotent: safe to run repeatedly.
- Handles globally unique subject names safely.
- Rolls back all changes if validation fails.

Run from the backend directory using the project's .venv Python.
"""

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal, engine
from app.models import Department, Subject, Instructor


DEPARTMENTS = [
    ("Artificial Intelligence and Data Science", "AIDS"),
    ("Artificial Intelligence and Machine Learning", "AIML"),
    ("Information Technology", "IT"),
    ("Computer Science and Engineering", "CSE"),
    ("Chemical Engineering", "CHEM"),
    ("Biomedical Engineering", "BME"),
]


# Six subjects for Semesters 1-6, four for Semester 7,
# and three for Semester 8.
SUBJECTS = {
    "AIDS": [
        ["Mathematics I", "Engineering Physics", "Programming in Python",
         "Engineering Graphics", "Basic Electrical Engineering", "Python Programming Lab"],
        ["Mathematics II", "Statistics for Data Science", "Data Structures",
         "Digital Systems", "Database Fundamentals", "Data Structures Lab"],
        ["Probability and Statistical Inference", "Object Oriented Programming",
         "Data Structures and Algorithms", "Database Management Systems",
         "Data Visualization", "DBMS Lab"],
        ["Linear Algebra for Data Science", "Machine Learning Fundamentals",
         "Operating Systems", "Computer Networks", "Exploratory Data Analysis",
         "Machine Learning Lab"],
        ["Deep Learning", "Big Data Analytics", "Data Mining",
         "Cloud Computing", "Natural Language Processing", "Big Data Lab"],
        ["Time Series Analysis", "Computer Vision", "Data Engineering",
         "Information Retrieval", "MLOps Fundamentals", "Applied AI Lab"],
        ["Generative AI", "Responsible AI and Governance",
         "Advanced Predictive Analytics", "Industry Project I"],
        ["Data Science Capstone", "AI Product Development",
         "Industry Internship and Seminar"],
    ],
    "AIML": [
        ["Mathematics I", "Engineering Physics", "Programming in Python",
         "Engineering Graphics", "Basic Electrical Engineering", "Python Lab"],
        ["Mathematics II", "Discrete Mathematics", "Object Oriented Programming",
         "Digital Logic", "Engineering Chemistry", "Programming Lab II"],
        ["Linear Algebra", "Data Structures", "Database Management Systems",
         "Computer Organization", "Probability for AI", "Data Structures Lab"],
        ["Machine Learning", "Operating Systems", "Computer Networks",
         "Optimization Techniques", "Design and Analysis of Algorithms",
         "Machine Learning Lab"],
        ["Deep Learning", "Natural Language Processing", "Computer Vision",
         "Reinforcement Learning", "Cloud Computing", "Deep Learning Lab"],
        ["Generative AI", "Knowledge Representation", "MLOps",
         "AI Security", "Edge AI Systems", "Applied AI Lab"],
        ["Large Language Models", "AI Ethics and Governance",
         "Advanced Reinforcement Learning", "Industry Project I"],
        ["AI Capstone Project", "Intelligent Systems Deployment",
         "Industry Internship and Seminar"],
    ],
    "IT": [
        ["Mathematics I", "Engineering Physics", "Programming in C",
         "Engineering Graphics", "Basic Electrical Engineering", "C Programming Lab"],
        ["Mathematics II", "Object Oriented Programming", "Digital Logic",
         "Data Structures", "Communication Skills", "Programming Lab II"],
        ["Discrete Mathematics", "Database Management Systems",
         "Computer Organization", "Java Programming", "Web Technologies",
         "DBMS Lab"],
        ["Operating Systems", "Computer Networks", "Design and Analysis of Algorithms",
         "Software Engineering", "Full Stack Development", "Networks Lab"],
        ["Cloud Computing", "Cybersecurity Fundamentals", "Big Data Technologies",
         "Mobile Application Development", "DevOps Engineering", "Cloud Lab"],
        ["Distributed Systems", "Data Warehousing", "Internet of Things",
         "Information Security", "Enterprise Application Development",
         "Data Engineering Lab"],
        ["Cloud Native Applications", "Site Reliability Engineering",
         "Advanced Cybersecurity", "Industry Project I"],
        ["IT Capstone Project", "Enterprise Systems Integration",
         "Industry Internship and Seminar"],
    ],
    "CSE": [
        ["Mathematics I", "Engineering Physics", "Programming in C",
         "Engineering Graphics", "Basic Electrical Engineering", "C Programming Lab"],
        ["Mathematics II", "Discrete Mathematics", "Object Oriented Programming",
         "Digital Logic Design", "Engineering Chemistry", "OOP Lab"],
        ["Data Structures", "Computer Organization", "Database Management Systems",
         "Probability and Statistics", "Java Programming", "Data Structures Lab"],
        ["Operating Systems", "Computer Networks", "Design and Analysis of Algorithms",
         "Theory of Computation", "Software Engineering", "OS and Networks Lab"],
        ["Artificial Intelligence", "Compiler Design", "Distributed Systems",
         "Web Application Development", "Computer Security", "Full Stack Lab"],
        ["Machine Learning", "Cloud Computing", "Big Data Systems",
         "Mobile Computing", "Information Retrieval", "Cloud and Data Lab"],
        ["Advanced Algorithms", "Blockchain Systems",
         "Secure Software Engineering", "Industry Project I"],
        ["CSE Capstone Project", "System Design and Deployment",
         "Industry Internship and Seminar"],
    ],
    "CHEM": [
        ["Engineering Mathematics I", "Engineering Physics", "Engineering Chemistry",
         "Engineering Mechanics", "Basic Electrical Engineering", "Chemistry Lab"],
        ["Engineering Mathematics II", "Material Science", "Fluid Mechanics",
         "Chemical Process Calculations", "Thermodynamics I", "Engineering Lab II"],
        ["Chemical Engineering Thermodynamics", "Mechanical Operations",
         "Heat Transfer", "Chemical Process Principles", "Numerical Methods",
         "Mechanical Operations Lab"],
        ["Mass Transfer", "Chemical Reaction Engineering I",
         "Process Instrumentation", "Momentum Transfer", "Environmental Engineering",
         "Heat Transfer Lab"],
        ["Chemical Reaction Engineering II", "Process Control",
         "Separation Processes", "Process Equipment Design",
         "Industrial Safety", "Reaction Engineering Lab"],
        ["Petroleum and Petrochemical Technology", "Process Simulation",
         "Biochemical Engineering", "Process Optimization",
         "Pollution Control Engineering", "Process Control Lab"],
        ["Process Systems Engineering", "Advanced Separation Technology",
         "Sustainable Chemical Processes", "Industry Project I"],
        ["Chemical Engineering Capstone", "Plant Design and Economics",
         "Industry Internship and Seminar"],
    ],
    "BME": [
        ["Engineering Mathematics I", "Engineering Physics", "Human Anatomy",
         "Engineering Chemistry", "Basic Electrical Engineering", "Physics Lab"],
        ["Engineering Mathematics II", "Human Physiology", "Biochemistry",
         "Medical Terminology", "Basic Electronics", "Physiology Lab"],
        ["Biomedical Instrumentation", "Signals and Systems",
         "Anatomy and Physiology II", "Digital Electronics",
         "Medical Sensors", "Instrumentation Lab"],
        ["Biomedical Signal Processing", "Medical Imaging Systems",
         "Microcontrollers", "Biomaterials", "Clinical Engineering",
         "Biomedical Signals Lab"],
        ["Biomedical Equipment Design", "Image Processing in Healthcare",
         "Biomechanics", "Hospital Information Systems",
         "Rehabilitation Engineering", "Medical Imaging Lab"],
        ["AI in Healthcare", "Wearable Medical Devices",
         "Medical Device Regulations", "Bioinformatics",
         "Embedded Medical Systems", "Healthcare AI Lab"],
        ["Advanced Medical Image Analysis", "Digital Health Systems",
         "Medical Device Innovation", "Industry Project I"],
        ["Biomedical Engineering Capstone", "Clinical Technology Evaluation",
         "Industry Internship and Seminar"],
    ],
}


def get_department(db, name, code):
    """Get an existing department without overwriting its settings."""
    dept = db.query(Department).filter(
        Department.name.ilike(name)
    ).first()

    if dept is None:
        dept = Department(
            name=name,
            code=code,
            is_active=True,
        )
        db.add(dept)
        db.flush()
        print(f"Added department: {name}")

    if not dept.is_active:
        raise RuntimeError(
            f"Department '{name}' is inactive. "
            "Review its status in Academic Management before seeding."
        )

    return dept


def get_or_create_faculty(db, dept, code, faculty_number):
    """
    Create or reuse sample faculty.
    Never overwrite an existing instructor's details.
    """
    name = f"{code} Sample Faculty {faculty_number:02d}"

    instructor = db.query(Instructor).filter(
        Instructor.name.ilike(name)
    ).first()

    if instructor is None:
        instructor = Instructor(
            name=name,
            department_id=dept.id,
            department_name=dept.name,
            department=dept.name,
            is_active=True,
        )
        db.add(instructor)
        db.flush()
        return instructor, True

    if not instructor.is_active:
        raise RuntimeError(
            f"Sample instructor '{name}' is inactive. "
            "Review it before rerunning the seeder."
        )

    if instructor.department_id != dept.id:
        raise RuntimeError(
            f"Sample instructor '{name}' belongs to another department."
        )

    return instructor, False


def make_unique_subject_name(db, original_name, dept, semester):
    """
    Respect the existing database rule that subject names must be unique
    globally, rather than only within a department.

    Keep the original name when available. If another department already
    uses it, append the department code and semester.
    """
    existing = db.query(Subject).filter(
        Subject.name.ilike(original_name)
    ).first()

    if existing is None:
        return original_name

    if existing.department_id == dept.id:
        # The caller should have found and reused this department's subject.
        # If it did not, fail safely rather than create a duplicate.
        raise RuntimeError(
            f"Subject '{original_name}' already exists in "
            f"{dept.name}, but could not be reused. "
            "No changes will be committed."
        )

    suffix = f" ({dept.code} S{semester})"
    candidate = f"{original_name}{suffix}"
    counter = 2

    while db.query(Subject).filter(
        Subject.name.ilike(candidate)
    ).first() is not None:
        candidate = f"{original_name}{suffix}-{counter}"
        counter += 1

    return candidate


def run_seed():
    # Check ORM model and real database schema before doing any work.
    if not hasattr(Subject, "semester"):
        raise RuntimeError(
            "Subject.semester is missing from the loaded model. "
            "Seed stopped without modifying data."
        )

    schema = inspect(engine)
    table_names = set(schema.get_table_names())

    required_tables = {"departments", "subjects", "instructors"}
    missing_tables = required_tables - table_names

    if missing_tables:
        raise RuntimeError(
            "Required database tables are missing: "
            + ", ".join(sorted(missing_tables))
        )

    subject_columns = {
        column["name"] for column in schema.get_columns("subjects")
    }

    if "semester" not in subject_columns:
        raise RuntimeError(
            "The subjects table has no semester column. "
            "Seed stopped without modifying data."
        )

    db = SessionLocal()

    added_departments = 0
    added_subjects = 0
    added_instructors = 0
    added_assignments = 0
    reused_subjects = 0

    try:
        # Verify the supplied dataset before creating records.
        if set(SUBJECTS.keys()) != {code for _, code in DEPARTMENTS}:
            raise RuntimeError(
                "Department codes in SUBJECTS do not match DEPARTMENTS."
            )

        expected_total = 0

        for _, code in DEPARTMENTS:
            if len(SUBJECTS[code]) != 8:
                raise RuntimeError(
                    f"{code} must have exactly 8 semester lists."
                )

            for semester, names in enumerate(SUBJECTS[code], start=1):
                expected = 6 if semester <= 6 else (
                    4 if semester == 7 else 3
                )

                if len(names) != expected:
                    raise RuntimeError(
                        f"{code} semester {semester} has {len(names)} "
                        f"subjects; expected {expected}."
                    )

                if len({name.casefold() for name in names}) != len(names):
                    raise RuntimeError(
                        f"{code} semester {semester} has duplicate subject names."
                    )

                expected_total += len(names)

        if expected_total != 258:
            raise RuntimeError(
                f"Dataset has {expected_total} subject slots; expected 258."
            )

        for dept_name, dept_code in DEPARTMENTS:
            department_existed = db.query(Department).filter(
                Department.name.ilike(dept_name)
            ).first() is not None

            dept = get_department(db, dept_name, dept_code)

            if not department_existed:
                added_departments += 1

            # Six sample instructors per department.
            faculty = []

            for number in range(1, 7):
                instructor, was_added = get_or_create_faculty(
                    db, dept, dept_code, number
                )

                if was_added:
                    added_instructors += 1

                faculty.append(instructor)

            for semester, names in enumerate(
                SUBJECTS[dept_code], start=1
            ):
                for index, original_name in enumerate(names, start=1):
                    subject_code = (
                        f"{dept_code}-S{semester:02d}-{index:02d}"
                    )

                    # Stable code is the primary idempotency key.
                    subject = db.query(Subject).filter(
                        Subject.department_id == dept.id,
                        Subject.code == subject_code,
                    ).first()

                    # Reuse a manually entered subject with the original name.
                    if subject is None:
                        subject = db.query(Subject).filter(
                            Subject.department_id == dept.id,
                            Subject.name.ilike(original_name),
                        ).first()

                    if subject is not None:
                        reused_subjects += 1

                        if subject.semester != semester:
                            raise RuntimeError(
                                f"Existing subject '{subject.name}' in "
                                f"{dept.name} has semester {subject.semester}, "
                                f"but the seed dataset expects semester "
                                f"{semester}. Review it before rerunning."
                            )

                    else:
                        # Apply a suffix only when another department already
                        # uses the same global subject name.
                        safe_name = make_unique_subject_name(
                            db,
                            original_name,
                            dept,
                            semester,
                        )

                        subject = Subject(
                            department_id=dept.id,
                            code=subject_code,
                            name=safe_name,
                            semester=semester,
                            is_active=True,
                        )
                        db.add(subject)
                        db.flush()
                        added_subjects += 1

                    if not subject.is_active:
                        raise RuntimeError(
                            f"Subject '{subject.name}' is inactive. "
                            "Review it before rerunning."
                        )

                    assigned = list(subject.instructors)

                    if len(assigned) > 2:
                        raise RuntimeError(
                            f"Subject '{subject.name}' already has "
                            f"{len(assigned)} instructors. The seeder will "
                            "not remove existing assignments."
                        )

                    for instructor in assigned:
                        if instructor.department_id != dept.id:
                            raise RuntimeError(
                                f"Subject '{subject.name}' has an instructor "
                                "from another department. Review the assignment."
                            )

                    # Preserve all existing assignments. Add faculty only
                    # when the subject has no instructor assigned.
                    if not assigned:
                        first = faculty[(index - 1) % len(faculty)]
                        subject.instructors.append(first)
                        added_assignments += 1

                        # Add a second instructor to selected subjects.
                        if index % 3 == 0:
                            second = faculty[index % len(faculty)]

                            if second.id != first.id:
                                subject.instructors.append(second)
                                added_assignments += 1

        # Final validation before committing the transaction.
        db.flush()

        for dept_name, dept_code in DEPARTMENTS:
            dept = db.query(Department).filter(
                Department.name.ilike(dept_name)
            ).first()

            if dept is None:
                raise RuntimeError(
                    f"Validation failed: department {dept_name} is missing."
                )

            for semester, names in enumerate(
                SUBJECTS[dept_code], start=1
            ):
                for index, original_name in enumerate(names, start=1):
                    code = f"{dept_code}-S{semester:02d}-{index:02d}"

                    subject = db.query(Subject).filter(
                        Subject.department_id == dept.id,
                        Subject.code == code,
                    ).first()

                    if subject is None:
                        # A manually entered subject may have another code.
                        subject = db.query(Subject).filter(
                            Subject.department_id == dept.id,
                            Subject.name.ilike(original_name),
                            Subject.semester == semester,
                        ).first()

                    if subject is None:
                        # Look for the department-specific name used for
                        # globally duplicated subject names.
                        prefix = f"{original_name} ({dept_code} S{semester})"
                        subject = db.query(Subject).filter(
                            Subject.department_id == dept.id,
                            Subject.name.ilike(f"{prefix}%"),
                            Subject.semester == semester,
                        ).first()

                    if subject is None:
                        raise RuntimeError(
                            f"Validation failed for {dept_code}, "
                            f"semester {semester}, subject '{original_name}'."
                        )

                    if subject.department_id != dept.id:
                        raise RuntimeError(
                            f"Subject '{subject.name}' belongs to the wrong department."
                        )

                    if subject.semester != semester:
                        raise RuntimeError(
                            f"Subject '{subject.name}' is in the wrong semester."
                        )

                    instructor_count = len(subject.instructors)

                    if not 1 <= instructor_count <= 2:
                        raise RuntimeError(
                            f"Subject '{subject.name}' has "
                            f"{instructor_count} instructors; expected 1 or 2."
                        )

                    if any(
                        instructor.department_id != dept.id
                        for instructor in subject.instructors
                    ):
                        raise RuntimeError(
                            f"Subject '{subject.name}' has an instructor "
                            "from another department."
                        )

        # Only commit after every check has passed.
        db.commit()

        print("\nACADEMIC SEED COMPLETED SUCCESSFULLY")
        print(f"Departments added: {added_departments}")
        print(f"Subjects added: {added_subjects}")
        print(f"Existing subjects reused: {reused_subjects}")
        print(f"Sample instructors added: {added_instructors}")
        print(f"Instructor assignments added: {added_assignments}")
        print("Departments configured: 6")
        print("Semesters per department: 8")
        print("Target subject slots: 258")
        print("Instructor assignments per subject: 1-2")
        print("Student feedback records created: 0")

        print("\nACTIVE SUBJECT COUNTS BY DEPARTMENT AND SEMESTER")

        for dept_name, dept_code in DEPARTMENTS:
            dept = db.query(Department).filter(
                Department.name.ilike(dept_name)
            ).first()

            counts = []

            for semester in range(1, 9):
                count = db.query(Subject).filter(
                    Subject.department_id == dept.id,
                    Subject.semester == semester,
                    Subject.is_active.is_(True),
                ).count()

                counts.append(f"S{semester}={count}")

            print(f"{dept_code}: " + ", ".join(counts))

        print("\nExisting feedback was not deleted or modified.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    try:
        run_seed()
    except (RuntimeError, SQLAlchemyError) as exc:
        print(f"\nSEED STOPPED: {exc}")
        print("The seeder rolled back this run's uncommitted changes.")
        raise SystemExit(1)