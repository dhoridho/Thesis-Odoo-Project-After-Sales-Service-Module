# -*- coding: utf-8 -*-
{
    'name': "equip3_base_import_extend",

    'summary': """
        Module for import data use background method""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",
    'website': "http://www.hashmicro.com",

    'category': 'Uncategorized',
    'version': '1.1.11',

    'depends': ['base','equip3_hashmicro_ui','base_import'],

    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'data/ir_config_parameter.xml',
        'views/import_logs.xml',
        'views/assets.xml',
        'views/res_config_setting.xml',
        'views/import_logs_history.xml',
        # 'views/templates.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],
    'qweb': [
        'static/src/xml/base_import.xml'
    ],
    'auto_install': True,
    'installable': True,
    'application': True,
}
