from odoo import fields, models, api, _ , tools
from odoo.exceptions import UserError

class PurchaseOrderProductCostAdjustment(models.TransientModel):
    _name = 'po.product.cost.adjustment'
    _description = 'Product Cost Adjustment'
    
    adjustment_line_ids = fields.One2many('po.product.cost.adjustment.line', 'adjusment_id', string='Product Cost Adjustment Line')

    def action_confirm_adjustment(self):
        active_purchase_order = self.env['purchase.order'].browse(self._context.get('active_id'))
        vendor_bills =  self.env['account.move'].search([('purchase_order_id', '=', active_purchase_order.id), ('move_type', '=', 'in_invoice')])
        po_amount = active_purchase_order.amount_total
        bills_amount = sum(vendor_bills.mapped('amount_total'))
        bills_difference = po_amount - bills_amount
        dp = 0
        line_ids = []
        for line in self.adjustment_line_ids:
            po_line = active_purchase_order.order_line.filtered(lambda x: x.product_id.id == line.product_id.id)
            if po_line and po_line.price_unit != line.price_unit:
                price_difference = line.price_unit - po_line.price_unit
                subtotal_difference = price_difference * po_line.product_qty
                tax_difference = line.price_subtotal - po_line.price_subtotal
                
                if bills_difference == 0:
                    debit = {
                        # 'product_id': line.product_id.id,
                        'name': 'Product Cost Adjustment',
                        'account_id': po_line.product_id.categ_id.property_stock_account_input_categ_id.id,
                        'quantity': po_line.product_qty,
                        'price_unit': price_difference,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'debit': price_difference,
                        'price_tax': tax_difference,
                        'price_subtotal': subtotal_difference,
                        'purchase_line_id': po_line.id,
                    }


                else:
                    debit = {
                        'product_id': line.product_id.id,
                        'name': line.product_id.name,
                        'account_id': po_line.product_id.categ_id.property_stock_account_input_categ_id.id,
                        'quantity': po_line.product_qty,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.tax_ids.ids)],
                        'debit': line.price_subtotal,
                        'purchase_line_id': po_line.id,
                    }

                line_ids.append((0, 0, debit))

        if line_ids:
            for po_line in active_purchase_order.order_line:
                if po_line.product_id.id == line.product_id.id:
                    po_line.price_unit = line.price_unit

            if bills_difference == 0:

                # bills = vendor_bills.filtered(lambda x: x.amount_total == active_purchase_order.amount_total)
                # product_lines = bills.line_ids.filtered(lambda x: x.product_id.id == active_purchase_order.partner_id.id)
                # tax_lines = bills.mapped('line_ids').filtered(lambda x: x.tax_line_id)
                # payable_lines = bills.mapped('line_ids').filtered(lambda x: x.account_id.user_type_id.type == 'payable')
                active_purchase_order._action_create_bill(price_difference, subtotal_difference, tax_difference, line_ids, dp)
                
            # Keep this code for future use
            # else:
            #     down_payment = vendor_bills.mapped('line_ids').filtered(lambda x: x.is_down_payment == True)
            #     dp = sum(down_payment.mapped('price_unit')) * -1
            #     down_payment_lines = {
            #         'product_id': down_payment.product_id.id,
            #         'name': down_payment.name,
            #         'account_id': down_payment.account_id.id,
            #         'quantity': down_payment.quantity,
            #         'price_unit': down_payment.price_unit * -1,
            #         'tax_ids': [(6, 0, down_payment.tax_ids.ids)],
            #         'debit': down_payment.credit,
            #         'credit': down_payment.debit,
            #         'purchase_line_id': down_payment.purchase_line_id.id,
            #     }
            #     line_ids.append((0, 0, down_payment_lines))
            #     active_purchase_order._action_create_bill(price_difference, subtotal_difference, tax_difference, line_ids, dp)
                

            stock_journal = line.product_id.product_tmpl_id.categ_id.property_stock_journal
            stock_valuation_lines = line.product_id.product_tmpl_id.categ_id.property_stock_valuation_account_id
            stock_input_lines = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id

            # pickings = self.env['stock.picking'].search([('purchase_id', '=', active_purchase_order.id)])
            pickings = active_purchase_order.picking_ids.filtered(lambda x: x.state == 'done')
            for picking in pickings:
                for stock in picking.move_ids_without_package:
                    if stock.product_id.id == line.product_id.id:
                        ref = picking.name + ' - ' + line.product_id.name
                        # qty_done = sum(picking.move_ids_without_package.mapped('quantity_done'))
                        subtotal_difference = price_difference * stock.quantity_done

                        adjusment_journal_vals = {
                                'journal_id': stock_journal.id,
                                'date': active_purchase_order.date_order,
                                'ref': ref,
                                'line_ids': [(0, 0, {
                                    'account_id': stock_valuation_lines.id,
                                    'name': line.product_id.name,
                                    'debit': subtotal_difference if subtotal_difference > 0 else 0.0,
                                    'credit': -subtotal_difference if subtotal_difference < 0 else 0.0,
                                }), (0, 0, {
                                    'account_id': stock_input_lines.id,
                                    'name': line.product_id.name,
                                    'debit': -subtotal_difference if subtotal_difference < 0 else 0.0,
                                    'credit': subtotal_difference if subtotal_difference > 0 else 0.0,
                                })],
                            }
                        self.env['account.move'].create(adjusment_journal_vals)

        active_purchase_order.close_purchase_order()

        order_lines = active_purchase_order.order_line
        picking_moves = active_purchase_order.picking_ids.move_ids_without_package.filtered(lambda o: o.state == 'done')
        svl_description = _('Purchase Revaluation')

        for line in self.adjustment_line_ids:
            product = line.product_id

            # should be filtered by purchase line, not product
            po_lines = active_purchase_order.order_line.filtered(lambda o: o.product_id == product)

            line_moves = picking_moves.filtered(lambda o: o.purchase_line_id in po_lines)
            svls_to_adjust = line_moves.stock_valuation_layer_ids
            svls_to_adjust._adjust_history(line.price_unit, svl_description, domain=[('stock_move_source_id', 'in', line_moves.ids)])

        return {'type': 'ir.actions.act_window_close'}
                        
    def get_default_tax_account(self, tax_ids):
        # Retrieve the tax account from the tax repartition lines
        for tax in tax_ids:
            for line in tax.invoice_repartition_line_ids:
                if line.account_id:
                    return line.account_id.id
        return False
    
class PurchaseOrderProductCostAdjustmentLine(models.TransientModel):
    _name = 'po.product.cost.adjustment.line'
    _description = 'Product Cost Adjustment Line'
    
    adjusment_id = fields.Many2one('po.product.cost.adjustment', string='Product Cost Adjustment')
    product_id = fields.Many2one('product.product', string='Product')
    currency_id = fields.Many2one('res.currency', string='Currency')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Float(string='Subtotal')
    po_id = fields.Many2one('purchase.order', string='Purchase Order')


    @api.onchange('price_subtotal')
    def _onchange_price_subtotal(self):
        self.price_unit = self.price_subtotal / self.quantity if self.quantity else 0.0

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        self.price_subtotal = self.price_unit * self.quantity if self.quantity else 0.0


            


            