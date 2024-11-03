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

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError, Warning
from dateutil import relativedelta


class VehicleBooking(models.Model):
    _name = 'fleet.vehicle.booking'
    _rec_name = "book_number"
    _description = "Book"

    book_number = fields.Char(string='Book Number')
    vehicle_type_id = fields.Many2one('fleet.vehicle.type', string='Type', require=True)
    from_date = fields.Datetime(string='From Date')
    to_date = fields.Datetime(string='To Date')
    ac_require = fields.Boolean(string='Ac Require?', default=False)
    fleet_vehicle_ids = fields.One2many('fleet.vehicle', 'vehicle_book_id', string="Available Vehicle")
    is_search = fields.Boolean(string='Is Search', default=False)
    unit_selection = fields.Selection([('per_day', 'Day'), ('per_km', 'K/M')], default="per_day", string="Unit")
    total_days = fields.Float(string='Total Days', )
    total_hours = fields.Char(string='Hours')
    total_km = fields.Float(string='Total K/m', )
    vehicle_class = fields.Many2one('vehicle.class', string='Vehicle Type', require=True)
    is_carrier = fields.Boolean(string='Carrier Require?')
    extra_charges = fields.Monetary(string='Extra Charges')
    sub_total = fields.Monetary(string='Sub Total(Exclusive Tax)')
    total = fields.Monetary(string='Total')
    fuel_type = fields.Many2one('fuel.type', required=True, string='Fuel Type')
    station_id = fields.Many2one('fleet.vehicle.station', required=True, string='Auto Station')
    currency_id = fields.Many2one('res.currency',
                                  default=lambda self: self.env.user.company_id.currency_id,
                                  string='Currency')

    @api.constrains('from_date', 'to_date')
    def check_date(self):
        if date.strftime(datetime.strptime(str(self.from_date), '%Y-%m-%d %H:%M:%S'), '%Y-%m-%d') < str(date.today()):
            raise Warning(_('You cannot enter past date'))
        if date.strftime(datetime.strptime(str(self.to_date), '%Y-%m-%d %H:%M:%S'), '%Y-%m-%d') < str(date.today()):
            raise Warning(_('You cannot enter past date'))

    @api.model
    def create(self, vals):
        vals.update({'book_number': self.env['ir.sequence'].next_by_code('fleet_booking') or _('Vehicle Booking')})
        return super(VehicleBooking, self).create(vals)

    @api.onchange('unit_selection', 'fleet_vehicle_ids', 'total_days', 'total_km', 'ac_require', 'is_carrier',
                  'extra_charges')
    def rate_onchange(self):
        if self.unit_selection:
            self.sub_total = 0
            self.total = 0;
            self.extra_charges = 0;
            for vehicle in self.fleet_vehicle_ids.filtered(lambda fv: fv.select_vehicle):
                if self.is_carrier:
                    self.extra_charges += vehicle.price_carrier
                if self.unit_selection == 'per_day':
                    if self.ac_require:
                        self.sub_total += vehicle.rate_day_ac * self.total_days
                    else:
                        self.sub_total += vehicle.rate_as_per_day * self.total_days
                else:
                    if self.ac_require:
                        self.sub_total += vehicle.rate_km_ac * self.total_km
                    else:
                        self.sub_total += vehicle.rate_as_per_km * self.total_km
                self.total = self.sub_total + self.extra_charges

    def search_vehicle(self):
        vehicle_id = []

        date_from = datetime.strptime(str(self.from_date), '%Y-%m-%d %H:%M:%S')
        date_to = datetime.strptime(str(self.to_date), '%Y-%m-%d %H:%M:%S')
        difference = relativedelta.relativedelta(date_from, date_to)
        self.env['fleet.vehicle'].search([('select_vehicle', '=', True)]).write({'select_vehicle': False})

        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise ValidationError("To Date must be greater than From date")
            else:
                self.env.cr.execute("""select id from fleet_vehicle where vehicle_type=%s AND auto_station_id=%s AND fuel_type=%s AND id NOT IN
                                        (select vl.vehicle_id from fleet_vehicle_order vo
                                                ,vehicle_order_line vl,fleet_vehicle fv
                                                Where vo.state NOT IN('cancel','close','draft')
                                                AND vo.id=vl.vehicle_order_id
                                                AND (((vo.from_date BETWEEN %s AND %s) OR (vo.to_date BETWEEN %s AND %s))
                                                OR  ((%s BETWEEN vo.from_date AND vo.to_date) OR(%s BETWEEN vo.from_date AND vo.to_date)
                                                ))) """, (
                self.vehicle_type_id.id, self.station_id.id, self.fuel_type.id, self.from_date, self.to_date, self.from_date, self.to_date,
                self.from_date, self.to_date,))
                vehicle_data = self.env.cr.fetchall()
                if vehicle_data:
                    for vehicles in vehicle_data:
                        vehicle_id.append(vehicles[0])
                    return {
                        'view_mode': 'form',
                        'res_model': 'fleet.vehicle.booking',
                        'type': 'ir.actions.act_window',
                        'context': {'default_fleet_vehicle_ids': [(6, 0, vehicle_id)],
                                    'default_from_date': self.from_date,
                                    'default_to_date': self.to_date,
                                    'default_vehicle_type_id': self.vehicle_type_id.id,
                                    'default_station_id': self.station_id.id,
                                    'default_is_search': True,
                                    'default_total_days': abs(difference.days),
                                    'default_vehicle_class': self.vehicle_class.id,
                                    'default_fuel_type': self.fuel_type.id,
                                    'default_ac_require': self.ac_require,
                                    'default_total': self.total,
                                    'default_is_carrier': self.is_carrier,
                                    },
                    }
                else:
                    raise ValidationError("Sorry!!! No any Vehicle Available!!!")

    def book_vehicle(self):
        vehicle = False
        for vehicle_line in self.fleet_vehicle_ids:
            if vehicle_line.select_vehicle:
                vehicle = True
        if vehicle:
            vehicle_order_id = []
            for vehicle in self.fleet_vehicle_ids.filtered(lambda fv: fv.select_vehicle):
                rate_total = 0
                if self.unit_selection == 'per_day':
                    if self.ac_require:
                        rate_total += vehicle.rate_day_ac
                    else:
                        rate_total += vehicle.rate_as_per_day
                else:
                    if self.ac_require:
                        rate_total += vehicle.rate_km_ac
                    else:
                        rate_total += vehicle.rate_as_per_km
                vehicle_order_id.append((0, 0, {'vehicle_id': vehicle.id,
                                                'price_based': self.unit_selection,
                                                'enter_days': self.total_days,
                                                'price': rate_total,
                                                'enter_kms': self.total_km,
                                                # 'odometer_unit':vehicle.odometer,
                                                }
                                         ))
            return {
                'name': "vehicle order",
                'view_mode': 'form',
                'res_model': "fleet.vehicle.order",
                'type': 'ir.actions.act_window',
                'context': {'default_from_date': self.from_date,
                            'default_to_date': self.to_date,
                            'default_vehicle_type_id': self.vehicle_type_id.id,
                            'default_extra_charges': self.extra_charges,
                            'default_vehicle_order_lines_ids': vehicle_order_id,
                            'default_station_id': self.station_id.id
                            },
            }
        else:
            raise Warning(_('First Please Select the Vehicle'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
