from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = "account.move"

    reimbursement_id = fields.Many2one('fmcg.reimbursement', string="Reimbursement")