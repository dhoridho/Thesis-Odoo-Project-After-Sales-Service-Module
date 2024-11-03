# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from datetime import date
from odoo import models, fields, api, _


class FleetVehicleInspection(models.Model):
    _name = 'fleet.vehicle.inspection'
    _description = 'Vehicle Inspection'
    _rec_name = 'ref_number'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    ref_number = fields.Char(string='Reference Number', default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    location_id = fields.Many2one('fleet.vehicle.location', string='Location')
    phone = fields.Char(string='Phone Number')
    responsible_person_id = fields.Many2one('hr.employee', string='Responsible')
    source_document = fields.Char(string='Source Document')
    date = fields.Datetime(string='Date')
    state = fields.Selection([('ready', 'Ready'), ('pause', 'Paused'), ('done', 'Done')], default='ready')
    inspection_exteriors_line_ids = fields.One2many('vehicles.exteriors.lines', 'exterior_line_id',
                                                    string='Inspection Lines')
    inspection_interiors_line_ids = fields.One2many('vehicles.interiors.lines', 'interior_line_id',
                                                    string='Inspection Lines ')
    inspection_mechanical_line_ids = fields.One2many('vehicles.mechanical.lines', 'mechanical_line_id',
                                                     string='Inspection Lines ')
    inspection_tools_line_ids = fields.One2many('vehicles.tools.lines', 'tools_line_id', string='Inspection Lines ')
    delayed_line_ids = fields.One2many('vehicle.delayed', 'inspection_id', string='Delayed Lines')
    fuel_line_ids = fields.One2many('vehicle.fuel', 'vehicle_inspection_id', string='Fuel Lines')
    total_charged_amount = fields.Float(compute='_charged_total_amount', string='Total Charged Amount', store=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  string='Currency')
    total_delayed_amount = fields.Float(string='Delayed Amount', readonly=True)
    total_fuel_charged = fields.Float(string='Fuel Charged Amount')

    @api.depends('inspection_exteriors_line_ids', 'inspection_interiors_line_ids', 'inspection_mechanical_line_ids', 'inspection_tools_line_ids')
    def _charged_total_amount(self):
        for each_tool in self.inspection_tools_line_ids:
            self.total_charged_amount += each_tool.charge_amount
        for each_exteriors in self.inspection_exteriors_line_ids:
            self.total_charged_amount += each_exteriors.charge_amount
        for each_interiors in self.inspection_interiors_line_ids:
            self.total_charged_amount += each_interiors.charge_amount
        for each_mechanical in self.inspection_mechanical_line_ids:
            self.total_charged_amount += each_mechanical.charge_amount

    def create_invoice(self):
        inv_obj = self.env['account.move']
        total_amount = 0
        invoice_line_data = []
        account_id = self.env['account.account'].search([('code', 'like', 'RO100100')])
        for each_tool in self.inspection_tools_line_ids:
            if each_tool.invoice_state == 'draft' and each_tool.charge_amount > 0:
                total_amount += each_tool.charge_amount
                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_id.id,
                                                 'name': 'Tools Missing Invoice ' + self.ref_number,
                                                 'account_id': account_id.id,
                                                 'price_unit': each_tool.charge_amount,
                                                 'quantity': 1,}))
                each_tool.invoice_state = 'to_invoice'
        for each_exteriors in self.inspection_exteriors_line_ids:
            if each_exteriors.invoice_state == 'draft' and each_exteriors.charge_amount > 0:
                total_amount += each_exteriors.charge_amount
                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_id.id,
                                                 'name': 'Exterior Damage Invoice ' + self.ref_number,
                                                 'account_id': account_id.id,
                                                 'price_unit': each_exteriors.charge_amount,
                                                 'quantity': 1, }))
                each_exteriors.invoice_state = 'to_invoice'
        for each_interiors in self.inspection_interiors_line_ids:
            if each_interiors.invoice_state == 'draft' and each_interiors.charge_amount > 0:
                total_amount += each_interiors.charge_amount
                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_id.id,
                                                 'name': 'Interior Damage Invoice ' + self.ref_number,
                                                 'account_id': account_id.id,
                                                 'price_unit': each_interiors.charge_amount,
                                                 'quantity': 1, }))
                each_interiors.invoice_state = 'to_invoice'
        for each_mechanical in self.inspection_mechanical_line_ids:
            if each_mechanical.invoice_state == 'draft' and each_mechanical.charge_amount > 0:
                total_amount += each_mechanical.charge_amount
                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_id.id,
                                                 'name': 'Michanical Damage Invoice ' + self.ref_number,
                                                 'account_id': account_id.id,
                                                 'price_unit': each_mechanical.charge_amount,
                                                 'quantity': 1, }))
                each_mechanical.invoice_state = 'to_invoice'
        for each_delay in self.delayed_line_ids:
            if each_delay.invoice_state == 'draft' and each_delay.delayed_amount > 0:
                total_amount += each_delay.delayed_amount
                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_id.id,
                                                 'name': 'Delay Charge Invoice ' + self.ref_number,
                                                 'account_id': account_id.id,
                                                 'price_unit': each_delay.delayed_amount,
                                                 'quantity': 1, }))
                each_delay.invoice_state = 'to_invoice'
        for each_fuel in self.fuel_line_ids:
            if each_fuel.invoice_state == 'draft' and each_fuel.fuel_charge_amount > 0:
                total_amount += each_fuel.fuel_charge_amount
                invoice_line_data.append((0, 0, {'vehicle_id': self.vehicle_id.id,
                                                 'name': 'Fuel Charge Invoice ' + self.ref_number,
                                                 'account_id': account_id.id,
                                                 'price_unit': each_fuel.fuel_charge_amount,
                                                 'quantity': 1, }))
                each_fuel.invoice_state = 'to_invoice'
        if total_amount > 0:
            invoice = inv_obj.create({
                'ref': self.ref_number,
                'partner_id': self.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': date.today(),
                'account_id': self.customer_id.property_account_receivable_id.id,
                'invoice_line_ids': invoice_line_data,
                'l10n_in_gst_treatment': self.customer_id.l10n_in_gst_treatment or 'regular'
            })
            invoice.action_post()

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('vehicle_inspection') or _('Vehicle Inspection')
        vals.update({'ref_number': sequence})
        return super(FleetVehicleInspection, self).create(vals)

    def done(self):
        self.state = 'done'

    def pause(self):
        self.state = 'pause'

    def resume(self):
        self.state = 'ready'


