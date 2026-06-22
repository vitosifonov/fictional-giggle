from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from datetime import datetime, date, timedelta
import json
import re
from functools import wraps
from typing import Optional, Dict, Any

# Импортируем ВСЕ функции из CRUD
from crud import (
    get_db_connection,
    hash_password,
    verify_user,
    get_user_by_username,
    create_user,
    get_employee_by_user_id,
    create_employee,
    update_employee,
    get_all_employees,
    get_examinations_by_employee,
    create_examination,
    update_examination,
    delete_examination,
    get_all_examinations
)

app = Flask(__name__)
app.secret_key = 'medical-examination-secret-key-2024'
app.permanent_session_lifetime = 86400  # 24 hours


# Декоратор для проверки авторизации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Пожалуйста, войдите в систему', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


# Вспомогательные функции валидации
def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    if not phone:
        return True
    pattern = r'^\+?[0-9\s\-\(\)]{10,20}$'
    return re.match(pattern, phone) is not None


def get_user_statistics(user_id: int) -> Dict[str, Any]:
    """Получение статистики для пользователя через CRUD"""
    employee = get_employee_by_user_id(user_id)
    if not employee:
        return {'total': 0, 'passed': 0, 'failed': 0, 'rate': 0}

    exams = get_examinations_by_employee(employee[0])
    total = len(exams)
    passed = sum(1 for exam in exams if exam[5])
    failed = total - passed

    return {
        'total': total,
        'passed': passed,
        'failed': failed,
        'rate': round((passed / total * 100), 1) if total > 0 else 0
    }


