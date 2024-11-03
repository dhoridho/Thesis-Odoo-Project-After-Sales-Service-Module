{
    "name": "Singapore Appendix8a report",
    "version": "14.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["sg_income_tax_report"],
    "author": "Serpent Consulting Services Pvt. Ltd.",
    "maintainer": "Serpent Consulting Services Pvt. Ltd.",
    "sequence": 1,
    "website": "http://www.serpentcs.com",
    "category": "Human Resources",
    "description": """
    Singapore Income Tax report.
    ============================
    - APPENDIX8A esubmission txt file reports
    - Module will add all the information fields to generate APPENDIX8A report
    - All fields will be added in employee contract based on sections as per
    IRAS rules.
    """,
    "summary": """Singapore Income Tax report.""",
    'data': [
         "security/ir.model.access.csv",
         "views/sg_income_tax_extended_view.xml",
         "views/sg_appendix8a_report_view.xml",
         "views/sg_appendix8a_report_menu.xml",
         "wizard/emp_appendix8a_text_file_view.xml",
         ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 49,
    "currency": 'EUR',
}
