import copy
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class JobEstimateExistingQuotation(models.TransientModel):
    _inherit = 'job.estimate.existing.quotation.const'
    _description = 'Existing Quotation For Main Contract'

    manufacture_line = fields.One2many("job.estimate.existing.line.manufacture",  "wiz_id",  string="To Manufacture")
    is_engineering = fields.Boolean(related='job_estimate_id.is_engineering')

    # overrided to add manufacture ref on estimate line
    @api.onchange('job_estimate_id')
    def _onchange_job_estimate_id(self):
        if self.job_estimate_id:
            job = self.job_estimate_id
            scope = []
            self.project_scope_wiz = False
            if job.project_scope_ids:
                for sco in job.project_scope_ids:
                    scope.append((0, 0, {
                        'project_scope': sco.project_scope.id or False,
                        'description': sco.description,
                        'subtotal': sco.subtotal,
                    }))
            
            if len(scope) > 0:
                self.project_scope_wiz = scope
            
            section = []
            self.section_wiz = False
            if job.section_ids:
                for sec in job.section_ids:
                    section.append((0, 0, {
                        'project_scope': sec.project_scope.id or False,
                        'section_name': sec.section_name.id or False,
                        'description': sec.description,
                        'quantity': sec.quantity,
                        'uom_id': sec.uom_id.id or False,
                        'subtotal': sec.subtotal,
                    }))
            
            if len(section) > 0:
                self.section_wiz = section

            variable = []
            self.variable_wiz = False
            if job.variable_ids:
                for var in job.variable_ids:
                    variable.append((0, 0, {
                        'project_scope': var.project_scope.id or False,
                        'section_name': var.section_name.id or False,
                        'variable_name': var.variable_name.id or False,
                        'variable_quantity': var.variable_quantity,
                        'variable_uom': var.variable_uom.id or False,
                        'subtotal': var.subtotal,
                    }))
            
            if len(variable) > 0:
                self.variable_wiz = variable
            
            material_lines = []
            self.material_estimation_wiz = False
            if job.material_estimation_ids:
                for material in job.material_estimation_ids:
                    if len(material.finish_good_id) == 0:
                        material_lines.append((0, 0, {
                            'project_scope': material.project_scope.id or False,
                            'section_name': material.section_name.id or False,
                            'variable_ref': material.variable_ref.id or False,
                            'group_of_product': material.group_of_product.id or False,
                            'product_id': material.product_id.id or False,
                            'description': material.description,
                            'analytic_ids': [(6, 0, material.analytic_idz.ids)] or False,
                            'quantity': material.quantity,
                            'uom_id': material.uom_id.id or False,
                            'unit_price': material.unit_price,
                            'subtotal': material.subtotal,
                        }))
            labour_lines = []
            self.labour_estimation_wiz = False
            if job.labour_estimation_ids:
                for labour in job.labour_estimation_ids:
                    if len(labour.finish_good_id) == 0:
                        labour_lines.append((0, 0, {
                            'project_scope': labour.project_scope.id or False,
                            'section_name': labour.section_name.id or False,
                            'variable_ref': labour.variable_ref.id or False,
                            'group_of_product': labour.group_of_product.id or False,
                            'product_id': labour.product_id.id or False,
                            'description': labour.description,
                            'analytic_ids': [(6, 0, labour.analytic_idz.ids)] or False,
                            'contractors': labour.contractors,
                            'time': labour.time,
                            'quantity': labour.quantity,
                            'uom_id': labour.uom_id.id or False,
                            'unit_price': labour.unit_price,
                            'subtotal': labour.subtotal,
                        }))
            overhead_lines = []
            self.overhead_estimation_wiz = False
            if job.overhead_estimation_ids:
                for overhead in job.overhead_estimation_ids:
                    if len(overhead.finish_good_id) == 0:
                        overhead_lines.append((0, 0, {
                            'project_scope': overhead.project_scope.id or False,
                            'section_name': overhead.section_name.id or False,
                            'overhead_catagory': overhead.overhead_catagory or False,
                            'variable_ref': overhead.variable_ref.id or False,
                            'group_of_product': overhead.group_of_product.id or False,
                            'product_id': overhead.product_id.id or False,
                            'description': overhead.description,
                            'analytic_ids': [(6, 0, overhead.analytic_idz.ids)] or False,
                            'quantity': overhead.quantity,
                            'uom_id': overhead.uom_id.id or False,
                            'unit_price': overhead.unit_price,
                            'subtotal': overhead.subtotal,
                        }))
            asset_lines = []
            self.internal_asset_wiz = False
            if job.internal_asset_ids:
                for asset in job.internal_asset_ids:
                    if len(asset.finish_good_id) == 0:
                        asset_lines.append((0, 0, {
                            'project_scope': asset.project_scope.id or False,
                            'section_name': asset.section_name.id or False,
                            'variable_ref': asset.variable_ref.id or False,
                            'asset_category_id': asset.asset_category_id.id or False,
                            'asset_id': asset.asset_id.id or False,
                            'description': asset.description,
                            'analytic_ids': [(6, 0, asset.analytic_idz.ids)] or False,
                            'quantity': asset.quantity,
                            'uom_id': asset.uom_id.id or False,
                            'unit_price': asset.unit_price,
                            'subtotal': asset.subtotal,
                        }))
            equipment_lines = []     
            self.equipment_estimation_wiz = False   
            if job.equipment_estimation_ids:
                for equipment in job.equipment_estimation_ids:
                    if len(equipment.finish_good_id) == 0:
                        equipment_lines.append((0, 0, {
                            'project_scope': equipment.project_scope.id or False,
                            'section_name': equipment.section_name.id or False,
                            'variable_ref': equipment.variable_ref.id or False,
                            'group_of_product': equipment.group_of_product.id or False,
                            'product_id': equipment.product_id.id or False,
                            'description': equipment.description,
                            'analytic_ids': [(6, 0, equipment.analytic_idz.ids)] or False,
                            'quantity': equipment.quantity,
                            'uom_id': equipment.uom_id.id or False,
                            'unit_price': equipment.unit_price,
                            'subtotal': equipment.subtotal,
                        }))
            subcon_lines = []
            self.subcon_estimation_wiz = False
            if job.subcon_estimation_ids:
                for subcon in job.subcon_estimation_ids:
                    if len(subcon.finish_good_id) == 0:
                        subcon_lines.append((0, 0, {
                            'project_scope': subcon.project_scope.id or False,
                            'section_name': subcon.section_name.id or False,
                            'variable_ref': subcon.variable_ref.id or False,
                            'variable': subcon.variable.id or False,
                            'description': subcon.description,
                            'analytic_ids': [(6, 0, subcon.analytic_idz.ids)] or False,
                            'quantity': subcon.quantity,
                            'uom_id': subcon.uom_id.id or False,
                            'unit_price': subcon.unit_price,
                            'subtotal': subcon.subtotal,
                        }))
                    
            if len(material_lines) > 0:
                self.material_estimation_wiz = material_lines
            if len(labour_lines) > 0:
                self.labour_estimation_wiz = labour_lines
            if len(overhead_lines) > 0:
                self.overhead_estimation_wiz = overhead_lines
            if len(asset_lines) > 0:
                self.internal_asset_wiz = asset_lines
            if len(equipment_lines) > 0:
                self.equipment_estimation_wiz = equipment_lines
            if len(subcon_lines) > 0:
                self.subcon_estimation_wiz = subcon_lines

            if self.is_engineering:
                self.manufacture_line = [(5, 0, 0)]
                for line in self.job_estimate_id.manufacture_line:
                    self.manufacture_line = [(0, 0, {
                        'wiz_id': self.id,
                        'job_estimate_id': self.job_estimate_id.id,
                        'project_scope_id': line.project_scope_id.id,
                        'variable_ref': line.variable_ref.id or False,
                        'section_id': line.section_id.id,
                        'finish_good_id': line.finish_good_id.id,
                        'bom_id': line.bom_id.id,
                        'quantity': line.quantity,
                        'uom_id': line.uom.id,
                        'subtotal': line.subtotal,
                        'onchange_pass': True,
                        'final_finish_good_id': line.final_finish_good_id.id or False,
                        'cascaded': line.cascaded,
                        'is_child': line.is_child,
                        'parent_manuf_line': line.parent_manuf_line.id or False,
                    })]

                    for material in job.material_estimation_ids:
                        if len(material.finish_good_id) > 0:
                            if material.project_scope == line.project_scope_id and material.section_name == line.section_id and material.finish_good_id.id == line.finish_good_id.id:
                                self.material_estimation_wiz = [(0, 0, {
                                    'wiz_id': self.id,
                                    'job_estimate_id': self.job_estimate_id.id,
                                    'project_scope': material.project_scope.id or False,
                                    'section_name': material.section_name.id or False,
                                    'variable_ref': material.variable_ref.id or False,
                                    'final_finish_good_id': material.final_finish_good_id.id or False,
                                    'finish_good_id': material.finish_good_id.id or False,
                                    'bom_id': material.bom_id.id or False,
                                    'product_id': material.product_id.id or False,
                                    'group_of_product': material.group_of_product.id or False,
                                    'description': material.description,
                                    'analytic_ids': [(6, 0, material.analytic_idz.ids)] or False,
                                    'quantity': material.quantity,
                                    'uom_id': material.uom_id.id or False,
                                    'unit_price': material.unit_price,
                                    'subtotal': material.subtotal,
                                })]
                    for labour in job.labour_estimation_ids:
                        if len(labour.finish_good_id) > 0:
                            if labour.project_scope == line.project_scope_id and labour.section_name == line.section_id and labour.finish_good_id.id == line.finish_good_id.id:
                                self.labour_estimation_wiz = [(0, 0, {
                                    'wiz_id': self.id,
                                    'project_scope': labour.project_scope.id or False,
                                    'section_name': labour.section_name.id or False,
                                    'variable_ref': labour.variable_ref.id or False,
                                    'bom_id': labour.bom_id.id or False,
                                    'final_finish_good_id': labour.final_finish_good_id.id or False,
                                    'finish_good_id': labour.finish_good_id.id or False,
                                    'group_of_product': labour.group_of_product.id or False,
                                    'product_id': labour.product_id.id or False,
                                    'description': labour.description,
                                    'analytic_ids': [(6, 0, labour.analytic_idz.ids)] or False,
                                    'contractors': labour.contractors,
                                    'time': labour.time,
                                    'quantity': labour.quantity,
                                    'uom_id': labour.uom_id.id or False,
                                    'unit_price': labour.unit_price,
                                    'subtotal': labour.subtotal,
                                })]
                    for overhead in job.overhead_estimation_ids:
                        if len(overhead.finish_good_id) > 0:
                            if overhead.project_scope == line.project_scope_id and overhead.section_name == line.section_id and overhead.finish_good_id.id == line.finish_good_id.id:
                                self.overhead_estimation_wiz = [(0, 0, {
                                    'wiz_id': self.id,
                                    'job_estimate_id': self.job_estimate_id.id,
                                    'project_scope': overhead.project_scope.id or False,
                                    'section_name': overhead.section_name.id or False,
                                    'bom_id': overhead.bom_id.id or False,
                                    'final_finish_good_id': overhead.final_finish_good_id.id or False,
                                    'finish_good_id': overhead.finish_good_id.id or False,
                                    'overhead_catagory': overhead.overhead_catagory or False,
                                    'group_of_product': overhead.group_of_product.id or False,
                                    'variable_ref': overhead.variable_ref.id or False,
                                    'product_id': overhead.product_id.id or False,
                                    'description': overhead.description,
                                    'analytic_ids': [(6, 0, overhead.analytic_idz.ids)] or False,
                                    'quantity': overhead.quantity,
                                    'uom_id': overhead.uom_id.id or False,
                                    'unit_price': overhead.unit_price,
                                    'subtotal': overhead.subtotal,
                                })]
                    for asset in job.internal_asset_ids:
                        if len(asset.finish_good_id) > 0:
                            if asset.project_scope == line.project_scope_id and asset.section_name == line.section_id and asset.finish_good_id.id == line.finish_good_id.id:
                                self.internal_asset_wiz = [(0, 0, {
                                    'wiz_id': self.id,
                                    'job_estimate_id': self.job_estimate_id.id,
                                    'project_scope': asset.project_scope.id or False,
                                    'section_name': asset.section_name.id or False,
                                    'variable_ref': asset.variable_ref.id or False,
                                    'bom_id': asset.bom_id.id or False,
                                    'final_finish_good_id': asset.final_finish_good_id.id or False,
                                    'finish_good_id': asset.finish_good_id.id or False,
                                    'asset_category_id': asset.asset_category_id.id or False,
                                    'asset_id': asset.asset_id.id or False,
                                    'description': asset.description,
                                    'analytic_ids': [(6, 0, asset.analytic_idz.ids)] or False,
                                    'quantity': asset.quantity,
                                    'uom_id': asset.uom_id.id or False,
                                    'unit_price': asset.unit_price,
                                    'subtotal': asset.subtotal,
                                })]
                    for equipment in job.equipment_estimation_ids:
                        if len(equipment.finish_good_id) > 0:
                            if equipment.project_scope == line.project_scope_id and equipment.section_name == line.section_id and equipment.finish_good_id.id == line.finish_good_id.id:
                                self.equipment_estimation_wiz = [(0, 0, {
                                    'wiz_id': self.id,
                                    'job_estimate_id': self.job_estimate_id.id,
                                    'project_scope': equipment.project_scope.id or False,
                                    'section_name': equipment.section_name.id or False,
                                    'variable_ref': equipment.variable_ref.id or False,
                                    'bom_id': equipment.bom_id.id or False,
                                    'final_finish_good_id': equipment.final_finish_good_id.id or False,
                                    'finish_good_id': equipment.finish_good_id.id or False,
                                    'group_of_product': equipment.group_of_product.id or False,
                                    'product_id': equipment.product_id.id or False,
                                    'description': equipment.description,
                                    'analytic_ids': [(6, 0, equipment.analytic_idz.ids)] or False,
                                    'quantity': equipment.quantity,
                                    'uom_id': equipment.uom_id.id or False,
                                    'unit_price': equipment.unit_price,
                                    'subtotal': equipment.subtotal,
                                })]

                    for subcon in job.subcon_estimation_ids:
                        if len(subcon.finish_good_id) > 0:
                            if subcon.project_scope == line.project_scope_id and subcon.section_name == line.section_id and subcon.finish_good_id.id == line.finish_good_id.id:
                                self.subcon_estimation_wiz = [(0, 0, {
                                    'wiz_id': self.id,
                                    'job_estimate_id': self.job_estimate_id.id,
                                    'project_scope': subcon.project_scope.id or False,
                                    'section_name': subcon.section_name.id or False,
                                    'variable_ref': subcon.variable_ref.id or False,
                                    'bom_id': subcon.bom_id.id or False,
                                    'final_finish_good_id': subcon.final_finish_good_id.id or False,
                                    'finish_good_id': subcon.finish_good_id.id or False,
                                    'variable': subcon.variable.id or False,
                                    'description': subcon.description,
                                    'analytic_ids': [(6, 0, subcon.analytic_idz.ids)] or False,
                                    'quantity': subcon.quantity,
                                    'uom_id': subcon.uom_id.id or False,
                                    'unit_price': subcon.unit_price,
                                    'subtotal': subcon.subtotal,
                                })]

    @api.onchange('project_scope_wiz')
    def _onchange_project_scope_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_project_scope_wiz()
        for scope in self.project_scope_wiz:
            if not scope.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == scope.project_scope.id:
                        manufacture.is_active = False
        return res

    @api.onchange('section_wiz')
    def _onchange_section_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_section_wiz()
        for section in self.section_wiz:
            if not section.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.section_id.id == section.section_name.id:
                        manufacture.is_active = False
        return res

    @api.onchange('variable_wiz')
    def _onchange_variable_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_variable_wiz()
        for variable in self.variable_wiz:
            if not variable.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.variable_ref.id == variable.variable_name.id:
                        manufacture.is_active = False
        return res

    @api.onchange('manufacture_line')
    def _onchange_manufacture_line_hello(self):
        for manufacture in self.manufacture_line:
            if not manufacture.is_active:
                for material in self.material_estimation_wiz:
                    if material.project_scope.id == manufacture.project_scope_id.id \
                        and material.section_name.id == manufacture.section_id.id \
                        and material.finish_good_id.id == manufacture.finish_good_id.id \
                        and material.bom_id.id == manufacture.bom_id.id:
                        material.is_active = False
                for labour in self.labour_estimation_wiz:
                    if labour.project_scope.id == manufacture.project_scope_id.id \
                        and labour.section_name.id == manufacture.section_id.id \
                        and labour.finish_good_id.id == manufacture.finish_good_id.id \
                        and labour.bom_id.id == manufacture.bom_id.id:
                        labour.is_active = False
                for overhead in self.overhead_estimation_wiz:
                    if overhead.project_scope.id == manufacture.project_scope_id.id \
                        and overhead.section_name.id == manufacture.section_id.id \
                        and overhead.finish_good_id.id == manufacture.finish_good_id.id \
                        and overhead.bom_id.id == manufacture.bom_id.id:
                        overhead.is_active = False
                for asset in self.internal_asset_wiz:
                    if asset.project_scope.id == manufacture.project_scope_id.id \
                        and asset.section_name.id == manufacture.section_id.id \
                        and asset.finish_good_id.id == manufacture.finish_good_id.id \
                        and asset.bom_id.id == manufacture.bom_id.id:
                        asset.is_active = False
                for equipment in self.equipment_estimation_wiz:
                    if equipment.project_scope.id == manufacture.project_scope_id.id \
                        and equipment.section_name.id == manufacture.section_id.id \
                        and equipment.finish_good_id.id == manufacture.finish_good_id.id \
                        and equipment.bom_id.id == manufacture.bom_id.id:
                        equipment.is_active = False
                for subcon in self.subcon_estimation_wiz:
                    if subcon.project_scope.id == manufacture.project_scope_id.id \
                        and subcon.section_name.id == manufacture.section_id.id \
                        and subcon.finish_good_id.id == manufacture.finish_good_id.id \
                        and subcon.bom_id.id == manufacture.bom_id.id:
                        subcon.is_active = False
            else:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == manufacture.project_scope_id.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == manufacture.project_scope_id.id \
                        and section.section_name.id == manufacture.section_id.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                for variable in self.variable_wiz:
                    if variable.project_scope.id == manufacture.project_scope_id.id \
                        and variable.section_name.id == manufacture.section_id.id \
                        and variable.variable_name.id == manufacture.variable_ref.id and variable.is_active == False:
                        raise ValidationError(_("Variable '%s' in the variable tab is inactive. You need to activate it first.") % variable.variable_name.name)


    @api.onchange('material_estimation_wiz')
    def _onchange_material_estimation_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_material_estimation_wiz()
        for material in self.material_estimation_wiz:
            if material.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == material.project_scope.id \
                        and manufacture.section_id.id == material.section_name.id \
                        and manufacture.finish_good_id.id == material.finish_good_id.id \
                        and manufacture.bom_id.id == material.bom_id.id and manufacture.is_active == False:
                        raise ValidationError(_("Finish Good '%s' with BOM '%s' in the to manufacture tab is inactive. You need to activate it first.") % (manufacture.finish_good_id.name, manufacture.bom_id.name))
        return res

    @api.onchange('labour_estimation_wiz')
    def _onchange_labour_estimation_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_labour_estimation_wiz()
        for labour in self.labour_estimation_wiz:
            if labour.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == labour.project_scope.id \
                        and manufacture.section_id.id == labour.section_name.id \
                        and manufacture.finish_good_id.id == labour.finish_good_id.id \
                        and manufacture.bom_id.id == labour.bom_id.id and manufacture.is_active == False:
                        raise ValidationError(_("Finish Good '%s' with BOM '%s' in the to manufacture tab is inactive. You need to activate it first.") % (manufacture.finish_good_id.name, manufacture.bom_id.name))
        return res

    @api.onchange('overhead_estimation_wiz')
    def _onchange_overhead_estimation_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_overhead_estimation_wiz()
        for overhead in self.overhead_estimation_wiz:
            if overhead.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == overhead.project_scope.id \
                        and manufacture.section_id.id == overhead.section_name.id \
                        and manufacture.finish_good_id.id == overhead.finish_good_id.id \
                        and manufacture.bom_id.id == overhead.bom_id.id and manufacture.is_active == False:
                        raise ValidationError(_("Finish Good '%s' with BOM '%s' in the to manufacture tab is inactive. You need to activate it first.") % (manufacture.finish_good_id.name, manufacture.bom_id.name))
        return res

    @api.onchange('internal_asset_wiz')
    def _onchange_internal_asset_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_internal_asset_wiz()
        for asset in self.internal_asset_wiz:
            if asset.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == asset.project_scope.id \
                        and manufacture.section_id.id == asset.section_name.id \
                        and manufacture.finish_good_id.id == asset.finish_good_id.id \
                        and manufacture.bom_id.id == asset.bom_id.id and manufacture.is_active == False:
                        raise ValidationError(_("Finish Good '%s' with BOM '%s' in the to manufacture tab is inactive. You need to activate it first.") % (manufacture.finish_good_id.name, manufacture.bom_id.name))
        return res

    @api.onchange('equipment_estimation_wiz')
    def _onchange_equipment_estimation_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_equipment_estimation_wiz()
        for equipment in self.equipment_estimation_wiz:
            if equipment.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == equipment.project_scope.id \
                        and manufacture.section_id.id == equipment.section_name.id \
                        and manufacture.finish_good_id.id == equipment.finish_good_id.id \
                        and manufacture.bom_id.id == equipment.bom_id.id and manufacture.is_active == False:
                        raise ValidationError(_("Finish Good '%s' with BOM '%s' in the to manufacture tab is inactive. You need to activate it first.") % (manufacture.finish_good_id.name, manufacture.bom_id.name))
        return res

    @api.onchange('subcon_estimation_wiz')
    def _onchange_subcon_estimation_wiz(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_subcon_estimation_wiz()
        for subcon in self.subcon_estimation_wiz:
            if subcon.is_active:
                for manufacture in self.manufacture_line:
                    if manufacture.project_scope_id.id == subcon.project_scope.id \
                        and manufacture.section_id.id == subcon.section_name.id \
                        and manufacture.finish_good_id.id == subcon.finish_good_id.id \
                        and manufacture.bom_id.id == subcon.bom_id.id and manufacture.is_active == False:
                        raise ValidationError(_("Finish Good '%s' with BOM '%s' in the to manufacture tab is inactive. You need to activate it first.") % (manufacture.finish_good_id.name, manufacture.bom_id.name))
        return res

    def action_confirm(self):
        ctx = self._context
        for rec in self:
            is_wizard = True
            sale_order_cons = rec.so_cons_id
            project_scope_ids = []
            section_ids = []
            variable_ids = []
            manufacture_line = []                
            material_line_ids = []
            labour_line_ids = []
            overhead_line_ids = []
            internal_asset_line_ids = []
            equipment_line_ids = []
            subcon_line_ids = []

            if rec.is_engineering:
                if rec.project_scope_wiz:
                    for project_scope in rec.project_scope_wiz.filtered(lambda x: x.is_active):
                        project_scope_ids.append(
                            (0, 0,
                            {
                                # "job_estimate_id": project_scope.job_estimate_id.id,
                                "project_scope": project_scope.project_scope.id or False,
                                "description": project_scope.description,
                                "subtotal_scope": project_scope.subtotal,
                            },
                            )
                        )

                if rec.section_wiz:
                    for section in rec.section_wiz.filtered(lambda x: x.is_active):
                        section_ids.append(
                            (0, 0,
                            {
                                # "job_estimate_id": section.job_estimate_id.id,
                                "project_scope": section.project_scope.id or False,
                                "section": section.section_name.id or False,
                                "description": section.description,
                                "quantity": section.quantity,
                                "uom_id": section.uom_id.id or False,
                                "subtotal_section": section.subtotal,
                            },
                            )
                        )

                if rec.variable_wiz:
                    for variable in rec.variable_wiz.filtered(lambda x: x.is_active):
                        variable_ids.append(
                            (0, 0,
                            {
                                # "job_estimate_id": variable.job_estimate_id.id,
                                "project_scope": variable.project_scope.id or False,
                                "section": variable.section_name.id or False,
                                "variable": variable.variable_name.id or False,
                                "quantity": variable.variable_quantity,
                                "uom_id": variable.variable_uom.id or False,
                                "subtotal_variable": variable.subtotal,
                            },
                            )
                        )

                if len(rec.manufacture_line) > 0:
                    for manufacture in rec.manufacture_line.filtered(lambda x: x.is_active):
                        manufacture_line.append((0, 0, {
                            'project_scope': manufacture.project_scope_id.id,
                            'section': manufacture.section_id.id,
                            'variable_ref': manufacture.variable_ref.id,
                            'finish_good_id': manufacture.finish_good_id.id,
                            'bom_id': manufacture.bom_id.id,
                            'quantity': manufacture.quantity,
                            'uom_id': manufacture.uom_id.id,
                            'subtotal_manuf': manufacture.subtotal,
                            'final_finish_good_id': manufacture.final_finish_good_id.id,
                            # 'is_active': manufacture.is_active,
                            # 'is_engineering': manufacture.is_engineering,
                        }))

                if rec.material_estimation_wiz:
                    for material in rec.material_estimation_wiz.filtered(lambda x: x.is_active):
                        material_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": material.project_scope.id or False,
                                "section_name": material.section_name.id or False,
                                "variable_ref": material.variable_ref.id or False,
                                "type": "material",
                                "group_of_product": material.group_of_product.id or False,
                                "material_id": material.product_id.id or False,
                                "finish_good_id": material.finish_good_id.id or False,
                                "bom_id": material.bom_id.id or False,
                                "description": material.description,
                                "analytic_idz": [(6, 0, material.analytic_ids.ids)] or False,
                                "quantity": material.quantity,
                                "uom_id": material.uom_id.id or False,
                                "unit_price": material.unit_price,
                                "subtotal": material.subtotal,
                            },
                            )
                        )

                if rec.labour_estimation_wiz:
                    for labour in rec.labour_estimation_wiz.filtered(lambda x: x.is_active):
                        labour_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": labour.project_scope.id or False,
                                "section_name": labour.section_name.id or False,
                                "variable_ref": labour.variable_ref.id or False,
                                "type": "labour",
                                "group_of_product": labour.group_of_product.id or False,
                                "labour_id": labour.product_id.id or False,
                                "finish_good_id": labour.finish_good_id.id or False,
                                "bom_id": labour.bom_id.id or False,
                                "description": labour.description,
                                "analytic_idz": [(6, 0, labour.analytic_ids.ids)] or False,
                                "contractors": labour.contractors,
                                "time": labour.time,
                                "quantity": labour.quantity,
                                "uom_id": labour.uom_id.id or False,
                                "unit_price": labour.unit_price,
                                "subtotal": labour.subtotal,
                            },
                            )
                        )

                if rec.subcon_estimation_wiz:
                    for subcon in rec.subcon_estimation_wiz.filtered(lambda x: x.is_active):
                        subcon_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": subcon.project_scope.id or False,
                                "section_name": subcon.section_name.id or False,
                                "variable_ref": subcon.variable_ref.id or False,
                                "type": "subcon",
                                "subcon_id": subcon.variable.id or False,
                                "finish_good_id": subcon.finish_good_id.id or False,
                                "bom_id": subcon.bom_id.id or False,
                                "description": subcon.description,
                                "analytic_idz": [(6, 0, subcon.analytic_ids.ids)] or False,
                                "quantity": subcon.quantity,
                                "uom_id": subcon.uom_id.id or False,
                                "unit_price": subcon.unit_price,
                                "subtotal": subcon.subtotal,
                            },
                            )
                        )

                if rec.internal_asset_wiz:
                    for internal_asset in rec.internal_asset_wiz.filtered(lambda x: x.is_active):
                        internal_asset_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": internal_asset.project_scope.id or False,
                                "section_name": internal_asset.section_name.id or False,
                                "variable_ref": internal_asset.variable_ref.id or False,
                                "type": "asset",
                                "asset_category_id": internal_asset.asset_category_id.id or False,
                                "asset_id": internal_asset.asset_id.id or False,
                                "finish_good_id": internal_asset.finish_good_id.id or False,
                                "bom_id": internal_asset.bom_id.id or False,
                                "description": internal_asset.description,
                                "analytic_idz": [(6, 0, internal_asset.analytic_ids.ids)] or False,
                                "quantity": internal_asset.quantity,
                                "uom_id": internal_asset.uom_id.id or False,
                                "unit_price": internal_asset.unit_price,
                                "subtotal": internal_asset.subtotal,
                            },
                            )
                        )

                if rec.equipment_estimation_wiz:
                    for equipment in rec.equipment_estimation_wiz.filtered(lambda x: x.is_active):
                        equipment_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": equipment.project_scope.id or False,
                                "section_name": equipment.section_name.id or False,
                                "variable_ref": equipment.variable_ref.id or False,
                                "type": "equipment",
                                "group_of_product": equipment.group_of_product.id or False,
                                "equipment_id": equipment.product_id.id or False,
                                "finish_good_id": equipment.finish_good_id.id or False,
                                "bom_id": equipment.bom_id.id or False,
                                "description": equipment.description,
                                "analytic_idz": equipment.analytic_ids and [(6, 0, equipment.analytic_ids.ids)] or False,
                                "quantity": equipment.quantity,
                                "uom_id": equipment.uom_id.id or False,
                                "unit_price": equipment.unit_price,
                                "subtotal": equipment.subtotal,
                            },
                            )
                        )

                if rec.overhead_estimation_wiz:
                    for overhead in rec.overhead_estimation_wiz.filtered(lambda x: x.is_active):
                        overhead_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": overhead.project_scope.id or False,
                                "section_name": overhead.section_name.id or False,
                                "variable_ref": overhead.variable_ref.id or False,
                                "type": "overhead",
                                "group_of_product": overhead.group_of_product.id or False,
                                "overhead_id": overhead.product_id.id or False,
                                "finish_good_id": overhead.finish_good_id.id or False,
                                "bom_id": overhead.bom_id.id or False,
                                "description": overhead.description,
                                "analytic_idz": [(6, 0, overhead.analytic_ids.ids)] or False,
                                "quantity": overhead.quantity,
                                "uom_id": overhead.uom_id.id or False,
                                "unit_price": overhead.unit_price,
                                "subtotal": overhead.subtotal,
                                "overhead_catagory": overhead.overhead_catagory,
                            },
                            )
                        )
            else:
                if rec.project_scope_wiz:
                    for project_scope in rec.project_scope_wiz.filtered(lambda x: x.is_active):
                        project_scope_ids.append(
                            (0, 0,
                             {
                                 # "job_estimate_id": project_scope.job_estimate_id.id,
                                 "project_scope": project_scope.project_scope.id or False,
                                 "description": project_scope.description,
                                 "subtotal_scope": project_scope.subtotal,
                             },
                             )
                        )

                if rec.section_wiz:
                    for section in rec.section_wiz.filtered(lambda x: x.is_active):
                        section_ids.append(
                            (0, 0,
                             {
                                 # "job_estimate_id": section.job_estimate_id.id,
                                 "project_scope": section.project_scope.id or False,
                                 "section": section.section_name.id or False,
                                 "description": section.description,
                                 "quantity": section.quantity,
                                 "uom_id": section.uom_id.id or False,
                                 "subtotal_section": section.subtotal,
                             },
                             )
                        )

                if rec.variable_wiz:
                    for variable in rec.variable_wiz.filtered(lambda x: x.is_active):
                        variable_ids.append(
                            (0, 0,
                             {
                                 # "job_estimate_id": variable.job_estimate_id.id,
                                 "project_scope": variable.project_scope.id or False,
                                 "section": variable.section_name.id or False,
                                 "variable": variable.variable_name.id or False,
                                 "quantity": variable.variable_quantity,
                                 "uom_id": variable.variable_uom.id or False,
                                 "subtotal_variable": variable.subtotal,
                             },
                             )
                        )
                if rec.material_estimation_wiz:
                    for material in rec.material_estimation_wiz.filtered(lambda x: x.is_active):
                        material_line_ids.append(
                            (0, 0,
                             {
                                 "project_scope": material.project_scope.id or False,
                                 "section_name": material.section_name.id or False,
                                 "variable_ref": material.variable_ref.id or False,
                                 "type": "material",
                                 "group_of_product": material.group_of_product.id or False,
                                 "material_id": material.product_id.id or False,
                                 "description": material.description,
                                 "analytic_idz": [(6, 0, material.analytic_ids.ids)] or False,
                                 "quantity": material.quantity,
                                 "uom_id": material.uom_id.id or False,
                                 "unit_price": material.unit_price,
                                 "subtotal": material.subtotal,
                             },
                             )
                        )

                if rec.labour_estimation_wiz:
                    for labour in rec.labour_estimation_wiz.filtered(lambda x: x.is_active):
                        labour_line_ids.append(
                            (0, 0,
                             {
                                 "project_scope": labour.project_scope.id or False,
                                 "section_name": labour.section_name.id or False,
                                 "variable_ref": labour.variable_ref.id or False,
                                 "type": "labour",
                                 "group_of_product": labour.group_of_product.id or False,
                                 "labour_id": labour.product_id.id or False,
                                 "description": labour.description,
                                 "analytic_idz": [(6, 0, labour.analytic_ids.ids)] or False,
                                 "contractors": labour.contractors,
                                 "time": labour.time,
                                 "quantity": labour.quantity,
                                 "uom_id": labour.uom_id.id or False,
                                 "unit_price": labour.unit_price,
                                 "subtotal": labour.subtotal,
                             },
                             )
                        )

                if rec.subcon_estimation_wiz:
                    for subcon in rec.subcon_estimation_wiz.filtered(lambda x: x.is_active):
                        subcon_line_ids.append(
                            (0, 0,
                             {
                                 "project_scope": subcon.project_scope.id or False,
                                 "section_name": subcon.section_name.id or False,
                                 "variable_ref": subcon.variable_ref.id or False,
                                 "type": "subcon",
                                 "subcon_id": subcon.variable.id or False,
                                 "description": subcon.description,
                                 "analytic_idz": [(6, 0, subcon.analytic_ids.ids)] or False,
                                 "quantity": subcon.quantity,
                                 "uom_id": subcon.uom_id.id or False,
                                 "unit_price": subcon.unit_price,
                                 "subtotal": subcon.subtotal,
                             },
                             )
                        )

                if rec.internal_asset_wiz:
                    for internal_asset in rec.internal_asset_wiz.filtered(lambda x: x.is_active):
                        internal_asset_line_ids.append(
                            (0, 0,
                             {
                                 "project_scope": internal_asset.project_scope.id or False,
                                 "section_name": internal_asset.section_name.id or False,
                                 "variable_ref": internal_asset.variable_ref.id or False,
                                 "type": "asset",
                                 "asset_category_id": internal_asset.asset_category_id.id or False,
                                 "asset_id": internal_asset.asset_id.id or False,
                                 "description": internal_asset.description,
                                 "analytic_idz": [(6, 0, internal_asset.analytic_ids.ids)] or False,
                                 "quantity": internal_asset.quantity,
                                 "uom_id": internal_asset.uom_id.id or False,
                                 "unit_price": internal_asset.unit_price,
                                 "subtotal": internal_asset.subtotal,
                             },
                             )
                        )

                if rec.equipment_estimation_wiz:
                    for equipment in rec.equipment_estimation_wiz.filtered(lambda x: x.is_active):
                        equipment_line_ids.append(
                            (0, 0,
                             {
                                 "project_scope": equipment.project_scope.id or False,
                                 "section_name": equipment.section_name.id or False,
                                 "variable_ref": equipment.variable_ref.id or False,
                                 "type": "equipment",
                                 "group_of_product": equipment.group_of_product.id or False,
                                 "equipment_id": equipment.product_id.id or False,
                                 "description": equipment.description,
                                 "analytic_idz": equipment.analytic_ids and [
                                     (6, 0, equipment.analytic_ids.ids)] or False,
                                 "quantity": equipment.quantity,
                                 "uom_id": equipment.uom_id.id or False,
                                 "unit_price": equipment.unit_price,
                                 "subtotal": equipment.subtotal,
                             },
                             )
                        )

                if rec.overhead_estimation_wiz:
                    for overhead in rec.overhead_estimation_wiz.filtered(lambda x: x.is_active):
                        overhead_line_ids.append(
                            (0, 0,
                             {
                                 "project_scope": overhead.project_scope.id or False,
                                 "section_name": overhead.section_name.id or False,
                                 "variable_ref": overhead.variable_ref.id or False,
                                 "type": "overhead",
                                 "group_of_product": overhead.group_of_product.id or False,
                                 "overhead_id": overhead.product_id.id or False,
                                 "description": overhead.description,
                                 "analytic_idz": [(6, 0, overhead.analytic_ids.ids)] or False,
                                 "quantity": overhead.quantity,
                                 "uom_id": overhead.uom_id.id or False,
                                 "unit_price": overhead.unit_price,
                                 "subtotal": overhead.subtotal,
                                 "overhead_catagory": overhead.overhead_catagory,
                             },
                             )
                        )

            if sale_order_cons:
                if rec.is_engineering:
                    project_scope_copy = copy.deepcopy(project_scope_ids)
                    for i in project_scope_copy:
                        target = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        i[2]['project_scope'] = target.name
                    section_copy = copy.deepcopy(section_ids)
                    for i in section_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section'] = target_section.name
                    variable_copy = copy.deepcopy(variable_ids)
                    for i in variable_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section'] = target_section.name
                        i[2]['variable'] = target_variable.name
                    manufacture_copy = copy.deepcopy(manufacture_line)
                    for i in manufacture_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        target_final_finish_good = self.env['product.product'].search([('id', '=', i[2]['final_finish_good_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                        i[2]['final_finish_good_id'] = target_final_finish_good.name
                    material_copy = copy.deepcopy(material_line_ids)
                    for i in material_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                    labour_copy = copy.deepcopy(labour_line_ids)
                    for i in labour_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                    overhead_copy = copy.deepcopy(overhead_line_ids)
                    for i in overhead_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                    internal_copy = copy.deepcopy(internal_asset_line_ids)
                    for i in internal_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                    equipment_copy = copy.deepcopy(equipment_line_ids)
                    for i in equipment_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                    subcon_copy = copy.deepcopy(subcon_line_ids)
                    for i in subcon_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        target_finish_good = self.env['product.product'].search([('id', '=', i[2]['finish_good_id'])])
                        target_bom = self.env['mrp.bom'].search([('id', '=', i[2]['bom_id'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                        i[2]['finish_good_id'] = target_finish_good.name
                        i[2]['bom_id'] = target_bom.name
                    scope_values = list(map(lambda x: (x[2].pop('subtotal_scope'), x[2])[1], project_scope_copy))
                    section_values = list(map(lambda x: (x[2].pop('subtotal_section'), x[2].pop('quantity'), x[2])[-1], section_copy))
                    variable_values = list(map(lambda x: (x[2].pop('subtotal_variable'), x[2].pop('quantity'), x[2])[-1], variable_copy))
                    manufacture_values = list(map(lambda x: (x[2].pop('subtotal_manuf'), x[2].pop('quantity'), x[2])[-1], manufacture_copy))
                    material_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], material_copy))
                    labour_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'),x[2].pop('contractors'), x[2].pop('time'), x[2])[-1], labour_copy))
                    overhead_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], overhead_copy))
                    internal_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], internal_copy))
                    equipment_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], equipment_copy))
                    subcon_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], subcon_copy))

                else:
                    project_scope_copy = copy.deepcopy(project_scope_ids)
                    for i in project_scope_copy:
                        target = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        i[2]['project_scope'] = target.name
                    section_copy = copy.deepcopy(section_ids)
                    for i in section_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section'] = target_section.name
                    variable_copy = copy.deepcopy(variable_ids)
                    for i in variable_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section'] = target_section.name
                        i[2]['variable'] = target_variable.name
                    material_copy = copy.deepcopy(material_line_ids)
                    for i in material_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                    labour_copy = copy.deepcopy(labour_line_ids)
                    for i in labour_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                    overhead_copy = copy.deepcopy(overhead_line_ids)
                    for i in overhead_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                    internal_copy = copy.deepcopy(internal_asset_line_ids)
                    for i in internal_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                    equipment_copy = copy.deepcopy(equipment_line_ids)
                    for i in equipment_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                    subcon_copy = copy.deepcopy(subcon_line_ids)
                    for i in subcon_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        i[2]['variable_ref'] = target_variable.name
                    scope_values = list(map(lambda x: (x[2].pop('subtotal_scope'), x[2])[1], project_scope_copy))
                    section_values = list(
                        map(lambda x: (x[2].pop('subtotal_section'), x[2].pop('quantity'), x[2])[-1], section_copy))
                    variable_values = list(
                        map(lambda x: (x[2].pop('subtotal_variable'), x[2].pop('quantity'), x[2])[-1], variable_copy))
                    material_values = list(
                        map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1],
                            material_copy))
                    labour_values = list(
                        map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'),
                                       x[2].pop('contractors'), x[2].pop('time'), x[2])[-1], labour_copy))
                    overhead_values = list(
                        map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1],
                            overhead_copy))
                    internal_values = list(
                        map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1],
                            internal_copy))
                    equipment_values = list(
                        map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1],
                            equipment_copy))
                    subcon_values = list(
                        map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1],
                            subcon_copy))

                if not ctx.get('create_new'):
                    exist_scope_idx = []
                    for scope in sale_order_cons.project_scope_ids:
                        value = {
                            "project_scope": scope.project_scope.name,
                            "description": scope.description
                        }
                        for i in range(len(scope_values)):
                            if value == scope_values[i]:
                                scope.subtotal_scope += project_scope_ids[i][2]['subtotal_scope']
                                if i not in exist_scope_idx:
                                    exist_scope_idx.append(i)
                    exist_scope_idx.sort(reverse=True)
                    for j in exist_scope_idx:
                        del project_scope_ids[j]

                    exist_sect_idx = []
                    for sect in sale_order_cons.section_ids:
                        value = {
                            "project_scope": sect.project_scope.name,
                            "section": sect.section.name,
                            "description": sect.description,
                            "uom_id": sect.uom_id.id
                        }
                        for i in range(len(section_values)):
                            if value == section_values[i]:
                                sect.subtotal_section += section_ids[i][2]['subtotal_section']
                                sect.quantity += section_ids[i][2]['quantity']
                                if i not in exist_sect_idx:
                                    exist_sect_idx.append(i)
                    exist_sect_idx.sort(reverse=True)
                    for j in exist_sect_idx:
                        del section_ids[j]
                    
                    exist_var_idx = []
                    for var in sale_order_cons.variable_ids:
                        value = {
                            "project_scope": var.project_scope.name,
                            "section": var.section.name,
                            "variable": var.variable.name,
                            "uom_id": var.uom_id.id
                        }
                        for i in range(len(variable_values)):
                            if value == variable_values[i]:
                                var.subtotal_variable += variable_ids[i][2]['subtotal_variable']
                                var.quantity += variable_ids[i][2]['quantity']
                                if i not in exist_var_idx:
                                    exist_var_idx.append(i)
                    exist_var_idx.sort(reverse=True)
                    for j in exist_var_idx:
                        del variable_ids[j]
                    
                    exist_manuf_idx = []
                    for manuf in sale_order_cons.manufacture_line:
                        value= {
                            "project_scope": manuf.project_scope.name,
                            "section": manuf.section.name,
                            "variable_ref": manuf.variable_ref.name,
                            "finish_good_id": manuf.finish_good_id.name,
                            "bom_id": manuf.bom_id.name,
                            "uom_id": manuf.uom_id.id,
                            "final_finish_good_id": manuf.final_finish_good_id.id,
                        }
                        for i in range(len(manufacture_values)):
                            if value == manufacture_values[i]:
                                manuf.subtotal_manuf += manufacture_line[i][2]['subtotal_manuf']
                                manuf.quantity += manufacture_line[i][2]['quantity']
                                if i not in exist_manuf_idx:
                                    exist_manuf_idx.append(i)
                        exist_manuf_idx.sort(reverse=True)
                        for j in exist_manuf_idx:
                            del manufacture_line[j]
                        
                    exist_mat_idx = []
                    for mat in sale_order_cons.material_line_ids:
                        if rec.is_engineering == False:
                            value = {
                                "project_scope": mat.project_scope.name,
                                "section_name": mat.section_name.name,
                                "variable_ref": mat.variable_ref.name,
                                "type": "material",
                                "group_of_product": mat.group_of_product.id,
                                "material_id": mat.material_id.id,
                                "description": mat.description,
                                "uom_id": mat.uom_id.id,
                                "unit_price": mat.unit_price,
                            }
                        else:
                             value = {
                                "project_scope": mat.project_scope.name,
                                "section_name": mat.section_name.name,
                                "variable_ref": mat.variable_ref.name,
                                "type": "material",
                                "group_of_product": mat.group_of_product.id,
                                "finish_good_id": mat.finish_good_id.name,
                                "bom_id": mat.bom_id.name,
                                "material_id": mat.material_id.id,
                                "description": mat.description,
                                "uom_id": mat.uom_id.id,
                                "unit_price": mat.unit_price,
                            }

                        for i in range(len(material_values)):
                            if value == material_values[i]:
                                if value['unit_price'] > material_line_ids[i][2]['unit_price']:
                                    material_line_ids[i][2]['unit_price'] = value['unit_price']

                                mat.subtotal += material_line_ids[i][2]['subtotal'] 
                                mat.quantity += material_line_ids[i][2]['quantity']
                                if i not in exist_mat_idx:
                                    exist_mat_idx.append(i)
                    exist_mat_idx.sort(reverse=True)
                    for j in exist_mat_idx:
                        del material_line_ids[j]
                    
                    exist_lab_idx = []
                    for lab in sale_order_cons.labour_line_ids:
                        if rec.is_engineering == False:
                            value = {
                                "project_scope": lab.project_scope.name,
                                "section_name": lab.section_name.name,
                                "variable_ref": lab.variable_ref.name,
                                "type": "labour",
                                "group_of_product": lab.group_of_product.id,
                                "labour_id": lab.labour_id.id,
                                "description": lab.description,
                                "uom_id": lab.uom_id.id,
                                "unit_price": labour.unit_price
                            }
                        else:
                            value = {
                                "project_scope": lab.project_scope.name,
                                "section_name": lab.section_name.name,
                                "variable_ref": lab.variable_ref.name,
                                "type": "labour",
                                "group_of_product": lab.group_of_product.id,
                                "labour_id": lab.labour_id.id,
                                "finish_good_id": lab.finish_good_id.name,
                                "bom_id": lab.bom_id.name,
                                "description": lab.description,
                                "uom_id": lab.uom_id.id,
                                "unit_price": labour.unit_price
                            }

                        for i in range(len(labour_values)):
                            if value == labour_values[i]:
                                if value['unit_price'] > labour_line_ids[i][2]['unit_price']:
                                    labour_line_ids[i][2]['unit_price'] = value['unit_price']

                                lab.subtotal += labour_line_ids[i][2]['subtotal'] 
                                lab.quantity += labour_line_ids[i][2]['quantity']
                                lab.contractors += labour_line_ids[i][2]['contractors'] 
                                lab.time += labour_line_ids[i][2]['time']
                                if i not in exist_lab_idx:
                                    exist_lab_idx.append(i)
                    exist_lab_idx.sort(reverse=True)
                    for j in exist_lab_idx:
                        del labour_line_ids[j]

                    exist_ov_idx = [] 
                    for ov in sale_order_cons.overhead_line_ids:
                        if rec.is_engineering == False:
                            value = {
                                "project_scope": ov.project_scope.name,
                                "section_name": ov.section_name.name,
                                "variable_ref": ov.variable_ref.name,
                                "type": "overhead",
                                "group_of_product": ov.group_of_product.id,
                                "overhead_id": ov.overhead_id.id,
                                "description": ov.description,
                                "uom_id": ov.uom_id.id,
                                "unit_price": ov.unit_price,
                                "overhead_catagory": ov.overhead_catagory,
                            }
                        else:
                            value = {
                                "project_scope": ov.project_scope.name,
                                "section_name": ov.section_name.name,
                                "variable_ref": ov.variable_ref.name,
                                "type": "overhead",
                                "group_of_product": ov.group_of_product.id,
                                "overhead_id": ov.overhead_id.id,
                                "finish_good_id": ov.finish_good_id.name,
                                "bom_id": ov.bom_id.name,
                                "description": ov.description,
                                "uom_id": ov.uom_id.id,
                                "unit_price": ov.unit_price,
                                "overhead_catagory": ov.overhead_catagory,
                            }

                        for i in range(len(overhead_values)):
                            if value == overhead_values[i]:
                                if value['unit_price'] > overhead_line_ids[i][2]['unit_price']:
                                    overhead_line_ids[i][2]['unit_price'] = value['unit_price']

                                ov.subtotal += overhead_line_ids[i][2]['subtotal']
                                ov.quantity += overhead_line_ids[i][2]['quantity']
                                if i not in exist_ov_idx:
                                    exist_ov_idx.append(i)
                    exist_ov_idx.sort(reverse=True)
                    for j in exist_ov_idx:
                        del overhead_line_ids[j]

                    exist_asset_idx = []
                    for asset in sale_order_cons.internal_asset_line_ids:
                        if rec.is_engineering == False:
                            value = {
                                "project_scope": asset.project_scope.name,
                                "section_name": asset.section_name.name,
                                "variable_ref": asset.variable_ref.name,
                                "type": "asset",
                                "asset_category_id": asset.asset_category_id.id,
                                "asset_id": asset.asset_id.id,
                                "description": asset.description,
                                "uom_id": asset.uom_id.id,
                                "unit_price": asset.unit_price
                            }
                        else:
                            value = {
                                "project_scope": asset.project_scope.name,
                                "section_name": asset.section_name.name,
                                "variable_ref": asset.variable_ref.name,
                                "type": "asset",
                                "asset_category_id": asset.asset_category_id.id,
                                "asset_id": asset.asset_id.id,
                                "finish_good_id": asset.finish_good_id.name,
                                "bom_id": asset.bom_id.name,
                                "description": asset.description,
                                "uom_id": asset.uom_id.id,
                                "unit_price": asset.unit_price
                            }

                        for i in range(len(internal_values)):
                            if value == internal_values[i]:
                                if value['unit_price'] > internal_asset_line_ids[i][2]['unit_price']:
                                    internal_asset_line_ids[i][2]['unit_price'] = value['unit_price']

                                asset.subtotal += internal_asset_line_ids[i][2]['subtotal'] 
                                asset.quantity += internal_asset_line_ids[i][2]['quantity']
                                if i not in exist_asset_idx:
                                    exist_asset_idx.append(i)
                    exist_asset_idx.sort(reverse=True)
                    for j in exist_asset_idx:
                        del internal_asset_line_ids[j]

                    exist_eq_idx = []    
                    for eq in sale_order_cons.equipment_line_ids:
                        if rec.is_engineering == False:
                            value = {
                                "project_scope": eq.project_scope.name,
                                "section_name": eq.section_name.name,
                                "variable_ref": eq.variable_ref.name,
                                "type": "equipment",
                                "group_of_product": eq.group_of_product.id,
                                "equipment_id": eq.equipment_id.id,
                                "description": eq.description,
                                "uom_id": eq.uom_id.id,
                                "unit_price": eq.unit_price
                            }
                        else:
                            value = {
                                "project_scope": eq.project_scope.name,
                                "section_name": eq.section_name.name,
                                "variable_ref": eq.variable_ref.name,
                                "type": "equipment",
                                "group_of_product": eq.group_of_product.id,
                                "equipment_id": eq.equipment_id.id,
                                "finish_good_id": eq.finish_good_id.name,
                                "bom_id": eq.bom_id.name,
                                "description": eq.description,
                                "uom_id": eq.uom_id.id,
                                "unit_price": eq.unit_price
                            }

                        for i in range(len(equipment_values)):
                            if value == equipment_values[i]:
                                if value['unit_price'] > equipment_line_ids[i][2]['unit_price']:
                                    equipment_line_ids[i][2]['unit_price'] = value['unit_price']

                                eq.subtotal += equipment_line_ids[i][2]['subtotal'] 
                                eq.quantity += equipment_line_ids[i][2]['quantity']
                                if i not in exist_eq_idx:
                                    exist_eq_idx.append(i)
                    exist_eq_idx.sort(reverse=True)
                    for j in exist_eq_idx:
                        del equipment_line_ids[j]
                    
                    exist_sub_idx = []
                    for sub in sale_order_cons.subcon_line_ids:
                        if rec.is_engineering == False:
                            value = {
                                "project_scope": sub.project_scope.name,
                                "section_name": sub.section_name.name,
                                "variable_ref": sub.variable_ref.name,
                                "type": "subcon",
                                "subcon_id": sub.subcon_id.id,
                                "description": sub.description,
                                "uom_id": sub.uom_id.id,
                                "unit_price": sub.unit_price,
                            }
                        else:
                            value = {
                                "project_scope": sub.project_scope.name,
                                "section_name": sub.section_name.name,
                                "variable_ref": sub.variable_ref.name,
                                "type": "subcon",
                                "subcon_id": sub.subcon_id.id,
                                "finish_good_id": sub.finish_good_id.name,
                                "bom_id": sub.bom_id.name,
                                "description": sub.description,
                                "uom_id": sub.uom_id.id,
                                "unit_price": sub.unit_price,
                            }

                        for i in range(len(subcon_values)):
                            if value == subcon_values[i]:
                                if value['unit_price'] > subcon_line_ids[i][2]['unit_price']:
                                    subcon_line_ids[i][2]['unit_price'] = value['unit_price']
                                    
                                sub.subtotal += subcon_line_ids[i][2]['subtotal']
                                sub.quantity += subcon_line_ids[i][2]['quantity']
                                if i not in exist_sub_idx:
                                    exist_sub_idx.append(i)
                    exist_sub_idx.sort(reverse=True)
                    for j in exist_sub_idx:
                        del subcon_line_ids[j]

                    if project_scope_ids:
                        sale_order_cons.project_scope_ids = project_scope_ids
                    if section_ids:
                        sale_order_cons.section_ids = section_ids
                    if variable_ids:
                        sale_order_cons.variable_ids = variable_ids
                    if manufacture_line:
                        sale_order_cons.manufacture_line = manufacture_line
                    if material_line_ids:
                        sale_order_cons.material_line_ids = material_line_ids
                    if labour_line_ids:
                        sale_order_cons.labour_line_ids = labour_line_ids
                    if overhead_line_ids:
                        sale_order_cons.overhead_line_ids = overhead_line_ids
                    if internal_asset_line_ids:
                        sale_order_cons.internal_asset_line_ids = internal_asset_line_ids
                    if equipment_line_ids:
                        sale_order_cons.equipment_line_ids = equipment_line_ids
                    if subcon_line_ids:
                        sale_order_cons.subcon_line_ids = subcon_line_ids
                    # sale_order_cons.job_reference = [(4, rec.job_estimate_id.id)]
                    sale_order_cons.job_references = [(4, rec.job_estimate_id.id)]
                    if sale_order_cons.is_wizard:
                        sale_order_cons.job_count += 1
                    for job in rec.job_estimate_id:
                        job.write({
                            'state': 'done',
                            'sale_state': 'quotation',
                            'quotation_id': [(4, sale_order_cons.id)]
                        })
                    context = ({'is_wizard': is_wizard})
                else:
                    if rec.is_engineering:
                        inexist_scope = []
                        for scope in sale_order_cons.project_scope_ids:
                            value = {
                                "project_scope": scope.project_scope.name,
                                "description": scope.description
                            }
                            if value not in scope_values:
                                inexist_scope.append((0, 0,
                                {
                                    # "job_estimate_id": project_scope.job_estimate_id.id,
                                    "project_scope": scope.project_scope.id or False,
                                    "description": scope.description,
                                    "subtotal_scope": scope.subtotal_scope,
                                }))
                            else:
                                i = scope_values.index(value)
                                project_scope_ids[i][2]['subtotal_scope'] += scope.subtotal_scope
                        project_scope_ids.extend(inexist_scope)

                        inexist_section = []
                        for sect in sale_order_cons.section_ids:
                            value = {
                                "project_scope": sect.project_scope.name,
                                "section": sect.section.name,
                                "description": sect.description,
                                "uom_id": sect.uom_id.id
                            }
                            if value not in section_values:
                                inexist_section.append((0, 0,
                                {
                                    "project_scope": sect.project_scope.id or False,
                                    "section": sect.section.id or False,
                                    "description": sect.description,
                                    "quantity": sect.quantity,
                                    "uom_id": sect.uom_id.id or False,
                                    "subtotal_section": sect.subtotal_section,
                                }))
                            else:
                                i = section_values.index(value)
                                section_ids[i][2]['subtotal_section'] += sect.subtotal_section
                                section_ids[i][2]['quantity'] += sect.quantity
                        section_ids.extend(inexist_section)

                        inexist_variable = []
                        for var in sale_order_cons.variable_ids:
                            value = {
                                "project_scope": var.project_scope.name,
                                "section": var.section.name,
                                "variable": var.variable.name,
                                "uom_id": var.uom_id.id
                            }
                            if value not in variable_values:
                                inexist_variable.append((0, 0,
                                {
                                    # "job_estimate_id": variable.job_estimate_id.id,
                                    "project_scope": var.project_scope.id or False,
                                    "section": var.section.id or False,
                                    "variable": var.variable.id or False,
                                    "quantity": var.quantity,
                                    "uom_id": var.uom_id.id or False,
                                    "subtotal_variable": var.subtotal_variable,
                                }))
                            else:
                                i = variable_values.index(value)
                                variable_ids[i][2]['subtotal_variable'] += var.subtotal_variable
                                variable_ids[i][2]['quantity'] += var.quantity
                        variable_ids.extend(inexist_variable)

                        inexist_manuf = []
                        for manuf in sale_order_cons.manufacture_line:
                            value = {
                                "project_scope": manuf.project_scope.name,
                                "section": manuf.section.name,
                                "variable_ref": manuf.variable_ref.name,
                                "finish_good_id": manuf.finish_good_id.name,
                                "bom_id": manuf.bom_id.name,
                                "uom_id": manuf.uom_id.id,
                                "final_finish_good_id": manuf.final_finish_good_id.name,
                            }
                            if value not in manufacture_values:
                                inexist_manuf.append((0, 0,
                                {
                                    # "job_estimate_id": variable.job_estimate_id.id,
                                    "project_scope": manuf.project_scope.id or False,
                                    "section": manuf.section.id or False,
                                    "variable_ref": manuf.variable.id or False,
                                    "final_finish_good_id": manuf.final_finish_good_id.id or False,
                                    "finish_good_id": manuf.finish_good_id.id or False,
                                    "bom_id": manuf.bom_id.id or False,
                                    "quantity": manuf.quantity,
                                    "uom_id": manuf.uom_id.id or False,
                                    "subtotal_manuf": manuf.subtotal,
                                }))
                            else:
                                i = manufacture_values.index(value)
                                manufacture_line[i][2]['subtotal_manuf'] += manuf.subtotal_manuf
                                manufacture_line[i][2]['quantity'] += manuf.quantity
                        manufacture_line.extend(inexist_manuf)

                        inexist_material = []
                        for mat in sale_order_cons.material_line_ids:
                            if rec.is_engineering == False:
                                value = {
                                    "project_scope": mat.project_scope.name,
                                    "section_name": mat.section_name.name,
                                    "variable_ref": mat.variable_ref.name,
                                    "type": "material",
                                    "group_of_product": mat.group_of_product.id,
                                    "material_id": mat.material_id.id,
                                    "description": mat.description,
                                    "uom_id": mat.uom_id.id,
                                    "unit_price": mat.unit_price,
                                }
                            else:
                                 value = {
                                    "project_scope": mat.project_scope.name,
                                    "section_name": mat.section_name.name,
                                    "variable_ref": mat.variable_ref.name,
                                    "type": "material",
                                    "group_of_product": mat.group_of_product.id,
                                    "material_id": mat.material_id.id,
                                    "finish_good_id": mat.finish_good_id.name,
                                    "bom_id": mat.bom_id.name,
                                    "description": mat.description,
                                    "uom_id": mat.uom_id.id,
                                    "unit_price": mat.unit_price,
                                }

                            if value not in material_values:
                                inexist_material.append((0, 0,
                                {
                                    "project_scope": mat.project_scope.id or False,
                                    "section_name": mat.section_name.id or False,
                                    "variable_ref": mat.variable_ref.id or False,
                                    "type": "material",
                                    "group_of_product": mat.group_of_product.id or False,
                                    "material_id": mat.material_id.id or False,
                                    "finish_good_id": mat.finish_good_id.id or False,
                                    "bom_id": mat.bom_id.id or False,
                                    "description": mat.description,
                                    "analytic_idz": [(6, 0, mat.analytic_idz.ids)] or False,
                                    "quantity": mat.quantity,
                                    "uom_id": mat.uom_id.id or False,
                                    "unit_price": mat.unit_price,
                                    "subtotal": mat.subtotal,
                                }))
                            else:
                                i = material_values.index(value)
                                material_line_ids[i][2]['subtotal'] += mat.subtotal
                        material_line_ids.extend(inexist_material)

                        inexist_labour = []
                        for lab in sale_order_cons.labour_line_ids:
                            if rec.is_engineering == False:
                                value = {
                                    "project_scope": lab.project_scope.name,
                                    "section_name": lab.section_name.name,
                                    "variable_ref": lab.variable_ref.name,
                                    "type": "labour",
                                    "group_of_product": lab.group_of_product.id,
                                    "labour_id": lab.labour_id.id,
                                    "description": lab.description,
                                    "uom_id": lab.uom_id.id,
                                    "unit_price": labour.unit_price
                                }
                            else:
                                 value = {
                                    "project_scope": lab.project_scope.name,
                                    "section_name": lab.section_name.name,
                                    "variable_ref": lab.variable_ref.name,
                                    "type": "labour",
                                    "group_of_product": lab.group_of_product.id,
                                    "labour_id": lab.labour_id.id,
                                    "finish_good_id": lab.finish_good_id.name,
                                    "bom_id": lab.bom_id.name,
                                    "description": lab.description,
                                    "uom_id": lab.uom_id.id,
                                    "unit_price": labour.unit_price
                                }

                            if value not in labour_values:
                                inexist_labour.append((0, 0,
                                {
                                    "project_scope": lab.project_scope.id or False,
                                    "section_name": lab.section_name.id or False,
                                    "variable_ref": lab.variable_ref.id or False,
                                    "type": "labour",
                                    "group_of_product": lab.group_of_product.id or False,
                                    "labour_id": lab.labour_id.id or False,
                                    "finish_good_id": lab.finish_good_id.id or False,
                                    "bom_id": lab.bom_id.id or False,
                                    "description": lab.description,
                                    "analytic_idz": [(6, 0, lab.analytic_idz.ids)] or False,
                                    "contractors": lab.contractors,
                                    "time": lab.time,
                                    "quantity": lab.quantity,
                                    "uom_id": lab.uom_id.id or False,
                                    "unit_price": lab.unit_price,
                                    "subtotal": lab.subtotal,
                                }))
                            else:
                                i = labour_values.index(value)
                                labour_line_ids[i][2]['subtotal'] += lab.subtotal
                                labour_line_ids[i][2]['quantity'] += lab.quantity
                                labour_line_ids[i][2]['contractors'] += lab.contractors
                                labour_line_ids[i][2]['time'] += lab.time
                        labour_line_ids.extend(inexist_labour)

                        inexist_overhead = []
                        for ov in sale_order_cons.overhead_line_ids:
                            if rec.is_engineering == False:
                                value = {
                                    "project_scope": ov.project_scope.name,
                                    "section_name": ov.section_name.name,
                                    "variable_ref": ov.variable_ref.name,
                                    "type": "overhead",
                                    "group_of_product": ov.group_of_product.id,
                                    "overhead_id": ov.overhead_id.id,
                                    "description": ov.description,
                                    "uom_id": ov.uom_id.id,
                                    "unit_price": ov.unit_price,
                                    "overhead_catagory": ov.overhead_catagory,
                                }
                            else:
                                value = {
                                    "project_scope": ov.project_scope.name,
                                    "section_name": ov.section_name.name,
                                    "variable_ref": ov.variable_ref.name,
                                    "type": "overhead",
                                    "group_of_product": ov.group_of_product.id,
                                    "overhead_id": ov.overhead_id.id,
                                    "finish_good_id": ov.finish_good_id.name,
                                    "bom_id": ov.bom_id.name,
                                    "description": ov.description,
                                    "uom_id": ov.uom_id.id,
                                    "unit_price": ov.unit_price,
                                    "overhead_catagory": ov.overhead_catagory,
                                }

                            if value not in overhead_values:
                                inexist_overhead.append((0, 0,
                                {
                                    "project_scope": ov.project_scope.id or False,
                                    "section_name": ov.section_name.id or False,
                                    "variable_ref": ov.variable_ref.id or False,
                                    "type": "overhead",
                                    "group_of_product": ov.group_of_product.id or False,
                                    "overhead_id": ov.overhead_id.id or False,
                                    "finish_good_id": ov.finish_good_id.id or False,
                                    "bom_id": ov.bom_id.id or False,
                                    "description": ov.description,
                                    "analytic_idz": [(6, 0, ov.analytic_idz.ids)] or False,
                                    "quantity": ov.quantity,
                                    "uom_id": ov.uom_id.id or False,
                                    "unit_price": ov.unit_price,
                                    "subtotal": ov.subtotal,
                                    "overhead_catagory": ov.overhead_catagory,
                                }))
                            else:
                                i = overhead_values.index(value)
                                overhead_line_ids[i][2]['subtotal'] += ov.subtotal
                                overhead_line_ids[i][2]['quantity'] += ov.quantity
                        overhead_line_ids.extend(inexist_overhead)

                        inexist_asset = []
                        for asset in sale_order_cons.internal_asset_line_ids:
                            if rec.is_engineering == False:
                                value = {
                                    "project_scope": asset.project_scope.name,
                                    "section_name": asset.section_name.name,
                                    "variable_ref": asset.variable_ref.name,
                                    "type": "asset",
                                    "asset_category_id": asset.asset_category_id.id,
                                    "asset_id": asset.asset_id.id,
                                    "description": asset.description,
                                    "uom_id": asset.uom_id.id,
                                    "unit_price": asset.unit_price
                                }
                            else:
                                value = {
                                    "project_scope": asset.project_scope.name,
                                    "section_name": asset.section_name.name,
                                    "variable_ref": asset.variable_ref.name,
                                    "type": "asset",
                                    "asset_category_id": asset.asset_category_id.id,
                                    "asset_id": asset.asset_id.id,
                                    "finish_good_id": asset.finish_good_id.name,
                                    "bom_id": asset.bom_id.name,
                                    "description": asset.description,
                                    "uom_id": asset.uom_id.id,
                                    "unit_price": asset.unit_price
                                }

                            if value not in internal_values:
                                inexist_asset.append((0, 0,
                                {
                                    "project_scope": asset.project_scope.id or False,
                                    "section_name": asset.section_name.id or False,
                                    "variable_ref": asset.variable_ref.id or False,
                                    "type": "asset",
                                    "asset_category_id": asset.asset_category_id.id or False,
                                    "asset_id": asset.asset_id.id or False,
                                    "finish_good_id": asset.finish_good_id.id or False,
                                    "bom_id": asset.bom_id.id or False,
                                    "description": asset.description,
                                    "analytic_idz": [(6, 0, asset.analytic_idz.ids)] or False,
                                    "quantity": asset.quantity,
                                    "uom_id": asset.uom_id.id or False,
                                    "unit_price": asset.unit_price,
                                    "subtotal": asset.subtotal,
                                }))
                            else:
                                i = internal_values.index(value)
                                internal_asset_line_ids[i][2]['subtotal'] += asset.subtotal
                                internal_asset_line_ids[i][2]['quantity'] += asset.quantity
                        internal_asset_line_ids.extend(inexist_asset)

                        inexist_equipment = []
                        for eq in sale_order_cons.equipment_line_ids:
                            if rec.is_engineering == False:
                                value = {
                                    "project_scope": eq.project_scope.name,
                                    "section_name": eq.section_name.name,
                                    "variable_ref": eq.variable_ref.name,
                                    "type": "equipment",
                                    "group_of_product": eq.group_of_product.id,
                                    "equipment_id": eq.equipment_id.id,
                                    "description": eq.description,
                                    "uom_id": eq.uom_id.id,
                                    "unit_price": eq.unit_price
                                }
                            else:
                                value = {
                                    "project_scope": eq.project_scope.name,
                                    "section_name": eq.section_name.name,
                                    "variable_ref": eq.variable_ref.name,
                                    "type": "equipment",
                                    "group_of_product": eq.group_of_product.id,
                                    "finish_good_id": eq.finish_good_id.name,
                                    "bom_id": eq.bom_id.name,
                                    "equipment_id": eq.equipment_id.id,
                                    "description": eq.description,
                                    "uom_id": eq.uom_id.id,
                                    "unit_price": eq.unit_price
                                }

                            if value not in equipment_values:
                                inexist_equipment.append((0, 0,
                                {
                                    "project_scope": eq.project_scope.id or False,
                                    "section_name": eq.section_name.id or False,
                                    "variable_ref": eq.variable_ref.id or False,
                                    "type": "equipment",
                                    "group_of_product": eq.group_of_product.id or False,
                                    "equipment_id": eq.equipment_id.id or False,
                                    "finish_good_id": eq.finish_good_id.id or False,
                                    "bom_id": eq.bom_id.id or False,
                                    "description": eq.description,
                                    "analytic_idz": eq.analytic_idz and [(6, 0, eq.analytic_idz.ids)] or False,
                                    "quantity": eq.quantity,
                                    "uom_id": eq.uom_id.id or False,
                                    "unit_price": eq.unit_price,
                                    "subtotal": eq.subtotal,
                                }))
                            else:
                                i = equipment_values.index(value)
                                equipment_line_ids[i][2]['subtotal'] += eq.subtotal
                                equipment_line_ids[i][2]['quantity'] += eq.quantity
                        equipment_line_ids.extend(inexist_equipment)

                        inexist_subcon = []
                        for sub in sale_order_cons.subcon_line_ids:
                            if rec.is_engineering == False:
                                value = {
                                    "project_scope": sub.project_scope.name,
                                    "section_name": sub.section_name.name,
                                    "variable_ref": sub.variable_ref.name,
                                    "type": "subcon",
                                    "subcon_id": sub.subcon_id.id,
                                    "description": sub.description,
                                    "uom_id": sub.uom_id.id,
                                    "unit_price": sub.unit_price,
                                }
                            else:
                                value = {
                                    "project_scope": sub.project_scope.name,
                                    "section_name": sub.section_name.name,
                                    "variable_ref": sub.variable_ref.name,
                                    "type": "subcon",
                                    "subcon_id": sub.subcon_id.id,
                                    "finish_good_id": sub.finish_good_id.name,
                                    "bom_id": sub.bom_id.name,
                                    "description": sub.description,
                                    "uom_id": sub.uom_id.id,
                                    "unit_price": sub.unit_price,
                                }

                            if value not in subcon_values:
                                inexist_subcon.append((0, 0,
                                {
                                    "project_scope": sub.project_scope.id or False,
                                    "section_name": sub.section_name.id or False,
                                    "variable_ref": sub.variable_ref.id or False,
                                    "type": "subcon",
                                    "subcon_id": sub.subcon_id.id or False,
                                    "finish_good_id": sub.finish_good_id.id or False,
                                    "bom_id": sub.bom_id.id or False,
                                    "description": sub.description,
                                    "analytic_idz": [(6, 0, sub.analytic_idz.ids)] or False,
                                    "quantity": sub.quantity,
                                    "uom_id": sub.uom_id.id or False,
                                    "unit_price": sub.unit_price,
                                    "subtotal": sub.subtotal,
                                }))
                            else:
                                i = subcon_values.index(value)
                                subcon_line_ids[i][2]['subtotal'] += sub.subtotal
                                subcon_line_ids[i][2]['quantity'] += sub.quantity
                        subcon_line_ids.extend(inexist_subcon)

                        context = {
                            'is_wizard': is_wizard,
                            'default_job_references':[(4, rec.job_estimate_id.id)] + [(4, job.id) for job in sale_order_cons.job_references],
                            'default_project_id': rec.project_id.id,
                            'default_partner_id': rec.customer_id.id,
                            'default_project_scope_ids': project_scope_ids,
                            'default_section_ids': section_ids,
                            'default_variable_ids': variable_ids,
                            'default_manufacture_line': manufacture_line,
                            'default_material_line_ids': material_line_ids,
                            'default_labour_line_ids': labour_line_ids,
                            'default_overhead_line_ids': overhead_line_ids,
                            'default_internal_asset_line_ids': internal_asset_line_ids,
                            'default_equipment_line_ids': equipment_line_ids,
                            'default_subcon_line_ids': subcon_line_ids,
                            'default_is_wizard': is_wizard,
                            'default_job_count': len(sale_order_cons.job_references) + 1,
                        }

                        if len(manufacture_line)>0:
                            context['default_is_engineering'] = True
                    else:
                        inexist_scope = []
                        for scope in sale_order_cons.project_scope_ids:
                            value = {
                                "project_scope": scope.project_scope.name,
                                "description": scope.description
                            }
                            if value not in scope_values:
                                inexist_scope.append((0, 0,
                                                      {
                                                          # "job_estimate_id": project_scope.job_estimate_id.id,
                                                          "project_scope": scope.project_scope.id or False,
                                                          "description": scope.description,
                                                          "subtotal_scope": scope.subtotal_scope,
                                                      }))
                            else:
                                i = scope_values.index(value)
                                project_scope_ids[i][2]['subtotal_scope'] += scope.subtotal_scope
                        project_scope_ids.extend(inexist_scope)

                        inexist_section = []
                        for sect in sale_order_cons.section_ids:
                            value = {
                                "project_scope": sect.project_scope.name,
                                "section": sect.section.name,
                                "description": sect.description,
                                "uom_id": sect.uom_id.id
                            }
                            if value not in section_values:
                                inexist_section.append((0, 0,
                                                        {
                                                            "project_scope": sect.project_scope.id or False,
                                                            "section": sect.section.id or False,
                                                            "description": sect.description,
                                                            "quantity": sect.quantity,
                                                            "uom_id": sect.uom_id.id or False,
                                                            "subtotal_section": sect.subtotal_section,
                                                        }))
                            else:
                                i = section_values.index(value)
                                section_ids[i][2]['subtotal_section'] += sect.subtotal_section
                                section_ids[i][2]['quantity'] += sect.quantity
                        section_ids.extend(inexist_section)

                        inexist_variable = []
                        for var in sale_order_cons.variable_ids:
                            value = {
                                "project_scope": var.project_scope.name,
                                "section": var.section.name,
                                "variable": var.variable.name,
                                "uom_id": var.uom_id.id
                            }
                            if value not in variable_values:
                                inexist_variable.append((0, 0,
                                                         {
                                                             # "job_estimate_id": variable.job_estimate_id.id,
                                                             "project_scope": var.project_scope.id or False,
                                                             "section": var.section.id or False,
                                                             "variable": var.variable.id or False,
                                                             "quantity": var.quantity,
                                                             "uom_id": var.uom_id.id or False,
                                                             "subtotal_variable": var.subtotal_variable,
                                                         }))
                            else:
                                i = variable_values.index(value)
                                variable_ids[i][2]['subtotal_variable'] += var.subtotal_variable
                                variable_ids[i][2]['quantity'] += var.quantity
                        variable_ids.extend(inexist_variable)

                        inexist_material = []
                        for mat in sale_order_cons.material_line_ids:
                            value = {
                                "project_scope": mat.project_scope.name,
                                "section_name": mat.section_name.name,
                                "variable_ref": mat.variable_ref.name,
                                "type": "material",
                                "group_of_product": mat.group_of_product.id,
                                "material_id": mat.material_id.id,
                                "description": mat.description,
                                "uom_id": mat.uom_id.id,
                                "unit_price": mat.unit_price,
                            }
                            if value not in material_values:
                                inexist_material.append((0, 0,
                                                         {
                                                             "project_scope": mat.project_scope.id or False,
                                                             "section_name": mat.section_name.id or False,
                                                             "variable_ref": mat.variable_ref.id or False,
                                                             "type": "material",
                                                             "group_of_product": mat.group_of_product.id or False,
                                                             "material_id": mat.material_id.id or False,
                                                             "description": mat.description,
                                                             "analytic_idz": [(6, 0, mat.analytic_idz.ids)] or False,
                                                             "quantity": mat.quantity,
                                                             "uom_id": mat.uom_id.id or False,
                                                             "unit_price": mat.unit_price,
                                                             "subtotal": mat.subtotal,
                                                         }))
                            else:
                                i = material_values.index(value)
                                material_line_ids[i][2]['subtotal'] += mat.subtotal
                                material_line_ids[i][2]['quantity'] += mat.quantity
                        material_line_ids.extend(inexist_material)

                        inexist_labour = []
                        for lab in sale_order_cons.labour_line_ids:
                            value = {
                                "project_scope": lab.project_scope.name,
                                "section_name": lab.section_name.name,
                                "variable_ref": lab.variable_ref.name,
                                "type": "labour",
                                "group_of_product": lab.group_of_product.id,
                                "labour_id": lab.labour_id.id,
                                "description": lab.description,
                                "uom_id": lab.uom_id.id,
                                "unit_price": labour.unit_price
                            }
                            if value not in labour_values:
                                inexist_labour.append((0, 0,
                                                       {
                                                           "project_scope": lab.project_scope.id or False,
                                                           "section_name": lab.section_name.id or False,
                                                           "variable_ref": lab.variable_ref.id or False,
                                                           "type": "labour",
                                                           "group_of_product": lab.group_of_product.id or False,
                                                           "labour_id": lab.labour_id.id or False,
                                                           "description": lab.description,
                                                           "analytic_idz": [(6, 0, lab.analytic_idz.ids)] or False,
                                                           "quantity": lab.quantity,
                                                           "uom_id": lab.uom_id.id or False,
                                                           "unit_price": lab.unit_price,
                                                           "subtotal": lab.subtotal,
                                                       }))
                            else:
                                i = labour_values.index(value)
                                labour_line_ids[i][2]['subtotal'] += lab.subtotal
                                labour_line_ids[i][2]['quantity'] += lab.quantity
                                labour_line_ids[i][2]['contractors'] += lab.contractors
                                labour_line_ids[i][2]['time'] += lab.time
                        labour_line_ids.extend(inexist_labour)

                        inexist_overhead = []
                        for ov in sale_order_cons.overhead_line_ids:
                            value = {
                                "project_scope": ov.project_scope.name,
                                "section_name": ov.section_name.name,
                                "variable_ref": ov.variable_ref.name,
                                "type": "overhead",
                                "group_of_product": ov.group_of_product.id,
                                "overhead_id": ov.overhead_id.id,
                                "description": ov.description,
                                "uom_id": ov.uom_id.id,
                                "unit_price": ov.unit_price,
                                "overhead_catagory": ov.overhead_catagory,
                            }
                            if value not in overhead_values:
                                inexist_overhead.append((0, 0,
                                                         {
                                                             "project_scope": ov.project_scope.id or False,
                                                             "section_name": ov.section_name.id or False,
                                                             "variable_ref": ov.variable_ref.id or False,
                                                             "type": "overhead",
                                                             "group_of_product": ov.group_of_product.id or False,
                                                             "overhead_id": ov.overhead_id.id or False,
                                                             "description": ov.description,
                                                             "analytic_idz": [(6, 0, ov.analytic_idz.ids)] or False,
                                                             "quantity": ov.quantity,
                                                             "uom_id": ov.uom_id.id or False,
                                                             "unit_price": ov.unit_price,
                                                             "subtotal": ov.subtotal,
                                                             "overhead_catagory": ov.overhead_catagory,
                                                         }))
                            else:
                                i = overhead_values.index(value)
                                overhead_line_ids[i][2]['subtotal'] += ov.subtotal
                                overhead_line_ids[i][2]['quantity'] += ov.quantity
                        overhead_line_ids.extend(inexist_overhead)

                        inexist_asset = []
                        for asset in sale_order_cons.internal_asset_line_ids:
                            value = {
                                "project_scope": asset.project_scope.name,
                                "section_name": asset.section_name.name,
                                "variable_ref": asset.variable_ref.name,
                                "type": "asset",
                                "asset_category_id": asset.asset_category_id.id,
                                "asset_id": asset.asset_id.id,
                                "description": asset.description,
                                "uom_id": asset.uom_id.id,
                                "unit_price": asset.unit_price
                            }
                            if value not in internal_values:
                                inexist_asset.append((0, 0,
                                                      {
                                                          "project_scope": asset.project_scope.id or False,
                                                          "section_name": asset.section_name.id or False,
                                                          "variable_ref": asset.variable_ref.id or False,
                                                          "type": "asset",
                                                          "asset_category_id": asset.asset_category_id.id or False,
                                                          "asset_id": asset.asset_id.id or False,
                                                          "description": asset.description,
                                                          "analytic_idz": [(6, 0, asset.analytic_idz.ids)] or False,
                                                          "quantity": asset.quantity,
                                                          "uom_id": asset.uom_id.id or False,
                                                          "unit_price": asset.unit_price,
                                                          "subtotal": asset.subtotal,
                                                      }))
                            else:
                                i = internal_values.index(value)
                                internal_asset_line_ids[i][2]['subtotal'] += asset.subtotal
                                internal_asset_line_ids[i][2]['quantity'] += asset.quantity
                        internal_asset_line_ids.extend(inexist_asset)

                        inexist_equipment = []
                        for eq in sale_order_cons.equipment_line_ids:
                            value = {
                                "project_scope": eq.project_scope.name,
                                "section_name": eq.section_name.name,
                                "variable_ref": eq.variable_ref.name,
                                "type": "equipment",
                                "group_of_product": eq.group_of_product.id,
                                "equipment_id": eq.equipment_id.id,
                                "description": eq.description,
                                "uom_id": eq.uom_id.id,
                                "unit_price": eq.unit_price
                            }
                            if value not in equipment_values:
                                inexist_equipment.append((0, 0,
                                                          {
                                                              "project_scope": eq.project_scope.id or False,
                                                              "section_name": eq.section_name.id or False,
                                                              "variable_ref": eq.variable_ref.id or False,
                                                              "type": "equipment",
                                                              "group_of_product": eq.group_of_product.id or False,
                                                              "equipment_id": eq.equipment_id.id or False,
                                                              "description": eq.description,
                                                              "analytic_idz": eq.analytic_idz and [
                                                                  (6, 0, eq.analytic_idz.ids)] or False,
                                                              "quantity": eq.quantity,
                                                              "uom_id": eq.uom_id.id or False,
                                                              "unit_price": eq.unit_price,
                                                              "subtotal": eq.subtotal,
                                                          }))
                            else:
                                i = equipment_values.index(value)
                                equipment_line_ids[i][2]['subtotal'] += eq.subtotal
                                equipment_line_ids[i][2]['quantity'] += eq.quantity
                        equipment_line_ids.extend(inexist_equipment)

                        inexist_subcon = []
                        for sub in sale_order_cons.subcon_line_ids:
                            value = {
                                "project_scope": sub.project_scope.name,
                                "section_name": sub.section_name.name,
                                "variable_ref": sub.variable_ref.name,
                                "type": "subcon",
                                "subcon_id": sub.subcon_id.id,
                                "description": sub.description,
                                "uom_id": sub.uom_id.id,
                                "unit_price": sub.unit_price,
                            }
                            if value not in subcon_values:
                                inexist_subcon.append((0, 0,
                                                       {
                                                           "project_scope": sub.project_scope.id or False,
                                                           "section_name": sub.section_name.id or False,
                                                           "variable_ref": sub.variable_ref.id or False,
                                                           "type": "subcon",
                                                           "subcon_id": sub.subcon_id.id or False,
                                                           "description": sub.description,
                                                           "analytic_idz": [(6, 0, sub.analytic_idz.ids)] or False,
                                                           "quantity": sub.quantity,
                                                           "uom_id": sub.uom_id.id or False,
                                                           "unit_price": sub.unit_price,
                                                           "subtotal": sub.subtotal,
                                                       }))
                            else:
                                i = subcon_values.index(value)
                                subcon_line_ids[i][2]['subtotal'] += sub.subtotal
                                subcon_line_ids[i][2]['quantity'] += sub.quantity
                        subcon_line_ids.extend(inexist_subcon)

                        context = {
                            'is_wizard': is_wizard,
                            'default_job_references': [(4, rec.job_estimate_id.id)] + [(4, job.id) for job in
                                                                                       sale_order_cons.job_references],
                            'default_project_id': rec.project_id.id,
                            'default_partner_id': rec.customer_id.id,
                            'default_project_scope_ids': project_scope_ids,
                            'default_section_ids': section_ids,
                            'default_variable_ids': variable_ids,
                            'default_material_line_ids': material_line_ids,
                            'default_labour_line_ids': labour_line_ids,
                            'default_overhead_line_ids': overhead_line_ids,
                            'default_internal_asset_line_ids': internal_asset_line_ids,
                            'default_equipment_line_ids': equipment_line_ids,
                            'default_subcon_line_ids': subcon_line_ids,
                            'default_is_wizard': is_wizard,
                            'default_job_count': len(sale_order_cons.job_references) + 1,
                        }

            else:
                context = {
                    'is_wizard': is_wizard,
                    'default_job_references':[(4, rec.job_estimate_id.id)],
                    'default_project_id': rec.project_id.id,
                    'default_partner_id': rec.customer_id.id,
                    'default_project_scope_ids': project_scope_ids,
                    'default_section_ids': section_ids,
                    'default_variable_ids': variable_ids,
                    'default_manufacture_line': manufacture_line,
                    'default_material_line_ids': material_line_ids,
                    'default_labour_line_ids': labour_line_ids,
                    'default_overhead_line_ids': overhead_line_ids,
                    'default_internal_asset_line_ids': internal_asset_line_ids,
                    'default_equipment_line_ids': equipment_line_ids,
                    'default_subcon_line_ids': subcon_line_ids,
                    'default_is_wizard': is_wizard,
                    'default_job_count': 1,
                }
                
                if len(manufacture_line)>0:
                        context['default_is_engineering'] = True

            return {
                "name": "Quotation",
                "type": "ir.actions.act_window",
                "res_model": "sale.order.const",
                "res_id": sale_order_cons.id if sale_order_cons and not ctx.get('create_new') else False,
                "context": context,
                "view_mode": 'form',
                "target": "current",
            }


