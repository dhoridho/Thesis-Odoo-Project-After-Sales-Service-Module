# -*- coding: utf-8 -*-

import json
from odoo import models, fields, api, _
from datetime import datetime,timedelta
from odoo.exceptions import UserError, ValidationError, Warning

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    sign_in_location = fields.Char(string="Sign In Location")
    sign_out_location = fields.Char(string="Sign Out Location")
    sign_in_date = fields.Datetime(string='Sign In Date and Time')
    sign_out_date = fields.Datetime(string='Sign Out Date and Time')
    sign_in = fields.Boolean('Sign In')
    sign_out = fields.Boolean('Sign Out')
    note_field = fields.Html(string='Comment')
    team_id = fields.Many2one(related='opportunity_id.team_id', string="Sale Team", store=True)
    state = fields.Selection([('meeting', 'On Schedule'), ('done', 'Done'),
                              ('rescheduled', 'Rescheduled'), ('cancel', 'Cancelled')], default='meeting',
                             string="Status", tracking=False)
    state_1 = fields.Selection(related='state', tracking=False)
    state_2 = fields.Selection(related='state', tracking=False)
    cancel_reason = fields.Text("Cancel Reason")
    opportunity_name = fields.Char(related='opportunity_id.name', readonly=True, store=True)
    res_name = fields.Char("Subject", compute='_compute_res_name_loc', store=True)
    res_loc = fields.Char("Location", compute='_compute_res_name_loc', store=True)

    @api.depends('name')
    def _compute_res_name_loc(self):
        for rec in self:
            if len(rec.name) > 50:
                rec.res_name = rec.name[0:50] + "..."
            else:
                rec.res_name = rec.name
            if rec.location:
                if len(rec.location) > 60:
                    rec.res_loc = rec.location[0:60] + "..."
                else:
                    rec.res_loc = rec.location

    def action_set_meeting_lost(self, **additional_values):
        self.write(dict(additional_values))

    def update_sign_in_out_location(self, lat, lng):
        for record in self:
            if not record.sign_in or record.sign_out:
                record.get_sign_in_location({'lat': lat, 'lng': lng})
            else:
                record.get_sign_out_location({'lat': lat, 'lng': lng})
        return True

    @api.onchange('opportunity_id')
    def _onchange_opportunity_id(self):
        if not self.opportunity_id:
            return False
        self.user_id = self.opportunity_id.user_id.id

    def get_sign_in_location(self, vals):
        for record in self:
            lat = vals.get('lat')
            lng = vals.get('lng')
            maps_loc = {u'position': {u'lat': lat, u'lng': lng}, u'zoom': 3}
            json_map = json.dumps(maps_loc)
            record.write({'sign_in_location': json_map,
                          'sign_in': True, 'sign_in_date': datetime.now()})

    def get_sign_out_location(self, vals):
        for record in self:
            lat = vals.get('lat')
            lng = vals.get('lng')
            maps_loc = {u'position': {u'lat': lat, u'lng': lng}, u'zoom': 3}
            json_map = json.dumps(maps_loc)
            record.write({'sign_out_location': json_map,
                             'sign_out': True, 'sign_out_date': datetime.now(), 'state': 'done'})

    def cancel_sign_in(self):
        for rec in self:
            rec.write({
                'sign_in': False,
                'sign_in_location': False,
                'sign_in_date': False
            })

    def cancel_sign_out(self):
        for rec in self:
            rec.write({
                'sign_out': False,
                'sign_out_location': False,
                'sign_out_date': False,
                'state': 'meeting'
            })

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_feedback_schedule_next(self, feedback=False):
        self.set_target()
        res = super(MailActivity, self).action_feedback_schedule_next(feedback)
        return res

    def action_feedback(self, feedback=False, attachment_ids=None):
        self.set_target()
        res = super(MailActivity, self).action_feedback(feedback, attachment_ids)
        return res

    def set_target(self):
        activity = self.env['target.activity'].search([('user_id', '=', self.user_id.id), ('from_date', '<=', datetime.now().date()), ('to_date', '>=', datetime.now().date())])
        if activity:
            for res in activity:
                line_res = self.env['target.activity.line.res'].search([('activity_id', '=', res.id), ('activity_type', '=', self.activity_type_id.id)])
                lines_act = self.env['target.activity.line'].search([('activity_id', '=', res.id), ('activity_type', '=', self.activity_type_id.id)])
                target = 0
                if lines_act:
                    for act in lines_act:
                        target += act.activity_target
                if line_res:
                    for line in line_res:
                        line.activity_done += 1
                else:
                    self.env['target.activity.line.res'].create({
                        'activity_id': res.id,
                        'user_id': res.user_id.id,
                        'activity_type': self.activity_type_id.id,
                        'activity_done': 1,
                        'target_activity': target,
                        'date': datetime.now()
                    })

