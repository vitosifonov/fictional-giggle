import psycopg2
import hashlib
from datetime import date

# Конфигурация подключения к базе данных
DB_CONFIG = {
    'dbname': 'medical_exam_db',
    'user': 'postgres',
    'password': 'rostik2007',
    'host': 'localhost',
    'port': '5432'
}


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_db_connection():
    """Получение соединения с базой данных"""
    return psycopg2.connect(**DB_CONFIG)


def hash_password(password: str) -> str:
    """Хеширование пароля с помощью SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


# ==================== USER (ПОЛЬЗОВАТЕЛИ) ====================

def create_user(user_name: str, password: str, email: str, full_name: str) -> int:
    """
    Создание нового пользователя
    Returns: user_id
    """
    conn = get_db_connection()
    cur = conn.cursor()

    password_hash = hash_password(password)
    cur.execute("""
        INSERT INTO users (user_name, password_hash, email, full_name)
        VALUES (%s, %s, %s, %s) RETURNING user_id
    """, (user_name, password_hash, email, full_name))

    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return user_id


def get_user_by_username(user_name: str):
    """
    Получение пользователя по имени пользователя
    Returns: (user_id, user_name, password_hash, email, full_name) или None
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT user_id, user_name, password_hash, email, full_name 
        FROM users 
        WHERE user_name = %s
    """, (user_name,))

    user = cur.fetchone()
    cur.close()
    conn.close()

    return user


def verify_user(user_name: str, password: str):
    """
    Проверка учетных данных пользователя
    Returns: (user_id, user_name, password_hash, email, full_name) или None
    """
    user = get_user_by_username(user_name)
    if user and user[2] == hash_password(password):
        return user
    return None


# ==================== EMPLOYEE (СОТРУДНИКИ) ====================

def create_employee(user_id: int, position: str, department: str,
                    hire_date: date, birth_date, phone) -> int:
    """
    Создание профиля сотрудника
    Returns: employee_id
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO employees (user_id, position, department, hire_date, birth_date, phone)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING employee_id
    """, (user_id, position, department, hire_date, birth_date, phone))

    employee_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return employee_id


def update_employee(employee_id: int, position: str, department: str,
                    hire_date: date, birth_date, phone) -> None:
    """
    Обновление информации о сотруднике
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE employees 
        SET position = %s, department = %s, hire_date = %s, birth_date = %s, phone = %s
        WHERE employee_id = %s
    """, (position, department, hire_date, birth_date, phone, employee_id))

    conn.commit()
    cur.close()
    conn.close()


def get_employee_by_user_id(user_id: int):
    """
    Получение сотрудника по ID пользователя
    Returns: (employee_id, user_id, position, department, hire_date, birth_date, phone, full_name, email) или None
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.employee_id, e.user_id, e.position, e.department, 
               e.hire_date, e.birth_date, e.phone, u.full_name, u.email
        FROM employees e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.user_id = %s
    """, (user_id,))

    employee = cur.fetchone()
    cur.close()
    conn.close()

    return employee


def get_all_employees():
    """
    Получение всех сотрудников
    Returns: list of (employee_id, position, department, hire_date, birth_date, phone, full_name, email, user_name)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.employee_id, e.position, e.department, e.hire_date, 
               e.birth_date, e.phone, u.full_name, u.email, u.user_name
        FROM employees e
        JOIN users u ON e.user_id = u.user_id
        ORDER BY e.employee_id
    """)

    employees = cur.fetchall()
    cur.close()
    conn.close()

    return employees


# ==================== EXAMINATION (ОБСЛЕДОВАНИЯ) ====================

def create_examination(employee_id: int, exam_date: date, exam_type: str,
                       doctor_name, result, is_passed: bool, next_exam_date) -> int:
    """
    Создание записи об обследовании
    Returns: exam_id
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO examinations (employee_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING exam_id
    """, (employee_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date))

    exam_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()

    return exam_id


def get_examinations_by_employee(employee_id: int):
    """
    Получение всех обследований сотрудника
    Returns: list of (exam_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT exam_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date
        FROM examinations 
        WHERE employee_id = %s
        ORDER BY exam_date DESC
    """, (employee_id,))

    exams = cur.fetchall()
    cur.close()
    conn.close()

    return exams


def update_examination(exam_id: int, result, is_passed: bool, next_exam_date) -> None:
    """
    Обновление информации об обследовании
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE examinations 
        SET result = %s, is_passed = %s, next_exam_date = %s
        WHERE exam_id = %s
    """, (result, is_passed, next_exam_date, exam_id))

    conn.commit()
    cur.close()
    conn.close()


def delete_examination(exam_id: int) -> None:
    """
    Удаление обследования
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM examinations WHERE exam_id = %s", (exam_id,))
    conn.commit()
    cur.close()
    conn.close()


def get_all_examinations():
    """
    Получение всех обследований с информацией о сотрудниках
    Returns: list of (exam_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date, full_name, email)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT e.exam_id, e.exam_date, e.exam_type, e.doctor_name, 
               e.result, e.is_passed, e.next_exam_date,
               u.full_name, u.email
        FROM examinations e
        JOIN employees emp ON e.employee_id = emp.employee_id
        JOIN users u ON emp.user_id = u.user_id
        ORDER BY e.exam_date DESC
    """)

    exams = cur.fetchall()
    cur.close()
    conn.close()

    return exams
