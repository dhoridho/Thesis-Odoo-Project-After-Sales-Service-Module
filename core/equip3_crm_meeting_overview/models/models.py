# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class QuotationAmount(models.Model):
    _name = 'quotation.amount'
    _description = "Quotation Amount"
    _rec_name = 'amount'

    order_id = fields.Many2one('sale.order', string="Quotation")
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=True)
    amount = fields.Monetary("Amount", related='order_id.amount_total',  currency_field='currency_id', store=True)
    state = fields.Selection(related='order_id.state', store=True, readonly=False)

class Lead(models.Model):
    _inherit = 'crm.lead'

    quotation = fields.Selection([
        ("sent", "Sent"),
        ("not_sent", "Not Sent"),
    ], string="Quotation Sent Status")
    final_quotation = fields.Many2one('quotation.amount', string="Final Quotation Amount")
    remark = fields.Char("Remarks")
    cannot_be_quoted = fields.Boolean(string='Cannot be Quoted')
    potential = fields.Boolean(string='Potential')

    def name_get(self):
        res = []
        for rec in self:
            if len(rec.name) > 35:
                name = rec.name[0:35] + "..."
            else:
                name = rec.name
            res.append((rec.id, name))
        return res

    def write(self, vals):
        if 'team_id' in vals and not self.original_team_id:
            vals['original_team_id'] = vals['team_id']
        res = super(Lead, self).write(vals)
        if 'quotation' in vals:
            meeting_overviews = self.env['crm.meeting.overview'].search([('opportunity_id', '=', self.id),('quotation', '!=', self.quotation)])
            for meeting_overview in meeting_overviews:
                meeting_overview.write({
                    'quotation': self.quotation
                })
        if 'final_quotation' in vals:
            meeting_overviews = self.env['crm.meeting.overview'].search([('opportunity_id', '=', self.id),('final_quotation', '!=', self.final_quotation.id)])
            for meeting_overview in meeting_overviews:
                meeting_overview.write({
                    'final_quotation': self.final_quotation
                })
        if 'remark' in vals:
            meeting_overviews = self.env['crm.meeting.overview'].search([('opportunity_id', '=', self.id),('remark', '!=', self.remark)])
            for meeting_overview in meeting_overviews:
                meeting_overview.write({
                    'remark': self.remark
                })
        return res

class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    meeting_overview = fields.Integer("Meeting Overview", compute="_compute_meeting_overviews", store=True)
    stage_id = fields.Many2one(related='opportunity_id.stage_id', store=True)
    meeting_count = fields.Integer(string='Meeting Count', related='opportunity_id.meeting_count', store=True)
    quotation = fields.Selection([
        ("sent", "Sent"),
        ("not_sent", "Not Sent"),
    ], string="Status", store=True)
    final_quotation = fields.Many2one('quotation.amount', string="Final Quotation Amount")

    def _compute_meeting_overviews(self):
        for res in self:
            if not res.meeting_overview:
                overview_id = self.env['crm.meeting.overview'].create({
                    'calendar_id': res.id,
                    'opportunity_id': res.opportunity_id.id,
                    'quotation': res.opportunity_id.quotation,
                    'final_quotation': res.opportunity_id.final_quotation.id,
                })
                res.meeting_overview = overview_id.id
            else:
                res.meeting_overview = 0

class MeetingCalendarOverview(models.Model):
    _name = "crm.meeting.overview"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Meeting Calendar Event"

    calendar_id = fields.Many2one('calendar.event', string='Calendar')
    opportunity_id = fields.Many2one(comodel_name="crm.lead", string="Lead/Opportunity")
    activity_type_id = fields.Many2one(related='opportunity_id.activity_type_id')
    cannot_be_quoted = fields.Boolean(string='Cannot be Quoted')
    potential = fields.Boolean(string='Potential')
    comment = fields.Char(string="Comment")
    res_name = fields.Char("Lead Name", related='opportunity_id.name')
    partner_ids = fields.Many2many('res.partner', related='calendar_id.partner_ids')
    stage_id = fields.Many2one(related='opportunity_id.stage_id')
    meeting_count = fields.Integer(string='Meeting Count', related='opportunity_id.meeting_count')
    quotation = fields.Selection([
        ("sent", "Sent"),
        ("not_sent", "Not Sent"),
    ], string="Quotation Sent Status")
    order_ids = fields.One2many(related='opportunity_id.order_ids')
    final_quotation = fields.Many2one('quotation.amount', string="Final Quotation Amount")
    start = fields.Datetime(related='calendar_id.start', store=True)
    meeting_count = fields.Integer(related='opportunity_id.meeting_count')
    activity_ids = fields.One2many(related='calendar_id.activity_ids')
    state_1 = fields.Selection(related='calendar_id.state')
    meeting_salesperson_ids = fields.Many2many(related='calendar_id.meeting_salesperson_ids')
    remark = fields.Text("Remarks")

    def write(self, vals):
        res = super(MeetingCalendarOverview, self).write(vals)
        if 'quotation' in vals:
            if self.opportunity_id.quotation != self.quotation:
                self.opportunity_id.quotation = self.quotation
        if 'final_quotation' in vals:
            if self.opportunity_id.final_quotation.id != self.final_quotation.id:
                self.opportunity_id.final_quotation = self.final_quotation
        if 'remark' in vals:
            if self.opportunity_id.remark != self.remark:
                self.opportunity_id.remark = self.remark
        if 'potential' in vals:
            if self.opportunity_id.potential != self.potential:
                self.opportunity_id.potential = self.potential
        if 'cannot_be_quoted' in vals:
            if self.opportunity_id.cannot_be_quoted != self.cannot_be_quoted:
                self.opportunity_id.cannot_be_quoted = self.cannot_be_quoted
        return res