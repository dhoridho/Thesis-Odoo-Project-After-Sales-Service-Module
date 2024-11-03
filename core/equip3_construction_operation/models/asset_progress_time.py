from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta


class AssetTimeProgress(models.Model):
    _name = 'asset.time.progress'
    _description = 'Asset Time Progress'

    allocation_id = fields.Many2one(comodel_name='allocation.asset')
    allocation_asset_id = fields.Many2one(comodel_name='allocation.asset.line')
    operator_id = fields.Many2one(comodel_name='res.users', string='Operator', required=True)
    fuel_type_id = fields.Many2one(related='allocation_asset_id.fuel_type_id', string='Fuel Type')
    fuel_qty = fields.Float(related='allocation_asset_id.fuel_qty', string='Fuel Quantity')
    # temp_fuel_qty = fields.Float(related='allocation_asset_id.temp_fuel_qty')
    date_start = fields.Datetime('Start Date', required=True)
    date_end = fields.Datetime('End Date')
    duration = fields.Float('Duration', compute='_compute_duration', store=True)
    distance = fields.Float('Distance')
    unit = fields.Selection([
        ('kilometers', 'km'),
        ('miles', 'mi')
    ], string='Unit', default='kilometers')
    hour_meter = fields.Float('Hour Meter Value', compute='_compute_hour_meter', store=True)
    fuel_log = fields.Float('Fuel Log', store=True)
    odometer = fields.Float('Odometer', store=True)
    is_new = fields.Boolean('New', default=True)

    @api.constrains('date_end')
    def _check_date(self):
        today = datetime.now()
        if self.date_end > today:
            raise ValidationError(_('You are not allowed to register a date later than today\'s datetime \n Please register a date prior to or on today.'))

    @api.onchange('date_start','date_end')
    def _onchange_date(self):
        if self.date_start and self.date_end and self.date_end < self.date_start:
            raise ValidationError(_('The End Time cannot be before the Start Time.'))

    @api.depends('duration')
    def _compute_hour_meter(self):
        for rec in self:
            if rec.duration:
                if rec.allocation_asset_id.cs_internal_asset_id.uom_id.name == 'Hours':
                    rec.hour_meter = rec.duration / 60.0
                elif rec.allocation_asset_id.cs_internal_asset_id.uom_id.name == 'Days':
                    rec.hour_meter = (rec.duration / 60) / rec.allocation_asset_id.project.working_hour_hours
            else:
                rec.hour_meter = 0.0

    @api.depends('date_end', 'date_start')
    def _compute_duration(self):
        for blocktime in self:
            if blocktime.date_start and blocktime.date_end:
                d1 = fields.Datetime.from_string(blocktime.date_start)
                d2 = fields.Datetime.from_string(blocktime.date_end)
                diff = d2 - d1
                blocktime.duration = round(diff.total_seconds() / 60.0, 2)
            else:
                blocktime.duration = 0.0

    @api.onchange('date_start')
    def _onchange_date_start(self):
        for rec in self:
            if rec.is_new:
                rec.is_new = False
                previous_end_date = rec.allocation_asset_id.time_ids.filtered(
                    lambda line: line.date_end
                ).mapped('date_end')
                if len(previous_end_date) > 0:
                    rec.date_start = max(previous_end_date)
                else:
                    rec.date_start = rec.allocation_asset_id.start_date

    #         if rec.date_start:
    #             if rec.date_start.date() > date.today():
    #                 raise ValidationError("Start Date must be less than or equal to Today")
    #         if rec.date_start and rec.date_end:
    #             if rec.date_start >= rec.date_end:
    #                 raise ValidationError("Start Date must be less than Scheduled End Date of Asset "
    #                                       "Allocation")
    #
    # @api.onchange('date_end')
    # def _onchange_date_end(self):
    #     for rec in self:
    #         if rec.date_end:
    #             if rec.date_end.date() > date.today():
    #                 raise ValidationError("End Date must be less than or equal to Today")
    #         if rec.date_start and rec.date_end:
    #             if rec.date_end <= rec.date_start:
    #                 raise ValidationError("End Date must be greater than Scheduled Start Date of Asset "
    #                                       "Allocation")

    # purposely not using unlink to be able to do delete sequence validation
    def delete_timestamp(self):
        for rec in self:
            if rec.allocation_asset_id:
                # delete sequence validation
                time_ids = self.allocation_asset_id.time_ids
                if len(time_ids) > 1:
                    if rec.id != time_ids[-1].id:
                        raise ValidationError(_("You can only delete the latest timestamp."))
                rec.unlink()

    def unlink(self):
        for rec in self:
            if rec.allocation_asset_id:
                hour_meter = self.env['maintenance.hour.meter'].search([
                    ('asset_allocation_line_id', '=', rec.allocation_asset_id.id)])
                odometer = self.env['maintenance.vehicle'].search([
                    ('asset_allocation_line_id', '=', rec.allocation_asset_id.id)])
                if hour_meter:
                    hour_meter.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
                if odometer:
                    odometer.with_context({'is_delete_from_asset_allocation_line': True}).unlink()
        return super(AssetTimeProgress, self).unlink()


class AssetUsage(models.Model):
    _inherit = 'asset.usage'

    asset_allocation_line_id = fields.Many2one('allocation.asset.line', string='Asset Allocation Line',
                                               ondelete="restrict")

    def unlink(self):
        for rec in self:
            if rec.asset_allocation_line_id:
                if 'is_delete_from_asset_allocation_line' not in self.env.context:
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
        return super(AssetUsage, self).unlink()


class MaintenanceFuelLogs(models.Model):
    _inherit = 'maintenance.fuel.logs'

    asset_allocation_line_id = fields.Many2one('allocation.asset.line', string='Asset Allocation Line',
                                               ondelete="restrict")

    def unlink(self):
        for rec in self:
            if rec.asset_allocation_line_id:
                if 'is_delete_from_asset_allocation_line' not in self.env.context:
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
        return super(MaintenanceFuelLogs, self).unlink()


class MaintenanceVehicle(models.Model):
    # odometer
    _inherit = 'maintenance.vehicle'

    asset_allocation_line_id = fields.Many2one('allocation.asset.line', string='Asset Allocation Line',
                                               ondelete="restrict")

    def unlink(self):
        for rec in self:
            if rec.asset_allocation_line_id:
                if 'is_delete_from_asset_allocation_line' not in self.env.context:
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
        return super(MaintenanceVehicle, self).unlink()


class MaintenanceHourMeter(models.Model):
    _inherit = 'maintenance.hour.meter'

    asset_allocation_line_id = fields.Many2one('allocation.asset.line', string='Asset Allocation Line',
                                               ondelete="restrict")

    def unlink(self):
        for rec in self:
            if rec.asset_allocation_line_id:
                if 'is_delete_from_asset_allocation_line' not in self.env.context:
                    raise ValidationError("You cannot delete this record because it is used in Asset Allocation Line "
                                          "(You may delete it from Asset Allocation Line)")
        return super(MaintenanceHourMeter, self).unlink()
