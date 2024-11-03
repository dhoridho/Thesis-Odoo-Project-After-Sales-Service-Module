from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class WizardBudgetCarryOver(models.TransientModel):
    _name = 'wizard.budget.carry.over'
    _description = 'Budget Carry Over'

    @api.model
    def default_get(self, fields):
        res = super(WizardBudgetCarryOver, self).default_get(fields)
        context = self.env.context.get("context")
        active_ids = self.env['project.budget'].browse(self.env.context.get('active_ids'))

        if active_ids:
            # Material Estimation
            lst_material = [(5, 0, 0)]
            if active_ids.budget_material_ids:
                for line in active_ids.budget_material_ids:
                    if line.group_of_product.is_carry_over == True and line.qty_left != 0.0 and line.amt_left != 0.0:
                        lst_material.append((0, 0, {
                            'bd_material_id': line.id or False,
                            'sr_no': line.sr_no or False,
                            'date': line.date or False,
                            'project_scope_id': line.project_scope.id or False,
                            'section_name_id': line.section_name.id or False,
                            'variable_id': line.variable.id or False,
                            'group_of_product_id': line.group_of_product.id or False,
                            'product_id': line.product_id.id or False,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.amount or 0,
                            'description': line.description or False,
                            'quantity': line.qty_left or False,
                            'amount': line.amt_left or False,
                            'total_amount': line.qty_left * line.amount or 0,
                        }))
            if lst_material:
                res.update({'wizard_material_estimation_ids': lst_material})

            # Labour Estimation
            lst_labour = [(5, 0, 0)]
            if active_ids.budget_labour_ids:
                for line in active_ids.budget_labour_ids:
                    if line.group_of_product.is_carry_over == True and line.time_left != 0.0 and line.amt_left != 0.0:
                        lst_labour.append((0, 0, {
                            'bd_labour_id': line.id or False,
                            'sr_no': line.sr_no or False,
                            'date': line.date or False,
                            'project_scope_id': line.project_scope.id or False,
                            'section_name_id': line.section_name.id or False,
                            'variable_id': line.variable.id or False,
                            'group_of_product_id': line.group_of_product.id or False,
                            'product_id': line.product_id.id or False,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.amount or 0,
                            'contractors': line.contractors or False,
                            'description': line.description or False,
                            'time': line.time_left or False,
                            'amount': line.amt_left or False,
                            'total_amount': line.time_left * line.amount * line.contractors or 0,
                        }))
            if lst_labour:
                res.update({'wizard_labour_estimation_ids': lst_labour})

            # Internal Asset
            lst_internal_asset = [(5, 0, 0)]
            if active_ids.budget_internal_asset_ids:
                for line in active_ids.budget_internal_asset_ids:
                    if line.budgeted_qty_left != 0.0 and line.budgeted_amt_left != 0.0:
                        lst_internal_asset.append((0, 0, {
                            'bd_internal_asset_id': line.id or False,
                            'sr_no': line.sr_no or False,
                            'date': line.date or False,
                            'project_scope_id': line.project_scope_line_id.id or False,
                            'section_name_id': line.section_name.id or False,
                            'variable_id': line.variable_id.id or False,
                            'asset_category_id': line.asset_category_id.id or False,
                            'asset_id': line.asset_id.id or False,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.price_unit or 0,
                            'quantity': line.budgeted_qty_left or False,
                            'amount': line.budgeted_amt_left or False,
                            'total_amount': line.budgeted_qty_left * line.price_unit or 0,
                        }))
            if lst_internal_asset:
                res.update({'wizard_internal_asset_estimation_ids': lst_internal_asset})

            # Equipment Lease Estimation
            lst_equipment = [(5, 0, 0)]
            if active_ids.budget_equipment_ids:
                for line in active_ids.budget_equipment_ids:
                    if line.group_of_product.is_carry_over == True and line.qty_left != 0.0 and line.amt_left != 0.0:
                        lst_equipment.append((0, 0, {
                            'bd_equipment_id': line.id or False,
                            'sr_no': line.sr_no or False,
                            'date': line.date or False,
                            'project_scope_id': line.project_scope.id or False,
                            'section_name_id': line.section_name.id or False,
                            'variable_id': line.variable.id or False,
                            'group_of_product_id': line.group_of_product.id or False,
                            'product_id': line.product_id.id or False,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.amount or 0,
                            'description': line.description or False,
                            'quantity': line.qty_left or False,
                            'amount': line.amt_left or False,
                            'total_amount': line.qty_left * line.amount or 0,
                        }))
            if lst_equipment:
                res.update({'wizard_equipment_lease_estimation_ids': lst_equipment})

            #  Subcon Estimation
            lst_subcon = [(5, 0, 0)]
            if active_ids.budget_subcon_ids:
                for line in active_ids.budget_subcon_ids:
                    if line.qty_left != 0.0 and line.amt_left != 0.0:
                        lst_subcon.append((0, 0, {
                            'bd_subcon_id': line.id or False,
                            'sr_no': line.sr_no or False,
                            'date': line.date or False,
                            'project_scope_id': line.project_scope.id or False,
                            'section_name_id': line.section_name.id or False,
                            'variable_id': line.variable_ref.id or False,
                            'subcon_id': line.subcon_id.id or False,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.amount or 0,
                            'description': line.description or False,
                            'quantity': line.qty_left or False,
                            'amount': line.amt_left or False,
                            'total_amount': line.qty_left * line.amount or 0,
                        }))
            if lst_subcon:
                res.update({'wizard_subcon_estimation_ids': lst_subcon})

            # Overhead Estimation
            lst_overhead = [(5, 0, 0)]
            if active_ids.budget_overhead_ids:
                for line in active_ids.budget_overhead_ids:
                    if line.group_of_product.is_carry_over == True and line.qty_left != 0.0 and line.amt_left != 0.0:
                        lst_overhead.append((0, 0, {
                            'bd_overhead_id': line.id or False,
                            'sr_no': line.sr_no,
                            'date': line.date,
                            'project_scope_id': line.project_scope.id or False,
                            'section_name_id': line.section_name.id or False,
                            'variable_id': line.variable.id or False,
                            'overhead_category': line.overhead_catagory or False,
                            'group_of_product_id': line.group_of_product.id or False,
                            'product_id': line.product_id.id or False,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.amount or 0,
                            'description': line.description or False,
                            'quantity': line.qty_left or False,
                            'amount': line.amt_left or False,
                            'total_amount': line.qty_left * line.amount or 0,
                        }))
            if lst_overhead:
                res.update({'wizard_budget_carry_overhead_ids': lst_overhead})
            return res

    def get_project_budget_id(self):
        active_ids = self.env['project.budget'].browse(self.env.context.get('active_ids'))
        hr_emp = self.env['project.budget'].search(
            [('state', '=', 'in_progress'), ('project_id', 'in', active_ids.project_id.ids)])
        return [('id', 'in', hr_emp.ids)]

    project_id = fields.Many2one('project.project', string='Project')
    budget_default_id = fields.Many2one('project.budget', string='Periodical Budget')
    project_budget_id = fields.Many2one('project.budget', string="To Periodical Budget",
                                        domain="[('project_id','=', project_id),('id','!=', budget_default_id)]",
                                        required=True)

    wizard_material_estimation_ids = fields.One2many('wizard.material.estimation', 'carry_id')
    wizard_labour_estimation_ids = fields.One2many('wizard.labour.estimation', 'carry_id')
    wizard_internal_asset_estimation_ids = fields.One2many('wizard.internal.asset.estimation', 'carry_id')
    wizard_equipment_lease_estimation_ids = fields.One2many('wizard.equipment.lease.estimation', 'carry_id')
    wizard_budget_carry_overhead_ids = fields.One2many('wizard.overhead.estimation', 'carry_id')
    wizard_subcon_estimation_ids = fields.One2many('wizard.subcon.estimation', 'carry_id')

    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id,
                                 readonly=True)
    branch_id = fields.Many2one(related='project_id.branch_id', string="Branch",
                                default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids),
                                                     ('company_id', '=', self.env.company.id)])
    budget_carry_over_approval_matrix = fields.Boolean(string="Custome Matrix", store=False,
                                                       compute='is_budget_carry_over_approval_matrix')
    approving_matrix_budget_carry_id = fields.Many2one('approval.matrix.budget.carry.over', string="Approval Matrix",
                                                       compute='_compute_approving_customer_matrix', store=True)

    @api.depends('project_id', 'branch_id', 'company_id', 'department_type')
    def _compute_approving_customer_matrix(self):
        for res in self:
            res.approving_matrix_budget_carry_id = False
            if res.budget_carry_over_approval_matrix:
                if res.department_type == 'project':
                    approving_matrix_budget_carry_id = self.env['approval.matrix.budget.carry.over'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('project_id', 'in', (res.project_id.id)),
                        ('department_type', '=', 'project'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.budget.carry.over'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'project')], limit=1)

                else:
                    approving_matrix_budget_carry_id = self.env['approval.matrix.budget.carry.over'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('project_id', 'in', (res.project_id.id)),
                        ('department_type', '=', 'department'),
                        ('set_default', '=', False)], limit=1)

                    approving_matrix_default = self.env['approval.matrix.budget.carry.over'].search([
                        ('company_id', '=', res.company_id.id),
                        ('branch_id', '=', res.branch_id.id),
                        ('set_default', '=', True),
                        ('department_type', '=', 'department')], limit=1)

                if approving_matrix_budget_carry_id:
                    res.approving_matrix_budget_carry_id = approving_matrix_budget_carry_id and approving_matrix_budget_carry_id.id or False
                else:
                    if approving_matrix_default:
                        res.approving_matrix_budget_carry_id = approving_matrix_default and approving_matrix_default.id or False
                    else:
                        res.approving_matrix_budget_carry_id = False

    @api.depends('project_budget_id')
    def is_budget_carry_over_approval_matrix(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        budget_carry_over_approval_matrix = IrConfigParam.get_param('budget_carry_over_approval_matrix')
        for record in self:
            record.budget_carry_over_approval_matrix = budget_carry_over_approval_matrix

    @api.onchange('project_budget_id')
    def _check_to_budget_project(self):
        active_ids = self.env['project.budget'].browse(self.env.context.get('active_ids'))
        if self.project_budget_id.id == active_ids.id:
            raise ValidationError(
                _('The origin periodical budget and the destination periodical budget can not be the same.'))

    def set_carry_over_history(self, line, status, line_type, budget_line_field, budget_line, active_id):
        for rec in self:
            if line_type == 'labour':
                if status == 'send':
                    self.env['labour.budget.carry.over.history'].create({
                        'project_budget_id': active_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_send_time': line.time,
                        'carry_send_contractors': line.contractors,
                        'carry_send_amt': line.unit_price * line.contractors * line.time,
                        'carried_to_id': rec.project_budget_id.id,
                    })
                else:
                    self.env['labour.budget.carry.over.history'].create({
                        'project_budget_id': rec.project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_from_time': line.time,
                        'carry_from_contractors': line.contractors,
                        'carry_from_amt': line.unit_price * line.contractors * line.time,
                        'carried_from_id': active_id.id,
                    })
            elif line_type == 'internal_asset':
                if status == 'send':
                    self.env['internal.asset.budget.carry.over.history'].create({
                        'project_budget_id': active_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'asset_category_id': line.asset_category_id.id,
                        'asset_id': line.asset_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price* line.quantity,
                        'carried_to_id': rec.project_budget_id.id,
                    })
                else:
                    self.env['internal.asset.budget.carry.over.history'].create({
                        'project_budget_id': rec.project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'asset_category_id': line.asset_category_id.id,
                        'asset_id': line.asset_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price* line.quantity,
                        'carried_from_id': active_id.id,
                    })
            elif line_type == 'overhead':
                if status == 'send':
                    self.env['overhead.budget.carry.over.history'].create({
                        'project_budget_id': active_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'overhead_category': line.overhead_category,
                        'product_id': line.product_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price* line.quantity,
                        'carried_to_id': rec.project_budget_id.id,
                    })
                else:
                    self.env['overhead.budget.carry.over.history'].create({
                        'project_budget_id': rec.project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'overhead_category': line.overhead_category,
                        'product_id': line.product_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price* line.quantity,
                        'carried_from_id': active_id.id,
                    })
            elif line_type == 'subcon':
                if status == 'send':
                    self.env['subcon.budget.carry.over.history'].create({
                        'project_budget_id': active_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'subcon_id': line.subcon_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price* line.quantity,
                        'carried_to_id': rec.project_budget_id.id,
                    })
                else:
                    self.env['subcon.budget.carry.over.history'].create({
                        'project_budget_id': rec.project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'subcon_id': line.subcon_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price* line.quantity,
                        'carried_from_id': active_id.id,
                    })
            elif line_type == 'material':
                if status == 'send':
                    self.env['material.budget.carry.over.history'].create({
                        'project_budget_id': active_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price* line.quantity,
                        'carried_to_id': rec.project_budget_id.id,
                    })
                else:
                    self.env['material.budget.carry.over.history'].create({
                        'project_budget_id': rec.project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price* line.quantity,
                        'carried_from_id': active_id.id,
                    })
            elif line_type == 'equipment':
                if status == 'send':
                    self.env['equipment.budget.carry.over.history'].create({
                        'project_budget_id': active_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_send_qty': line.quantity,
                        'carry_send_amt': line.unit_price* line.quantity,
                        'carried_to_id': rec.project_budget_id.id,
                    })
                else:
                    self.env['equipment.budget.carry.over.history'].create({
                        'project_budget_id': rec.project_budget_id.id,
                        budget_line_field: budget_line.id,
                        'date': datetime.now(),
                        'project_scope_id': line.project_scope_id.id,
                        'section_id': line.section_name_id.id,
                        'group_of_product_id': line.group_of_product_id.id,
                        'product_id': line.product_id.id,
                        'carry_from_qty': line.quantity,
                        'carry_from_amt': line.unit_price * line.quantity,
                        'carried_from_id': active_id.id,
                    })

    def submit(self):
        for rec in self:
            active_ids = self.env['project.budget'].browse(self.env.context.get('active_ids'))
            # write state and carried to field in project budget
            # Material Estimation
            if not self.budget_carry_over_approval_matrix:
                carry_material = []
                carry_labour = []
                carry_overhead = []
                carry_internal_asset = []
                carry_equipment = []
                carry_subcon = []

                # Material Estimation
                if rec.wizard_material_estimation_ids:
                    for line in rec.wizard_material_estimation_ids:
                        material = []
                        budget_material = line.bd_material_id
                        if budget_material.group_of_product.is_carry_over == True and budget_material.qty_left != 0.0 and budget_material.amt_left != 0.0:
                            if budget_material.amt_left < line.unit_price * line.quantity:
                                raise ValidationError(
                                    _("The amount of carried over material must be less than the amount of the material's budget left amount."))
                            same_material = rec.project_budget_id.budget_material_ids.filtered(lambda
                                                                                                   x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)

                            if rec.project_budget_id.state not in ['in_progress', 'complete']:
                                budget_material.cs_material_id.allocated_budget_amt -= line.quantity * line.unit_price
                                budget_material.cs_material_id.allocated_budget_qty -= line.quantity
                                if same_material:
                                    same_material.unallocated_amount += line.quantity * line.unit_price
                                    same_material.unallocated_quantity += line.quantity
                                    same_material.quantity += line.quantity
                                else:
                                    material.append((0, 0, {
                                        'cs_material_id': budget_material.cs_material_id.id or False,
                                        'project_scope': budget_material.project_scope.id or False,
                                        'section_name': budget_material.section_name.id or False,
                                        'variable': budget_material.variable.id or False,
                                        'group_of_product': budget_material.group_of_product.id or False,
                                        'product_id': budget_material.product_id.id or False,
                                        'uom_id': budget_material.uom_id.id or False,
                                        'description': budget_material.description or False,
                                        'quantity': line.quantity or False,
                                        'amount': line.unit_price or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                        'unallocated_amount': line.quantity * line.unit_price,
                                        'unallocated_quantity': line.quantity,
                                    }))
                            else:
                                if same_material:
                                    same_material.quantity += line.quantity
                                    same_material.carried_from = active_ids.id
                                else:
                                    material.append((0, 0, {
                                        'cs_material_id': budget_material.cs_material_id.id or False,
                                        'project_scope': budget_material.project_scope.id or False,
                                        'section_name': budget_material.section_name.id or False,
                                        'variable': budget_material.variable.id or False,
                                        'group_of_product': budget_material.group_of_product.id or False,
                                        'product_id': budget_material.product_id.id or False,
                                        'uom_id': budget_material.uom_id.id or False,
                                        'description': budget_material.description or False,
                                        'quantity': line.quantity or False,
                                        'amount': line.unit_price or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                    }))

                            budget_material.update({'quantity': budget_material.quantity - line.quantity,
                                                    'status': 'carried_over',
                                                    'carried_to': self.project_budget_id,
                                                    })

                        rec.set_carry_over_history(line, 'send', 'material', 'bd_material_id', budget_material, active_ids)
                        rec.set_carry_over_history(line, 'receive', 'material', 'bd_material_id', budget_material, active_ids)

                        self.project_budget_id.update({'budget_material_ids': material})
                        carry_material.append((0, 0, {
                            'bd_material_id': line.bd_material_id.id,
                            'date': line.date,
                            'project_scope_id': line.project_scope_id.id,
                            'section_name_id': line.section_name_id.id,
                            'variable_id': line.variable_id.id,
                            'group_of_product_id': line.group_of_product_id.id,
                            'product_id': line.product_id.id,
                            'uom_id': budget_material.uom_id.id or False,
                            'unit_price': line.unit_price,
                            'description': line.description,
                            'quantity': line.quantity,
                            'amount': line.amount,
                            'total_amount': line.total_amount,
                        }))

                        if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(rec.wizard_material_estimation_ids) > 0:
                            rec.project_budget_id.get_gop_material_table()

                # Labour Estimation
                if rec.wizard_labour_estimation_ids:
                    for line in rec.wizard_labour_estimation_ids:
                        labour = []
                        budget_labour = line.bd_labour_id
                        if budget_labour.group_of_product.is_carry_over == True and budget_labour.time_left != 0.0 and budget_labour.amt_left != 0.0:
                            if budget_labour.amt_left < line.unit_price * line.time * line.contractors:
                                raise ValidationError(
                                    _("The amount of carried over labour must be less than the amount of the labour's budget left amount."))
                            same_labour = rec.project_budget_id.budget_labour_ids.filtered(lambda
                                                                                               x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)
                            if rec.project_budget_id.state not in ['in_progress', 'complete']:
                                budget_labour.cs_labour_id.allocated_budget_amt -= line.time * line.contractors * line.unit_price
                                budget_labour.cs_labour_id.allocated_budget_time -= line.time
                                budget_labour.cs_labour_id.allocated_contractors -= line.contractors
                                if same_labour:
                                    same_labour.unallocated_amount += line.quantity * line.unit_price
                                    same_labour.unallocated_quantity += line.quantity
                                    same_labour.time += line.time
                                    same_labour.contractors += line.contractors
                                else:
                                    labour.append((0, 0, {
                                        'cs_labour_id': budget_labour.cs_labour_id.id or False,
                                        'project_scope': budget_labour.project_scope.id or False,
                                        'section_name': budget_labour.section_name.id or False,
                                        'variable': budget_labour.variable.id or False,
                                        'group_of_product': budget_labour.group_of_product.id or False,
                                        'product_id': budget_labour.product_id.id or False,
                                        'uom_id': budget_labour.uom_id.id or False,
                                        'contractors': line.contractors or False,
                                        'description': budget_labour.description or False,
                                        'time': line.time or False,
                                        'amount': line.unit_price or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                        'unallocated_amount': line.time * line.contractors * line.unit_price,
                                        'unallocated_time': line.time,
                                        'unallocated_contractors': line.contractors,
                                    }))
                            else:
                                if same_labour:
                                    same_labour.time += line.time
                                    same_labour.contractors += line.contractors
                                    same_labour.carried_from = active_ids.id
                                else:
                                    labour.append((0, 0, {
                                        'cs_labour_id': budget_labour.cs_labour_id.id or False,
                                        'project_scope': budget_labour.project_scope.id or False,
                                        'section_name': budget_labour.section_name.id or False,
                                        'variable': budget_labour.variable.id or False,
                                        'group_of_product': budget_labour.group_of_product.id or False,
                                        'product_id': budget_labour.product_id.id or False,
                                        'uom_id': budget_labour.uom_id.id or False,
                                        'contractors': line.contractors or False,
                                        'description': budget_labour.description or False,
                                        'time': line.time or False,
                                        'amount': line.unit_price or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                    }))

                            budget_labour.update({'time': budget_labour.time - line.time,
                                                  'contractors': budget_labour.contractors - line.contractors,
                                                  'status': 'carried_over',
                                                  'carried_to': self.project_budget_id.id
                                                  })

                        rec.set_carry_over_history(line, 'send', 'labour', 'bd_labour_id', budget_labour,
                                                   active_ids)
                        rec.set_carry_over_history(line, 'receive', 'labour', 'bd_labour_id', budget_labour,
                                                   active_ids)

                        self.project_budget_id.update({'budget_labour_ids': labour})
                        carry_labour.append((0, 0, {
                            'bd_labour_id': line.bd_labour_id.id,
                            'date': line.date,
                            'project_scope_id': line.project_scope_id.id,
                            'section_name_id': line.section_name_id.id,
                            'variable_id': line.variable_id.id,
                            'group_of_product_id': line.group_of_product_id.id,
                            'product_id': line.product_id.id,
                            'uom_id': line.uom_id.id or False,
                            'time': line.time,
                            'unit_price': line.unit_price,
                            'description': line.description,
                            'quantity': line.quantity,
                            'amount': line.amount,
                            'total_amount': line.total_amount,
                        }))
                        if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(rec.wizard_labour_estimation_ids) > 0:
                            rec.project_budget_id.get_gop_labour_table()

                # Internal Asset
                if rec.wizard_internal_asset_estimation_ids:
                    for line in rec.wizard_internal_asset_estimation_ids:
                        internal_asset = []
                        budget_internal_asset = line.bd_internal_asset_id
                        if budget_internal_asset.budgeted_qty_left != 0.0 and budget_internal_asset.budgeted_amt_left != 0.0:
                            if budget_internal_asset.budgeted_amt_left < line.unit_price * line.quantity:
                                raise ValidationError(
                                    _("The amount of carried over internal asset must be less than the amount of the internal asset's budget left amount."))
                            same_asset = rec.project_budget_id.budget_internal_asset_ids.filtered(lambda
                                                                                                      x: x.project_scope_line_id.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.asset_category_id.id == line.asset_category_id.id and x.asset_id.id == line.asset_id.id)
                            if rec.project_budget_id.state not in ['in_progress', 'complete']:
                                budget_internal_asset.cs_internal_asset_id.allocated_budget_amt -= line.quantity * line.unit_price
                                budget_internal_asset.cs_internal_asset_id.allocated_budget_qty -= line.quantity
                                if same_asset:
                                    same_asset.unallocated_budget_amt += line.quantity * line.unit_price
                                    same_asset.unallocated_budget_qty += line.quantity
                                    same_asset.budgeted_qty += line.quantity
                                else:
                                    internal_asset.append((0, 0, {
                                        'cs_internal_asset_id': budget_internal_asset.cs_internal_asset_id.id or False,
                                        'project_scope_line_id': budget_internal_asset.project_scope_line_id.id or False,
                                        'section_name': budget_internal_asset.section_name.id or False,
                                        'variable_id': budget_internal_asset.variable_id.id or False,
                                        'asset_category_id': budget_internal_asset.asset_category_id.id or False,
                                        'asset_id': budget_internal_asset.asset_id.id or False,
                                        # 'description': budget_internal_asset.description or False,
                                        'budgeted_qty': line.quantity or False,
                                        'price_unit': line.unit_price or False,
                                        'uom_id': budget_internal_asset.uom_id.id or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                        'unallocated_budget_amt': line.quantity * line.unit_price,
                                        'unallocated_budget_qty': line.quantity,
                                    }))
                            else:
                                if same_asset:
                                    same_asset.budgeted_qty += line.quantity
                                    same_asset.carried_from = active_ids.id
                                else:
                                    internal_asset.append((0, 0, {
                                        'cs_internal_asset_id': budget_internal_asset.cs_internal_asset_id.id or False,
                                        'project_scope_line_id': budget_internal_asset.project_scope_line_id.id or False,
                                        'section_name': budget_internal_asset.section_name.id or False,
                                        'variable_id': budget_internal_asset.variable_id.id or False,
                                        'asset_category_id': budget_internal_asset.asset_category_id.id or False,
                                        'asset_id': budget_internal_asset.asset_id.id or False,
                                        # 'description': budget_internal_asset.description or False,
                                        'budgeted_qty': line.quantity or False,
                                        'price_unit': line.unit_price or False,
                                        'uom_id': budget_internal_asset.uom_id.id or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                    }))

                            budget_internal_asset.update({'budgeted_qty': budget_internal_asset.budgeted_qty - line.quantity,
                                                          'status': 'carried_over',
                                                          'carried_to': self.project_budget_id.id,
                                                          })

                        rec.set_carry_over_history(line, 'send', 'internal_asset', 'bd_internal_asset_id', budget_internal_asset,
                                                   active_ids)
                        rec.set_carry_over_history(line, 'receive', 'internal_asset', 'bd_internal_asset_id', budget_internal_asset,
                                                   active_ids)

                        self.project_budget_id.update({'budget_internal_asset_ids': internal_asset})
                        carry_internal_asset.append((0, 0, {
                            'bd_internal_asset_id': line.bd_internal_asset_id.id,
                            'date': line.date,
                            'project_scope_id': line.project_scope_id.id,
                            'section_name_id': line.section_name_id.id,
                            'variable_id': line.variable_id.id,
                            'asset_category_id': line.asset_category_id.id,
                            'asset_id': line.asset_id.id,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.unit_price,
                            # 'description': line.description,
                            'quantity': line.quantity,
                            'amount': line.amount,
                            'total_amount': line.total_amount,
                        }))

                # Equipment Lease Estimation
                if rec.wizard_equipment_lease_estimation_ids:
                    for line in rec.wizard_equipment_lease_estimation_ids:
                        equipment = []
                        budget_equipment = line.bd_equipment_id
                        if budget_equipment.group_of_product.is_carry_over == True and budget_equipment.qty_left != 0.0 and budget_equipment.amt_left != 0.0:
                            if budget_equipment.amt_left < line.unit_price * line.quantity:
                                raise ValidationError(
                                    _("The amount of carried over equipment must be less than the amount of the equipment's budget left amount."))
                            same_equipment = rec.project_budget_id.budget_equipment_ids.filtered(lambda
                                                                                                     x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)
                            if rec.project_budget_id.state not in ['in_progress', 'complete']:
                                budget_equipment.cs_equipment_id.allocated_budget_amt -= line.quantity * line.unit_price
                                budget_equipment.cs_equipment_id.allocated_budget_qty -= line.quantity
                                if same_equipment:
                                    same_equipment.unallocated_amount += line.quantity * line.unit_price
                                    same_equipment.unallocated_quantity += line.quantity
                                    same_equipment.quantity += line.quantity
                                else:
                                    equipment.append((0, 0, {
                                        'cs_equipment_id': budget_equipment.cs_equipment_id.id or False,
                                        'project_scope': budget_equipment.project_scope.id or False,
                                        'section_name': budget_equipment.section_name.id or False,
                                        'variable': budget_equipment.variable.id or False,
                                        'group_of_product': budget_equipment.group_of_product.id or False,
                                        'product_id': budget_equipment.product_id.id or False,
                                        'amount': line.unit_price or False,
                                        'uom_id': budget_equipment.uom_id.id or False,
                                        'description': budget_equipment.description or False,
                                        'quantity': line.quantity or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                        'unallocated_amount': line.quantity * line.unit_price,
                                        'unallocated_quantity': line.quantity,
                                    }))
                            else:
                                if same_equipment:
                                    same_equipment.quantity += line.quantity
                                    same_equipment.carried_from = active_ids.id
                                else:
                                    equipment.append((0, 0, {
                                        'cs_equipment_id': budget_equipment.cs_equipment_id.id or False,
                                        'project_scope': budget_equipment.project_scope.id or False,
                                        'section_name': budget_equipment.section_name.id or False,
                                        'variable': budget_equipment.variable.id or False,
                                        'group_of_product': budget_equipment.group_of_product.id or False,
                                        'product_id': budget_equipment.product_id.id or False,
                                        'amount': line.unit_price or False,
                                        'uom_id': budget_equipment.uom_id.id or False,
                                        'description': budget_equipment.description or False,
                                        'quantity': line.quantity or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                    }))

                            budget_equipment.update({'quantity': budget_equipment.quantity - line.quantity,
                                                     'status': 'carried_over',
                                                     'carried_to': self.project_budget_id.id,
                                                     })

                        rec.set_carry_over_history(line, 'send', 'equipment', 'bd_equipment_id', budget_equipment,
                                                   active_ids)
                        rec.set_carry_over_history(line, 'receive', 'equipment', 'bd_equipment_id', budget_equipment,
                                                   active_ids)

                        self.project_budget_id.update({'budget_equipment_ids': equipment})
                        carry_equipment.append((0, 0, {
                            'bd_equipment_id': line.bd_equipment_id.id,
                            'date': line.date,
                            'project_scope_id': line.project_scope_id.id,
                            'section_name_id': line.section_name_id.id,
                            'variable_id': line.variable_id.id,
                            'group_of_product_id': line.group_of_product_id.id,
                            'product_id': line.product_id.id,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.unit_price,
                            'description': line.description,
                            'quantity': line.quantity,
                            'amount': line.amount,
                            'total_amount': line.total_amount,
                        }))

                        if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(rec.wizard_equipment_lease_estimation_ids) > 0:
                            rec.project_budget_id.get_gop_equipment_table()

                #  Subcon Estimation
                if rec.wizard_subcon_estimation_ids:
                    for line in rec.wizard_subcon_estimation_ids:
                        subcon = []
                        budget_subcon = line.bd_subcon_id
                        if budget_subcon.qty_left != 0.0 and budget_subcon.amt_left != 0.0:
                            if budget_subcon.amt_left < line.unit_price * line.quantity:
                                raise ValidationError(
                                    _("The amount of carried over subcon must be less than the amount of the subcon's budget left amount."))
                            same_subcon = rec.project_budget_id.budget_subcon_ids.filtered(lambda
                                                                                               x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.subcon_id.id == line.subcon_id.id)
                            if rec.project_budget_id.state not in ['in_progress', 'complete']:
                                budget_subcon.cs_subcon_id.allocated_budget_amt -= line.quantity * line.unit_price
                                budget_subcon.cs_subcon_id.allocated_budget_qty -= line.quantity
                                if same_subcon:
                                    same_subcon.unallocated_amount += line.quantity * line.unit_price
                                    same_subcon.unallocated_quantity += line.quantity
                                    same_subcon.quantity += line.quantity
                                else:
                                    subcon.append((0, 0, {
                                        'cs_subcon_id': budget_subcon.cs_subcon_id.id or False,
                                        'project_scope': budget_subcon.project_scope.id or False,
                                        'section_name': budget_subcon.section_name.id or False,
                                        'variable_ref': budget_subcon.variable_ref.id or False,
                                        'subcon_id': budget_subcon.subcon_id.id or False,
                                        'description': budget_subcon.description or False,
                                        'quantity': line.quantity or False,
                                        'amount': line.unit_price or False,
                                        'uom_id': budget_subcon.uom_id.id or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                        'unallocated_amount': line.quantity * line.unit_price,
                                        'unallocated_quantity': line.quantity,
                                    }))
                            else:
                                if same_subcon:
                                    same_subcon.quantity += line.quantity
                                    same_subcon.carried_from = active_ids.id
                                else:
                                    subcon.append((0, 0, {
                                        'cs_subcon_id': budget_subcon.cs_subcon_id.id or False,
                                        'project_scope': budget_subcon.project_scope.id or False,
                                        'section_name': budget_subcon.section_name.id or False,
                                        'variable_ref': budget_subcon.variable_ref.id or False,
                                        'subcon_id': budget_subcon.subcon_id.id or False,
                                        'amount': line.unit_price or False,
                                        'uom_id': budget_subcon.uom_id.id or False,
                                        'description': budget_subcon.description or False,
                                        'quantity': line.quantity or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                    }))

                            budget_subcon.update({'quantity': budget_subcon.quantity - line.quantity,
                                                  'status': 'carried_over',
                                                  'carried_to': self.project_budget_id.id,
                                                  })

                        rec.set_carry_over_history(line, 'send', 'subcon', 'bd_subcon_id', budget_subcon,
                                                   active_ids)
                        rec.set_carry_over_history(line, 'receive', 'subcon', 'bd_subcon_id', budget_subcon,
                                                   active_ids)

                        self.project_budget_id.update({'budget_subcon_ids': subcon})
                        carry_subcon.append((0, 0, {
                            'bd_subcon_id': line.bd_subcon_id.id,
                            'date': line.date,
                            'project_scope_id': line.project_scope_id.id,
                            'section_name_id': line.section_name_id.id,
                            'variable_id': line.variable_id.id,
                            'subcon_id': line.subcon_id.id,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.unit_price,
                            'description': line.description,
                            'quantity': line.quantity,
                            'amount': line.amount,
                            'total_amount': line.total_amount,
                        }))

                # Overhead Estimation
                if rec.wizard_budget_carry_overhead_ids:
                    for line in rec.wizard_budget_carry_overhead_ids:
                        overhead = []
                        budget_overhead = line.bd_overhead_id
                        if budget_overhead.group_of_product.is_carry_over == True and budget_overhead.qty_left != 0.0 and budget_overhead.amt_left != 0.0:
                            if budget_overhead.amt_left < line.unit_price * line.quantity:
                                raise ValidationError(
                                    _("The amount of carried over overhead must be less than the amount of the overhead's budget left amount."))
                            same_overhead = rec.project_budget_id.budget_overhead_ids.filtered(lambda
                                                                                                   x: x.project_scope.name == line.project_scope_id.name and x.section_name.name == line.section_name_id.name and x.product_id.id == line.product_id.id)

                            if rec.project_budget_id.state not in ['in_progress', 'complete']:
                                budget_overhead.cs_overhead_id.allocated_budget_amt -= line.quantity * line.unit_price
                                budget_overhead.cs_overhead_id.allocated_budget_qty -= line.quantity
                                if same_overhead:
                                    same_overhead.unallocated_amount += line.quantity * line.unit_price
                                    same_overhead.unallocated_quantity += line.quantity
                                    same_overhead.quantity += line.quantity
                                else:
                                    overhead.append((0, 0, {
                                        'cs_overhead_id': budget_overhead.cs_overhead_id.id or False,
                                        'project_scope': budget_overhead.project_scope.id or False,
                                        'section_name': budget_overhead.section_name.id or False,
                                        'variable': budget_overhead.variable.id or False,
                                        'group_of_product': budget_overhead.group_of_product.id or False,
                                        'overhead_catagory': budget_overhead.overhead_catagory or False,
                                        'product_id': budget_overhead.product_id.id or False,
                                        'description': budget_overhead.description or False,
                                        'quantity': line.quantity or False,
                                        'amount': line.unit_price or False,
                                        'uom_id': budget_overhead.uom_id.id or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                        'unallocated_amount': line.quantity * line.unit_price,
                                        'unallocated_quantity': line.quantity,
                                    }))
                            else:
                                if same_overhead:
                                    same_overhead.quantity += line.quantity
                                    same_overhead.carried_from = active_ids.id
                                else:
                                    overhead.append((0, 0, {
                                        'cs_overhead_id': budget_overhead.cs_overhead_id.id or False,
                                        'project_scope': budget_overhead.project_scope.id or False,
                                        'section_name': budget_overhead.section_name.id or False,
                                        'variable': budget_overhead.variable.id or False,
                                        'group_of_product': budget_overhead.group_of_product.id or False,
                                        'overhead_catagory': budget_overhead.overhead_catagory or False,
                                        'product_id': budget_overhead.product_id.id or False,
                                        'amount': line.unit_price or False,
                                        'uom_id': budget_overhead.uom_id.id or False,
                                        'description': budget_overhead.description or False,
                                        'quantity': line.quantity or False,
                                        'status': 'carried_over',
                                        'carried_from': active_ids.id,
                                    }))

                            budget_overhead.update({'quantity': budget_overhead.quantity - line.quantity,
                                                    'status': 'carried_over',
                                                    'carried_to': self.project_budget_id.id,
                                                    })

                        rec.set_carry_over_history(line, 'send', 'overhead', 'bd_overhead_id', budget_overhead,
                                                   active_ids)
                        rec.set_carry_over_history(line, 'receive', 'overhead', 'bd_overhead_id', budget_overhead,
                                                   active_ids)

                        self.project_budget_id.update({'budget_overhead_ids': overhead})
                        carry_overhead.append((0, 0, {
                            'bd_overhead_id': line.bd_overhead_id.id,
                            'date': line.date,
                            'project_scope_id': line.project_scope_id.id,
                            'section_name_id': line.section_name_id.id,
                            'variable_id': line.variable_id.id,
                            'overhead_category': line.overhead_category,
                            'group_of_product_id': line.group_of_product_id.id,
                            'product_id': line.product_id.id,
                            'uom_id': line.uom_id.id or False,
                            'unit_price': line.unit_price,
                            'description': line.description,
                            'quantity': line.quantity,
                            'amount': line.amount,
                            'total_amount': line.total_amount,
                        }))
                        if rec.project_id.cost_sheet.budgeting_method == 'gop_budget' and len(rec.wizard_budget_carry_overhead_ids) > 0:
                            rec.project_budget_id.get_gop_overhead_table()

                budget_carry = self.env['project.budget.carry'].create({
                    'project_id': self.project_id.id,
                    'from_project_budget_id': self.budget_default_id.id,
                    'to_project_budget_id': self.project_budget_id.id,
                    'branch_id': self.branch_id.id,
                    'budget_carry_material_ids': carry_material,
                    'budget_carry_Labour_ids': carry_labour,
                    'budget_carry_overhead_ids': carry_overhead,
                    'budget_carry_internal_asset_ids': carry_internal_asset,
                    'budget_carry_equipment_ids': carry_equipment,
                    'budget_carry_subcon_ids': carry_subcon,
                    'state': 'done',
                })

            else:
                if not self.approving_matrix_budget_carry_id:
                    raise ValidationError(
                        _("There's no budget carry over approval matrix for this project or approval matrix default created. You have to create it first."))
                else:
                    material_set = []
                    labour_set = []
                    overhead_set = []
                    asset_set = []
                    equipment_set = []
                    subcon_set = []
                    if self.wizard_material_estimation_ids:
                        for mat in self.wizard_material_estimation_ids:
                            if mat.bd_material_id.amt_left < mat.unit_price * mat.quantity:
                                raise ValidationError(
                                    _("The amount of carried over material must be less than the amount of the material's budget left amount."))
                            def material_value(mat):
                                return {
                                    'bd_material_id': mat.bd_material_id.id,
                                    'date': mat.date,
                                    'project_scope_id': mat.project_scope_id.id,
                                    'section_name_id': mat.section_name_id.id,
                                    'variable_id': mat.variable_id.id,
                                    'group_of_product_id': mat.group_of_product_id.id,
                                    'product_id': mat.product_id.id,
                                    'uom_id': mat.uom_id.id,
                                    'unit_price': mat.unit_price,
                                    'description': mat.description,
                                    'quantity': mat.quantity,
                                    'amount': mat.amount,
                                    'total_amount': mat.total_amount,
                                }

                            material_set.append((0, 0, material_value(mat)))

                    if self.wizard_labour_estimation_ids:
                        for lab in self.wizard_labour_estimation_ids:
                            if lab.bd_labour_id.amt_left < lab.unit_price * lab.time * lab.contractors:
                                raise ValidationError(
                                    _("The amount of carried over labour must be less than the amount of the labour's budget left amount."))
                            def labour_value(lab):
                                return {
                                    'bd_labour_id': lab.bd_labour_id.id,
                                    'date': lab.date,
                                    'project_scope_id': lab.project_scope_id.id,
                                    'section_name_id': lab.section_name_id.id,
                                    'variable_id': lab.variable_id.id,
                                    'group_of_product_id': lab.group_of_product_id.id,
                                    'product_id': lab.product_id.id,
                                    'contractors': lab.contractors,
                                    'uom_id': lab.uom_id.id,
                                    'unit_price': lab.unit_price,
                                    'description': lab.description,
                                    'time': lab.time,
                                    'amount': lab.amount,
                                    'total_amount': lab.total_amount,
                                }

                            labour_set.append((0, 0, labour_value(lab)))

                    if self.wizard_budget_carry_overhead_ids:
                        for over in self.wizard_budget_carry_overhead_ids:
                            if over.bd_overhead_id.amt_left < over.unit_price * over.quantity:
                                raise ValidationError(
                                    _("The amount of carried over overhead must be less than the amount of the overhead's budget left amount."))
                            def overhead_value(over):
                                return {
                                    'bd_overhead_id': over.bd_overhead_id.id,
                                    'date': over.date,
                                    'project_scope_id': over.project_scope_id.id,
                                    'section_name_id': over.section_name_id.id,
                                    'variable_id': over.variable_id.id,
                                    'overhead_category': over.overhead_category,
                                    'group_of_product_id': over.group_of_product_id.id,
                                    'product_id': over.product_id.id,
                                    'uom_id': over.uom_id.id,
                                    'unit_price': over.unit_price,
                                    'description': over.description,
                                    'quantity': over.quantity,
                                    'amount': over.amount,
                                    'total_amount': over.total_amount,
                                }

                            overhead_set.append((0, 0, overhead_value(over)))

                    if self.wizard_internal_asset_estimation_ids:
                        for ass in self.wizard_internal_asset_estimation_ids:
                            if ass.bd_internal_asset_id.budgeted_amt_left < ass.unit_price * ass.quantity:
                                raise ValidationError(
                                    _("The amount of carried over internal asset must be less than the amount of the internal asset's budget left amount."))
                            def asset_value(ass):
                                return {
                                    'bd_internal_asset_id': ass.bd_internal_asset_id.id,
                                    'date': ass.date,
                                    'project_scope_id': ass.project_scope_id.id,
                                    'section_name_id': ass.section_name_id.id,
                                    'variable_id': ass.variable_id.id,
                                    'asset_category_id': ass.asset_category_id.id,
                                    'asset_id': ass.asset_id.id,
                                    'uom_id': ass.uom_id.id,
                                    'unit_price': ass.unit_price,
                                    'description': ass.description,
                                    'quantity': ass.quantity,
                                    'amount': ass.amount,
                                    'total_amount': ass.total_amount,
                                }

                            asset_set.append((0, 0, asset_value(ass)))

                    if self.wizard_equipment_lease_estimation_ids:
                        for equip in self.wizard_equipment_lease_estimation_ids:
                            if equip.bd_equipment_id.amt_left < equip.unit_price * equip.quantity:
                                raise ValidationError(
                                    _("The amount of carried over equipment must be less than the amount of the equipment's budget left amount."))
                            def equipment_value(equip):
                                return {
                                    'bd_equipment_id': equip.bd_equipment_id.id,
                                    'date': equip.date,
                                    'project_scope_id': equip.project_scope_id.id,
                                    'section_name_id': equip.section_name_id.id,
                                    'variable_id': equip.variable_id.id,
                                    'group_of_product_id': equip.group_of_product_id.id,
                                    'product_id': equip.product_id.id,
                                    'uom_id': equip.uom_id.id,
                                    'unit_price': equip.unit_price,
                                    'description': equip.description,
                                    'quantity': equip.quantity,
                                    'amount': equip.amount,
                                    'total_amount': equip.total_amount,
                                }

                            equipment_set.append((0, 0, equipment_value(equip)))

                    if self.wizard_subcon_estimation_ids:
                        for sub in self.wizard_subcon_estimation_ids:
                            def subcon_value(sub):
                                return {
                                    'bd_subcon_id': sub.bd_subcon_id.id,
                                    'date': sub.date,
                                    'project_scope_id': sub.project_scope_id.id,
                                    'section_name_id': sub.section_name_id.id,
                                    'variable_id': sub.variable_id.id,
                                    'subcon_id': sub.subcon_id.id,
                                    'uom_id': sub.uom_id.id,
                                    'unit_price': sub.unit_price,
                                    'description': sub.description,
                                    'quantity': sub.quantity,
                                    'amount': sub.amount,
                                    'total_amount': sub.total_amount,
                                }

                            subcon_set.append((0, 0, subcon_value(sub)))

                    budget_carry = self.env['project.budget.carry'].create({
                        'project_id': self.project_id.id,
                        'from_project_budget_id': self.budget_default_id.id,
                        'to_project_budget_id': self.project_budget_id.id,
                        'branch_id': self.branch_id.id,
                        'budget_carry_material_ids': material_set,
                        'budget_carry_Labour_ids': labour_set,
                        'budget_carry_overhead_ids': overhead_set,
                        'budget_carry_internal_asset_ids': asset_set,
                        'budget_carry_equipment_ids': equipment_set,
                        'budget_carry_subcon_ids': subcon_set,
                    })

                    budget_carry.sudo().is_budget_carry_over_approval_matrix()
                    budget_carry.sudo()._compute_approving_customer_matrix()
                    budget_carry.sudo().onchange_approving_matrix_lines()
                    budget_carry.sudo().request_approval()
