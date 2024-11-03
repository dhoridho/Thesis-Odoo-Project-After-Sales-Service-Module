from odoo import api, fields, models, _

class BankAccounAccount(models.Model):
    _name = 'bank.account.account'
    _description = "Bank Account Account"
    _rec_name = 'bank_id'

    acc_number = fields.Char(string="Account Number", required=True)
    bank_id = fields.Many2one('res.bank', string="Bank")
    bank_bic = fields.Char(string="Bank Identifier Code")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, readonly=False, domain=lambda self: [('id', 'in', self.env.branches.ids)])

    @api.model
    def create(self, values):
        res = super(BankAccounAccount, self).create(values)
        for rec in res:
            values = {
                'company_id': rec.company_id.id,
                'name': rec.bank_id.name + "-"+ rec.acc_number,
                'type': 'bank',
                'code': rec.bank_bic,
                }
            self.env['account.journal'].sudo().create(values)
        return res