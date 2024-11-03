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

from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning


class FleetVehicleMove(models.Model):
    _name = 'fleet.vehicle.move'
    _description = 'Fleet Vehicle Move'
    _rec_name = 'ref_number'

    ref_number = fields.Char(string='Reference Number', default='New')
    customer_id = fields.Many2one('res.partner', string='Customer')
    scheduled_date = fields.Datetime(string='Scheduled Date')
    from_date = fields.Datetime(string='From Date')
    to_date = fields.Datetime(string='To date')
    is_delayed = fields.Boolean(string='Is Delayed')
    delayed_hours = fields.Char('Delayed Hours')
    source_location = fields.Many2one('fleet.vehicle.location', string='Source Location')
    destination_location = fields.Many2one('fleet.vehicle.location', string='Destination Location')
    state = fields.Selection([('ready', 'Ready'), ('partial', 'Partially Transfered'),
                              ('on_rent', 'On Rent'), ('inspection', 'Inspections Created'),
                              ('service', 'Service'), ('done', 'Done')], default='ready')
    source_document = fields.Char(string='Source Document')
    move_type = fields.Selection([('outgoing', 'Customers'), ('incoming', 'Return'),
                                  ('internal', 'Internal')], string='Type of Operation',
                                 required=True, default='outgoing')
    vehicle_move_line_id = fields.One2many('vehicle.move.lines', 'vehicle_move_id',
                                           string='Move Lines')
    vehicle_delay_line_ids = fields.One2many('vehicle.delayed.lines', 'vehicle_delay_id',
                                             string='Delayed Hours ')
    vehicle_order_rel_id = fields.Many2one('fleet.vehicle.order', string='Vehicle Order')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total', store=True)
    contract_count = fields.Integer(compute='_contract_total', string="Total Contract")
    contract_ids = fields.One2many('fleet.vehicle.contract', 'move_id', string="Contract Id")
    station_id = fields.Many2one('fleet.vehicle.station', string='Auto Station')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id',
                                  string='Currency')
    fuel_level = fields.Float(string='Fuel Level')
    return_fuel_level = fields.Float(string='Fuel Level ')
    is_fuel_charge = fields.Boolean(string='Is Fuel Charge')
    fuel_charge_line_ids = fields.One2many('vehicle.fuel.lines', 'vehicle_fuel_id',
                                           string='Fuel Charge')

    @api.onchange('return_fuel_level')
    def _onchange_return_fuel(self):
        if self.return_fuel_level < self.fuel_level:
            self.is_fuel_charge = True

    @api.constrains('fuel_level')
    def check_fuel_level(self):
        if self.state == 'ready' and self.fuel_level <= 0.0:
            raise Warning (_('Please add some fuel in the vehicle'))

    @api.depends('contract_ids')
    def _contract_total(self):
        for contract in self:
            contract.contract_count = len(contract.contract_ids)

    def action_view_move_contract(self):
        action = self.env.ref('aspl_vehicle_rental.action_rental_contract_view_tree').read()[0]
        contracts = self.mapped('contract_ids')
        if len(contracts) > 1:
            action['domain'] = [('id', 'in', contracts.ids)]
        elif contracts:
            action['views'] = [(self.env.ref('aspl_vehicle_rental.fleet_vehicle_contract_form').id, 'form')]
            action['res_id'] = contracts.id
        return action

    @api.depends('vehicle_delay_line_ids')
    def _compute_total(self):
        for each in self:
            for line in each.vehicle_delay_line_ids:
                each.total_amount += line.sub_total

    @api.model
    def create(self, vals):
        sequence = self.env['ir.sequence'].next_by_code('vehicle_move') or _('Vehicle Move')
        vals.update({'ref_number': sequence})
        return super(FleetVehicleMove, self).create(vals)

    def delivery(self):
        vehicle_order_id = []
        vehi_order_id = []
        vehi_delay_id = []
        for each_contract in self.contract_ids:
            if all([each.vehicles_checked for each in self.vehicle_move_line_id]):
                deli_order_id = self.copy()
                for each in self.vehicle_move_line_id.filtered(lambda l: l.vehicles_checked):
                    vehi_order_id.append(
                        (0, 0, {'vehicle_id': each.vehicle_id.id,
                                'vehicles_checked': each.vehicles_checked,
                                'current_odometer': each.current_odometer,
                                'tools_ids': [(6, 0, each.tools_ids.ids)]
                                }))
                    vehi_delay_id.append((0,0,{'vehicle_id': each.vehicle_id.id,
                                               'vehicle_delay_id':self.id}))
                deli_order_id.write({'move_type': 'incoming',
                                     'state': 'on_rent',
                                     'vehicle_move_line_id': vehi_order_id,
                                     'vehicle_delay_line_ids': vehi_delay_id
                                     })

                self.state = 'done'

            elif any([each.vehicles_checked for each in self.vehicle_move_line_id]):
                deliver_move_id = self.copy()
                for each in self.vehicle_move_line_id:
                    if not each.vehicle_id:
                        self.unlink()
                for each in self.vehicle_move_line_id.filtered(lambda l: l.vehicles_checked):
                    vehicle_order_id.append(
                        (0, 0, {'vehicle_id': each.vehicle_id.id,
                                'vehicles_checked': each.vehicles_checked,
                                'current_odometer': each.current_odometer,
                                'tools_ids': [(6, 0, each.tools_ids.ids)]
                                }))
                    vehi_delay_id.append((0,0,{'vehicle_id': each.vehicle_id.id,
                                               'vehicle_delay_id':self.id}))
                    each.unlink()
                deliver_move_id.write({'move_type': 'incoming',
                                       'state': 'on_rent',
                                       'vehicle_move_line_id': vehicle_order_id,
                                       'vehicle_delay_line_ids': vehi_delay_id
                                       })

            else:
                raise UserError(_('Please Select Some Vehicles to Move'))

    def incoming(self):
        if self.state == 'on_rent' and self.return_fuel_level <= 0.0:
            raise Warning(_('Please first check the fuel in the vehicle'))
        incoming_move_id = self.copy()
        vehicle_order_id = []
        inspection_exterior = []
        inspection_interior = []
        inspection_mechanical = []
        delayed_line = []
        fuel_line = []
        total_fuel_charge = 0

        for line in self.env['vehicle.inspection.exteriors'].search([]):
            inspection_exterior.append((0, 0, {'inspection': line.id}))
        for line in self.env['vehicle.inspection.interiors'].search([]):
            inspection_interior.append((0, 0, {'inspection': line.id}))
        for line in self.env['vehicle.inspection.mechanical'].search([]):
            inspection_mechanical.append((0, 0, {'inspection': line.id}))

        for line in self.fuel_charge_line_ids:
            total_fuel_charge += line.fuel_charge_amount
            fuel_line.append((0, 0, {'name': line.name,
                                     'fuel_charge_amount': line.fuel_charge_amount}))

        for line in self.vehicle_delay_line_ids:
            delayed_line.append((0, 0, {'name': 'Vehicle Delayed Charges',
                                        'vehicle_id': line.vehicle_id.id,
                                        'delay_cost_per_hour': line.delay_cost_per_hour,
                                        'delayed_hours': line.delayed_hours,
                                        'delayed_amount': line.sub_total}))

        for each in self.vehicle_move_line_id:
            inspection_tools = []
            for tool in each.tools_ids.ids:
                inspection_tools.append((0, 0, {'inspection': tool}))

            vehicle_order_id.append((0, 0, {'vehicle_id': each.vehicle_id.id,
                                            'vehicles_checked': each.vehicles_checked,
                                            }))
            self.env['fleet.vehicle.inspection'].create({'customer_id': self.customer_id.id,
                                                         'vehicle_id': each.vehicle_id.id,
                                                         'phone': self.customer_id.phone,
                                                         'date': self.to_date,
                                                         'source_document': self.source_document,
                                                         'total_delayed_amount': self.total_amount,
                                                         'delayed_line_ids': delayed_line,
                                                         'total_fuel_charged': total_fuel_charge,
                                                         'fuel_line_ids': fuel_line,
                                                         'inspection_tools_line_ids': inspection_tools,
                                                         'inspection_exteriors_line_ids': inspection_exterior,
                                                         'inspection_interiors_line_ids': inspection_interior,
                                                         'inspection_mechanical_line_ids': inspection_mechanical,
                                                         })
            self.env['fleet.vehicle.logs'].create({'customer_id': self.customer_id.id,
                                                   'vehicle_id': each.vehicle_id.id,
                                                   'odometer': each.current_odometer,
                                                   'odometer_unit': each.vehicle_id.odometer_unit,
                                                   'from_date': self.from_date,
                                                   'to_date': self.to_date,
                                                   })

            each.vehicle_id.write({'odometer': each.current_odometer})

        incoming_move_id.write({'move_type': 'internal',
                                'state': 'service',
                                'vehicle_move_line_id': vehicle_order_id})

        order_id = self.env['fleet.vehicle.order'].search([('res_number', '=', self.source_document)])
        for each_order in order_id:
            each_order.state = 'close'
            each_order.return_date = datetime.now()
        self.state = 'inspection'

    def move(self):
        if all([each.state == 'done' for each in
                self.env['fleet.vehicle.inspection'].search([('source_document', '=', self.source_document)])]):
            self.state = 'done'

        else:
            raise Warning('You Need To Complete The Inspections Before You Move To Vehicle Parking')

    def unlink(self):
        for each in self:
            if each.state == 'done':
                raise Warning('Cannot delete a Vehicle Move in Done State')
            return super(FleetVehicleMove, each).unlink()