class TargetActivity(models.Model):
    _name = 'target.activity'
    _description = "Target Activity"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    def _compute_status(self):
        for res in self:
            state = True
            for line in res.activity_line:
                if line.achieved_target < 100:
                    state = False
                    break
            res.activity_target_achieved = state

    def _compute_head_team(self):
        for res in self:
            if res.sales_team and res.sales_team.user_id:
                res.head_team = res.sales_team.user_id
            else:
                res.head_team = False

    name = fields.Char("Name")
    sales_team = fields.Many2one('crm.team', string="Sales Team", domain="[('company_id', '=', company_id)]", tracking=True)
    head_team = fields.Many2one('res.users', compute="_compute_head_team")
    user_id = fields.Many2one('res.users', string="Sales Person", required=True, tracking=True, domain="['|', ('sale_team_id', '=', sales_team),('id', '=', head_team)]")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.user.company_id, tracking=True)
    branch_id = fields.Many2one('res.branch', domain="[('company_id', '=', company_id)]", string="Branch", tracking=True)
    activity_target_achieved = fields.Boolean('Follow Ups Target Achieved', tracking=True, compute="_compute_status")
    from_date = fields.Date(string='From Date', required=True, tracking=True)
    to_date = fields.Date(string='To Date', required=True, tracking=True)
    activity_line = fields.One2many('target.activity.line', 'activity_id', string="Target Activity Line", tracking=True)
    activity_line_res = fields.One2many('target.activity.line.res', 'activity_id', string="Target Activity Line Res", tracking=True)

    def duplicate_target_activity(self):
        self.ensure_one()
        context = {
            'default_sales_team': self.sales_team.id,
            'default_user_id': self.user_id.id,
            'default_branch_id': self.branch_id.id,
            'default_activity_line': [(6, 0, self.activity_line.ids)],
        }
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'target.activity',
            'views': [(self.env.ref('equip3_crm_operation.target_activity_form').id, 'form')],
            'view_id': self.env.ref('equip3_crm_operation.target_activity_form').id,
            'target': 'current',
            'context': context,
        }

    @api.model
    def create(self, vals):
        target = self.search([('user_id', '=', vals['user_id']),
                              '|', '|',
                              '&', ('from_date', '<=', vals['from_date']), ('to_date', '>=', vals['from_date']),
                              '&', ('from_date', '<=', vals['to_date']), ('to_date', '>=', vals['to_date']),
                              '&', ('from_date', '>=', vals['from_date']), ('to_date', '<=', vals['to_date']),
                              ], limit=1)
        if target:
            raise ValidationError("The date range of this activity target is intersects with other activity target [%s] in same salesperson. Please check the Activity Target again." % (target.name))
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('target.activity.seq')
            return super(TargetActivity, self).create(vals)

    @api.onchange('sales_team')
    def onchange_partner_id(self):
        for rec in self:
            user = rec.user_id
            if user.id == rec.sales_team.user_id.id or user.id in rec.sales_team.member_ids.ids:
                rec.user_id = user
            else:
                rec.user_id = False
            if rec.sales_team:
                return {'domain': {'user_id': ['|', ('sale_team_id', '=', rec.sales_team.id), ('id', '=', rec.sales_team.user_id.id)]}}



class TargetActivityLineRes(models.Model):
    _name = 'target.activity.line.res'
    _description = "Target Activity Line Res"

    activity_id = fields.Many2one('target.activity', string="Target Activity")
    user_id = fields.Many2one('res.users', string="Sales Person")
    sales_team = fields.Many2one(related='activity_id.sales_team', store=True)
    activity_type = fields.Many2one('mail.activity.type', string="Follow Ups Type", tracking=True)
    activity_done = fields.Integer("Achieved Target", tracking=True)
    target_activity = fields.Integer("Target Follow Ups")
    date = fields.Datetime("Date")
    from_date = fields.Date(related='activity_id.from_date')
    to_date = fields.Date(related='activity_id.to_date')


class TargetActivityLine(models.Model):
    _name = 'target.activity.line'
    _Description = "Target Activity Line"

    def _compute_target(self):
        for res in self:
            # activity = self.env['mail.activity'].search([('activity_type_id', '=', res.activity_type.id), ('user_id', '=', res.activity_id.user_id.id), ('date_deadline', '<=', res.activity_id.to_date),('date_deadline', '>=', res.activity_id.from_date)])
            done = 0
            for line in res.activity_id.activity_line_res:
                if res.activity_type == line.activity_type:
                    done += line.activity_done
            achieved_target = done / res.activity_target * 100
            remaining_target = 100 - achieved_target
            res.update({
                'achieved_target': achieved_target or 0,
                'remaining_target': remaining_target or 0,
            })

    user_id = fields.Many2one(related='activity_id.user_id')
    activity_id = fields.Many2one('target.activity', string="Target Activity")
    activity_type = fields.Many2one('mail.activity.type', string="Follow Ups Type")
    activity_target = fields.Integer("Follow Ups Target")
    achieved_target = fields.Float("Achieved Target (%)", compute="_compute_target")
    remaining_target = fields.Float("Remaining Target (%)", compute="_compute_target")

    @api.model
    def create(self, vals):
        if 'activity_type' in vals:
            if vals['activity_type'] == False:
                raise ValidationError("Activity Type cannot be empty.")
        if 'activity_target' in vals:
            if vals['activity_target'] <= 0:
                raise ValidationError("Activity Target must be positive.")
        res = super(TargetActivityLine, self).create(vals)
        return res
