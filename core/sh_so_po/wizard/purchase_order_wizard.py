# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api
from datetime import datetime


class PurchaseOrderWizard(models.TransientModel):
    _name = 'purchase.order.wizard'
    _description = "Purchase Order Wizard"

    partner_id = fields.Many2one('res.partner', string='Vendor', required=True)
    order_line = fields.One2many(
        'purchase.order.line.wizard', 'wizard_id', string='Order Lines')
    date_planned = fields.Datetime(
        string='Scheduled Date', required=True, default=datetime.now())
    order_selection = fields.Selection(
        [('rfq', 'RFQ'), ('order', 'Purchase Order')], default='rfq', required=True)

    def sh_create_purchase_order(self):

        purchase_order_line_obj = self.env['purchase.order.line']
        purchase_order_obj = self.env['purchase.order']
        active_so_id = self.env.context.get("active_id")
        if self and self.partner_id and self.date_planned and active_so_id:
            vals = {'partner_id': self.partner_id.id,
                    'date_planned': self.date_planned,
                    'sh_sale_order_id': active_so_id,
                    }
            created_po = purchase_order_obj.create(vals)
        if created_po and self.order_line:
            for ol in self.order_line:
                if ol.product_id and ol.name and ol.product_id.uom_po_id:
                    purchase_order_line_obj.create({'product_id': ol.product_id.id,
                                                                  'name': ol.name,
                                                                  'product_uom': ol.product_id.uom_id.id,
                                                                  'order_id': created_po.id,
                                                                  'date_planned': self.date_planned,
                                                                  'product_qty': ol.product_qty,
                                                                  'price_unit': ol.price_unit
                                                                  })
            if self.order_selection == 'order':
                created_po.button_confirm()
            return {
                "type": "ir.actions.act_window",
                "res_model": "purchase.order",
                "views": [[False, "form"]],
                "res_id": created_po.id,
                "target": "self",
            }

    @api.model
    def default_get(self, fields):
        res = super(PurchaseOrderWizard, self).default_get(fields)
        active_so_id = self.env.context.get("active_id")
        sale_order_obj = self.env['sale.order']
        if active_so_id:
            sale_order_search = sale_order_obj.search(
                [('id', '=', active_so_id)], limit=1)
            if sale_order_search and sale_order_search.order_line:
                tick_order_line = []
                for rec in sale_order_search.order_line:
                    if rec.tick:
                        tick_order_line.append(rec.id)
                if len(tick_order_line) > 0:
                    result = []
                    for rec in sale_order_search.order_line.search([('id', 'in', tick_order_line)]):
                        result.append((0, 0, {'product_id': rec.product_id.id,
                                              'name': rec.name,
                                              'product_qty': rec.product_uom_qty,
                                              'price_unit': rec.product_id.standard_price,
                                              'product_uom': rec.product_uom.id,
                                              'price_subtotal': rec.price_unit * rec.product_uom_qty

                                              }))
                    res.update({'order_line': result})
                elif len(tick_order_line) == 0:
                    result = []
                    for rec in sale_order_search.order_line:
                        result.append((0, 0, {'product_id': rec.product_id.id,
                                              'name': rec.name,
                                              'product_qty': rec.product_uom_qty,
                                              'price_unit': rec.product_id.standard_price,
                                              'product_uom': rec.product_uom.id,
                                              'price_subtotal': rec.price_unit * rec.product_uom_qty

                                              }))
                    res.update({'order_line': result})
        return res
