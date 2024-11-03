from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_channel_id = fields.Many2one(comodel_name='sale.channel', string='Sales Channel')
    sale_outlet_id = fields.Many2one(comodel_name='sale.outlet', string='Sales Outlet')
    
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        res = super(SaleOrder, self).onchange_partner_id()
        if self.partner_id.sale_channel_ids:
            self.sale_channel_id = self.partner_id.sale_channel_ids[0].id
        return res

    def _prepare_invoice(self):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'sale_channel_id': self.sale_channel_id.id,
            'sale_outlet_id': self.sale_outlet_id.id,
        })
        return invoice_vals

    def _action_confirm(self):
        for order in self:
            if order.sale_channel_id:
                channel = order.sale_channel_id
                # Auto Post Invoice
                if channel.confirm_sale_auto_post_invoice:
                    order._create_invoices(grouped=False, final=True)
                    for invoice in order.invoice_ids:
                        if invoice.partner_id.l10n_id_kode_transaksi:
                            invoice.l10n_id_kode_transaksi = invoice.partner_id.l10n_id_kode_transaksi
                        invoice.action_post()
                # Without Create Picking
                if channel.confirm_sale_without_picking:
                    return super(SaleOrder, self.with_context(confirm_sale_without_picking=True))._action_confirm()
        return super(SaleOrder, self)._action_confirm()

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        if self._context.get('confirm_sale_without_picking'):
            return False
        return super(SaleOrderLine, self)._action_launch_stock_rule(previous_product_uom_qty)

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    sale_channel_id = fields.Many2one(comodel_name='sale.channel', string='Sales Channel')
    sale_outlet_id = fields.Many2one(comodel_name='sale.outlet', string='Sales Outlet')