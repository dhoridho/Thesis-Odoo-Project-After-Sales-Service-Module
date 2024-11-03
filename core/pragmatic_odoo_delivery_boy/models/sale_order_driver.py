from datetime import datetime, date
from odoo import fields, models, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"
    
    payment_status_driver = fields.Char()

    def action_delivered_sale_order(self):
        self.write({
            'delivery_state': 'delivered'
        })

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        # Delete previous cache
        # self.delete_previous_cache()
        if res != None:
            if res.warehouse_id:
                res.write({
                    'latitude': res.warehouse_id.partner_id.partner_latitude,
                    'longitude': res.warehouse_id.partner_id.partner_longitude,
                })
            return res
        else:
            return False

    # @api.model
    def write(self, vals):
        if 'state' in vals:
            if vals.get('state'):
                order_stage_id = self.env['order.stage'].search(
                    [('action_type', '=', vals.get('state'))])
                if order_stage_id:
                    vals['stage_id'] = order_stage_id.id
        # if 'reference' in vals:
        #     payment_transaction_obj = self.env['payment.transaction'].search([('id', '=', self.transaction_ids.ids)])
        #     if payment_transaction_obj.acquirer_id.journal_id.type != 'cash':
        #         # vals['state'] = 'sale'
        #         self.action_confirm()
        #         line_ids = {}
        #
        #
        #         # inv = self.env['account.move'].with_context(default_type='in_invoice').create({
        #         #     'partner_id': self.partner_id.id,
        #         #     'invoice_line_ids': self.order_line
        #         # })
        #         items_data = []
        #         items_arry = []
        #         for line_id in self.order_line:
        #             items_data = [0, 0,{
        #                 'name': self.partner_id.name,
        #                 'product_id': line_id.product_id.id,
        #                 'product_uom_id': line_id.product_id.uom_id.id,
        #                 'quantity': line_id.product_uom_qty,
        #                 'price_unit': line_id.price_unit,
        #                 'price_subtotal': line_id.price_subtotal,
        #                 'analytic_account_id': self.analytic_account_id.id,
        #                           }]
        #             if items_data:
        #                 items_arry.append(items_data)
        #         inv = self.env['account.move'].with_context(default_type='in_invoice').create({
        #             'partner_id': self.partner_id.id,
        #             'invoice_line_ids': items_arry,
        #             'type': 'out_invoice'
        #             # 'state': 'posted'
        #         })
        #         inv.post()
        #
        #         vals['invoice_ids'] = (0, 0, inv)
        #         vals['invoice_count'] = len(inv)
        #         # payment_method = self.env['account.payment.method'].sudo().search([])
        #         picking_order = self.env['picking.order'].sudo().search([('sale_order', '=', self.id)])
        #         #
        #         # account_journal = self.env['account.journal'].sudo().search([('name', '=', 'Bank')])
        #         # # invoice_obj = self.env['account.move']
        #         # # invoice_line_obj = self.env['account.move.line']
        #         # # invoice = {'partner_id': self.partner_id.id, 'invoice_date': datetime.now().date()}
        #         # # invoice_id = invoice_obj.create(invoice)
        #         # # vals['invoice_ids'] = invoice_id
        #         #
        #         # # invoice_lines = {'product_id': treatment_id, 'name': product_name, 'invoice_id': int(invoice_id), 'price_unit': product_template_id.list_price,
        #         # #                  'account_id': product_account_id}
        #         #
        #         # # self._prepare_invoice()
        #         # invoice_obj = self._create_invoices()
        #         # invoice_obj.action_post()
        #         # picking_order.invoice = invoice_obj.id
        #         # payment = self.env['account.payment'].sudo().create({
        #         #     'payment_type': 'inbound',
        #         #     'partner_type': 'customer',
        #         #     'partner_id': invoice_obj.partner_id.id,
        #         #     'communication': invoice_obj.name,
        #         #     'amount': invoice_obj.amount_total,
        #         #     'payment_method_id': payment_method[0].id,
        #         #     'journal_id': account_journal.id,
        #         #     'invoice_ids': [(4, invoice_obj.id)]
        #         # })
        #         # # self.write({'delivery_state': 'paid'})
        #         #
        #         if inv:
        #             picking_order.write({'payment': 'paid'})
        #             picking_order.action_picking_order_paid()
        #             picking_order.invoice = inv.id
        #         #     payment.post()
        return super(SaleOrder, self).write(vals)
