from odoo import api, fields, models, _

class BankAccounAccount(models.Model):
    _inherit = 'bank.account.account'


    bank_id = fields.Many2one('res.bank', string="Bank")
    bank_bic = fields.Char(string="Bank Identifier Code")

    @api.onchange('bank_id')
    def onchange_bank_id(self):
        if self.bank_id:
            self.bank_bic = self.bank_id.bic