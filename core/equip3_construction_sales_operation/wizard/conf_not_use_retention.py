from odoo import api , models, fields 
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

class ConfirmationRetention(models.TransientModel):
    _name = 'confirm.retention'
    _description = 'Confirmation Not Use Retention '

    txt = fields.Text(string="Confirmation",default="Are you sure you don't want to use retention on this contract?")

    def action_confirm(self):
        sale = self.env['sale.order.const'].browse([self._context.get('active_id')])
        sale.write({'use_retention': False})

    