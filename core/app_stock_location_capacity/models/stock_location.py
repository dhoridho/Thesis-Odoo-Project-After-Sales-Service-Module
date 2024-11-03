# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, tools, models, _


class Location(models.Model):
    _inherit = "stock.location"

    # 库存容量 capacity
    capacity_type = fields.Selection([
        ('model', 'Unique Order'),
        ('unit', 'Unit'),
        # ('weight', 'Weight'),
        # ('volume', 'Volume'),
    ], default='model', string='Capacity Type',
        help='Capacity Type of this Stock Location.')

    occupied_order = fields.Reference(string='Current Order', copy=False,
                                      selection=[
                                          ('sale.order', 'Sale'),
                                          ('purchase.order', 'Purchase'),
                                          ('mrp.production', 'Manufacture'),
                                      ])

    # 容量与当前占用
    capacity_unit = fields.Float('Qty Max', digits='Product Unit of Measure', default=1.0)
    occupied_unit = fields.Float('Qty Occupied', digits='Product Unit of Measure', copy=False)
    # todo: 预计的
    occupied_unit_theoretical = fields.Float('Qty Forecast Max', digits='Product Unit of Measure')
    # todo: 重量及体积
    capacity_weight = fields.Float('Weight Max', digits='Stock Weight')
    occupied_weight = fields.Float('Weight Occupied', digits='Stock Weight', copy=False)
    capacity_volume = fields.Float('Volume Max')
    occupied_volume = fields.Float('Volume Occupied', copy=False)

    occupied_percent = fields.Integer('Occupied(%)', compute='_compute_occupied', store=True)

    # 计算该位置的数量，主要是quant
    @api.depends('capacity_type', 'occupied_order', 'capacity_unit', 'occupied_unit')
    def _compute_occupied(self):
        for rec in self:
            # 只有中转位和内部位置才有库容
            occupied_percent = 0
            if rec.usage in ('internal', 'transit'):
                if rec.capacity_type == 'model':
                    if rec.occupied_order:
                        occupied_percent = 100
                else:
                    try:
                        occupied_percent = 100.0 * rec.occupied_unit / rec.capacity_unit
                    except:
                        occupied_percent = 0
            rec.occupied_percent = occupied_percent


    @api.onchange('capacity_type')
    def onchange_model(self):
        self.occupied_order = None
        if self.capacity_type != 'model':
            self.occupied_order = None