class VehicleToolsLines(models.Model):
    _name = 'vehicles.tools.lines'
    _description = 'Vehicles Tools Lines'

    tools_line_id = fields.Many2one('fleet.vehicle.inspection', string='Mechanical Inspection')
    inspection = fields.Many2one('vehicle.inspection.tools', String='Inspection')
    result = fields.Selection([('present', 'Present'), ('absent', 'Absent')], string='Status')
    charge_amount = fields.Monetary(string='Charged Amount')
    invoice_state = fields.Selection([('draft', 'Draft'),
                                      ('to_invoice', 'To Invoice')], default='draft')
    currency_id = fields.Many2one('res.currency', related='tools_line_id.currency_id',
                                  string='Currency')


class VehicleExteriorLines(models.Model):
    _name = 'vehicles.exteriors.lines'
    _description = 'Vehicles Exterior Lines'

    exterior_line_id = fields.Many2one('fleet.vehicle.inspection', string='Exterior Inspection')
    inspection = fields.Many2one('vehicle.inspection.exteriors', String='Inspection')
    result = fields.Selection([('passed', 'Passed'), ('repaired', 'Repaired'),
                               ('replaced', 'Replaced'), ('na', 'N/A')], string='Status')
    charge_amount = fields.Monetary(string='Charged Amount')
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_invoice', 'To Invoice')
    ], default='draft')
    currency_id = fields.Many2one('res.currency', related='exterior_line_id.currency_id',
                                  string='Currency')


