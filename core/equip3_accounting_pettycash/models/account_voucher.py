from odoo import api, fields, models


class AccountVoucher(models.Model):
    _inherit = 'account.voucher'

    def _get_voucher_fund_custodian(self):
        for voucher in self:
            if voucher.petty_cash_fund and voucher.petty_cash_fund.custodian == self.env.user:
                voucher.is_voucher_fund_custodian = True

    petty_cash_fund = fields.Many2one('account.pettycash.fund', 'Petty Cash Fund')
    submitter_id = fields.Many2one('res.users', string='Submitter')
    is_pettycash_voucher_approved = fields.Boolean('Petty Cash Voucher Approved')
    attachment = fields.Binary('Attachment')
    attachment_name = fields.Char("Attachment Name")
    is_voucher_fund_custodian = fields.Boolean(compute='_get_voucher_fund_custodian', string='Voucher Fund Custodian')

    def action_voucher_approve(self):
        for voucher in self:
            voucher.is_pettycash_voucher_approved = True
            pettycash_fund_voucher_id = self.env['account.pettycash.fund.voucher'].search(
                [('voucher', '=', voucher.id)])
            for fund_voucher in pettycash_fund_voucher_id:
                if fund_voucher:
                    fund_voucher.write({'state': 'approved'})
        return True

    def button_cancel_voucher(self):
        for voucher in self:
            voucher.cancel_voucher()
