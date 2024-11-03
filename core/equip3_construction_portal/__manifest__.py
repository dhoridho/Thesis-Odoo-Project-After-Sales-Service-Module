# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Portal",

    'summary': """
    Restrict Project,Job Order,Tasks from portal
        """,

    'description': """
        Restrict Project,Job Order,Tasks from portal
    """,

    'author': "Antsyz - Balaji",
    'website': "http://www.hashmicro.com",

    'category': 'Construction',
    'version': '1.1.3',

    'depends': ['project', 'portal', 'equip3_construction_purchase_operation', 'equip3_construction_purchase_other_operation', 'purchase'],

    'data': ['views/open_subcon_tender_submission_template.xml',
             'views/subcon_purchase_order_template.xml',
             'views/portal_menu.xml',
             'views/assets.xml'
             ],
}
