import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "feedback.db")

REQUIRED_DEPARTMENTS = [
    ("Artificial Intelligence and Data Science", "AIDS"),
    ("Artificial Intelligence and Machine Learning", "AIML"),
    ("Information Technology", "IT"),
    ("Computer Science and Engineering", "CSE"),
    ("Chemical Engineering", "CHEM"),
    ("Biomedical Engineering", "BME"),
]

def migrate():
    print(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create departments table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(150) UNIQUE NOT NULL,
        code VARCHAR(20),
        is_active BOOLEAN DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Insert required departments if not already present
    for name, code in REQUIRED_DEPARTMENTS:
        cursor.execute("SELECT id FROM departments WHERE name = ?", (name,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT INTO departments (name, code, is_active) VALUES (?, ?, 1)", (name, code))
            print(f"Added department: {name}")

    conn.commit()

    # Get department map
    cursor.execute("SELECT name, id FROM departments")
    dept_map = dict(cursor.fetchall())
    print("Department ID mapping:", dept_map)

    # 3. Add columns to subjects if not present
    cursor.execute("PRAGMA table_info(subjects)")
    subject_cols = [c[1] for c in cursor.fetchall()]
    if "department_id" not in subject_cols:
        cursor.execute("ALTER TABLE subjects ADD COLUMN department_id INTEGER REFERENCES departments(id)")
        print("Added department_id to subjects")
    if "is_active" not in subject_cols:
        cursor.execute("ALTER TABLE subjects ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("Added is_active to subjects")

    # 4. Add columns to instructors if not present
    cursor.execute("PRAGMA table_info(instructors)")
    inst_cols = [c[1] for c in cursor.fetchall()]
    if "department_id" not in inst_cols:
        cursor.execute("ALTER TABLE instructors ADD COLUMN department_id INTEGER REFERENCES departments(id)")
        print("Added department_id to instructors")
    if "department_name" not in inst_cols:
        cursor.execute("ALTER TABLE instructors ADD COLUMN department_name VARCHAR(150)")
        print("Added department_name to instructors")
    if "is_active" not in inst_cols:
        cursor.execute("ALTER TABLE instructors ADD COLUMN is_active BOOLEAN DEFAULT 1")
        print("Added is_active to instructors")

    # 5. Create subject_instructors association table if not exists
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subject_instructors (
        subject_id INTEGER NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
        instructor_id INTEGER NOT NULL REFERENCES instructors(id) ON DELETE CASCADE,
        PRIMARY KEY (subject_id, instructor_id)
    );
    """)
    print("Checked subject_instructors table")

    # 6. Add columns to feedback_submissions if not present
    cursor.execute("PRAGMA table_info(feedback_submissions)")
    sub_cols = [c[1] for c in cursor.fetchall()]
    if "department_name" not in sub_cols:
        cursor.execute("ALTER TABLE feedback_submissions ADD COLUMN department_name VARCHAR(150) DEFAULT 'Computer Science and Engineering'")
        print("Added department_name to feedback_submissions")
    if "department_id" not in sub_cols:
        cursor.execute("ALTER TABLE feedback_submissions ADD COLUMN department_id INTEGER REFERENCES departments(id)")
        print("Added department_id to feedback_submissions")
    if "is_other" not in sub_cols:
        cursor.execute("ALTER TABLE feedback_submissions ADD COLUMN is_other BOOLEAN DEFAULT 0")
        print("Added is_other to feedback_submissions")

    # 7. Migrate existing subjects to department "Computer Science and Engineering"
    cse_id = dept_map.get("Computer Science and Engineering")
    it_id = dept_map.get("Information Technology")
    cursor.execute("UPDATE subjects SET department_id = ? WHERE department_id IS NULL", (cse_id,))

    # 8. Migrate existing instructors
    cursor.execute("SELECT id, name, department FROM instructors")
    existing_insts = cursor.fetchall()
    for inst_id, name, dept in existing_insts:
        target_dept_name = "Computer Science and Engineering"
        target_dept_id = cse_id
        if dept and "Information" in dept:
            target_dept_name = "Information Technology"
            target_dept_id = it_id
        elif dept and "Artificial" in dept:
            target_dept_name = "Artificial Intelligence and Machine Learning"
            target_dept_id = dept_map.get("Artificial Intelligence and Machine Learning", cse_id)

        cursor.execute("""
            UPDATE instructors 
            SET department_id = ?, department_name = ?, department = ?, is_active = 1 
            WHERE id = ?
        """, (target_dept_id, target_dept_name, target_dept_name, inst_id))

    # 9. Link existing instructors to existing subjects in subject_instructors
    # Dr. Sarah Jenkins (1) -> Data Structures & Algorithms (2), Software Engineering (5)
    # Prof. Rajesh Kumar (2) -> Computer Networks Lab (3), Operating Systems (4)
    # Dr. Michael Chen (3) -> Database Management Systems (1)
    # Prof. Anita Sharma (4) -> Operating Systems (4), Database Management Systems (1)
    links = [
        (2, 1), (5, 1), # Dr. Sarah Jenkins
        (3, 2), (4, 2), # Prof. Rajesh Kumar
        (1, 3),         # Dr. Michael Chen
        (4, 4), (1, 4), # Prof. Anita Sharma
    ]
    for sub_id, inst_id in links:
        cursor.execute("""
            INSERT OR IGNORE INTO subject_instructors (subject_id, instructor_id)
            VALUES (?, ?)
        """, (sub_id, inst_id))

    # 10. Update existing feedback_submissions to have valid department_name and department_id
    cursor.execute("UPDATE feedback_submissions SET department_name = 'Computer Science and Engineering', department_id = ? WHERE department_name IS NULL OR department_name = ''", (cse_id,))
    cursor.execute("UPDATE feedback_submissions SET department_name = 'Information Technology', department_id = ? WHERE instructor_name = 'Dr. Michael Chen'", (it_id,))

    conn.commit()
    conn.close()
    print("Migration completed successfully!")

if __name__ == "__main__":
    migrate()