class VehicleMoveLines(models.Model):
    _name = 'vehicle.move.lines'
    _description = 'Vehicle Move Lines'

    vehicle_move_id = fields.Many2one('fleet.vehicle.move', string='Vehicle Move')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Name')
    vehicles_checked = fields.Boolean(string='Select Vehicles')
    current_odometer = fields.Float(string='Current Odometer')
    tools_ids = fields.Many2many('vehicle.inspection.tools', 'vehicle_inspection_tools_rel', string='Tools')


class VehicleDelayLines(models.Model):
    _name = 'vehicle.delayed.lines'
    _description = 'Vehicle Delayed Lines'

    @api.depends('delayed_hours', 'delay_cost_per_hour')
    def _get_subtotal(self):
        for each in self:
            each.sub_total = each.delayed_hours * each.delay_cost_per_hour

    vehicle_delay_id = fields.Many2one('fleet.vehicle.move', string='Vehicle Move')
    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle Name')
    delay_cost_per_hour = fields.Float(string='Cost/Hour')
    delayed_hours = fields.Float(string='Total Hours')
    sub_total = fields.Monetary(string='Sub Total', compute='_get_subtotal', store=True)
    currency_id = fields.Many2one('res.currency', related='vehicle_delay_id.currency_id',
                                  string='Currency')


