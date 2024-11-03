{
    'name': 'Equip3 Aftersales Master Data',
    'version': '1.1.4',
    'author': 'Hashmicro / Diki',
    'website': "https://www.hashmicro.com",
    'category': 'Uncategorized',
    'summary': """
    """,
    'depends': [
        'base',
        'branch',
        'equip3_hashmicro_ui'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/aftersale_masterdata_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
