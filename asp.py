from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, date, timedelta
from typing import Optional
from collections import defaultdict

# Импортируем ТОЛЬКО CRUD функции, никаких прямых SQL запросов
from core_service.crud import (
    get_db_connection,
    get_all_employees,
    get_all_examinations,
    get_employee_by_user_id,
    get_examinations_by_employee,
    get_user_by_username,
    verify_user
)

app = FastAPI(
    title="Medical Examination Analytics Service",
    description="Сервис аналитики и отчетности для медицинских обследований",
    version="2.0.0"
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_token(authorization: Optional[str] = Header(None)):
    """Простая верификация токена"""
    return True


# Health check
@app.get("/")
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "supporting_service",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/analytics/summary")
async def get_summary(authorized: bool = Depends(verify_token)):
    """Общая статистика по всем обследованиям"""
    # Используем CRUD функции вместо SQL
    employees = get_all_employees()
    all_exams = get_all_examinations()

    total_employees = len(employees)
    total_exams = len(all_exams)

    # Подсчет статистики через Python, а не SQL
    passed = 0
    failed = 0
    exam_types = defaultdict(int)

    for exam in all_exams:
        # exam: exam_id, exam_date, exam_type, doctor_name, result, is_passed, next_exam_date, full_name, email
        if exam[5]:  # is_passed
            passed += 1
        else:
            failed += 1

        exam_types[exam[2]] += 1  # exam_type

    by_type = [{"type": t, "count": c} for t, c in exam_types.items()]

    return {
        "summary": {
            "total_employees": total_employees,
            "total_examinations": total_exams,
            "passed_examinations": passed,
            "failed_examinations": failed,
            "pass_rate": round((passed / total_exams * 100), 2) if total_exams > 0 else 0
        },
        "by_type": by_type,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/by-department")
async def get_analytics_by_department(authorized: bool = Depends(verify_token)):
    """Детальная аналитика по отделам"""
    employees = get_all_employees()

    # Структуры для сбора данных по отделам
    departments_data = defaultdict(lambda: {
        "employees": set(),
        "total_exams": 0,
        "passed_exams": 0
    })

    for emp in employees:
        # emp: employee_id, position, department, hire_date, birth_date, phone, full_name, email, user_name
        department = emp[2]  # department
        employee_id = emp[0]

        departments_data[department]["employees"].add(employee_id)

        # Получаем обследования для этого сотрудника через CRUD
        exams = get_examinations_by_employee(employee_id)

        departments_data[department]["total_exams"] += len(exams)
        departments_data[department]["passed_exams"] += sum(1 for ex in exams if ex[5])

    # Формируем результат
    departments = []
    for dept, data in departments_data.items():
        total_exams = data["total_exams"]
        passed = data["passed_exams"]

        departments.append({
            "department": dept,
            "employee_count": len(data["employees"]),
            "total_exams": total_exams,
            "passed_exams": passed,
            "failed_exams": total_exams - passed,
            "success_rate": round((passed / total_exams * 100), 2) if total_exams > 0 else 0
        })

    # Сортируем по успеваемости
    departments.sort(key=lambda x: x["success_rate"], reverse=True)

    return {
        "departments": departments,
        "total_departments": len(departments),
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/employee/{employee_id}")
async def get_employee_analytics(employee_id: int, authorized: bool = Depends(verify_token)):
    """Полная аналитика по конкретному сотруднику"""
    # Получаем всех сотрудников и ищем нужного
    all_employees = get_all_employees()
    employee = None

    for emp in all_employees:
        if emp[0] == employee_id:
            employee = emp
            break

    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    # Получаем обследования через CRUD
    examinations = get_examinations_by_employee(employee_id)

    # Статистика
    total_exams = len(examinations)
    passed = sum(1 for ex in examinations if ex[5])

    # Анализ по типам обследований
    exam_types = defaultdict(int)
    for ex in examinations:
        exam_types[ex[2]] += 1

    return {
        "employee_info": {
            "employee_id": employee[0],
            "full_name": employee[6],
            "position": employee[1],
            "department": employee[2],
            "email": employee[7],
            "username": employee[8],
            "hire_date": str(employee[3]) if employee[3] else None,
            "birth_date": str(employee[4]) if employee[4] else None,
            "phone": employee[5]
        },
        "examinations": [
            {
                "id": ex[0],
                "date": str(ex[1]),
                "type": ex[2],
                "doctor": ex[3],
                "result": ex[4],
                "is_passed": ex[5],
                "next_date": str(ex[6]) if ex[6] else None
            } for ex in examinations
        ],
        "statistics": {
            "total": total_exams,
            "passed": passed,
            "failed": total_exams - passed,
            "pass_rate": round((passed / total_exams * 100), 2) if total_exams > 0 else 0,
            "by_type": [{"type": t, "count": c} for t, c in exam_types.items()]
        },
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/upcoming-exams")
async def get_upcoming_exams(days: int = 30, authorized: bool = Depends(verify_token)):
    """Обследования, требующие внимания в ближайшие дни"""
    all_employees = get_all_employees()
    today = date.today()
    deadline = today + timedelta(days=days)

    upcoming = []
    urgency_stats = {
        "Просрочено": 0,
        "Сегодня": 0,
        "На этой неделе": 0,
        "В ближайшее время": 0
    }

    for emp in all_employees:
        employee_id = emp[0]
        full_name = emp[6]
        position = emp[1]
        department = emp[2]

        # Получаем все обследования сотрудника
        exams = get_examinations_by_employee(employee_id)

        for exam in exams:
            next_date = exam[6]  # next_exam_date
            if next_date and next_date <= deadline:
                days_until = (next_date - today).days

                if days_until < 0:
                    urgency = "Просрочено"
                elif days_until == 0:
                    urgency = "Сегодня"
                elif days_until <= 7:
                    urgency = "На этой неделе"
                else:
                    urgency = "В ближайшее время"

                urgency_stats[urgency] += 1

                upcoming.append({
                    "full_name": full_name,
                    "position": position,
                    "department": department,
                    "next_exam_date": str(next_date),
                    "exam_type": exam[2],
                    "last_exam_date": str(exam[1]),
                    "days_until": days_until,
                    "urgency": urgency
                })

    # Сортируем по дате
    upcoming.sort(key=lambda x: x["days_until"])

    return {
        "upcoming_examinations": upcoming,
        "total_upcoming": len(upcoming),
        "urgency_stats": urgency_stats,
        "period_days": days,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/export/json")
async def export_full_report(authorized: bool = Depends(verify_token)):
    """Экспорт полного отчета в JSON формате"""
    employees = get_all_employees()

    employees_data = []
    total_exams_all = 0
    total_passed_all = 0

    for emp in employees:
        exams = get_examinations_by_employee(emp[0])
        total_exams = len(exams)
        passed = sum(1 for ex in exams if ex[5])

        total_exams_all += total_exams
        total_passed_all += passed

        employees_data.append({
            "employee_id": emp[0],
            "full_name": emp[6],
            "position": emp[1],
            "department": emp[2],
            "email": emp[7],
            "username": emp[8],
            "hire_date": str(emp[3]) if emp[3] else None,
            "birth_date": str(emp[4]) if emp[4] else None,
            "phone": emp[5],
            "examinations": [
                {
                    "exam_id": ex[0],
                    "exam_date": str(ex[1]),
                    "exam_type": ex[2],
                    "doctor_name": ex[3],
                    "result": ex[4],
                    "is_passed": ex[5],
                    "next_exam_date": str(ex[6]) if ex[6] else None
                } for ex in exams
            ],
            "statistics": {
                "total_exams": total_exams,
                "passed": passed,
                "failed": total_exams - passed,
                "pass_rate": round((passed / total_exams * 100), 2) if total_exams > 0 else 0
            }
        })

    return {
        "report_type": "full_medical_examination_report",
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_employees": len(employees),
            "total_examinations": total_exams_all,
            "total_passed": total_passed_all,
            "pass_rate": round((total_passed_all / total_exams_all * 100), 2) if total_exams_all > 0 else 0
        },
        "employees": employees_data
    }


@app.get("/analytics/export/csv")
async def export_csv_report(authorized: bool = Depends(verify_token)):
    """Экспорт отчета в CSV формате"""
    employees = get_all_employees()

    # Собираем данные через CRUD
    csv_data = []
    for emp in employees:
        exams = get_examinations_by_employee(emp[0])
        total_exams = len(exams)
        passed = sum(1 for ex in exams if ex[5])

        last_exam_date = max([ex[1] for ex in exams]) if exams else None
        next_exam_date = min([ex[6] for ex in exams if ex[6]]) if exams else None

        csv_data.append({
            "full_name": emp[6],
            "position": emp[1],
            "department": emp[2],
            "total_exams": total_exams,
            "passed": passed,
            "failed": total_exams - passed,
            "last_exam_date": str(last_exam_date) if last_exam_date else "Нет",
            "next_exam_date": str(next_exam_date) if next_exam_date else "Не назначено"
        })

    # Создаем CSV
    import csv
    from io import StringIO

    output = StringIO()
    if csv_data:
        writer = csv.DictWriter(output, fieldnames=csv_data[0].keys())
        writer.writeheader()
        writer.writerows(csv_data)

    return JSONResponse(
        content={
            "csv_data": output.getvalue(),
            "filename": f"medical_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        }
    )


@app.get("/analytics/department/{department_name}")
async def get_department_details(department_name: str, authorized: bool = Depends(verify_token)):
    """Детальная информация по конкретному отделу"""
    employees = get_all_employees()

    # Фильтруем сотрудников по отделу
    department_employees = [emp for emp in employees if emp[2] == department_name]

    if not department_employees:
        raise HTTPException(status_code=404, detail="Department not found")

    employees_list = []
    for emp in department_employees:
        exams = get_examinations_by_employee(emp[0])
        total_exams = len(exams)
        passed = sum(1 for ex in exams if ex[5])

        last_exam = max([ex[1] for ex in exams]) if exams else None

        employees_list.append({
            "employee_id": emp[0],
            "full_name": emp[6],
            "position": emp[1],
            "total_exams": total_exams,
            "passed": passed,
            "failed": total_exams - passed,
            "pass_rate": round((passed / total_exams * 100), 2) if total_exams > 0 else 0,
            "last_exam_date": str(last_exam) if last_exam else None
        })

    # Статистика по отделу
    total_exams = sum(e["total_exams"] for e in employees_list)
    total_passed = sum(e["passed"] for e in employees_list)

    return {
        "department": department_name,
        "total_employees": len(employees_list),
        "total_examinations": total_exams,
        "total_passed": total_passed,
        "total_failed": total_exams - total_passed,
        "department_pass_rate": round((total_passed / total_exams * 100), 2) if total_exams > 0 else 0,
        "employees": employees_list,
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/statistics/trends")
async def get_trends(year: Optional[int] = None, authorized: bool = Depends(verify_token)):
    """Аналитика по месяцам"""
    if year is None:
        year = datetime.now().year

    all_exams = get_all_examinations()

    # Группируем по месяцам
    monthly_data = defaultdict(lambda: {"total": 0, "passed": 0})

    for exam in all_exams:
        exam_year = exam[1].year
        if exam_year == year:
            month = exam[1].month
            monthly_data[month]["total"] += 1
            if exam[5]:  # is_passed
                monthly_data[month]["passed"] += 1

    months_data = []
    for month in range(1, 13):
        data = monthly_data[month]
        total = data["total"]
        passed = data["passed"]

        months_data.append({
            "month": month,
            "month_name": date(2000, month, 1).strftime('%B'),
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "pass_rate": round((passed / total * 100), 2) if total > 0 else 0
        })

    return {
        "year": year,
        "months": months_data,
        "total_for_year": sum(m["total"] for m in months_data),
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/doctors/ranking")
async def get_doctors_ranking(authorized: bool = Depends(verify_token)):
    """Рейтинг врачей по количеству проведенных обследований"""
    all_exams = get_all_examinations()

    # Собираем статистику по врачам
    doctors_data = defaultdict(lambda: {"total": 0, "passed": 0})

    for exam in all_exams:
        doctor = exam[3]  # doctor_name
        if doctor:  # только если врач указан
            doctors_data[doctor]["total"] += 1
            if exam[5]:  # is_passed
                doctors_data[doctor]["passed"] += 1

    # Формируем рейтинг
    doctors = []
    for doctor, data in doctors_data.items():
        total = data["total"]
        passed = data["passed"]

        doctors.append({
            "name": doctor,
            "total_exams": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": round((passed / total * 100), 2) if total > 0 else 0
        })

    # Сортируем по количеству обследований
    doctors.sort(key=lambda x: x["total_exams"], reverse=True)

    return {
        "doctors": doctors[:10],  # Топ-10 врачей
        "total_doctors": len(doctors),
        "generated_at": datetime.now().isoformat()
    }


@app.get("/analytics/employee/search")
async def search_employee(query: str, authorized: bool = Depends(verify_token)):
    """Поиск сотрудника по имени или email"""
    employees = get_all_employees()

    query_lower = query.lower()
    results = []

    for emp in employees:
        if (query_lower in emp[6].lower() or  # full_name
                query_lower in emp[7].lower() or  # email
                query_lower in emp[8].lower()):  # username

            exams = get_examinations_by_employee(emp[0])

            results.append({
                "employee_id": emp[0],
                "full_name": emp[6],
                "position": emp[1],
                "department": emp[2],
                "email": emp[7],
                "total_exams": len(exams),
                "last_exam": str(max([ex[1] for ex in exams])) if exams else None
            })

    return {
        "query": query,
        "results": results,
        "total_found": len(results),
        "generated_at": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("📊 Supporting сервис (FastAPI) запущен на порту 8000")
    print("=" * 60)
    print("📈 Доступные аналитические endpoints:")
    print("   GET /analytics/summary - Общая статистика")
    print("   GET /analytics/by-department - Статистика по отделам")
    print("   GET /analytics/employee/{id} - Аналитика сотрудника")
    print("   GET /analytics/upcoming-exams - Предстоящие обследования")
    print("   GET /analytics/export/json - Экспорт в JSON")
    print("   GET /analytics/export/csv - Экспорт в CSV")
    print("   GET /analytics/department/{name} - Детали отдела")
    print("   GET /analytics/statistics/trends - Тренды по месяцам")
    print("   GET /analytics/doctors/ranking - Рейтинг врачей")
    print("   GET /analytics/employee/search - Поиск сотрудников")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
