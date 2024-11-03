from odoo import models, fields, api, _, SUPERUSER_ID
from odoo.exceptions import ValidationError
from datetime import datetime, date
import pytz
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT




class AssetEmployeeRental(models.Model):
    _name = 'asset.employee.rental'
    _inherit = ['mail.thread','mail.activity.mixin']
    _description = 'Asset Employee Rental'
    
    name = fields.Char(string='Name', readonly=True, default='New', Tracking=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)], Tracking=True)
    date_from = fields.Datetime(string='From', required=True, tracking=True)
    date_to = fields.Datetime(string='To', required=True, tracking=True)
    priority = fields.Selection(string='Priority', selection=[('0', 'Not Urgent'), ('1', 'Low Urgency'), ('2', 'Normal Urgency'), ('3', 'High Urgency')], default='0', tracking=True)
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('running', 'Running'), ('on_rent', 'On Rent'), ('done', 'Done'),], default='draft', group_expand='_read_group_state', tracking=True)
    rental_type = fields.Selection(string='Rental Type', selection=[('asset', 'Asset'), ('facility', 'Facility Area'),], required=True, tracking=True)
    asset_ids = fields.One2many(comodel_name='maintenance.equipment', inverse_name='asset_rental_id', string='Assets', compute='_compute_asset_ids')
    facility_ids = fields.One2many(comodel_name='maintenance.facilities.area', inverse_name='facility_rental_id', string='Facility Areas', compute='_compute_facility_ids')
    rental_line = fields.One2many(comodel_name='asset.employee.rental.line', inverse_name='rental_id', string='Rental Line', copy=True)
    
    @api.model
    def _read_group_state(self, stages, domain, order):
        """ Read group customization in order to display all the stages in the
            kanban view, even if they are empty
        """
        state = ['draft','running','on_rent','done']
        return state
    
    @api.depends('rental_line')
    def _compute_asset_ids(self):
        for rec in self:
            rec.asset_ids = False
            if rec.rental_type == 'asset' and rec.rental_line:
                rec.asset_ids = rec.rental_line.mapped('asset_id')
                
    @api.depends('rental_line')
    def _compute_facility_ids(self):
        for rec in self:
            rec.facility_ids = False
            if rec.rental_type == 'facility' and rec.rental_line:
                rec.facility_ids = rec.rental_line.mapped('facility_id')
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('asset.employee.rental')
        self._calendar_create(vals)
        return super(AssetEmployeeRental, self).create(vals)
    
    
    def _calendar_create(self, vals):
        context = dict(self._context or {})
        if 'create_from_calendar' in context and vals['state'] == 'draft':
            rental_line = vals.get('rental_line')
            if not rental_line:
                if vals.get('rental_type') == 'asset':
                    raise ValidationError(_('Please add asset'))
                else:
                    raise ValidationError(_('Please add facility area'))
            else:
                for line in rental_line:
                    if vals.get('rental_type') == 'asset':
                        overlap_rental = self.env['asset.employee.rental.line'].search([('asset_id', '=', line[2]['asset_id']), ('rental_id.date_from', '<=', vals['date_to']), ('rental_id.date_to', '>=', vals['date_from']), ('rental_id.state', 'in', ['running', 'on_rent'])])
                        if overlap_rental:
                            date_from = overlap_rental.rental_id.date_from.astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                            date_to = overlap_rental.rental_id.date_to.astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                            raise ValidationError(_(f'This Asset has been rented for the chosen date indicated by this reference number {overlap_rental.rental_id.name} with due date {date_from.strftime("%d/%m/%Y %H:%M:%S")} - {date_to.strftime("%d/%m/%Y %H:%M:%S")}'))
                        else:
                            vals['state'] = 'running'
                    else:
                        overlap_facility = self.env['asset.employee.rental.line'].search([('facility_id', '=', line[2]['facility_id']), ('rental_id.date_from', '<=', vals['date_to']), ('rental_id.date_to', '>=', vals['date_from']), ('rental_id.state', 'in', ['running', 'on_rent'])])
                        if overlap_facility:
                            date_from = overlap_facility.rental_id.date_from.astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                            date_to = overlap_facility.rental_id.date_to.astimezone(pytz.timezone(self.env.user.tz)).replace(tzinfo=None)
                            raise ValidationError(_(f'This Facilty Area has been rented for the chosen date indicated by this reference number {overlap_facility.rental_id.name} with due date {date_from.strftime("%d/%m/%Y %H:%M:%S")} - {date_to.strftime("%d/%m/%Y %H:%M:%S")}'))
                        else:
                            vals['state'] = 'running'

    
    @api.onchange('date_from', 'date_to', 'rental_line')
    def _onchange_date(self):
        if self.date_to and self.date_from:
            if self.date_to < self.date_from:
                raise ValidationError(_('Date To must be greater than Date From'))

    def button_running(self):
        if not self.rental_line:
            if self.rental_type == 'asset':
                raise ValidationError(_('Please add asset'))
            else:
                raise ValidationError(_('Please add facility area'))
        for line in self.rental_line:
            if self.rental_type == 'asset':
                overlap_rental = self.env['asset.employee.rental.line'].search([('id', '!=', line.id), ('asset_id', '=', line.asset_id.id), ('rental_id.date_from', '<=', self.date_to), ('rental_id.date_to', '>=', self.date_from), ('rental_id.state', 'in', ['running', 'on_rent'])])
                if overlap_rental:
                    raise ValidationError(_(f'This Asset has been rented for the chosen date indicated by this reference number {overlap_rental.rental_id.name}'))
            else:
                overlap_rental = self.env['asset.employee.rental.line'].search([('id', '!=', line.id), ('facility_id', '=', line.facility_id.id), ('rental_id.date_from', '<=', self.date_to), ('rental_id.date_to', '>=', self.date_from), ('rental_id.state', 'in', ['running', 'on_rent'])])
                if overlap_rental:
                    raise ValidationError(_(f'This Facilty Area has been rented for the chosen date indicated by this reference number {overlap_rental.rental_id.name}'))
            self.write({'state': 'running'})

    def button_done(self):
        self.write({'state': 'done'})
        
    def button_draft(self):
        self.write({'state': 'draft'})
        
    def button_on_rent(self):
        self.write({'state': 'on_rent'})
        
    def scheduled_asset_employee_rental(self):
        asset_employee_rental_running_ids = self.env['asset.employee.rental'].search([('state', '=', 'running')])
        for asset_rental_running in asset_employee_rental_running_ids:
            if asset_rental_running.date_from <= fields.Datetime.now() <= asset_rental_running.date_to:
                asset_rental_running.write({'state': 'on_rent'})
        
        asset_employee_rental_ids = self.env['asset.employee.rental'].search([('state', 'in', ['running', 'on_rent'])])
        for asset_rental in asset_employee_rental_ids:
            if asset_rental.date_to <= fields.Datetime.now(): 
                asset_rental.write({'state': 'done'})
        return True

class AssetEmployeeRentalLine(models.Model):
    _name = 'asset.employee.rental.line'
    _description = 'Asset Employee Rental Line'
    
    rental_id = fields.Many2one(comodel_name='asset.employee.rental', string='Rental')
    asset_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset')
    facility_id = fields.Many2one(comodel_name='maintenance.facilities.area', string='Facility Area')
    user_id = fields.Many2one(comodel_name='res.users', string='Rented By', default=lambda self: self.env.user)
    notes = fields.Char(string='Notes')

class MaintennaceEquipmentAssetRental(models.Model):
    _inherit = 'maintenance.equipment'
    
    asset_rental_id = fields.Many2one(comodel_name='asset.employee.rental', string='Asset Rental')
    
class MaintenanceFasilityAreaRent(models.Model):
    _inherit = 'maintenance.facilities.area'
    
    facility_rental_id = fields.Many2one(comodel_name='asset.employee.rental', string='Facility Rental')