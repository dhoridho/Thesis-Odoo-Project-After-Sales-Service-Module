# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name': "Maintenance Request Approval Workflow",
    'version': '1.1.1',
    'price': 19.0,
    'currency': 'EUR',
    'license': 'Other proprietary',
    'category': 'Operations/Maintenance',
    'summary': """Equipment Maintenance Request Approval Workflow""",
    'description': """
Maintenance Approval Workflow
Maintenance Request Approval Workflow
Maintenance Request
Equipment Maintenance Request Approval Workflow

    """,
    'author': "Probuse Consulting Service Pvt. Ltd.",
    'website': 'www.probuse.com',
    'images': ['static/description/approval_request.jpg'],
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/maintenance_approval_workflow/776',#'https://youtu.be/l-sGV0T-884',
    'depends': ['base', 'maintenance'],
    'data': [
        'views/maintenance_stage_view.xml',
        # 'data/approval_workflow.xml',
    ],
    'installable': True,
    'application': False,
    
}
