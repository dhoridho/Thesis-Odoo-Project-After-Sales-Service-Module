# -*- coding: utf-8 -*-

{
    'name': 'ChatRoom WhatsApp CRM',
    'summary': '',
    'description': '',
    'version': '1.1.1',
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
        'crm',
    ],
    'data': [
        'views/crm_lead_views.xml',
        'views/acrux_chat_conversation_views.xml',
        'views/include_template.xml',
    ],
    'qweb': [
        'static/src/xml/acrux_chat_template.xml',
    ],
}
