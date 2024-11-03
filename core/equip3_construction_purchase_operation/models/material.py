from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
import re


class MaterialRequest(models.Model):
    _inherit = 'material.request'
    
    @api.model
    def _domain_project(self):
        return [('company_id','=', self.env.company.id),('primary_states','=','progress')]

    request_to_departement = fields.Many2one(comodel_name = 'hr.department', string='Request to Department')
    project = fields.Many2one(comodel_name = 'project.project', string='Project', domain=_domain_project)
    job_cost_sheet = fields.Many2one('job.cost.sheet', 'Cost Sheet')
    project_budget = fields.Many2one(comodel_name='project.budget', string='Periodical Budget', domain="[('project_id','=', project), ('state','=','in_progress')]")
    multi_budget = fields.Boolean('Multiple Project Budget', default=False)
    multiple_budget_ids = fields.Many2many('project.budget', string='Multiple Budget', domain="[('project_id','=',project), ('state','=','in_progress')]")
    is_multiple_budget = fields.Boolean('Multiple Budget', default=False)
    agreement_count = fields.Integer(compute='_compute_agreement_count',
                                     string='Agreement', compute_sudo=True)
    type_of_mr = fields.Selection([('material','Material'),('labour','Labour'),('overhead','Overhead')],
                                  string = "Type Of MR")
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    is_multiple_budget_procurement = fields.Boolean(string="Is Multiple Budget", compute='_is_multiple_budget_procurement')


    def _is_multiple_budget_procurement(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_multiple_budget_procurement = IrConfigParam.get_param('is_multiple_budget_procurement')
        for record in self:
            record.is_multiple_budget_procurement = is_multiple_budget_procurement

    @api.onchange('job_cost_sheet')
    def onchange_job_cost_sheet(self):
        for rec in self.job_cost_sheet:
            if rec.state != 'in_progress':
                raise ValidationError(_('Cost sheet status is not in progress. Please In Progress cost sheet first.'))

    def mr_cancel(self):
        res = super(MaterialRequest, self).mr_cancel()
        for rec in self:
            for line in rec.product_line:
                if line.status_2 not in ['cancel', 'draft']:
                    line.action_cancel_line()
        return res

    def convert_material_uom_bd(self, line):
        converted_bd = 0.00
        line_factor_inv = line.product_unit_measure.factor_inv
        line_factor = line.product_unit_measure.factor
        dest_bd_factor_inv = line.bd_material_id.uom_id.factor_inv
        dest_bd_factor = line.bd_material_id.uom_id.factor
        if line.product_unit_measure.uom_type == 'bigger':
            if line.bd_material_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity * line_factor_inv / dest_bd_factor_inv)
            elif line.bd_material_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * line_factor_inv * dest_bd_factor)
            elif line.bd_material_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.bd_material_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / line_factor / dest_bd_factor_inv)
            elif line.bd_material_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity / line_factor * dest_bd_factor)
            elif line.bd_material_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.bd_material_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / dest_bd_factor_inv)
            elif line.bd_material_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * dest_bd_factor)
            elif line.bd_material_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity)
        return converted_bd

    def convert_material_uom_cs(self, line):
        converted_cs = 0.00
        line_factor = line.product_unit_measure.factor
        line_factor_inv = line.product_unit_measure.factor_inv
        dest_cs_factor = line.cs_material_id.uom_id.factor
        dest_cs_factor_inv = line.cs_material_id.uom_id.factor_inv
        if line.product_unit_measure.uom_type == 'bigger':
            if line.cs_material_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity * line_factor_inv / dest_cs_factor_inv)
            elif line.cs_material_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * line_factor_inv * dest_cs_factor)
            elif line.cs_material_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.cs_material_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / line_factor / dest_cs_factor_inv)
            elif line.cs_material_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity / line_factor * dest_cs_factor)
            elif line.cs_material_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.cs_material_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / dest_cs_factor_inv)
            elif line.cs_material_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * dest_cs_factor)
            elif line.cs_material_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity)
        return converted_cs

    def convert_labour_uom_bd(self, line):
        converted_bd = 0.00
        line_factor_inv = line.product_unit_measure.factor_inv
        line_factor = line.product_unit_measure.factor
        dest_bd_factor_inv = line.bd_labour_id.uom_id.factor_inv
        dest_bd_factor = line.bd_labour_id.uom_id.factor
        if line.product_unit_measure.uom_type == 'bigger':
            if line.bd_labour_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity * line_factor_inv / dest_bd_factor_inv)
            elif line.bd_labour_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * line_factor_inv * dest_bd_factor)
            elif line.bd_labour_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.bd_labour_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / line_factor / dest_bd_factor_inv)
            elif line.bd_labour_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity / line_factor * dest_bd_factor)
            elif line.bd_labour_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.bd_labour_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / dest_bd_factor_inv)
            elif line.bd_labour_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * dest_bd_factor)
            elif line.bd_labour_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity)
        return converted_bd

    def convert_labour_uom_cs(self, line):
        converted_cs = 0.00
        line_factor = line.product_unit_measure.factor
        line_factor_inv = line.product_unit_measure.factor_inv
        dest_cs_factor = line.cs_labour_id.uom_id.factor
        dest_cs_factor_inv = line.cs_labour_id.uom_id.factor_inv
        if line.product_unit_measure.uom_type == 'bigger':
            if line.cs_labour_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity * line_factor_inv / dest_cs_factor_inv)
            elif line.cs_labour_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * line_factor_inv * dest_cs_factor)
            elif line.cs_labour_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.cs_labour_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / line_factor / dest_cs_factor_inv)
            elif line.cs_labour_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity / line_factor * dest_cs_factor)
            elif line.cs_labour_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.cs_labour_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / dest_cs_factor_inv)
            elif line.cs_labour_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * dest_cs_factor)
            elif line.cs_labour_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity)
        return converted_cs

    def convert_overhead_uom_bd(self, line):
        converted_bd = 0.00
        line_factor_inv = line.product_unit_measure.factor_inv
        line_factor = line.product_unit_measure.factor
        dest_bd_factor_inv = line.bd_overhead_id.uom_id.factor_inv
        dest_bd_factor = line.bd_overhead_id.uom_id.factor
        if line.product_unit_measure.uom_type == 'bigger':
            if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity * line_factor_inv / dest_bd_factor_inv)
            elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * line_factor_inv * dest_bd_factor)
            elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / line_factor / dest_bd_factor_inv)
            elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity / line_factor * dest_bd_factor)
            elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / dest_bd_factor_inv)
            elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * dest_bd_factor)
            elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity)
        return converted_bd

    def convert_overhead_uom_cs(self, line):
        converted_cs = 0.00
        line_factor = line.product_unit_measure.factor
        line_factor_inv = line.product_unit_measure.factor_inv
        dest_cs_factor = line.cs_overhead_id.uom_id.factor
        dest_cs_factor_inv = line.cs_overhead_id.uom_id.factor_inv
        if line.product_unit_measure.uom_type == 'bigger':
            if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity * line_factor_inv / dest_cs_factor_inv)
            elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * line_factor_inv * dest_cs_factor)
            elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / line_factor / dest_cs_factor_inv)
            elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity / line_factor * dest_cs_factor)
            elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / dest_cs_factor_inv)
            elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * dest_cs_factor)
            elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity)
        return converted_cs

    def convert_equipment_uom_bd(self, line):
        converted_bd = 0.00
        line_factor_inv = line.product_unit_measure.factor_inv
        line_factor = line.product_unit_measure.factor
        dest_bd_factor_inv = line.bd_equipment_id.uom_id.factor_inv
        dest_bd_factor = line.bd_equipment_id.uom_id.factor
        if line.product_unit_measure.uom_type == 'bigger':
            if line.bd_equipment_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity * line_factor_inv / dest_bd_factor_inv)
            elif line.bd_equipment_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * line_factor_inv * dest_bd_factor)
            elif line.bd_equipment_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.bd_equipment_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / line_factor / dest_bd_factor_inv)
            elif line.bd_equipment_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity / line_factor * dest_bd_factor)
            elif line.bd_equipment_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.bd_equipment_id.uom_id.uom_type == 'bigger':
                converted_bd = (line.quantity / dest_bd_factor_inv)
            elif line.bd_equipment_id.uom_id.uom_type == 'smaller':
                converted_bd = (line.quantity * dest_bd_factor)
            elif line.bd_equipment_id.uom_id.uom_type == 'reference':
                converted_bd = (line.quantity)
        return converted_bd

    def convert_equipment_uom_cs(self, line):
        converted_cs = 0.00
        line_factor = line.product_unit_measure.factor
        line_factor_inv = line.product_unit_measure.factor_inv
        dest_cs_factor = line.cs_equipment_id.uom_id.factor
        dest_cs_factor_inv = line.cs_equipment_id.uom_id.factor_inv
        if line.product_unit_measure.uom_type == 'bigger':
            if line.cs_equipment_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity * line_factor_inv / dest_cs_factor_inv)
            elif line.cs_equipment_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * line_factor_inv * dest_cs_factor)
            elif line.cs_equipment_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity * line_factor_inv)
        elif line.product_unit_measure.uom_type == 'smaller':
            if line.cs_equipment_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / line_factor / dest_cs_factor_inv)
            elif line.cs_equipment_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity / line_factor * dest_cs_factor)
            elif line.cs_equipment_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity / line_factor)
        elif line.product_unit_measure.uom_type == 'reference':
            if line.cs_equipment_id.uom_id.uom_type == 'bigger':
                converted_cs = (line.quantity / dest_cs_factor_inv)
            elif line.cs_equipment_id.uom_id.uom_type == 'smaller':
                converted_cs = (line.quantity * dest_cs_factor)
            elif line.cs_equipment_id.uom_id.uom_type == 'reference':
                converted_cs = (line.quantity)
        return converted_cs

    def prepare_reserved_bd(self, reserved_bud):
        return {
            'qty_res': reserved_bud,
        }

    def prepare_reserved_cs(self, reserved_cs):
        return {
            'reserved_qty': reserved_cs,
        }

    @api.constrains('product_line')
    def _check_exist_product_line_project_constrains(self):
        exist_product_line = []
        for line in self.product_line:
            same = str(line.project_scope.id) + ' - ' + str(line.section.id) + ' - ' + str(line.product.id)
            if (same in exist_product_line):
                raise ValidationError(
                    _('The product "%s" already exists in the project scope "%s" and the section "%s",' % (
                    (line.product.name), (line.project_scope.name), (line.section.name))))
            exist_product_line.append(same)
    
    def button_confirm(self):
        res = super(MaterialRequest, self).button_confirm()

        if self.type_of_mr in ['material', 'overhead'] :
            material_line_ids = []
            overhead_line_ids = []
            if self.job_cost_sheet.budgeting_period in ['project']:
                material_line_ids = self.product_line.filtered(lambda x: (x.budget_quantity != x.cs_material_id.budgeted_qty_left) if x.cs_material_id else False )
                overhead_line_ids = self.product_line.filtered(lambda x: (x.budget_quantity != x.cs_overhead_id.budgeted_qty_left) if x.cs_overhead_id else False )
            elif self.job_cost_sheet.budgeting_period in ['monthly', 'custom']:
                material_line_ids = self.product_line.filtered(lambda x: (x.budget_quantity != x.bd_material_id.qty_left) if x.bd_material_id else False )
                overhead_line_ids = self.product_line.filtered(lambda x: (x.budget_quantity != x.bd_overhead_id.qty_left) if x.bd_overhead_id else False )
            if len(material_line_ids) + len(overhead_line_ids) > 0:
                raise ValidationError("There’s differences on this document budget quantity with Cost Sheet/ Periodical Budget. Please create new document.")

        if self.job_cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            for line in self.product_line:
                line.write({
                    'status_2': 'confirm',
                })

            if self.type_of_mr == 'material':                  
                if self.project_budget:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            if not line.cs_material_id:
                                for cos in self.job_cost_sheet:
                                    cos.material_ids = [(0, 0, {
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable_ref': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'product_qty': line.quantity,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'reserved_qty': line.quantity,
                                                                # 'price_unit': line.product.list_price,
                                                                # 'material_amount_total': line.subtotal,
                                                            })]
                                for bud in self.project_budget:
                                    if not line.bd_material_id:
                                        cs_mat = self.env['material.material'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                                        bud.budget_material_ids = [(0, 0, {
                                                                'cs_material_id': cs_mat.id,
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'budget_quantity': line.quantity,
                                                                'qty_res': line.quantity,
                                                                # 'amount': line.price_unit,
                                                                # 'budget_amount': line.line_amount_total,
                                                            })]
                                line.cs_material_id = cs_mat.id
                                line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', self.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_material_id.uom_id:
                                    converted_bd = self.convert_material_uom_bd(line)
                                    reserved_bud = line.bd_material_id.qty_res + converted_bd
                                    reserved_cs = line.cs_material_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_material_ids = [(1, line.bd_material_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_material_id.qty_res + line.quantity
                                    reserved_cs = line.cs_material_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_material_ids = [(1, line.bd_material_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]

                        return res  
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_material_id.uom_id:
                                    converted_bd = self.convert_material_uom_bd(line)
                                    reserved_bud = line.bd_material_id.qty_res + converted_bd
                                    reserved_cs = line.cs_material_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_material_ids = [(1, line.bd_material_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_material_id.qty_res + line.quantity
                                    reserved_cs = line.cs_material_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_material_ids = [(1, line.bd_material_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                else:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            for cos in self.job_cost_sheet:
                                if not line.cs_material_id:
                                    cos.material_ids = [(0, 0, {
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable_ref': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'product_qty': line.quantity,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'reserved_qty': line.quantity,
                                                                # 'price_unit': line.product.list_price,
                                                                # 'material_amount_total': line.subtotal,
                                                            })]
                                    line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                                else:
                                    reserved_cs = 0.00
                                    converted_cs = 0.00
                                    reserved_cs = 0.00
                                    converted_cs = 0.00
                                    if line.product_unit_measure != line.cs_material_id.uom_id:
                                        converted_cs = self.convert_material_uom_cs(line)
                                        reserved_cs = line.cs_material_id.reserved_qty + converted_cs
                                        for cs in self.job_cost_sheet:
                                            cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                                    else:
                                        reserved_cs = line.cs_material_id.reserved_qty + line.quantity
                                        for cs in self.job_cost_sheet:
                                            cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_cs = 0.00
                                converted_cs = 0.00
                                if line.product_unit_measure != line.cs_material_id.uom_id:
                                    converted_cs = self.convert_material_uom_cs(line)
                                    reserved_cs = line.cs_material_id.reserved_qty + converted_cs
                                    for cs in self.job_cost_sheet:
                                        cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_cs = line.cs_material_id.reserved_qty + line.quantity
                                    for cs in self.job_cost_sheet:
                                        cs.material_ids = [(1, line.cs_material_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
        
            if self.type_of_mr == 'labour':
                if self.project_budget:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            if not line.cs_labour_id:
                                for cos in self.job_cost_sheet:
                                        cos.material_labour_ids = [(0, 0, {
                                                                    'project_scope': line.project_scope.id,
                                                                    'section_name': line.section.id,
                                                                    'variable_ref': line.variable.id,
                                                                    'group_of_product': line.group_of_product.id,
                                                                    'product_id': line.product.id,
                                                                    'description': line.description,
                                                                    'product_qty': line.quantity,
                                                                    'uom_id': line.product_unit_measure.id,
                                                                    'reserved_qty': line.quantity,
                                                                    # 'price_unit': line.product.list_price,
                                                                    # 'material_amount_total': line.subtotal,
                                                                })]
                                for bud in self.project_budget:
                                    if not line.bd_labour_id:
                                        cs_mat = self.env['material.labour'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                                        bud.budget_labour_ids = [(0, 0, {
                                                                'cs_labour_id': cs_mat.id,
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'budget_quantity': line.quantity,
                                                                'qty_res': line.quantity,
                                                                # 'amount': line.price_unit,
                                                                # 'budget_amount': line.line_amount_total,
                                                            })] 
                                line.cs_labour_id = cs_mat.id
                                line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', self.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                            else:
                                for line in self.product_line:
                                    reserved_bud = 0.00
                                    reserved_cs = 0.00
                                    converted_bd = 0.00
                                    if line.product_unit_measure != line.bd_labour_id.uom_id:
                                        converted_bd = self.convert_labour_uom_bd(line)
                                        reserved_bud = line.bd_labour_id.qty_res + converted_bd
                                        reserved_cs = line.cs_labour_id.reserved_qty + converted_bd
                                        for sub in self.project_budget:
                                            sub.budget_labour_ids = [(1, line.bd_labour_id.id, self.prepare_reserved_bd(reserved_bud))]
                                        for cs in self.job_cost_sheet:
                                            cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                                    else:
                                        reserved_bud = line.bd_labour_id.qty_res + line.quantity
                                        reserved_cs = line.cs_labour_id.reserved_qty + line.quantity
                                        for sub in self.project_budget:
                                            sub.budget_labour_ids = [(1, line.bd_labour_id.id, self.prepare_reserved_bd(reserved_bud))]
                                        for cs in self.job_cost_sheet:
                                            cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_labour_id.uom_id:
                                    converted_bd = self.convert_labour_uom_bd(line)
                                    reserved_bud = line.bd_labour_id.qty_res + converted_bd
                                    reserved_cs = line.cs_labour_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_labour_ids = [(1, line.bd_labour_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_labour_id.qty_res + line.quantity
                                    reserved_cs = line.cs_labour_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_labour_ids = [(1, line.bd_labour_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                else:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            for cos in self.job_cost_sheet:
                                if not line.cs_labour_id:
                                    cos.material_labour_ids = [(0, 0, {
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable_ref': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'product_qty': line.quantity,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'reserved_qty': line.quantity,
                                                                # 'price_unit': line.product.list_price,
                                                                # 'material_amount_total': line.subtotal,
                                                            })]
                                    line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                else:
                                    reserved_cs = 0.00
                                    converted_cs = 0.00
                                    if line.product_unit_measure != line.cs_labour_id.uom_id:
                                        converted_cs = self.convert_labour_uom_cs(line)
                                        reserved_cs = line.cs_labour_id.reserved_qty + converted_cs
                                        for cs in self.job_cost_sheet:
                                            cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                                    else:
                                        reserved_cs = line.cs_labour_id.reserved_qty + line.quantity
                                        for cs in self.job_cost_sheet:
                                            cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_cs = 0.00
                                converted_cs = 0.00
                                if line.product_unit_measure != line.cs_labour_id.uom_id:
                                    converted_cs = self.convert_labour_uom_cs(line)
                                    reserved_cs = line.cs_labour_id.reserved_qty + converted_cs
                                    for cs in self.job_cost_sheet:
                                        cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_cs = line.cs_labour_id.reserved_qty + line.quantity
                                    for cs in self.job_cost_sheet:
                                        cs.material_labour_ids = [(1, line.cs_labour_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
            
            if self.type_of_mr == 'overhead':
                if self.project_budget:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            if not line.cs_overhead_id:
                                for cos in self.job_cost_sheet:
                                    cos.material_overhead_ids = [(0, 0, {
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable_ref': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'product_qty': line.quantity,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'reserved_qty': line.quantity,
                                                                # 'price_unit': line.product.list_price,
                                                                # 'material_amount_total': line.subtotal,
                                                            })]
                                for bud in self.project_budget:
                                    if not line.bd_overhead_id:
                                        cs_mat = self.env['material.overhead'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                                        bud.budget_overhead_ids = [(0, 0, {
                                                                'cs_overhead_id': cs_mat.id,
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'budget_quantity': line.quantity,
                                                                'qty_res': line.quantity,
                                                                # 'amount': line.price_unit,
                                                                # 'budget_amount': line.line_amount_total,
                                                            })]
                                line.cs_overhead_id = cs_mat.id
                                line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', self.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_overhead_id.uom_id:
                                    converted_bd = self.convert_overhead_uom_bd(line)
                                    reserved_bud = line.bd_overhead_id.qty_res + converted_bd
                                    reserved_cs = line.cs_overhead_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_overhead_ids = [(1, line.bd_overhead_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_overhead_id.qty_res + line.quantity
                                    reserved_cs = line.cs_overhead_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_overhead_ids = [(1, line.bd_overhead_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_overhead_id.uom_id:
                                    converted_bd = self.convert_overhead_uom_bd(line)
                                    reserved_bud = line.bd_overhead_id.qty_res + converted_bd
                                    reserved_cs = line.cs_overhead_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_overhead_ids = [(1, line.bd_overhead_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_overhead_id.qty_res + line.quantity
                                    reserved_cs = line.cs_overhead_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_overhead_ids = [(1, line.bd_overhead_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                else:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            for cos in self.job_cost_sheet:
                                if not line.cs_overhead_id:
                                    cos.material_overhead_ids = [(0, 0, {
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable_ref': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'product_qty': line.quantity,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'reserved_qty': line.quantity,
                                                                # 'price_unit': line.product.list_price,
                                                                # 'material_amount_total': line.subtotal,
                                                            })] 
                                    line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                                else:
                                    reserved_cs = 0.00
                                    converted_cs = 0.00
                                    if line.product_unit_measure != line.cs_overhead_id.uom_id:
                                        converted_cs = self.convert_overhead_uom_cs(line)
                                        reserved_cs = line.cs_overhead_id.reserved_qty + converted_cs
                                        for cs in self.job_cost_sheet:
                                            cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                                    else:
                                        reserved_cs = line.cs_overhead_id.reserved_qty + line.quantity
                                        for cs in self.job_cost_sheet:
                                            cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  

                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_cs = 0.00
                                converted_cs = 0.00
                                if line.product_unit_measure != line.cs_overhead_id.uom_id:
                                    converted_cs = self.convert_overhead_uom_cs(line)
                                    reserved_cs = line.cs_overhead_id.reserved_qty + converted_cs
                                    for cs in self.job_cost_sheet:
                                        cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_cs = line.cs_overhead_id.reserved_qty + line.quantity
                                    for cs in self.job_cost_sheet:
                                        cs.material_overhead_ids = [(1, line.cs_overhead_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
            if self.type_of_mr == 'equipment':
                if self.project_budget:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            if not line.cs_equipment_id:
                                for cos in self.job_cost_sheet:
                                        cos.material_equipment_ids = [(0, 0, {
                                                                    'project_scope': line.project_scope.id,
                                                                    'section_name': line.section.id,
                                                                    'variable_ref': line.variable.id,
                                                                    'group_of_product': line.group_of_product.id,
                                                                    'product_id': line.product.id,
                                                                    'description': line.description,
                                                                    'product_qty': line.quantity,
                                                                    'uom_id': line.product_unit_measure.id,
                                                                    'reserved_qty': line.quantity,
                                                                    # 'price_unit': line.product.list_price,
                                                                    # 'material_amount_total': line.subtotal,
                                                                })]
                                for bud in self.project_budget:
                                    if not line.bd_equipment_id:
                                        cs_mat = self.env['material.equipment'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                                        bud.budget_equipment_ids = [(0, 0, {
                                                                'cs_equipment_id': cs_mat.id,
                                                                'project_scope': line.project_scope.id,
                                                                'section_name': line.section.id,
                                                                'variable': line.variable.id,
                                                                'group_of_product': line.group_of_product.id,
                                                                'product_id': line.product.id,
                                                                'description': line.description,
                                                                'uom_id': line.product_unit_measure.id,
                                                                'budget_quantity': line.quantity,
                                                                'qty_res': line.quantity,
                                                                # 'amount': line.price_unit,
                                                                # 'budget_amount': line.line_amount_total,
                                                            })]
                                line.cs_equipment_id = cs_mat.id
                                line.bd_equipment_id = self.env['budget.equipment'].search([('budget_id', '=', self.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_equipment_id.uom_id:
                                    converted_bd = self.convert_equipment_uom_bd(line)
                                    reserved_bud = line.bd_equipment_id.qty_res + converted_bd
                                    reserved_cs = line.cs_equipment_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_equipment_ids = [(1, line.bd_equipment_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_equipment_id.qty_res + line.quantity
                                    reserved_cs = line.cs_equipment_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_equipment_ids = [(1, line.bd_equipment_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_bud = 0.00
                                reserved_cs = 0.00
                                converted_bd = 0.00
                                if line.product_unit_measure != line.bd_equipment_id.uom_id:
                                    converted_bd = self.convert_equipment_uom_bd(line)
                                    reserved_bud = line.bd_equipment_id.qty_res + converted_bd
                                    reserved_cs = line.cs_equipment_id.reserved_qty + converted_bd
                                    for sub in self.project_budget:
                                        sub.budget_equipment_ids = [(1, line.bd_equipment_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_cs(reserved_cs))]
                                else:
                                    reserved_bud = line.bd_equipment_id.qty_res + line.quantity
                                    reserved_cs = line.cs_equipment_id.reserved_qty + line.quantity
                                    for sub in self.project_budget:
                                        sub.budget_equipment_ids = [(1, line.bd_equipment_id.id, self.prepare_reserved_bd(reserved_bud))]
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                else:
                    if self.budgeting_method != 'product_budget':
                        for line in self.product_line:
                            if not line.cs_equipment_id:                            
                                for cos in self.job_cost_sheet:
                                        cos.material_equipment_ids = [(0, 0, {
                                                                    'project_scope': line.project_scope.id,
                                                                    'section_name': line.section.id,
                                                                    'variable_ref': line.variable.id,
                                                                    'group_of_product': line.group_of_product.id,
                                                                    'product_id': line.product.id,
                                                                    'description': line.description,
                                                                    'product_qty': line.quantity,
                                                                    'uom_id': line.product_unit_measure.id,
                                                                    'reserved_qty': line.quantity,
                                                                    # 'price_unit': line.product.list_price,
                                                                    # 'material_amount_total': line.subtotal,
                                                                })]
                                line.cs_equipment_id = self.env['material.overhead'].search([('job_sheet_id', '=', self.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)], limit=1)
                            else:
                                reserved_cs = 0.00
                                converted_cs = 0.00
                                
                                if line.product_unit_measure != line.cs_equipment_id.uom_id:
                                    converted_cs = self.convert_equipment_uom_cs(line)
                                    reserved_cs = line.cs_equipment_id.reserved_qty + converted_cs
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_bd(reserved_bud))]
                                else:
                                    reserved_cs = line.cs_equipment_id.reserved_qty + line.quantity
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res
                    else:
                        for line in self.product_line:
                            if line.quantity > line.budget_quantity:
                                raise ValidationError(_("The quantity is over the remaining budget"))
                            else:
                                reserved_cs = 0.00
                                converted_cs = 0.00
                                
                                if line.product_unit_measure != line.cs_equipment_id.uom_id:
                                    converted_cs = self.convert_equipment_uom_cs(line)
                                    reserved_cs = line.cs_equipment_id.reserved_qty + converted_cs
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_bd(reserved_bud))]
                                else:
                                    reserved_cs = line.cs_equipment_id.reserved_qty + line.quantity
                                    for cs in self.job_cost_sheet:
                                        cs.material_equipment_ids = [(1, line.cs_equipment_id.id, self.prepare_reserved_cs(reserved_cs))]
                        return res  
                    
    def prepare_pr_line(self, line, count, qty):
        return {
            'no': count,
            'mr_id': self.id,
            'mr_line_id': line.id,
            'type': self.type_of_mr,
            'project_scope': line.project_scope.id,
            'section': line.section.id,
            'variable_ref': line.variable.id,
            'group_of_product': line.group_of_product.id,
            'product_id' : line.product.id,
            'description' : line.description,
            'uom_id' : line.product_unit_measure.id,
            'qty_purchase' : qty,
            'request_date' : line.request_date,
        }

    def create_purchase_request(self):
        context = self.env.context.copy()
        pr_line = []
        count = 1
        if self.job_cost_sheet.state == 'freeze':
            raise ValidationError("The budget for this project is being freeze")
        else:
            for line in self.product_line:
                qty = line.quantity - line.done_qty
                if qty < 0:
                    qty = 0
                if line.status_2 == 'confirm':
                    vals = self.prepare_pr_line(line, count, qty)
                    pr_line.append((0,0, vals))
                    count = count+1
            context.update({
                'default_material_request': self.id,
                'default_pr_wizard_line': pr_line,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Purchase Request',
                'res_model': 'purchase.request.wizard',
                'view_id': self.env.ref('equip3_inventory_operation.purchase_request_wizard_form_view').id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
                'context': context,
            }

    def _compute_agreement_count(self):
        for rec in self:
            dom = [('sh_source', '=', self.name)]
            rec.agreement_count = self.env['purchase.agreement'].search_count(
                dom)

    type_of_mr = fields.Selection([('material','Material'),('labour','Labour'),('overhead','Overhead'),('equipment','Equipment')],
                                  string = "Type Of MR")
     
    def get_material_cs(self, res, material, mat):
        if mat.budgeted_qty_left > 0:
            res.product_line = [(0, 0, {
                'project_scope': mat.project_scope.id,
                'section': mat.section_name.id,
                'product': mat.product_id.id,
                'description': mat.description,
                'group_of_product': mat.group_of_product.id,
                'quantity': mat.budgeted_qty_left,
                'budget_quantity': mat.budgeted_qty_left,
                'product_unit_measure': mat.uom_id.id,
                'destination_warehouse_id': material.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, [v.id for v in material.account_tag_ids])],
                'source_document': res.job_cost_sheet.number,
            })]

    def get_labour_cs(self, res, labour, lab):
        if lab.budgeted_qty_left > 0:
            res.product_line = [(0, 0, {
                'project_scope': lab.project_scope.id,
                'section': lab.section_name.id,
                'product': lab.product_id.id,
                'description': lab.description,
                'group_of_product': lab.group_of_product.id,
                'quantity': lab.budgeted_qty_left,
                'budget_quantity': lab.budgeted_qty_left,
                'product_unit_measure': lab.uom_id.id,
                'destination_warehouse_id': labour.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, [v.id for v in labour.account_tag_ids])],
                'source_document': res.job_cost_sheet.number,
            })]

    def get_overhead_cs(self, res, overhead, ove):
        if ove.budgeted_qty_left > 0:
            res.product_line = [(0, 0, {
                'project_scope': ove.project_scope.id,
                'section': ove.section_name.id,
                'product': ove.product_id.id,
                'description': ove.description,
                'group_of_product': ove.group_of_product.id,
                'quantity': ove.budgeted_qty_left,
                'budget_quantity': ove.budgeted_qty_left,
                'product_unit_measure': ove.uom_id.id,
                'destination_warehouse_id': overhead.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, [v.id for v in overhead.account_tag_ids])],
                'source_document': res.job_cost_sheet.number,
            })]
    
    def get_material_bd(self, res, material, mat):
        if mat.qty_left > 0:
            res.product_line = [(0, 0, {
                'project_scope': mat.project_scope.id,
                'section': mat.section_name.id,
                'product': mat.product_id.id,
                'description': mat.description,
                'group_of_product': mat.group_of_product.id,
                'quantity': mat.qty_left,
                'budget_quantity': mat.qty_left,
                'product_unit_measure': mat.uom_id.id,
                'destination_warehouse_id': material.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, [v.id for v in material.analytic_group_id])],
                'source_document': res.project_budget.name,
            })]
        
    def get_labour_bd(self, res, labour, lab):
        if lab.qty_left > 0:
            res.product_line = [(0, 0, {
                'project_scope': lab.project_scope.id,
                'section': lab.section_name.id,
                'product': lab.product_id.id,
                'description': lab.description,
                'group_of_product': lab.group_of_product.id,
                'quantity': lab.qty_left,
                'budget_quantity': lab.qty_left,
                'product_unit_measure': lab.uom_id.id,
                'destination_warehouse_id': labour.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, [v.id for v in labour.analytic_group_id])],
                'source_document': res.project_budget.name,
            })]
    
    def get_overhead_bd(self, res, overhead, ove):
        if ove.qty_left > 0:
            res.product_line = [(0, 0, {
                'project_scope': ove.project_scope.id,
                'section': ove.section_name.id,
                'product': ove.product_id.id,
                'description': ove.description,
                'group_of_product': ove.group_of_product.id,
                'quantity': ove.qty_left,
                'budget_quantity': ove.qty_left,
                'product_unit_measure': ove.uom_id.id,
                'destination_warehouse_id': overhead.warehouse_id.id,
                'analytic_account_group_ids': [(6, 0, [v.id for v in overhead.analytic_group_id])],
                'source_document': res.project_budget.name,
            })]

    def get_material_from_cost(self, res):
        for material in res.job_cost_sheet:
            for mat in material.material_ids:
                if res.budgeting_method != 'product_budget':
                    if mat.budgeted_qty_left > 0 and mat.budgeted_amt_left:
                        res.get_material_cs(res, material, mat)
                else:
                    if mat.budgeted_qty_left > 0 and mat.budgeted_amt_left:
                        res.get_material_cs(res, material, mat)
        
    def get_labour_from_cost(self, res):
        for labour in res.job_cost_sheet:
            for lab in labour.material_labour_ids:
                if res.budgeting_method != 'product_budget':
                    if lab.budgeted_qty_left > 0 and lab.budgeted_amt_left > 0:
                        res.get_labour_cs(res, labour, lab)
                else:
                    if lab.budgeted_qty_left > 0 and lab.budgeted_amt_left > 0:
                        res.get_labour_cs(res, labour, lab)
           
    def get_overhead_from_cost(self, res):
        for overhead in res.job_cost_sheet:
            for ove in overhead.material_overhead_ids:
                if res.budgeting_method != 'product_budget':
                    if ove.overhead_catagory in ('product','fuel') and ove.budgeted_qty_left > 0 and ove.budgeted_amt_left > 0:
                        res.get_overhead_cs(res, overhead, ove)
                else:
                    if ove.overhead_catagory in ('product','fuel') and ove.budgeted_qty_left > 0 and ove.budgeted_amt_left > 0:
                       res.get_overhead_cs(res, overhead, ove)
    
    def get_material_from_budget(self, res):
        for material in res.project_budget:
            for mat in material.budget_material_ids:
                if res.budgeting_method != 'product_budget':
                    if mat.qty_left > 0 and mat.amt_left > 0:
                        res.get_material_bd(res, material, mat)
                else:
                    if mat.qty_left > 0 and mat.amt_left > 0:
                        res.get_material_bd(res, material, mat)
        
    def get_labour_from_budget(self, res):
        for labour in res.project_budget:
            for lab in labour.budget_labour_ids:
                if res.budgeting_method != 'product_budget':
                    if lab.qty_left > 0 and lab.amt_left > 0:
                        res.get_labour_bd(res, labour, lab)
                else:
                    if lab.qty_left > 0 and lab.amt_left > 0:
                        res.get_labour_bd(res, labour, lab)

    def get_overhead_from_budget(self, res):
        for overhead in res.project_budget:
            for ove in overhead.budget_overhead_ids:
                if res.budgeting_method != 'product_budget':
                    if ove.overhead_catagory in ('product','fuel') and ove.qty_left > 0 and ove.amt_left > 0:
                        res.get_overhead_bd(res, overhead, ove)
                else:
                    if ove.overhead_catagory in ('product','fuel') and ove.qty_left > 0 and ove.amt_left > 0:
                        res.get_overhead_bd(res, overhead, ove)
    
    @api.onchange('project', 'type_of_mr', 'multiple_budget_ids', 'is_multiple_budget')
    def _onchange_project(self):
        for res in self:
            if res.project:
                for proj in res.project:
                    res.job_cost_sheet = res.env['job.cost.sheet'].search([('project_id', '=', proj.id), ('state', 'not in', ['cancelled','reject','revised'])])
                    res.analytic_account_group_ids = [(6, 0, [v.id for v in proj.analytic_idz])]
                    res.branch_id = res.project.branch_id.id
                return
                res.product_line = [(5, 0, 0)]
                # validation budget left
                bud_qty_left = 0
                bud_amt_left = 0
                if res.type_of_mr == 'material':
                    if res.budgeting_method == 'product_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.job_cost_sheet.material_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for material left")
                            else:
                                for material in res.job_cost_sheet:
                                    for mat in material.material_ids:
                                        if mat.budgeted_qty_left > 0:
                                            res.get_material_cs(res, material, mat)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_material_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.project_budget:
                                        for mat in material.budget_material_ids:
                                            if mat.qty_left > 0:
                                                res.get_material_bd(res, material, mat)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_material_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.multiple_budget_ids:
                                        for mat in material.budget_material_ids:
                                            if mat.qty_left > 0:
                                                res.get_material_bd(res, material, mat)
                    
                    elif res.budgeting_method == 'gop_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.job_cost_sheet.material_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for material left")
                            else:
                                for material in res.job_cost_sheet:
                                    for mat in material.material_ids:
                                        res.get_material_cs(res, material, mat)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_material_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.project_budget:
                                        for mat in material.budget_material_ids:
                                            res.get_material_bd(res, material, mat)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_material_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.multiple_budget_ids:
                                        for mat in material.budget_material_ids:
                                            res.get_material_bd(res, material, mat)
                    
                    elif res.budgeting_method == 'budget_type':
                        if res.budgeting_period == 'project':
                            if res.job_cost_sheet.material_budget_left < 1 :
                                ValidationError("There is no budget for material left")
                            else:
                                for material in res.job_cost_sheet:
                                    for mat in material.material_ids:
                                        res.get_material_cs(res, material, mat)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.amount_left_material < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.project_budget:
                                        for mat in material.budget_material_ids:
                                            res.get_material_bd(res, material, mat)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_material
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.multiple_budget_ids:
                                        for mat in material.budget_material_ids:
                                            res.get_material_bd(res, material, mat)

                    elif res.budgeting_method == 'total_budget':
                        if res.budgeting_period == 'project':
                            if res.job_cost_sheet.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for material left")
                            else:
                                for material in res.job_cost_sheet:
                                    for mat in material.material_ids:
                                        res.get_material_cs(res, material, mat)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.budget_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.project_budget:
                                        for mat in material.budget_material_ids:
                                            res.get_material_bd(res, material, mat)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.budget_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for material left")
                                else:
                                    for material in res.multiple_budget_ids:
                                        for mat in material.budget_material_ids:
                                            res.get_material_bd(res, material, mat)
                
                elif res.type_of_mr == 'labour':
                    if res.budgeting_method == 'product_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.job_cost_sheet.material_labour_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                            else:
                                for labour in res.job_cost_sheet:
                                    for lab in labour.material_labour_ids:
                                        if lab.budgeted_qty_left > 0:
                                            res.get_labour_cs(res, labour, lab)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_labour_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.project_budget:
                                        for lab in labour.budget_labour_ids:
                                            if lab.qty_left > 0:
                                                res.get_labour_bd(res, labour, lab)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_labour_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.multiple_budget_ids:
                                        for lab in labour.budget_labour_ids:
                                            if lab.qty_left > 0:
                                                res.get_labour_bd(res, labour, lab)
                    
                    elif res.budgeting_method == 'gop_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.job_cost_sheet.material_labour_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                            else:
                                for labour in res.job_cost_sheet:
                                    for lab in labour.material_labour_ids:
                                        res.get_labour_cs(res, labour, lab)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_labour_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.project_budget:
                                        for lab in labour.budget_labour_ids:
                                            res.get_labour_bd(res, labour, lab)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_labour_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.multiple_budget_ids:
                                        for lab in labour.budget_labour_ids:
                                            res.get_labour_bd(res, labour, lab)
                    
                    elif res.budgeting_method == 'budget_type':
                        if res.budgeting_period == 'project':
                            if res.job_cost_sheet.labour_budget_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                            else:
                                for labour in res.job_cost_sheet:
                                    for lab in labour.material_labour_ids:
                                        res.get_labour_cs(res, labour, lab)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.amount_left_labour < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.project_budget:
                                        for lab in labour.budget_labour_ids:
                                            res.get_labour_bd(res, labour, lab)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_labour
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.multiple_budget_ids:
                                        for lab in labour.budget_labour_ids:
                                            res.get_labour_bd(res, labour, lab)

                    elif res.budgeting_method == 'total_budget':
                        if res.budgeting_period == 'project':
                            if res.job_cost_sheet.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for labour left")
                            else:
                                for labour in res.job_cost_sheet:
                                    for lab in labour.material_labour_ids:
                                        res.get_labour_cs(res, labour, lab)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.budget_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.project_budget:
                                        for lab in labour.budget_labour_ids:
                                            res.get_labour_bd(res, labour, lab)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.budget_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for labour left")
                                else:
                                    for labour in res.multiple_budget_ids:
                                        for lab in labour.budget_labour_ids:
                                            res.get_labour_bd(res, labour, lab)

                elif res.type_of_mr == 'overhead':
                    if res.budgeting_method == 'product_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.job_cost_sheet.material_overhead_ids:
                                bud_qty_left += line_id.budgeted_qty_left
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_qty_left < 1 or bud_amt_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                            else:
                                for overhead in res.job_cost_sheet:
                                    for ove in overhead.material_overhead_ids:
                                        if ove.overhead_catagory in ('product','fuel') and ove.budgeted_qty_left > 0:
                                            res.get_overhead_cs(res, overhead, ove)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_overhead_ids:
                                    bud_qty_left += line_bud.qty_left
                                    bud_amt_left += line_bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.project_budget:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel') and ove.qty_left > 0:
                                                res.get_overhead_bd(res, overhead, ove)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_overhead_ids:
                                        bud_qty_left += bud.qty_left
                                        bud_amt_left += bud.amt_left
                                if bud_qty_left < 1 or bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.multiple_budget_ids:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel') and ove.qty_left > 0:
                                                res.get_overhead_bd(res, overhead, ove)
                    
                    elif res.budgeting_method == 'gop_budget':
                        if res.budgeting_period == 'project':
                            for line_id in res.job_cost_sheet.material_overhead_gop_ids:
                                bud_amt_left += line_id.budgeted_amt_left
                            if bud_amt_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                            else:
                                for overhead in res.job_cost_sheet:
                                    for ove in overhead.material_overhead_ids:
                                        if ove.overhead_catagory in ('product','fuel'):
                                            res.get_overhead_cs(res, overhead, ove)
                        else:
                            if res.is_multiple_budget == False:
                                for line_bud in res.project_budget.budget_overhead_gop_ids:
                                    bud_amt_left += line_bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.project_budget:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel'):
                                                res.get_overhead_bd(res, overhead, ove)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    for bud in budget_id.budget_overhead_gop_ids:
                                        bud_amt_left += bud.amt_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.multiple_budget_ids:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel'):
                                                res.get_overhead_bd(res, overhead, ove)
                    
                    elif res.budgeting_method == 'budget_type':
                        if res.budgeting_period == 'project':
                            if res.job_cost_sheet.overhead_budget_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                            else:
                                for overhead in res.job_cost_sheet:
                                    for ove in overhead.material_overhead_ids:
                                        if ove.overhead_catagory in ('product','fuel'):
                                            res.get_overhead_cs(res, overhead, ove)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.amount_left_overhead < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.project_budget:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel'):
                                                res.get_overhead_bd(res, overhead, ove)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.amount_left_overhead
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.multiple_budget_ids:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel'):
                                                res.get_overhead_bd(res, overhead, ove)

                    elif res.budgeting_method == 'total_budget':
                        if res.budgeting_period == 'project':
                            if res.job_cost_sheet.contract_budget_left < 1 :
                                raise ValidationError("There is no budget for overhead left")
                            else:
                                for overhead in res.job_cost_sheet:
                                    for ove in overhead.material_overhead_ids:
                                        if ove.overhead_catagory in ('product','fuel'):
                                            res.get_overhead_cs(res, overhead, ove)
                        else:
                            if res.is_multiple_budget == False:
                                if res.project_budget.budget_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.project_budget:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel'):
                                                res.get_overhead_bd(res, overhead, ove)
                            else:
                                for budget_id in res.multiple_budget_ids:
                                    bud_amt_left += budget_id.budget_left
                                if bud_amt_left < 1 :
                                    raise ValidationError("There is no budget for overhead left")
                                else:
                                    for overhead in res.multiple_budget_ids:
                                        for ove in overhead.budget_overhead_ids:
                                            if ove.overhead_catagory in ('product','fuel'):
                                                res.get_overhead_bd(res, overhead, ove)
                
                
                for line in res.product_line:
                    line._onchange_product()


    def _get_project_budget(self, res):
        Job_cost_sheet = res.job_cost_sheet
        if res.schedule_date:
            schedule = datetime.strptime(str(self.schedule_date), "%Y-%m-%d")
            month_date = schedule.strftime("%B")
            if res.project.budgeting_period == 'monthly':
                data = res.env['budget.period.line'].search([('month', '=', month_date),
                                                            ('line_project_ids', '=', Job_cost_sheet.project_id.id),], limit=1)
                budget = res.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                            ('cost_sheet', '=', Job_cost_sheet.id),
                                                            ('month', '=', data.id)], limit=1)
                return budget
            elif res.project.budgeting_period == 'custom':
                budget = res.env['project.budget'].search([('project_id', '=', Job_cost_sheet.project_id.id),
                                                            ('cost_sheet', '=', Job_cost_sheet.id),
                                                            ('bd_start_date', '<=', res.schedule_date),
                                                            ('bd_end_date', '>=', res.schedule_date)], limit=1)
                return budget
            else:
                pass

    @api.onchange('project', 'schedule_date')
    def _onchange_project_budget(self):
        for res in self:
            if res.project:
                # res.analytic_account_group_ids = [(6, 0, res.project.analytic_idz.ids)]
                res.destination_warehouse_id = res.project.warehouse_address.id
                if res.budgeting_period != 'project':
                    budget = res._get_project_budget(res)
                    if budget:
                        res.project_budget = budget.id
                    else:
                        raise ValidationError(_("There is no periodical budget created for this date"))

    # @api.onchange('type_of_mr')
    # def _onchange_type_of_mr(self):
    #     for record in self:
    #         {}

    @api.onchange('project', 'type_of_mr', 'destination_warehouse_id','product_line')
    def onchange_approval_matrix(self):
        quntity_val =[]
        for rec in self.product_line:
            quntity_val.append(rec.quantity)
        total_quntity = sum(quntity_val)
        for rec in self:
            matrix_id = self.env['mr.approval.matrix'].search([('project', '=', self.project.id),
                                                               ('type_of_mr', '=', self.type_of_mr),
                                                               ('warehouse_id', '=', self.destination_warehouse_id.id),
                                                               ('minimum_amount','<=',total_quntity),
                                                               ('maximum_amount','>=',total_quntity)])
            if matrix_id:
                rec.mr_approval_matrix_id = matrix_id[0].id
            else:
                rec.mr_approval_matrix_id = False      

    @api.constrains('product_line')
    def _check_product_dup(self):
        pass

    def create_asset_purchase_request(self):
        data = []
        for record in self:
            for line in self.product_line:
                data.append((0, 0, {'project_scope': line.project_scope.id,
                                    'section': line.section.id,
                                    'variable': line.variable.id,
                                    'group_of_product': line.group_of_product.id,
                                    'product_id': line.product.id,
                                    'name': line.description,
                                    'product_qty': line.quantity,
                                    'budget_quantity': line.quantity,
                                    'product_uom_id': line.product_unit_measure.id,
                                    }))
                
            purchase_request = self.env['purchase.request'].create({
                    'requested_by' : record.create_uid.id,
                    'company_id' : record.company_id.id,
                    'project': record.project.id,
                    'cost_sheet': record.job_cost_sheet.id,
                    'project_budget': record.project_budget.id,
                    'branch_id': record.branch_id.id,
                    'line_ids': data,
                    'is_assets_orders' : True,
                    'is_orders' : True,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': 'Purchase Request',
                'view_mode': 'form',
                'res_model': 'purchase.request',
                'res_id' : purchase_request.id,
                'target': 'current',
            }

    #  on click 'interwarehouse transfer' button -------
    def create_internal_transfer(self):
        context = self.env.context.copy()
        ir_line = []
        count = 1
        for line in self.product_line:
            qty = line.quantity - line.done_qty
            if qty < 0:
                qty = 0
            vals = {
                'no': count,
                'mr_id': self.id,
                'mr_line_id': line.id,
                'project_scope': line.project_scope.id,
                'section': line.section.id,
                'variable': line.variable.id,
                'group_of_product': line.group_of_product.id,
                'product_id': line.product.id,
                'description': line.product.description,
                'uom_id': line.product.uom_id.id,
                # 'current_qty' : avl_qty,
                # 'virtual_available' : forecast_qty,
                'qty_transfer': qty,
            }
            ir_line.append((0, 0, vals))
            count = count+1
        context.update({
            'default_project_budget': self.project_budget.id,
            'default_cost_sheet': self.job_cost_sheet.id,
            'default_ir_wizard_line': ir_line,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Interwarehouse Transfer',
            'res_model': 'mr.internal_transfer',
            'view_id': self.env.ref('equip3_inventory_operation.internal_transfer_wizard_form_view').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }
    
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines",
                                              compute='get_scope_lines')

    @api.depends('project.project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            pro = rec.project
            scope_ids = []
            if pro.project_scope_ids:
                for line in pro.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

class OrdersMaterialRequestLine(models.Model):
    _inherit = 'material.request.line'

    project = fields.Many2one(related='material_request_id.project', string='Project')
    sequence = fields.Integer(string="sequence", default=0)
    no = fields.Integer('No.', compute="_sequence_ref")

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
    bd_equipment_id = fields.Many2one('budget.equipment', string='BD equipment ID')

    project_scope = fields.Many2one('project.scope.line', 'Project Scope')
    section = fields.Many2one('section.line', 'Section')
    variable = fields.Many2one('variable.template', 'Variable')
    budget_quantity = fields.Float('Budget Quantity')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    status_2 = fields.Selection([
        ('draft', 'Draft'),
        ('to_approve', 'To be Approved'),
        ('approved', 'Approved'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled'),
        ('Rejected', 'Rejected')], 
        string = "Status", 
        readonly='1',
        default= 'draft')
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                 compute='get_section_lines')

    @api.depends('material_request_id.product_line', 'material_request_id.product_line.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.no = no
            for l in line.material_request_id.product_line:
                no += 1
                l.no = no
    
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
                    'domain': {'product': [('group_of_product', '=', group_of_product)]}
                }
            else:
                return {
                    'domain': {'product': []}
                }
    
    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product and self.group_of_product:
            if self.group_of_product.id not in self.product.group_of_product.ids:
                self.update({
                    'product': False,
                })
    
    @api.onchange('material_request_id')
    def _onchange_material_request_id(self):
        domain_dict = { x.group_of_product.id : 0 for x in self.material_request_id.job_cost_sheet.material_ids}
        domain_dict.update({ x.group_of_product.id : 0 for x in self.material_request_id.job_cost_sheet.material_labour_ids})
        domain_dict.update({ x.group_of_product.id : 0 for x in self.material_request_id.job_cost_sheet.material_overhead_ids})
        return {
                    'domain': {'group_of_product': [('id','in', [k for k, v in domain_dict.items()])]}
                }

    #@api.onchange('project_scope')
    #def onchange_project_scope(self):
    #    if not self.material_request_id.project:
    #        raise ValidationError(_("Select Project First"))

    @api.constrains('product')
    def _check_product_type(self):
        for record in self:
            if self.material_request_id.type_of_mr == 'labour':
                pass
            else:
                if record.product.type == 'service':
                    raise ValidationError('user can’t add a product which type is service in material requests')

    @api.onchange('material_request_id.type_of_mr', 'material_request_id.is_multiple_budget',  
                  'project_scope', 'section', 'product', 'group_of_product')
    def _onchange_product(self):
        for line in self:
            if line.material_request_id.budgeting_method == 'gop_budget':
                if line.project_scope and line.section and line.group_of_product:
                    if line.material_request_id.type_of_mr == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False
                        line.cs_material_gop_id = False
                        line.bd_material_gop_id = False
                        line.bd_material_gop_ids = False
                        line.cs_material_gop_id = self.env['material.gop.material'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                        
                        if line.material_request_id.is_multiple_budget == False:
                            if line.material_request_id.project_budget:
                                line.bd_material_gop_id = self.env['budget.gop.material'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                line.budget_quantity = line.bd_material_id.qty_left
                            else:
                                line.budget_quantity = line.cs_material_id.budgeted_qty_left
                        else:
                            budget_gop_ids = []
                            budget_mat_ids = []
                            budget = self.env['budget.gop.material'].search([('budget_id', 'in', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_mat = self.env['budget.material'].search([('budget_id', 'in', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                            
                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_mat: 
                                for buds in budget_mat:
                                    budget_mat_ids.append((0,0, buds.id))
                                    line.budget_quantity += buds.qty_left
                            else:
                                line.budget_quantity = 0
                        
                            line.bd_material_gop_ids = budget_gop_ids
                            line.bd_material_ids = budget_mat_ids

                    if line.material_request_id.type_of_mr == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        line.bd_labour_ids = False
                        line.cs_labour_gop_id = False
                        line.bd_labour_gop_id = False
                        line.bd_labour_gop_ids = False
                        line.cs_labour_gop_id = self.env['material.gop.labour'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                        line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                        
                        if line.material_request_id.is_multiple_budget == False:    
                            if line.material_request_id.project_budget:
                                line.bd_labour_gop_id = self.env['budget.gop.labour'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                line.budget_quantity = line.bd_labour_id.qty_left
                            else:
                                line.budget_quantity = line.cs_labour_id.budgeted_qty_left
                        else:
                            budget_gop_ids = []
                            budget_lab_ids = []
                            budget = self.env['budget.gop.labour'].search([('budget_id', 'in', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_lab = self.env['budget.labour'].search([('budget_id', 'in', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                            
                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_lab:
                                for buds in budget_lab:
                                    budget_lab_ids.append((0,0, buds.id))
                                    line.budget_quantity += buds.qty_left
                            else:
                                line.budget_quantity = 0
                        
                            line.bd_labour_gop_ids = budget_gop_ids
                            line.bd_labour_ids = budget_lab_ids

                    if line.material_request_id.type_of_mr == 'overhead':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False
                        line.cs_overhead_gop_id = False
                        line.bd_overhead_gop_id = False
                        line.bd_overhead_gop_ids = False
                        line.cs_overhead_gop_id = self.env['material.gop.overhead'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])       
                        line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])       
                        
                        if line.material_request_id.is_multiple_budget == False:    
                            if line.material_request_id.project_budget:
                                line.bd_overhead_gop_id = self.env['budget.gop.overhead'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                                line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                line.budget_quantity = line.bd_overhead_id.qty_left
                            else:
                                line.budget_quantity = line.cs_overhead_id.budgeted_qty_left
                        else:
                            budget_gop_ids = []
                            budget_ove_ids = []
                            budget = self.env['budget.gop.overhead'].search([('budget_id', '=', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id)])
                            budget_ove = self.env['budget.overhead'].search([('budget_id', '=', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                            
                            if budget:
                                for bud in budget:
                                    budget_gop_ids.append((0,0, bud.id))

                            if budget_ove:
                                for buds in budget:
                                    budget_ove_ids.append((0,0, buds.id))
                                    line.budget_quantity += bud.qty_left
                            else:
                                line.budget_quantity = 0
                        
                            line.bd_overhead_gop_ids = budget_gop_ids
                            line.bd_overhead_ids = budget_ove_ids
                        
                        
            elif line.material_request_id.budgeting_method in ('product_budget', 'budget_type', 'total_budget'):
                if line.project_scope and line.section and line.product:
                    if line.material_request_id.type_of_mr == 'material':
                        line.cs_material_id = False
                        line.bd_material_id = False
                        line.bd_material_ids = False
                        line.cs_material_id = self.env['material.material'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                        
                        if line.material_request_id.is_multiple_budget == False:
                            if line.material_request_id.project_budget:
                                line.bd_material_id = self.env['budget.material'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                line.budget_quantity = line.bd_material_id.qty_left
                            else:
                                line.budget_quantity = line.cs_material_id.budgeted_qty_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.material'].search([('budget_id', 'in', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))
                                    line.budget_quantity += bud.qty_left
                            else:
                                line.budget_quantity = 0
                        
                            line.bd_material_ids = budget_ids

                    if line.material_request_id.type_of_mr == 'labour':
                        line.cs_labour_id = False
                        line.bd_labour_id = False
                        line.bd_labour_ids = False
                        line.cs_labour_id = self.env['material.labour'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                        
                        if line.material_request_id.is_multiple_budget == False:    
                            if line.material_request_id.project_budget:
                                line.bd_labour_id = self.env['budget.labour'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                line.budget_quantity = line.bd_labour_id.qty_left
                            else:
                                line.budget_quantity = line.cs_labour_id.budgeted_qty_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.labour'].search([('budget_id', 'in', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))
                                    line.budget_quantity += bud.qty_left
                            else:
                                line.budget_quantity = 0
                        
                            line.bd_labour_ids = budget_ids

                    if line.material_request_id.type_of_mr == 'overhead':
                        line.cs_overhead_id = False
                        line.bd_overhead_id = False
                        line.bd_overhead_ids = False
                        line.cs_overhead_id = self.env['material.overhead'].search([('job_sheet_id', '=', line.material_request_id.job_cost_sheet.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])       
                        
                        if line.material_request_id.is_multiple_budget == False:    
                            if line.material_request_id.project_budget:
                                line.bd_overhead_id = self.env['budget.overhead'].search([('budget_id', '=', line.material_request_id.project_budget.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                                line.budget_quantity = line.bd_overhead_id.qty_left
                            else:
                                line.budget_quantity = line.cs_overhead_id.budgeted_qty_left

                        else:
                            budget_ids = []
                            budget = self.env['budget.overhead'].search([('budget_id', '=', line.material_request_id.multiple_budget_ids.id), ('project_scope', '=', line.project_scope.id), ('section_name', '=', line.section.id), ('group_of_product', '=', line.group_of_product.id), ('product_id', '=', line.product.id)])
                            if budget:
                                for bud in budget:
                                    budget_ids.append((0,0, bud.id))
                                    line.budget_quantity += bud.qty_left
                            else:
                                line.budget_quantity = 0
                        
                            line.bd_overhead_ids = budget_ids


    @api.onchange('product_unit_measure')
    def _onchange_product_unit_measure(self):
        for line in self:
            converted_budget = 0
            if line.material_request_id.type_of_mr == 'material':
                if line.material_request_id.is_multiple_budget == False:
                    if line.cs_material_id and line.bd_material_id:
                        if line.product_unit_measure == line.bd_material_id.uom_id:
                            converted_budget = line.bd_material_id.qty_left
                        else:
                            line_factor = line.product_unit_measure.factor
                            line_factor_inv = line.product_unit_measure.factor_inv
                            dest_bd_factor = line.bd_material_id.uom_id.factor
                            dest_bd_factor_inv = line.bd_material_id.uom_id.factor_inv
                            if line.product_unit_measure.uom_type == 'reference':
                                if line.bd_material_id.uom_id.uom_type == 'bigger':
                                    converted_budget = (line.bd_material_id.qty_left * dest_bd_factor_inv)
                                elif line.bd_material_id.uom_id.uom_type == 'smaller':
                                    converted_budget = (line.bd_material_id.qty_left / dest_bd_factor)
                                elif line.bd_material_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_material_id.qty_left)
                            elif line.product_unit_measure.uom_type == 'bigger':
                                if line.bd_material_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.bd_material_id.qty_left * line_factor_inv) / dest_bd_factor_inv)
                                elif line.bd_material_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.bd_material_id.qty_left / dest_bd_factor) / line_factor_inv)
                                elif line.bd_material_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_material_id.qty_left / line_factor_inv)
                            elif line.product_unit_measure.uom_type == 'smaller':
                                if line.bd_material_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.bd_material_id.qty_left * dest_bd_factor_inv) * line_factor)
                                elif line.bd_material_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.bd_material_id.qty_left / dest_bd_factor) * line_factor)
                                elif line.bd_material_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_material_id.qty_left * line_factor)
                        line.budget_quantity = converted_budget
                        
                    elif line.cs_material_id and not line.bd_material_id:
                        if line.product_unit_measure == line.cs_material_id.uom_id:
                            converted_budget = line.cs_material_id.budgeted_qty_left
                        else:
                            line_factor = line.product_unit_measure.factor
                            line_factor_inv = line.product_unit_measure.factor_inv
                            dest_cs_factor = line.cs_material_id.uom_id.factor
                            dest_cs_factor_inv = line.cs_material_id.uom_id.factor_inv
                            if line.product_unit_measure.uom_type == 'reference':
                                if line.cs_material_id.uom_id.uom_type == 'bigger':
                                    converted_budget = (line.cs_material_id.budgeted_qty_left * dest_cs_factor_inv)
                                elif line.cs_material_id.uom_id.uom_type == 'smaller':
                                    converted_budget = (line.cs_material_id.budgeted_qty_left / dest_cs_factor)
                                elif line.cs_material_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_material_id.budgeted_qty_left)
                            elif line.product_unit_measure.uom_type == 'bigger':
                                if line.cs_material_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.cs_material_id.budgeted_qty_left * line_factor_inv) / dest_cs_factor_inv)
                                elif line.cs_material_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.cs_material_id.budgeted_qty_left / dest_cs_factor) / line_factor_inv)
                                elif line.cs_material_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_material_id.budgeted_qty_left / line_factor_inv)
                            elif line.product_unit_measure.uom_type == 'smaller':
                                if line.cs_material_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.cs_material_id.budgeted_qty_left * dest_cs_factor_inv) * line_factor)
                                elif line.cs_material_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.cs_material_id.budgeted_qty_left / dest_cs_factor) * line_factor)
                                elif line.cs_material_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_material_id.budgeted_qty_left * line_factor)
                        line.budget_quantity = converted_budget

            if line.material_request_id.type_of_mr == 'labour':
                if line.material_request_id.is_multiple_budget == False:
                    if line.cs_labour_id and line.bd_labour_id:
                        if line.product_unit_measure == line.bd_labour_id.uom_id:
                            converted_budget = line.bd_labour_id.qty_left
                        else:
                            line_factor = line.product_unit_measure.factor
                            line_factor_inv = line.product_unit_measure.factor_inv
                            dest_bd_factor = line.bd_labour_id.uom_id.factor
                            dest_bd_factor_inv = line.bd_labour_id.uom_id.factor_inv
                            if line.product_unit_measure.uom_type == 'reference':
                                if line.bd_labour_id.uom_id.uom_type == 'bigger':
                                    converted_budget = (line.bd_labour_id.qty_left * dest_bd_factor_inv)
                                elif line.bd_labour_id.uom_id.uom_type == 'smaller':
                                    converted_budget = (line.bd_labour_id.qty_left / dest_bd_factor)
                                elif line.bd_labour_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_labour_id.qty_left)
                            elif line.product_unit_measure.uom_type == 'bigger':
                                if line.bd_labour_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.bd_labour_id.qty_left * line_factor_inv) / dest_bd_factor_inv)
                                elif line.bd_labour_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.bd_labour_id.qty_left / dest_bd_factor) / line_factor_inv)
                                elif line.bd_labour_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_labour_id.qty_left / line_factor_inv)
                            elif line.product_unit_measure.uom_type == 'smaller':
                                if line.bd_labour_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.bd_labour_id.qty_left * dest_bd_factor_inv) * line_factor)
                                elif line.bd_labour_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.bd_labour_id.qty_left / dest_bd_factor) * line_factor)
                                elif line.bd_labour_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_labour_id.qty_left * line_factor)
                        line.budget_quantity = converted_budget
                        
                    elif line.cs_labour_id and not line.bd_labour_id:
                        if line.product_unit_measure == line.cs_labour_id.uom_id:
                            converted_budget = line.cs_labour_id.budgeted_qty_left
                        else:
                            line_factor = line.product_unit_measure.factor
                            line_factor_inv = line.product_unit_measure.factor_inv
                            dest_cs_factor = line.cs_labour_id.uom_id.factor
                            dest_cs_factor_inv = line.cs_labour_id.uom_id.factor_inv
                            if line.product_unit_measure.uom_type == 'reference':
                                if line.cs_labour_id.uom_id.uom_type == 'bigger':
                                    converted_budget = (line.cs_labour_id.budgeted_qty_left * dest_cs_factor_inv)
                                elif line.cs_labour_id.uom_id.uom_type == 'smaller':
                                    converted_budget = (line.cs_labour_id.budgeted_qty_left / dest_cs_factor)
                                elif line.cs_labour_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_labour_id.budgeted_qty_left)
                            elif line.product_unit_measure.uom_type == 'bigger':
                                if line.cs_labour_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.cs_labour_id.budgeted_qty_left * line_factor_inv) / dest_cs_factor_inv)
                                elif line.cs_labour_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.cs_labour_id.budgeted_qty_left / dest_cs_factor) / line_factor_inv)
                                elif line.cs_labour_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_labour_id.budgeted_qty_left / line_factor_inv)
                            elif line.product_unit_measure.uom_type == 'smaller':
                                if line.cs_labour_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.cs_labour_id.budgeted_qty_left * dest_cs_factor_inv) * line_factor)
                                elif line.cs_labour_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.cs_labour_id.budgeted_qty_left / dest_cs_factor) * line_factor)
                                elif line.cs_labour_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_labour_id.budgeted_qty_left * line_factor)
                        line.budget_quantity = converted_budget
            
            if line.material_request_id.type_of_mr == 'overhead':
                if line.material_request_id.is_multiple_budget == False:
                    if line.cs_overhead_id and line.bd_overhead_id:
                        if line.product_unit_measure == line.bd_overhead_id.uom_id:
                            converted_budget = line.bd_overhead_id.qty_left
                        else:
                            line_factor = line.product_unit_measure.factor
                            line_factor_inv = line.product_unit_measure.factor_inv
                            dest_bd_factor = line.bd_overhead_id.uom_id.factor
                            dest_bd_factor_inv = line.bd_overhead_id.uom_id.factor_inv
                            if line.product_unit_measure.uom_type == 'reference':
                                if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                                    converted_budget = (line.bd_overhead_id.qty_left * dest_bd_factor_inv)
                                elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                                    converted_budget = (line.bd_overhead_id.qty_left / dest_bd_factor)
                                elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_overhead_id.qty_left)
                            elif line.product_unit_measure.uom_type == 'bigger':
                                if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.bd_overhead_id.qty_left * line_factor_inv) / dest_bd_factor_inv)
                                elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.bd_overhead_id.qty_left / dest_bd_factor) / line_factor_inv)
                                elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_overhead_id.qty_left / line_factor_inv)
                            elif line.product_unit_measure.uom_type == 'smaller':
                                if line.bd_overhead_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.bd_overhead_id.qty_left * dest_bd_factor_inv) * line_factor)
                                elif line.bd_overhead_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.bd_overhead_id.qty_left / dest_bd_factor) * line_factor)
                                elif line.bd_overhead_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.bd_overhead_id.qty_left * line_factor)
                        line.budget_quantity = converted_budget
                        
                    elif line.cs_overhead_id and not line.bd_overhead_id:
                        if line.product_unit_measure == line.cs_overhead_id.uom_id:
                            converted_budget = line.cs_overhead_id.budgeted_qty_left
                        else:
                            line_factor = line.product_unit_measure.factor
                            line_factor_inv = line.product_unit_measure.factor_inv
                            dest_cs_factor = line.cs_overhead_id.uom_id.factor
                            dest_cs_factor_inv = line.cs_overhead_id.uom_id.factor_inv
                            if line.product_unit_measure.uom_type == 'reference':
                                if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                                    converted_budget = (line.cs_overhead_id.budgeted_qty_left * dest_cs_factor_inv)
                                elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                                    converted_budget = (line.cs_overhead_id.budgeted_qty_left / dest_cs_factor)
                                elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_overhead_id.budgeted_qty_left)
                            elif line.product_unit_measure.uom_type == 'bigger':
                                if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.cs_overhead_id.budgeted_qty_left * line_factor_inv) / dest_cs_factor_inv)
                                elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.cs_overhead_id.budgeted_qty_left / dest_cs_factor) / line_factor_inv)
                                elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_overhead_id.budgeted_qty_left / line_factor_inv)
                            elif line.product_unit_measure.uom_type == 'smaller':
                                if line.cs_overhead_id.uom_id.uom_type == 'bigger':
                                    converted_budget = ((line.cs_overhead_id.budgeted_qty_left * dest_cs_factor_inv) * line_factor)
                                elif line.cs_overhead_id.uom_id.uom_type == 'smaller':
                                    converted_budget = ((line.cs_overhead_id.budgeted_qty_left / dest_cs_factor) * line_factor)
                                elif line.cs_overhead_id.uom_id.uom_type == 'reference':
                                    converted_budget = (line.cs_overhead_id.budgeted_qty_left * line_factor)
                        line.budget_quantity = converted_budget

    
    @api.onchange('quantity')
    def _onchange_qty(self):
        for rec in self:
            if rec.material_request_id.budgeting_method == 'product_budget':
                if rec.quantity > rec.budget_quantity:
                    {} #for testing
                    # raise ValidationError(_("The quantity is over the remaining budget"))
            else:
                pass

    @api.onchange('project_scope')
    def _onchange_project_scope(self):
        for rec in self:
            rec.section = False
            rec.variable = False
            rec.group_of_product = False
            rec.product = False
            rec.budget_quantity = 0
    
    @api.onchange('section')
    def _onchange_section(self):
        for rec in self:
            rec.variable = False
            rec.group_of_product = False
            rec.product = False
            rec.budget_quantity = 0

    @api.onchange('group_of_product')
    def _onchange_gop(self):
        for rec in self:
            rec.product = False
            rec.budget_quantity = 0

    def cancel_budget(self, rec, qty):
        for bud in rec.material_request_id.project_budget:
            if rec.bd_material_id:
                for mat in rec.bd_material_id:
                    qty = (mat.qty_res - rec.quantity)
                    bud.budget_material_ids = [(1, rec.bd_material_id.id, {
                            'qty_res': qty,
                        })]
                for cos in rec.material_request_id.job_cost_sheet:
                    qty = (rec.cs_material_id.reserved_qty - rec.quantity)
                    cos.material_ids = [(1, rec.cs_material_id.id, {
                            'reserved_qty': qty,
                        })]
            if rec.bd_labour_id:
                for lab in rec.bd_labour_id:
                    qty = (lab.qty_res - rec.quantity)
                    bud.budget_labour_ids = [(1, rec.bd_labour_id.id, {
                            'qty_res': qty,
                        })]
                for cos in rec.material_request_id.job_cost_sheet:
                    qty = (rec.cs_labour_id.reserved_qty - rec.quantity)
                    cos.material_labour_ids = [(1, rec.cs_labour_id.id, {
                            'reserved_qty': qty,
                        })]
            if rec.bd_overhead_id:
                for ove in rec.bd_overhead_id:
                    qty = (ove.qty_res - rec.quantity)
                    bud.budget_overhead_ids = [(1, rec.bd_overhead_id.id, {
                            'qty_res': qty,
                        })]
                for cos in rec.material_request_id.job_cost_sheet:
                    qty = (rec.cs_overhead_id.reserved_qty - rec.quantity)
                    cos.material_overhead_ids = [(1, rec.cs_overhead_id.id, {
                            'reserved_qty': qty,
                        })]
            if rec.bd_equipment_id:
                for equ in rec.bd_equipment_id:
                    qty = (equ.qty_res - rec.quantity)
                    bud.budget_equipment_ids = [(1, rec.bd_equipment_id.id, {
                            'qty_res': qty,
                        })]
                for cos in rec.material_request_id.job_cost_sheet:
                    qty = (rec.cs_equipment_id.reserved_qty - rec.quantity)
                    cos.material_equipment_ids = [(1, rec.cs_equipment_id.id, {
                            'reserved_qty': qty,
                        })]

    def cancel_cost(self, rec, qty):
        for cos in rec.material_request_id.job_cost_sheet:
            if rec.cs_material_id:
                qty = (rec.cs_material_id.reserved_qty - rec.quantity)
                cos.material_ids = [(1, rec.cs_material_id.id, {
                        'reserved_qty': qty,
                    })]
            if rec.cs_labour_id:
                qty = (rec.cs_labour_id.reserved_qty - rec.quantity)
                cos.material_labour_ids = [(1, rec.cs_labour_id.id, {
                        'reserved_qty': qty,
                    })]
            if rec.cs_overhead_id:
                qty = (rec.cs_overhead_id.reserved_qty - rec.quantity)
                cos.material_overhead_ids = [(1, rec.cs_overhead_id.id, {
                        'reserved_qty': qty,
                    })] 
            if rec.cs_equipment_id:
                qty = (rec.cs_equipment_id.reserved_qty - rec.quantity)
                cos.material_equipment_ids = [(1, rec.cs_equipment_id.id, {
                        'reserved_qty': qty,
                    })]

    def action_cancel_line(self):
        qty = 0.00
        for rec in self:
            if rec.pr_lines_ids:
                if rec.pr_cancelled_qty == rec.pr_lines_ids.qty_cancelled:
                    if rec.material_request_id.project_budget:
                        rec.cancel_budget(rec, qty)
                    else:
                        rec.cancel_cost(rec, qty)
                    self.write({'status_2': 'cancel'})
                else:
                    raise ValidationError(_("Please cancel the product in purchase request created")) 
            else:
                if rec.material_request_id.project_budget:
                    rec.cancel_budget(rec, qty)
                else:
                    rec.cancel_cost(rec, qty)
                self.write({'status_2': 'cancel'})  

    def done_budget(self, rec, gap):
        if rec.bd_material_id:
            rec.cs_material_id.reserved_qty -= gap
            rec.bd_material_id.qty_res -= gap
        if rec.bd_labour_id:
            rec.cs_labour_id.reserved_qty -= gap
            rec.bd_labour_id.qty_res -= gap
        if rec.bd_overhead_id:
            rec.cs_overhead_id.reserved_qty -= gap
            rec.bd_overhead_id.qty_res -= gap
        if rec.bd_equipment_id:
            rec.cs_equipment_id.reserved_qty -= gap
            rec.bd_equipment_id.qty_res -= gap

    def done_cost(self, rec, gap):
        if rec.cs_material_id:
            rec.cs_material_id.reserved_qty -= gap
        if rec.cs_labour_id:
            rec.cs_labour_id.reserved_qty -= gap
        if rec.cs_overhead_id:
            rec.cs_overhead_id.reserved_qty -= gap
        if rec.cs_equipment_id:
            rec.cs_equipment_id.reserved_qty -= gap

    def action_done_line(self):
        for rec in self:
            gap = 0.00
            gap = rec.quantity - rec.done_qty
            if rec.material_request_id.project_budget:
                rec.done_budget(rec, gap)
            else:
                rec.done_cost(rec, gap)   

