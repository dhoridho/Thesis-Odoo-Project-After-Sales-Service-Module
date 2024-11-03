# -*- coding: utf-8 -*-

from odoo import fields, models

class PosEmenuOutletImage(models.Model):
    _name = 'pos.emenu.outlet.image'
    _description = 'POS E-menu Outlet Image'
    _order = 'sequence, id'

    name = fields.Char('Filename')
    image = fields.Image('Image')
    sequence = fields.Integer(default=10, index=True)
    url = fields.Char('URL', compute='_compute_url')

    def _compute_url(self):
        for rec in self:
            rec.url = f'/emenu/content/outlet_image/{rec.id}/image/{rec.name}'
