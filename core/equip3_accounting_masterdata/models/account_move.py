
from odoo import fields, models, api, _
from datetime import datetime


class AccountMove(models.Model):
    _inherit = 'account.move'


    analytic_group_ids  = fields.Many2many('account.analytic.tag',  domain="[('company_id', '=', company_id)]", string="Analytic Group")
    move_type = fields.Selection(selection=[
            ('entry', 'Journal Entry'),
            ('out_invoice', 'Customer Invoice'),
            ('out_refund', 'Customer Credit Note'),
            ('in_invoice', 'Vendor Bill'),
            ('in_refund', 'Vendor Debit Note'),
            ('out_receipt', 'Sales Receipt'),
            ('in_receipt', 'Purchase Receipt'),
        ], string='Type', required=True, store=True, index=True, readonly=True, tracking=True,
        default="entry", change_default=True)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    branch_id = fields.Many2one('res.branch', related='move_id.branch_id')