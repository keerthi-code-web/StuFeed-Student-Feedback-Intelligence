
"""
StuFeed academic data seeder.

- Adds missing departments, semester-specific subjects and sample instructors.
- Preserves existing records and existing subject/instructor assignments.
- Does not create student records or feedback.
- Idempotent: safe to run repeatedly.
- Aborts and rolls back if semester support or data consistency checks fail.

Run from the backend directory using the project's .venv Python.
"""

from collections import Counter
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
        dept = Department(name=name, code=code, is_active=True)
        db.add(dept)
        db.flush()
        print(f"Added department: {name}")

    if not dept.is_active:
        raise RuntimeError(
            f"Department '{name}' is inactive. No records were changed; "
            "review its status in Academic Management first."
        )

    return dept


def get_or_create_faculty(db, dept, code, faculty_number):
    """
    Create/reuse sample faculty. Existing instructor details are never changed.
    Six sample instructors per department are reused across its subjects.
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
    else:
        if not instructor.is_active:
            raise RuntimeError(
                f"Sample instructor '{name}' already exists but is inactive. "
                "No records were changed; review it before rerunning."
            )
        if instructor.department_id != dept.id:
            raise RuntimeError(
                f"Sample instructor '{name}' belongs to another department. "
                "No records were changed."
            )

    return instructor


def run_seed():
    # Validate both the SQLAlchemy model and actual database schema first.
    if not hasattr(Subject, "semester"):
        raise RuntimeError(
            "Subject.semester is missing from the loaded model. "
            "Seed stopped without modifying data."
        )

    schema = inspect(engine)
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
    problems = []

    try:
        faculty_cache = {}

        for dept_name, dept_code in DEPARTMENTS:
            existed = db.query(Department).filter(
                Department.name.ilike(dept_name)
            ).first() is not None

            dept = get_department(db, dept_name, dept_code)
            if not existed:
                added_departments += 1

            # Create/reuse six sample instructors for this department.
            faculty = []
            for number in range(1, 7):
                before = db.query(Instructor).filter(
                    Instructor.name.ilike(
                        f"{dept_code} Sample Faculty {number:02d}"
                    )
                ).first()
                inst = get_or_create_faculty(
                    db, dept, dept_code, number
                )
                if before is None:
                    added_instructors += 1
                faculty.append(inst)

            faculty_cache[dept_code] = faculty

            for semester, names in enumerate(
                SUBJECTS[dept_code], start=1
            ):
                expected_count = 6 if semester <= 6 else (
                    4 if semester == 7 else 3
                )
                if len(names) != expected_count:
                    raise RuntimeError(
                        f"{dept_code} semester {semester} has "
                        f"{len(names)} subjects; expected {expected_count}."
                    )

                for index, subject_name in enumerate(names, start=1):
                    subject_code = (
                        f"{dept_code}-S{semester:02d}-{index:02d}"
                    )

                    # Stable code is the primary idempotency key.
                    subject = db.query(Subject).filter(
                        Subject.department_id == dept.id,
                        Subject.code == subject_code,
                    ).first()

                    # If a subject was already entered manually under the
                    # same name, reuse it rather than creating a duplicate.
                    if subject is None:
                        subject = db.query(Subject).filter(
                            Subject.department_id == dept.id,
                            Subject.name.ilike(subject_name),
                        ).first()

                    if subject is None:
                        subject = Subject(
                            department_id=dept.id,
                            code=subject_code,
                            name=subject_name,
                            semester=semester,
                            is_active=True,
                        )
                        db.add(subject)
                        db.flush()
                        added_subjects += 1
                    else:
                        reused_subjects += 1

                        # Preserve existing edits; never silently move a
                        # subject from one semester to another.
                        if subject.semester != semester:
                            raise RuntimeError(
                                f"Existing subject '{subject.name}' in "
                                f"{dept.name} has semester "
                                f"{subject.semester}, expected {semester}. "
                                "No records were committed."
                            )

                    if not subject.is_active:
                        raise RuntimeError(
                            f"Subject '{subject.name}' is inactive. "
                            "No records were committed."
                        )

                    assigned = list(subject.instructors)

                    if len(assigned) > 2:
                        raise RuntimeError(
                            f"Subject '{subject.name}' already has "
                            f"{len(assigned)} instructors. The maximum "
                            "is 2; no assignments were removed."
                        )

                    for inst in assigned:
                        if inst.department_id != dept.id:
                            raise RuntimeError(
                                f"Subject '{subject.name}' has an instructor "
                                "from another department. No records committed."
                            )

                    # Keep existing assignments. Fill only empty assignments.
                    if not assigned:
                        first = faculty[(index - 1) % len(faculty)]
                        subject.instructors.append(first)
                        added_assignments += 1

                        # Some subjects get a second instructor, never more.
                        if index % 3 == 0:
                            second = faculty[index % len(faculty)]
                            if second.id != first.id:
                                subject.instructors.append(second)
                                added_assignments += 1

        # Final validation of all seeded subject codes and assignments.
        db.flush()
        seeded_codes = [
            f"{code}-S{semester:02d}-{index:02d}"
            for _, code in DEPARTMENTS
            for semester, names in enumerate(SUBJECTS[code], start=1)
            for index, _ in enumerate(names, start=1)
        ]

        for dept_name, dept_code in DEPARTMENTS:
            dept = db.query(Department).filter(
                Department.name.ilike(dept_name)
            ).first()

            for semester, names in enumerate(
                SUBJECTS[dept_code], start=1
            ):
                for index, name in enumerate(names, start=1):
                    code = f"{dept_code}-S{semester:02d}-{index:02d}"
                    subject = db.query(Subject).filter(
                        Subject.department_id == dept.id,
                        Subject.code == code,
                    ).first()

                    if subject is None:
                        # A matching manually-created subject may have a
                        # different code; find it by department/name/semester.
                        subject = db.query(Subject).filter(
                            Subject.department_id == dept.id,
                            Subject.name.ilike(name),
                            Subject.semester == semester,
                        ).first()

                    if subject is None:
                        raise RuntimeError(
                            f"Validation failed: {dept_code} S{semester}: {name}"
                        )

                    count = len(subject.instructors)
                    if count < 1 or count > 2:
                        raise RuntimeError(
                            f"Validation failed: '{subject.name}' has "
                            f"{count} assigned instructors."
                        )

                    if subject.department_id != dept.id:
                        raise RuntimeError(
                            f"Validation failed: '{subject.name}' "
                            "belongs to the wrong department."
                        )

        db.commit()

        print("\nACADEMIC SEED COMPLETED")
        print(f"Departments added: {added_departments}")
        print(f"Subjects added: {added_subjects}")
        print(f"Existing subjects reused: {reused_subjects}")
        print(f"Sample instructors added: {added_instructors}")
        print(f"Instructor assignments added: {added_assignments}")
        print("Departments: 6")
        print("Semesters per department: 8")
        print("Target subject count: 258")
        print("Instructor assignments per subject: 1-2")
        print("Student feedback records created: 0")

        print("\nSUBJECT COUNTS BY DEPARTMENT AND SEMESTER")
        for dept_name, dept_code in DEPARTMENTS:
            dept = db.query(Department).filter(
                Department.name.ilike(dept_name)
            ).first()
            counts = []
            for semester in range(1, 9):
                count = db.query(Subject).filter(
                    Subject.department_id == dept.id,
                    Subject.semester == semester,
                    Subject.is_active == True,
                ).count()
                counts.append(f"S{semester}={count}")
            print(f"{dept_code}: " + ", ".join(counts))

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
        print("No changes from this run were committed.")
        raise SystemExit(1)
