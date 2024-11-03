# -*- coding: utf-8 -*-
{
    'name': "Equip3 Construction Reports",

    'summary': """
        This module is made for reporting sub menu""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Angeline Felicia",
    'website': "http://www.hashmicro.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Construction',
    'version': '1.1.24',

    # any module necessary for this one to work correctly
    'depends': [
                'equip3_construction_accounting_operation',
                'equip3_construction_operation',
                'ks_dashboard_ninja','ks_gantt_view_base',
                'equip3_construction_accessright_setting',
                ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/construction_report_css_assets.xml',
        'views/cons_reporting_view.xml',
        'wizard/s_curve_view.xml',
        'views/job_order_analysis.xml',
        'views/cost_progress_analysis_view.xml',
        'views/gantt_chart.xml',
        'views/progressive_claim_view.xml',
        'data/cons_data.xml',
        'views/weekly_report_view.xml',
        'views/issue_analysis_view.xml',
        'views/view_icon_flow.xml',
        'wizard/const_sale_flow_wizard_views.xml',
        'wizard/material_purchase_flow_wizard_views.xml',
        'wizard/subcontracting_flow_wizard_views.xml',
        'wizard/project_flow_view.xml',
        'wizard/project_budget_flow_wizard_views.xml',
        'wizard/claim_request_view.xml',
        'wizard/customer_progressive_claim_flow_wizard_views.xml',
        'wizard/vendor_progressive_claim_flow_wizard_views.xml',
        'wizard/assets.xml',
    ],
    
    'qweb': [
        'static/xml/const_sale_configuration_flow.xml',
        'static/xml/t_customer_progressive_claim_flow_wizard.xml',
        'static/xml/t_material_purchase_flow_wizard.xml',
        'static/xml/t_project_budget_flow_wizard.xml',
        'static/xml/t_project_flow_wizard.xml',
        'static/xml/t_subcontracting_flow_wizard.xml',
        'static/xml/t_vendor_progressive_claim_flow_wizard.xml',
    ],

}
