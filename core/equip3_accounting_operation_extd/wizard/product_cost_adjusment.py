from odoo import fields, models, api, _ , tools

class ProductCostAdjustment(models.TransientModel):
    _name = 'product.cost.adjustment'
    _description = 'Product Cost Adjustment'
    
    adjustment_line_ids = fields.One2many('product.cost.adjustment.line', 'adjusment_id', string='Product Cost Adjustment Line')


    def action_confirm_adjustment(self):
        # Trigger the action_request_for_approval 
        active_invoice = self.env['account.move'].browse(self._context.get('active_ids'))
        po_reference = active_invoice.po_reference_ids[0].id
        ro_reference = active_invoice.ro_reference_ids[0].name
        for line in self.adjustment_line_ids:
        # Update the price_unit in the related account.move.line
            
            # line.move_id.write({
        #         'amount_total': line.cost_adjustment_amount,
        #     })
        #     line.move_id.action_post()

            # Find the corresponding invoice line
            move_line = active_invoice.invoice_line_ids.filtered(lambda x: x.product_id.id == line.product_id.id)
            if move_line and move_line.price_unit != line.price_unit:
                # Calculate the difference in price
                price_difference = line.price_unit - move_line.price_unit
                subtotal_difference = price_difference * move_line.quantity
                tax_difference = line.price_subtotal - move_line.price_subtotal
                
                # Update the corresponding journal items to ensure the journal entry is balanced
                for journal_item in active_invoice.line_ids:
                    if journal_item.product_id == line.product_id:
                        if journal_item.debit > 0:
                            journal_item.price_unit += price_difference
                            journal_item.debit = line.price_subtotal
                        if journal_item.credit > 0:
                            journal_item.price_unit += price_difference
                            journal_item.credit = line.price_subtotal

                stock_journal = line.product_id.product_tmpl_id.categ_id.property_stock_journal
                stock_valuation_lines = line.product_id.product_tmpl_id.categ_id.property_stock_valuation_account_id
                stock_input_lines = line.product_id.product_tmpl_id.categ_id.property_stock_account_input_categ_id

                # Create a new journal item to record the price difference
                adjusment_journal_vals = {
                    'journal_id': stock_journal.id,
                    'date': active_invoice.invoice_date,
                    'ref': ro_reference + ' - ' + line.product_id.name,
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

                

                # Recompute the totals for the move
                active_invoice._recompute_dynamic_lines(recompute_all_taxes=True)
                active_invoice._compute_amount()


        
        if active_invoice.is_invoice_approval_matrix:
            active_invoice.with_context(from_product_cost_adjustment=True).action_request_for_approval()
        else:
            active_invoice.with_context(from_product_cost_adjustment=True).action_confirm()
        # Close the wizard and return to the previous view
        return {'type': 'ir.actions.act_window_close'}
    




class ProductCostAdjustmentLine(models.TransientModel):
    _name = 'product.cost.adjustment.line'
    _description = 'Product Cost Adjustment Line'
    
    adjusment_id = fields.Many2one('product.cost.adjustment', string='Product Cost Adjustment')
    product_id = fields.Many2one('product.product', string='Product')
    currency_id = fields.Many2one('res.currency', string='Currency')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    price_subtotal = fields.Float(string='Subtotal')
    move_id = fields.Many2one('account.move', string='Account Move')
    # cost_adjusment_amount = fields.Monetary(string='Amount', currency_field='currency_id')


    @api.onchange('price_subtotal')
    def _onchange_price_subtotal(self):
        self.price_unit = self.price_subtotal / self.quantity if self.quantity else 0.0

    @api.onchange('price_unit')
    def _onchange_price_unit(self):
        self.price_subtotal = self.price_unit * self.quantity if self.quantity else 0.0


            


            