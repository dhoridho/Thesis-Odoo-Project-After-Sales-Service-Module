# -*- coding: utf-8 -*-
# Part of CoderlabTechnology. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.osv.expression import AND, expression

class MaintenanceEquipmentReport(models.Model):
    _name = 'maintenance.equipment.asset.report'
    _description = "Maintenance Equipment Asset Report"
    _auto = False

    category_id = fields.Many2one('maintenance.equipment.category', string="Asset Category")
    fac_area = fields.Many2one('maintenance.facilities.area', string="Facilities Area")
    maintenance_work_order = fields.Many2one('maintenance.work.order', string="Maintenance Work Order",
    store=True, tracking=True)
    # maintenance_workorder_name = fields.Char(string="Work Order")
    maintenance_repair_order = fields.Many2one('maintenance.repair.order', string="Maintenance Repair Order",
                                               store=True, tracking=True)
    name = fields.Char('Asset Name', required=True, translate=True)
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
                me.name as name,
                me.category_id as category_id,
                me.fac_area as fac_area,
                mwo.id as maintenance_work_order,
                mwo.amount_total as amount_total_mwo,
                mro.id as maintenance_repair_order,
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
                me.fac_area,
                me.name,
                mwo.id,
                mwo.amount_total,
                mro.id,
                mro.amount_total
        """
        return group_by_str

    def _where(self):
        where_str = """ 
            WHERE
                me.vehicle_checkbox=false
        """
        return where_str
