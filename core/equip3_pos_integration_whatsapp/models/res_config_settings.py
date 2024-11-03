# -*- coding: utf-8 -*-

from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    pos_whatsapp_notification_for_receipt = fields.Boolean(string='Whatsapp Notification for Receipt', 
        related='company_id.pos_whatsapp_notification_for_receipt', readonly=False)
    pos_whatsapp_auto_sent_receipt_to_member = fields.Boolean(string='Whatsapp Auto Sent receipt to Member', 
        related='company_id.pos_whatsapp_auto_sent_receipt_to_member', readonly=False)