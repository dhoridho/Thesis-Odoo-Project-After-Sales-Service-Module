# -*- coding: utf-8 -*-

{
    'name': 'Equip3 Construction Engineering Extd',
    'version': '1.1.2',
    'category': 'Construction',
    'description':
        """
        equip3_construction_engineering_extd

    """,
    'summary': 'equip3_construction_engineering',
    'author': 'Hashmicro',
    'website': 'http://www.hashmicro.com',
    'depends': ['sh_po_tender_management', 'equip3_construction_engineering', 'equip3_construction_purchase_other_operation'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/purchase_tender_create_wizard_view_inherit.xml',
        'views/purchase_tender_view_inherit.xml',
        ],
    "installable": True,
    "application": False,
    "auto_install": False
}