from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    agri_agreement_id = fields.Many2one('agri.agreement')
    agri_activity_record_ids = fields.Many2many('agriculture.daily.activity.record')

    def action_invoice_paid(self):
        res = super(AccountMove, self).action_invoice_paid()
        for move in self:
            if move.agri_agreement_id:
                move.agri_agreement_id.activity_line_ids._action_paid()
        return res

    def action_post(self):
        res = super(AccountMove, self).action_post()
        for move in self:
            if move.agri_agreement_id:
                move.agri_agreement_id._create_valuation(self)
        return res


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    agri_agreement_contract_id = fields.Many2one('agri.agreement.contract')