class VehicleInteriorLines(models.Model):
    _name = 'vehicles.interiors.lines'
    _description = 'Vehicles Interior Lines'

    interior_line_id = fields.Many2one('fleet.vehicle.inspection', string='Interior Inspection')
    inspection = fields.Many2one('vehicle.inspection.interiors', String='Inspection')
    result = fields.Selection([('passed', 'Passed'), ('repaired', 'Repaired'),
                               ('replaced', 'Replaced'), ('na', 'N/A')], string='Status')
    charge_amount = fields.Monetary(string='Charged Amount')
    invoice_state = fields.Selection([
        ('draft', 'Draft'),
        ('to_invoice', 'To Invoice')
    ], default='draft')
    currency_id = fields.Many2one('res.currency', related='interior_line_id.currency_id',
                                  string='Currency')


class VehicleMechanicalLines(models.Model):
    _name = 'vehicles.mechanical.lines'
    _description = 'Vehicles Mechanical Lines'

    mechanical_line_id = fields.Many2one('fleet.vehicle.inspection', string='Mechanical Inspection')
    inspection = fields.Many2one('vehicle.inspection.mechanical', String='Inspection')
    result = fields.Selection([('passed', 'Passed'), ('repaired', 'Repaired'),
                               ('replaced', 'Replaced'), ('na', 'N/A')], string='Status')
    charge_amount = fields.Monetary(string='Charged Amount')
    invoice_state = fields.Selection([('draft', 'Draft'), ('to_invoice', 'To Invoice')],
                                     default='draft')
    currency_id = fields.Many2one('res.currency', related='mechanical_line_id.currency_id',
                                  string='Currency')


class VehicleDelayed(models.Model):
    _name = 'vehicle.delayed'

    inspection_id = fields.Many2one('fleet.vehicle.inspection', string='Inspection')
    name = fields.Char(string='Description')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Name')
    delay_cost_per_hour = fields.Float(string='Cost/Hour')
    delayed_hours = fields.Float(string='Total Hours')
    delayed_amount = fields.Float(string='Delayed Amount')
    invoice_state = fields.Selection([('draft', 'Draft'), ('to_invoice', 'To Invoice')],
                                     default='draft')


class VehicleFuel(models.Model):
    _name = 'vehicle.fuel'

    vehicle_inspection_id = fields.Many2one('fleet.vehicle.inspection', string='Inspection')
    name = fields.Char(string='Description')
    fuel_charge_amount = fields.Float(string='Fuel Charged Amount')
    invoice_state = fields.Selection([('draft', 'Draft'), ('to_invoice', 'To Invoice')],
                                     default='draft')


class VehicleInspectionTools(models.Model):
    _name = 'vehicle.inspection.tools'
    _description = 'Vehicles Inspection Tools'
    _rec_name = 'tools_name'

    tools_name = fields.Char(string='Tools Name')


class VehicleInspectionExteriors(models.Model):
    _name = 'vehicle.inspection.exteriors'
    _description = 'Vehicles Inspection Exteriors'
    _rec_name = 'exterior_inspection_name'

    exterior_inspection_name = fields.Char(string='Exterior Inspection Name')


class VehicleInspectionInteriors(models.Model):
    _name = 'vehicle.inspection.interiors'
    _description = 'Vehicles Inspection Interiors'
    _rec_name = 'interior_inspection_name'

    interior_inspection_name = fields.Char(string='Interior Inspection Name')


class VehicleInspectionMechanical(models.Model):
    _name = 'vehicle.inspection.mechanical'
    _description = 'Vehicles Inspection Mechanical'
    _rec_name = 'mechanical_inspection_name'

    mechanical_inspection_name = fields.Char(string='Mechanical Inspection Name')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
