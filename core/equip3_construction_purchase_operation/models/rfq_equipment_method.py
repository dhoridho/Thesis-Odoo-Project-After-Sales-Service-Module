# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

import odoo.addons.decimal_precision as dp
from odoo import api, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero
from itertools import groupby
from odoo.tools.misc import formatLang, get_lang
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import UserError


class ELPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @api.depends('equipment_line_ids','equipment_line_ids.total','equipment_line_ids.subtotal',\
        'equipment_line_ids.quantity','discount_amount_el',\
        'discount_method_el','discount_type' ,'equipment_line_ids.discount_amount',\
        'equipment_line_ids.discount_method')
    def _el_amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        res_config= self.env['res.config.settings'].sudo().search([],order="id desc", limit=1)
        cur_obj = self.env['res.currency']
        for order in self:
            applied_discount = line_discount = sums = order_discount =  el_amount_untaxed = el_amount_tax  = 0.0
            for line in order.equipment_line_ids:
                el_amount_untaxed += line.subtotal
                el_amount_tax += line.tax
                applied_discount += line.discount_amt
                if line.discount_method == 'fixed':
                    line_discount += line.discount_amount
                elif line.discount_method == 'percentage':
                    line_discount += line.subtotal * (line.discount_amount/ 100)
            if res_config:
                if res_config.tax_discount_policy == 'tax':
                    if order.discount_type == 'line':
                        order.el_discount_amt = 0.00
                        order.update({
                            'el_amount_untaxed': el_amount_untaxed,
                            'el_amount_tax': el_amount_tax,
                            'el_amount_total': el_amount_untaxed + el_amount_tax - line_discount,
                            'el_discount_amt_line' : line_discount,
                        })
                    elif order.discount_type == 'global':
                        order.el_discount_amt_line = 0.00
                        if order.discount_method_el == 'percentage':
                            order_discount = el_amount_untaxed * (order.discount_amount_el / 100) 
                            
                            order.update({
                                'el_amount_untaxed': el_amount_untaxed,
                                'el_amount_tax': el_amount_tax,
                                'el_amount_total': el_amount_untaxed + el_amount_tax - order_discount,
                                'el_discount_amt' : order_discount,
                            })
                        elif order.discount_method_el == 'fixed':
                            order_discount = order.discount_amount_el
                            order.update({
                                'el_amount_untaxed': el_amount_untaxed,
                                'el_amount_tax': el_amount_tax,
                                'el_amount_total': el_amount_untaxed + el_amount_tax - order_discount,
                                'el_discount_amt' : order_discount,
                            })
                        else:
                            order.update({
                                'el_amount_untaxed': el_amount_untaxed,
                                'el_amount_tax': el_amount_tax,
                                'el_amount_total': el_amount_untaxed + el_amount_tax ,
                            })
                    else:
                        order.update({
                            'el_amount_untaxed': el_amount_untaxed,
                            'el_amount_tax': el_amount_tax,
                            'el_amount_total': el_amount_untaxed + el_amount_tax ,
                            })
                elif res_config.tax_discount_policy == 'untax':
                    if order.discount_type == 'line':
                        order.el_discount_amt = 0.00
                        order.update({
                            'el_amount_untaxed': el_amount_untaxed,
                            'el_amount_tax': el_amount_tax,
                            'el_amount_total': el_amount_untaxed + el_amount_tax - applied_discount,
                            'el_discount_amt_line' : applied_discount,
                        })
                    elif order.discount_type == 'global':
                        order.el_discount_amt_line = 0.00
                        if order.discount_method_el == 'percentage':
                            order_discount = el_amount_untaxed * (order.discount_amount_el / 100)
                            if order.equipment_line_ids:
                                for line in order.equipment_line_ids:
                                    if line.taxes:
                                        final_discount = 0.0
                                        try:
                                            final_discount = ((order.discount_amount_el*line.subtotal)/100.0)
                                        except ZeroDivisionError:
                                            pass
                                        discount = line.subtotal - final_discount
                                        taxes = line.taxes.compute_all(discount, \
                                                            order.currency_id,1.0, product=line.product, \
                                                            partner=order.partner_id)
                                        sums += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                            order.update({
                                'el_amount_untaxed': el_amount_untaxed,
                                'el_amount_tax': sums,
                                'el_amount_total': el_amount_untaxed + sums - order_discount,
                                'el_discount_amt' : order_discount,  
                            })
                        elif order.discount_method_el == 'fixed':
                            order_discount = order.discount_amount_el
                            if order.equipment_line_ids:
                                for line in order.equipment_line_ids:
                                    if line.taxes:
                                        final_discount = 0.0
                                        try:
                                            final_discount = ((order.discount_amount_el*line.subtotal)/el_amount_untaxed)
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
                                'el_amount_untaxed': el_amount_untaxed,
                                'el_amount_tax': sums,
                                'el_amount_total': el_amount_untaxed + sums - order_discount,
                                'el_discount_amt' : order_discount,
                            })
                        else:
                            order.update({
                                'el_amount_untaxed': el_amount_untaxed,
                                'el_amount_tax': el_amount_tax,
                                'el_amount_total': el_amount_untaxed + el_amount_tax ,
                            })
                    else:
                        order.update({
                            'el_amount_untaxed': el_amount_untaxed,
                            'el_amount_tax': el_amount_tax,
                            'el_amount_total': el_amount_untaxed + el_amount_tax ,
                            })
                else:
                    order.update({
                            'el_amount_untaxed': el_amount_untaxed,
                            'el_amount_tax': el_amount_tax,
                            'el_amount_total': el_amount_untaxed + el_amount_tax ,
                            })         
            else:
                order.update({
                    'el_amount_untaxed': el_amount_untaxed,
                    'el_amount_tax': el_amount_tax,
                    'el_amount_total': el_amount_untaxed + el_amount_tax ,
                    }) 


class ELPurchaseOrderLine(models.Model):
    _inherit = 'rfq.equipment.line'

    @api.depends('quantity', 'unit_price', 'taxes','discount_method','discount_amount','discount_type')
    def _compute_el_amount(self):
        for line in self:
            vals = line.el_prepare_compute_all_values()
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
                                'el_discount_amt' : line.discount_amount,
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