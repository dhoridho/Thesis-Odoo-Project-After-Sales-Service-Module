# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models


class Picking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'portal.mixin']

    def _compute_access_url(self):
        super(Picking, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/pickings/%s' % (order.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % ('Delivery', self.name)
