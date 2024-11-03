# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
from odoo import tools

import logging
_logger = logging.getLogger(__name__)

class JobEstimateTemplate(models.Model):
    _name = 'job.estimate.template'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin', 'utm.mixin']
    _description = "BOQ Template"
    _order = 'id DESC'
    _check_company_auto = True

    project_scope_computed = fields.Many2many('project.scope.line', string='Project Scope', compute="get_scope_lines")
    section_name_computed = fields.Many2many('section.line', string='Section Computed')

    @api.depends('project_scope_ids')
    def get_scope_lines(self):
        for rec in self:
            scope_ids = []
            if rec.project_scope_ids:
                for line in rec.project_scope_ids:
                    if line.project_scope:
                        scope_ids.append(line.project_scope.id)
                rec.project_scope_computed = [(6, 0, scope_ids)]
            else:
                rec.project_scope_computed = [(6, 0, [])]

    @api.onchange('variable_ids', 'variable_ids.project_scope', 'variable_ids.section_name',
                  'variable_ids.variable_name', 'variable_ids.variable_quantity')
    def update_material(self):
        material = []
        labour = []
        subcon = []
        overhead = []
        equip = []
        asset = []
        variable_list = []

        for rec in self.variable_ids:
            scope = rec.project_scope
            section = rec.section_name
            variable = rec.variable_name
            var_quantity = 1

            if scope and section and variable:
                if var_quantity > 0:
                    if rec.onchange_pass == False:
                        rec.write({'onchange_pass': True})

                        # for material
                        if variable.material_variable_ids:
                            for mater in self.material_estimation_ids:
                                if mater.project_scope != False and mater.section_name != False and len(
                                        mater.variable_ref) != 0:
                                    if mater.project_scope == scope and mater.section_name == section and mater.variable_ref == variable:
                                        self.material_estimation_ids = [(2, mater.id)]
                            for mat in variable.material_variable_ids:
                                matx = (0, 0, {
                                    'product_id': mat.product_id.id,
                                    'quantity': var_quantity * mat.quantity,
                                    'subtotal': mat.unit_price * (var_quantity * mat.quantity),
                                    'unit_price': mat.unit_price,
                                    'uom_id': mat.uom_id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'description': mat.description,
                                    'group_of_product': mat.group_of_product.id
                                })
                                material.append(matx)
                            self.material_estimation_ids = material

                        # for labor
                        if variable.labour_variable_ids:
                            for labo in self.labour_estimation_ids:
                                if labo.project_scope != False and labo.section_name != False and len(
                                        labo.variable_ref) != 0:
                                    if labo.project_scope == scope and labo.section_name == section and labo.variable_ref == variable:
                                        self.labour_estimation_ids = [(2, labo.id)]
                            for lab in variable.labour_variable_ids:
                                labx = (0, 0, {
                                    'product_id': lab.product_id.id,
                                    'subtotal': lab.unit_price * (lab.contractors * (var_quantity * lab.time)),
                                    'unit_price': lab.unit_price,
                                    'uom_id': lab.uom_id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'description': lab.description,
                                    'group_of_product': lab.group_of_product.id,
                                    'contractors': lab.contractors,
                                    'time': var_quantity * lab.time,
                                    'quantity': lab.contractors * (var_quantity * lab.time),
                                })
                                labour.append(labx)
                            self.labour_estimation_ids = labour

                        # for subcon
                        if variable.subcon_variable_ids:
                            for subc in self.subcon_estimation_ids:
                                if subc.project_scope != False and subc.section_name != False and len(
                                        subc.variable_ref) != 0:
                                    if subc.project_scope == scope and subc.section_name == section and subc.variable_ref == variable:
                                        self.subcon_estimation_ids = [(2, subc.id)]
                            for sub in variable.subcon_variable_ids:
                                subx = (0, 0, {
                                    'variable': sub.variable.id,
                                    'quantity': var_quantity * sub.quantity,
                                    'subtotal': sub.unit_price * (var_quantity * sub.quantity),
                                    'unit_price': sub.unit_price,
                                    'uom_id': sub.uom_id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'description': sub.description,
                                })
                                subcon.append(subx)
                            self.subcon_estimation_ids = subcon

                        # for over
                        if variable.overhead_variable_ids:
                            for overh in self.overhead_estimation_ids:
                                if overh.project_scope != False and overh.section_name != False and len(
                                        overh.variable_ref) != 0:
                                    if overh.project_scope == scope and overh.section_name == section and overh.variable_ref == variable:
                                        self.overhead_estimation_ids = [(2, overh.id)]
                            for over in variable.overhead_variable_ids:
                                overx = (0, 0, {
                                    'overhead_catagory': over.overhead_catagory,
                                    'product_id': over.product_id.id,
                                    'quantity': var_quantity * over.quantity,
                                    'subtotal': over.unit_price * (var_quantity * over.quantity),
                                    'unit_price': over.unit_price,
                                    'uom_id': over.uom_id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'description': over.description,
                                    'group_of_product': over.group_of_product.id
                                })
                                overhead.append(overx)
                            self.overhead_estimation_ids = overhead

                        # for equip
                        if variable.equipment_variable_ids:
                            for equi in self.equipment_estimation_ids:
                                if equi.project_scope != False and equi.section_name != False and len(
                                        equi.variable_ref) != 0:
                                    if equi.project_scope == scope and equi.section_name == section and equi.variable_ref == variable:
                                        self.equipment_estimation_ids = [(2, equi.id)]
                            for eqp in variable.equipment_variable_ids:
                                eqpx = (0, 0, {
                                    'product_id': eqp.product_id.id,
                                    'quantity': var_quantity * eqp.quantity,
                                    'subtotal': eqp.unit_price * (var_quantity * eqp.quantity),
                                    'unit_price': eqp.unit_price,
                                    'uom_id': eqp.uom_id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'description': eqp.description,
                                    'group_of_product': eqp.group_of_product.id
                                })
                                equip.append(eqpx)
                            self.equipment_estimation_ids = equip

                        # for asset
                        if variable.asset_variable_ids:
                            for asse in self.asset_estimation_ids:
                                if asse.project_scope != False and asse.section_name != False and len(
                                        asse.variable_ref) != 0:
                                    if asse.project_scope == scope and asse.section_name == section and asse.variable_ref == variable:
                                        self.asset_estimation_ids = [(2, asse.id)]
                            for ass in variable.asset_variable_ids:
                                assx = (0, 0, {
                                    'asset_category_id': ass.asset_category_id.id,
                                    'asset_id': ass.asset_id.id,
                                    'quantity': var_quantity * ass.quantity,
                                    'subtotal': ass.unit_price * (var_quantity * ass.quantity),
                                    'unit_price': ass.unit_price,
                                    'uom_id': ass.uom_id,
                                    'project_scope': scope.id,
                                    'section_name': section.id,
                                    'variable_ref': variable.id,
                                    'description': ass.description,
                                })
                                asset.append(assx)
                            self.asset_estimation_ids = asset
                    variable_list.append((scope.name, section.name, variable.name))

        for mat in self.material_estimation_ids:
            if mat.project_scope != False and mat.section_name != False and len(mat.variable_ref) != 0:
                if (mat.project_scope.name, mat.section_name.name, mat.variable_ref.name) not in variable_list:
                    self.material_estimation_ids = [(2, mat.id)]
        for lab in self.labour_estimation_ids:
            if lab.project_scope != False and lab.section_name != False and len(lab.variable_ref) != 0:
                if (lab.project_scope.name, lab.section_name.name, lab.variable_ref.name) not in variable_list:
                    self.labour_estimation_ids = [(2, lab.id)]
        for ov in self.overhead_estimation_ids:
            if ov.project_scope != False and ov.section_name != False and len(ov.variable_ref) != 0:
                if (ov.project_scope.name, ov.section_name.name, ov.variable_ref.name) not in variable_list:
                    self.overhead_estimation_ids = [(2, ov.id)]
        for asset in self.asset_estimation_ids:
            if asset.project_scope != False and asset.section_name != False and len(asset.variable_ref) != 0:
                if (asset.project_scope.name, asset.section_name.name, asset.variable_ref.name) not in variable_list:
                    self.asset_estimation_ids = [(2, asset.id)]
        for eq in self.equipment_estimation_ids:
            if eq.project_scope != False and eq.section_name != False and len(eq.variable_ref) != 0:
                if (eq.project_scope.name, eq.section_name.name, eq.variable_ref.name) not in variable_list:
                    self.equipment_estimation_ids = [(2, eq.id)]
        for sub in self.subcon_estimation_ids:
            if sub.project_scope != False and sub.section_name != False and len(sub.variable_ref) != 0:
                if (sub.project_scope.name, sub.section_name.name, sub.variable_ref.name) not in variable_list:
                    self.subcon_estimation_ids = [(2, sub.id)]

    @api.depends('material_estimation_ids.subtotal', 'labour_estimation_ids.subtotal', 'subcon_estimation_ids.subtotal',
                 'overhead_estimation_ids.subtotal', 'equipment_estimation_ids.subtotal',
                 'asset_estimation_ids.subtotal')
    def _onchange_calculate_total(self):
        for order in self:
            total_job_cost = 0.0
            if order.material_estimation_ids:
                for line in order.material_estimation_ids:
                    material_price = (line.quantity * line.unit_price)
                    order.total_material_estimate += material_price
                    total_job_cost += material_price

            else:

                order.total_material_estimate = 0

            if order.labour_estimation_ids:
                for line in order.labour_estimation_ids:
                    labour_price = (line.quantity * line.unit_price)
                    order.total_labour_estimate += labour_price
                    total_job_cost += labour_price
            else:

                order.total_labour_estimate = 0

            if order.overhead_estimation_ids:
                for line in order.overhead_estimation_ids:
                    overhead_price = (line.quantity * line.unit_price)
                    order.total_overhead_estimate += overhead_price
                    total_job_cost += overhead_price

            else:

                order.total_overhead_estimate = 0

            if order.subcon_estimation_ids:
                for line in order.subcon_estimation_ids:
                    subcon_price = (line.quantity * line.unit_price)
                    order.total_subcon_estimate += subcon_price
                    total_job_cost += subcon_price
            else:

                order.total_subcon_estimate = 0

            if order.equipment_estimation_ids:
                for line in order.equipment_estimation_ids:
                    equipment_price = (line.quantity * line.unit_price)
                    order.total_equipment_estimate += equipment_price
                    total_job_cost += equipment_price
            else:

                order.total_equipment_estimate = 0

            # ---------- total internal asset estimation -----------
            if order.asset_estimation_ids:
                subtotals = [line.subtotal for line in order.asset_estimation_ids]
                order.total_internal_assets_estimate = sum(subtotals)
                total_job_cost += order.total_internal_assets_estimate
            else:

                order.total_internal_assets_estimate = 0

            order.total_assets_estimate = order.total_equipment_estimate + order.total_internal_assets_estimate

            order.total_job_estimate += total_job_cost

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id
            line.company_id = res_user_id.company_id

    name = fields.Char(string='Name', required=True, copy=False)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id')
    material_estimation_ids = fields.One2many('material.estimate.template', 'material_id', 'Material')
    labour_estimation_ids = fields.One2many('labour.estimate.template', 'labour_id', 'Labour')
    overhead_estimation_ids = fields.One2many('overhead.estimate.template', 'overhead_id', 'Overhead')
    subcon_estimation_ids = fields.One2many('subcon.estimate.template', 'subcon_id', 'Subcon')
    equipment_estimation_ids = fields.One2many('equipment.estimate.template', 'equipment_id', 'Equipment')
    asset_estimation_ids = fields.One2many('internal.assets.estimate.template', 'asset_job_id', 'Asset')
    project_scope_ids = fields.One2many('project.scope.estimate.template', 'scope_id', 'Project Scope')
    section_ids = fields.One2many('section.estimate.template', 'section_id', 'Section')
    variable_ids = fields.One2many('variable.estimate.template', 'variable_id', 'Variable')
    total_material_estimate = fields.Monetary(compute='_onchange_calculate_total', string='Total Material Estimate',
                                              default=0.0,
                                              readonly=True, tracking=True)
    total_labour_estimate = fields.Monetary(compute='_onchange_calculate_total', string='Total Labour Estimate',
                                            default=0.0,
                                            readonly=True, tracking=True)
    total_subcon_estimate = fields.Monetary(compute='_onchange_calculate_total', string='Total Subcon Estimate',
                                            default=0.0,
                                            store=False,
                                            readonly=True, tracking=True)
    total_overhead_estimate = fields.Monetary(compute='_onchange_calculate_total', string='Total Overhead Estimate',
                                              default=0.0,
                                              readonly=True, tracking=True)
    total_equipment_estimate = fields.Monetary(compute='_onchange_calculate_total',
                                               string='Total Equipment Lease Estimate',
                                               default=0.0, tracking=True)
    total_internal_assets_estimate = fields.Monetary(string='Total Internal Asset Estimate',
                                                     default=0.0, tracking=True, compute="_onchange_calculate_total")
    total_assets_estimate = fields.Monetary(compute='_onchange_calculate_total', string='Total Asset Estimate',
                                            default=0.0, tracking=True)
    total_job_estimate = fields.Monetary(string='Total BOQ', tracking=True, compute='_onchange_calculate_total')

    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")

    @api.onchange('project_scope_ids')
    def _onchange_project_scope(self):
        """
        If changed scope doesn't exist in any estimate tab, then delete the lines
        This method has two approach:
        1. If the record is saved to database, then use _origin
        2. If the record is new, then use id
        """
        for rec in self:
            changed_scope = list()
            scope_list = list()
            if len(rec.project_scope_ids) > 0 or len(rec._origin.section_ids._origin) > 0:
                for scope in rec.project_scope_ids:
                    # If BOQ record saved to database, use origin
                    # If new, then use id
                    scope_list.append(scope.project_scope.id)
                    if scope._origin.project_scope._origin.id:
                        if scope.project_scope.id != scope._origin.project_scope._origin.id:
                            changed_scope.append(scope._origin.project_scope._origin.id)
                    else:
                        changed_scope.append(scope.project_scope.id)
            if len(rec.section_ids) > 0:
                for section in rec.section_ids:
                    if section.project_scope.id in changed_scope:
                        rec.section_ids = [(2, section._origin.id, 0)]
                    elif section.project_scope.id not in scope_list:
                        rec.section_ids = [(2, section.id, 0)]
            if len(rec.variable_ids) > 0:
                for variable in rec.variable_ids._origin:
                    if variable.project_scope.id in changed_scope:
                        rec.variable_ids = [(2, variable._origin.id, 0)]
                    elif variable.project_scope.id not in scope_list:
                        rec.variable_ids = [(2, variable.id, 0)]

    @api.onchange('section_ids')
    def _onchange_section(self):
        """
        If changed section doesn't exist in any estimate tab, then delete the lines
        This method has two approach:
        1. If the record is saved to database, then use _origin
        2. If the record is new, then use id
        """
        for rec in self:
            changed_section = list()
            section_list = list()
            if len(rec.section_ids) > 0 or len(rec._origin.section_ids._origin):
                for section in rec.section_ids:
                    # same logic as _onchange_project_scope
                    section_list.append(section.section_name.id)
                    if section._origin.section_name._origin.id:
                        if section.section_name.id != section._origin.section_name._origin.id:
                            changed_section.append(section._origin.section_name._origin.id)
                    else:
                        changed_section.append(section.section_name.id)
            if len(rec.variable_ids) > 0:
                for variable in rec.variable_ids:
                    if variable.section_name.id in changed_section:
                        rec.variable_ids = [(2, variable._origin.id, 0)]
                    elif variable.section_name.id not in section_list:
                        rec.variable_ids = [(2, variable.id, 0)]
            else:
                for material in rec.material_estimation_ids:
                    if material.section_name.id in changed_section:
                        rec.material_estimation_ids = [(2, material._origin.id, 0)]
                    elif material.section_name.id not in section_list:
                        rec.material_estimation_ids = [(2, material.id, 0)]
                for labour in rec.labour_estimation_ids:
                    if labour.section_name.id in changed_section:
                        rec.labour_estimation_ids = [(2, labour._origin.id, 0)]
                    elif labour.section_name.id not in section_list:
                        rec.labour_estimation_ids = [(2, labour.id, 0)]
                for overhead in rec.overhead_estimation_ids:
                    if overhead.section_name.id in changed_section:
                        rec.overhead_estimation_ids = [(2, overhead._origin.id, 0)]
                    elif overhead.section_name.id not in section_list:
                        rec.overhead_estimation_ids = [(2, overhead.id, 0)]
                for internal in rec.asset_estimation_ids:
                    if internal.section_name.id in changed_section:
                        rec.asset_estimation_ids = [(2, internal._origin.id, 0)]
                    elif internal.section_name.id not in section_list:
                        rec.asset_estimation_ids = [(2, internal.id, 0)]
                for equipment in rec.equipment_estimation_ids:
                    if equipment.section_name.id in changed_section:
                        rec.equipment_estimation_ids = [(2, equipment._origin.id, 0)]
                    elif equipment.section_name.id not in section_list:
                        rec.equipment_estimation_ids = [(2, equipment.id, 0)]
                for subcon in rec.subcon_estimation_ids:
                    if subcon.section_name.id in changed_section:
                        rec.subcon_estimation_ids = [(2, subcon._origin.id, 0)]
                    elif subcon.section_name.id not in section_list:
                        rec.subcon_estimation_ids = [(2, subcon.id, 0)]

    @api.constrains('project_scope_ids')
    def _check_exist_project_scope1(self):
        exist_scope_list1 = []
        for line1 in self.project_scope_ids:
            if line1.project_scope.id in exist_scope_list1:
                raise ValidationError(
                    _('The Project Scope "%s" already exists. Please change the Project Scope (must be unique).' % (
                    (line1.project_scope.name))))
            exist_scope_list1.append(line1.project_scope.id)

    @api.onchange('project_scope_ids')
    def _check_exist_project_scope2(self):
        exist_scope_list2 = []
        for line2 in self.project_scope_ids:
            if line2.project_scope.id in exist_scope_list2:
                raise ValidationError(
                    _('The Project Scope "%s" already exists. Please change the Project Scope (must be unique).' % (
                    (line2.project_scope.name))))
            exist_scope_list2.append(line2.project_scope.id)

    @api.constrains('section_ids')
    def _check_exist_section1(self):
        exist_section_list3 = []
        for line3 in self.section_ids:
            same1 = str(line3.project_scope.id) + ' - ' + str(line3.section_name.id)
            if (same1 in exist_section_list3):
                raise ValidationError(
                    _('The Section "%s" already exists in project scope "%s". Please change the Section.' % (
                    (line3.section_name.name), (line3.project_scope.name))))
            exist_section_list3.append(same1)

    @api.onchange('section_ids')
    def _check_exist_section2(self):
        exist_section_list4 = []
        for line4 in self.section_ids:
            same2 = str(line4.project_scope.id) + ' - ' + str(line4.section_name.id)
            if (same2 in exist_section_list4):
                raise ValidationError(
                    _('The Section "%s" already exists in project scope "%s". Please change the Section.' % (
                    (line4.section_name.name), (line4.project_scope.name))))
            exist_section_list4.append(same2)

    @api.constrains('variable_ids')
    def _check_exist_variable(self):
        exist_variable_list = []
        for line in self.variable_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable_name.id)
            if (same in exist_variable_list):
                raise ValidationError(
                    _('The Variable "%s" already exists in project scope "%s" and section "%s". Please change the Variable.' % (
                    (line.variable_name.name), (line.project_scope.name), (line.section_name.name))))
            exist_variable_list.append(same)

    @api.onchange('variable_ids')
    def _check_exist_variable2(self):
        exist_variable_list = []
        for line in self.variable_ids:
            same = str(line.project_scope.id) + ' - ' + str(line.section_name.id) + ' - ' + str(line.variable_name.id)
            if (same in exist_variable_list):
                raise ValidationError(
                    _('The Variable "%s" already exists in project scope "%s" and section "%s". Please change the Variable.' % (
                    (line.variable_name.name), (line.project_scope.name), (line.section_name.name))))
            exist_variable_list.append(same)

    @api.onchange('material_estimation_ids')
    def _check_exist_group_of_product_material(self):
        exist_section_group_list_material = []
        for line5 in self.material_estimation_ids:
            same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(line5.product_id.id)
            if (same3 in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                    (line5.product_id.name), (line5.section_name.name))))
            exist_section_group_list_material.append(same3)

    @api.constrains('material_estimation_ids')
    def _check_exist_group_of_product_material_2(self):
        exist_section_group_list_material = []
        for line5 in self.material_estimation_ids:
            same3 = str(line5.project_scope.id) + ' - ' + str(line5.section_name.id) + ' - ' + str(line5.product_id.id)
            if (same3 in exist_section_group_list_material):
                raise ValidationError(
                    _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                    (line5.product_id.name), (line5.section_name.name))))
            exist_section_group_list_material.append(same3)

    @api.onchange('labour_estimation_ids')
    def _check_exist_group_of_product_labour(self):
        exist_section_group_list_labour1 = []
        for line6 in self.labour_estimation_ids:
            same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(line6.product_id.id)
            if (same41 in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                    (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name))))
            exist_section_group_list_labour1.append(same41)

    @api.constrains('labour_estimation_ids')
    def _check_exist_group_of_product_labour_2(self):
        exist_section_group_list_labour1 = []
        for line6 in self.labour_estimation_ids:
            same41 = str(line6.project_scope.id) + ' - ' + str(line6.section_name.id) + ' - ' + str(line6.product_id.id)
            if (same41 in exist_section_group_list_labour1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                    (line6.product_id.name), (line6.project_scope.name), (line6.section_name.name))))
            exist_section_group_list_labour1.append(same41)

    @api.onchange('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead(self):
        exist_section_group_list_overhead = []
        for line7 in self.overhead_estimation_ids:
            same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(line7.product_id.id)
            if (same5 in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                    (line7.product_id.name), (line7.section_name.name))))
            exist_section_group_list_overhead.append(same5)

    @api.constrains('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead_2(self):
        exist_section_group_list_overhead = []
        for line7 in self.overhead_estimation_ids:
            same5 = str(line7.project_scope.id) + ' - ' + str(line7.section_name.id) + ' - ' + str(line7.product_id.id)
            if (same5 in exist_section_group_list_overhead):
                raise ValidationError(
                    _('The product "%s" already exists in the section "%s", please change the Section or Product selected.' % (
                    (line7.product_id.name), (line7.section_name.name))))
            exist_section_group_list_overhead.append(same5)

    @api.onchange('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment(self):
        exist_section_group_list_equipment1 = []
        for line8 in self.equipment_estimation_ids:
            same51 = str(line8.project_scope.id) + ' - ' + str(line8.section_name.id) + ' - ' + str(line8.product_id.id)
            if (same51 in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                    (line8.product_id.name), (line8.project_scope.name), (line8.section_name.name))))
            exist_section_group_list_equipment1.append(same51)

    @api.constrains('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment_2(self):
        exist_section_group_list_equipment1 = []
        for line8 in self.equipment_estimation_ids:
            same51 = str(line8.project_scope.id) + ' - ' + str(line8.section_name.id) + ' - ' + str(line8.product_id.id)
            if (same51 in exist_section_group_list_equipment1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                    (line8.product_id.name), (line8.project_scope.name), (line8.section_name.name))))
            exist_section_group_list_equipment1.append(same51)

    @api.onchange('asset_estimation_ids')
    def _check_exist_group_of_product_asset(self):
        exist_section_group_list_asset1 = []
        for line9 in self.asset_estimation_ids:
            same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(line9.asset_id.id)
            if (same71 in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                    (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name))))
            exist_section_group_list_asset1.append(same71)

    @api.constrains('asset_estimation_ids')
    def _check_exist_group_of_product_asset_2(self):
        exist_section_group_list_asset1 = []
        for line9 in self.asset_estimation_ids:
            same71 = str(line9.project_scope.id) + ' - ' + str(line9.section_name.id) + ' - ' + str(line9.asset_id.id)
            if (same71 in exist_section_group_list_asset1):
                raise ValidationError(
                    _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                    (line9.asset_id.name), (line9.project_scope.name), (line9.section_name.name))))
            exist_section_group_list_asset1.append(same71)

    @api.onchange('subcon_estimation_ids')
    def _check_exist_subcon(self):
        exist_section_subcon_list_subcon = []
        for line10 in self.subcon_estimation_ids:
            same8 = str(line10.project_scope.id) + ' - ' + str(line10.section_name.id) + ' - ' + str(line10.variable.id)
            if (same8 in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The subcon "%s" already exists in the section "%s", please change the Subcon.' % (
                    (line10.variable.name), (line10.section_name.name))))
            exist_section_subcon_list_subcon.append(same8)

    @api.constrains('subcon_estimation_ids')
    def _check_exist_subcon_2(self):
        exist_section_subcon_list_subcon = []
        for line10 in self.subcon_estimation_ids:
            same8 = str(line10.project_scope.id) + ' - ' + str(line10.section_name.id) + ' - ' + str(line10.variable.id)
            if (same8 in exist_section_subcon_list_subcon):
                raise ValidationError(
                    _('The subcon "%s" already exists in the section "%s", please change the Subcon.' % (
                    (line10.variable.name), (line10.section_name.name))))
            exist_section_subcon_list_subcon.append(same8)


