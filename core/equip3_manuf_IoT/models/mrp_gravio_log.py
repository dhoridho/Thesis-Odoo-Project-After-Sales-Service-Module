from odoo import models, fields, api, _
from odoo.tools import float_round


class MrpGravioArea(models.Model):
    _name = 'mrp.gravio.area'
    _description = 'Production Gravio Area'
    _rec_name = 'gravio_id'

    gravio_id = fields.Char() 
    name = fields.Char()


class MrpGravioKind(models.Model):
    _name = 'mrp.gravio.kind'
    _description = 'Production Gravio Kind'
    _rec_name = 'gravio_id'

    gravio_id = fields.Char() 
    name = fields.Char()


class MrpGravioLayer(models.Model):
    _name = 'mrp.gravio.layer'
    _description = 'Production Gravio Layer'
    _rec_name = 'gravio_id'

    gravio_id = fields.Char() 
    name = fields.Char()


class MrpGravioPhysical(models.Model):
    _name = 'mrp.gravio.physical'
    _description = 'Production Gravio Physical Device'
    _rec_name = 'gravio_id'

    @api.depends('name')
    def _compute_sensor_type(self):
        for record in self:
            sensor_type = 'unknown'
            name = record.name or ''
            for i in range(1, 4):
                sensor_name = 'sensor%s' % i
                if name.endswith(sensor_name):
                    sensor_type = sensor_name
                    break
            record.sensor_type = sensor_type

    gravio_id = fields.Char() 
    name = fields.Char()
    sensor_type = fields.Selection([
        ('unknown', 'Unknown'),
        ('sensor1', 'Sensor 1'),
        ('sensor2', 'Sensor 2'),
        ('sensor3', 'Sensor 3')
    ], string='Sensor Type', compute=_compute_sensor_type)


class MrpGravioVirtual(models.Model):
    _name = 'mrp.gravio.virtual'
    _description = 'Production Gravio Virtual Virtual'
    _rec_name = 'gravio_id'

    gravio_id = fields.Char() 


class MrpGravioData(models.Model):
    _name = 'mrp.gravio.data'
    _description = 'Production Gravio Data'
    _rec_name = 'gravio_id'

    @api.model
    def _get_meter_uom(self):
        uom_category = self.env['uom.category'].search([('name', 'ilike', 'length')], limit=1)
        uom = self.env['uom.uom'].search([
            ('category_id', '=', uom_category.id), 
            '|', 
                ('name', '=', 'm'), 
                ('name', '=ilike', 'meter')
        ], limit=1)
        return uom.id

    gravio_id = fields.Char()
    data = fields.Float(digits='Gravio Unit of Measure')
    type = fields.Char()
    uom_id = fields.Many2one('uom.uom', string='UoM', default=_get_meter_uom)


class MrpGravioLog(models.Model):
    _name = 'mrp.gravio.log'
    _description = 'Production Gravio Log'
    _rec_name = 'area_name'

    def unlink(self):
        records = self.mapped('record_id')
        result = super(MrpGravioLog, self).unlink()
        if not self.env.context.get('skip_check_logs', False):
            for record in records:
                if not record.log_ids:
                    record.with_context(skip_check_record=True).unlink()
        return result

    @api.depends('data_uom_id', 'record_uom_id', 'data_data')
    def _compute_data_uom(self):
        for record in self:
            data_uom = record.data_uom_id
            record_uom = record.record_uom_id
            data_data_uom = 0.0
            if data_uom and record_uom:
                data_data_uom = float_round(data_uom._compute_quantity(record.data_data, record_uom), precision_digits=0)
            record.data_data_uom = data_data_uom

    area_id = fields.Many2one(comodel_name='mrp.gravio.area', string='Area ID')
    area_name = fields.Char(string='Area Name', related='area_id.name')
    kind_id = fields.Many2one(comodel_name='mrp.gravio.kind', string='Kind ID')
    kind_name = fields.Char(string='Kind Name', related='kind_id.name')
    layer_id = fields.Many2one(comodel_name='mrp.gravio.layer', string='Layer ID')
    layer_name = fields.Char(string='Layer Name', related='layer_id.name')
    physical_device_id = fields.Many2one(comodel_name='mrp.gravio.physical', string='Physical Device ID')
    physical_device_name = fields.Char(string='Physical Device Name', related='physical_device_id.name')
    virtual_device_id = fields.Many2one(comodel_name='mrp.gravio.virtual', string='Virtual Device ID')
    data_id = fields.Many2one(comodel_name='mrp.gravio.data', string='Data ID')
    data_data = fields.Float(string='Gravio Data', related='data_id.data')
    data_uom_id = fields.Many2one(comodel_name='uom.uom', related='data_id.uom_id', string='Gravio UoM') 
    data_type = fields.Char(string='Data Type', related='data_id.type')
    timestamp = fields.Datetime(string='Timestamp')
    json_data = fields.Text(string='JSON Data')

    record_id = fields.Many2one('mrp.gravio.record', string='Record')
    record_uom_id = fields.Many2one('uom.uom', string='UoM', related='record_id.uom_id')
    data_data_uom = fields.Float(string='Data', compute=_compute_data_uom, digits='Gravio Unit of Measure')
