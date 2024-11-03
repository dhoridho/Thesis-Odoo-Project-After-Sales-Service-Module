from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class CostSheetApprovalWizard(models.TransientModel):
    _name = 'cost.sheet.approval.wizard'
    _description = 'Cost Sheet Approval Wizard'

    # fields
    project_id = fields.Many2one(comodel_name='project.project', string='Project', required=True)
    act_start_date = fields.Date(string='Project Actual Start Date')
    act_start_date_proj = fields.Date(string='Project Actual Start Date')
    start_date = fields.Date(string='Project Planned Start Date', related="project_id.start_date")
    end_date = fields.Date(string='Project Planned End Date', related="project_id.end_date")
    job_sheet_id = fields.Many2one('job.cost.sheet', string="Cost Sheet")
    period = fields.Many2one('project.budget.period', string='Period')
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', default='product_budget')
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'), ], string='Budgeting Period', default='project')

    # table
    project_budget_ids = fields.One2many('cost.sheet.budget.line', 'cost_sheet_wizard_id', string='Periodical Budget')

    def get_line_material(self, cs, amount):
        return {
            'cs_material_id': cs.id,
            'project_scope': cs.project_scope.id,
            'section_name': cs.section_name.id,
            'variable': cs.variable_ref.id,
            'group_of_product': cs.group_of_product.id,
            'product_id': cs.product_id.id,
            'description': cs.description,
            'quantity': cs.product_qty,
            'uom_id': cs.uom_id.id,
            'budget_quantity': cs.product_qty,
            'amount': cs.price_unit,
            'budget_amount': amount,
            'unallocated_quantity': cs.product_qty_na,
            'unallocated_amount': cs.product_amt_na,
        }

    def get_line_labour(self, cs, amount):
        return {
            'cs_labour_id': cs.id,
            'project_scope': cs.project_scope.id,
            'section_name': cs.section_name.id,
            'variable': cs.variable_ref.id,
            'group_of_product': cs.group_of_product.id,
            'product_id': cs.product_id.id,
            'description': cs.description,
            'quantity': cs.product_qty,
            'time': cs.time,
            'contractors': cs.contractors,
            'uom_id': cs.uom_id.id,
            'budget_quantity': cs.product_qty,
            'amount': cs.price_unit,
            'budget_amount': amount,
            'unallocated_contractors': cs.unallocated_contractors,
            'unallocated_time': cs.unallocated_budget_time,
            'unallocated_quantity': cs.product_qty_na,
            'unallocated_amount': cs.product_amt_na,
        }

    def get_line_overhead(self, cs, amount):
        return {
            'cs_overhead_id': cs.id,
            'project_scope': cs.project_scope.id,
            'section_name': cs.section_name.id,
            'variable': cs.variable_ref.id,
            'overhead_catagory': cs.overhead_catagory,
            'group_of_product': cs.group_of_product.id,
            'product_id': cs.product_id.id,
            'description': cs.description,
            'quantity': cs.product_qty,
            'uom_id': cs.uom_id.id,
            'budget_quantity': cs.product_qty,
            'amount': cs.price_unit,
            'budget_amount': amount,
            'unallocated_quantity': cs.product_qty_na,
            'unallocated_amount': cs.product_amt_na,
        }

    def get_line_equipment(self, cs, amount):
        return {
            'cs_equipment_id': cs.id,
            'project_scope': cs.project_scope.id,
            'section_name': cs.section_name.id,
            'variable': cs.variable_ref.id,
            'group_of_product': cs.group_of_product.id,
            'product_id': cs.product_id.id,
            'description': cs.description,
            'quantity': cs.product_qty,
            'uom_id': cs.uom_id.id,
            'budget_quantity': cs.product_qty,
            'amount': cs.price_unit,
            'budget_amount': amount,
            'unallocated_quantity': cs.product_qty_na,
            'unallocated_amount': cs.product_amt_na,
        }

    def get_line_subcon(self, cs, amount):
        return {
            'cs_subcon_id': cs.id,
            'project_scope': cs.project_scope.id,
            'section_name': cs.section_name.id,
            'variable_ref': cs.variable_ref.id,
            'subcon_id': cs.variable.id,
            'description': cs.description,
            'quantity': cs.product_qty,
            'uom_id': cs.uom_id.id,
            'budget_quantity': cs.product_qty,
            'amount': cs.price_unit,
            'budget_amount': amount,
            'unallocated_quantity': cs.product_qty_na,
            'unallocated_amount': cs.product_amt_na,
        }

    def get_line_asset(self, cs, amount):
        return {
            'cs_internal_asset_id': cs.id,
            'project_scope_line_id': cs.project_scope.id,
            'section_name': cs.section_name.id,
            'variable_id': cs.variable_ref.id,
            'asset_category_id': cs.asset_category_id.id,
            'asset_id': cs.asset_id.id,
            'uom_id': cs.uom_id.id,
            'budgeted_qty': cs.budgeted_qty,
            'price_unit': cs.price_unit,
            'budgeted_amt': amount,
            'unallocated_budget_qty': cs.unallocated_budget_qty,
            'unallocated_budget_amt': cs.unallocated_amt,
        }

    def create_project_budget(self, res):
        for line in res.project_budget_ids:
            budget = False
            budget_material = [(5, 0, 0)]
            budget_labour = [(5, 0, 0)]
            budget_internal = [(5, 0, 0)]
            budget_equipment = [(5, 0, 0)]
            budget_subcon = [(5, 0, 0)]
            budget_overhead = [(5, 0, 0)]

            # Material ids
            for cs in res.job_sheet_id.material_ids:
                if line.project_scope and line.section_name:
                    for scope in line.project_scope:
                        for section in line.section_name:
                            if (cs.project_scope.id == scope.id) and (cs.section_name.id == section.id):
                                amount = cs.material_amount_total
                                budget_material.append((0, 0, res.get_line_material(cs, amount)))
                elif line.project_scope and not line.section_name:
                    for scope in line.project_scope:
                        if (cs.project_scope.id == scope.id):
                            amount = cs.material_amount_total
                            budget_material.append((0, 0, res.get_line_material(cs, amount)))

            # labour ids
            for cs in res.job_sheet_id.material_labour_ids:
                if line.project_scope and line.section_name:
                    for scope in line.project_scope:
                        for section in line.section_name:
                            if (cs.project_scope.id == scope.id) and (cs.section_name.id == section.id):
                                amount = cs.labour_amount_total
                                budget_labour.append((0, 0, res.get_line_labour(cs, amount)))
                elif line.project_scope and not line.section_name:
                    for scope in line.project_scope:
                        if cs.project_scope.id == scope.id:
                            amount = cs.labour_amount_total
                            budget_labour.append((0, 0, res.get_line_labour(cs, amount)))

            # overhead ids
            for cs in res.job_sheet_id.material_overhead_ids:
                if line.project_scope and line.section_name:
                    for scope in line.project_scope:
                        for section in line.section_name:
                            if (cs.project_scope.id == scope.id) and (cs.section_name.id == section.id):
                                amount = cs.overhead_amount_total
                                budget_overhead.append((0, 0, res.get_line_overhead(cs, amount)))
                elif line.project_scope and not line.section_name:
                    for scope in line.project_scope:
                        if (cs.project_scope.id == scope.id):
                            amount = cs.overhead_amount_total
                            budget_overhead.append((0, 0, res.get_line_overhead(cs, amount)))

            # equipment ids
            for cs in res.job_sheet_id.material_equipment_ids:
                if line.project_scope and line.section_name:
                    for scope in line.project_scope:
                        for section in line.section_name:
                            if (cs.project_scope.id == scope.id) and (cs.section_name.id == section.id):
                                amount = cs.equipment_amount_total
                                budget_equipment.append((0, 0, res.get_line_equipment(cs, amount)))
                elif line.project_scope and not line.section_name:
                    for scope in line.project_scope:
                        if cs.project_scope.id == scope.id:
                            amount = cs.equipment_amount_total
                            budget_equipment.append((0, 0, res.get_line_equipment(cs, amount)))

            # internal asset ids
            for cs in res.job_sheet_id.internal_asset_ids:
                if line.project_scope and line.section_name:
                    for scope in line.project_scope:
                        for section in line.section_name:
                            if (cs.project_scope.id == scope.id) and (cs.section_name.id == section.id):
                                amount = cs.budgeted_amt
                                budget_internal.append((0, 0, res.get_line_asset(cs, amount)))
                elif line.project_scope and not line.section_name:
                    for scope in line.project_scope:
                        if cs.project_scope.id == scope.id:
                            amount = cs.budgeted_amt
                            budget_internal.append((0, 0, res.get_line_asset(cs, amount)))

            # subcon ids
            for cs in res.job_sheet_id.material_subcon_ids:
                if line.project_scope and line.section_name:
                    for scope in line.project_scope:
                        for section in line.section_name:
                            if (cs.project_scope.id == scope.id) and (cs.section_name.id == section.id):
                                amount = cs.subcon_amount_total
                                budget_subcon.append((0, 0, res.get_line_subcon(cs, amount)))
                elif line.project_scope and not line.section_name:
                    for scope in line.project_scope:
                        if (cs.project_scope.id == scope.id):
                            amount = cs.subcon_amount_total
                            budget_subcon.append((0, 0, res.get_line_subcon(cs, amount)))

            budget = res.env['project.budget'].create({
                'project_id': res.project_id.id,
                'cost_sheet': res.job_sheet_id.id,
                'analytic_group_id': [(6, 0, [v.id for v in res.job_sheet_id.account_tag_ids])],
                'period': line.period.id,
                'month': line.month.id,
                'bd_start_date': line.bd_start_date,
                'bd_end_date': line.bd_end_date,
                'budget_material_ids': budget_material,
                'budget_labour_ids': budget_labour,
                'budget_internal_asset_ids': budget_internal,
                'budget_equipment_ids': budget_equipment,
                'budget_subcon_ids': budget_subcon,
                'budget_overhead_ids': budget_overhead,
            })

            budget._amount_total()

            budget.sudo().onchange_approving_matrix_lines()
            budget.get_gop_material_table()
            budget.get_gop_labour_table()
            budget.get_gop_overhead_table()
            budget.get_gop_equipment_table()

    def action_approved(self):
        for res in self:
            res.project_id.write({
                'budgeting_method': res.budgeting_method,
                'budgeting_period': res.budgeting_period
            })
            if res.project_id.act_start_date == False:
                res.project_id.write({
                    'act_start_date': res.act_start_date,
                })
            if res.budgeting_period == 'monthly':
                res.create_project_budget(res)
                res.job_sheet_id.write({'state': 'in_progress'})
            elif res.budgeting_period == 'custom':
                res.create_project_budget(res)
                res.job_sheet_id.write({'state': 'in_progress'})
            else:
                res.job_sheet_id.write({'state': 'in_progress'})

    def get_monthly_period(self):
        for res in self:
            if self.budgeting_period:
                budget = []
                for per_line in res.period.budget_period_line_ids:
                    budget.append((0, 0, {
                        'month': per_line.id,
                    }))
                res.project_budget_ids = budget

    def get_budget_period(self):
        for res in self:
            period_id = res.env['project.budget.period'].sudo().search([('project.id', '=', res.project_id.id)],
                                                                       limit=1)
            if period_id:
                res.write({'period': period_id})
            else:
                period_id = self.env['project.budget.period'].create({
                    'name': self.project_id.name,
                    'project': self.project_id.id,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'branch_id': self.project_id.branch_id.id,
                })
                period_id.sudo().action_create_period()
                period_id.sudo().action_open()
                res.write({'period': period_id})

    @api.onchange('budgeting_period')
    def onchange_budgeting_period(self):
        self.project_budget_ids = [(5, 0, 0)]
        for res in self:
            if res.budgeting_period == 'monthly':
                self.get_budget_period()

    @api.onchange('period', 'budgeting_period')
    def onchange_period(self):
        self.project_budget_ids = [(5, 0, 0)]
        if self.budgeting_period and self.period:
            if self.budgeting_period == 'monthly':
                self.get_monthly_period()
            else:
                pass

    @api.onchange('project_id')
    def onchange_project_id(self):
        for res in self:
            if res.project_id:
                res.act_start_date_proj = res.project_id.act_start_date

    @api.onchange('act_start_date_proj')
    def onchange_act_start_date_proj(self):
        for res in self:
            if res.act_start_date_proj:
                res.act_start_date = res.act_start_date_proj

    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')

    @api.depends('project_id.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            pro = rec.project_id
            scope_ids = []
            if pro.project_scope_ids:
                for line in pro.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

    @api.onchange('project_budget_ids')
    def _onchange_project_budget_ids(self):
        # project_section_ids = rec.env['section.project'].search([('section_id', '=', rec.project_id.id)])
        # for budget in rec.project_budget_ids:
        #     if budget.section_name.ids:
        #         for section in budget.section_name:
        #             if (project_section_ids.filtered(lambda x: x.section.id == section._origin.id).project_scope.id
        #                     not in budget.project_scope.ids):
        #                 budget.section_name = [(3, section.id)]
        pass


class CostSheetBudgetLine(models.TransientModel):
    _name = 'cost.sheet.budget.line'
    _description = 'Cost Sheet Budget Line'

    # fields
    cost_sheet_wizard_id = fields.Many2one(comodel_name='cost.sheet.approval.wizard',
                                           string='Cost Sheet Approval Wizard')
    project_id = fields.Many2one(related='cost_sheet_wizard_id.project_id', string='Project')
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'), ], string='Budgeting Period',
        related="cost_sheet_wizard_id.budgeting_period")
    period = fields.Many2one('project.budget.period', string='Period', related="cost_sheet_wizard_id.period")
    month = fields.Many2one('budget.period.line', string='Month', domain="[('budget_period_line_id','=', period)]")
    bd_start_date = fields.Date('Budget Start Date')
    bd_end_date = fields.Date('Budget End Date')
    project_scope = fields.Many2many('project.scope.line', string='Project Scope')
    section_name = fields.Many2many('section.line', string='Section')
    variable_ref = fields.Many2many('variable.template', string='Variable')

    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('project_id.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            # if rec.project_id.project_section_ids:
            #     for line in rec.project_id.project_section_ids:
            #         for res in rec.project_scope:
            #             if res._origin.id:
            #                 if res.id == line.project_scope.id or res._origin.id == line.project_scope.id:
            #                     section.append(line.section.id)
            #             else:
            #                 if res.id == line.project_scope.id:
            #                     section.append(line.section.id)
            rec.project_section_computed = False
            # rec.project_section_computed = False

    @api.onchange('project_scope', 'section_name')
    def _onchange_section_ids(self):
        for rec in self:
            section_ids = []
            if rec.project_id.project_section_ids:
                for line in rec.project_id.project_section_ids:
                    if line.section and line.project_scope.id in rec.project_scope.ids:
                        section_ids.append(line.section.id)

                # Remove section if corresponding scope is removed
                for section in rec.section_name:
                    project_sections = rec.project_id.project_section_ids.filtered(
                        lambda x: x.section.id == section._origin.id)
                    is_exist = False
                    for item in project_sections:
                        if item.project_scope.id in rec.project_scope.ids:
                            is_exist = True
                    if not is_exist:
                        rec.section_name = [(3, section.id)]
            return {'domain': {'section_name': [('id', 'in', section_ids)]}}

    @api.onchange('month')
    def _onchange_month(self):
        for rec in self:
            if not rec.budgeting_period == "custom":
                if len(rec.cost_sheet_wizard_id.project_budget_ids.filtered(lambda x: x.month.id == rec.month.id)) > 2:
                    raise ValidationError(_('Month already exists.'))

    # @api.onchange('project_scope')
    # def onchange_project_scope(self):
    #     scope_ids = []
    #     for res in self:
    #         for scope in res.project_scope:
    #             scope_ids = [(6, 0, scope.name)]
    #         return {'domain': {'section_name': [('project_scope.name', 'in', scope_ids)]}}
