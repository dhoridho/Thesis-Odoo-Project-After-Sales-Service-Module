from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, UserError
from datetime import datetime


class RFQMaterialOrdersMenu(models.Model):
    _inherit = 'purchase.order'

    is_orders = fields.Boolean('Is Orders', default=False)

    @api.onchange('is_orders')
    def _onchange_is_orders(self):
        context = dict(self.env.context) or {}
        if context.get('orders'):
            self.is_orders = True


class RFQMaterialOrdersMenuLines(models.Model):
    _inherit = 'purchase.order.line'

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

    # Subcon
    cs_subcon_id = fields.Many2one('material.subcon', 'CS Subcon ID')
    bd_subcon_id = fields.Many2one('budget.subcon', 'BD Subcon ID')

    type = fields.Selection([('material', 'Material'),
                             ('labour', 'Labour'),
                             ('overhead', 'Overhead'),
                             ('equipment', 'Equipment'),
                             ('split', 'Split')],
                            string="Type")
    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    subcon_id = fields.Many2one('variable.template', 'Subcon')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    budget_quantity = fields.Float('Budget Quantity')
    budget_unit_price = fields.Float('Budget Unit Price')
    remining_budget_amount = fields.Float('Budget Amount Left')
    is_orders = fields.Boolean('Is Orders', default=False)
    billed_amt = fields.Float(string='BILLED AMOUNT')
    paid_amt = fields.Float(string='PAID AMOUNT')
    is_reserved = fields.Boolean('Reserved', default=False)

    project = fields.Many2one(related='order_id.project', string='Project')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    is_default_unit_price_budget = fields.Boolean('Default Unit Price Budget',
                                                  compute='_compute_default_unit_price_budget')

    @api.depends('cs_material_id', 'cs_overhead_id', 'cs_equipment_id', 'cs_subcon_id', 'bd_material_id',
                 'bd_overhead_id', 'bd_equipment_id', 'bd_subcon_id')
    def _compute_default_unit_price_budget(self, is_new_from_purchase_request=False):
        for rec in self:
            if rec.project and ((isinstance(rec.id,
                                            models.NewId) and not rec._origin) or is_new_from_purchase_request):
                if not rec.is_default_unit_price_budget:
                    if rec.type == 'material':
                        if rec.bd_material_id or rec.cs_material_id:
                            rec.price_unit = rec.budget_unit_price
                            rec.is_default_unit_price_budget = True
                        else:
                            rec.is_default_unit_price_budget = False
                    elif rec.type == 'overhead':
                        if rec.bd_overhead_id or rec.cs_overhead_id:
                            rec.price_unit = rec.budget_unit_price
                            rec.is_default_unit_price_budget = True
                        else:
                            rec.is_default_unit_price_budget = False
                    elif rec.type == 'equipment':
                        if rec.bd_equipment_id or rec.cs_equipment_id:
                            rec.price_unit = rec.budget_unit_price
                            rec.is_default_unit_price_budget = True
                        else:
                            rec.is_default_unit_price_budget = False
                    elif rec.type == 'split':
                        if rec.bd_subcon_id or rec.cs_subcon_id:
                            rec.price_unit = rec.budget_unit_price
                            rec.is_default_unit_price_budget = True
                        else:
                            rec.is_default_unit_price_budget = False
                    else:
                        rec.is_default_unit_price_budget = False
                else:
                    rec.is_default_unit_price_budget = True
            else:
                rec.is_default_unit_price_budget = False

    # already include ensure_one in super
    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        res = super(RFQMaterialOrdersMenuLines, self)._prepare_stock_move_vals(picking, price_unit, product_uom_qty,
                                                                               product_uom)

        _id_fields = ['cs_material_id', 'cs_material_gop_id', 'bd_material_id', 'cs_labour_id', 'cs_labour_gop_id',
                      'bd_labour_id', 'cs_overhead_id', 'cs_overhead_gop_id', 'bd_overhead_id', 'cs_equipment_id',
                      'cs_equipment_gop_id', 'bd_equipment_id', 'bd_equipment_gop_id']
        _ids_fields = ['bd_material_ids', 'bd_labour_ids', 'bd_overhead_ids', 'bd_equipment_ids', 'bd_material_gop_ids',
                       'bd_labour_gop_ids', 'bd_overhead_gop_ids', 'bd_equipment_gop_ids']
        for field in _id_fields:
            res[field] = self[field].id if self[field] else False

        for field in _ids_fields:
            res[field] = [(6, 0, self[field])]

        return res

    @api.depends('project.project_section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.project.project_section_ids:
                    for line in rec.project.project_section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            if rec.group_of_product:
                group_of_product = rec.group_of_product.id if rec.group_of_product else False
                return {
                    'domain': {'product_template_id': [('group_of_product', '=', group_of_product)]}
                }
            else:
                return {
                    'domain': {'product_template_id': []}
                }

    # @api.model
    # def create(self, vals):
    #     result = super(RFQMaterialOrdersMenuLines, self).create(vals)
    #     result._onchange_product()
    #     return result

    @api.onchange('type', 'order_id', 'project_scope', 'section', 'product_template_id',
                  'group_of_product')
    def _onchange_product(self):
        for line in self:
            if line.order_id.budgeting_method == 'gop_budget':
                if line.project_scope and line.section and line.group_of_product:
                    if line.type == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False
                        line.cs_material_gop_id = False
                        line.bd_material_gop_id = False
                        line.bd_material_gop_ids = False
                        line.cs_material_id = self.env['material.material'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id),
                             ('product_id', '=', line.product_template_id.id)])
                        line.cs_material_gop_id = self.env['material.gop.material'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.order_id.is_multiple_budget == False:
                            if line.order_id.project_budget:
                                line.bd_material_id = self.env['budget.material'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_template_id.id)])
                                line.bd_material_gop_id = self.env['budget.gop.material'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budget_quantity = line.bd_material_id.qty_left
                                line.budget_unit_price = line.bd_material_id.amount
                                line.remining_budget_amount = line.bd_material_id.amt_left
                            else:
                                line.budget_quantity = line.cs_material_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_material_id.price_unit
                                line.remining_budget_amount = line.cs_material_id.budgeted_amt_left
                        else:
                            budget_gop_ids = []
                            budget_mat_ids = []
                            budget = self.env['budget.gop.material'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            budget_mat = self.env['budget.material'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0, 0, bud.id))

                            if budget_mat:
                                for buds in budget_mat:
                                    budget_mat_ids.append((0, 0, buds.id))
                                    line.budget_unit_price += buds.amount
                                    line.remining_budget_amount += buds.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_material_gop_id.budgeted_amt_left

                            line.bd_material_gop_ids = budget_gop_ids
                            line.bd_material_ids = budget_mat_ids

                    if line.type == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        line.bd_labour_ids = False
                        line.cs_labour_gop_id = False
                        line.bd_labour_gop_id = False
                        line.bd_labour_gop_ids = False
                        line.cs_labour_id = self.env['material.labour'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id),
                             ('product_id', '=', line.product_template_id.id)])
                        line.cs_labour_gop_id = self.env['material.gop.labour'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.order_id.is_multiple_budget == False:
                            if line.order_id.project_budget:
                                line.bd_labour_id = self.env['budget.labour'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_template_id.id)])
                                line.bd_labour_gop_id = self.env['budget.gop.labour'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budget_unit_price = line.bd_labour_id.amount
                                line.remining_budget_amount = line.bd_labour_id.amt_left
                            else:
                                line.budget_unit_price = line.cs_labour_id.price_unit
                                line.remining_budget_amount = line.cs_labour_id.budgeted_amt_left
                        else:
                            budget_gop_ids = []
                            budget_lab_ids = []
                            budget = self.env['budget.gop.labour'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            budget_lab = self.env['budget.labour'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0, 0, bud.id))

                            if budget_lab:
                                for buds in budget_lab:
                                    budget_lab_ids.append((0, 0, buds.id))
                                    line.budget_unit_price += buds.amount
                                    line.remining_budget_amount += buds.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_labour_gop_id.budgeted_amt_left

                            line.bd_labour_gop_ids = budget_gop_ids
                            line.bd_labour_ids = budget_lab_ids

                    if line.type == 'overhead':
                        line.cs_overhead_id = False
                        line.bd_overhead_id = False
                        line.bd_overhead_ids = False
                        line.cs_overhead_gop_id = False
                        line.bd_overhead_gop_id = False
                        line.bd_overhead_gop_ids = False
                        line.cs_overhead_id = self.env['material.overhead'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id),
                             ('product_id', '=', line.product_template_id.id)])
                        line.cs_overhead_gop_id = self.env['material.gop.overhead'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.order_id.is_multiple_budget == False:
                            if line.order_id.project_budget:
                                line.bd_overhead_id = self.env['budget.overhead'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_template_id.id)])
                                line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budget_quantity = line.bd_overhead_id.qty_left
                                line.budget_unit_price = line.bd_overhead_id.amount
                                line.remining_budget_amount = line.bd_overhead_id.amt_left
                            else:
                                line.budget_quantity = line.cs_overhead_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_overhead_id.price_unit
                                line.remining_budget_amount = line.cs_overhead_id.budgeted_amt_left

                        else:
                            budget_gop_ids = []
                            budget_ove_ids = []
                            budget = self.env['budget.gop.overhead'].search(
                                [('budget_id', '=', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            budget_ove = self.env['budget.overhead'].search(
                                [('budget_id', '=', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0, 0, bud.id))

                            if budget_ove:
                                for buds in budget:
                                    budget_ove_ids.append((0, 0, buds.id))
                                    line.budget_unit_price += buds.amount
                                    line.remining_budget_amount += buds.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_overhead_gop_id.budgeted_amt_left

                            line.bd_overhead_gop_ids = budget_gop_ids
                            line.bd_overhead_ids = budget_ove_ids

                    if line.type == 'equipment':
                        line.cs_equipment_id = False
                        line.bd_equipment_id = False
                        line.bd_equipment_ids = False
                        line.cs_equipment_gop_id = False
                        line.bd_equipment_gop_id = False
                        line.bd_equipment_gop_ids = False
                        line.cs_equipment_id = self.env['material.equipment'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id),
                             ('product_id', '=', line.product_template_id.id)])
                        line.cs_equipment_gop_id = self.env['material.gop.equipment'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id)])

                        if line.order_id.is_multiple_budget == False:
                            if line.order_id.project_budget:
                                line.bd_equipment_id = self.env['budget.equipment'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_template_id.id)])
                                line.bd_equipment_gop_id = self.env['budget.gop.equipment'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id)])
                                line.budget_quantity = line.bd_equipment_id.qty_left
                                line.budget_unit_price = line.bd_equipment_id.amount
                                line.remining_budget_amount = line.bd_equipment_id.amt_left
                            else:
                                line.budget_quantity = line.cs_equipment_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_equipment_id.price_unit
                                line.remining_budget_amount = line.cs_equipment_id.budgeted_amt_left

                        else:
                            budget_gop_ids = []
                            budget_equ_ids = []
                            budget = self.env['budget.gop.equipment'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id)])
                            budget_equ = self.env['budget.equipment'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])

                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0, 0, bud.id))

                            if budget_equ:
                                for buds in budget_equ:
                                    budget_equ_ids.append((0, 0, buds.id))
                                    line.budget_unit_price += buds.amount
                                    line.remining_budget_amount += buds.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_equipment_gop_id.budgeted_amt_left

                            line.bd_equipment_gop_ids = budget_gop_ids
                            line.bd_equipment_ids = budget_equ_ids

                    if line.type == 'split':
                        line.cs_subcon_id = False
                        line.bd_subcon_id = False
                        if line.order_id.project_budget:
                            if not line.cs_subcon_id:
                                line.cs_subcon_id = self.env['material.subcon'].search(
                                    [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('variable', '=', line.subcon.id)])
                                line.bd_subcon_id = self.env['budget.subcon'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('subcon_id', '=', line.subcon.id)])

                        else:
                            if not line.cs_subcon_id:
                                line.cs_subcon_id = self.env['material.subcon'].search(
                                    [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('variable', '=', line.subcon_id.id)])

            elif line.order_id.budgeting_method in ('product_budget', 'budget_type', 'total_budget'):
                if line.project_scope and line.section and line.group_of_product and line.product_template_id:
                    if line.type == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False

                        line.cs_material_id = line.order_id.cost_sheet.material_ids.filtered(
                            lambda x: x.project_scope.id == line.project_scope.id
                            and x.section_name.id == line.section.id
                            and x.group_of_product.id == line.group_of_product.id
                            and x.product_id.id == line.product_template_id.product_variant_id.id)

                        if line.order_id.is_multiple_budget is False:
                            if line.order_id.project_budget:
                                line.bd_material_id = line.order_id.project_budget.budget_material_ids.filtered(
                                    lambda x: x.project_scope.id == line.project_scope.id
                                    and x.section_name.id == line.section.id
                                    and x.group_of_product.id == line.group_of_product.id
                                    and x.product_id.id == line.product_template_id.product_variant_id.id)

                                line.budget_quantity = line.bd_material_id.qty_left
                                line.budget_unit_price = line.bd_material_id.amount
                                line.remining_budget_amount = line.bd_material_id.amt_left
                            else:
                                line.budget_quantity = line.cs_material_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_material_id.price_unit
                                line.remining_budget_amount = line.cs_material_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.material'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budget_unit_price += bud.amount
                                    line.remining_budget_amount += bud.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_material_id.budgeted_amt_left

                            line.bd_material_ids = budget_ids

                    if line.type == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        line.bd_labour_ids = False
                        line.cs_labour_id = self.env['material.labour'].search(
                            [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                             ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                             ('group_of_product', '=', line.group_of_product.id),
                             ('product_id', '=', line.product_template_id.id)])

                        if line.order_id.is_multiple_budget == False:
                            if line.order_id.project_budget:
                                line.bd_labour_id = self.env['budget.labour'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id),
                                     ('group_of_product', '=', line.group_of_product.id),
                                     ('product_id', '=', line.product_template_id.id)])
                                line.budget_unit_price = line.bd_labour_id.amount
                                line.remining_budget_amount = line.bd_labour_id.amt_left
                            else:
                                line.budget_unit_price = line.cs_labour_id.price_unit
                                line.remining_budget_amount = line.cs_labour_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.labour'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budget_unit_price += bud.amount
                                    line.remining_budget_amount += bud.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_labour_id.budgeted_amt_left

                            line.bd_labour_ids = budget_ids

                    if line.type == 'overhead':
                        line.cs_overhead_id = False
                        line.bd_overhead_id = False
                        line.bd_overhead_ids = False

                        line.cs_overhead_id = line.order_id.cost_sheet.material_overhead_ids.filtered(
                            lambda x: x.project_scope.id == line.project_scope.id
                            and x.section_name.id == line.section.id
                            and x.group_of_product.id == line.group_of_product.id
                            and x.product_id.id == line.product_template_id.product_variant_id.id)

                        if line.order_id.is_multiple_budget is False:
                            if line.order_id.project_budget:
                                line.bd_overhead_id = line.order_id.project_budget.budget_overhead_ids.filtered(
                                    lambda x: x.project_scope.id == line.project_scope.id
                                    and x.section_name.id == line.section.id
                                    and x.group_of_product.id == line.group_of_product.id
                                    and x.product_id.id == line.product_template_id.product_variant_id.id)

                                line.budget_quantity = line.bd_overhead_id.qty_left
                                line.budget_unit_price = line.bd_overhead_id.amount
                                line.remining_budget_amount = line.bd_overhead_id.amt_left
                            else:
                                line.budget_quantity = line.cs_overhead_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_overhead_id.price_unit
                                line.remining_budget_amount = line.cs_overhead_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.overhead'].search(
                                [('budget_id', '=', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budget_unit_price += bud.amount
                                    line.remining_budget_amount += bud.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_overhead_id.budgeted_amt_left

                            line.bd_overhead_ids = budget_ids

                    if line.type == 'equipment':
                        line.cs_equipment_id = False
                        line.bd_equipment_id = False
                        line.bd_equipment_ids = False

                        line.cs_equipment_id = line.order_id.cost_sheet.material_equipment_ids.filtered(
                            lambda x: x.project_scope.id == line.project_scope.id
                            and x.section_name.id == line.section.id
                            and x.group_of_product.id == line.group_of_product.id
                            and x.product_id.id == line.product_template_id.product_variant_id.id)

                        if line.order_id.is_multiple_budget is False:
                            if line.order_id.project_budget:
                                line.bd_equipment_id = line.order_id.project_budget.budget_equipment_ids.filtered(
                                    lambda x: x.project_scope.id == line.project_scope.id
                                    and x.section_name.id == line.section.id
                                    and x.group_of_product.id == line.group_of_product.id
                                    and x.product_id.id == line.product_template_id.product_variant_id.id)

                                line.budget_quantity = line.bd_equipment_id.qty_left
                                line.budget_unit_price = line.bd_equipment_id.amount
                                line.remining_budget_amount = line.bd_equipment_id.amt_left
                            else:
                                line.budget_quantity = line.cs_equipment_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_equipment_id.price_unit
                                line.remining_budget_amount = line.cs_equipment_id.budgeted_amt_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.equipment'].search(
                                [('budget_id', 'in', line.order_id.multiple_budget_ids.id),
                                 ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id),
                                 ('group_of_product', '=', line.group_of_product.id),
                                 ('product_id', '=', line.product_template_id.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0, 0, bud.id))
                                    line.budget_unit_price += bud.amount
                                    line.remining_budget_amount += bud.amt_left
                            else:
                                line.budget_unit_price = 0
                                line.remining_budget_amount = line.cs_equipment_id.budgeted_amt_left

                            line.bd_equipment_ids = budget_ids

                    if line.type == 'split':
                        line.cs_subcon_id = False
                        line.bd_subcon_id = False
                        if line.order_id.project_budget:
                            if not line.cs_subcon_id:
                                line.cs_subcon_id = self.env['material.subcon'].search(
                                    [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('variable', '=', line.subcon.id)])
                                line.bd_subcon_id = self.env['budget.subcon'].search(
                                    [('budget_id', '=', line.order_id.project_budget.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable', '=', line.variable.id),
                                     ('subcon_id', '=', line.subcon.id)])
                                # line.budget_quantity = line.bd_subcon_id.qty_left
                                line.budget_unit_price = line.bd_subcon_id.amount
                                line.remining_budget_amount = line.bd_subcon_id.amt_left
                        else:
                            if not line.cs_subcon_id:
                                line.cs_subcon_id = self.env['material.subcon'].search(
                                    [('job_sheet_id', '=', line.order_id.cost_sheet.id),
                                     ('project_scope', '=', line.project_scope.id),
                                     ('section_name', '=', line.section.id), ('variable_ref', '=', line.variable.id),
                                     ('variable', '=', line.subcon.id)])
                                # line.budget_quantity = line.cs_subcon_id.budgeted_qty_left
                                line.budget_unit_price = line.cs_subcon_id.price_unit
                                line.remining_budget_amount = line.cs_subcon_id.budgeted_amt_left

    def _cal_billed_amount(self):
        total_billed_amount = 0
        for rec in self:
            if rec.invoice_lines:
                total_billed_amount = (
                                                  rec.invoice_lines.move_id.amount_residual / rec.invoice_lines.move_id.amount_total) * rec.price_subtotal
            return total_billed_amount

    def _cal_billed_quantity(self):
        total_billed_quantity = 0
        for rec in self:
            if rec.invoice_lines:
                total_billed_quantity = (
                                                    rec.invoice_lines.move_id.amount_residual / rec.invoice_lines.move_id.amount_total) * rec.product_qty
            return total_billed_quantity

    def _cal_purchased_amount(self, inv_amount, untaxed_down_payment_amount):
        total_paid_amount = 0
        for rec in self:
            if rec.invoice_lines:
                account_move = rec.invoice_lines[0].move_id
                total_paid_amount = inv_amount / (account_move.subtotal_amount + account_move.down_payment_amount) * (
                            rec.price_subtotal - untaxed_down_payment_amount)
            return total_paid_amount

    def _cal_purchased_quantity(self, inv_amount, untaxed_down_payment_amount):
        total_paid_quantity = 0
        for rec in self:
            if rec.invoice_lines:
                account_move = rec.invoice_lines[0].move_id
                total_paid_quantity = inv_amount / (account_move.subtotal_amount + account_move.down_payment_amount) * (
                            rec.product_qty - (rec.product_qty * (untaxed_down_payment_amount / rec.price_subtotal)))
            return total_paid_quantity

    # billed amount
    def update_billed_material_cs(self, line, total_billed_amount, total_billed_quantity, sign):
        for cs in line.cs_material_id:
            cs.billed_amt += total_billed_amount * sign
            cs.billed_qty += total_billed_quantity * sign

        for gop_cs in line.cs_material_gop_id:
            gop_cs.billed_amt += total_billed_amount * sign

        return line

    def update_billed_material_bd(self, line, total_billed_amount, total_billed_quantity, sign):
        for bd in line.bd_material_id:
            bd.billed_amt += total_billed_amount * sign
            bd.billed_qty += total_billed_quantity * sign

        for gop_bd in line.bd_material_gop_id:
            gop_bd.billed_amt += total_billed_amount * sign

        return line

    def update_billed_labour_cs(self, line, total_billed_amount, total_billed_quantity, sign):
        for cs in line.cs_labour_id:
            cs.billed_amt += total_billed_amount * sign
            cs.billed_qty += total_billed_quantity * sign

        for gop_cs in line.cs_labour_gop_id:
            gop_cs.billed_amt += total_billed_amount * sign

        return line

    def update_billed_labour_bd(self, line, total_billed_amount, total_billed_quantity, sign):
        for bd in line.bd_labour_id:
            bd.billed_amt += total_billed_amount * sign
            bd.billed_qty += total_billed_quantity * sign

        for gop_bd in line.bd_labour_gop_id:
            gop_bd.billed_amt += total_billed_amount * sign

        return line

    def update_billed_overhead_cs(self, line, total_billed_amount, total_billed_quantity, sign):
        for cs in line.cs_overhead_id:
            cs.billed_amt += total_billed_amount * sign
            cs.billed_qty += total_billed_quantity * sign

        for gop_cs in line.cs_overhead_gop_id:
            gop_cs.billed_amt += total_billed_amount * sign

        return line

    def update_billed_overhead_bd(self, line, total_billed_amount, total_billed_quantity, sign):
        for bd in line.bd_overhead_id:
            bd.billed_amt += total_billed_amount * sign
            bd.billed_qty += total_billed_quantity * sign

        for gop_bd in line.bd_overhead_gop_id:
            gop_bd.billed_amt += total_billed_amount * sign

        return line

    def update_billed_equipment_cs(self, line, total_billed_amount, total_billed_quantity, sign):
        for cs in line.cs_equipment_id:
            cs.billed_amt += total_billed_amount * sign
            cs.billed_qty += total_billed_quantity * sign

        for gop_cs in line.cs_equipment_gop_id:
            gop_cs.billed_amt += total_billed_amount * sign

        return line

    def update_billed_equipment_bd(self, line, total_billed_amount, total_billed_quantity, sign):
        for bd in line.bd_equipment_id:
            bd.billed_amt += total_billed_amount * sign
            bd.billed_qty += total_billed_quantity * sign

        for gop_bd in line.bd_equipment_gop_id:
            gop_bd.billed_amt += total_billed_amount * sign

        return line

    def update_billed_subcon_cs(self, line, total_billed_amount, total_billed_quantity, sign):
        for cs in line.cs_subcon_id:
            cs.billed_amt = total_billed_amount * sign
            cs.billed_qty = total_billed_quantity * sign
            return line

    def update_billed_subcon_bd(self, line, total_billed_amount, total_billed_quantity, sign):
        for bd in line.bd_subcon_id:
            bd.billed_amt = total_billed_amount * sign
            bd.billed_qty = total_billed_quantity * sign
            return line

    # paid amount
    def update_purchased_material_cs(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for cs in line.cs_material_id:
            cs.purchased_amt += total_paid_amount
            cs.purchased_qty += total_paid_quantity
            cs.billed_amt -= total_paid_amount
            cs.billed_qty -= total_paid_quantity
            cs.reserved_amt -= total_paid_amount
            cs.reserved_qty -= total_paid_quantity
            cs.po_reserved_qty -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            cs.reserved_return_amount -= reserved_return_amount
            cs.reserved_over_amount -= abs(reserved_over_amount)
            cs.over_amount += abs(reserved_over_amount)

        for gop_cs in line.cs_material_gop_id:
            gop_cs.purchased_amt += total_paid_amount
            gop_cs.billed_amt -= total_paid_amount
            gop_cs.reserved_amt -= total_paid_amount

        return line

    def update_purchased_material_bd(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for bd in line.bd_material_id:
            bd.purchased_amt += total_paid_amount
            bd.purchased_qty += total_paid_quantity
            bd.billed_amt -= total_paid_amount
            bd.billed_qty -= total_paid_quantity
            bd.amt_res -= total_paid_amount
            bd.qty_res -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            bd.reserved_return_amount -= reserved_return_amount
            bd.reserved_over_amount -= abs(reserved_over_amount)
            bd.over_amount += abs(reserved_over_amount)

        for gop_bd in line.bd_material_gop_id:
            gop_bd.purchased_amt += total_paid_amount
            gop_bd.billed_amt -= total_paid_amount
            gop_bd.amt_res -= total_paid_amount

        return line

    def update_purchased_labour_cs(self, line, total_paid_amount, total_paid_quantity):
        for cs in line.cs_labour_id:
            cs.purchased_amt += total_paid_amount
            cs.purchased_qty += total_paid_quantity
            cs.billed_amt -= total_paid_amount
            cs.billed_qty -= total_paid_quantity
            cs.reserved_amt -= total_paid_amount
            cs.reserved_qty -= total_paid_quantity

        for gop_cs in line.cs_labour_gop_id:
            gop_cs.purchased_amt += total_paid_amount
            gop_cs.billed_amt -= total_paid_amount
            gop_cs.reserved_amt -= total_paid_amount

        return line

    def update_purchased_labour_bd(self, line, total_paid_amount, total_paid_quantity):
        for bd in line.bd_labour_id:
            bd.purchased_amt += total_paid_amount
            bd.purchased_qty += total_paid_quantity
            bd.billed_amt -= total_paid_amount
            bd.billed_qty -= total_paid_quantity
            bd.amt_res -= total_paid_amount
            bd.qty_res -= total_paid_quantity

        for gop_bd in line.bd_labour_gop_id:
            gop_bd.purchased_amt += total_paid_amount
            gop_bd.billed_amt -= total_paid_amount
            gop_bd.amt_res -= total_paid_amount

        return line

    def update_purchased_overhead_cs(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for cs in line.cs_overhead_id:
            cs.purchased_amt += total_paid_amount
            cs.purchased_qty += total_paid_quantity
            cs.billed_amt -= total_paid_amount
            cs.billed_qty -= total_paid_quantity
            cs.reserved_amt -= total_paid_amount
            cs.reserved_qty -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            cs.reserved_return_amount -= reserved_return_amount
            cs.reserved_over_amount -= abs(reserved_over_amount)
            cs.over_amount += abs(reserved_over_amount)

        for gop_cs in line.cs_overhead_gop_id:
            gop_cs.purchased_amt += total_paid_amount
            gop_cs.billed_amt -= total_paid_amount
            gop_cs.reserved_amt -= total_paid_amount

        return line

    def update_purchased_overhead_bd(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for bd in line.bd_overhead_id:
            bd.purchased_amt += total_paid_amount
            bd.purchased_qty += total_paid_quantity
            bd.billed_amt -= total_paid_amount
            bd.billed_qty -= total_paid_quantity
            bd.amt_res -= total_paid_amount
            bd.qty_res -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            bd.reserved_return_amount -= reserved_return_amount
            bd.reserved_over_amount -= abs(reserved_over_amount)
            bd.over_amount += abs(reserved_over_amount)

        for gop_bd in line.bd_overhead_gop_id:
            gop_bd.purchased_amt += total_paid_amount
            gop_bd.billed_amt -= total_paid_amount
            gop_bd.amt_res -= total_paid_amount

        return line

    def update_purchased_equipment_cs(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for cs in line.cs_equipment_id:
            # purchase
            cs.purchased_amt += total_paid_amount
            cs.purchased_qty += total_paid_quantity
            # actual
            cs.actual_used_amt += total_paid_amount
            cs.actual_used_qty += total_paid_quantity
            # sub
            cs.billed_amt -= total_paid_amount
            cs.billed_qty -= total_paid_quantity
            cs.reserved_amt -= total_paid_amount
            cs.reserved_qty -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            cs.reserved_return_amount -= reserved_return_amount
            cs.reserved_over_amount -= abs(reserved_over_amount)
            cs.over_amount += abs(reserved_over_amount)

        for gop_cs in line.cs_equipment_gop_id:
            gop_cs.purchased_amt += total_paid_amount
            gop_cs.actual_used_amt += total_paid_amount
            gop_cs.billed_amt -= total_paid_amount
            gop_cs.reserved_amt -= total_paid_amount

        return line

    def update_purchased_equipment_bd(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for bd in line.bd_equipment_id:
            # purchase
            bd.purchased_amt += total_paid_amount
            bd.purchased_qty += total_paid_quantity
            # actual
            bd.amt_used += total_paid_amount
            bd.amt_used += total_paid_quantity
            # sub
            bd.billed_amt -= total_paid_amount
            bd.billed_qty -= total_paid_quantity
            bd.amt_res -= total_paid_amount
            bd.qty_res -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            bd.reserved_return_amount -= reserved_return_amount
            bd.reserved_over_amount -= abs(reserved_over_amount)
            bd.over_amount += abs(reserved_over_amount)

        for gop_bd in line.bd_equipment_gop_id:
            gop_bd.purchased_amt += total_paid_amount
            gop_bd.actual_used_amt += total_paid_amount
            gop_bd.billed_amt -= total_paid_amount
            gop_bd.amt_res -= total_paid_amount

        return line

    def update_purchased_subcon_cs(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for cs in line.cs_subcon_id:
            cs.purchased_amt = total_paid_amount
            cs.purchased_qty = total_paid_quantity
            cs.billed_amt -= total_paid_amount
            cs.billed_qty -= total_paid_quantity
            cs.reserved_amt -= total_paid_amount
            cs.reserved_qty -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            cs.reserved_return_amount -= reserved_return_amount
            cs.reserved_over_amount -= abs(reserved_over_amount)
            cs.over_amount += abs(reserved_over_amount)
            return line

    def update_purchased_subcon_bd(self, line, total_paid_amount, total_paid_quantity, estimated_budget_amount):
        for bd in line.bd_subcon_id:
            bd.purchased_amt = total_paid_amount
            bd.purchased_qty = total_paid_quantity
            bd.billed_amt -= total_paid_amount
            bd.billed_qty -= total_paid_quantity
            bd.amt_res -= total_paid_amount
            bd.qty_res -= total_paid_quantity

            # if fully paid
            # need different logic if reconcile/partially paid
            reserved_return_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount > total_paid_amount else 0
            reserved_over_amount = (estimated_budget_amount - total_paid_amount) if estimated_budget_amount < total_paid_amount else 0
            bd.reserved_return_amount -= reserved_return_amount
            bd.reserved_over_amount -= abs(reserved_over_amount)
            bd.over_amount += abs(reserved_over_amount)
            return line

    # billed
    def _budget_bill_amount(self, bill, down_payment_amount, down_payment_quantity, sign):
        total_billed_amount = 0.00
        total_billed_quantity = 0.00
        for line in self:
            if line.type == 'material':
                total_billed_amount = bill.price_subtotal - down_payment_amount
                total_billed_quantity = bill.quantity - down_payment_quantity
                if line.order_id.project_budget:
                    line.update_billed_material_cs(line, total_billed_amount, total_billed_quantity, sign)
                    line.update_billed_material_bd(line, total_billed_amount, total_billed_quantity, sign)
                else:
                    line.update_billed_material_cs(line, total_billed_amount, total_billed_quantity, sign)
            elif line.type == 'labour':
                total_billed_amount = bill.price_subtotal - down_payment_amount
                total_billed_quantity = bill.quantity - down_payment_quantity
                if line.order_id.project_budget:
                    line.update_billed_labour_cs(line, total_billed_amount, total_billed_quantity, sign)
                    line.update_billed_labour_bd(line, total_billed_amount, total_billed_quantity, sign)
                else:
                    line.update_billed_labour_cs(line, total_billed_amount, total_billed_quantity, sign)
            elif line.type == 'overhead':
                total_billed_amount = bill.price_subtotal - down_payment_amount
                total_billed_quantity = bill.quantity - down_payment_quantity
                if line.order_id.project_budget:
                    line.update_billed_overhead_cs(line, total_billed_amount, total_billed_quantity, sign)
                    line.update_billed_overhead_bd(line, total_billed_amount, total_billed_quantity, sign)
                else:
                    line.update_billed_overhead_cs(line, total_billed_amount, total_billed_quantity, sign)
            elif line.type == 'equipment':
                total_billed_amount = bill.price_subtotal - down_payment_amount
                total_billed_quantity = bill.quantity - down_payment_quantity
                if line.order_id.project_budget:
                    line.update_billed_equipment_cs(line, total_billed_amount, total_billed_quantity, sign)
                    line.update_billed_equipment_bd(line, total_billed_amount, total_billed_quantity, sign)
                else:
                    line.update_billed_equipment_cs(line, total_billed_amount, total_billed_quantity, sign)
            elif line.type == 'split':
                total_billed_amount = bill.price_subtotal - down_payment_amount
                total_billed_quantity = bill.quantity - down_payment_quantity
                if line.order_id.project_budget:
                    line.update_billed_subcon_cs(line, total_billed_amount, total_billed_quantity, sign)
                    line.update_billed_subcon_bd(line, total_billed_amount, total_billed_quantity, sign)
                else:
                    line.update_billed_subcon_cs(line, total_billed_amount, total_billed_quantity, sign)

    # paid
    def _budget_purchased_amount(self, amount, untaxed_down_payment_amount=0):
        total_paid_amount = 0.00
        total_paid_quantity = 0.00
        inv_amount = amount
        for line in self:
            total_paid_amount = line._cal_purchased_amount(inv_amount, untaxed_down_payment_amount)
            total_paid_quantity = line._cal_purchased_quantity(inv_amount, untaxed_down_payment_amount)
            estimated_budget_amount = (line.budget_quantity * line.budget_unit_price) - untaxed_down_payment_amount
            if line.type == 'material':
                if line.order_id.project_budget:
                    line.update_purchased_material_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                    line.update_purchased_material_bd(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                else:
                    line.update_purchased_material_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
            elif line.type == 'labour':
                if line.order_id.project_budget:
                    line.update_purchased_labour_cs(line, total_paid_amount, total_paid_quantity)
                    line.update_purchased_labour_bd(line, total_paid_amount, total_paid_quantity)
                else:
                    line.update_purchased_labour_cs(line, total_paid_amount, total_paid_quantity)
            elif line.type == 'overhead':
                if line.order_id.project_budget:
                    line.update_purchased_overhead_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                    line.update_purchased_overhead_bd(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                else:
                    line.update_purchased_overhead_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
            elif line.type == 'equipment':
                if line.order_id.project_budget:
                    line.update_purchased_equipment_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                    line.update_purchased_equipment_bd(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                else:
                    line.update_purchased_equipment_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
            elif line.type == 'split':
                if line.order_id.project_budget:
                    line.update_purchased_subcon_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                    line.update_purchased_subcon_bd(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)
                else:
                    line.update_purchased_subcon_cs(line, total_paid_amount, total_paid_quantity, estimated_budget_amount)

    def reserved_budget_cancel(self):
        for rec in self:
            if rec.type == 'material':
                if rec.order_id.project_budget:
                    rec.order_id.cancel_line_material_cs(rec)
                    rec.order_id.cancel_line_material_bd(rec)

                    rec.cs_material_id.job_sheet_id.get_gop_material_table()
                    rec.bd_material_id.budget_id.get_gop_material_table()
                else:
                    rec.order_id.cancel_line_material_cs(rec)
                    rec.cs_material_id.job_sheet_id.get_gop_material_table()
            elif rec.type == 'labour':
                if rec.order_id.project_budget:
                    rec.order_id.cancel_line_labour_cs(rec)
                    rec.order_id.cancel_line_labour_bd(rec)

                else:
                    rec.order_id.cancel_line_labour_cs(rec)
            elif rec.type == 'overhead':
                if rec.order_id.project_budget:
                    rec.order_id.cancel_line_overhead_cs(rec)
                    rec.order_id.cancel_line_overhead_bd(rec)

                    rec.cs_overhead_id.job_sheet_id.get_gop_overhead_table()
                    rec.bd_overhead_id.budget_id.get_gop_overhead_table()
                else:
                    rec.order_id.cancel_line_overhead_cs(rec)
                    rec.cs_overhead_id.job_sheet_id.get_gop_overhead_table()
            elif rec.type == 'equipment':
                if rec.order_id.project_budget:
                    rec.order_id.cancel_line_equipment_cs(rec)
                    rec.order_id.cancel_line_equipment_bd(rec)

                    rec.cs_equipment_id.job_sheet_id.get_gop_equipment_table()
                    rec.bd_equipment_id.budget_id.get_gop_equipment_table()
                else:
                    rec.order_id.cancel_line_equipment_cs(rec)
                    rec.cs_equipment_id.job_sheet_id.get_gop_equipment_table()

    def purchase_order_line_cancel(self):
        for rec in self:
            if rec.order_id.invoice_ids:
                for bill in rec.order_id.invoice_ids:
                    if bill.state1 != ('draft', 'cancel'):
                        raise UserError(_("Invoice already created for this order.hence we cannot this order line!"))
                rec.state = 'cancel'

                if rec.is_reserved:
                    rec.reserved_budget_cancel()

                all_count = len(rec.order_id.order_line.ids)
                current_cancal_count = 0
                for line in rec.order_id.order_line:
                    if line.state == 'cancel':
                        current_cancal_count += 1
                if all_count == current_cancal_count:
                    rec.order_id.state = 'cancel'
            else:
                rec.state = 'cancel'

                if rec.is_reserved:
                    rec.reserved_budget_cancel()

                all_count = len(rec.order_id.order_line.ids)
                current_cancal_count = 0
                for line in rec.order_id.order_line:
                    if line.state == 'cancel':
                        current_cancal_count += 1
                if all_count == current_cancal_count:
                    rec.order_id.state = 'cancel'

        return True

    @api.onchange('is_orders')
    def _onchange_is_orders(self):
        context = dict(self.env.context) or {}
        if context.get('orders'):
            self.is_orders = True

    # @api.onchange('product_qty')
    # def budget_quantity_validation(self):
    #     for res in self:
    #         if res.order_id.budgeting_method == 'product_budget':
    #             # if res.bd_material_id:
    #             #     for bud in res.bd_material_id:
    #             #         if res.product_qty > bud.qty_left:
    #             #             raise ValidationError(_("The quantity is over the remaining budget"))
    #             # else:
    #             #     for cost in res.cs_material_id:
    #             #         if res.product_qty > cost.budgeted_qty_left:
    #             #             raise ValidationError(_("The quantity is over the remaining budget"))
    #             if res.product_qty > res.budget_quantity:
    #                 raise ValidationError(_("The quantity is over the budget quantity"))
    #         else:
    #             pass

    # @api.onchange('price_subtotal')
    # def budget_amount_validation(self):
        # for res in self:
            # if res.order_id.budgeting_method == 'product_budget':
            #     if res.bd_material_id:
            #         for bud in res.bd_material_id:
            #             if res.price_subtotal > bud.amt_left:
            #                 raise ValidationError(_("The quantity is over the remaining budget"))
            #     else:
            #         for cost in res.cs_material_id:
            #             if res.price_subtotal > cost.budgeted_amt_left:
            #                 raise ValidationError(_("The quantity is over the remaining budget"))

            # elif res.order_id.budgeting_method == 'budget_type':
            #     if res.order_id.project_budget:
            #         for bud in res.order_id.project_budget:
            #             if res.order_id.amount_total > bud.amount_left_material:
            #                 raise ValidationError(_("The quantity is over the remaining budget"))
            #     else:
            #         # for cost in res.cs_material_id:
            #         #     if res.product_qty > cost.budgeted_qty_left:
            #         #         raise ValidationError(_("The quantity is over the remaining budget"))
            #         pass
            # else:
            #     pass
