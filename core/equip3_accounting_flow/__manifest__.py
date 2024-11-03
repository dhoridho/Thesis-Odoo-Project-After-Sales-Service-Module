
{
    'name': 'Accounting Flow',
    'version': '1.1.7',
    'author': 'Hashmicro',
    'category' : 'Accounting',
    'depends': [
                'base',
                'equip3_hashmicro_ui',
                'equip3_accounting_reports',
                ],
    'data': [
    
        'security/ir.model.access.csv',
        'views/assets.xml',
        
        'wizard/accounting_flow_config_view.xml',
        'wizard/accounting_payable_flow.xml',
        'wizard/accounting_receivable_flow.xml',
        'wizard/flow_menuitem.xml',

        'views/menu_views.xml',
        
    ],
    'qweb': [
        'static/src/xml/accounting_flow.xml',
        'static/src/xml/finance_flow.xml',
        'static/src/xml/receivable_flow.xml',
    ],
    
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': True
}
