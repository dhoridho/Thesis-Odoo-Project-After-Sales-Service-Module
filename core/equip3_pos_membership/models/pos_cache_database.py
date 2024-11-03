# -*- coding: utf-8 -*-

from odoo import  models

class PosCacheDatabase(models.Model):
    _inherit = 'pos.cache.database'

    def _sync_pos_partner_domain(self):
        res = super(PosCacheDatabase, self)._sync_pos_partner_domain()
        res += [('is_pos_member','=',True)]
        return res