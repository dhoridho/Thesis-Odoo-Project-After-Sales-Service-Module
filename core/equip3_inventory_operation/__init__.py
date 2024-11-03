# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models
from . import wizard

import logging
_logger = logging.getLogger(__name__)

from odoo import api, SUPERUSER_ID
from odoo.addons.stock.models.stock_quant import StockQuant


def create_picking_type_dashboard_cards(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['stock.picking.type']._create_dashboard_cards()


def _uninstall_hook(cr, registry):
    try:
        StockQuant._revert_method('_update_available_quantity')
    except Exception as err:
        _logger.error('Cannot revert method _update_available_quantity: %s' % err)
