# -*- coding: utf-8 -*-

from odoo import api, fields, models

class UoMCategory(models.Model):
    _inherit = 'uom.category'

    @api.model
    def default_get(self, fields):
      vals = super(UoMCategory, self).default_get(fields)
      if 'is_pos_groupable' in fields:
        vals['is_pos_groupable'] = True
      return vals