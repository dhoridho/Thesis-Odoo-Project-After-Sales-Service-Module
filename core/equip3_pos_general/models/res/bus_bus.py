# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class ImBus(models.Model):
    _inherit = 'bus.bus'

    # TODO Delete data in model bus.bus if older than 10 days
    def auto_remove_data(self):
        days = 10
        create_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S.999999')
        domain = [('create_date','<',create_date)]
        records = self.env['bus.bus'].sudo().search(domain)
        records.unlink()
        _logger.info(f"[auto_remove_data] - model: bus.bus {len(records)} records deleted")
        return True