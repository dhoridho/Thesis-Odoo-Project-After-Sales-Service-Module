# -*- coding: utf-8 -*-
{
   'name': 'Equip3 CRM Meeting Summary',
   'version': '1.1.4',
   'author': 'Hashmicro / Prince',
   'depends': [
      'calendar',
      'equip3_crm_operation'
   ],
   'data': [
        'security/ir.model.access.csv',
        "views/calendar_event_views.xml",
        'views/calendar_meeting_summary_views.xml',
        'views/res_config.xml',
        'views/calendar_event_type.xml',
        'views/summary_template.xml',
        'views/calendar_event_type.xml',
   ],
   'installable': True,
}
