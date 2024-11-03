# -*- coding: utf-8 -*-

from odoo import fields, models, api


class PosOrder(models.Model):
    _inherit = "pos.order"
 
    is_emenu_order = fields.Boolean('E-Menu')
    emenu_order_id = fields.Many2one('pos.emenu.order', string="E-Menu Order")

    @api.model
    def _process_order(self, order, draft, existing_order):
        res = super(PosOrder,self)._process_order(order, draft, existing_order) 
        if res:
            order = self.env['pos.order'].search([('id','=', res)])
            if order and order.emenu_order_id:
                values = {
                    'pos_order_id': order.id,
                    'state': 'paid',
                }
                order.emenu_order_id.write(values)

        return res

    def _order_fields(self, ui_order):
        res = super(PosOrder,self)._order_fields(ui_order)
        res.update({
            'is_emenu_order': ui_order.get('is_emenu_order') or False,
            'emenu_order_id': ui_order.get('emenu_order_id') or False,
        })
        return res

    def _prepare_void_order_vals(self, order, vals):
        values = super(PosOrder,self)._prepare_void_order_vals(order=order, vals=vals)

        values['is_emenu_order'] = order.is_emenu_order
        values['emenu_order_id'] = order.emenu_order_id and order.emenu_order_id.id or False
        
        return values


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    emenu_order_line_id = fields.Many2one('pos.emenu.order.line', string='E-Menu Order Line')
