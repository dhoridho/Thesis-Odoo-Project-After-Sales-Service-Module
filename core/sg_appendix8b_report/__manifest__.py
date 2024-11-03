{
    "name": "Singapore Appendix8b report",
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
    - APPENDIX8B e-submission text file reports
    - This Module is used to add all the information fields
     to generate APPENDIX8B report
    """,
    "summary": """Singapore Appendix 8B Income Tax report.""",
    'data': [
        "data/incometax_data.xml",
        "security/ir.model.access.csv",
        "views/sg_income_tax_extended_view.xml",
        "wizard/emp_appendix8b_text_file_view.xml",
        "views/sg_appendix8b_report_view.xml",
        "views/sg_appendix8b_report_menu.xml",
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "price": 49,
    "currency": 'EUR',
}
