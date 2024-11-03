# -*- coding: utf-8 -*-
{
    'name': "Equip3 Work Center Result Report",
    'summary': "Feature Work Center Result Report",
    'description': "Feature Work Center Result Report",
    'author': "PT. HashMicro Pte. Ltd.",
    'website': "http://www.hashmicro.com",
    'category': 'Uncategorized',
    'version': '1.1.3',
    'depends': ['hr','equip3_manuf_operations_contd'],
    'data': [
        'views/assets.xml',
        'views/mrp_views.xml',
        'views/wo_result_report_dashboard_views.xml',
    ],
    'qweb': [
      'static/src/xml/*.xml',
   ],

}
