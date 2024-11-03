# -*- coding: utf-8 -*-
{
   'name': 'Hashmicro Theme',
   'version': '1.6.36',
   'author': 'Hashmicro / Prince / Rajib',
   'depends': [
      'sh_backmate_theme_adv',
      'oi_web_search',
      'website',
      'oi_login_as',
      'ks_dn_advance',
      'app_search_range_date_number'
   ],
   'data': [
      'security/ir.model.access.csv',
      'data/ir_ui_menu_category_data.xml',
      'data/on_upgrade.xml',
      'views/assets.xml',
      'views/ir_ui_menu_views.xml',
      'views/website_inherit.xml',
      'views/customer_view.xml',
   ],
   'qweb': [
      'static/src/xml/base.xml',
      'static/src/xml/menu.xml',
      'static/src/xml/control_panel.xml',
      'static/src/xml/debug.xml'
   ],
   'auto_install': True,
   'installable': True,
   'application': True,
   'post_load': '_post_load_hook',
   'uninstall_hook': '_uninstall_hook',
}
