# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero
from itertools import groupby
from odoo.tools.misc import formatLang, get_lang
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class MLPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('material_line_ids','material_line_ids.total','material_line_ids.subtotal',\
        'material_line_ids.quantity','discount_amount_ml',\
        'discount_method_ml','discount_type' ,'material_line_ids.discount_amount',\
        'material_line_ids.discount_method')
    def _ml_amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        res_config= self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
        cur_obj = self.env['res.currency']
        for order in self:
            applied_discount = line_discount = sums = order_discount =  ml_amount_untaxed = ml_amount_tax  = 0.0
            for line in order.material_line_ids:
                ml_amount_untaxed += line.subtotal
                ml_amount_tax += line.tax
                applied_discount += line.discount_amt
                if line.discount_method == 'fixed':
                    line_discount += line.discount_amount
                elif line.discount_method == 'percentage':
                    line_discount += line.subtotal * (line.discount_amount/ 100)
            if res_config:
                if res_config.tax_discount_policy == 'tax':
                    if order.discount_type == 'line':
                        order.ml_discount_amt = 0.00
                        order.update({
                            'ml_amount_untaxed': ml_amount_untaxed,
                            'ml_amount_tax': ml_amount_tax,
                            'ml_amount_total': ml_amount_untaxed + ml_amount_tax - line_discount,
                            'ml_discount_amt_line' : line_discount,
                        })
                    elif order.discount_type == 'global':
                        order.ml_discount_amt_line = 0.00
                        if order.discount_method_ml == 'percentage':
                            order_discount = ml_amount_untaxed * (order.discount_amount_ml / 100) 
                            
                            order.update({
                                'ml_amount_untaxed': ml_amount_untaxed,
                                'ml_amount_tax': ml_amount_tax,
                                'ml_amount_total': ml_amount_untaxed + ml_amount_tax - order_discount,
                                'ml_discount_amt' : order_discount,
                            })
                        elif order.discount_method_ml == 'fixed':
                            order_discount = order.discount_amount_ml
                            order.update({
                                'ml_amount_untaxed': ml_amount_untaxed,
                                'ml_amount_tax': ml_amount_tax,
                                'ml_amount_total': ml_amount_untaxed + ml_amount_tax - order_discount,
                                'ml_discount_amt' : order_discount,
                            })
                        else:
                            order.update({
                                'ml_amount_untaxed': ml_amount_untaxed,
                                'ml_amount_tax': ml_amount_tax,
                                'ml_amount_total': ml_amount_untaxed + ml_amount_tax ,
                            })
                    else:
                        order.update({
                            'ml_amount_untaxed': ml_amount_untaxed,
                            'ml_amount_tax': ml_amount_tax,
                            'ml_amount_total': ml_amount_untaxed + ml_amount_tax ,
                            })
                elif res_config.tax_discount_policy == 'untax':
                    if order.discount_type == 'line':
                        order.ml_discount_amt = 0.00
                        order.update({
                            'ml_amount_untaxed': ml_amount_untaxed,
                            'ml_amount_tax': ml_amount_tax,
                            'ml_amount_total': ml_amount_untaxed + ml_amount_tax - applied_discount,
                            'ml_discount_amt_line' : applied_discount,
                        })
                    elif order.discount_type == 'global':
                        order.ml_discount_amt_line = 0.00
                        if order.discount_method_ml == 'percentage':
                            order_discount = ml_amount_untaxed * (order.discount_amount_ml / 100)
                            if order.material_line_ids:
                                for line in order.material_line_ids:
                                    if line.taxes:
                                        final_discount = 0.0
                                        try:
                                            final_discount = ((order.discount_amount_ml*line.subtotal)/100.0)
                                        except ZeroDivisionError:
                                            pass
                                        discount = line.subtotal - final_discount
                                        taxes = line.taxes.compute_all(discount, \
                                                            order.currency_id,1.0, product=line.product, \
                                                            partner=order.partner_id)
                                        sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                            order.update({
                                'ml_amount_untaxed': ml_amount_untaxed,
                                'ml_amount_tax': sums,
                                'ml_amount_total': ml_amount_untaxed + sums - order_discount,
                                'ml_discount_amt' : order_discount,  
                            })
                        elif order.discount_method_ml == 'fixed':
                            order_discount = order.discount_amount_ml
                            if order.material_line_ids:
                                for line in order.material_line_ids:
                                    if line.taxes:
                                        final_discount = 0.0
                                        try:
                                            final_discount = ((order.discount_amount_ml*line.subtotal)/ml_amount_untaxed)
                                        except ZeroDivisionError:
                                            pass
                                        discount = line.subtotal - final_discount
                                        taxes = line.taxes._origin.compute_all(discount, \
                                                            order.currency_id,1.0, product=line.product, \
                                                            partner=order.partner_id,)
                                        # taxes = line.taxes.compute_all(discount, \
                                        #                     order.currency_id,1.0, product=line.product, \
                                        #                     partner=order.partner_id)
                                        sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                            order.update({
                                'ml_amount_untaxed': ml_amount_untaxed,
                                'ml_amount_tax': sums,
                                'ml_amount_total': ml_amount_untaxed + sums - order_discount,
                                'ml_discount_amt' : order_discount,
                            })
                        else:
                            order.update({
                                'ml_amount_untaxed': ml_amount_untaxed,
                                'ml_amount_tax': ml_amount_tax,
                                'ml_amount_total': ml_amount_untaxed + ml_amount_tax ,
                            })
                    else:
                        order.update({
                            'ml_amount_untaxed': ml_amount_untaxed,
                            'ml_amount_tax': ml_amount_tax,
                            'ml_amount_total': ml_amount_untaxed + ml_amount_tax ,
                            })
                else:
                    order.update({
                            'ml_amount_untaxed': ml_amount_untaxed,
                            'ml_amount_tax': ml_amount_tax,
                            'ml_amount_total': ml_amount_untaxed + ml_amount_tax ,
                            })         
            else:
                order.update({
                    'ml_amount_untaxed': ml_amount_untaxed,
                    'ml_amount_tax': ml_amount_tax,
                    'ml_amount_total': ml_amount_untaxed + ml_amount_tax ,
                    }) 

    # def prepare_invoice(self):
    #     """Prepare the dict of values to create the new invoice for a purchase order.
    #     """
    #     self.ensure_one()
    #     move_type = self._context.get('default_move_type', 'in_invoice')
    #     journal = self.env['account.move'].with_context(default_move_type=move_type)._get_default_journal()
    #     if not journal:
    #         raise UserError(_('Please define an accounting purchase journal for the company %s (%s).') % (self.company_id.name, self.company_id.id))

    #     partner_invoice_id = self.partner_id.address_get(['invoice'])['invoice']
    #     invoice_vals = {
    #         'ref': self.partner_ref or '',
    #         'move_type': move_type,
    #         'narration': self.notes,
    #         'currency_id': self.currency_id.id,
    #         'invoice_user_id': self.user_id and self.user_id.id,
    #         'partner_id': partner_invoice_id,
    #         'fiscal_position_id': (self.fiscal_position_id or self.fiscal_position_id.get_fiscal_position(partner_invoice_id)).id,
    #         'payment_reference': self.partner_ref or '',
    #         'partner_bank_id': self.partner_id.bank_ids[:1].id,
    #         'invoice_origin': self.name,
    #         'invoice_payment_term_id': self.payment_term_id.id,
    #         'invoice_line_ids': [],
    #         'company_id': self.company_id.id,
    #         'discount_method_ml': self.discount_method_ml,
    #         'discount_type' : self.discount_type,
    #         'discount_amount_ml':self.discount_amount_ml,
    #         'ml_discount_amt': self.ml_discount_amt,
    #         'ml_discount_amt_line': self.ml_discount_amt_line,
    #     }
    #     return invoice_vals            

    
    # def action_create_invoice(self):
    #     """Create the invoice associated to the PO.
    #     """
    #     precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')

    #     # 1) Prepare invoice vals and clean-up the section lines
    #     invoice_vals_list = []
    #     for order in self:
    #         if order.invoice_status != 'to invoice':
    #             continue

    #         order = order.with_company(order.company_id)
    #         pending_section = None
    #         # Invoice values.
    #         invoice_vals = order.prepare_invoice()
    #         # Invoice line values (keep only necessary sections).
    #         for line in order.order_line:
    #             if line.display_type == 'line_section':
    #                 pending_section = line
    #                 continue
    #             if not float_is_zero(line.qty_to_invoice, precision_digits=precision):
    #                 if pending_section:
    #                     invoice_vals['invoice_line_ids'].append((0, 0, pending_section._prepare_account_move_line()))
    #                     pending_section = None
    #                 invoice_vals['invoice_line_ids'].append((0, 0, line._prepare_account_move_line()))
    #         invoice_vals_list.append(invoice_vals)

    #     if not invoice_vals_list:
    #         raise UserError(_('There is no invoiceable line. If a product has a control policy based on received quantity, please make sure that a quantity has been received.'))

    #     # 2) group by (company_id, partner_id, currency_id) for batch creation
    #     new_invoice_vals_list = []
    #     for grouping_keys, invoices in groupby(invoice_vals_list, key=lambda x: (x.get('company_id'), x.get('partner_id'), x.get('currency_id'))):
    #         origins = set()
    #         payment_refs = set()
    #         refs = set()
    #         ref_invoice_vals = None
    #         for invoice_vals in invoices:
    #             if not ref_invoice_vals:
    #                 ref_invoice_vals = invoice_vals
    #             else:
    #                 ref_invoice_vals['invoice_line_ids'] += invoice_vals['invoice_line_ids']
    #             origins.add(invoice_vals['invoice_origin'])
    #             payment_refs.add(invoice_vals['payment_reference'])
    #             refs.add(invoice_vals['ref'])
    #         ref_invoice_vals.update({
    #             'ref': ', '.join(refs)[:2000],
    #             'invoice_origin': ', '.join(origins),
    #             'payment_reference': len(payment_refs) == 1 and payment_refs.pop() or False,
    #         })
    #         new_invoice_vals_list.append(ref_invoice_vals)
    #     invoice_vals_list = new_invoice_vals_list

    #     # 3) Create invoices.
    #     moves = self.env['account.move']
    #     AccountMove = self.env['account.move'].with_context(default_move_type='in_invoice')
    #     for vals in invoice_vals_list:
    #         moves |= AccountMove.with_company(vals['company_id']).create(vals)

    #     # 4) Some moves might actually be refunds: convert them if the total amount is negative
    #     # We do this after the moves have been created since we need taxes, etc. to know if the total
    #     # is actually negative or not
    #     moves.filtered(lambda m: m.currency_id.round(m.ml_amount_total) < 0).action_switch_invoice_into_refund_credit_note()
    #     for line in moves.line_ids:
    #         name = line.name
    #     if moves.discount_type == 'line':
    #         price = moves.ml_discount_amt_line
    #     elif moves.discount_type == 'global':
    #         price = moves.ml_discount_amt
    #     else:
    #         price = 0
    #     if moves.line_ids:
    #         if name != 'Discount':
    #             if moves.discount_account_id:       
    #                 discount_vals = {
    #                         'account_id': moves.discount_account_id, 
    #                         'quantity': 1,
    #                         'unit_price': -price,
    #                         'name': "Discount", 
    #                         'exclude_from_invoice_tab': True,
    #                         }          
    #                 moves.with_context(check_move_validity=False).write({
    #                         'invoice_line_ids' : [(0,0,discount_vals)]
    #                     })
    #     return self.action_view_invoice(moves)                 

    # def action_view_invoice(self, invoices=False):
    #     """This function returns an action that display existing vendor bills of
    #     given purchase order ids. When only one found, show the vendor bill
    #     immediately.
    #     """
    #     if not invoices:
    #         # Invoice_ids may be filtered depending on the user. To ensure we get all
    #         # invoices related to the purchase order, we read them in sudo to fill the
    #         # cache.
    #         self.sudo()._read(['invoice_ids'])
    #         invoices = self.invoice_ids

    #     action = self.env.ref('account.action_move_in_invoice_type').sudo()
    #     result = action.read()[0]
    #     invoices.write({
    #         'discount_method_ml' : self.discount_method_ml , 
    #         'ml_discount_amt' : self.ml_discount_amt,
    #         'discount_amount_ml' : self.discount_amount_ml ,
    #         'discount_type' : self.discount_type,
    #         'ml_discount_amt_line' : self.ml_discount_amt_line,
    #         'ml_amount_untaxed' : self.ml_amount_untaxed,
    #         'ml_amount_total': self.ml_amount_total,

    #     })
        
    #     # choose the view_mode accordingly
    #     if len(invoices) > 1:
    #         result['domain'] = [('id', 'in', invoices.ids)]
    #     elif len(invoices) == 1:
    #         res = self.env.ref('account.view_move_form', False)
    #         form_view = [(res and res.id or False, 'form')]
    #         if 'views' in result:
    #             result['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
    #         else:
    #             result['views'] = form_view
    #         result['res_id'] = invoices.id
    #     else:
    #         result = {'type': 'ir.actions.act_window_close'}
    #     return result


    # def copy(self, default=None):
    #     ctx = dict(self.env.context)
    #     ctx.pop('default_product_id', None)
    #     self = self.with_context(ctx)
    #     new_po = super(MLPurchaseOrder, self).copy(default=default)
    #     for line in new_po.material_line_ids:
    #         if line.product:
    #             seller = line.product._select_seller(
    #                 partner_id=line.partner_id, quantity=line.quantity,
    #                 date=line.material_id.date_order and line.material_id.date_order.date(), uom_id=line.uom)
    #             line.date_planned = line._get_date_planned(seller)
    #     return new_po

