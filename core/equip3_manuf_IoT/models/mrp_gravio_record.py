import logging
from odoo import models, fields, api
from odoo.tools import float_compare, float_round

_logger = logging.getLogger(__name__)


class MrpGravioRecord(models.Model):
    _name = 'mrp.gravio.record'
    _description = 'Production Gravio Record'

    @api.model
    def create(self, values):
        records = super(MrpGravioRecord, self).create(values)
        records._assign_to_production_record()
        return records

    def unlink(self):
        if not self.env.context.get('skip_check_record', False):
            for record in self:
                if record.log_ids:
                    record.log_ids.with_context(skip_check_logs=True).unlink()
        return super(MrpGravioRecord, self).unlink()

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

    def _assign_to_production_record(self):
        cm_uom = self.env['uom.uom'].browse(self._get_centimeter_uom())
        if not cm_uom:
            _logger.info(_('Centimeter UoM not found!'))
            return

        product_obj = self.env['product.product']
        mpr_obj = self.env['mrp.consumption']
        for record in self:
            if not record.workcenter_id:
                continue
            height = float_round(record.uom_id._compute_quantity(record.height, cm_uom), precision_digits=0)
            width = float_round(record.uom_id._compute_quantity(record.width, cm_uom), precision_digits=0)

            mprs = mpr_obj.search([('state', '=', 'draft')])
            for mpr in mprs:
                for move in mpr.move_raw_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                    product_width_rounded = float_round(move.product_id.width, precision_digits=0)
                    product_height_rounded = float_round(move.product_id.height, precision_digits=0)
                    if not float_compare(width, product_width_rounded, precision_digits=0) and \
                        not float_compare(height, product_height_rounded, precision_digits=0) and \
                            record not in move.gravio_record_ids:
                        move.quantity_done += 1
                        move.gravio_record_ids = [(4, record.id)]

    @api.depends('log_ids', 'log_ids.area_id', 'log_ids.kind_id', 'log_ids.layer_id', 'log_ids.physical_device_id')
    def _compute_from_logs(self):
        for record in self:
            area_id = False
            kind_id = False
            layer_id = False
            physical_device_ids = []
            if record.log_ids:
                log_id = record.log_ids[0]
                area_id = log_id.area_id
                kind_id = log_id.kind_id
                layer_id = log_id.layer_id
                physical_device_ids = record.log_ids.mapped('physical_device_id').ids

            record.area_id = area_id
            record.kind_id = kind_id
            record.layer_id = layer_id
            record.physical_device_ids = [(6, 0, physical_device_ids)]

    @api.depends('log_ids', 'log_ids.timestamp')
    def _compute_timestamp(self):
        for record in self:
            timestamp = False
            if record.log_ids:
                log_id = record.log_ids[0]
                timestamp = log_id.timestamp
            record.timestamp = timestamp

    def _compute_workcenter(self):
        workcenter = self.env['mrp.workcenter']
        for record in self:
            device_id = record.physical_device_ids.filtered(lambda p: p.sensor_type == 'sensor1')
            device_ids = record.physical_device_ids.filtered(lambda p: p.sensor_type in ('sensor2', 'sensor3'))
            exist_workcenter = workcenter.search([
                ('device_id', '=', device_id.id),
                ('device_ids', 'in', device_ids.ids),
            ], limit=1)
            record.workcenter_id = exist_workcenter.id

    def _compute_height_width(self):
        for record in self:
            workcenter = record.workcenter_id
            wc_uom = workcenter and workcenter.device_uom_id or False
            product_uom = record.uom_id
            height = 0.0
            width = 0.0
            if wc_uom and product_uom:
                wc_height = float_round(wc_uom._compute_quantity(workcenter.height_device, product_uom), precision_digits=0)
                wc_width = float_round(wc_uom._compute_quantity(workcenter.width_device, product_uom), precision_digits=0)
                log_id = record.log_ids.filtered(lambda l: l.physical_device_id.sensor_type == 'sensor1')
                log_ids = record.log_ids.filtered(lambda l: l.physical_device_id.sensor_type in ('sensor2', 'sensor3'))
                height = max([0.0, wc_height - sum(log_id.mapped('data_data_uom'))])
                width = max([0.0, wc_width - sum(log_ids.mapped('data_data_uom'))])
            record.height = height
            record.width = width

    area_id = fields.Many2one(comodel_name='mrp.gravio.area', string='Area ID', compute=_compute_from_logs)
    area_name = fields.Char(string='Area Name', related='area_id.name')
    kind_id = fields.Many2one(comodel_name='mrp.gravio.kind', string='Kind ID', compute=_compute_from_logs)
    kind_name = fields.Char(string='Kind Name', related='kind_id.name')
    layer_id = fields.Many2one(comodel_name='mrp.gravio.layer', string='Layer ID', compute=_compute_from_logs)
    layer_name = fields.Char(string='Layer Name', related='layer_id.name')
    physical_device_ids = fields.One2many(comodel_name='mrp.gravio.physical', string='Physical Devices', compute=_compute_from_logs)
    timestamp = fields.Datetime(string='Timestamp', compute=_compute_timestamp, store=True)
    log_ids = fields.One2many('mrp.gravio.log', 'record_id', string='Logs')

    # UoM used in product height & width
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM', default=_get_centimeter_uom, readonly=True)

    workcenter_id = fields.Many2one('mrp.workcenter', compute=_compute_workcenter)
    height = fields.Float(string='Height', compute=_compute_height_width, digits='Gravio Unit of Measure')
    width = fields.Float(string='Width', compute=_compute_height_width, digits='Gravio Unit of Measure')
