# -*- coding: utf-8 -*-

from odoo import fields, models, tools
from datetime import date
import time
from calendar import monthrange


class HrOvertimeAnalysis(models.Model):
    _name = 'hr.overtime.analysis'
    _auto = False

    employee_id = fields.Many2one('hr.employee', string='Employee')
    overtime_request = fields.Char(string='Overtime Request Number')
    date = fields.Date('Date')
    start_date = fields.Date('Start Date')
    end_date = fields.Date('End Date')
    request_hours = fields.Float('Request Hours')
    actual_id = fields.Many2one('hr.overtime.actual', string='Actual Overtime Number')
    actual_date = fields.Date('Actual Date')
    actual_start_date = fields.Date('Actual Start Date')
    actual_end_date = fields.Date('Actual End Date')
    actual_hours = fields.Float('Actual Hours')
    coefficient_hours = fields.Float('Coefficient Hours')
    overtime_fee = fields.Float('Overtime Fee')

    def _select(self):
        select_str = """
            min(actl.id) as id,actl.employee_id,act.id as actual_id,act.period_start as actual_start_date,
            act.period_end as actual_end_date,actl.date as actual_date,actl.actual_hours,actl.coefficient_hours,
            actl.amount as overtime_fee,req.name as overtime_request,req.period_start as start_date,
            req.period_end as end_date,reql.date,reql.number_of_hours as request_hours"""
        return select_str

    def _from(self):
        from_str = """
                hr_overtime_actual_line actl   
                join hr_overtime_actual act on act.id=actl.actual_id
                left join hr_overtime_request req on req.id=act.overtime_request
                left join hr_overtime_request_line reql on reql.request_id=req.id and reql.date=actl.date
                where act.state='approved'
             """
        return from_str

    def _group_by(self):
        group_by_str = """group by actl.employee_id,act.id,act.period_start,act.period_end,actl.
        date,actl.actual_hours,actl.coefficient_hours,actl.amount,req.id,req.period_start,req.period_end,
        req.total_hours,reql.date,reql.number_of_hours"""
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( SELECT
                   %s
                   FROM %s
                   %s
                   )""" % (self._table, self._select(), self._from(), self._group_by()))