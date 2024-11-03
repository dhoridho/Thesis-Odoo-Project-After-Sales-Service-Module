# -*- coding: utf-8 -*-
{
    'name': "equip3_clonning_prevention",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Hashmicro",
    'website': "https://www.hashmicro.com",

    # for the full list
    'category': 'Uncategorized',
    'version': '1.1.1',

    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/prevention_group.xml',
        'data/ip_data.xml',
        'wizard/update_ip_rules.xml',
        'data/redirect_page.xml',
        'views/ip_alllowed_rules.xml',

    ],

}
