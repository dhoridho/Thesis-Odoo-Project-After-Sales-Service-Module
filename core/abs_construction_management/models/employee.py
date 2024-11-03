# -*- coding: utf-8 -*-
#################################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2021-today Ascetic Business Solution <www.asceticbs.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#################################################################################
from odoo import api, fields, models, _

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    driver = fields.Boolean(string = 'Is a Driver')
    vehicle_request_count = fields.Integer(string = 'Vehicle Request', compute = 'compute_vehicle_request_count')

    def compute_vehicle_request_count(self):
        vehicle_request_obj = self.env['vehicle.request']
        for driver in self:
            driver.vehicle_request_count = vehicle_request_obj.search_count([('driver_id', '=', driver.id)])

    def action_view_vehicle_request(self):
        return {
                'name': _('Vehicle Request'),
                'domain': [('driver_id','=',self.id)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'vehicle.request',
                'view_id': False,
                'views': [(self.env.ref('abs_construction_management.view_vehicle_request_menu_tree').id, 'tree'),
                          (self.env.ref('abs_construction_management.view_vehicle_request_menu_form').id, 'form')],
                'type': 'ir.actions.act_window'
               }
