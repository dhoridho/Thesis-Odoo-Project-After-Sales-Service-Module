from odoo import models, fields, api, _


class MPSProduction(models.Model):
    _name = 'equip.mps.production'
    _description = 'MPS Production'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'))
    date = fields.Datetime(string='Production Date', required=True, readonly=True)
    plan_ids = fields.One2many('mrp.plan', 'mps_production_id', string='Production Plans', readonly=True)
    production_ids = fields.One2many('mrp.production', 'mps_production_id', string='Production Orders', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'equip.mps.production', sequence_date=seq_date
            ) or _('New')
        return super(MPSProduction, self).create(vals)

