from pickle import TRUE
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, date
import json

class MaintenanceHourMeter(models.Model):
    _name = 'maintenance.hour.meter'
    _description = 'Maintenance Hour Meter'

    name = fields.Char(compute='_compute_asset_log_name', store=True)
    maintenance_asset = fields.Many2one('maintenance.equipment', string='Asset')
    unit = fields.Selection(related='maintenance_asset.hm_unit', string="Unit", readonly=True)
    date = fields.Date(string='Date', required=True)
    value = fields.Float(string='Hour Meter Value',)
    total_value = fields.Float('Total Hourmeter',)

    @api.model
    def create(self, vals):
        res = super(MaintenanceHourMeter, self).create(vals)
        maintenance_asset = vals.get('maintenance_asset')
        maintenance_id = self.env['maintenance.hour.meter'].search([('maintenance_asset', '=', maintenance_asset),
                                                                 ('id','!=',res.id)])
        total_value = sum(maintenance_id.mapped('value'))
        if vals.get('value'):
            res.total_value = total_value + vals.get('value')
        if vals.get('total_value'):
            res.value = vals.get('total_value') - total_value

        return res


    @api.depends('maintenance_asset', 'date')
    def _compute_asset_log_name(self):
        for record in self:
            name = record.maintenance_asset.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('maintenance_asset')
    def _onchange_asset(self):
        if self.maintenance_asset:
            self.unit = self.maintenance_asset.hm_unit

    @api.constrains('date')
    def _check_date(self):
        today = date.today()
        if self.date > today:
            raise ValidationError(_('You are not allowed to register a date later than today\'s date \n Please register a date prior to or on today.'))

class MaintenanceVehicleOdometer(models.Model):
    _name = 'maintenance.vehicle'
    _description = 'Maintenance Vehicle'

    name = fields.Char(compute='_compute_vehicle_log_name', store=True)
    date = fields.Date(string='Date', required=True)
    maintenance_vehicle = fields.Many2one('maintenance.equipment', string='Vehicle')
    value = fields.Float('Odometer Value')
    unit = fields.Selection(related='maintenance_vehicle.odometer_unit', string="Unit", readonly=True)
    total_value = fields.Float('Total Odometer',  required=True)

    @api.model
    def create(self, vals):
        res = super(MaintenanceVehicleOdometer, self).create(vals)
        maintenance_vehicle = vals.get('maintenance_vehicle')
        maintenance_id = self.env['maintenance.vehicle'].search([('maintenance_vehicle', '=', maintenance_vehicle),
                                                                 ('id','!=',res.id)])
        total_value = sum(maintenance_id.mapped('value'))
        if vals.get('value'):
            res.total_value = total_value + vals.get('value')
        if vals.get('total_value'):
            res.value = vals.get('total_value') - total_value

        return res

    @api.depends('maintenance_vehicle', 'date')
    def _compute_vehicle_log_name(self):
        for record in self:
            name = record.maintenance_vehicle.name
            if not name:
                name = str(record.date)
            elif record.date:
                name += ' / ' + str(record.date)
            record.name = name

    @api.onchange('maintenance_vehicle')
    def _onchange_vehicle(self):
        if self.maintenance_vehicle:
            self.unit = self.maintenance_vehicle.odometer_unit


    @api.constrains('date')
    def _check_date(self):
        today = date.today()
        if self.date > today:
            raise ValidationError(_('You are not allowed to register a date later than today\'s date \n Please register a date prior to or on today.'))

