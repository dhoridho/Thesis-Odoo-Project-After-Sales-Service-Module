# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.
{
    "name": "All In One Purchase Tools | Best Purchase Tools | Top Purchase Tools",

    'author': 'Softhealer Technologies',

    'website': 'https://www.softhealer.com',

    "support": "support@softhealer.com",

    'version': '1.1.1',

    'category': "Purchases",
    
    "license": "OPL-1",

    'summary': "Split Purchase,Merge Purchase,Archive Record,Unarchive Record,Cancel Purchase,Checklist,Document Management,Excel Report,Product Search,Custom Field,Customer History,Product History,Report Section,Template Product,Whatsapp Integration Odoo",

    'description':"All In One Purchase Tools",


    "depends": ["purchase",],

    "data": [
        
    "views/sh_all_in_one_purchase_tool_config_views.xml",

    "sh_base_whatsapp_integration/security/whatsapp_security.xml",
    "sh_base_whatsapp_integration/security/ir.model.access.csv",
    "sh_base_whatsapp_integration/views/res_users_inherit_view.xml",
    "sh_base_whatsapp_integration/wizard/send_whasapp_number_view.xml",
    "sh_base_whatsapp_integration/wizard/send_whatsapp_message_view.xml",
    "sh_base_whatsapp_integration/views/res_partner_views.xml",
    "sh_base_whatsapp_integration/views/mail_message.xml",
    
    "sh_merge_purchase_order/security/ir.model.access.csv",
    "sh_merge_purchase_order/security/sh_merge_purchase_order_security.xml",
    "sh_merge_purchase_order/wizard/merge_purchase_order.xml",
   
    "sh_purchase_archive/views/purchase_order_inherit.xml",
     
    "sh_purchase_cancel/security/purchase_security.xml",
    "sh_purchase_cancel/data/data.xml",
    "sh_purchase_cancel/views/purchase_config_settings.xml",
    "sh_purchase_cancel/views/views.xml",
    
    "sh_purchase_custom_checklist/security/purchase_custom_checklist_security.xml",
    "sh_purchase_custom_checklist/security/ir.model.access.csv",
    "sh_purchase_custom_checklist/views/purchase_custom_checklist.xml",
    "sh_purchase_custom_checklist/views/purchase_custom_checklist_template.xml",    
    
    "sh_purchase_custom_product_template/security/purchase_custom_product_template_security.xml",
    "sh_purchase_custom_product_template/security/ir.model.access.csv",
    "sh_purchase_custom_product_template/views/purchase_template_product.xml",
    
    "sh_purchase_digital_sign/views/digital_sign.xml",
    "sh_purchase_digital_sign/reports/digital_sign_report.xml",
    
    "sh_purchase_document/security/purchase_document_security.xml",
    "sh_purchase_document/data/purchase_document_email_notification_template.xml",
    "sh_purchase_document/data/purchase_document_scheduler.xml",
    "sh_purchase_document/views/sh_ir_attachments_views.xml",
    "sh_purchase_document/views/purchase.xml",
    "sh_purchase_document/views/general_config_settings.xml",
    
    "sh_purchase_excel/security/ir.model.access.csv",
    "sh_purchase_excel/views/purchase_order_inherit_view.xml",
    "sh_purchase_excel/views/purchase_report_xlsx_view.xml",
    "sh_purchase_excel/views/purchase_quotation_inherit_view.xml",
    "sh_purchase_excel/views/purchase_quotation_xlsx_view.xml",
    
    "sh_purchase_multi_product_adv/security/ir.model.access.csv",
    "sh_purchase_multi_product_adv/security/purchase_multi_product_adv_security.xml",
    "sh_purchase_multi_product_adv/views/settings_view.xml",
    "sh_purchase_multi_product_adv/wizard/pmps_wizard.xml",
    "sh_purchase_multi_product_adv/views/purchase_view.xml",
    
    "sh_purchase_order_custom_fields/data/purchase_order_custom_field_group.xml",
    "sh_purchase_order_custom_fields/security/ir.model.access.csv",
    "sh_purchase_order_custom_fields/views/purchase_order.xml",
    "sh_purchase_order_custom_fields/views/purchase_tab.xml",
    
    "sh_purchase_order_history/security/ir.model.access.csv",
    "sh_purchase_order_history/security/purchase_order_history_security.xml",
    "sh_purchase_order_history/views/purchase_order_history.xml",
    
    "sh_purchase_price_history/security/ir.model.access.csv",
    "sh_purchase_price_history/security/purchase_order_price_history_security.xml",
    "sh_purchase_price_history/views/purchase_price_history.xml",
    
    "sh_report_section/security/report_template_security.xml",
    "sh_report_section/security/ir.model.access.csv",
    "sh_report_section/data/section_data.xml",
    "sh_report_section/report/sale_order_template.xml",
    "sh_report_section/report/sale_order_template_basic.xml",
    "sh_report_section/report/sale_order_template_internal.xml",
    "sh_report_section/views/sh_report_section_view.xml",
    
    "sh_purchase_report_section/views/purchase_order_template_view.xml",
    "sh_purchase_report_section/report/purchase_template.xml",
    "sh_purchase_report_section/report/purchase_rfq_template.xml",
    
    "sh_purchase_tags/security/ir.model.access.csv",
    "sh_purchase_tags/security/mass_tag_update_rights.xml",
    "sh_purchase_tags/views/purchase_order_tags_view.xml",
    "sh_purchase_tags/views/purchase_order_view.xml",
    "sh_purchase_tags/views/mass_tag_update_wizard_view.xml",
    "sh_purchase_tags/views/mass_tag_update_action.xml",
    
    "sh_purchase_whatsapp_integration/data/purchase_email_data.xml",
    "sh_purchase_whatsapp_integration/security/whatsapp_security.xml",
    "sh_purchase_whatsapp_integration/views/purchase_order_inherit_view.xml",
    "sh_purchase_whatsapp_integration/views/res_config_settings.xml",
    
    "split_rfq/security/split_rfq_security.xml",
    "split_rfq/security/ir.model.access.csv",
    "split_rfq/views/split_rfq_view.xml",
    "split_rfq/wizard/split_rfq_wizard.xml",
    
    
    
    ],

    'images': ['static/description/background.gif', ],

    "installable": True,
    "application": True,
    "autoinstall": False,

    "price": 100,
    "currency": "EUR"
}
