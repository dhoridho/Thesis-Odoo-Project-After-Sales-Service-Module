# -*- coding: utf-8 -*-

from odoo import fields, models

class PosCategory(models.Model):
    _inherit = 'pos.category'

    def get_the_great_parent(self):
        if self.parent_id:
            return self.parent_id.get_the_great_parent()
        else:
            return self