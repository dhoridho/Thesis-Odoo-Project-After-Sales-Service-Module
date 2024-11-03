# -*- coding: utf-8 -*-

from odoo import fields, models


class Picking(models.Model):
    _name = "stock.picking"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'stock.picking', 'portal.mixin']


    def _compute_access_url(self):
        super(Picking, self)._compute_access_url()
        for picking in self:
            picking.access_url = '/my/delivery_orders_details/%s' % (picking.id)