class ShowMaterialDonePopup(models.TransientModel):
    _inherit = 'show.material.done.popup'

    def force_done_material_request(self):
        material_request_id = self.env['material.request'].browse(self._context.get('active_ids'))
        if material_request_id.budgeting_method == 'product_budget':
            for line in material_request_id.product_line:
                line.action_done_line()
        return super(ShowMaterialDonePopup, self).force_done_material_request()

class MaterialRequestApprovalMatrix(models.Model):
    _inherit = 'mr.approval.matrix'

    project = fields.Many2one(comodel_name = 'project.project', string='Project')
    department = fields.Many2one(comodel_name = 'hr.department', string='Department')
    type_of_mr = fields.Selection([('material','Material'),('labour','Labour'),('assets','Assets'),('overhead','Overhead')],
                                  string = "Type Of MR")
    minimum_amount = fields.Float(string='Minimum Amount')
    maximum_amount = fields.Float(string='Maximum Amount')

    @api.constrains('project', 'department', 'type_of_mr', 'minimum_amount', 'maximum_amount',
                    'branch_id', 'warehouse_id')
    def _constraint_unique(self):
        rec = self.env['mr.approval.matrix'].search([('project', '=', self.project.id),
                                                     ('department', '=', self.department.id),
                                                     ('type_of_mr', '=', self.type_of_mr),
                                                     ('branch_id', '=', self.branch_id.id),
                                                     ('warehouse_id', '=', self.warehouse_id.id)])
        rec_minimum = rec.filtered(lambda r: r.minimum_amount <= self.minimum_amount and r.maximum_amount >= self.minimum_amount)
        rec_maximum = rec.filtered(lambda r: r.minimum_amount <= self.maximum_amount and r.maximum_amount >= self.maximum_amount)
        if len(rec_minimum) > 1 or len(rec_maximum) > 1:
            raise UserError(_("Record Already exist!"))
