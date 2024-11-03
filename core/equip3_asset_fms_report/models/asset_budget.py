from odoo import api, fields, models
from datetime import datetime
import time


class Assetbudget(models.Model):
    _name = 'asset.budget'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'
    _description = 'Asset Budget'

    name = fields.Char(string='Asset Budget Name', required=True, tracking=True)
    state = fields.Selection(string='Status', selection=[('draft', 'Draft'), ('confirm', 'Confirmed'),('validate', 'Validate'),('done', 'Done'),], default='draft', tracking=True)
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', tracking=True,default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)])
    company_id = fields.Many2one(comodel_name='res.company', string='Company',store=True, readonly=True, default=lambda self: self.env.company)
    company_currency_id = fields.Many2one(string='Company Currency', readonly=True,related='company_id.currency_id')
    analytic_group_id = fields.Many2one(comodel_name='account.analytic.tag', string='Analytic Group', tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    asset_budget_line = fields.One2many(comodel_name='asset.budget.line', inverse_name='asset_budget_id', string='Asset Budget Line')

    def action_confirm(self):
        self.state = 'confirm'

    def action_draft(self):
        self.state = 'draft'

    def action_validate(self):
        now = datetime.now()
        for rec in self:
            rec.state = 'validate'
            if now.date() > rec.end_date:
                for line in rec.asset_budget_line:
                    line._compute_budget()
                    rec.action_done()


    def action_done(self):
        for rec in self:
            for line in rec.asset_budget_line:
                # if line.practical_amount > 0 and line.theoretical_amount > 0 and line.achievement != False:
                line.write({
                    'practical_amount_cp': line.practical_amount,
                    'theoretical_amount_cp': line.theoretical_amount,
                    'achievement_cp': line.achievement,
                    'counting_date_cp': line.counting_date,
                    })
                rec.state = 'done'


class AssetBugetLine(models.Model):
    _name = 'asset.budget.line'
    _description = 'Asset Budget Line'

    asset_budget_id = fields.Many2one(comodel_name='asset.budget', string='Asset Budget')
    equipment_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset', required=True)
    analytic_group_id = fields.Many2one(comodel_name='account.analytic.tag', string='Analytic Group', related='asset_budget_id.analytic_group_id')
    currency_id = fields.Many2one(comodel_name='res.currency', string='Currency', related='asset_budget_id.company_currency_id')
    start_date = fields.Date(string='Start Date', related='asset_budget_id.start_date',)
    end_date = fields.Date(string='End Date', related='asset_budget_id.end_date')
    planned_amount = fields.Monetary(string='Planned Amount', required=True)

    counting_date = fields.Date(string='Counting Date', compute='_compute_budget', compute_sudo=True)
    practical_amount = fields.Monetary(string='Practical Amount', compute='_compute_budget', store=True)
    theoretical_amount = fields.Monetary(string='Theoretical Amount', compute='_compute_budget', store=True)
    achievement = fields.Char(string='Achievement', compute='_compute_budget', store=True)

    counting_date_cp = fields.Date(string='Counting Date')
    practical_amount_cp = fields.Monetary(string='Practical Amount', store=True)
    theoretical_amount_cp = fields.Monetary(string='Theoretical Amount', store=True)
    achievement_cp = fields.Char(string='Achievement', store=True)


    @api.depends('equipment_id', 'start_date', 'end_date', 'planned_amount','practical_amount','theoretical_amount','achievement')
    def _compute_budget(self):
        practical_amount = 0
        vals = {}
        for rec in self:
            now = datetime.now()
            rec.counting_date = False
            rec.practical_amount = 0
            rec.theoretical_amount = 0
            rec.achievement = False

            if rec.asset_budget_id.state == 'validate':

                if rec.asset_budget_id.analytic_group_id:
                    rapair_order_ids = self.env['maintenance.repair.order'].search([('date_start', '<=', rec.end_date), ('date_stop', '>=', rec.start_date), ('analytic_group_id', 'in', rec.asset_budget_id.analytic_group_id.id),('state_id', 'not in', ['draft','cancel'])])
                    for rapair_order_id in rapair_order_ids:
                        for ro_line in rapair_order_id.task_check_list_ids.filtered(lambda x: x.equipment_id.id == rec.equipment_id.id):
                            invoice_id = ro_line.maintenance_ro_id.invoice_id
                            if invoice_id.state == 'posted':
                                practical_amount += rapair_order_id.invoice_id.amount_total
                                rec.practical_amount = practical_amount
                                # print('MRO POSTED WITH ANALYTIC >', rapair_order_id.name)

                    work_order_ids = self.env['maintenance.work.order'].search([('startdate', '<=', rec.end_date), ('enddate', '>=', rec.start_date),'|', ('analytic_group_id', 'in', rec.asset_budget_id.analytic_group_id.id), ('analytic_group_id', '=', rec.analytic_group_id.id), ('state_id', 'not in', ['draft','cancel'])])
                    for work_order in work_order_ids:
                        for wo_line in work_order.task_check_list_ids.filtered(lambda x: x.equipment_id.id == rec.equipment_id.id):
                            invoice_id = wo_line.maintenance_wo_id.invoice_id
                            if invoice_id.state == 'posted':
                                practical_amount += invoice_id.amount_total
                                rec.practical_amount = practical_amount
                                # print('MWO POSTED WITH ANALYTIC >', wo_line.maintenance_wo_id.name)
                else:
                    rapair_order_ids = self.env['maintenance.repair.order'].search([('date_start', '<=', rec.end_date), ('date_stop', '>=', rec.start_date), ('state_id', 'not in', ['draft','cancel'])])
                    for rapair_order_id in rapair_order_ids:
                        for ro_line in rapair_order_id.task_check_list_ids.filtered(lambda x: x.equipment_id.id == rec.equipment_id.id):
                            invoice_id = ro_line.maintenance_ro_id.invoice_id
                            if invoice_id.state == 'posted':
                                practical_amount += rapair_order_id.invoice_id.amount_total
                                rec.practical_amount = practical_amount
                                # print('MRO >', rapair_order_id.name)

                    work_order_ids = self.env['maintenance.work.order'].search([('startdate', '<=', rec.end_date), ('enddate', '>=', rec.start_date), ('state_id', 'not in', ['draft','cancel'])])
                    for work_order in work_order_ids:
                        for wo_line in work_order.task_check_list_ids.filtered(lambda x: x.equipment_id.id == rec.equipment_id.id):
                            invoice_id = wo_line.maintenance_wo_id.invoice_id
                            if invoice_id.state == 'posted':
                                practical_amount += invoice_id.amount_total
                                rec.practical_amount = practical_amount
                                # print('MWO >', wo_line.maintenance_wo_id.name)

                if rec.end_date and rec.start_date and rec.practical_amount > 0:

                    rec.counting_date = now.date() if now.date() <= rec.end_date else rec.end_date
                    period_day = (rec.end_date - rec.start_date).days + 1
                    # print('period_day', period_day)

                if now.date() > rec.end_date and rec.practical_amount > 0:
                    rec.theoretical_amount = (period_day / period_day) * rec.planned_amount
                    if rec.theoretical_amount > 0:
                        rec.achievement = str(round((practical_amount / rec.theoretical_amount) * 100, 2)) + '%'
                        # print('THEORETICAL', rec.theoretical_amount)
                else:
                    if rec.practical_amount > 0:
                        rec.theoretical_amount = (((now.date() - rec.start_date).days + 1) / period_day) * rec.planned_amount
                    if rec.theoretical_amount > 0:
                        rec.achievement = str(round((practical_amount / rec.theoretical_amount) * 100, 2)) + '%'

            if rec.asset_budget_id.state == 'done':
                vals.update({
                    'practical_amount': rec.practical_amount_cp,
                    'theoretical_amount': rec.theoretical_amount_cp,
                    'achievement': rec.achievement_cp,
                    'counting_date': rec.counting_date_cp,
                        })
                rec.update(vals)
