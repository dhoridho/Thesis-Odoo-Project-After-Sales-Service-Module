from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    @api.model
    def _get_centimeter_uom(self):
        uom_category = self.env['uom.category'].search([('name', 'ilike', 'length')], limit=1)
        uom = self.env['uom.uom'].search([
            ('category_id', '=', uom_category.id), 
            '|', 
                ('name', '=', 'cm'), 
                ('name', '=ilike', 'centimeter')
        ], limit=1)
        return uom.id

    device_id = fields.Many2one('mrp.gravio.physical', string='Device 1', domain="[('name', 'ilike', 'sensor1')]")
    device_ids = fields.Many2many('mrp.gravio.physical', string='Device 2 & 3', domain="['|', ('name', 'ilike', 'sensor2'), ('name', 'ilike', 'sensor3')]")

    height_device = fields.Float(string='Device Height', digits='Gravio Unit of Measure')
    width_device = fields.Float(string='Device Width', digits='Gravio Unit of Measure')
    device_uom_id = fields.Many2one('uom.uom', string='Device UoM', default=_get_centimeter_uom, domain="[('category_id.name', 'ilike', 'length')]")

    @api.constrains('device_id', 'device_ids')
    def _constrains_devices(self):
        workcenter = self.env['mrp.workcenter']
        for record in self:
            exist_workcenter = workcenter.search([
                ('id', '!=', record.id),
                '|',
                    '&',
                        ('device_id', '=', record.device_id.id),
                        ('device_id', '!=', False),
                    '&',
                        ('device_ids', 'in', record.device_ids.ids),
                        ('device_ids', '!=', False)
            ])
            if exist_workcenter:
                raise ValidationError(_('Device %s already assigned in workcenter %s!' % (device.display_name, exist_workcenter[0].display_name)))
