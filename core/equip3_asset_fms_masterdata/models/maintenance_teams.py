
from odoo import api, fields, models,_
from odoo.exceptions import UserError

class inherit_team(models.Model):
    
    _inherit = ['maintenance.team']

    m_assignation = fields.Many2one('maintenance.assignation.type', string='Maintenance Assignation Type')
    company_partner = fields.Many2one('res.partner', string='Company')
    company_ref = fields.Selection(
        [('0', 'Company'), ('1', 'Partner')],
        'Company References', default='0', help='')
    working_time = fields.Char(string='Working Time')
    h_labor_cost = fields.Float(string='Hourly Labor Cost')
    m_cost_analytic = fields.Many2one('account.analytic.account', string='Maintenance Cost Analytic Account')


class Maintenance_teams(models.Model):
    _name = 'maintenance.teams'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Maintenance Teams'
    _parent_name = "name"
    _order = 'name'
    _rec_name = 'name'

    name = fields.Char('Team Name', required=True, translate=True, store=True)
    active = fields.Boolean(default=True)
    user_id = fields.Many2one('res.users', string='Team Leader')
    m_assignation = fields.Many2one('maintenance.assignation.type', string='Maintenance Assignation Type')
    company_partner = fields.Many2one('res.partner', string='Company')
    company_ref = fields.Selection(
        [('0', 'Company'), ('1', 'Partner')],
        'Company References', default='0', help='')
    working_time = fields.Char(string='Working Time')
    h_labor_cost = fields.Float(string='Hourly Labor Cost')
    m_cost_analytic = fields.Many2one('account.analytic.account', string='Maintenance Cost Analytic Account')
    description = fields.Text()
    child_ids = fields.Many2many('res.users', string='Child Tags')

    # complete_name = fields.Char('Complete Name', compute='_compute_complete_name', store=True)
    # @api.depends('name', 'parent_location.name')
    # def _compute_complete_name(self):
    #     for group in self:
    #         if group.parent_location:
    #             group.complete_name = '%s / %s' % (group.parent_location.name, group.name)
    #         else:
    #             group.complete_name = group.name

    # request_count = fields.Integer(string='Requests Count', compute='_compute_request_count')

    wo_count = fields.Integer(string='Work Order Count', compute='_compute_work_order_count', readonly=True)
    re_count = fields.Integer(string='Repair Order Count', compute='_compute_repair_order_count', readonly=True)
    state = fields.Selection([('busy', 'busy'),
                              ('free', 'free')
                              ], string="Partner's", required=True, default='free')

    # maintenance_plan_count = fields.Integer(
    #     compute="_compute_maintenance_plan_count",
    #     string="Maintenance Plan Count",
    #     store=True,
    # )

    asset_count = fields.Integer(string='Asset', compute='_compute_asset_count')

    maintenance_plan_pre = fields.Integer(
        compute="_compute_maintenance_plan_count",
        string="Preventive Maintenance Plan Count",

    )
    maintenance_plan_meter = fields.Integer(
        compute="_compute_maintenance_plan_count2",
        string="Hour Meter Maintenance Plan Count",

    )
    maintenance_plan_odo = fields.Integer(
        compute="_compute_maintenance_plan_count3",
        string="Odometer Maintenance Plan Count",

    )

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Maintenance Teams'),
            'template': '/equip3_asset_fms_masterdata/static/xls/maintenance_teams_template.xls'
        }]

    def _compute_maintenance_plan_count(self):
        for rec in self:
            maintenance_plan_pre = self.env['maintenance.plan'].search_count([('maintenance_team_id', '=', rec.id), ('is_preventive_m_plan', '=', True)])
            rec.maintenance_plan_pre = maintenance_plan_pre

    def _compute_maintenance_plan_count2(self):
        for rec in self:
            maintenance_plan_meter = self.env['maintenance.plan'].search_count([('maintenance_team_id', '=', rec.id), ('is_hourmeter_m_plan', '=', True)])
            rec.maintenance_plan_meter = maintenance_plan_meter

    def _compute_maintenance_plan_count3(self):
        for rec in self:
            maintenance_plan_odo = self.env['maintenance.plan'].search_count([('maintenance_team_id', '=', rec.id), ('is_odometer_m_plan', '=', True)])
            rec.maintenance_plan_odo = maintenance_plan_odo

    # def _compute_request_count(self):
    #     for rec in self:
    #         request_count = self.env['maintenance.request'].search_count([('facility', '=', rec.id)])
    #         rec.request_count = request_count

    # def _compute_maintenance_plan_count(self):
    #     for rec in self:
    #         maintenance_plan_count = self.env['maintenance.plan'].search_count([('company_id', '=', rec.id)])
    #         rec.maintenance_plan_count = maintenance_plan_count

    def _compute_asset_count(self):
        for rec in self:
            asset_count = self.env['maintenance.equipment'].search_count([('maintenance_teams_id', '=', rec.id)])
            rec.asset_count = asset_count

    def _compute_work_order_count(self):
        work_order_obj = self.env['maintenance.work.order']
        work_order_ids = work_order_obj.search([('maintenanceteam', '=', self.name)])
        for book in self:
            book.update({
                'wo_count': len(work_order_ids)
            })

    def wo_action_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Work Order',
            'res_model': 'maintenance.work.order',
            'domain': [('maintenanceteam', '=', self.name)]}

    def re_action_link(self):
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'list',
            'view_mode': 'list,form',
            'name': 'Repair Order',
            'res_model': 'maintenance.repair.order',
            'domain': [('maintenance_team', '=', self.name)]}

    def _compute_repair_order_count(self):
        repair_order_obj = self.env['maintenance.repair.order']
        repair_order_ids = repair_order_obj.search([('maintenance_team', '=', self.name)])
        for book in self:
            book.update({
                're_count': len(repair_order_ids)
            })



