# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosConfig(models.Model):
    _inherit = "pos.config"

    online_outlet_id = fields.Many2one('pos.online.outlet', string='Online Outlet', copy=False)

    @api.model
    def create(self, vals):
        res = super(PosConfig, self).create(vals)
        self.check_duplicate_outlet(vals.get('online_outlet_id'))
        return res


    def write(self, vals):
        res = super(PosConfig, self).write(vals)
        self.check_duplicate_outlet(vals.get('online_outlet_id'))
        return res

    def check_duplicate_outlet(self, online_outlet_id):
        if online_outlet_id:
            domain = [('online_outlet_id','=', online_outlet_id)]
            pos_configs = self.env[self._name].search(domain, limit=3)
            if len(pos_configs) > 1:
                raise ValidationError('Duplicate online outlet! (%s)' % str(pos_configs[0].online_outlet_id.name))
        return True