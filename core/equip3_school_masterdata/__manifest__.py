# See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 School Masterdata',
    'summary': """
        a Modul for Masterdata""",

    'description': """
        Long description of module's purpose
    """,
    'version': '1.1.24',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'category': 'Uncategorized',
    'license': "AGPL-3",
    'depends': ['school', 'equip3_school_operation', 'school_fees'],
    'data': [
            'security/ir.model.access.csv',
            'views/teacher.xml',
            'views/student_views.xml',
            'views/student_fees_register_views.xml',
            'views/school_views.xml',
            'views/school_equipment_views.xml',
            'views/timetable_views.xml',
            'views/exam_views.xml',
            'views/student_news_form_views.xml',
            'views/student_fees_views.xml'
            # 'views/school_document_type_views.xml',
    ],
    'demo': [''],
    'application': True,
    'installable': True,

}
