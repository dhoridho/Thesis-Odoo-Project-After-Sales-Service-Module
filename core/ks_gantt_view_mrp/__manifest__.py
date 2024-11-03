# -*- coding: utf-8 -*-
{
    'name': "Odoo Gantt View Manufacturing",

    'summary': """
            This module provides you a Gantt View while scheduling different manufacturing tasks,
            which helps you to effectively manage your tasks with time. You can keep track of
            dependent tasks, prioritize a task over another, and see the availability of resources to
            complete a task within a time limit.
        """,

    'description': """
        work orders management system in odoo
        work orders in odoo
        manage / edit work orders in odoo
        odoo manufacturing app  
        odoo manufacturing module
        manufacturing module odoo
        manufacturing modules in odoo
        employee work schedule in odoo
        apps for odoo manufacturing
        manufacturing apps for odoo
        odoo work orders apps
        odoo 14 manufacturing management
        odoo manufacturing 14
        manufacturing gantt chart
        manufacturing managers odoo app
        manufacturing order management in odoo
        gantt view in work orders 
        gantt view in manufacturing
        work orders  in manufacturing module 
        manufacturing app for odoo
    """,
    'author': "Ksolves India Ltd.",
    'license': 'OPL-1',
    'currency': 'EUR',
    'price': 0,
    'live_test_url': 'https://ganttview14.kappso.com',
    'website': "https://store.ksolves.com",
    'maintainer': 'Ksolves India Ltd.',
    'category': 'Tools',
    'version': '14.0.0',
    'support': 'sales@ksolves.com',
    'depends': ['ks_gantt_view_base', 'mrp', 'hr'],
    'images': [
        "static/description/banner_new.gif",
    ],
    'data': [
        'data/data.xml',
        'views/ks_mrp_production.xml',
        'views/ks_mrp_production_view.xml',
        'security/ir.model.access.csv',
        'views/ks_mrp_gantt_settings.xml',
        'views/ks_gantt_mrp_production_assets.xml',
        'views/ks_import_mrp_production.xml',
        'views/ks_import_work_order.xml',
        'views/ks_gantt_mrp_wo.xml',
    ],
}
