# -*- coding: utf-8 -*-
###################################################################################
#    A part of OpenHRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2018-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author: Jesni Banu (<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################
from datetime import datetime, time, date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from lxml import etree
from odoo.addons.base.models.res_partner import _tz_get

MAX_RECURRENT_EVENT = 720

RRULE_TYPE_SELECTION = [
    ('daily', 'Days'),
    ('weekly', 'Weeks'),
    ('monthly', 'Months'),
    ('yearly', 'Years'),
]

class HrAnnouncementTable(models.Model):
    _name = 'hr.announcement'
    _description = 'HR Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    sequence = fields.Integer(string="Sequence", default=10)
    name = fields.Char(string='Code No:', help="Sequence Number of the Announcement")
    announcement_reason = fields.Text(string='Title', states={'draft': [('readonly', False)]}, required=True,
                                      readonly=True, help="Announcement Subject")
    # state = fields.Selection([('draft', 'Draft'), ('to_approve', 'Waiting For Approval'),
    #                           ('approved', 'Approved'), ('rejected', 'Refused'), ('expired', 'Expired')],
    #                          string='Status', default='draft',
    #                          track_visibility='always')
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('expired', 'Expired')],
                             string='Status', default='draft',
                             tracking=True)
    requested_date = fields.Date(string='Requested Date', default=datetime.now().strftime('%Y-%m-%d'),
                                 help="Create Date of Record")
    attachment_id = fields.Many2many('ir.attachment', 'doc_warning_rel', 'doc_id', 'attach_id4',
                                     string="Attachment", help='You can attach the copy of your Letter')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, readonly=True,
                                 help="Login user Company")
    is_announcement = fields.Boolean(string='Is general Announcement?',
                                     help="To set Announcement as general announcement")
    announcement_type = fields.Selection(
        [('employee', 'By Employee'), ('department', 'By Department'), ('job_position', 'By Job Position')])
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_announcements', 'announcement', 'employee',
                                    string='Employees', help="Employee's which want to see this announcement")
    department_ids = fields.Many2many('hr.department', 'hr_department_announcements', 'announcement', 'department',
                                      string='Departments', help="Department's which want to see this announcement")
    position_ids = fields.Many2many('hr.job', 'hr_job_position_announcements', 'announcement', 'job_position',
                                    string='Job Positions', help="Job Position's which want to see this announcement")
    announcement = fields.Html(string='Letter', states={'draft': [('readonly', False)]}, readonly=True,
                               help="Announcement Content")
    date_start = fields.Datetime(string='Start Date', default=datetime.now().strftime('%Y-%m-%d'), required=True, help="Start date of "
                                                                                                   "announcement want"
                                                                                                   " to see")
    date_end = fields.Datetime(string='End Date', default=datetime.now().strftime('%Y-%m-%d'), required=True, help="End date of "
                                                                                               "announcement want too"
                                                                                               " see")
    email_employee_ids = fields.Many2many('hr.employee', 'email_employees_list', string='Get Employees Email Details')

    recurrency = fields.Boolean('Recurrent', help="Recurrent Announcement")
    interval = fields.Integer(
        string='Repeat Every', readonly=False,
        help="Repeat every (Days/Week/Month/Year)", default=1)
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence',
                                  help="Let the event automatically repeat at that interval",
                                  readonly=False, default='weekly')
    event_tz = fields.Selection(
        _tz_get, string='Timezone', readonly=False)
    count = fields.Integer(
        string='Repeat', help="Repeat x times", readonly=False, default=1)
    is_hr_manager = fields.Boolean(compute='_compute_hr_manager')
    parent_id = fields.Many2one('hr.announcement', string="Parent")
    child_ids = fields.One2many('hr.announcement', 'parent_id', 'Child Announcement')
    
    @api.depends('announcement_type')
    def _compute_hr_manager(self):
        for record in self:
            if record.announcement_type == 'department':
                if self.env.user.has_group('hr_reward_warning.group_hr_reward_warning_hr_manager'):
                    record.is_hr_manager = True
                else:
                    record.is_hr_manager = False
            else:
                record.is_hr_manager = False

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(HrAnnouncementTable, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if  self.env.user.has_group('hr_reward_warning.group_hr_reward_warning_department_leader') or self.env.user.has_group('hr_reward_warning.group_hr_reward_warning_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        
        return res

    def get_email_emp_list(self):
        for rec in self:
            if rec.is_announcement:
                if self.env.user.has_group('hr_reward_warning.group_hr_reward_warning_department_leader') and not self.env.user.has_group('hr_reward_warning.group_hr_reward_warning_hr_manager'):
                    department_leader = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
                    rec.email_employee_ids = self.env['hr.employee'].search([('department_id', '=', department_leader.department_id.id)])
                    rec.announcement_type = False
                else:
                    rec.email_employee_ids = self.env['hr.employee'].search([])
                    rec.announcement_type = False
            elif rec.announcement_type == 'employee':
                rec.email_employee_ids = rec.employee_ids
            elif rec.announcement_type == 'department':
                rec.email_employee_ids = self.env['hr.employee'].search(
                    [('department_id', 'in', rec.department_ids.ids)])
            elif rec.announcement_type == 'job_position':
                rec.email_employee_ids = self.env['hr.employee'].search([('job_id', 'in', rec.position_ids.ids)])
            else:
                rec.email_employee_ids = False

    def get_emp_ids(self, email_employee_ids):
        return str([emp.work_email for emp in email_employee_ids]).replace('[', '').replace(']', '').replace("'", '')

    def get_emp_name(self, email_employee_ids):
        return str([emp_name.name for emp_name in email_employee_ids]).replace('[', '').replace(']', '').replace("'", '')

    def get_dept_name(self, department_ids):
        return str([dept_name.name for dept_name in department_ids]).replace('[', '').replace(']', '').replace("'", '')

    def get_job_name(self, position_ids):
        return str([job_name.name for job_name in position_ids]).replace('[', '').replace(']', '').replace("'", '')

    # def reject(self):
    #     self.state = 'rejected'

    # def approve(self):
    #     template_id = self.env.ref('hr_reward_warning.email_template_announcement')
    #     template_id.sudo().send_mail(self.id, force_send=True)
    #     self.state = 'approved'

    # def sent(self):
    #     self.get_email_emp_list()
    #     self.state = 'to_approve'

    @api.constrains('date_start', 'date_end')
    def validation(self):
        if self.date_start > self.date_end:
            raise ValidationError("Start date must be less than End Date")


    @api.model
    def create(self, vals):
        if vals.get('is_announcement'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.announcement.general')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('hr.announcement')
        return super(HrAnnouncementTable, self).create(vals)

    def action_cron_running(self):
        announce = self.search([('state', '=', 'draft')])
        now_date = datetime.now()
        for res in announce:
            if now_date >= res.date_start and now_date <= res.date_end:
                res.write({
                    'state': 'submitted'
                })

    def get_expiry_state(self):
        """
        Function is used for Expiring Announcement based on expiry date
        it activate from the crone job.

        """
        now = datetime.now()
        ann_obj = self.search([('state', '!=', 'draft')])
        for recd in ann_obj:
            if recd.date_end < now:
                recd.write({
                    'state': 'expired'
                })

    @api.onchange("announcement_type")
    def onchange_announcement_type(self):
        if self.announcement_type:
            self.employee_ids = False
            self.department_ids = False
            self.position_ids = False
            department_lst = []
            current_employee = self.env['hr.employee'].search([('user_id', '=', self.env.user.id)], limit=1)
            # current_all_employee = self.env['hr.employee'].search([])
            all_department = self.env['hr.department'].search([])
            if not self.env.user.has_group('hr_reward_warning.group_hr_reward_warning_hr_manager'):
                if self.announcement_type == 'employee':
                    domain = {'domain': {'employee_ids': [('department_id', '=', current_employee.department_id.id)]}}
                    return domain
                elif self.announcement_type == 'department':
                    department_lst.append(current_employee.department_id.id)
                    self.department_ids = [(6, 0, department_lst)]
                elif self.announcement_type == 'job_position':
                    domain = {'domain': {'position_ids': [('department_id', '=', current_employee.department_id.id)]}}
                    return domain
            # else:
            #     if self.announcement_type == 'department':
            #         for data_depart in all_department:
            #             department_lst.append(data_depart.id)
            #         self.department_ids = [(6, 0, department_lst)]

    @api.constrains('recurrency','count')
    def onchange_recurrence_count(self):
        if self.recurrency:
            if self.count > MAX_RECURRENT_EVENT:
                raise ValidationError("Max Number of repetitions is 720!")

    @api.constrains('recurrency','count')
    def onchange_recurrence_count(self):
        if self.recurrency:
            if self.count > MAX_RECURRENT_EVENT:
                raise ValidationError("Max Number of repetitions is 720!")

    def submit(self):
        self.get_email_emp_list()
        template_id = self.env.ref('hr_reward_warning.email_template_announcement')
        if self.attachment_id:
            template_id.attachment_ids = [(4, id) for id in self.attachment_id.ids]
        template_id.sudo().send_mail(self.id, force_send=True)
        self.state = 'submitted'

    def compute_next_date(self, date, period, interval):
        if period == 'daily':
            date += relativedelta(days=interval)
        elif period == 'weekly':
            date += relativedelta(weeks=interval)
        elif period == 'monthly':
            date += relativedelta(months=interval)
        elif period == 'yearly':
            date += relativedelta(years=interval)
        return date

    def action_create_recurrence(self):
        recurrence_ids = self.env['hr.announcement']
        announce = self.search([('state', '=', 'expired'),('parent_id', '=', False)])
        for rec in announce:
            if rec.recurrency:
                count = min(rec.count, MAX_RECURRENT_EVENT)
                count_child = len(rec.child_ids)
                child_ids = rec.child_ids.filtered(lambda l: l.state == "expired").sorted(key="id")[-1:]
                if count_child > 0 and not child_ids:
                    continue
                elif count_child > 0 and child_ids:
                    date_begin = child_ids.date_start
                    date_begin_time = child_ids.date_start.time()
                    date_end = child_ids.date_end
                else:
                    date_begin = rec.date_start
                    date_begin_time = rec.date_start.time()
                    date_end = rec.date_end
                if count_child < count:
                    start_date = date_begin
                    end_date = date_end
                    diff = (end_date.date() - start_date.date()).days
                    date_begin = self.compute_next_date(end_date, rec.rrule_type, rec.interval)
                    ends_date = date_begin + relativedelta(days=diff)
                    date_end = ends_date
                    date_begin = datetime.combine(date_begin, date_begin_time)
                    vals = {
                        'parent_id': rec.id,
                        'attachment_id': rec.attachment_id.ids or [],
                        'is_announcement': rec.is_announcement,
                        'announcement_reason': rec.announcement_reason,
                        'announcement_type': rec.announcement_type,
                        'employee_ids': rec.employee_ids.ids or [],
                        'department_ids': rec.department_ids.ids or [],
                        'position_ids': rec.position_ids.ids or [],
                        'announcement': rec.announcement,
                        'date_start': date_begin,
                        'date_end': date_end,
                        'email_employee_ids': rec.email_employee_ids.ids or False,
                    }
                    recurrence_ids.create(vals)
    
    def set_to_draft(self):
        self.state = 'draft'