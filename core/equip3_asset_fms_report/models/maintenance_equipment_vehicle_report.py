# -*- coding: utf-8 -*-
# Part of CoderlabTechnology. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.osv.expression import AND, expression

class MaintenanceEquipmentVehicleReport(models.Model):
    _name = 'maintenance.equipment.vehicle.report'
    _description = "Maintenance Equipment Vehicle Report"
    _auto = False

    category_id = fields.Many2one('maintenance.equipment.category', string="Vehicle Category")
    fac_area = fields.Many2one('maintenance.facilities.area', string="Facilities Area")
    maintenance_work_order = fields.Many2one('maintenance.work.order', string="Maintenance Work Order")
    maintenance_repair_order = fields.Many2one('maintenance.repair.order', string="Maintenance Repair Order")
    name = fields.Char('Vehicle Name', required=True, translate=True)
    driver_1 = fields.Many2one('res.partner', string="Driver 1")
    driver_2 = fields.Many2one('res.partner', string="Driver 2")
    chassis_number = fields.Char(string="Chassis Number")
    engine_number = fields.Char(string="Engine Number")
    fuel_type = fields.Many2one('product.product', string="Fuel Type")
    horsepower = fields.Integer(string="Horsepower")
    manufacture_year = fields.Integer(string="Manufacture Year")
    model_year = fields.Integer(string="Model Year")
    transmission = fields.Selection([('manual', 'Manual'), ('automatic', 'Automatic')], string="Transmission")
    amount_total_mwo = fields.Float(string="Total Price MWO")
    amount_total_mro = fields.Float(string="Total Price MRO")

    @property
    def _table_query(self):
        query =  '%s %s %s %s' % (self._select(), self._from(), self._where(), self._group_by())
        return query

    def _select(self):
        select_str = """
            SELECT
                min (me.id) as id,
                me.category_id as category_id,
                me.chassis_number as chassis_number,
                me.driver_1 as driver_1,
                me.driver_2 as driver_2,
                me.engine_number as engine_number,
                me.name as name,
                me.fac_area as fac_area,
                me.fuel_type as fuel_type,
                me.horsepower as horsepower,
                mwo.id as maintenance_work_order,
                mro.id as maintenance_repair_order,
                me.manufacture_year as manufacture_year,
                me.model_year as model_year,
                me.transmission as transmission,
                mwo.amount_total as amount_total_mwo,
                mro.amount_total as amount_total_mro
        """
        return select_str

    def _from(self):
        from_str = """
            FROM
            maintenance_equipment me
            left join plan_task_check_list ptcl on ptcl.equipment_id=me.id
            left join maintenance_work_order mwo on mwo.id=ptcl.maintenance_wo_id
            left join maintenance_repair_order mro on mro.work_order_id=mwo.id

        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                me.category_id,
                me.name,
                me.chassis_number,
                me.driver_1,
                me.driver_2,
                me.engine_number,
                me.fac_area,
                me.fuel_type,
                me.horsepower,
                mro.id,
                mwo.id,
                me.manufacture_year,
                me.model_year,
                me.transmission,
                mwo.amount_total,
                mro.amount_total
        """
        return group_by_str

    def _where(self):
        where_str = """
            WHERE
                me.vehicle_checkbox=true
        """
        return where_str
