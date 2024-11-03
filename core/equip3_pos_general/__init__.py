# -*- coding: utf-8 -*-

from . import controllers
from . import controller_cache
#from . import controller_printer_network
from . import models
from . import report
from . import wizard

import logging
from odoo import api, fields, SUPERUSER_ID

_logger = logging.getLogger(__name__)

def _auto_clean_cache_when_installed(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    caches = env['pos.cache.database'].search([])
    caches.unlink()
    env['ir.config_parameter'].sudo().set_param('license_started_date', fields.Date.today())
    _logger.info('!!!!!!! Removed caches !!!!!!!')
    _logger.info('!!!!!!! THANKS FOR PURCHASED MODULE !!!!!!!')

