# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import datetime, date
import json


class InheritedInternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    project = fields.Many2one('project.project', 'Project')
    budgeting_method = fields.Selection([
        ('product_budget', 'Based on Product Budget'),
        ('gop_budget', 'Based on Group of Product Budget'),
        ('budget_type', 'Based on Budget Type'),
        ('total_budget', 'Based on Total Budget')], string='Budgeting Method', related='project.budgeting_method',
        store=True)
    budgeting_period = fields.Selection([
        ('project', 'Project Length Budgeting'),
        ('monthly', 'Monthly Budgeting'),
        ('custom', 'Custom Time Budgeting'), ], string='Budgeting Period', related='project.budgeting_period',
        store=True)
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    project_budget = fields.Many2one('project.budget', string='Project Budget')
    type_of_mr = fields.Selection([('material', 'Material'), ('labour', 'Labour'), ('overhead', 'Overhead')],
                                  string="Type Of MR")
    is_from_itr_wizard = fields.Boolean('Is From ITR Wizard')

    @api.onchange('project')
    def _onchange_project(self):
        for rec in self:
            for proj in rec.project:
                # self.cost_sheet = rec.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', '!=', 'cancelled')])
                self.analytic_account_group_ids = proj.analytic_idz
                stock_warehouse = self.env['stock.warehouse'].search([('name', '=', proj.name)], limit=1)
                rec.write({'destination_warehouse_id': stock_warehouse})
                self.cost_sheet = rec.project.cost_sheet
                self.branch_id = rec.project.branch_id

    def action_done(self):
        res = super(InheritedInternalTransfer, self).action_done()
        if self.project and self.mr_id:
            mr_rec = self.env['material.request'].search([('id', '=', self.mr_id.ids)])
            for ir_line in self.product_line_ids:
                for mr_line in mr_rec.product_line:
                    if ir_line.project_scope.id == mr_line.project_scope.id and ir_line.section.id == mr_line.section.id and ir_line.group_of_product.id == mr_line.group_of_product.id and ir_line.product_id.id == mr_line.product.id:
                        # mr_line.done_qty = mr_line.done_qty + ir_line.qty
                        mr_line.itr_done_qty += ir_line.transfer_qty
                        mr_line.itr_returned_qty += ir_line.return_qty
        return res

    def reserve_budget_amount(self, line):
        if self.type_of_mr == 'material':
            if line.cs_material_id:
                line.cs_material_id.reserved_amt += (line.cs_material_id.price_unit * line.qty)
            if line.cs_material_gop_id:
                line.cs_material_gop_id.reserved_amt += (line.cs_material_id.price_unit * line.qty)
            if self.budgeting_period in ['custom', 'project']:
                if line.bd_material_id:
                    line.bd_material_id.amt_res += (line.bd_material_id.price_unit * line.qty)
                if line.bd_material_gop_id:
                    line.bd_material_gop_id.amt_res += (line.bd_material_id.price_unit * line.qty)
        elif self.type_of_mr == 'overhead':
            if line.cs_overhead_id:
                line.cs_overhead_id.reserved_amt += (line.cs_overhead_id.price_unit * line.qty)
            if line.cs_overhead_gop_id:
                line.cs_overhead_gop_id.reserved_amt += (line.cs_overhead_id.price_unit * line.qty)
            if self.budgeting_period in ['custom', 'project']:
                if line.bd_overhead_id:
                    line.bd_overhead_id.amt_res += (line.bd_overhead_id.price_unit * line.qty)
                if line.bd_overhead_gop_id:
                    line.bd_overhead_gop_id.amt_res += (line.bd_overhead_id.price_unit * line.qty)

    def action_confirm(self):
        res = super(InheritedInternalTransfer, self).action_confirm()
        stock_picking = self.env['stock.picking'].search([('transfer_id', '=', self.id)])
        for line in self.product_line_ids:
            self.reserve_budget_amount(line)
        for stock in stock_picking:
            if stock.transfer_id.project:
                for move in stock.move_ids_without_package:
                    if not move.project_scope and not move.section:
                        internal_transfer_line = self.product_line_ids.filtered(
                            lambda r: r.product_id.id == move.product_id.id and r.qty == move.product_uom_qty and
                                      r.group_of_product.id in move.product_id.group_of_product.ids)
                        stock_move_line = stock.move_ids_without_package.filtered(
                            lambda r: r.product_id.id == move.product_id.id and r.product_uom_qty == move.product_uom_qty and
                                        r.group_of_product.id in move.product_id.group_of_product.ids)
                        scope_section = {'scope': [], 'section': []}
                        if len(internal_transfer_line) > 1:
                            for line in internal_transfer_line:
                                scope_section['scope'].append(line.project_scope.id)
                                scope_section['section'].append(line.section.id)
                        if internal_transfer_line:
                            if len(internal_transfer_line) > 1:
                                for i in range(len(internal_transfer_line)):
                                    stock_move_line[i].write({
                                        'project_scope': scope_section['scope'][i],
                                        'section': scope_section['section'][i],
                                        'group_of_product': internal_transfer_line[i].group_of_product.id
                                    })
                                    stock_move_line[i]._onchange_group_of_product()
                            else:
                                move.write({
                                    'project_scope': internal_transfer_line.project_scope.id,
                                    'section': internal_transfer_line.section.id,
                                    'group_of_product': internal_transfer_line.group_of_product.id
                                })
                                move._onchange_group_of_product()
        return res


