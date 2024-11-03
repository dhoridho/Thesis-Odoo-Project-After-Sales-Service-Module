from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sales_to_manufacturing = fields.Boolean('Sales To Production')
    send_email_so_confirm = fields.Boolean('Send Email Notification when SO Confirm')
    send_system_so_confirm = fields.Boolean('Send System Notification when SO Confirm')
    send_whatsapp_so_confirm = fields.Boolean('Send WhatsApp Notification when SO Confirm')
    check_availability = fields.Boolean()
