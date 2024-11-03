{
    'name': 'Equip3 - Spreadsheet',
    'author': 'Hashmicro / Rajib',
    'version': '1.1.1',
    'category': 'General',
    'summary': 'Spreadsheet',
    'description': 'Spreadsheet',
    'depends': [
        'web'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/assets.xml',
        'views/spreadsheet_document_views.xml'
    ],
    'qweb': [
        'static/src/xml/pivot_dialog.xml',
        'static/src/xml/spreadsheet.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}