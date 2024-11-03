# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizards
from odoo.addons.equip3_manuf_operations.models.stock_move import StockMove


def _action_assign(self):
    """ Exclude only moves that hasn't create production record """
    moves_todo = self
    if self._context.get('exclude_mrp_moves', False):
        moves_todo = moves_todo.filtered(
            lambda m: not m.raw_material_production_id or (m.raw_material_production_id and m.mrp_consumption_id))
    return super(StockMove, moves_todo)._action_assign()


def _monkey():
    """ So, we need mrp moves not to auto reserve when material is available, 
    but this doesn't apply to moves already assigned to production record. 
    Since calling `mrp_consumption_id` in equip3_manuf_operations is not allowed, 
    and `self` will change when `super()` is called, so we came up with this solution. """
    StockMove._action_assign = _action_assign
