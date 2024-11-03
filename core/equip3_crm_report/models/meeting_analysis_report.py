from odoo import tools
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta

class MeetingAnalysisReport(models.Model):
    _name = 'meeting.analysis.report'
    _description = "Meeting Analysis Report"
    _auto = False

    user_id = fields.Many2one('res.users', string="Sales Person")
    start = fields.Datetime(string='Starting at')
    duration = fields.Float(string='Meeting Duration (Hours)')
    meeting_count = fields.Integer(string='On Schedule (Count)')
    reschedule_count = fields.Integer(string='Rescheduled (Count)')
    done_count = fields.Integer(string='Done (Count)')
    cancel_count = fields.Integer(string='Cancelled (Count)')

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        with_ = ("WITH %s" % with_clause) if with_clause else ""

        select_ = """
            min(ce.id) as id,
            ce.user_id as user_id,
            ce.start as start,
            ce.duration_count as duration,
            ce.meeting_count as meeting_count,
            ce.reschedule_count as reschedule_count,
            ce.done_count as done_count,
            ce.cancel_count as cancel_count
        """

        for field in fields.values():
            select_ += field

        from_ = """
            calendar_event ce
        """

        where_ = """
            ce.user_id is not null
        """

        groupby_ = """
            ce.user_id,
            ce.start,
            ce.duration_count,
            ce.meeting_count,
            ce.reschedule_count,
            ce.done_count,
            ce.cancel_count
        """

        return '%s (SELECT %s FROM %s WHERE %s GROUP BY %s)' % (with_, select_, from_, where_, groupby_)

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))


class MeetingAnalysisReportNew(models.Model):
    _name = 'meeting.analysis.report.new'
    _description = "Meeting Analysis Report"

    user_id = fields.Many2one('res.users', string="Sales Person")
    start = fields.Datetime(string='Starting at')
    duration = fields.Float(string='Meeting Duration (Hours)')
    meeting_count = fields.Float(string='On Schedule (Count)')
    reschedule_count = fields.Float(string='Rescheduled (Count)')
    done_count = fields.Float(string='Done (Count)')
    cancel_count = fields.Float(string='Cancelled (Count)')
    event_id = fields.Many2one('calendar.event')
    name = fields.Char(related='event_id.name', string="Subject")
    stop = fields.Datetime(related='event_id.stop', string='End Date')
    partner_ids = fields.Many2many(related='event_id.partner_ids')
    location = fields.Char(related='event_id.location')
    team_id = fields.Many2one(related='event_id.team_id', store=True)

    def init(self):
        self.env['meeting.analysis.report.new'].search([]).unlink()
        calendar = self.env['calendar.event'].search([])
        users = calendar.mapped('meeting_salesperson_ids')
        for user in users:
            calendar_user = self.env['calendar.event'].search([('meeting_salesperson_ids', 'in', user.id)])
            for i in calendar_user:
                # start = calendar_user.mapped('start')[-1]
                # duration = sum(calendar_user.mapped('duration'))
                # meeting_count = len(calendar_user)
                rec_done_count = rec_cancel_count = rec_reschedule_count = 0
                val = i.opportunity_id.salesperson_lines.filtered(lambda r: r.salesperson_id == user).weightage / 100
                if i.state == 'done':
                    rec_done_count =val
                if i.state == 'cancel':
                    rec_cancel_count = val
                if i.reschedule_count:
                    rec_reschedule_count = val
                self.env['meeting.analysis.report.new'].create({
                    'event_id': i.id,
                    'user_id': user.id,
                    'start': i.start,
                    'duration': i.duration,
                    'meeting_count': val,
                    'reschedule_count': rec_reschedule_count,
                    'done_count': rec_done_count,
                    'cancel_count': rec_cancel_count
                })