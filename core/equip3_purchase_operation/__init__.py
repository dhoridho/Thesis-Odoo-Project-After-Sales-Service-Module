# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import controllers
from . import models
from . import wizard

from odoo import api, SUPERUSER_ID
from odoo.addons.purchase_stock.models.purchase import PurchaseOrderLine as BasicPurchaseOrderLine
from odoo.addons.purchase_stock.models.stock import StockMove as PurchaseStockMove

def assign_purchase_request_template(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company']._assign_purchase_request_template()

def _uninstall_hook(cr, registry):
    to_reverts = [
        (BasicPurchaseOrderLine, ('_get_stock_move_price_unit',)),
        (PurchaseStockMove, ('_get_price_unit',)),
    ]
    for model, methods in to_reverts:
        for method in methods:
            try:
                model._revert_method(method)
            except Exception as err:
                _logger.error('Cannot revert method %s: %s' % (method, err))