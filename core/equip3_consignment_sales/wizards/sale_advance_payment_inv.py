from odoo import _, api, fields, models



class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def create_invoices(self):
        res = super(SaleAdvancePaymentInv, self).create_invoices()
        context = self._context or {}
        sale_id = self.env['sale.order'].browse(context.get('active_id'))
        if sale_id and sale_id.sale_consignment_id:
            account_move = self.env['account.move'].browse(res.get('res_id'))
            account_move.write({'sale_consignment_id': sale_id.sale_consignment_id.id})
        return res