# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CreateRecurringInvoice(models.TransientModel):
    _name = 'create.recurring.invoice'
    _description = 'Create Recurring Invoice'
    
    start_date = fields.Date(
        string='Date',
        required=True,
        default=fields.date.today(),
    )
    
#    @api.multi
    def create_recurring_invoice(self):
        analytic_account_obj = self.env['account.analytic.account']
        contracts = analytic_account_obj.search([('recurring_next_date','=',self.start_date)])
        invoice_id = []
        if not contracts:
            raise UserError(_("Recurring Invoice are not found for selected date."))
        else:
            for contract in contracts:
                invoice = contract._recurring_create_invoice()
                invoice_id.append(invoice[0].id)
        return self.action_subscription_invoice(invoice_id)

#    @api.multi
    def action_subscription_invoice(self, invoice):
#        action = self.env.ref('account.action_invoice_tree1').read()[0]
#        action = self.env.ref('account.view_invoice_tree').read()[0]
        action = self.env.ref('account.action_move_out_invoice_type').sudo().read()[0]
        action['domain'] = [('id', 'in', invoice)]
        return action