class InheritedInternalTransferLine(models.Model):
    _inherit = 'internal.transfer.line'

    project = fields.Many2one(related='product_line.project', string='Project')
    cs_material_gop_id = fields.Many2one('material.gop.material', 'CS Material ID')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', 'CS Labour ID')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', 'CS Overhead ID')

    bd_material_gop_id = fields.Many2one('budget.gop.material', 'BD Material ID')
    bd_labour_gop_id = fields.Many2one('budget.gop.labour', 'BD Labour ID')
    bd_overhead_gop_id = fields.Many2one('budget.gop.overhead', 'BD Overhead ID')

    cs_material_id = fields.Many2one('material.material', 'CS Material ID')
    cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID')
    cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID')
    bd_material_id = fields.Many2one('budget.material', 'BD Material ID')
    bd_labour_id = fields.Many2one('budget.labour', 'BD Labour ID')
    bd_overhead_id = fields.Many2one('budget.overhead', 'BD Overhead ID')
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', string="Section")
    variable = fields.Many2one('variable.template', string="Variable")
    group_of_product = fields.Many2one('group.of.product', 'Group of Product')
    project_scope_domain = fields.Char('Project Scope Domain', compute='_compute_project_scope_domain')

    @api.onchange('project', 'project_scope')
    def _compute_project_scope_domain(self):
        for rec in self:
            if rec.product_line and rec.product_line.type_of_mr:
                project_scope_domain = []
                if rec.product_line.project_budget:
                    if rec.product_line.type_of_mr == 'material':
                        project_scope_domain = [('id', 'in', rec.product_line.project_budget.budget_material_ids.mapped(
                            'project_scope').ids)]
                    elif rec.product_line.type_of_mr == 'overhead':
                        project_scope_domain = [('id', 'in', rec.product_line.project_budget.budget_overhead_ids.mapped(
                            'project_scope').ids)]
                    rec.project_scope_domain = json.dumps(project_scope_domain)
                else:
                    if rec.product_line.type_of_mr == 'material':
                        project_scope_domain = [('id', 'in', rec.product_line.cost_sheet.material_ids.mapped(
                            'project_scope').ids)]
                    elif rec.product_line.type_of_mr == 'overhead':
                        project_scope_domain = [('id', 'in', rec.product_line.cost_sheet.material_overhead_ids.mapped(
                            'project_scope').ids)]
                    rec.project_scope_domain = json.dumps(project_scope_domain)
            else:
                rec.project_scope_domain = json.dumps([('id', 'in', [])])

    @api.onchange('project_scope',)
    def _onchange_project_scope(self):
        for rec in self:
            section_domain = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section_domain.append(line.section.id)
                    return {'domain': {'section': [('id', 'in', section_domain)]}}
                else:
                    return {'domain': {'section': [('id', 'in', section_domain)]}}
            else:
                return {'domain': {'section': [('id', 'in', section_domain)]}}

    @api.onchange('group_of_product', 'product_id')
    def _onchange_group_of_product(self):
        for line in self:
            if line.product_line.project:
                if line.product_line.budgeting_method != 'gop_budget':
                    if line.product_line.type_of_mr == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        if line.product_line.project_budget:
                            if not line.cs_material_id:
                                line.cs_material_id = self.env['material.material'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                                line.bd_material_id = self.env['budget.material'].search(
                                    [('budget_id', '=', line.product_line.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                        else:
                            if not line.cs_material_id:
                                line.cs_material_id = self.env['material.material'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                    elif line.product_line.type_of_mr == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        if line.product_line.project_budget:
                            if not line.cs_labour_id:
                                line.cs_labour_id = self.env['material.labour'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                                line.bd_labour_id = self.env['budget.labour'].search(
                                    [('budget_id', '=', line.product_line.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                        else:
                            if not line.cs_labour_id:
                                line.cs_labour_id = self.env['material.labour'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                    elif line.product_line.type_of_mr == 'overhead':
                        line.cs_overhead_id = False
                        line.bd_overhead_id = False
                        if line.product_line.project_budget:
                            if not line.cs_overhead_id:
                                line.cs_overhead_id = self.env['material.overhead'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                                line.bd_overhead_id = self.env['budget.overhead'].search(
                                    [('budget_id', '=', line.product_line.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                        else:
                            if not line.cs_overhead_id:
                                line.cs_overhead_id = self.env['material.overhead'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_id.id)])
                else:
                    if line.product_line.type_of_mr == 'material':
                        line.cs_material_gop_id = False
                        line.bd_material_gop_id = False
                        if line.product_line.project_budget:
                            if not line.cs_material_gop_id:
                                line.cs_material_gop_id = self.env['material.gop.material'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_material_gop_id = self.env['budget.gop.material'].search(
                                    [('budget_id', '=', line.product_line.project_budget.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                        else:
                            if not line.cs_material_gop_id:
                                line.cs_material_gop_id = self.env['material.gop.material'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])

                    elif line.product_line.type_of_mr == 'labour':
                        line.cs_labour_gop_id = False
                        line.bd_labour_gop_id = False
                        if line.product_line.project_budget:
                            if not line.cs_labour_gop_id:
                                line.cs_labour_gop_id = self.env['material.gop.labour'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_labour_gop_id = self.env['budget.gop.labour'].search(
                                    [('budget_id', '=', line.product_line.project_budget.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                        else:
                            if not line.cs_labour_gop_id:
                                line.cs_labour_gop_id = self.env['material.gop.labour'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])

                    elif line.product_line.type_of_mr == 'overhead':
                        line.cs_overhead_gop_id = False
                        line.bd_overhead_gop_id = False
                        if line.product_line.project_budget:
                            if not line.cs_overhead_gop_id:
                                line.cs_overhead_gop_id = self.env['material.gop.overhead'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search(
                                    [('budget_id', '=', line.product_line.project_budget.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                        else:
                            if not line.cs_overhead_gop_id:
                                line.cs_overhead_gop_id = self.env['material.gop.overhead'].search(
                                    [('job_sheet_id', '=', line.product_line.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('variable_ref', '=', line.variable.id),
                                     ('group_of_product', '=', line.group_of_product.id)])


class InheritedStockMove(models.Model):
    _inherit = 'stock.move'

    # Material
    cs_material_id = fields.Many2one('material.material', string='CS Material ID')
    cs_material_gop_id = fields.Many2one('material.gop.material', string='CS Material GOP ID')
    bd_material_id = fields.Many2one('budget.material', string='BD Material ID')
    bd_material_ids = fields.Many2many('budget.material', string='BD Material IDS')
    bd_material_gop_id = fields.Many2one('budget.gop.material', string='BD Material GOP ID')
    bd_material_gop_ids = fields.Many2many('budget.gop.material', string='BD Material GOP IDS')

    # Labour
    cs_labour_id = fields.Many2one('material.labour', string='CS Labour ID')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', string='CS Labour GOP ID')
    bd_labour_id = fields.Many2one('budget.labour', string='BD Labour ID')
    bd_labour_ids = fields.Many2many('budget.labour', string='BD Labour IDS')
    bd_labour_gop_id = fields.Many2one('budget.gop.labour', string='BD Labour GOP ID')
    bd_labour_gop_ids = fields.Many2many('budget.gop.labour', string='BD Labour GOP IDS')

    # Overhead
    cs_overhead_id = fields.Many2one('material.overhead', string='CS Overhead ID')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', string='CS Overhead GOP ID')
    bd_overhead_id = fields.Many2one('budget.overhead', string='BD Overhead ID')
    bd_overhead_ids = fields.Many2many('budget.overhead', string='BD Overhead IDS')
    bd_overhead_gop_id = fields.Many2one('budget.gop.overhead', string='BD Overhead GOP ID')
    bd_overhead_gop_ids = fields.Many2many('budget.gop.overhead', string='BD Overhead GOP IDS')

    # Equipment
    cs_equipment_id = fields.Many2one('material.equipment', string='CS Equipment ID')
    cs_equipment_gop_id = fields.Many2one('material.gop.equipment', string='CS Equipment ID')
    bd_equipment_id = fields.Many2one('budget.equipment', string='BD equipment ID')
    bd_equipment_ids = fields.Many2many('budget.equipment', string='BD Equipment IDS')
    bd_equipment_gop_id = fields.Many2one('budget.gop.equipment', string='BD Equipment GOP ID')
    bd_equipment_gop_ids = fields.Many2many('budget.gop.equipment', string='BD Equipment GOP IDS')

    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')

    @api.onchange('group_of_product', 'product_id')
    def _onchange_group_of_product(self):
        for line in self:
            internal_transfer_id = line.picking_id.transfer_id
            if line.picking_id.transfer_id.project:
                # if internal_transfer_id.budgeting_method != 'gop_budget':
                if internal_transfer_id.type_of_mr == 'material':
                    line.cs_material_id = False
                    line.bd_material_id = False
                    if internal_transfer_id.project_budget:
                        if not line.cs_material_id:
                            # line.cs_material_id = self.env['material.material'].search(
                            #     [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                            #      ('project_scope', '=', line.project_scope.id),
                            #      ('section_name', '=', line.section.id),
                            #      ('group_of_product', '=', line.group_of_product.id),
                            #      ('product_id', '=', line.product_id.id)])
                            line.cs_material_id = internal_transfer_id.cost_sheet.material_ids.filtered(
                                lambda r: r.project_scope.id == line.project_scope.id and
                                          r.section_name.id == line.section.id and
                                          r.group_of_product.id == line.group_of_product.id and
                                          r.product_id.id == line.product_id.id)
                            # line.bd_material_id = self.env['budget.material'].search(
                            #     [('budget_id', '=', internal_transfer_id.project_budget.id),
                            #      ('project_scope', '=', line.project_scope.id),
                            #      ('section_name', '=', line.section.id),
                            #      ('group_of_product', '=', line.group_of_product.id),
                            #      ('product_id', '=', line.product_id.id)])
                            line.bd_material_id = internal_transfer_id.project_budget.budget_material_ids.filtered(
                                lambda r: r.project_scope.id == line.project_scope.id and
                                          r.section_name.id == line.section.id and
                                          r.group_of_product.id == line.group_of_product.id and
                                          r.product_id.id == line.product_id.id)
                    else:
                        if not line.cs_material_id:
                            line.cs_material_id = internal_transfer_id.cost_sheet.material_ids.filtered(
                                lambda r: r.project_scope.id == line.project_scope.id and
                                          r.section_name.id == line.section.id and
                                          r.group_of_product.id == line.group_of_product.id and
                                          r.product_id.id == line.product_id.id)
                elif internal_transfer_id.type_of_mr == 'labour':
                    line.cs_labour_id = False
                    line.bd_labour_id = False
                    if internal_transfer_id.project_budget:
                        if not line.cs_labour_id:
                            line.cs_labour_id = self.env['material.labour'].search(
                                [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_id.id)])
                            line.bd_labour_id = self.env['budget.labour'].search(
                                [('budget_id', '=', internal_transfer_id.project_budget.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_id.id)])
                    else:
                        if not line.cs_labour_id:
                            line.cs_labour_id = self.env['material.labour'].search(
                                [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                                 ('project_scope', '=', line.project_scope.id),
                                 ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_id.id)])
                elif internal_transfer_id.type_of_mr == 'overhead':
                    line.cs_overhead_id = False
                    line.bd_overhead_id = False
                    if internal_transfer_id.project_budget:
                        if not line.cs_overhead_id:
                            # line.cs_overhead_id = self.env['material.overhead'].search(
                            #     [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                            #      ('project_scope', '=', line.project_scope.id),
                            #      ('section_name', '=', line.section.id),
                            #      ('group_of_product', '=', line.group_of_product.id),
                            #      ('product_id', '=', line.product_id.id)])
                            line.cs_overhead_id = internal_transfer_id.cost_sheet.material_overhead_ids.filtered(
                                lambda r: r.project_scope.id == line.project_scope.id and
                                          r.section_name.id == line.section.id and
                                          r.group_of_product.id == line.group_of_product.id and
                                          r.product_id.id == line.product_id.id)
                            # line.bd_overhead_id = self.env['budget.overhead'].search(
                            #     [('budget_id', '=', internal_transfer_id.project_budget.id),
                            #      ('project_scope', '=', line.project_scope.id),
                            #      ('section_name', '=', line.section.id),
                            #      ('group_of_product', '=', line.group_of_product.id),
                            #      ('product_id', '=', line.product_id.id)])
                            line.bd_overhead_id = internal_transfer_id.project_budget.budget_overhead_ids.filtered(
                                lambda r: r.project_scope.id == line.project_scope.id and
                                          r.section_name.id == line.section.id and
                                          r.group_of_product.id == line.group_of_product.id and
                                          r.product_id.id == line.product_id.id)
                    else:
                        if not line.cs_overhead_id:
                            line.cs_overhead_id = internal_transfer_id.cost_sheet.material_overhead_ids.filtered(
                                lambda r: r.project_scope.id == line.project_scope.id and
                                          r.section_name.id == line.section.id and
                                          r.group_of_product.id == line.group_of_product.id and
                                          r.product_id.id == line.product_id.id)
                if internal_transfer_id.budgeting_method == 'gop_budget':
                    if internal_transfer_id.type_of_mr == 'material':
                        line.cs_material_gop_id = False
                        line.bd_material_gop_id = False
                        if internal_transfer_id.project_budget:
                            if not line.cs_material_gop_id:
                                # line.cs_material_gop_id = self.env['material.gop.material'].search(
                                #     [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                                #      ('project_scope.name', '=', line.project_scope.name),
                                #      ('section_name.name', '=', line.section.name),
                                #      ('group_of_product', '=', line.group_of_product.id)])
                                line.cs_material_gop_id = internal_transfer_id.cost_sheet.material_gop_ids.filtered(
                                    lambda r: r.project_scope.name == line.project_scope.name and
                                              r.section_name.name == line.section.name and
                                              r.group_of_product.id == line.group_of_product.id)
                                # line.bd_material_gop_id = self.env['budget.gop.material'].search(
                                #     [('budget_id', '=', internal_transfer_id.project_budget.id),
                                #      ('project_scope.name', '=', line.project_scope.name),
                                #      ('section_name.name', '=', line.section.name),
                                #      ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_material_gop_id = internal_transfer_id.project_budget.budget_material_ids.filtered(
                                    lambda r: r.project_scope.name == line.project_scope.name and
                                              r.section_name.name == line.section.name and
                                              r.group_of_product.id == line.group_of_product.id)
                        else:
                            if not line.cs_material_gop_id:
                                line.cs_material_gop_id = internal_transfer_id.cost_sheet.material_gop_ids.filtered(
                                    lambda r: r.project_scope.name == line.project_scope.name and
                                              r.section_name.name == line.section.name and
                                              r.group_of_product.id == line.group_of_product.id)

                    elif internal_transfer_id.type_of_mr == 'labour':
                        line.cs_labour_gop_id = False
                        line.bd_labour_gop_id = False
                        if internal_transfer_id.project_budget:
                            if not line.cs_labour_gop_id:
                                line.cs_labour_gop_id = self.env['material.gop.labour'].search(
                                    [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),

                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_labour_gop_id = self.env['budget.gop.labour'].search(
                                    [('budget_id', '=', internal_transfer_id.project_budget.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),
                                     ('group_of_product', '=', line.group_of_product.id)])
                        else:
                            if not line.cs_labour_gop_id:
                                line.cs_labour_gop_id = self.env['material.gop.labour'].search(
                                    [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                                     ('project_scope.name', '=', line.project_scope.name),
                                     ('section_name.name', '=', line.section.name),

                                     ('group_of_product', '=', line.group_of_product.id)])

                    elif internal_transfer_id.type_of_mr == 'overhead':
                        line.cs_overhead_gop_id = False
                        line.bd_overhead_gop_id = False
                        if internal_transfer_id.project_budget:
                            if not line.cs_overhead_gop_id:
                                # line.cs_overhead_gop_id = self.env['material.gop.overhead'].search(
                                #     [('job_sheet_id', '=', internal_transfer_id.cost_sheet.id),
                                #      ('project_scope.name', '=', line.project_scope.name),
                                #      ('section_name.name', '=', line.section.name),
                                #      ('group_of_product', '=', line.group_of_product.id)])
                                line.cs_overhead_gop_id = internal_transfer_id.cost_sheet.material_overhead_ids.filtered(
                                    lambda r: r.project_scope.name == line.project_scope.name and
                                              r.section_name.name == line.section.name and
                                              r.group_of_product.id == line.group_of_product.id)
                                # line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search(
                                #     [('budget_id', '=', internal_transfer_id.project_budget.id),
                                #      ('project_scope.name', '=', line.project_scope.name),
                                #      ('section_name.name', '=', line.section.name),
                                #      ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_overhead_gop_id = internal_transfer_id.project_budget.budget_overhead_ids.filtered(
                                    lambda r: r.project_scope.name == line.project_scope.name and
                                              r.section_name.name == line.section.name and
                                              r.group_of_product.id == line.group_of_product.id)
                        else:
                            if not line.cs_overhead_gop_id:
                                line.cs_overhead_gop_id = internal_transfer_id.cost_sheet.material_overhead_ids.filtered(
                                    lambda r: r.project_scope.name == line.project_scope.name and
                                              r.section_name.name == line.section.name and
                                              r.group_of_product.id == line.group_of_product.id)

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super(InheritedStockMove, self)._prepare_merge_moves_distinct_fields()
        if self.project_scope and self.section and self.group_of_product:
            distinct_fields += ['project_scope', 'section', 'group_of_product']
        return distinct_fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def update_cs_gop_material(self, res, line):
        line.cs_material_gop_id.reserved_amt -= (line.cs_material_id.price_unit * line.quantity_done)
        line.cs_material_gop_id.transferred_amt += (line.cs_material_id.price_unit * line.quantity_done)

    def update_cs_gop_labour(self, res, line):
        line.cs_labour_gop_id.transferred_amt += (line.product_id.standard_price * line.quantity_done)

    def update_cs_gop_overhead(self, res, line):
        line.cs_equipment_gop_id.reserved_amt -= (line.cs_overhead_id.price_unit * line.quantity_done)
        line.cs_overhead_gop_id.transferred_amt += (line.cs_overhead_id.price_unit * line.quantity_done)

    def update_cs_material(self, res, line):
        line.cs_material_id.reserved_amt -= (line.cs_material_id.price_unit * line.quantity_done)
        line.cs_material_id.transferred_qty += line.quantity_done
        line.cs_material_id.transferred_amt += (line.cs_material_id.price_unit * line.quantity_done)
        line.cs_material_id.reserved_qty -= line.quantity_done
        line.cs_material_id.received_qty += line.quantity_done

    def update_cs_labour(self, res, line):
        line.cs_labour_id.transferred_qty += line.quantity_done
        line.cs_labour_id.transferred_amt += (line.product_id.standard_price * line.quantity_done)
        line.cs_labour_id.reserved_qty -= line.quantity_done
        line.cs_labour_id.received_qty += line.quantity_done

    def update_cs_overhead(self, res, line):
        line.cs_overhead_id.reserved_amt -= (line.cs_overhead_id.price_unit * line.quantity_done)
        line.cs_overhead_id.transferred_qty += line.quantity_done
        line.cs_overhead_id.transferred_amt += (line.cs_overhead_id.price_unit * line.quantity_done)
        line.cs_overhead_id.reserved_qty -= line.quantity_done
        line.cs_overhead_id.received_qty += line.quantity_done

    def update_bd_gop_material(self, res, line):
        line.bd_material_gop_ids.amt_res -= (line.cs_material_id.price_unit * line.quantity_done)
        line.bd_material_gop_id.transferred_amt += (line.cs_material_id.price_unit * line.quantity_done)

    def update_bd_gop_labour(self, res, line):
        line.bd_labour_gop_id.transferred_amt += (line.product_id.standard_price * line.quantity_done)

    def update_bd_gop_overhead(self, res, line):
        line.bd_overhead_gop_ids.amt_res -= (line.cs_overhead_id.price_unit * line.quantity_done)
        line.bd_overhead_gop_id.transferred_amt += (line.cs_overhead_id.price_unit * line.quantity_done)

    def update_bd_material(self, res, line):
        line.bd_material_id.amt_res -= (line.cs_material_id.price_unit * line.quantity_done)
        line.bd_material_id.transferred_qty += line.quantity_done
        line.bd_material_id.transferred_amt += (line.cs_material_id.price_unit * line.quantity_done)
        line.bd_material_id.qty_res -= line.quantity_done
        line.bd_material_id.qty_received += line.quantity_done

    def update_bd_labour(self, res, line):
        line.bd_labour_id.transferred_qty += line.quantity_done
        line.bd_labour_id.transferred_amt += (line.product_id.standard_price * line.quantity_done)
        line.bd_labour_id.qty_res -= line.quantity_done
        line.bd_labour_id.qty_received += line.quantity_done

    def update_bd_overhead(self, res, line):
        line.bd_overhead_id.amt_res -= (line.cs_overhead_id.price_unit * line.quantity_done)
        line.bd_overhead_id.transferred_qty += line.quantity_done
        line.bd_overhead_id.transferred_amt += (line.cs_overhead_id.price_unit * line.quantity_done)
        line.bd_overhead_id.qty_res -= line.quantity_done
        line.bd_overhead_id.qty_received += line.quantity_done

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for rec in self:
            transferred_product = []
            is_actualization = False
            if type(res) is dict:
                if "res_model" in res:
                    if res["res_model"] != "stock.backorder.confirmation":
                        is_actualization = True
                else:
                    is_actualization = True
            else:
                is_actualization = True

            if is_actualization:
                if rec.is_transfer_in and rec.transfer_id.project:
                    for line in rec.move_ids_without_package:
                        if line.quantity_done > 0:
                            transferred_product.append({'id': line.product_id.id,
                                                        'gop': line.group_of_product.id,
                                                        'qty_done': line.quantity_done,
                                                        'description': line.product_description,
                                                        'state': "in"})
                        if rec.transfer_id.budgeting_method == 'gop_budget':
                            if rec.transfer_id.type_of_mr == 'material':
                                if rec.transfer_id.project_budget:
                                    rec.update_bd_gop_material(rec, line)
                                    rec.update_cs_gop_material(rec, line)
                                else:
                                    rec.update_cs_gop_material(rec, line)
                            elif rec.transfer_id.type_of_mr == 'labour':
                                if rec.transfer_id.project_budget:
                                    rec.update_bd_gop_labour(rec, line)
                                    rec.update_cs_gop_labour(rec, line)
                                else:
                                    rec.update_cs_gop_labour(rec, line)
                            elif rec.transfer_id.type_of_mr == 'overhead':
                                if rec.transfer_id.project_budget:
                                    rec.update_bd_gop_overhead(rec, line)
                                    rec.update_cs_gop_overhead(rec, line)
                                else:
                                    rec.update_cs_gop_overhead(rec, line)
                        else:
                            if rec.transfer_id.type_of_mr == 'material':
                                if rec.transfer_id.project_budget:
                                    rec.update_bd_material(rec, line)
                                    rec.update_cs_material(rec, line)
                                else:
                                    rec.update_cs_material(rec, line)
                            elif rec.transfer_id.type_of_mr == 'labour':
                                if rec.transfer_id.project_budget:
                                    rec.update_bd_labour(rec, line)
                                    rec.update_cs_labour(rec, line)
                                else:
                                    rec.update_cs_labour(rec, line)
                            elif rec.transfer_id.type_of_mr == 'overhead':
                                if rec.transfer_id.project_budget:
                                    rec.update_bd_overhead(rec, line)
                                    rec.update_cs_overhead(rec, line)
                                else:
                                    rec.update_cs_overhead(rec, line)
                elif rec.is_transfer_out and rec.transfer_id.project:
                    for line in rec.move_ids_without_package:
                        if line.quantity_done > 0:
                            transferred_product.append({'id': line.product_id.id,
                                                        'gop': line.group_of_product.id,
                                                        'qty_done': line.quantity_done,
                                                        'description': line.product_description,
                                                        'state': "out"})
            if len(transferred_product) > 0:
                source_project = rec.transfer_id.source_warehouse_id.project
                destination_cost_sheet = rec.transfer_id.cost_sheet
                source_cost_sheet = rec.env['job.cost.sheet'].search([('project_id', '=', source_project.id),
                                                                      ('state', 'in', ['in_progress'])])
                destination_cost_sheet_vals = []
                source_cost_sheet_vals = []

                for j in transferred_product:
                    if j['state'] == 'in':
                        destination_cost_sheet_vals.append((0, 0, {
                            'job_cost_sheet_id': destination_cost_sheet.id,
                            'document_id': rec.id,
                            'name': j['description'] + " (IN)",
                            'date': date.today(),
                            'source_location_id': rec.transfer_id.source_location_id.id,
                            'destination_location_id': rec.transfer_id.destination_location_id.id,
                            'group_of_product_id': j['gop'],
                            'product_id': j['id'],
                            'transferred_qty': j['qty_done']
                        }))
                    elif j['state'] == 'out':
                        source_cost_sheet_vals.append((0, 0, {
                            'job_cost_sheet_id': source_cost_sheet.id,
                            'document_id': rec.id,
                            'name': j['description'] + " (OUT)",
                            'date': date.today(),
                            'source_location_id': rec.transfer_id.source_location_id.id,
                            'destination_location_id': rec.transfer_id.destination_location_id.id,
                            'group_of_product_id': j['gop'],
                            'product_id': j['id'],
                            'transferred_qty': j['qty_done']
                        }))

                if len(destination_cost_sheet_vals) > 0:
                    destination_cost_sheet.interwarehouse_transfer_history_ids = destination_cost_sheet_vals
                if len(source_cost_sheet_vals) > 0:
                    source_cost_sheet.interwarehouse_transfer_history_ids = source_cost_sheet_vals

        return res
