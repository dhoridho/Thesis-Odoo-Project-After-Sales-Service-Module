from odoo import api, fields, models, _


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def unlink(self):
        aml_to_cancel = self.env['account.move.line']
        for partial in self:
            aml_to_cancel |= partial.credit_move_id
            aml_to_cancel |= partial.debit_move_id
        res = super(AccountPartialReconcile, self).unlink()
        for aml in aml_to_cancel:
            if aml.move_id.move_type != 'entry':
                aml.move_id._compute_amount()
        return res
