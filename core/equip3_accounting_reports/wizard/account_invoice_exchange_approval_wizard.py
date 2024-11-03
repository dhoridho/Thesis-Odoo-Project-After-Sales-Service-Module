from odoo import fields, models, api


class AccountInvoiceExchangeApprovalWizard(models.TransientModel):
    _name = 'account.invoice.exchange.approval.wizard'

    reason = fields.Text()


    def action_submit(self):
        self.ensure_one()
        AccountInvoiceExchange = self.env['account.invoice.exchange'].browse(self._context.get('active_ids', []))
        AccountInvoiceExchange.reason = self.reason
        
        if self.env.context.get('is_approve'):
            AccountInvoiceExchange.action_approve()
        else:
            AccountInvoiceExchange.action_reject()