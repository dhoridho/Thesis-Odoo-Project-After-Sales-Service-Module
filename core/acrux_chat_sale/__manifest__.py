# -*- coding: utf-8 -*-

{
    'name': 'ChatRoom WhatsApp All in One',
    'summary': 'Real WhatsApp All in One Screen integration. Send Product, Sale Order, Invoice, Partner. Connector. Chat-Api. ChatApi. Drag and Drop. ChatRoom.',
    'description': 'Real WhatsApp All in One Screen integration. Send Product, Sale Order, Invoice and Partner. Connector. Chat-Api. ChatApi. Drag and Drop. ChatRoom.',
    'version': '1.1.3',
    'author': 'AcruxLab',
    'live_test_url': 'https://chatroom.acruxlab.com/web/signup',
    'support': 'info@acruxlab.com',
    'price': 50,
    'currency': 'USD',
    'images': ['static/description/Banner_full.gif'],
    'website': 'https://acruxlab.com',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'category': 'Sales',
    'depends': [
        'acrux_chat',
        'acrux_chat_chatapi',  # Uncomment for Odoo Apps. Comment if buy 'acrux_chat_gupshup' !
        'sale_management',
    ],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'wizard/MessageWizard.xml',
        'wizard/SelectConversation.xml',
        'views/sale_order_views.xml',
        'views/account_view.xml',
        'views/acrux_chat_connector_views.xml',
        'views/acrux_chat_conversation_views.xml',
        'views/res_partner.xml',
        'reports/reports.xml',
        'reports/dashboard.xml',
        'views/include_template.xml',
    ],
    'qweb': [
        'static/src/xml/acrux_chat_template.xml',
    ],
}
