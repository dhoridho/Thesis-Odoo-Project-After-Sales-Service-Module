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
from odoo.exceptions import Warning


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    is_driver = fields.Boolean(string='With Driver')
    vehicle_type = fields.Many2one('fleet.vehicle.type', string="Vehicle Type")
    vehicle_book_id = fields.Many2one('fleet.vehicle.booking', string='Vehicle Book')
    rate_as_per_day = fields.Monetary(string='Rate Per Day')
    rate_day_ac = fields.Monetary(string='Rate Per Day AC')
    is_ac = fields.Boolean(string="AC?", default=False)
    rate_as_per_km = fields.Monetary(string='Rate Per Km')
    rate_km_ac = fields.Monetary(string='Rate Per KM AC')
    select_vehicle = fields.Boolean(string="Select Vehicle", default=False)
    fleet_registration_id = fields.Many2one('fleet.vehicle.order', string="Registration Id")
    current_status = fields.Selection([('available','AVAILABLE'), ('on_rent','ON RENT'), ('workshop','IN WORKSHOP')],
                                      string='Current Status', default='available')
    is_carrier = fields.Boolean(string="Compatible With Carrier?", default=False)
    price_carrier = fields.Monetary(string="Carrier Price")
    fuel_type = fields.Many2one('fuel.type', required=True, string='Fuel Type')
    auto_station_id = fields.Many2one('fleet.vehicle.station', string='Auto Station', required=True)
    maximum_km = fields.Integer(string="Maximum KM")
    vehicle_log_count = fields.Integer(compute="_compute_count")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')

    def _compute_count(self):
        Logs_count = self.env['fleet.vehicle.logs']

        for record in self:
            record.vehicle_log_count = Logs_count.search_count([('vehicle_id', '=', record.id)])

    @api.constrains('vin_sn')
    def check_chassis(self):
        if self.vin_sn:
            check_chassis = self.search([('vin_sn', '=', self.vin_sn)])
            if len(check_chassis) > 1:
                raise Warning('Chassis Number Must be Unique !!!')

    def show_logs_vehicle(self):
        return {
            'name': _('Logs'),
            'res_model': 'fleet.vehicle.logs',
            'views': [([], 'tree'),],
            'type': 'ir.actions.act_window',
            'domain':[('vehicle_id','=',self.id)]
        }

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        vehicle_id = {}
        if self._context.get('from_vehicle_order'):
            from_date = self._context.get('from_date')
            to_date = self._context.get('to_date')
            vehicle_type_id = self._context.get('vehicle_type')
            if from_date and to_date and vehicle_type_id:
               self.env.cr.execute("""select id from fleet_vehicle  where vehicle_type=%s AND id NOT IN
                                    (select vl.vehicle_id  from fleet_vehicle_order vo ,
                                    vehicle_order_line vl Where vo.state NOT IN('cancel','close')
                                    AND vo.id=vl.vehicle_order_id AND (((vo.from_date BETWEEN %s AND %s)
                                    OR (vo.to_date BETWEEN %s AND %s))OR((%s BETWEEN vo.from_date AND vo.to_date)
                                    OR(%s BETWEEN vo.from_date AND vo.to_date)))) """, (vehicle_type_id,from_date, to_date, from_date, to_date, from_date, to_date,));
               vehicles = self.env.cr.dictfetchall()
               vehicle_list = [vehicle['id'] for vehicle in vehicles ]
               return self.browse(vehicle_list).name_get()
            else:
                   raise Warning('Please select From Date and To date and Vehicle Type!!!')
        else:
            return super(FleetVehicle, self).name_search(name, args=args, operator=operator, limit=limit)


class FleetVehicleType(models.Model):
    _name = 'fleet.vehicle.type'
    _description = 'Vehicle Type'

    name = fields.Char(string="Name", require=True)
    type_id = fields.Many2one('vehicle.class', string="Type")

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if self._context.get('from_quick_search'):
            if self._context.get('v_type'):
                 res = self.search([('type_id', '=', self._context.get('v_type'))])
                 return res.name_get()
            else:
               raise Warning('Please select Vehicle Type !!!')
        else:
            return super(FleetVehicleType, self).name_search(name, args=args, operator=operator, limit=limit)


class VehicleClass(models.Model):
    _name = 'vehicle.class'
    _description = 'Vehicle Class'
    _rec_name = 'vehicle_class'

    vehicle_class = fields.Char(string="Type")


class FuelType(models.Model):
    _name = 'fuel.type'
    _description = 'Fuel Type'

    name = fields.Char(string='Type of Fuel')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
