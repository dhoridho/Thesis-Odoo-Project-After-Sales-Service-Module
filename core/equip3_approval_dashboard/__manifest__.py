# -*- coding: utf-8 -*-
{
   'name': 'Approval Dashboard',
   'version': '1.1.8',
   'author': 'Hashmicro / Denada',
   'depends': [
      'board',
      'base',
      'mail',
      'web',
      'ks_dashboard_ninja',
      'equip3_hashmicro_ui',

      ],
   'data': [
      'security/ir.model.access.csv',
      "views/views.xml",

   ],
   'qweb': [
      'static/src/xml/*.xml',
   ],
   'installable': True,
   'application': True,

}
