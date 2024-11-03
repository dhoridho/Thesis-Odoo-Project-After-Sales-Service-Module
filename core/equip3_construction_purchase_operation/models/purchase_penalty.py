from odoo import models, fields, api


class PurchasePenalty(models.Model):
    _inherit = 'construction.penalty'

    penalty_contract = fields.Selection([('contract_cancel', 'Contract Cancel')], string='Penalty Type',default='contract_cancel')
    is_purchase_penalty = fields.Boolean('Purchase penalty', default=False)

    @api.model
    def create(self, vals):
        if 'penalty_contract' in vals:
            vals['penalty'] = 'contract_cancel'
        return super(PurchasePenalty, self).create(vals)

PurchasePenalty()