class MLPurchaseOrderLine(models.Model):
    _inherit = 'rfq.material.line'

    @api.depends('quantity', 'unit_price', 'taxes','discount_method','discount_amount','discount_type')
    def _compute_ml_amount(self):
        for line in self:
            vals = line.ml_prepare_compute_all_values()
            res_config= self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
            if res_config:
                if res_config.tax_discount_policy == 'untax':
                    if line.discount_type == 'line':
                        if line.discount_method == 'fixed':
                            price = (vals['unit_price'] * vals['quantity']) - line.discount_amount
                            taxes = line.taxes.compute_all(price,vals['currency_id'],1,vals['product'],vals['partner'])
                            line.update({
                                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                                'total': taxes['total_included'] + line.discount_amount,
                                'subtotal': taxes['total_excluded'] + line.discount_amount,
                                'ml_discount_amt' : line.discount_amount,
                            })

                        elif line.discount_method == 'percentage':
                            price = (vals['unit_price'] * vals['quantity']) * (1 - (line.discount_amount or 0.0) / 100.0)
                            price_x = ((vals['unit_price'] * vals['quantity'])-((vals['unit_price'] * vals['quantity']) * (1 - (line.discount_amount or 0.0) / 100.0)))
                            taxes = line.taxes.compute_all(price,vals['currency_id'],1,vals['product'],vals['partner'])
                            line.update({
                                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                                'total': taxes['total_included'] + price_x,
                                'subtotal': taxes['total_excluded'] + price_x,
                                'discount_amt' : price_x,
                            })
                        else:
                            taxes = line.taxes.compute_all(vals['unit_price'],vals['currency_id'],vals['quantity'],vals['product'],vals['partner'])
                            line.update({
                                'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                                'total': taxes['total_included'],
                                'subtotal': taxes['total_excluded'],
                            })
                    else:
                        taxes = line.taxes.compute_all(vals['unit_price'],vals['currency_id'],vals['quantity'],vals['product'],vals['partner'])
                        line.update({
                            'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'total': taxes['total_included'],
                            'subtotal': taxes['total_excluded'],
                        })
                elif res_config.tax_discount_policy == 'tax':
                    price_x = 0.0
                    if line.discount_type == 'line':
                        taxes = line.taxes.compute_all(vals['unit_price'],vals['currency_id'],vals['quantity'],vals['product'],vals['partner'])
                        if line.discount_method == 'fixed':
                            price_x = (taxes['total_included']) - (taxes['total_included'] - line.discount_amount)
                        elif line.discount_method == 'percentage':
                            price_x = (taxes['total_included']) - (taxes['total_included'] * (1 - (line.discount_amount or 0.0) / 100.0))                        

                        line.update({
                            'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'total': taxes['total_included'],
                            'subtotal': taxes['total_excluded'],
                            'discount_amt' : price_x,
                        })
                    else:
                        taxes = line.taxes.compute_all(vals['unit_price'],vals['currency_id'],vals['quantity'],vals['product'],vals['partner'])
                        line.update({
                            'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                            'total': taxes['total_included'],
                            'subtotal': taxes['total_excluded'],
                        })
                else:
                    taxes = line.taxes.compute_all(vals['unit_price'],vals['currency_id'],vals['quantity'],vals['product'],vals['partner'])
                    line.update({
                        'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                        'total': taxes['total_included'],
                        'subtotal': taxes['total_excluded'],
                    })
            else:
                taxes = line.taxes.compute_all(vals['unit_price'],vals['currency_id'],vals['quantity'],vals['product'],vals['partner'])
                line.update({
                    'tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                    'total': taxes['total_included'],
                    'subtotal': taxes['total_excluded'],
                })

    # def _prepare_account_move_line(self, move=False):
    #     res =super(MLPurchaseOrderLine,self)._prepare_account_move_line(move)
    #     res.update({'discount_method':self.discount_method,'discount_amount':self.discount_amount,'quantity':self.quantity})
    #     return res
