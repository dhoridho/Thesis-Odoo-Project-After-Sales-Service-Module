# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class CrmLeadSalespersonLine(models.Model):
    _inherit = 'crm.lead.salesperson.lines'

    def write(self, vals):
        res = super(CrmLeadSalespersonLine, self).write(vals)
        analysis = self.env['crm.lead.analysis.new'].sudo().search([('lead_id', '=', self.lead_id.id),('user_id', '=', self.salesperson_id.id)])
        analysis.weightage = self.weightage
        if self.weightage > 0:
            analysis.lead_count = self.weightage / 100
        else:
            analysis.lead_count = 0
        return res

class CrmLead(models.Model):
    _inherit = "crm.lead"

    # day_open = fields.Float('Duration to Assign (Days)', compute='_compute_day_open', store=True)

    lost_date = fields.Datetime('Lost Date')
    won_date = fields.Datetime('Won Date')
    quotation_date = fields.Datetime('Quotation Date')
    meeting_date = fields.Datetime('First Meeting Date')

    lost_day = fields.Integer('Duration to Lost (Days)', default=0)
    won_day = fields.Integer('Duration to Won (Days)', default=0)
    quotation_day = fields.Integer('Duration to Quotation (Days)', default=0)
    meeting_day = fields.Integer('Duration to First Meeting (Hour)', default=0)
    stage_day = fields.Integer('Duration First Move Stage (Hour)', default=0)

    first_to_second_meeting_days = fields.Integer('First to Second Meeting (days)', default=0)
    created_to_second_meeting_days = fields.Integer('Leads Created to Second Meeting (days)', default=0)
    trigger_lead_analysis = fields.Boolean("Trigger", compute="_compute_lead_analysis", store=True)

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('crm.crm_menu_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-crm-crm-dashboard'})

    @api.model
    def set_leads_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'leads'),
            ('parent_id', '=', self.env.ref('crm.crm_menu_root').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-crm-leads-monitoring'})

    def _compute_lead_analysis(self):
        for rec in self:
            rec.trigger_lead_analysis = True
            rec.create_lead_analysis()

    def create_lead_analysis(self):
        for res in self:
            # is_multi_salesperson = self.env.user.id in self.env.ref('equip3_crm_operation.group_use_multi_salesperson_on_leads').users.ids
            partner_ids = []
            if res.salesperson_lines:
                for line in res.salesperson_lines:
                    self.env['crm.lead.analysis.new'].sudo().create({
                        'lead_id': res.id,
                        'user_id': line.salesperson_id.id,
                        'weightage': line.weightage
                    })
            else:
                self.env['crm.lead.analysis.new'].sudo().create({
                    'lead_id': res.id,
                    'user_id': res.user_id.id,
                    'weightage': 100
                })

    @api.model
    def create(self, vals):
        res = super(CrmLead, self).create(vals)
        res.create_lead_analysis()
        return res

    def write(self, vals):
        for record in self:
            diff = (fields.Datetime.now() - record.create_date)
            days = diff.days
            sec = diff.seconds
            hour = days * 24 + sec // 3600
            if 'active' in vals:
                if not vals['active']:
                    vals['lost_date'] = fields.Datetime.now()
                    vals['lost_day'] = days
                else:
                    vals['lost_date'] = False
                    vals['lost_day'] = False
            if record.stage_id.id == 1 and not record.stage_day:
                vals['stage_day'] = hour
            if 'stage_id' in vals:
                stage_name = self.env['crm.stage'].browse(vals['stage_id']).name
                if stage_name == "Won":
                    vals['won_date'] = fields.Datetime.now()
                    vals['won_day'] = days
            if 'salesperson_lines' in vals:
                for line in vals['salesperson_lines']:
                    if line[0] == 2:
                        line_id = self.env['crm.lead.salesperson.lines'].browse(line[1])
                        id = self.env['crm.lead.analysis.new'].sudo().search([('lead_id', '=', record.id),('user_id', '=', line_id.salesperson_id.id)])
                        if id:
                            id.unlink()
                    elif line[0] == 0:
                        user = self.env['res.users'].browse(line[2]['salesperson_id'])
                        self.env['crm.lead.analysis.new'].sudo().create({
                            'lead_id': record.id,
                            'user_id': user.id,
                            'weightage': line[2]['weightage']
                        })
        res = super(CrmLead, self).write(vals)
        return res

class CrmLeadAnalysis(models.Model):
    _name = "crm.lead.analysis.new"
    _description = "CRM Lead Analysis New"

    lead_id = fields.Many2one('crm.lead', string='Lead')
    name = fields.Char(related='lead_id.name', store=True)
    user_id = fields.Many2one('res.users', string="Sales Person")
    automated_probability = fields.Float(related='lead_id.automated_probability', store=True)
    day_open = fields.Float(related='lead_id.day_open', store=True)
    day_close = fields.Float(related='lead_id.day_close', store=True)
    lost_day = fields.Integer(related='lead_id.lost_day', store=True)
    won_day = fields.Integer(related='lead_id.won_day', store=True)
    quotation_day = fields.Integer(related='lead_id.quotation_day', store=True)
    meeting_day = fields.Integer(related='lead_id.meeting_day', store=True)
    stage_day = fields.Integer(related='lead_id.stage_day', store=True)
    company_id = fields.Many2one(related='lead_id.company_id', store=True)
    company_currency = fields.Many2one("res.currency", string='Currency', related='company_id.currency_id', readonly=True)
    expected_revenue = fields.Integer(compute='_compute_expected_revenue', store=True)
    first_to_second_meeting_days = fields.Integer(related='lead_id.first_to_second_meeting_days', store=True)
    created_to_second_meeting_days = fields.Integer(related='lead_id.created_to_second_meeting_days', store=True)
    one_metting = fields.Boolean(related='lead_id.one_metting', store=True)
    multiple_metting = fields.Boolean(related='lead_id.multiple_metting', store=True)
    probability_new = fields.Float(related='lead_id.probability_new', string='Probability New', store=True)
    create_date = fields.Datetime(related='lead_id.create_date', store=True)
    team_id = fields.Many2one(related='lead_id.team_id', store=True)
    weightage = fields.Float("Weightage")
    lead_count = fields.Float("Lead Count", compute="_compute_lead_count", store=True)
    einstein_score = fields.Float(string="Hash Quality Score", related='lead_id.einstein_score', store=True)
    one_metting_int = fields.Integer(string="Had First Meeting", related='lead_id.one_metting_int', store=True)
    multiple_metting_int = fields.Integer(string="Had Multiple Meetings", related='lead_id.multiple_metting_int', store=True)
    prorated_revenue = fields.Monetary('Prorated Revenue', currency_field='company_currency', related='lead_id.prorated_revenue', store=True)
    lost_reason_new = fields.Many2one(related='lead_id.lost_reason', string='Lost Reason', store=True)

    # Add following fields for filter
    active = fields.Boolean(related='lead_id.active', string="Active", store=True)
    date_closed = fields.Datetime(related='lead_id.date_closed', store=True)
    stage_id = fields.Many2one(related='lead_id.stage_id', store=True)
    probability = fields.Float(related='lead_id.probability', store=True)
    partner_id = fields.Many2one(related='lead_id.partner_id', store=True)
    activity_data = fields.One2many(related='lead_id.activity_data', string="Activity")
    date_deadline = fields.Date(related='lead_id.date_deadline',string="Closed Date")
    activity_type_id = fields.Many2one(related='activity_data.activity_type_id', string="Type")
    activity_state = fields.Selection(related='lead_id.activity_state', string="Status Activity")
    user_ids = fields.Many2many(related='lead_id.user_ids', string='Salesperson')

    @api.depends('lead_id','lead_id.expected_revenue')
    def _compute_expected_revenue(self):
        for rec in self:
            rec.expected_revenue = rec.lead_id.expected_revenue or 0

    @api.depends('weightage')
    def _compute_lead_count(self):
        for rec in self:
            if rec.weightage > 0:
                rec.lead_count = rec.weightage / 100
            else:
                rec.lead_count = 0



