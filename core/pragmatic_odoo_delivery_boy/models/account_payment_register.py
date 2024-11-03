from odoo import fields, models, api, _

class AccountPaymentRegisterInherit(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super(AccountPaymentRegisterInherit, self).action_create_payments()
        if self._context.get('active_id'):
            sale_order_id = self.env['sale.order'].search([('invoice_ids', '=', self._context.get('active_id'))])
            if sale_order_id:
                picking_id = self.env['picking.order'].search([('sale_order', '=', sale_order_id.id)])
                picking_id.write({'invoice': self._context.get('active_id'), 'payment': 'paid', 'state': 'paid'})
        return res