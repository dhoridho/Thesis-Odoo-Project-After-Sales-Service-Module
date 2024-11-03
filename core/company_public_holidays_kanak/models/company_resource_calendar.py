# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import datetime
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, Warning
from lxml import etree



class CompanyResourceCalendar(models.Model):
    _name = 'company.resource.calendar'
    _description = 'Company Resource Calendar'
    _inherit = ['mail.thread']

    def _compute_selection(self):
        flag = 0
        year_list = []
        year = datetime.datetime.now().year
        while flag <= 10:
            year_list.append((str(year), str(year)))
            flag += 1
            year += 1
        return year_list

    name = fields.Char('Name', required=1)
    company_global_leave_ids = fields.One2many(
        'company.resource.calendar.leaves', 'company_calendar_id', string='Company Global Leaves')
    employee_id = fields.Many2one('hr.employee', string='Employee')
    year = fields.Datetime()
    year_list = fields.Selection(selection=lambda self: self._compute_selection())
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed')], default="draft", string="States")
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(CompanyResourceCalendar, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(CompanyResourceCalendar, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(CompanyResourceCalendar, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
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

    @api.constrains('company_global_leave_ids')
    def _check_exist_dates(self):
        exist_product_list = []
        for global_leaves in self:
            for line in global_leaves.company_global_leave_ids:
                if datetime.datetime.strftime(line.date_from, "%Y-%m-%d") in exist_product_list:
                    raise ValidationError(_('You can not Add Twice Same Date Public Holiday'))
                exist_product_list.append(datetime.datetime.strftime(line.date_from, "%Y-%m-%d"))

    def action_public_holiday_send(self):
        self.ensure_one()
        template = self.env.ref('company_public_holidays_kanak.email_template_company_public_holidays', False)
        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        employee_partner = self.env['hr.employee'].search([]).mapped('user_id').mapped('partner_id')
        ctx = dict(
            default_model='company.resource.calendar',
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='mass_mail',
            user_email=self.env.user.email,
            default_partner_ids=[(6, 0, employee_partner.ids)]
        )
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx
        }

    def action_holiday_update_calendar(self):
        public_holiday = []
        Calendar = self.env['calendar.event']
        start_date = date(int(self.year_list), 1, 1)
        end_date = date(int(self.year_list), 12, 31)
        query_start_date = "'" + str(start_date) + "'"
        query_end_date = "'" + str(end_date) + "'"
        self.env.cr.execute("""delete from
                                    employee_working_schedule_calendar where is_holiday=True and date_start between 
                                    %s and %s""" % (
            query_start_date, query_end_date))
        self.env.cr.execute("""delete from
                                            calendar_event where is_holiday=True and start between 
                                            %s and %s""" % (
            query_start_date, query_end_date))
        for comp_global_leave in self.company_global_leave_ids:
            public_holiday.append({
                'name': "Holiday" + "/" + comp_global_leave.name,
                'start': comp_global_leave.date_from,
                'stop': comp_global_leave.date_to,
                'is_holiday': True,
                'categ_ids': [(6, 0, [self.env.ref('company_public_holidays_kanak.categ_meet6').id])]
            })
            start = comp_global_leave.date_from
            end = comp_global_leave.date_to
            while start <= end:
                leaves_exist = self.env['employee.working.schedule.calendar'].search(
                    [('date_start', '=', start), ('is_holiday', '=', True)])
                if not leaves_exist:
                    self.env['employee.working.schedule.calendar'].create({
                        'employee_id': False,
                        'contract_id': False,
                        'department_id': False,
                        'working_hours': False,
                        'dayofweek': str(start.weekday()),
                        'date_start': start,
                        'date_end': start,
                        'hour_from': 0.01,
                        'hour_to': 23.99,
                        'is_holiday': True,
                        'holiday_remark': comp_global_leave.name,
                    })
                start += relativedelta(days=1)
        for holiday in public_holiday:
            existing_calender = Calendar.search([('start', '=', holiday['start'])])
            if not existing_calender:
                Calendar.create(holiday)

    def action_confirm(self):
        for rec in self:
            rec.company_global_leave_ids.update_calender_while_confirm()
            rec.write({'state': 'confirmed'})

    def unlink(self):
        for each in self:
            if each.state == 'confirmed':
                raise Warning('Unable to delete if status = “Confirmed”')
            return super(CompanyResourceCalendar, each).unlink()


class CompanyResourceCalendarLeaves(models.Model):
    _name = 'company.resource.calendar.leaves'
    _description = 'Company Resouce Calendar Leaves'

    name = fields.Char('Reason')
    company_calendar_id = fields.Many2one('company.resource.calendar', 'Working Hours')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)

    def write(self, values):
        if self.company_calendar_id.state== 'confirmed':
            resource_calendar = self.env['resource.calendar.leaves'].search(
                [('company_res_calendar_leaves_id', '=', self.id)])
            resource_calendar.write(values)
        res = super(CompanyResourceCalendarLeaves, self).write(values)
        return res

    def update_calender_while_confirm(self):
        resource_calendar = self.env['resource.calendar'].search([])
        for comp_global_leave in self:
            res_cal_leaves_vals = {
                'name': comp_global_leave.name,
                'date_from': comp_global_leave.date_from,
                'date_to': comp_global_leave.date_to,
                'company_res_calendar_leaves_id': comp_global_leave.id
            }
            for calendar in resource_calendar:
                calendar.global_leave_ids = [(0, 0, res_cal_leaves_vals)]

    def unlink(self):
        resource_calendar = self.env['resource.calendar.leaves'].search(
            [('company_res_calendar_leaves_id', '=', self.id)])
        resource_calendar.unlink()
        res = super(CompanyResourceCalendarLeaves, self).unlink()
        return res


class ResourceCalendarLeaves(models.Model):
    _inherit = "resource.calendar.leaves"

    company_res_calendar_leaves_id = fields.Many2one('company.resource.calendar.leaves',
                                                     string='Company Resouce Calendar')


class MailComposer(models.TransientModel):
    _inherit = 'mail.compose.message'

    employee_ids = fields.Many2many(
        'hr.employee', 'mail_compose_message_hr_employee_rel', 'wizard_id', 'employee_id', 'Employee')


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_holiday = fields.Boolean(string="Is holiday", default=False)
