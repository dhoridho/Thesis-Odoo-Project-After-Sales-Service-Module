{
    'name': 'Purchase Accessright Setting',
    'version': '1.8.20',
    'category': 'Purchase/Purchase',
    'summary': '''
            This module help you to use checklist in Calendar Meetings.
        ''',
    'depends': ['purchase', 'purchase_request', 'equip3_general_setting', 'sh_all_in_one_purchase_tools', 'sh_po_tender_management'],
    'data': [
        'data/purchase_request_line.xml',
        'data/purchase_config_setting.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/approval_matrix_configuration.xml',
        'views/purchase_config_setting_view.xml'
    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}