class MaterialEstimateTemplate(models.Model):
    _name = 'material.estimate.template'
    _description = 'BOQ Material Estimate Template'
    _order = 'sequence'
    _check_company_auto = True

    material_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment')
    ], string="Type", default='material', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    subtotal = fields.Float('Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='material_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description', required=True)
    quantity = fields.Float('Quantity', default=0.0)
    coefficient = fields.Float('Coeff', default=1.0)
    unit_price = fields.Float('Unit Price', default=0.0)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.product_id:
                section_id = rec.material_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
            }

    @api.depends('material_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.material_id.section_ids:
                    for line in rec.material_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        # prevent update if user select the same data
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                    'description': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        # prevent update if user select the same data
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False
            self.unit_price = False
            self.group_of_product = False

    @api.depends('material_id.material_estimation_ids', 'material_id.material_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.material_id.material_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            price = (line.quantity * line.unit_price)
            line.subtotal = price


class LabourEstimateTemplate(models.Model):
    _name = 'labour.estimate.template'
    _description = 'BOQ Labour Estimate Template'
    _order = 'sequence'
    _check_company_auto = True

    labour_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment')
    ], string="Type", default='labour', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    subtotal = fields.Float('Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='labour_id.company_id', string='Company', readonly=True)
    description = fields.Text('Description', required=True)
    quantity = fields.Float('Quantity', default=0.0)
    unit_price = fields.Float('Unit Price', default=0.0)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    contractors = fields.Integer('Contractors', default=1, required=True)
    time = fields.Integer('Time', default=1, required=True)
    coefficient = fields.Float('Coeff', default=1.0)

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.product_id:
                section_id = rec.labour_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.time = rec.coefficient * s.quantity

    @api.onchange('contractors', 'time', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            quantity = (line.contractors * line.time)
            line.quantity = quantity
            if line.variable_ref:
                variable_estimate = self.env['variable.estimate'].search(
                    [('variable_name', '=', line.variable_ref.id), ('project_scope', '=', line.project_scope.id),
                     ('section_name', '=', line.section_name.id)], limit=1)
                line.quantity = line.quantity * variable_estimate.variable_quantity
            price = (quantity * line.unit_price)
            line.subtotal = price

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', 'in', ['product', 'service'])]}
            }

    @api.depends('labour_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.labour_id.section_ids:
                    for line in rec.labour_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False
            self.unit_price = False
            self.group_of_product = False

    @api.depends('labour_id.labour_estimation_ids', 'labour_id.labour_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.labour_id.labour_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id


class OverheadEstimateTemplate(models.Model):
    _name = 'overhead.estimate.template'
    _description = 'BOQ Overhead Estimate Template'
    _order = 'sequence'
    _check_company_auto = True

    overhead_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment')
    ], string="Type", default='overhead', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    description = fields.Text(string="Description", required=True)
    subtotal = fields.Float('Subtotal', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='overhead_id.company_id', string='Company', readonly=True)
    quantity = fields.Float('Quantity', default=0.0)
    coefficient = fields.Float('Coeff', default=1.0)
    unit_price = fields.Float('Unit Price', defaut=0.0)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    overhead_catagory = fields.Selection([
        ('product', 'Product'),
        ('petty cash', 'Petty Cash'),
        ('cash advance', 'Cash Advance'),
        ('fuel', 'Fuel'),
    ], string='Overhead Catagory', required=False)

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.product_id:
                section_id = rec.overhead_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('overhead_catagory', 'group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            if rec.overhead_catagory in ('product','fuel'):
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'product')]}
                }
            else:
                return {
                    'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'consu')]}
                }

    @api.depends('overhead_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.overhead_id.section_ids:
                    for line in rec.overhead_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'overhead_catagory': False,
                    'product_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'overhead_catagory': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'overhead_catagory': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'overhead_catagory': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'overhead_catagory': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'overhead_catagory': False,
                'product_id': False,
            })

    @api.onchange('overhead_catagory')
    def _onchange_overhead_catagory_handling(self):
        if self._origin.overhead_catagory:
            if self._origin.overhead_catagory != self.overhead_catagory:
                self.update({
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False
            self.unit_price = False
            self.group_of_product = False

    @api.depends('overhead_id.overhead_estimation_ids', 'overhead_id.overhead_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.overhead_id.overhead_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            price = (line.quantity * line.unit_price)
            line.subtotal = price


class SubconEstimateTemplate(models.Model):
    _name = 'subcon.estimate.template'
    _description = 'BOQ Subcon Estimate Template'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('variable')
    def onchange_variable(self):
        if self.variable:
            self.uom_id = self.variable.variable_uom.id
            self.quantity = 1.0
            self.unit_price = self.variable.total_variable
            self.description = self.variable.name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False
            self.unit_price = False

    @api.depends('subcon_id.subcon_estimation_ids', 'subcon_id.subcon_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.subcon_id.subcon_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            price = (line.quantity * line.unit_price)
            line.subtotal = price

    sequence = fields.Integer(string="sequence", default=0)
    subcon_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment')
    ], string="Type", default='subcon', readonly=1)
    company_id = fields.Many2one(related='subcon_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float('Quantity', default=0.0)
    coefficient = fields.Float('Coeff', default=1.0)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure', )
    unit_price = fields.Float('Unit Price', default=0.0)
    subtotal = fields.Float('Subtotal', readonly=True)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    variable = fields.Many2one('variable.template', string='Subcon',
                               domain="[('variable_subcon', '=', True), ('company_id', '=', parent.company_id)]",
                               check_company=True, ondelete='restrict', required=True)
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")

    @api.onchange('coefficient', 'variable')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.variable:
                section_id = rec.subcon_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.depends('subcon_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.subcon_id.section_ids:
                    for line in rec.subcon_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'variable': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'variable': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'variable': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'variable': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'variable': False,
                })
        else:
            self.update({
                'variable': False,
            })


class InternalAssetsEstimateTemplate(models.Model):
    _name = 'internal.assets.estimate.template'
    _description = "Assets"
    _order = 'sequence'

    asset_job_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment'),
        ('asset', 'Asset'),
    ], string="Type", default='asset', readonly=1)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category', required=True)
    asset_id = fields.Many2one('maintenance.equipment', string='Asset', required=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float('Quantity', default=0.00, required=True)
    coefficient = fields.Float('Coeff', default=1.0)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price', default=0.00, required=True)
    subtotal = fields.Float(string='Subtotal', default=0.00, compute="_compute_subtotal")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    company_id = fields.Many2one(related='asset_job_id.company_id', string='Company', readonly=True)

    @api.onchange('coefficient', 'asset_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.asset_id:
                section_id = rec.asset_job_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('asset_id')
    def onchange_asset_id(self):
        if self.asset_id:
            self.quantity = 1.0
            self.description = self.asset_id.display_name
        else:
            self.description = False
            self.quantity = False

    @api.depends('asset_job_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.asset_job_id.section_ids:
                    for line in rec.asset_job_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.depends('asset_job_id.asset_estimation_ids', 'asset_job_id.asset_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.asset_job_id.asset_estimation_ids:
                no += 1
                l.sr_no = no

    @api.onchange('asset_category_id')
    def onchange_asset_category(self):
        if self.asset_category_id:
            asset = self.env['maintenance.equipment'].sudo().search(
                [('category_id.id', '=', self.asset_category_id.id)])
            # self.asset_id = asset.id
            return {'domain': {'asset_id': [('id', 'in', asset.ids)]}}

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for rec in self:
            qty = rec.quantity
            unit_price = rec.unit_price
            rec.subtotal = qty * unit_price

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('asset_id')
    def _onchange_uom_asset_id(self):
        for rec in self:
            domain = self.env['uom.category'].search([('name', '=', 'Working Time')], limit=1)
            if rec.asset_id:
                if domain:
                    return {
                        'domain': {'uom_id': [('category_id', '=', domain.id)]}
                    }
                else:
                    return {
                        'domain': {'uom_id': []}
                    }
            else:
                return {
                    'domain': {'uom_id': []}
                }

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'asset_category_id': False,
                    'asset_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'asset_category_id': False,
                'asset_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'asset_id': False,
                    'asset_category_id': False,
                })
        else:
            self.update({
                'asset_id': False,
                'asset_category_id': False,
            })


class EquipmentEstimateTemplate(models.Model):
    _name = 'equipment.estimate.template'
    _description = 'BOQ Equipment Estimate Template'
    _order = 'sequence'
    _check_company_auto = True

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.uom_id = self.product_id.uom_id.id
            self.quantity = 1.0
            self.unit_price = self.product_id.list_price
            self.description = self.product_id.display_name
        else:
            self.description = False
            self.uom_id = False
            self.quantity = False
            self.unit_price = False
            self.group_of_product = False

    @api.depends('equipment_id.equipment_estimation_ids', 'equipment_id.equipment_estimation_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.equipment_id.equipment_estimation_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.onchange('quantity', 'unit_price')
    def onchange_quantity(self):
        price = 0.0
        for line in self:
            price = (line.quantity * line.unit_price)
            line.subtotal = price

    sequence = fields.Integer(string="sequence", default=0)
    equipment_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    type = fields.Selection([
        ('material', 'Material'),
        ('labour', 'Labour'),
        ('subcon', 'Subcon'),
        ('overhead', 'Overhead'),
        ('equipment', 'Equipment')
    ], string="Type", default='equipment', readonly=1)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    company_id = fields.Many2one(related='equipment_id.company_id', string='Company', readonly=True)
    description = fields.Text(string="Description", required=True)
    quantity = fields.Float('Quantity', default=0.0)
    coefficient = fields.Float('Coeff', default=1.0)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure', )
    unit_price = fields.Float('Unit Price', default=0.0)
    subtotal = fields.Float('Subtotal', readonly=True)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', 'Group of Product', required=True,
                                       domain="[('company_id','=',parent.company_id)]")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')
    project_scope_computed = fields.Many2many('project.scope.line', string="computed scope lines")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')

    @api.onchange('coefficient', 'product_id')
    def _onchange_coefficient(self):
        for rec in self:
            if rec.coefficient <= 0: return
            if rec.product_id:
                section_id = rec.equipment_id.section_ids.filtered(lambda x: x.section_name.id == rec.section_name.id and x.project_scope.id == rec.project_scope.id)
                for s in section_id:
                    rec.quantity = rec.coefficient * s.quantity

    @api.onchange('group_of_product')
    def _onchange_group_of_product(self):
        for rec in self:
            group_of_product = rec.group_of_product.id if rec.group_of_product else False
            return {
                'domain': {'product_id': [('group_of_product', '=', group_of_product), ('type', '=', 'asset')]}
            }

    @api.depends('equipment_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.equipment_id.section_ids:
                    for line in rec.equipment_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_ref': False,
                    'group_of_product': False,
                    'product_id': False,
                })
        else:
            self.update({
                'variable_ref': False,
                'group_of_product': False,
                'product_id': False,
            })

    @api.onchange('variable_ref')
    def _onchange_variable_handling(self):
        if self._origin.variable_ref._origin.id:
            if self._origin.variable_ref._origin.id != self.variable_ref.id:
                self.update({
                    'group_of_product': False,
                    'product_id': False,

                })
        else:
            self.update({
                'group_of_product': False,
                'product_id': False,

            })

    @api.onchange('group_of_product')
    def _onchange_group_of_product_handling(self):
        if self.product_id and self.group_of_product:
            if self.group_of_product.id not in self.product_id.group_of_product.ids:
                self.update({
                    'product_id': False,
                })


class ProjectScopeEstimateTemplate(models.Model):
    _name = 'project.scope.estimate.template'
    _rec_name = 'project_scope'
    _order = 'sequence'

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('scope_id.project_scope_ids', 'scope_id.project_scope_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.scope_id.project_scope_ids:
                no += 1
                l.sr_no = no

    # @api.onchange('project_scope')
    # def project_scope_ref(self):
    #     if self.project_scope:
    #         self.description = self.project_scope.scope_description
    #     else:
    #         self.description = False

    @api.depends('scope_id.material_estimation_ids', 'scope_id.labour_estimation_ids',
                 'scope_id.overhead_estimation_ids', 'scope_id.subcon_estimation_ids',
                 'scope_id.equipment_estimation_ids', 'scope_id.asset_estimation_ids',
                 'scope_id.material_estimation_ids.subtotal', 'scope_id.labour_estimation_ids.subtotal',
                 'scope_id.overhead_estimation_ids.subtotal', 'scope_id.subcon_estimation_ids.subtotal',
                 'scope_id.equipment_estimation_ids.subtotal', 'scope_id.asset_estimation_ids.subtotal')
    def _amount_total(self):
        for scope in self:
            total_subtotal = 0.0
            material_ids = scope.scope_id.material_estimation_ids.filtered(
                lambda m: m.project_scope.id == scope.project_scope.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal
            labour_ids = scope.scope_id.labour_estimation_ids.filtered(
                lambda l: l.project_scope.id == scope.project_scope.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal
            overhead_ids = scope.scope_id.overhead_estimation_ids.filtered(
                lambda o: o.project_scope.id == scope.project_scope.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal
            subcon_ids = scope.scope_id.subcon_estimation_ids.filtered(
                lambda s: s.project_scope.id == scope.project_scope.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal
            asset_ids = scope.scope_id.asset_estimation_ids.filtered(
                lambda e: e.project_scope.id == scope.project_scope.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal
            equipment_ids = scope.scope_id.equipment_estimation_ids.filtered(
                lambda e: e.project_scope.id == scope.project_scope.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal

            scope.subtotal = total_subtotal

    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    scope_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    description = fields.Text(string='Description')
    subtotal = fields.Float(string='Subtotal', compute="_amount_total")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='scope_id.company_id', string='Company', readonly=True)


class SectionEstimateTemplate(models.Model):
    _name = 'section.estimate.template'
    _order = 'sequence'
    _rec_name = 'section_name'

    @api.depends('section_id.section_ids', 'section_id.section_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.section_id.section_ids:
                no += 1
                l.sr_no = no

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('section_id.material_estimation_ids', 'section_id.labour_estimation_ids',
                 'section_id.overhead_estimation_ids', 'section_id.subcon_estimation_ids',
                 'section_id.equipment_estimation_ids', 'section_id.asset_estimation_ids',
                 'section_id.material_estimation_ids.subtotal', 'section_id.labour_estimation_ids.subtotal',
                 'section_id.overhead_estimation_ids.subtotal', 'section_id.subcon_estimation_ids.subtotal',
                 'section_id.equipment_estimation_ids.subtotal', 'section_id.asset_estimation_ids.subtotal')
    def _amount_total_section(self):
        for section in self:
            total_subtotal = 0.0
            material_ids = section.section_id.material_estimation_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section_name.id)
            for mat in material_ids:
                total_subtotal += mat.subtotal
            labour_ids = section.section_id.labour_estimation_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section_name.id)
            for lab in labour_ids:
                total_subtotal += lab.subtotal
            overhead_ids = section.section_id.overhead_estimation_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section_name.id)
            for ove in overhead_ids:
                total_subtotal += ove.subtotal
            subcon_ids = section.section_id.subcon_estimation_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section_name.id)
            for sub in subcon_ids:
                total_subtotal += sub.subtotal
            asset_ids = section.section_id.asset_estimation_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section_name.id)
            for ass in asset_ids:
                total_subtotal += ass.subtotal
            equipment_ids = section.section_id.equipment_estimation_ids.filtered(
                lambda m: m.project_scope.id == section.project_scope.id and
                          m.section_name.id == section.section_name.id)
            for equ in equipment_ids:
                total_subtotal += equ.subtotal

            section.subtotal = total_subtotal

    section_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    description = fields.Text(string='Description')
    quantity = fields.Float('Quantity', default=1)
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    subtotal = fields.Float(string='Subtotal', compute="_amount_total_section")
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='section_id.company_id', string='Company', readonly=True)

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'description': False,
                    'subtotal': False,
                    'quantity': 1.0,
                    'uom_id': False,
                })
        else:
            self.update({
                'section_name': False,
                'description': False,
                'subtotal': False,
                'quantity': 1.0,
                'uom_id': False,
            })

    @api.onchange('section_name')
    def _onchange_section_name_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'description': False,
                    'subtotal': False,
                    'quantity': 1.0,
                    'uom_id': False,
                })
                section_values = []

                for section in self.section_id.section_ids:
                    section_values.append(section.section_name.id)
                for variable in self.section_id.variable_ids:
                    if variable.section_name.id not in section_values:
                        self.section_id.update({
                            'variable_ids': (2, variable.id, 0)
                        })


