# -*- coding: utf-8 -*-

from odoo import api, fields, models, tools
from datetime import date
import time
from calendar import monthrange


class PayrollReportView(models.Model):
    _name = 'hr.payroll.report.view'
    _auto = False

    name = fields.Many2one('hr.employee', string='Employee')
    date_from = fields.Date(string='DateFrom')
    date_to = fields.Date(string='Date To')
    payslip_report_date = fields.Date(string='Payslip Report Date')
    state = fields.Selection([('draft', 'Draft'), ('verify', 'Waiting'), ('done', 'Done'), ('cancel', 'Rejected')],
                             string='Status')
    job_id = fields.Many2one('hr.job', string='Job Title')
    company_id = fields.Many2one('res.company', string='Company')
    department_id = fields.Many2one('hr.department', string='Department')
    rule_name = fields.Many2one('hr.salary.rule.category', string="Rule Category")
    rule_amount = fields.Float(string="Amount")
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    rule_id = fields.Many2one('hr.salary.rule', string="Salary Rule")
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(PayrollReportView, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(PayrollReportView, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def _select(self):
        select_str = """
            min(psl.id),ps.id,ps.number,emp.id as name,dp.id as department_id,jb.id as job_id,cmp.id as company_id,ps.date_from, ps.date_to, ps.state as state ,rl.id as rule_name, 
            psl.total as rule_amount,ps.struct_id as struct_id,rlu.id as rule_id,ps.payslip_report_date"""
        return select_str

    def _from(self):
        from_str = """
                hr_payslip_line psl   
                join hr_payslip ps on ps.id=psl.slip_id
                join hr_salary_rule rlu on rlu.id = psl.salary_rule_id
                join hr_employee emp on ps.employee_id=emp.id
                join hr_salary_rule_category rl on rl.id = psl.category_id
                left join hr_department dp on emp.department_id=dp.id
                left join hr_job jb on emp.job_id=jb.id
                join res_company cmp on cmp.id=ps.company_id
                where rlu.appears_on_report=True and ps.payslip_pesangon is null or rlu.appears_on_report=true and ps.payslip_pesangon=false
             """
        return from_str

    def _group_by(self):
        group_by_str = """group by ps.number,ps.id,emp.id,dp.id,jb.id,cmp.id,ps.date_from,ps.date_to,ps.state,
            psl.total,psl.name,psl.category_id,rl.id,rlu.id,ps.payslip_report_date"""
        return group_by_str

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as ( SELECT
                   %s
                   FROM %s
                   %s
                   )""" % (self._table, self._select(), self._from(), self._group_by()))