class JobEstimateExistingQuotationManufacture(models.TransientModel):
    _name = "job.estimate.existing.line.manufacture"
    _description = "BOQ Existing Quotation Manufacture"
    _order = 'number'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    manufacture_id = fields.Many2one("to.manufacture.line", string="Manufacture")
    is_active = fields.Boolean(string="Active", default=True)
    is_engineering = fields.Boolean(related='job_estimate_id.is_engineering')
    number = fields.Integer('No.', compute="_sequence_ref")
    project_scope_id = fields.Many2one('project.scope.line', 'Project Scope', required=True)
    section_id = fields.Many2one('section.line','Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
    cascaded = fields.Boolean(string="Cascaded", default=False)
    is_child = fields.Boolean(string="Is child", default=False)
    parent_manuf_line = fields.Many2one('mrp.bom', string='Parent BOM')
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)
    quantity = fields.Float('Quantity', default=1)
    uom_id = fields.Many2one('uom.uom','Unit Of Measure')
    currency_id = fields.Many2one('res.currency', invisible=True)
    subtotal = fields.Monetary('Subtotal')
    onchange_pass = fields.Boolean(string="Pass", default=False)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")

    @api.depends('wiz_id')
    def _sequence_ref(self):
        no = 0
        for line in self:
            no += 1
            line.number = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id


