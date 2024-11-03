# -*- coding: utf-8 -*-
{
    'name': "Equip3 CRM WhatsApp",
    'summary': """
        Posting message to Sale Quotation/CRM Chatter from ChatRoom """,
    'description': """
        This module manages these features :
        1. Post message to Sale Quotation oe_chatter from Chat Room
        2. Post message to CRM oe_chatter from Chat Room
    """,
    'author': "HashMicro",
    'website': 'www.hashmicro.com',
    'category': 'CRM',
    'version': '1.3.1',
    'depends': ['product', 'acrux_chat', 'acrux_chat_sale', 'crm'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/sync_conversation.xml',
        'wizard/users_wiz_login.xml',
        'views/qiscuss_connector.xml',
        'views/chatroom_view.xml',
        'views/backend_views.xml',
        'views/default_answer.xml',
        # 'views/crm_lead_views.xml',
        'views/res_partner_view.xml',
        ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
