# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    whatsapp_api_url = fields.Char(string='WhatsApp API URL', default='https://api.chat-api.com')
    whatsapp_api_instance = fields.Char(string='Instance')
    whatsapp_api_token = fields.Char(string='Token')
    whatsapp_api_authentication = fields.Boolean("Authentication")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: