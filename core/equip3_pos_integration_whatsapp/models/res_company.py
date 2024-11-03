# -*- coding: utf-8 -*-

from odoo import models, fields

class Company(models.Model):
    _inherit = 'res.company'

    pos_whatsapp_notification_for_receipt = fields.Boolean('Whatsapp Notification for Receipt')
    pos_whatsapp_auto_sent_receipt_to_member = fields.Boolean('Whatsapp Auto Sent receipt to Member')