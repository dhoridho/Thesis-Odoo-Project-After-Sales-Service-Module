from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import json

class AssetUsage(models.Model):
    _name = 'asset.usage'
    _description = 'Asset Usage'

    name = fields.Char(string='Name', required=True)
    facility_id = fields.Many2one(comodel_name='maintenance.facilities.area', string='Facility', required=True)
    equipment_ids = fields.Many2many(comodel_name='maintenance.equipment', string='Equipment', required=True)
    start_date = fields.Datetime(string='Start Date', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one(comodel_name='res.branch', string="Branch", required=True, tracking=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    asset_usage_line = fields.One2many(comodel_name='asset.usage.line', inverse_name='asset_usage_id', string='Asset Usage Line')
    vehicle_usage_line = fields.One2many('asset.usage.line', 'vehicle_usage_id', string='Vehicle Usage Line')

    state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done')], default='draft', tracking=True)
    is_vehicle_or_asset = fields.Selection(string='Is Vehicle or Asset', selection=[('vehicle', 'Vehicle'), ('asset', 'Asset'), ('both', 'Both')], compute='_compute_is_vehicle_or_asset')

    @api.depends('equipment_ids')
    def _compute_is_vehicle_or_asset(self):
        self.is_vehicle_or_asset = False
        list_equipment = [x for x in self.equipment_ids.mapped('vehicle_checkbox')]
        if True in list_equipment and False in list_equipment:
            self.is_vehicle_or_asset = 'both'
        elif False in list_equipment:
            self.is_vehicle_or_asset = 'asset'
        elif True in list_equipment:
            self.is_vehicle_or_asset = 'vehicle'


    def action_confirm(self):
        self.write({'state': 'confirm'})


    def action_done(self):
        maintenance_hour_meter = []
        maintenance_odometer = []

        for asset_usage in self.asset_usage_line:
            hour_meter_vals_asset = self._prepare_maintenance_hour_meter(asset_usage.equipment_id.id, asset_usage.end_time, asset_usage.hour_meter)
            if hour_meter_vals_asset:
                maintenance_hour_meter.append(hour_meter_vals_asset)

        for vehicle_usage in self.vehicle_usage_line:
            hour_meter_vals_vehicle = self._prepare_maintenance_hour_meter(vehicle_usage.equipment_id.id, vehicle_usage.end_time, vehicle_usage.hour_meter)
            if hour_meter_vals_vehicle:
                maintenance_hour_meter.append(hour_meter_vals_vehicle)

            odometer_vals_vehicle = self._prepare_maintenance_odometer(vehicle_usage.equipment_id.id, vehicle_usage.end_time, vehicle_usage.odometer)
            if odometer_vals_vehicle:
                maintenance_odometer.append(odometer_vals_vehicle)

            # for create maintenance_fuel_logs
            equip_fuel_logs = self.env['maintenance.fuel.logs'].search([('vehicle', '=', vehicle_usage.equipment_id.id)],limit = 1, order='id DESC' )
            self.env['maintenance.fuel.logs'].create({
                'vehicle' : vehicle_usage.equipment_id.id,
                'date' : vehicle_usage.start_time,
                'fuel_type' : vehicle_usage.equipment_id.fuel_type.id,
                'fuel_usage' : vehicle_usage.fuel_usage,
                'liter' : 0,
                'current_fuel' : equip_fuel_logs.current_fuel - vehicle_usage.fuel_usage,
                'odometer' : vehicle_usage.odometer,
                'hour_meter' :vehicle_usage.hour_meter,
                'not_fueling': 1,
                'state': 'confirm',
                })

        if maintenance_hour_meter:
            self.env['maintenance.hour.meter'].create(maintenance_hour_meter)

        if maintenance_odometer:
            self.env['maintenance.vehicle'].create(maintenance_odometer)

        self.write({'state': 'done'})
        self.asset_usage_line.write({'state': 'done'})
        self.vehicle_usage_line.write({'state': 'done'})

    def _prepare_maintenance_hour_meter(self, equipment_id, end_time, hour_meter_value):
        """
        Prepare a maintenance hour meter record for the given asset with the given values
        """
        if hour_meter_value > 0:
            vals = {
                'maintenance_asset': equipment_id,
                'date': end_time,
                'value': hour_meter_value,
            }
            return vals

    def _prepare_maintenance_odometer(self, equipment_id, end_time, odometer_value):
        """
        Prepare a maintenance odometer record for the given vehicle with the given values
        """
        if odometer_value > 0:
            vals = {
                'maintenance_vehicle': equipment_id,
                'date': end_time,
                'total_value': odometer_value,
            }
            return vals


class AssetUsageLine(models.Model):
    _name = 'asset.usage.line'
    _description = 'Asset Usage Line'

    asset_usage_id = fields.Many2one(comodel_name='asset.usage', string='Asset Usage')
    vehicle_usage_id = fields.Many2one(comodel_name='asset.usage', string='Vehicle Usage')
    start_time = fields.Datetime(string='Start Time', required=True)
    end_time = fields.Datetime(string='End Time', required=True)
    operator_id = fields.Many2one(comodel_name='res.users', string='Operator', required=True)
    equipment_asset_id_domain = fields.Char(string='Equipment Domain', compute='_compute_asset_equipment_id_domain')
    equipment_vehicle_id_domain = fields.Char(string='Equipment Domain', compute='_compute_vehicle_equipment_id_domain')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Equipment', required=True)
    activity_type = fields.Selection(string='Activity Type', selection=[('operative', 'Operative'), ('idle', 'Idle'), ('breakdown', 'Breakdown'), ('maintenance', 'Maintenance'), ('standby', 'Standby')], required=True)
    asset_activity_id = fields.Many2one(comodel_name='asset.activity', string='Activity')
    notes = fields.Text(string='Notes')
    fuel_usage = fields.Float(string='Fuel Usage')
    odometer = fields.Float(string='Odometer')
    hour_meter = fields.Float(string='Hour Meter')
    state = fields.Selection(string='State', selection=[('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done')], default='draft')


    @api.depends('asset_usage_id.equipment_ids')
    def _compute_asset_equipment_id_domain(self):
        asset_equipment_ids = self.asset_usage_id.equipment_ids.filtered(lambda x: not x.vehicle_checkbox).ids
        self.equipment_asset_id_domain = json.dumps([('id', 'in', False)])
        if asset_equipment_ids:
            self.equipment_asset_id_domain = json.dumps([('id', 'in', asset_equipment_ids)])
        else:
            self.equipment_asset_id_domain = json.dumps([('id', '=', False)])

    @api.depends('vehicle_usage_id.equipment_ids')
    def _compute_vehicle_equipment_id_domain(self):
        vehicle_equipment_ids = self.vehicle_usage_id.equipment_ids.filtered(lambda x: x.vehicle_checkbox).ids
        self.equipment_vehicle_id_domain = json.dumps([('id', 'in', False)])
        if vehicle_equipment_ids:
            self.equipment_vehicle_id_domain = json.dumps([('id', 'in', vehicle_equipment_ids)])
        else:
            self.equipment_vehicle_id_domain = json.dumps([('id', '=', False)])


    @api.onchange('equipment_id')
    def _onchange_equipment_id(self):

        if self.equipment_id:
            if self.asset_usage_id:
                asset_usage_lines = self.asset_usage_id.asset_usage_line.filtered(
                    lambda line: line.equipment_id == self.equipment_id and line.end_time
                ).mapped('end_time')
                if asset_usage_lines:
                    self.start_time = max(asset_usage_lines)

            if self.vehicle_usage_id:
                vehicle_usage_lines = self.vehicle_usage_id.vehicle_usage_line.filtered(
                    lambda line: line.equipment_id == self.equipment_id and line.end_time
                ).mapped('end_time')
                if vehicle_usage_lines:
                    self.start_time = max(vehicle_usage_lines)


    @api.onchange('end_time','start_time','activity_type')
    def _onchange_date(self):
        if self.start_time and self.end_time and self.end_time < self.start_time:
            raise UserError(_('The End Time cannot be before the Start Time.'))

        if self.start_time and self.end_time and self.activity_type == 'operative':
            time_difference_seconds = (self.end_time - self.start_time).total_seconds()
            time_difference_seconds -= time_difference_seconds % 60  # Remove seconds
            hours = int(time_difference_seconds // 3600)
            minutes = int((time_difference_seconds % 3600) // 60)
            self.hour_meter = hours + (minutes / 60)
        else:
            self.hour_meter = 0.0
