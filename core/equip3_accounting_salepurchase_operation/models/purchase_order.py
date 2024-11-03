from odoo import tools, models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from itertools import groupby
from odoo.tools.float_utils import float_is_zero

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    # overbudget_po_state = fields.Selection([
    #     ('overbudget_po', 'Overbudget PO'),
    #     ('overbudget_approved', 'Overbudget Approved'),
    # ], 'Overbudget PO Status', readonly=True, copy=False, tracking=True)

    def _prepare_invoice(self):
        res = super(PurchaseOrder, self)._prepare_invoice()
        for rec in self:
            res['purchase_order_ids'] = [(4, rec.id)]
        
        context = dict(self.env.context) or {}
        if context.get('down_payment'):
            amount = 0
            is_down_payment = False
            if context.get('down_payment_by') == "percentage":
                amount = round((self.amount_untaxed * context.get('amount')) / 100, 2)
                is_down_payment = True
            elif context.get('down_payment_by') == "fixed":
                amount = context.get('amount')
                is_down_payment = True
            if is_down_payment:
                down_payment_line = self.order_line.filtered(lambda x: x.is_down_payment)
                
                if down_payment_line:
                    down_payment_line.update({'price_unit': amount})
        return res
    
    def _action_create_bill(self, price_difference, subtotal_difference, tax_difference, line_ids, dp=False):
        """Create the invoice associated to the PO and handle payment difference."""
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

        # 1 Prepare invoice vals and clean-up the section lines
        invoice_vals_list = []
        for order in self:
            # if order.invoice_status != 'to invoice':
            #     continue

            order = order.with_company(order.company_id)
            pending_section = None
            # Invoice values.
            invoice_vals = order._prepare_invoice()
            # Invoice line values (keep only necessary sections).
            for line in order.order_line:
                if line.display_type == 'line_section':
                    pending_section = line
                    continue
                if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
                    if pending_section:
                        invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
                        pending_section = None
                    invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
            invoice_vals_list.append(invoice_vals)

        if not invoice_vals_list:
            raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

        # 2 group by (company_id, partner_id, currency_id) for batch creation
        new_invoice_vals_list = []
        for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
            origins = set()
            payment_refs = set()
            refs = set()
            ref_invoice_vals = None
            for invoice_vals in invoices:
                if not ref_invoice_vals:
                    ref_invoice_vals = invoice_vals
                else:
                    ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
                origins.add(invoice_vals['invoice_origin'])
                payment_refs.add(invoice_vals['payment_reference'])
                refs.add(invoice_vals['ref'])
            ref_invoice_vals.update({
                'ref': ', '.join(refs)[:2000],
                'invoice_origin': ', '.join(origins),
                'invoice_line_ids': line_ids,
                'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
            })
            new_invoice_vals_list.append(ref_invoice_vals)
        invoice_vals_list = new_invoice_vals_list

        # 4 Create invoices.
        moves = self.env['account.move']
        AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
        for vals in invoice_vals_list:
            move = AccountMove.with_company(vals['company_id']).create(vals)
            tax_lines = move.line_ids.filtered(lambda x: x.tax_line_id)
            payable_lines = move.line_ids.filtered(lambda x: x.account_id.user_type_id.type == 'payable')
            if tax_lines.debit == 0:
                tax_lines.debit = tax_lines.credit
                tax_lines.credit = 0
                payable_lines.credit = payable_lines.credit + tax_lines.debit

            # if dp < 0:
            #     move.down_payment_amount = dp
            # move.amount_untaxed = price_difference  # Set amount_total to price_difference
            # move.amount_untaxed_signed = price_difference  # Set amount_total to price_difference
            # move.amount_tax = tax_difference  # Set amount_tax to tax_difference
            # move.amount_tax_signed = tax_difference  # Set amount_tax to tax_difference
            # move.amount_total = subtotal_difference  # Set amount_total to 
            # move.amount_total_signed = subtotal_difference  # Set amount_total to
            moves |= move

        return moves

    def get_default_tax_account(self, tax):
        # Retrieve the tax account from the tax repartition lines
        for line in tax.invoice_repartition_line_ids:
            if line.account_id:
                return line.account_id.id
        return False
    
    def wizard_close_purchase_order(self):
        if self.company_id.anglo_saxon_accounting:
            lines_to_confirm = []
            for line in self.order_line:
                if line.product_id.product_tmpl_id.valuation == 'real_time' : 
                    lines_to_confirm.append(line)
            if lines_to_confirm:
                adjustment_lines = []
                for line in lines_to_confirm:
                    adjustment_lines.append((0, 0, {
                        'po_id': self.id,
                        'product_id': line.product_id.id,
                        'currency_id': self.currency_id.id,
                        'quantity': line.product_qty,
                        'price_unit': line.price_unit,
                        'tax_ids': [(6, 0, line.taxes_id.ids)],
                        'price_subtotal': line.price_subtotal,
                    }))
                adjustment = self.env['po.product.cost.adjustment'].create({
                'adjustment_line_ids': adjustment_lines,
                })

                return {
                    'name': _('Product Cost Adjustment Confirmation'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'po.product.cost.adjustment',
                    'view_mode': 'form',
                    'res_id': adjustment.id,
                    'target': 'new',
                    'view_id': self.env.ref('equip3_accounting_salepurchase_operation.view_po_product_cost_adjustment_form').id,
                    'context': {'from_product_cost_adjustment': True},
                }
            else:
                return super(PurchaseOrder, self).wizard_close_purchase_order()
        else:
            return super(PurchaseOrder, self).wizard_close_purchase_order()

