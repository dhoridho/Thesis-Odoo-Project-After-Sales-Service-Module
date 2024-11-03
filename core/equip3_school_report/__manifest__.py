# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Equip3 School Report',
    'version': '1.1.14',
    'summary': 'Manage your Purchase Requests and Purchase Orders Report Analysis',
    'depends': ['timetable','exam', 'school_fees', 'general_template', 'school_attendance', 'web', 'equip3_school_operation'],
    'category': 'School Management',
    'data': [
        'security/ir.model.access.csv',
        'report/timetable.xml',
        'report/timetable_report_view.xml',
        'report/result_information_report.xml',
        'views/timetable_views.xml',
        'report/student_payslip_report_pdf.xml',
        'report/exam_result_report.xml',
        'report/additional_exam_report.xml',
        'report/hostel_fee_receipt.xml',
        'report/fees_register_report.xml',
        'report/idcard_report_views.xml',
        'report/identity_card_views.xml',
        'report/attendance_report_template.xml',
        'report/attendance_report.xml',
        'wizard/attendance_report_wizard.xml',
        'report/student_transcript_report.xml',
        'report/finished_exam_report.xml',
        'report/finished_exam_report_template.xml',
        'report/finished_assignment_report.xml',
        'report/finished_assignment_report_template.xml',
        'report/finished_additional_exam_report.xml',
        'report/finished_additional_exam_report_template.xml',
        'report/final_grade_subject_weightage_report.xml',
        'report/final_grade_subject_weightage_report_template.xml',

    ],
    'installable': True,
    'application': True,
}