# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools, _


class PosOrder(models.Model):
    _inherit = "pos.order"
 
    is_online_outlet = fields.Boolean('Online Outlet')
    oloutlet_order_id = fields.Many2one('pos.online.outlet.order', 'Online Order')
    oloutlet_order_from = fields.Char(string='Online Order From', compute='_compute_oloutlet_order_from', store=True)
    oloutlet_order_type = fields.Char(string='Online Order Type', compute='_compute_oloutlet_order_type', store=True)
    oloutlet_order_info = fields.Char(string='Online Order Info', compute='_compute_oloutlet_order_info', store=True)

    @api.model
    def _process_order(self, order, draft, existing_order):
        data = order.get('data')
        res = super(PosOrder,self)._process_order(order, draft, existing_order) 
        if res:
            order = self.env['pos.order'].search([('id','=', res)])
            if order and order.oloutlet_order_id and order.state in ['paid']:
                values = {
                    'state': 'paid',
                    'has_pos_order': True,
                }
                order.oloutlet_order_id.write(values)

        return res

    @api.model
    def _order_fields(self, ui_order):
        res = super(PosOrder,self)._order_fields(ui_order)
        res.update({
            'is_online_outlet': ui_order.get('is_online_outlet') or False,
            'oloutlet_order_id': ui_order.get('oloutlet_order_id') or False,
        })
        return res

    @api.depends('oloutlet_order_id')
    def _compute_oloutlet_order_from(self):
        for rec in self:
            order_from = ''
            if rec.oloutlet_order_from:
                order_from = rec.oloutlet_order_from.order_from
            rec.oloutlet_order_from = order_from

    @api.depends('oloutlet_order_id')
    def _compute_oloutlet_order_type(self):
        for rec in self:
            order_type = ''
            if rec.oloutlet_order_id:
                order_type = rec.oloutlet_order_id.order_type
            rec.oloutlet_order_type = order_type

    @api.depends('oloutlet_order_id')
    def _compute_oloutlet_order_info(self):
        for rec in self:
            info = ''
            if rec.oloutlet_order_id:
                info = rec.oloutlet_order_id.info
            rec.oloutlet_order_info = info

    