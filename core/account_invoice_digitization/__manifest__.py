# -*- coding: utf-8 -*-

{
    'name': 'Account Invoice Digitization',
    'summary': 'Digitize your vendor bills and invoices with OCR and Artificial Intelligence | Invoice automation | ChatGPT | GPT | Automate Accounting',
    'description': "Digitize your vendor bills and invoices with OCR and Artificial Intelligence",
    'category': 'Accounting/Accounting',
    'author': 'Winotto',
    'website': 'https://winotto.com',
    'version': '14.0.2.3',
    'depends': [
        'account_edi', 'mail'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
    'price': 197.00,
    'data': [
      'views/assets.xml',
    ],
    'qweb': [
        'static/src/attachment_viewer/attachment_viewer.xml',
        'static/src/xml/*.xml',
    ],
    'external_dependencies': {
        'python': ['pytesseract', 'pypdf', 'pdf2image']
    },
    'images': ['static/description/main_screenshot.png'],
    'live_test_url': 'https://odooapps-demo.winotto.com'
}
