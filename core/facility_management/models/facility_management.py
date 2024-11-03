# -*- encoding: utf-8 -*-

from odoo import api, fields, models
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import calendar

class FacilityActivity(models.Model):
    _name = 'facility.activity'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Facility Activity'
    _order = 'id desc'

    READONLYSTATES = {'done': [('readonly', True)]}

    name = fields.Char(size=256, string='Sequence', states=READONLYSTATES)
    activity_name = fields.Char('Activity Name', required="True", states=READONLYSTATES)
    date_activity = fields.Date('Date', states=READONLYSTATES)
    user_id = fields.Many2one('res.users','Assigned To', help="Name of the reviewer who is Assigned the Activity", ondelete="restrict", states=READONLYSTATES)
    reviewer_id = fields.Many2one('res.users','Reviewer', help="Name of the reviewer who is reviewing the Activity", ondelete="restrict", states=READONLYSTATES)
    date_review = fields.Date('Review Date', readonly="True", states=READONLYSTATES)
    state = fields.Selection([
        ('draft','Draft'),
        ('done','Done')], 'Status', default="draft", tracking=1) 
    remark = fields.Text('Remark', states=READONLYSTATES)

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('facility.activity') or ''
        return super(FacilityActivity, self).create(values)

    def action_done(self):
        self.date_review = fields.Date.today()
        self.reviewer_id =  self.env.user.id
        self.state = 'done'

    def unlink(self):
        for rec in self:
            if rec.state=='done':
                raise UserError(_('You cannot delete an record which is not draft or cancelled.'))
        return super(FacilityActivity, self).unlink()


class FacilityMaster(models.Model):
    _name = 'facility.master'
    _description = "Facility Master"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    READONLYSTATES = {'running': [('readonly', True)], 'done': [('readonly', True)], 'cancel': [('readonly', True)]}

    name = fields.Char(string='Sequence', states=READONLYSTATES)
    facility_name = fields.Char('Name', required="True", states=READONLYSTATES)
    reviewer_id = fields.Many2one('res.users','Reviewer', 
        help="Name of the reviewer who is reviewing the task", ondelete="restrict", states=READONLYSTATES)
    recurring_type = fields.Selection([
        ('daily', 'Day(s)'),
        ('weekly', 'Week(s)'),
        ('monthly', 'Month(s)'),
        ('yearly', 'Year(s)'), ], default="daily", required=True, string='Recurring Period', states=READONLYSTATES)
    recurring_interval = fields.Integer(string="Repeat Every", default=1, required=True, states=READONLYSTATES)
    user_id = fields.Many2one('res.users','Responsible', states=READONLYSTATES, 
        help="Name of the person who is responsible for the task", ondelete="restrict")
    start_date = fields.Date('Start Date', states=READONLYSTATES)
    end_date = fields.Date('End Date', states=READONLYSTATES)
    next_execution_date = fields.Date('Next Execution Date', states=READONLYSTATES)
    state = fields.Selection([
        ('draft','Draft'),
        ('running','Running'),
        ('done','Done'),
        ('cancel','Cancel')], 'Status', default="draft", tracking=1, states=READONLYSTATES)
    remark = fields.Text('Remark', states=READONLYSTATES)

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('facility.master') or ''
        return super(FacilityMaster, self).create(values) 

    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel'):
                raise UserError(_('You cannot delete an record which is not draft or cancelled.'))
        return super(FacilityMaster, self).unlink()

    def action_running(self):
        self.state = 'running'

    def action_cancel(self):
        self.state = 'cancel'

    def action_done(self):
        self.state = 'done'

    @api.model
    def create_facility_activity(self):
        ActivityObj = self.env['facility.activity']
        master_data = self.search([
            ('start_date', '<=', fields.date.today()), '|',
            ('end_date', '>', fields.date.today()), ('end_date', '=', False),
            ('state', '=', 'running'),
            '|', ('next_execution_date','=',False),
                ('next_execution_date','=',fields.date.today())
            ])
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        for master in master_data:
            next_date = master.next_execution_date or master.start_date
            ActivityObj.create({
                'activity_name': master.facility_name,
                'date_activity': next_date,
                'user_id': master.user_id.id,
                'reviewer_id': master.reviewer_id.id
            })
            rule, interval = master.recurring_type, master.recurring_interval
            new_date = next_date + relativedelta(**{periods[rule]: interval})
            master.write({'next_execution_date': new_date})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: