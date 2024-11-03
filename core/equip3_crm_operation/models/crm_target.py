from odoo import fields,api, models, _
from odoo.exceptions import ValidationError
from operator import itemgetter
from datetime import datetime, date
from lxml import etree
import json as simplejson
from odoo.addons.base.models.ir_ui_view import (transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)

class CrmTarget(models.Model):
    _name = 'crm.target'
    _description = "CRM Target"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('salesperson_id')
    def _compute_sale_team(self):
        for rec in self:
            sale_team_id = False
            if rec.salesperson_id:
                if rec.salesperson_id.sale_team_id:
                    sale_team_id = rec.salesperson_id.sale_team_id
            if not sale_team_id:
                raise ValidationError("user %s is not included in any team" % rec.salesperson_id.name)
            rec.sale_team_id = sale_team_id

    @api.depends('state')
    def _compute_hide(self):
        for rec in self:
            hide = False
            if rec.state == 'draft':
                if self.env.user.id != rec.salesperson_id.id:
                    hide = True
            if rec.state == 'waiting_approval':
                if self.env.user.id != rec.team_leader_id.id:
                    if self.env.user.id not in rec.sale_team_id.additional_leader_ids.ids:
                        hide = True
            if rec.state == 'rejected':
                if self.env.user.id != rec.salesperson_id.id and self.env.user.id != rec.team_leader_id.id and self.env.user.id not in rec.sale_team_id.additional_leader_ids.ids:
                    hide = True
            rec.hide = hide

    name = fields.Char("Reference", index=True)
    salesperson_id = fields.Many2one('res.users', string="Salesperson", readonly=False, required=True, tracking=True, default=lambda self: self.env.user.id, index=True)
    sale_team_id = fields.Many2one('crm.team', string="Sales Team", tracking=True, required=False, compute=_compute_sale_team, store=True)
    team_leader_id = fields.Many2one('res.users', string="Team Leader", related='sale_team_id.user_id', required=True, readonly=True, tracking=True)
    start_date = fields.Date('Start Date', required=True, default=fields.Date.today)
    end_date = fields.Date('End Date',required=True, default=fields.Date.today)
    based_on = fields.Selection([('expected_revenue', 'Expected Revenue'),('amount', 'Amount'),('quantity', 'Quantity')], default='expected_revenue', required=True, tracking=True)
    main_target = fields.Float("Main Target", readonly=False, required=True, tracking=True, default=0)
    current_achievement = fields.Float("Current Achievement", readonly=True, tracking=True)
    target_left = fields.Float("Target left", tracking=True, compute="_compute_target_left")
    created_on = fields.Datetime(string='Created On', default=datetime.now(), readonly=True, tracking=True)
    created_by = fields.Many2one('res.users',default=lambda self:self.env.user, readonly=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'),('waiting_approval', 'Waiting for Approval'),('approved', 'Approved'),('rejected', 'Rejected')], string="State", tracking=True, default='draft')
    state_new = fields.Selection(related='state', tracking=False)
    hide = fields.Boolean("Hide", compute=_compute_hide, store=False)

    @api.depends('main_target','current_achievement')
    def _compute_target_left(self):
        for rec in self:
            target_left = rec.main_target
            if rec.current_achievement:
                target_left = rec.main_target - rec.current_achievement
            rec.target_left = target_left

    @api.model
    def create(self, vals):
        vals['target_left'] = vals['main_target']
        start_date = datetime.strptime(vals['start_date'],'%Y-%m-%d').date()
        end_date = datetime.strptime(vals['end_date'],'%Y-%m-%d').date()
        my_target = self.env['crm.target'].search([('salesperson_id','=',self.env.user.id),('state','!=','rejected')])
        if my_target:
            for rec in my_target:
                rec.check_date(start_date,end_date)
        res = super().create(vals)
        res.name = self.env['ir.sequence'].next_by_code('crm.target.seq') or _('New')
        return res

    def check_date(self, start_date, end_date):
        for rec in self:
            if rec.start_date <= start_date <= rec.end_date or rec.start_date <= end_date <= rec.end_date:
                raise ValidationError("There is already target data for that date!")
            elif start_date <= rec.start_date <= end_date or start_date <= rec.end_date <= end_date:
                raise ValidationError("There is already target data for that date!")

    def write(self, vals):
        res = super().write(vals)
        if 'end_date' in vals or 'start_date' in vals:
            self.check_date(self.start_date,self.end_date)
        return res


    def button_request(self):
        for rec in self:
            rec.state = 'waiting_approval'

    def button_approve(self):
        for rec in self:
            rec.state = 'approved'

    def button_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def button_reset(self):
        for rec in self:
            rec.state = 'draft'

    @api.model
    def fields_view_get(self, view_id=None, view_type=False, toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,         submenu=submenu)
        doc = etree.XML(res['arch'])
        if view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = [['state','=','approved']]
                node.set('modifiers', simplejson.dumps(modifiers))
            node = doc.xpath("//field[@name='target_left']")[0]
            node.set('readonly', '1')
            setup_modifiers(node, res['fields']['target_left'])
            res['arch'] = etree.tostring(doc)
        return res