class VariableEstimateTemplate(models.Model):
    _name = 'variable.estimate.template'
    _description = 'BOQ Variable Estimate Template'
    _order = 'sequence'
    _rec_name = 'variable_name'

    @api.depends('variable_id.variable_ids', 'variable_id.variable_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.variable_id.variable_ids:
                no += 1
                l.sr_no = no

    @api.onchange('project_scope', 'section_name', 'variable_name', 'variable_quantity')
    def onchange_quantity(self):
        self.write({'onchange_pass': False})

    @api.onchange('variable_name')
    def onchange_variable_name(self):
        res = {}
        if not self.variable_name:
            return res
        self.variable_uom = self.variable_name.variable_uom.id
        self.variable_quantity = 1.0
        self.total_variable = self.variable_name.total_variable

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    variable_id = fields.Many2one('job.estimate.template', string="BOQ Template", ondelete='cascade')
    sequence = fields.Integer(string="sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section_name = fields.Many2one('section.line', string='Section', required=True)
    variable_name = fields.Many2one('variable.template', string='Variable', required=True,
                                    domain="[('variable_subcon', '=', False), ('company_id', '=', parent.company_id)]")
    variable_quantity = fields.Float(string='Quantity', default=1.0)
    variable_uom = fields.Many2one('uom.uom', string="Unit Of Measure")
    total_variable = fields.Float(string='Total Variable', readonly=True)
    subtotal = fields.Float(string='Subtotal')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    company_id = fields.Many2one(related='variable_id.company_id', string='Company', readonly=True)
    onchange_pass = fields.Boolean(string="Pass", default=False)
    project_section_computed = fields.Many2many('section.line', string="computed section lines",
                                                compute='get_section_lines')

    @api.depends('variable_id.section_ids', 'project_scope')
    def get_section_lines(self):
        for rec in self:
            section = []
            if rec.project_scope:
                if rec.variable_id.section_ids:
                    for line in rec.variable_id.section_ids:
                        if rec.project_scope.id == line.project_scope.id:
                            section.append(line.section_name.id)
                    rec.project_section_computed = [(6, 0, section)]
                else:
                    rec.project_section_computed = [(6, 0, [])]
            else:
                rec.project_section_computed = [(6, 0, [])]

    @api.onchange('project_scope')
    def _onchange_project_scope_handling(self):
        if self._origin.project_scope._origin.id:
            if self._origin.project_scope._origin.id != self.project_scope.id:
                self.update({
                    'section_name': False,
                    'variable_name': False,
                })
        else:
            self.update({
                'section_name': False,
                'variable_name': False,
            })

    @api.onchange('section_name')
    def onchange_section_handling(self):
        if self._origin.section_name._origin.id:
            if self._origin.section_name._origin.id != self.section_name.id:
                self.update({
                    'variable_name': False,
                })
        else:
            self.update({
                'variable_name': False,
            })

    @api.onchange('variable_name')
    def onchange_variable_name(self):
        if self.variable_name:
            self.variable_quantity = 1.0
            self.variable_uom = self.variable_name.variable_uom.id
            self.total_variable = self.variable_name.total_variable
        else:
            self.variable_quantity = 1.0
            self.variable_uom = False
            self.total_variable = False

    def unlink(self):
        res = super(VariableEstimateTemplate, self).unlink()
        self.clear_caches()
        return res
