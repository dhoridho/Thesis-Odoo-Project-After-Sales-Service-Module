# Part of Softhealer Technologies.
{
    "name": "HR Dashboard",
    "author": "Softhealer Technologies",
    "website": "https://www.softhealer.com",
    "support": "support@softhealer.com",
    "category": "Human Resources",
    "license": "OPL-1",
    "summary": "HR Detailed Dashboard App, Information Dashboard Of Employee, Detail Dashboard Of HR, Human Resource Smart Dashboard Module, Modify HR Dashboard,Manage HR Dashboard, Set HR Dashboard Odoo",
    "description": """Do you want to show all the employee details on the dashboard? So here it is. we have made a materialize dashboard for employees and managers. The dashboard is a powerful way to keep all details in a single bucket. An HR dashboard is a type of graphical user interface that often provides a glance view relevant to a particular objective or business process of HR. HR dashboard displays all information related to human resources in different menus. "HRMS dashboard" is the most advanced HR management system. You can quickly access all information about the employees. This includes different analysis and very helpful for the managers. Here you can easily manage your employees with various services such as Leave details, Attendance analysis, Contracts report, Employee expenses, Payslip counter, Greetings Menu (Birthday & Anniversary), Announcement menu. HR Dashboard Odoo, HRMS Dashboard Odoo, HR Detailed Dashboard, Information Dashboard Of Employee, Detail Dashboard Of HR, Human Resource Smart Dashboard Module, Modify HR Dashboard,Manage HR Dashboard, Set HR Dashboard Odoo, HR Detailed Dashboard App, Information Dashboard Of Employee, Detail Dashboard Of HR, Human Resource Smart Dashboard Module, Modify HR Dashboard,Manage HR Dashboard, Set HR Dashboard Odoo""",
    "version": "1.1.9",
    'depends': ['hr_attendance', 'hr_contract', 'hr_expense', 'hr_holidays', 'hr_recruitment', 'hr_timesheet','equip3_hr_employee_access_right_setting'],
    "application": True,
    "data": [
        'security/ir.model.access.csv',
        # 'security/security.xml',
        'data/dashboard_data.xml',
        'views/templates.xml',
        'views/annoucement_view.xml',
        'views/hr_dashboard.xml',
    ],
    "images": ["static/description/background.png", ],
    "auto_install": False,
    "installable": True,
    "price": 30,
    "currency": "EUR"
}