class MaterialLine(models.TransientModel):
    _inherit = 'job.estimate.existing.line.material'

    finish_good_id = fields.Many2one('product.product', 'Finish Goods', domain=[('bom_count','>',0)])
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class LabourLine(models.TransientModel):
    _inherit = 'job.estimate.existing.line.labour'

    finish_good_id = fields.Many2one('product.product', 'Finish Goods', domain=[('bom_count','>',0)])
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class OverheadLine(models.TransientModel):
    _inherit = 'job.estimate.existing.line.overhead'

    finish_good_id = fields.Many2one('product.product', 'Finish Goods', domain=[('bom_count','>',0)])
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class InternalAssets(models.TransientModel):
    _inherit = 'job.estimate.existing.line.asset'

    finish_good_id = fields.Many2one('product.product', 'Finish Goods', domain=[('bom_count','>',0)])
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class EquipmentLine(models.TransientModel):
    _inherit = 'job.estimate.existing.line.equipment'

    finish_good_id = fields.Many2one('product.product', 'Finish Goods', domain=[('bom_count','>',0)])
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')

class SubconLine(models.TransientModel):
    _inherit = 'job.estimate.existing.line.subcon'

    finish_good_id = fields.Many2one('product.product', 'Finish Goods', domain=[('bom_count','>',0)])
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    final_finish_good_id = fields.Many2one('product.product', 'Final Finished Goods')
