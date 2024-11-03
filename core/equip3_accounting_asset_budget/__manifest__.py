{
    'name': 'Accounting Asset Budget',
    'version': '1.1.2',
    'category': 'Accounting',
    'author': 'Santomi Fitrada',
    'depends': [
        'account','equip3_hashmicro_ui',
    ],
    'data': [
        # 'data/ir_sequence_data.xml',
        # 'data/asset_matrix_template.xml',
        # 'data/wa_asset_template.xml',
        'security/ir.model.access.csv',
        'data/asset_budget_sequence.xml',
        'data/ir_cron.xml',
        'views/asset_budget_menuitem.xml',
        'views/asset_budget_view.xml',
        'views/carry_over_asset_budget_view.xml',
        'views/asset_budget_transfer_view.xml',
        'views/asset_budget_change_request_view.xml',
        'views/asset_budget_analysis_view.xml',
        

    ],
    'demo': [],
    'auto_install': False,
    'installable': True,
    'application': False
}
