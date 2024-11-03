
{
    'name': 'Equip3 School Access Right',
    'version': '1.1.11',
    'summary': 'Manage your School Portal Access Right',
    'depends': ['school', 'website', 'equip3_school_operation', 'equip3_school_portal', 'equip3_school_flow_configuration', 'portal', 'exam', 'school_attendance'],
    'category': 'School Management',
    'data': [
        # 'data/accessright_data.xml',
        'security/exam_security.xml',
        'security/school_security.xml',
        'security/timetable_security.xml',
        'security/ir.model.access.csv',
        'views/academic_year_views.xml',
        'views/batch_result.xml',
        'views/parent_views.xml',
        'views/school_flow_wizard_views.xml',
        'views/school_view.xml',
        'views/student_view.xml',
    ],
    'installable': True,
    'application': False,
}
