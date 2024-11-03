from odoo import models,fields,api,_


class CalendarEventInherit(models.Model):
    _inherit = 'calendar.event'

    # meeting_salesperson_ids = fields.One2many(comodel_name='meetings.salespersons', inverse_name='calendar_event_id', string='Salesperson')
    meeting_salesperson_ids = fields.Many2many(comodel_name='res.users', string='Salesperson', readonly=True)
    
    is_hide_salesperson = fields.Boolean(string='Hide Salesperson', compute="_compute_is_hide_salesperson",store=False)

    dummy_boolean = fields.Boolean("Dummy", compute="set_user_ids", store=True)
    user_ids = fields.Many2many('res.users','user_calendar_rel', 'calendar_id', 'user_id', string="Salesperson")
    mandatory = fields.Boolean("Mandatory")
    partner_attendees_ids = fields.Many2many(
        'res.partner', 'calendar_event_res_partners_rel',
        string='Other Attendees')

    reasons_reschedule = fields.Char('Reasons Reschedule', readonly=True)
    cancelled_reasons = fields.Char('Cancelled Reasons', readonly=True)
    customer_id = fields.Many2one(related='opportunity_id.partner_id')
    is_leader = fields.Boolean("Is Leader", compute="_is_leader")
    state_3 = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ('cancel', 'Cancel')
    ], default='draft', string="State")

    def _is_leader(self):
        for rec in self:
            if self.env.user.my_team_ids:
                rec.is_leader = True
            else:
                rec.is_leader = False

    @api.model
    def _get_public_fields(self):
        return self._get_recurrent_fields() | self._get_time_fields() | self._get_custom_fields() | {
            'id', 'active', 'allday',
            'duration', 'user_id', 'interval',
            'count', 'rrule', 'recurrence_id', 'show_as', 'state'}

    @api.model
    def create(self, vals):
        res = super(CalendarEventInherit, self).create(vals)
        if res.opportunity_id:
            res.opportunity_id.set_due_date_and_missed()
        if res.meeting_salesperson_ids:
            for i in res.meeting_salesperson_ids:
                rec_done_count = rec_cancel_count = rec_reschedule_count = 0
                val = res.opportunity_id.salesperson_lines.filtered(lambda r: r.salesperson_id == i).weightage / 100
                if res.state == 'done':
                    rec_done_count = val
                if res.state == 'cancel':
                    rec_cancel_count = val
                if res.reschedule_count:
                    rec_reschedule_count = val
                self.env['meeting.analysis.report.new'].create({
                    'event_id': res.id,
                    'user_id': i.id,
                    'start': res.start,
                    'duration': res.duration,
                    'meeting_count': val,
                    'reschedule_count': rec_reschedule_count,
                    'done_count': rec_done_count,
                    'cancel_count': rec_cancel_count
                })
        return res

    def write(self, vals):
        rec = super(CalendarEventInherit, self).write(vals)
        for res in self:
            if res.meeting_salesperson_ids:
                for i in res.meeting_salesperson_ids:
                    rec_done_count = rec_cancel_count = rec_reschedule_count = 0
                    val = res.opportunity_id.salesperson_lines.filtered(lambda r: r.salesperson_id == i).weightage / 100
                    if res.state == 'done':
                        rec_done_count =val
                    if res.state == 'cancel':
                        rec_cancel_count = val
                    if res.reschedule_count:
                        rec_reschedule_count = val
                    report_ids = self.env['meeting.analysis.report.new'].search([('event_id', '=', res.id),('user_id','=',i.id)])
                    if report_ids:
                        for report_id in report_ids:
                            report_id.write({
                                'start': res.start,
                                'duration': res.duration,
                                'meeting_count': val,
                                'reschedule_count': rec_reschedule_count,
                                'done_count': rec_done_count,
                                'cancel_count': rec_cancel_count
                            })
        return rec

    @api.onchange('opportunity_id')
    def set_salesperson(self):
        for rec in self:
            if rec.opportunity_id:
                salesperson_ids = []
                for i in rec.opportunity_id.salesperson_lines:
                    salesperson_ids.append(i.salesperson_id.id)
                rec.write({
                    'meeting_salesperson_ids': [(6,0, salesperson_ids)],
                    'team_id': rec.opportunity_id.team_id
                })
            else:
                rec.write({
                    'meeting_salesperson_ids': [(6,0, [])],
                    'team_id': False
                })


    @api.onchange('categ_ids')
    def set_mandatory(self):
        for res in self:
            if res.categ_ids:
                for i in res.categ_ids:
                    if i.leads_meeting:
                        res.mandatory = True
                        break
                    else:
                        res.mandatory = False
            else:
                res.mandatory = False

    @api.depends('partner_ids')
    def set_user_ids(self):
        for res in self:
            res.user_ids = [(6, 0, [])]
            for line in res.partner_ids:
                if line.user_ids:
                    for user in line.user_ids:
                        if user.id not in res.user_ids.ids:
                            res.user_ids = [(4, user.id)]
                            res.dummy_boolean = True

    @api.depends('user_id')
    def _compute_is_hide_salesperson(self):
        for i in self:
            is_multi_salesperson = self.env.user.id in self.env.ref('equip3_crm_operation.group_use_multi_salesperson_on_leads').users.ids
            if is_multi_salesperson:
                i.is_hide_salesperson = True
            else:
                i.is_hide_salesperson = False
        


class MeetingSalesperson(models.Model):
    _name = 'meetings.salespersons'
    _description = 'Meeting Salespersons'

    salesperson_id = fields.Many2one('res.users', string="Salesperson")
    weightage = fields.Float("Weightage")
    status = fields.Selection([
        ("main", "Main Salesperson"),
        ("pairing", "Pairing Salesperson"),
    ], string="Status")
    calendar_event_id = fields.Many2one('calendar.event', ondelete="cascade")

class MeetingType(models.Model):

    _inherit = 'calendar.event.type'

    leads_meeting = fields.Boolean("Leads Meeting")
