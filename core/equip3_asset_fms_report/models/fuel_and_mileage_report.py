# -*- coding: utf-8 -*-
# Part of CoderlabTechnology. See LICENSE file for full copyright and licensing details.

import re
from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.osv.expression import AND, expression

class FuelandMileageReport(models.Model):
    _name = 'fuel.and.mileage.report'
    _description = "Fuel and Mileage Report"
    _auto = False
    
    asset = fields.Char(string="Asset")
    serial_no = fields.Char('Serial Number')
    current_odometer = fields.Float('Current Odometer ( KM )')
    current_hourmeter = fields.Float('Current Hour Meter ( Hour )')
    current_fuel = fields.Float('Current Fuel ( Liter )')
    cummulative_odometer = fields.Float('Cummulative Odometer ( KM )')
    cummulative_hourmeter = fields.Float('Cummulative Hour Meter ( Hour )')
    cummulative_fuel = fields.Float('Cummulative Fuel ( Liter )')
    average_odometer = fields.Float('Average Odometer ( L/KM )')
    average_hourmeter = fields.Float('Average Hour Meter ( L / Hour )')

    @property
    def _table_query(self):
        query =  '%s %s %s' % (self._select(), self._from(), self._group_by())
        print(query)
        return query

    def _select(self):
        select_str = """
            SELECT
                coalesce(min(me.id)) as id,
                me.name as asset, 
                me.serial_no as serial_no,
                sum(xx.amount) as current_odometer, 
                sum(xx.amount2)as current_hourmeter, 
                sum(xx.amount3) as current_fuel,
                sum(xx.amount5) as cummulative_odometer, 
                sum(xx.amount6) as cummulative_hourmeter, 
                sum(xx.amount4) as cummulative_fuel,
                case when sum(xx.amount4)=0 and sum(xx.amount5)=0 then 0
                        when sum(xx.amount4)>0 and sum(xx.amount5)=0 then 0
                        when sum(xx.amount4)=0 and sum(xx.amount5)>0 then 0
                        else sum(xx.amount4)/sum(xx.amount5) end as average_odometer,
                case when sum(xx.amount4)=0 and sum(xx.amount6)=0 then 0
                        when sum(xx.amount4)>0 and sum(xx.amount6)=0 then 0
                        when sum(xx.amount4)=0 and sum(xx.amount6)>0 then 0
                        else sum(xx.amount4)/sum(xx.amount6) end as average_hourmeter
        """ 
        return select_str

    def _from(self):
        from_str = """
            FROM
            (
            (SELECT mv.maintenance_vehicle, SUM(mv.value) AS amount, 0 amount2, 0 amount3,0 amount4,
                    SUM (mv.value) FILTER (WHERE mv.value > 0) as amount5, 0 amount6
            FROM maintenance_vehicle as mv
            GROUP BY mv.maintenance_vehicle)
            UNION
            (SELECT mhm.maintenance_asset,0 amount, SUM(mhm.value) AS amount2, 0 amount3,0 amount4,
                    0 amount5, SUM (mhm.value) FILTER (WHERE mhm.value > 0) as amount6
            FROM maintenance_hour_meter as mhm
            GROUP BY mhm.maintenance_asset)
            UNION
            (SELECT p.vehicle,0 amount, 0 amount2, p.current_fuel,0 amount4, 0 amount5, 0 amount6
            FROM
                (SELECT distinct vehicle, max(create_date) AS createon
                FROM maintenance_fuel_logs
                GROUP BY vehicle) AS mx 
                JOIN maintenance_fuel_logs p ON
                    mx.vehicle = p.vehicle AND mx.createon = p.create_date
            ORDER BY
                id)
            UNION
            (SELECT mfl.vehicle,0 amount,0 AS amount2, 0 amount3, sum(mfl.liter) amount4, 0 amount5, 0 amount6
            FROM maintenance_fuel_logs as mfl
            GROUP BY mfl.vehicle)
            )
            as xx 
            left join maintenance_equipment as me on xx.maintenance_vehicle = me.id
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY
                me.id,
                me.serial_no
        """
        return group_by_str
