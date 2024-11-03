# -*- coding: utf-8 -*-
{
   'name': 'Equip3 CRM Masterdata',
   'version': '1.1.14',
   'author': 'Hashmicro / Prince',
   'depends': ['base', 'equip3_sale_masterdata', 'crm', 'crm_phonecall', 'simplify_access_management'],
   'data': [
      'data/access_management.xml',
      'security/ir.model.access.csv',
      "security/crm_security.xml",
      "views/crm_meeting_config_views.xml",
      "views/res_partner_views.xml",
      "views/whatsapp_template_views.xml",
      "views/crm_stage_views.xml",
      "views/crm_lead_view.xml",
      "views/sale_order_view.xml"
   ],
   'installable': True,
}
