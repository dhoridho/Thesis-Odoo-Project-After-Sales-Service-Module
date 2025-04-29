# -*- coding: utf-8 -*-
{
    'name': "Dashboard Ninja",

    'summary': """
        Revamp your Odoo Dashboard like never before! It is one of the best dashboard odoo apps in the market.
    """,

    'description': """
        Dashboard Ninja v14.0,
        Odoo Dashboard,
        Dashboard,
        Dashboards,
        Odoo apps,
        Dashboard app,
        HR Dashboard,
        Sales Dashboard,
        inventory Dashboard,
        Lead Dashboard,
        Opportunity Dashboard,
        CRM Dashboard,
        POS,
        POS Dashboard,
        Connectors,
        Web Dynamic,
        Report Import/Export,
        Date Filter,
        HR,
        Sales,
        Theme,
        Tile Dashboard,
        Dashboard Widgets,
        Dashboard Manager,
        Debranding,
        Customize Dashboard,
        Graph Dashboard,
        Charts Dashboard,
        Invoice Dashboard,
        Project management,
        ksolves,
        ksolves apps,
        Ksolves India Ltd.
        Ksolves India  Limited,
        odoo dashboard apps
        odoo dashboard app
        odoo dashboard module
        odoo modules
        dashboards
        powerful dashboards
        beautiful odoo dashboard
        odoo dynamic dashboard
        all in one dashboard
        multiple dashboard menu
        odoo dashboard portal
        beautiful odoo dashboard
        odoo best dashboard
        dashboard for management
        Odoo custom dashboard
        odoo dashboard management
        odoo dashboard apps
        create odoo dashboard
        odoo dashboard extension
        odoo dashboard module
    """,

    'author': "Ksolves India Ltd.",
    'license': 'OPL-1',
    'currency': 'EUR',

    'price': 344.9,
    'website':  "https://store.ksolves.com/",
    'maintainer': 'Ksolves India Ltd.',

    'live_test_url': 'https://dashboardninja14.kappso.com/web/demo_login',
    'category': 'Tools',
    'version': '1.1.2',
    'support': 'sales@ksolves.com',
    'images': ['static/description/diwali_discount.gif'],

    'depends': ['base', 'web', 'base_setup', 'bus'],

    'data': [
        'security/ir.model.access.csv',
        'security/ks_security_groups.xml',
        'data/ks_default_data.xml',
        'views/ks_dashboard_ninja_view.xml',
        'views/ks_dashboard_ninja_item_view.xml',
        'views/ks_dashboard_ninja_assets.xml',
        'views/ks_dashboard_action.xml',
        'views/ks_import_dashboard_view.xml',
    ],

    'qweb': [
        'static/src/xml/ks_dn_global_filter.xml',
        'static/src/xml/ks_dashboard_ninja_templates.xml',
        'static/src/xml/ks_dashboard_ninja_item_templates.xml',
        'static/src/xml/ks_dashboard_ninja_item_theme.xml',
        'static/src/xml/ks_widget_toggle.xml',
        'static/src/xml/ks_dashboard_pro.xml',
        'static/src/xml/ks_import_list_view_template.xml',
        'static/src/xml/ks_quick_edit_view.xml',
        'static/src/xml/ks_to_do_template.xml',
    ],

    'demo': [
        'demo/ks_dashboard_ninja_demo.xml',
    ],

    'uninstall_hook': 'uninstall_hook',
    'auto_install': True,
}
