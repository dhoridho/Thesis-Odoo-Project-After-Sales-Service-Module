from odoo import models, fields, api, _

class AccountMoveInherit(models.Model):
    _inherit = 'account.move'


    @api.model
    def default_get(self, fields):
        res = super(AccountMoveInherit, self).default_get(fields)
        for move in self:
            if move.stock_move_id:
                for line in move.line_ids:
                    line.analytic_tag_ids = move.stock_move_id.analytic_account_group_ids
        return res