class MaintenanceVehicle(models.Model):
    _inherit = 'maintenance.equipment'

    vehicle_checkbox = fields.Boolean(string="Check box")
    maintenance_v = fields.One2many('maintenance.vehicle', 'maintenance_vehicle', string='Vehicle')
    driver_1 = fields.Many2one('res.partner', string='Driver 1')
    driver_2 = fields.Many2one('res.partner', string='Driver 2')
    engine_number = fields.Char('Engine Number')
    chassis_number = fields.Char('Chassis Number')
    transmission =  fields.Selection(string='Transmission', selection=[('manual', 'Manual'), ('automatic', 'Automatic')])
    fuel_type = fields.Many2one('product.product', string='Fuel Type')
    horsepower = fields.Integer(string="Horsepower")
    manufacture_year = fields.Integer(string="Manufacture Year")
    model_year = fields.Integer(string="Model Year")
    capacity = fields.Float(string='Capacity (ton)')
    volume = fields.Float(string='Volume (m3)')
    vehicle_parts_ids = fields.One2many('vehicle.parts', 'maintenance_equipment_id', string='Parts')
    frequency_hourmeter_ids = fields.One2many(comodel_name='request.line', inverse_name='hourmeter_id', string='Frequency Hour')
    frequency_odoometer_ids = fields.One2many(comodel_name='request.line', inverse_name='odoometer_id', string='Frequency Odoo')
    threshold_hourmeter_ids = fields.One2many(comodel_name='threshold.line', inverse_name='thresholdhourmeter_id', string='Frequency Hour')
    threshold_odoometer_ids = fields.One2many(comodel_name='threshold.line', inverse_name='thresholdodometer_id', string='Frequency Odoo')

    odometer_unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi')
        ], 'Odometer Unit', default='kilometers', help='Unit of the odometer ', required=True)

    odometer_count = fields.Integer(string='Odometer Count', compute='_compute_odometer_count')

    def vehicle_moves_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Asset Moves',
            'res_model': 'inter.asset.transfer',
            'domain': [('asset_ids.asset_id','=',self.id)]}

    def _compute_odometer_count(self):
        for rec in self:
            odometer_count = self.env['maintenance.vehicle'].search_count([('maintenance_vehicle', '=', rec.id)])
            rec.odometer_count = odometer_count

    fuel_logs_count = fields.Integer(string='Odometer Count', compute='_compute_fuel_logs_count')

    def _compute_fuel_logs_count(self):
        for rec in self:
            fuel_logs_count = self.env['maintenance.fuel.logs'].search_count([('vehicle', '=', rec.id)])
            rec.fuel_logs_count = fuel_logs_count

class RequestLine(models.Model):
    _name = 'request.line'
    _description = 'Request Line'

    hourmeter_id = fields.Many2one(comodel_name='maintenance.equipment', string='Hour Meter')
    is_hourmeter_m_plan = fields.Many2one(comodel_name='maintenance.plan', string='Hour Meter Maintenance', domain=[('is_hourmeter_m_plan', '=', True)])
    floorhour_value = fields.Integer(string='Floor Value')

    odoometer_id = fields.Many2one(comodel_name='maintenance.equipment', string='Odoo Meter')
    is_odometer_m_plan = fields.Many2one(comodel_name='maintenance.plan', string='Odo Meter Maintenance', domain=[('is_odometer_m_plan', '=', True)])
    floorodoo_value = fields.Integer(string='Floor Value')

class ThresholdLine(models.Model):
    _name = 'threshold.line'
    _description = 'Threshold Line'

    thresholdhourmeter_id = fields.Many2one(comodel_name='maintenance.equipment', string='Hour Meter')
    is_hourmeter = fields.Many2one(comodel_name='maintenance.plan', string='Hour Meter Maintenance', domain=[('is_hourmeter_m_plan', '=', True)])
    last_threshold = fields.Float(string='Last Threshold')

    thresholdodometer_id = fields.Many2one(comodel_name='maintenance.equipment', string='Odoo Meter')
    is_odometer = fields.Many2one(comodel_name='maintenance.plan', string='Odo Meter Maintenance', domain=[('is_odometer_m_plan', '=', True)])
    last_threshold = fields.Float(string='Last Threshold')

class VehicleParts(models.Model):
    _name = 'vehicle.parts'
    _description = 'Vehicle Parts'
    _rec_name = 'equipment_id'

    name = fields.Char(string='Name')
    maintenance_equipment_id = fields.Many2one('maintenance.equipment', string='Maintenance Equipment')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset Name')
    serial_no = fields.Char(string='Serial Number')
    equipment_id_domain = fields.Char("Equipment Domain", compute="_compute_equipment_id_domain")

    @api.onchange('equipment_id')
    def onchange_equipment(self):
        if self._context.get('popup') and self.equipment_id:
            existing_equipment_ids = self.env['vehicle.parts'].search([('equipment_id', '!=', False),('maintenance_equipment_id', '!=', False)]).mapped('equipment_id').ids
            if self.equipment_id.id in existing_equipment_ids:
                existing_equipment = self.env['vehicle.parts'].search([('equipment_id', '=', self.equipment_id.id)], limit=1).maintenance_equipment_id.name
                raise ValidationError(_('Please choose a different equipment.\n This equipment already exists in "%s"') % (existing_equipment))
            self.serial_no = self.equipment_id.serial_no
            
    @api.depends('equipment_id')
    def _compute_equipment_id_domain(self):
        for record in self:
            existing_equipment_ids = self.env['vehicle.parts'].search([('equipment_id', '!=', False),('maintenance_equipment_id', '!=', False)]).mapped('equipment_id').ids
            selected_equipment_ids = record.maintenance_equipment_id.vehicle_parts_ids.mapped('equipment_id.id')
            record.equipment_id_domain = json.dumps (['&',('id', 'not in', selected_equipment_ids), ('id', 'not in', existing_equipment_ids)])
