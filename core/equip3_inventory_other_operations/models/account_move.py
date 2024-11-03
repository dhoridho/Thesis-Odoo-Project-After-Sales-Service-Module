
from odoo import fields, models, api, _

class AccountMove(models.Model):
    _inherit = "account.move"

    repair_id = fields.Many2one('repair.order', string='Repair Order')
