from numpy import record
from odoo import _, api, fields, models
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import calendar
from lxml import etree

class equip3HrYears(models.Model):
    _name = 'hr.years'
    _description = 'HR Years'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('status')
    def compute_state(self):
        for rec in self:
            rec.state = rec.status

    state = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')], compute='compute_state')
    status = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')])
    name = fields.Integer("HR Year", required=True, states={'closed': [('readonly', True)]})
    code = fields.Char("Code")
    start_date = fields.Date(required=True, string="Start Date", states={'closed': [('readonly', True)]})
    end_date = fields.Date(required=True, string="End date", states={'closed': [('readonly', True)]})
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True, states={'closed': [('readonly', True)]})
    year_ids = fields.One2many('hr.years.line', 'year_id', states={'closed': [('readonly', True)]})
    is_hide_create_month = fields.Boolean(default=False)
    is_hide_open_period = fields.Boolean(default=True)
    is_hide_close_period = fields.Boolean(default=True)
    start_period_based_on = fields.Selection([('start_date', 'Start Date'), ('end_date', 'End Date')],
                     'Period Based on', default='', required=True)
    
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(equip3HrYears, self).fields_view_get(
            view_id=view_id, view_type=view_type)

        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
            
        return res


    def unlink(self):
        for record in self:
            if record.status in ('closed', 'open'):
                raise ValidationError("Only Draft status can be deleted")
        data = super(equip3HrYears, self).unlink()
        return data

    @api.onchange('start_date', 'end_date')
    def _onchange_date(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date > record.end_date:
                    raise ValidationError("End Date must be greater than Start Date!")

    @api.constrains('name')
    def check_name(self):
        for record in self:
            if record.name:
                check_name = self.search([('name', '=', record.name), ('id', '!=', record.id)])
                if check_name:
                    raise ValidationError("HR Year must be unique!")

    def diff_month(self, d1, d2):
        return (d1.year - d2.year) * 12 + d1.month - d2.month

    def create_month(self):
        for record in self:
            if not record.start_period_based_on:
                raise ValidationError("Period Based on must be select first!")
            if record.year_ids:
                remove = []
                for line in record.year_ids:
                    remove.append((2, line.id))
                record.year_ids = remove
            start_date = datetime.strptime(str(record.start_date), "%Y-%m-%d")
            end_date = datetime.strptime(str(record.end_date), "%Y-%m-%d")
            line = []
            while start_date.strftime("%Y-%m-%d") < end_date.strftime("%Y-%m-%d"):
                ends_date = start_date + relativedelta(months=+1, days=-1)

                if ends_date.strftime("%Y-%m-%d") > end_date.strftime("%Y-%m-%d"):
                    ends_date = end_date

                if record.start_period_based_on == 'start_date':
                    year_date = start_date.strftime("%Y")
                    month_date = start_date.strftime("%B")
                    month_num = start_date.strftime("%m")
                elif record.start_period_based_on == 'end_date':
                    year_date = ends_date.strftime("%Y")
                    month_date = ends_date.strftime("%B")
                    month_num = ends_date.strftime("%m")

                line.append((0, 0, {'year': year_date,
                                    'month': month_date,
                                    'start_period': start_date.strftime("%Y-%m-%d"),
                                    'end_period': ends_date.strftime("%Y-%m-%d"),
                                    'period_name': f"{month_num}/{year_date}",
                                    'code': f"{month_num}/{year_date}",
                                    'status': "draft"
                                    }))
                start_date = start_date + relativedelta(months=+1)
            record.year_ids = line
            record.status = 'draft'
            record.is_hide_create_month = True
            record.is_hide_open_period = False
            record.message_post(body=f"Periods Status:draft")

    def to_open(self):
        for record in self:
            if record.year_ids:
                data = []
                for line in record.year_ids:
                    data.append((1, line.id, {'status': 'open'}))
                record.year_ids = data
            record.status = "open"
            record.is_hide_open_period = True
            record.is_hide_close_period = False
            record.message_post(body=f"Periods Status:Draft -> Open")

    def to_close(self):
        for record in self:
            if record.year_ids:
                data = []
                for line in record.year_ids:
                    data.append((1, line.id, {'status': 'closed'}))
                record.year_ids = data
            record.status = "closed"
            record.is_hide_close_period = True
            record.message_post(body=f"Periods Status:Open -> Closed")

    def to_re_open(self):
        for record in self:
            if record.year_ids:
                data = []
                for line in record.year_ids:
                    data.append((1, line.id, {'status': 'open'}))
                record.year_ids = data
            record.status = "open"
            record.is_hide_close_period = False
            record.message_post(body=f"Periods Status:Closed -> Open")

class equip3HrYearsLine(models.Model):
    _name = 'hr.years.line'
    year_id = fields.Many2one('hr.years')
    period_name = fields.Char('Period Name')
    code = fields.Char("Code")
    start_period = fields.Date("Start Of Period")
    end_period = fields.Date("End Of Period")
    status = fields.Selection([('draft', 'Draft'), ('open', 'Open'), ('closed', 'Closed')])
    year = fields.Char('Year')
    month = fields.Char("Month")
