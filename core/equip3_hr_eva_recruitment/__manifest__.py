# -*- coding: utf-8 -*-
{
   'name': 'Hashmicro eva recruitment',
   'version': '1.1.4',
   'author': 'Hashmicro / denada',
   'depends': ['web','hr_recruitment','equip3_hr_recruitment_extend','sh_backmate_theme_adv','equip3_hr_accessright_settings'],
   'data': [
      "data/groups.xml",
      "data/group_data.xml",
      "data/user_data.xml",
      "views/views.xml",
      "views/menu.xml",
      "views/res_users_views.xml",
   ],
   'qweb': [
      'static/src/xml/*.xml',
   ],
   # 'auto_install': True,
   'installable': True,
   # 'application': True
}