# Маршруты
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Если пользователь уже авторизован, перенаправляем на дашборд
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user_name = request.form.get('user_name', '').strip()
        password = request.form.get('password', '')

        if not user_name or not password:
            flash('Заполните все поля', 'error')
            return render_template('login.html')

        # Используем CRUD функцию verify_user
        user = verify_user(user_name, password)

        if user:
            session.permanent = True
            session['user_id'] = user[0]  # user_id
            session['user_name'] = user[1]  # user_name
            session['user_email'] = user[3]  # email
            session['user_fullname'] = user[4]  # full_name

            flash(f'Добро пожаловать, {user[4] or user[1]}!', 'success')

            # Перенаправление на запрошенную страницу или дашборд
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль', 'error')
            return render_template('login.html')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        user_name = request.form.get('user_name', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        email = request.form.get('email', '').strip()
        full_name = request.form.get('full_name', '').strip()

        # Валидация
        errors = []

        if not user_name or len(user_name) < 3:
            errors.append('Имя пользователя должно содержать минимум 3 символа')

        if not password or len(password) < 6:
            errors.append('Пароль должен содержать минимум 6 символов')

        if password != confirm_password:
            errors.append('Пароли не совпадают')

        if not email or not validate_email(email):
            errors.append('Введите корректный email адрес')

        if not full_name:
            errors.append('Введите полное имя')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('register.html')

        # Проверка существующего пользователя через CRUD
        existing_user = get_user_by_username(user_name)
        if existing_user:
            flash('Пользователь с таким именем уже существует', 'error')
            return render_template('register.html')

        # Создание пользователя через CRUD
        try:
            user_id = create_user(user_name, password, email, full_name)
            flash('Регистрация успешна! Теперь вы можете войти в систему', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Ошибка при регистрации: {str(e)}', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/logout')
def logout():
    user_name = session.get('user_name', 'Пользователь')
    session.clear()
    flash(f'До свидания, {user_name}!', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    # Получение данных через CRUD
    user_id = session['user_id']
    employee = get_employee_by_user_id(user_id)

    # Получение обследований
    exams = []
    if employee:
        exams_raw = get_examinations_by_employee(employee[0])
        # Преобразуем данные для удобства использования в шаблоне
        exams = [{
            'id': exam[0],
            'date': exam[1],
            'type': exam[2],
            'doctor': exam[3] or 'Не указан',
            'result': exam[4] or 'Не указан',
            'is_passed': exam[5],
            'next_date': exam[6]
        } for exam in exams_raw]

    # Статистика
    stats = get_user_statistics(user_id)

    # Информация для отображения
    user_info = {
        'user_name': session['user_name'],
        'full_name': session.get('user_fullname', ''),
        'email': session.get('user_email', '')
    }

    return render_template('dashboard.html',
                           user=user_info,
                           employee=employee,
                           exams=exams,
                           stats=stats)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user_id = session['user_id']
    employee = get_employee_by_user_id(user_id)

    if request.method == 'POST':
        # Получение данных из формы
        position = request.form.get('position', '').strip()
        department = request.form.get('department', '').strip()
        hire_date = request.form.get('hire_date', '')
        birth_date = request.form.get('birth_date', '') or None
        phone = request.form.get('phone', '').strip() or None

        # Валидация
        errors = []

        if not position:
            errors.append('Укажите должность')

        if not department:
            errors.append('Укажите отдел')

        if not hire_date:
            errors.append('Укажите дату приема на работу')

        if phone and not validate_phone(phone):
            errors.append('Введите корректный номер телефона')

        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('profile.html', employee=employee)

        try:
            if not employee:
                # Создание нового профиля через CRUD
                create_employee(user_id, position, department, hire_date, birth_date, phone)
                flash('Профиль сотрудника успешно создан!', 'success')
            else:
                # Обновление существующего профиля через CRUD
                update_employee(employee[0], position, department, hire_date, birth_date, phone)
                flash('Профиль сотрудника успешно обновлен!', 'success')

            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Ошибка при сохранении профиля: {str(e)}', 'error')
            return render_template('profile.html', employee=employee)

    return render_template('profile.html', employee=employee)


@app.route('/exams/create', methods=['POST'])
@login_required
def create_exam():
    user_id = session['user_id']
    employee = get_employee_by_user_id(user_id)

    if not employee:
        flash('Сначала заполните профиль сотрудника', 'error')
        return redirect(url_for('profile'))

    # Получение данных
    exam_date = request.form.get('exam_date', '')
    exam_type = request.form.get('exam_type', '')
    doctor_name = request.form.get('doctor_name', '').strip() or None
    result = request.form.get('result', '').strip() or None
    is_passed = request.form.get('is_passed') == 'on'
    next_exam_date = request.form.get('next_exam_date', '') or None

    # Валидация
    if not exam_date:
        flash('Укажите дату обследования', 'error')
        return redirect(url_for('dashboard'))

    if not exam_type:
        flash('Укажите тип обследования', 'error')
        return redirect(url_for('dashboard'))

    # Преобразуем строки в даты
    try:
        exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d').date()
        next_date_obj = datetime.strptime(next_exam_date, '%Y-%m-%d').date() if next_exam_date else None
    except ValueError:
        flash('Неверный формат даты', 'error')
        return redirect(url_for('dashboard'))

    try:
        # Создание обследования через CRUD
        create_examination(employee[0], exam_date_obj, exam_type,
                           doctor_name, result, is_passed, next_date_obj)
        flash('Обследование успешно добавлено!', 'success')
    except Exception as e:
        flash(f'Ошибка при добавлении обследования: {str(e)}', 'error')

    return redirect(url_for('dashboard'))


@app.route('/exams/update/<int:exam_id>', methods=['POST'])
@login_required
def update_exam(exam_id):
    result = request.form.get('result', '').strip() or None
    is_passed = request.form.get('is_passed') == 'on'
    next_exam_date = request.form.get('next_exam_date', '') or None

    # Преобразуем дату
    next_date_obj = None
    if next_exam_date:
        try:
            next_date_obj = datetime.strptime(next_exam_date, '%Y-%m-%d').date()
        except ValueError:
            flash('Неверный формат даты', 'error')
            return redirect(url_for('dashboard'))

    try:
        # Обновление обследования через CRUD
        update_examination(exam_id, result, is_passed, next_date_obj)
        flash('Обследование успешно обновлено!', 'success')
    except Exception as e:
        flash(f'Ошибка при обновлении: {str(e)}', 'error')

    return redirect(url_for('dashboard'))


@app.route('/exams/delete/<int:exam_id>')
@login_required
def delete_exam(exam_id):
    try:
        # Удаление обследования через CRUD
        delete_examination(exam_id)
        flash('Обследование удалено', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении: {str(e)}', 'error')

    return redirect(url_for('dashboard'))


# API endpoints для Supporting Service
@app.route('/api/health')
def api_health():
    """Проверка статуса сервиса"""
    return jsonify({
        'status': 'healthy',
        'service': 'core_service',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/user/info')
@login_required
def api_user_info():
    """Получение информации о текущем пользователе через CRUD"""
    user_id = session['user_id']
    user = get_user_by_username(session['user_name'])
    employee = get_employee_by_user_id(user_id)

    return jsonify({
        'user_id': user_id,
        'username': session['user_name'],
        'email': session.get('user_email'),
        'full_name': session.get('user_fullname'),
        'employee': {
            'id': employee[0] if employee else None,
            'position': employee[2] if employee else None,
            'department': employee[3] if employee else None,
            'hire_date': str(employee[4]) if employee and employee[4] else None,
            'phone': employee[6] if employee else None
        } if employee else None
    })


@app.route('/api/exams/all')
@login_required
def api_all_exams():
    """Получение всех обследований пользователя в JSON через CRUD"""
    user_id = session['user_id']
    employee = get_employee_by_user_id(user_id)

    if not employee:
        return jsonify({'exams': []})

    exams_raw = get_examinations_by_employee(employee[0])
    exams_list = []

    for exam in exams_raw:
        exams_list.append({
            'id': exam[0],
            'date': str(exam[1]),
            'type': exam[2],
            'doctor': exam[3],
            'result': exam[4],
            'is_passed': exam[5],
            'next_date': str(exam[6]) if exam[6] else None
        })

    return jsonify({
        'user_id': user_id,
        'employee_id': employee[0],
        'total': len(exams_list),
        'exams': exams_list
    })


@app.route('/api/employees/all')
@login_required
def api_all_employees():
    """Получение всех сотрудников через CRUD (только для админов)"""
    # В реальном приложении здесь должна быть проверка прав администратора
    employees = get_all_employees()

    employees_list = []
    for emp in employees:
        employees_list.append({
            'employee_id': emp[0],
            'position': emp[1],
            'department': emp[2],
            'full_name': emp[6],
            'email': emp[7],
            'username': emp[8]
        })

    return jsonify({
        'total': len(employees_list),
        'employees': employees_list
    })


@app.route('/api/examinations/all')
@login_required
def api_all_examinations():
    """Получение всех обследований системы через CRUD"""
    exams_raw = get_all_examinations()

    exams_list = []
    for exam in exams_raw:
        exams_list.append({
            'id': exam[0],
            'date': str(exam[1]),
            'type': exam[2],
            'doctor': exam[3],
            'result': exam[4],
            'is_passed': exam[5],
            'next_date': str(exam[6]) if exam[6] else None,
            'employee_name': exam[7],
            'employee_email': exam[8]
        })

    return jsonify({
        'total': len(exams_list),
        'examinations': exams_list
    })


# Обработчики ошибок
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    flash('Внутренняя ошибка сервера', 'error')
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
