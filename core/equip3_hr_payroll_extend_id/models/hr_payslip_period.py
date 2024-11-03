# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError

class Equip3HrPayslipPeriod(models.Model):
    _name = 'hr.payslip.period'
    _description = 'HR Payslip Period'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Period Name", required=True)
    code = fields.Char(string="Code", required=True)
    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)
    start_period_based_on = fields.Selection([('start_date', 'Start Date'), ('end_date', 'End Date')],
                     'Period Based on', default='', required=True)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')],
                             string='Status')
    payslip_period_ids = fields.One2many('hr.payslip.period.line', 'period_id', states={'closed': [('readonly', True)]})
    is_hide_create_month = fields.Boolean(default=False)
    is_hide_open_period = fields.Boolean(default=True)
    is_hide_close_period = fields.Boolean(default=True)
    overtime_period = fields.Selection([('payslip_period', 'Based on Payslip Period'), ('hr_years', 'HR Years')],
                     'Overtime Period', default='payslip_period')
    hr_years_id = fields.Many2one("hr.years", string="HR Years", domain=[('status','=','open')])
    overtime_period_ids = fields.One2many('payslip.overtime.period.line', 'period_id')
    tax_calculation_method = fields.Selection([('monthly', 'Monthly'), ('average', 'Average')], string="Tax Calculation Method", 
                                              required=True, default=lambda self: self.env["ir.config_parameter"].sudo().get_param('equip3_hr_payroll_extend_id.tax_calculation_method'))
    tax_calculation_schema = fields.Selection([('pph21_ter', 'PPH21 TER'), ('pph21', 'PPH21')], string="Tax Calculation Schema", 
                                              required=True, default=lambda self: self.env["ir.config_parameter"].sudo().get_param('equip3_hr_payroll_extend_id.tax_calculation_schema'))
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(Equip3HrPayslipPeriod, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(Equip3HrPayslipPeriod, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    def unlink(self):
        for record in self:
            if record.state in ('closed', 'open'):
                raise ValidationError("Only Draft status can be deleted")
        data = super(Equip3HrPayslipPeriod, self).unlink()
        return data

    @api.constrains('code')
    def check_code(self):
        for record in self:
            if record.code:
                check_name = self.search([('code', '=', record.code), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("Code must be unique!")

    @api.constrains('name')
    def check_name(self):
        for record in self:
            if record.name:
                check_name = self.search([('name', '=', record.name), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("Period Name must be unique!")

    @api.onchange('start_date', 'end_date')
    def _onchange_date(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError("End Date must be greater than Start Date!")

    @api.onchange('overtime_period')
    def onchange_overtime_period(self):
        if self.overtime_period == 'payslip_period':
            self.hr_years_id = False
            if self.overtime_period_ids:
                remove = []
                for line in self.overtime_period_ids:
                    remove.append((2, line.id))
                self.overtime_period_ids = remove

    @api.onchange('hr_years_id')
    def onchange_hr_years_id(self):
        for record in self:
            if record.hr_years_id:
                if record.overtime_period_ids:
                    remove = []
                    for line in record.overtime_period_ids:
                        remove.append((2, line.id))
                    record.overtime_period_ids = remove
                if record.hr_years_id.year_ids:
                    line = []
                    for rec in record.hr_years_id.year_ids:
                        line.append((0, 0, {'year': rec.year,
                                            'month': rec.month,
                                            'start_period': rec.start_period,
                                            'end_period': rec.end_period,
                                            'period_name': rec.period_name,
                                            'code': rec.code,
                                            'status': rec.status
                                            }))
                    record.overtime_period_ids = line

    def action_create_period(self):
        for period in self:
            period._create_period()
            period.state = 'draft'
            period.is_hide_create_month = True
            period.is_hide_open_period = False
            period.message_post(body=_('Periods Status: Draft'))

    def _create_period(self):
        self.ensure_one()
        obj_period = self.env["hr.payslip.period.line"]
        start_date = datetime.strptime(str(self.start_date), "%Y-%m-%d")
        ends_date = datetime.strptime(str(self.end_date), "%Y-%m-%d")
        while start_date.strftime("%Y-%m-%d") < ends_date.strftime("%Y-%m-%d"):
            end_date = start_date + relativedelta(months=+1, days=-1)

            if end_date.strftime("%Y-%m-%d") > ends_date.strftime("%Y-%m-%d"):
                end_date = ends_date

            if self.start_period_based_on == 'start_date':
                year_date = start_date.strftime("%Y")
                month_date = start_date.strftime("%B")
            elif self.start_period_based_on == 'end_date':
                year_date = end_date.strftime("%Y")
                month_date = end_date.strftime("%B")

            obj_period.create({
                "year": year_date,
                "month": month_date,
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "state": "draft",
                "period_id": self.id,
            })
            start_date = start_date + relativedelta(months=+1)

    def to_open(self):
        for record in self:
            if record.payslip_period_ids:
                data = []
                for line in record.payslip_period_ids:
                    data.append((1, line.id, {'state': 'open'}))
                record.payslip_period_ids = data
            record.state = "open"
            record.is_hide_close_period = False
            record.is_hide_open_period = True
            record.message_post(body=_('Periods Status: Draft -> Open'))

    def to_close(self):
        for record in self:
            if record.payslip_period_ids:
                data = []
                for line in record.payslip_period_ids:
                    data.append((1, line.id, {'state': 'closed', 'is_hide_re_open_line':False}))
                record.payslip_period_ids = data
            record.state = "closed"
            record.is_hide_close_period = True
            record.message_post(body=_('Periods Status: Open -> Closed'))

class Equip3HrPayslipPeriodLine(models.Model):
    _name = 'hr.payslip.period.line'

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % (rec.month)))
        return res

    period_id = fields.Many2one('hr.payslip.period')
    year = fields.Char('Year')
    month = fields.Char("Month")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')], string='Status')
    is_hide_re_open_line = fields.Boolean(default=True)
    is_hide_close_line = fields.Boolean(default=True)

    def re_open(self):
        for rec in self:
            rec.is_hide_re_open_line = True
            rec.is_hide_close_line = False
            rec.state = 'open'

    def to_close(self):
        for rec in self:
            rec.is_hide_re_open_line = False
            rec.is_hide_close_line = True
            rec.state = 'closed'

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        recs = self.search([('month', operator, name)] + args, limit=limit)
        return recs.name_get()

class PayslipOvertimePeriodLine(models.Model):
    _name = 'payslip.overtime.period.line'

    def name_get(self):
        res = []
        for rec in self:
            res.append((rec.id, "%s" % (rec.month)))
        return res
    
    period_id = fields.Many2one('hr.payslip.period')
    year = fields.Char('Year')
    month = fields.Char("Month")
    period_name = fields.Char('Period Name')
    code = fields.Char("Code")
    start_period = fields.Date("Start Of Period")
    end_period = fields.Date("End Of Period")
    status = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')])