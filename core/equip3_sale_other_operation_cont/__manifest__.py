# -*- coding: utf-8 -*-
{
    'name': "Equip3 Sale Other Operation Cont",

    'summary': """
        Manage your blanket orders activities""",

    'description': """
        This module manages these features :
        1. Blanket Order
        2. Blanket Order Approval Matrix
        3. Blanket Order to Sale Order
        4. Sale Agreement Type
    """,

    'author': "Hashmicro",
    'category': 'Sales',
    'version': '1.3.38',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'sale',
        'account',
        'mail',
        'stock',
        'blanket_sale_order_app',
        'branch',
        'equip3_sale_operation',
        'equip3_general_features',
        'equip3_sale_other_operation',
        'equip3_general_setting'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/rule.xml',
        'data/ir_sequence.xml',
        'data/ir_cron_data.xml',
        'report/blanket_template.xml',
        'report/blanket_report.xml',
        'data/mail_template_bo.xml',
        'wizards/bo_approval_matrix_sale_reject_views.xml',
        'views/sale_blanket_views.xml',
        'views/force_done_memory_view.xml',
        'views/res_config_setting_views.xml',
        'views/bo_approval_matrix_view.xml',
        'views/templates.xml',

        'views/creative_blanket.xml',
        'views/elegant_blanket.xml',
        'views/professional_blanket.xml',
        'views/exclusive_blanket.xml',
        'views/advanced_blanket.xml',
        'views/custom_blanket.xml',
        'views/incredible_blanket.xml',
        'views/innovative_blanket.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
