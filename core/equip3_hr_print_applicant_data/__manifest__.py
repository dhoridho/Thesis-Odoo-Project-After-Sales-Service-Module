

# -*- coding: utf-8 -*-
################################################
#   Copyright PT HashMicro Solusi Indonesia   ##
################################################
{
    'name': "HR Print Applicant Data",

    'summary': """
        HR Print Applicant Data
        """,
    'description': """
        HR Print Applicant Data
    """,
    'author': "PT HashMicro Solusi Indonesia - Fransiskus Gidi",
    'support': "fransiskus.hashmicro@gmail.com",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '1.1.2',
    'license': "AGPL-3",
    'currency': "IDR",

    'depends': [
        'base','hr_recruitment'
        ],
    'external_dependencies': {'python': [], 'bin': []},

    'data': [
        'views/hr_view.xml',
        'report/hr_report.xml',
        'report/hr_applicantdata_template.xml',
    ],
    'images': [],
    'demo': [],
    'qweb': [],
    'post_load': None,
    'pre_init_hook': None,
    'post_init_hook': None,
    'auto_install': False,
    'installable': True,
    'application': True,
}