class VehicleFuelLines(models.Model):
    _name = 'vehicle.fuel.lines'
    _description = 'Vehicle Fuel Lines'

    def default_name(self):
        return 'Fuel Charge'

    vehicle_fuel_id = fields.Many2one('fleet.vehicle.move', string='Vehicle Fuel')
    name = fields.Char(string='Description', readonly=True, default=default_name)
    fuel_charge_amount = fields.Float(string='Charge Amount')


class FleetVehicleStation(models.Model):
    _name = 'fleet.vehicle.station'
    _description = 'Fleet Vehicles Station'

    name = fields.Char(string='Auto Station Name', required=True)
    short_name = fields.Char(string='Short Name', required=True, size=5)
    address_id = fields.Many2one('res.partner', required=True, string='Address')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)


class FleetVehicleLocation(models.Model):
    _name = 'fleet.vehicle.location'
    _description = 'Auto Station Locations'
    _parent_name = 'location_id'
    _parent_store = True
    _parent_order = 'name'
    _order = 'parent_left'
    _rec_name = 'complete_name'

    name = fields.Char(string='Auto Station Name', required=True)
    complete_name = fields.Char(string='Full Location Name', compute='_compute_complete_name',
                                store=True)
    location_id = fields.Many2one('fleet.vehicle.location', string='Parent Location',
                                  index=True, ondelete='cascade')
    location_type = fields.Selection([('transit', 'Transit Location'),
                                      ('return', 'Recieving Location')], string='Location Type')
    station_id = fields.Many2one('fleet.vehicle.station', string='Auto Station')
    parent_left = fields.Integer('Left Parent', index=True)
    parent_right = fields.Integer('Right Parent', index=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)
    parent_path = fields.Char(index=True)

    @api.depends('name', 'location_id.name')
    def _compute_complete_name(self):
        name = self.name
        current = self
        while current.location_id:
            current = current.location_id
            name = '%s/%s' % (current.name, name)
        self.complete_name = name


