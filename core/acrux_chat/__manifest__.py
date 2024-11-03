# -*- coding: utf-8 -*-

{
    'name': 'ChatRoom WhatsApp Base',
    'summary': 'Connector base module. It only contains the communication structure. ChatRoom.',
    'description': 'Connector base module. It only contains the communication structure. ChatRoom.',
    'version': '1.1.3',
    'author': 'AcruxLab',
    'live_test_url': '',
    'support': 'info@acruxlab.com',
    'price': 1800.0,
    'currency': 'USD',
    'images': ['static/description/Banner_base.png'],
    'website': 'https://acruxlab.com',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'category': 'Sales',
    'depends': [
        'board',
        'bus',
        'stock',
        'product',
        'sales_team'
    ],
    'data': [
        'data/data.xml',
        'data/cron.xml',
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/CustomMessage.xml',
        'views/ir_attachment.xml',
        'views/acrux_chat_default_answer_views.xml',
        'views/acrux_chat_connector_views.xml',
        'views/acrux_chat_conversation_views.xml',
        'views/acrux_chat_message_views.xml',
        'views/res_users_views.xml',
        'views/menu.xml',
        'reports/reports.xml',
        'reports/dashboard.xml',
        'views/include_template.xml',
    ],
    'qweb': [
        'static/src/xml/acrux_chat_template.xml',
    ],
    'post_load': 'patch_json_response',
    'external_dependencies': {'python': ['phonenumbers']},

}
