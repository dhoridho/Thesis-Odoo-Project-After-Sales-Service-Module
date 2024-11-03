# -*- coding: utf-8 -*-

{
    'name': 'Equip 3 - Manufacturing Reports',
    'version': '1.1.84',
    'category': 'Manufacturing',
    'summary': 'Manufacturing Reports',
    'description': '''
    i. Manufacturing Plan Report
    ii. Manufacturing Order Report
    iii. Work Order Report
    iv. Production Record Report
    v. Dashboard
    vi. Gantt Chart Report for Manufacturing Plan/ Manufacturing Order/ Work Order
    ''',
    'author': 'HashMicro / Rajib',
    'website': 'www.hashmicro.com',
    'depends': [
        'equip3_manuf_kiosk',
        'equip3_manuf_purchase',
        'equip3_manuf_sale',
        'equip3_manuf_cutting',
        'equip3_manuf_subcontracting',
        'equip3_manuf_other_operations',
        'equip3_inventory_reports',
        'dynamic_accounts_report',
        'ks_dashboard_ninja',
        'ks_dn_advance',
        'equip3_hashmicro_ui'
    ],
    'data': [
        'data/ks_dashboard_data.xml',
        'security/ir.model.access.csv',
        'templates/templates.xml',
        'views/mrp_report.xml',
        'views/finished_good_report_view.xml',
        'views/rejected_good_report_view.xml',
        'views/rejected_material_report_view.xml',
        'views/material_usage_report_view.xml',
        'views/work_center_gantt_chart.xml',
        'views/mrp_production_gantt_views.xml',
        'views/mrp_production_views.xml',
        'views/mrp_workcenter_views.xml',
        'views/stock_quant_view.xml',
        'views/mrp_subcon_report_views.xml',
        'views/ks_dashboard_ninja_item_views.xml',
        'views/moving_production_cost_report_views.xml',
        'views/moving_plan_cost_report_views.xml',
        'views/production_cost_comparison_views.xml',
        'wizard/manuf_flow_wizard.xml',
        'views/mrp_menuitems.xml',
        'views/iconmenu.xml',
        'reports/manuf_layout.xml',
        'reports/report_mrp_production.xml',
        'reports/report_mrp_plan.xml',
        'reports/report_work_order.xml',
        'reports/mrp_cost_analysis.xml',
        'reports/report_production_record.xml',
        'reports/cogm_report.xml',
        'views/smart_button.xml',

    ],
    'qweb': [
        "static/src/xml/custom_template.xml",
        "static/src/xml/manuf_flow.xml",
        "static/src/xml/cost_of_goods_manufactured.xml",
        "static/src/xml/moving_production_cost_report.xml",
        "static/src/xml/moving_plan_cost_report.xml",
        "static/src/xml/ks_gantt_workorder.xml",
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}
