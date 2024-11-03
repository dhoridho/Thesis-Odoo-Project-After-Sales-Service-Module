from odoo import api, fields, models, _
from datetime import datetime

class AccountPaymentRegIng(models.TransientModel):
    _inherit = 'account.payment.register'

    journal_id2 = fields.Many2one('account.journal', string='Journal', required=False, domain="[('type', 'in', ('bank', 'cash'))]", compute='_compute_journal_id', store=True, readonly=False)

    def _create_payment_vals_from_wizard(self):
        res = super(AccountPaymentRegIng, self)._create_payment_vals_from_wizard()
        active = self.env['account.move'].browse(self.env.context.get('active_ids'))
        res['analytic_group_ids'] = active.analytic_group_ids.ids
        return res
    

    @api.depends('company_id', 'source_currency_id')
    def _compute_journal_id(self):
        for wizard in self:
            domain = [
                ('type', 'in', ('bank', 'cash')),
                ('company_id', '=', wizard.company_id.id),
            ]
            journal = None
            if wizard.source_currency_id:
                journal = self.env['account.journal'].search(domain, limit=1)
            if not journal:
                journal = self.env['account.journal'].search(domain, limit=1)
            wizard.journal_id = journal.id
            wizard.journal_id2 = journal.id