class FleetVehicleOperation(models.Model):
    _name = 'fleet.vehicle.operation'
    _description = 'Fleet Vehicles Operation'

    name = fields.Char(string='Operation Types Name', required=True, translate=True)
    color = fields.Integer(string='Color')
    move_type = fields.Selection([('outgoing', 'Customers'), ('incoming', 'Return'),
                                  ('internal', 'Internal')], string='Type of Operation',
                                 required=True, default='outgoing')
    source_location = fields.Many2one('fleet.vehicle.location', string='Source Location')
    destination_location = fields.Many2one('fleet.vehicle.location', string='Destination Location')
    station_id = fields.Many2one('fleet.vehicle.station', string='Auto Station')
    state = fields.Selection([('ready', 'Ready'), ('on_rent', 'On Rent'),
                              ('service', 'Service'), ('done', 'Done')])
    count_operation_ready = fields.Integer(compute='_compute_operation_count')
    count_operation_on_rent = fields.Integer(compute='_compute_operation_count')
    count_operation_service = fields.Integer(compute='_compute_operation_count')
    operation_type_id = fields.Many2one('fleet.vehicle.operation', string='Operation Type')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)

    def _compute_operation_count(self):
        fleet_vehicle_move_obj = self.env['fleet.vehicle.move']
        for each in self:
            ready_state = fleet_vehicle_move_obj.search([('state', 'in', ['ready', 'partial']),
                                                         ('station_id', '=', each.station_id.id),
                                                         ('move_type', '=', each.move_type)])
            each.count_operation_ready = len(ready_state)
            on_rent_state = fleet_vehicle_move_obj.search([('state', '=', 'on_rent'),
                                                           ('station_id', '=', each.station_id.id),
                                                           ('move_type', '=', each.move_type)])
            each.count_operation_on_rent = len(on_rent_state)
            service_state = fleet_vehicle_move_obj.search([('state', '=', 'service'),
                                                           ('station_id', '=', each.station_id.id),
                                                           ('move_type', '=', each.move_type)])
            each.count_operation_service = len(service_state)

    def get_action_operation(self):
        if self.move_type == 'outgoing':
            state = ['ready', 'partial']
        if self.move_type == 'incoming':
            state = ['on_rent']
        if self.move_type == 'internal':
            state = ['service']
        action_id = self.env.ref('aspl_vehicle_rental.action_fleet_vehicle_move').read()[0]
        action_id['context'] = {'default_move_type': self.move_type}
        action_id['domain'] = [('state', 'in', state), ('move_type', '=',  self.move_type),
                               ('station_id', 'in', self.station_id.ids)]
        return action_id


class FleetVehicleLogs(models.Model):
    _name = 'fleet.vehicle.logs'
    _description = 'Fleet Vehicles Logs'
    _rec_name = 'vehicle_id'

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle')
    customer_id = fields.Many2one('res.partner', string='Customer')
    odometer = fields.Float(string='Odometer Value')
    odometer_unit = fields.Selection([('kilometers', 'Kilometer'), ('miles', 'Miles')], string='Unit')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
