# -*- coding: utf-8 -*-
# Copyright 2022 IZI PT Solusi Usaha Mudah

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"
    
    sale_channel_ids = fields.Many2many(comodel_name='sale.channel', string="Sale Channel")
    loyalty_points = fields.Float(company_dependent=True, help='The loyalty points the user won as part of a Loyalty Program')
    loyalty_points_move_ids = fields.One2many('sale.loyalty.points.move', 'partner_id', string='Loyalty Points Moves')
    birthday = fields.Date('Birthday')

    def compute_loyalty_points(self):
        for record in self:
            total = 0
            for move in record.loyalty_points_move_ids:
                total += move.loyalty_points
            record.loyalty_points = total