# -*- coding: utf-8 -*-
from odoo import models, fields, tools, api
from datetime import date
from dateutil.relativedelta import relativedelta


class HrEmployeeAnalysis(models.Model):
    _name = 'hr.employee.analysis'
    _description = "Hr Employee Analysis"
    _auto = False

    department_id = fields.Many2one('hr.department', string='Department', readonly=True)
    job_id = fields.Many2one('hr.job', string='Job Position', readonly=True)
    count_male = fields.Integer(string="Male", group_operator="sum", readonly=True)
    count_female = fields.Integer(string="Female", group_operator="sum", readonly=True)
    count_others = fields.Integer(string="Others", group_operator="sum", readonly=True)
    birth_years = fields.Integer(string="Years of Service", group_operator="avg", readonly=True)
    wage = fields.Float('Wage', group_operator="avg", readonly=True)
    min_salary = fields.Float('Lowest Salary', group_operator="min", readonly=True)
    max_salary = fields.Float('Highest Salary', group_operator="max", readonly=True)
    standard_deviation = fields.Float('Standard Deviation', readonly=True)
    low_average_salary = fields.Float('Low Average Salary', readonly=True)
    high_average_salary = fields.Float('High Average Salary', readonly=True)

    def _query(self):
        select = """
                SELECT
                    ROW_NUMBER () over() as id,
                    emp.department_id AS department_id,
                    emp.job_id AS job_id,
                    count(1) filter (where emp.gender = 'male') AS count_male,
                    count(1) filter (where emp.gender = 'female') AS count_female,
                    count(1) filter (where emp.gender = 'other') AS count_others,
                    avg(emp.birth_years) AS birth_years,
                    avg(con.wage) AS wage,
                    min(con.wage) AS min_salary,
                    max(con.wage) AS max_salary,
                    stddev(con.wage) AS standard_deviation,
                    avg(con.wage) - stddev(con.wage) AS low_average_salary,
                    avg(con.wage) + stddev(con.wage) AS high_average_salary
                    FROM hr_employee emp
                    LEFT JOIN hr_contract con ON (con.employee_id = emp.id)
                WHERE
                    con.state = 'open' 
                GROUP BY
                    emp.department_id,
                    emp.job_id
                """
        return select

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("CREATE OR REPLACE VIEW %s AS (%s)" % (
            self._table, self._query()))
