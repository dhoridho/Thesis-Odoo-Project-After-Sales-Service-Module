
from odoo import api , models, fields 


class LimitRequestWizard(models.TransientModel):
    _name = 'limit.request.wizard'
    _description = "Limit Request Wizard"

    def action_validate_limit_request(self):
        limit_id = self.env['limit.request'].browse(self._context.get('active_ids'))
        limit_id.write({'state': 'confirmed'})
        if limit_id.limit_type == 'credit_limit':
            limit_id.partner_id.cust_credit_limit = limit_id.credit_amount
            available_credit_limit = limit_id.partner_id.customer_credit_limit
            credit_limit = limit_id.partner_id.cust_credit_limit
            new_credit_limit = limit_id.credit_amount
            if available_credit_limit == credit_limit:
                new_credit_limit = limit_id.credit_amount
            elif available_credit_limit < credit_limit:
                new_credit_limit = limit_id.credit_amount + available_credit_limit
            limit_id.partner_id.customer_credit_limit = new_credit_limit
        if limit_id.limit_type == 'max_invoice_overdue_days':
            limit_id.partner_id.customer_max_invoice_overdue = limit_id.new_max_invoice
