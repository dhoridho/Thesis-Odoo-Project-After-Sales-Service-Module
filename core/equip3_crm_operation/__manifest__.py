# -*- coding: utf-8 -*-
{
    'name': "Equip3 CRM Operation",

    'summary': """
          Manage Lead, Pipeline, Opportunity, Activity Operation""",

    'description': """
        This module manages these features :
        1. Leads 
        2. Pipelines 
        3. Opportunity 
        4. Activity 
    """,

    'author': "Hashmicro",
    'category': 'CRM',
    'version': '1.3.24',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'branch',
        'crm',
        'sale_crm',
        'app_crm_superbar',
        'base_geolocalize',
        'calendar',
        "equip3_crm_masterdata",
        'sales_team',
        'acrux_chat_sale',
        'equip3_hashmicro_ui',
        'acrux_whatsapp_crm',
        'equip3_general_setting',
        'equip3_kanban_view'
    ],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/crm_security.xml',
        "data/data.xml",
        'data/ir_sequence.xml',
        'data/crm_types_data.xml',
        'data/crm_city_data.xml',
        'data/ir_cron.xml',
        'data/mail_template.xml',
        'data/crm_send_message_mass_data.xml',
        'wizard/crm_lead_meeting_lost_views.xml',
        'wizard/crm_lead_meeting_reschedule_views.xml',
        'wizard/crm_send_message_mass_view.xml',
        'views/menu_category.xml',
        "views/assets.xml",
        'views/views.xml',
        "views/calendar_event_views.xml",
        'views/templates.xml',
        'views/res_config_settings_views.xml',
        'views/crm_lead_view_updated.xml',
        'views/crm_lead_type_views.xml',
        'views/res_partner_views.xml',
        'views/crm_stage.xml',
        'views/whatsapp_wizard_view.xml',
        'views/mail_activity_type_views.xml',
        "views/mail_activity_views.xml",
        'views/crm_phonecall.xml',
        'views/crm_team_views.xml',
        'views/crm_target_view.xml'
    ],
    'qweb': [
        'static/src/xml/kanban.xml',
        'static/src/xml/einstein_score.xml',
        'static/src/xml/web_map.xml',
        'static/src/xml/base.xml',
        'static/src/xml/activity.xml',
        'static/src/xml/web_kanban_activity.xml'
    ],
    "auto_install": True,
}