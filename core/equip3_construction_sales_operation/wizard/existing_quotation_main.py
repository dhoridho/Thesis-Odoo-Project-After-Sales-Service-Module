import copy
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo import tools


class JobEstimateExistingQuotation(models.TransientModel):
    _name = 'job.estimate.existing.quotation.const'
    _description = 'Existing Quotation For Main Contract'

    job_estimate_id = fields.Many2one('job.estimate', string='BOQ')
    contract_category = fields.Selection(related='job_estimate_id.contract_category', string="Contract Category")
    so_cons_id = fields.Many2one("sale.order.const", string="Quotation")
    customer_id = fields.Many2one("res.partner", string="Customer",)
    project_id = fields.Many2one("project.project", string="Project")
    project_scope_wiz = fields.One2many("job.estimate.existing.line.scope", "wiz_id", string="Project Scope")
    section_wiz = fields.One2many("job.estimate.existing.line.section", "wiz_id", string="Section")
    variable_wiz = fields.One2many("job.estimate.existing.line.variable", "wiz_id", "Variable")
    material_estimation_wiz = fields.One2many("job.estimate.existing.line.material", "wiz_id", string="Material Estimation")
    labour_estimation_wiz = fields.One2many("job.estimate.existing.line.labour", "wiz_id", string="Labour Estimation")
    subcon_estimation_wiz = fields.One2many("job.estimate.existing.line.subcon", "wiz_id", string="Subcon Estimation")
    internal_asset_wiz = fields.One2many("job.estimate.existing.line.asset", "wiz_id", string="Internal Asset Estimation")
    equipment_estimation_wiz = fields.One2many("job.estimate.existing.line.equipment", "wiz_id", string="Equipment Lease Estimation")
    overhead_estimation_wiz = fields.One2many("job.estimate.existing.line.overhead",  "wiz_id",  string="Overhead Estimation")
    currency_id = fields.Many2one(relate='job_estimate_id.currency_id', string='Currency')
    total_variation_order_material = fields.Monetary(string='Total Variation Order Material',
                                                   compute="_compute_total_variation_order",
                                                   )
    total_variation_order_labour = fields.Monetary(string='Total Variation Order Labour',
                                                   compute="_compute_total_variation_order",
                                                   )
    total_variation_order_overhead = fields.Monetary(string='Total Variation Order Overhead',
                                                     compute="_compute_total_variation_order",
                                                     )
    total_variation_order_asset = fields.Monetary(string='Total Variation Order Internal Asset',
                                                  compute="_compute_total_variation_order",
                                                  )
    total_variation_order_equipment = fields.Monetary(string='Total Variation Order Equipment',
                                                      compute="_compute_total_variation_order",
                                                      )
    total_variation_order_subcon = fields.Monetary(string='Total Variation Order SUbcon',
                                                   compute="_compute_total_variation_order",
                                                   )
    total_variation_order = fields.Monetary(string='Total Variation Order', compute="_compute_total_variation_order")

    @api.depends('material_estimation_wiz', 'labour_estimation_wiz', 'subcon_estimation_wiz', 'overhead_estimation_wiz',
                 'equipment_estimation_wiz', 'internal_asset_wiz')
    def _compute_total_variation_order(self):
        for rec in self:
            total = 0
            total_material = 0
            total_labour = 0
            total_subcon = 0
            total_overhead = 0
            total_equipment = 0
            total_internal_assets = 0
            if rec.contract_category == 'var':
                total_material = sum((material.quantity * material.unit_price) for material in rec.material_estimation_wiz if material.is_active)
                total_labour = 0
                total_subcon = sum((subcon.quantity * subcon.unit_price) for subcon in rec.subcon_estimation_wiz if subcon.is_active)
                total_overhead = sum((overhead.quantity * overhead.unit_price) for overhead in rec.overhead_estimation_wiz if overhead.is_active)
                total_equipment = sum((equipment.quantity * equipment.unit_price) for equipment in rec.equipment_estimation_wiz if equipment.is_active)
                total_internal_assets = sum((asset.quantity * asset.unit_price) for asset in rec.internal_asset_wiz if asset.is_active)

                for labour in rec.labour_estimation_wiz:
                    if labour.is_active:
                        if labour.contractors == 0:
                            total_labour += labour.unit_price * labour.time
                        elif labour.time == 0:
                            total_labour += labour.unit_price * labour.contractors
                        else:
                            total_labour += labour.unit_price * labour.time * labour.contractors

                total = total_material + total_labour + total_subcon + total_overhead + total_equipment + total_internal_assets
            rec.total_variation_order = total
            rec.total_variation_order_material = total_material
            rec.total_variation_order_labour = total_labour
            rec.total_variation_order_subcon = total_subcon
            rec.total_variation_order_overhead = total_overhead
            rec.total_variation_order_equipment = total_equipment
            rec.total_variation_order_asset = total_internal_assets

    @api.onchange('contract_category')
    def _onchange_domain_so_cons_id(self):
        res = {}
        for rec in self:
            if rec.contract_category == 'main':
                res['domain'] = {'so_cons_id': [('project_id', '=', rec.project_id.id), ('partner_id', '=', rec.customer_id.id),('contract_category', '=', ['main']), ('state', '=', 'draft')]}
            elif rec.contract_category == 'var':
                res['domain'] = {'so_cons_id': [('project_id', '=', rec.project_id.id),('partner_id', '=', rec.customer_id.id),('contract_category', '=', ['var']), ('state', '=', 'draft')]}
        return res 

    @api.onchange('job_estimate_id')
    def _onchange_job_estimate_id(self):
        if self.job_estimate_id and self.job_estimate_id.contract_category == 'main':
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

            # variable = []
            # self.variable_wiz = False
            # if job.variable_ids:
            #     for var in job.variable_ids:
            #         variable.append((0, 0, {
            #             'project_scope': var.project_scope.id or False,
            #             'section_name': var.section_name.id or False,
            #             'variable_name': var.variable_name.id or False,
            #             'variable_quantity': var.variable_quantity,
            #             'variable_uom': var.variable_uom.id or False,
            #             'subtotal': var.subtotal,
            #         }))
            
            # if len(variable) > 0:
            #     self.variable_wiz = variable
            
            material_lines = []
            self.material_estimation_wiz = False
            if job.material_estimation_ids:
                for material in job.material_estimation_ids:
                    material_lines.append((0, 0, {
                        'project_scope': material.project_scope.id or False,
                        'section_name': material.section_name.id or False,
                        # 'variable_ref': material.variable_ref.id or False,
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
                    labour_lines.append((0, 0, {
                        'project_scope': labour.project_scope.id or False,
                        'section_name': labour.section_name.id or False,
                        # 'variable_ref': labour.variable_ref.id or False,
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
                    overhead_lines.append((0, 0, {
                        'project_scope': overhead.project_scope.id or False,
                        'section_name': overhead.section_name.id or False,
                        'overhead_catagory': overhead.overhead_catagory or False,
                        # 'variable_ref': overhead.variable_ref.id or False,
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
                    asset_lines.append((0, 0, {
                        'project_scope': asset.project_scope.id or False,
                        'section_name': asset.section_name.id or False,
                        # 'variable_ref': asset.variable_ref.id or False,
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
                    equipment_lines.append((0, 0, {
                        'project_scope': equipment.project_scope.id or False,
                        'section_name': equipment.section_name.id or False,
                        # 'variable_ref': equipment.variable_ref.id or False,
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
                    subcon_lines.append((0, 0, {
                        'project_scope': subcon.project_scope.id or False,
                        'section_name': subcon.section_name.id or False,
                        # 'variable_ref': subcon.variable_ref.id or False,
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

    @api.onchange('project_scope_wiz')
    def _onchange_project_scope_wiz(self):
        for scope in self.project_scope_wiz:
            if not scope.is_active:
                for section in self.section_wiz:
                    if section.project_scope.id == scope.project_scope.id:
                        section.is_active = False
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == scope.project_scope.id:
                #         variable.is_active = False
                for material in self.material_estimation_wiz:
                    if material.project_scope.id == scope.project_scope.id:
                        material.is_active = False
                for labour in self.labour_estimation_wiz:
                    if labour.project_scope.id == scope.project_scope.id:
                        labour.is_active = False
                for overhead in self.overhead_estimation_wiz:
                    if overhead.project_scope.id == scope.project_scope.id:
                        overhead.is_active = False
                for asset in self.internal_asset_wiz:
                    if asset.project_scope.id == scope.project_scope.id:
                        asset.is_active = False
                for equipment in self.equipment_estimation_wiz:
                    if equipment.project_scope.id == scope.project_scope.id:
                        equipment.is_active = False
                for subcon in self.subcon_estimation_wiz:
                    if subcon.project_scope.id == scope.project_scope.id:
                        subcon.is_active = False
            
    @api.onchange('section_wiz')
    def _onchange_section_wiz(self):
        for section in self.section_wiz:
            if not section.is_active:
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == section.project_scope.id \
                #         and variable.section_name.id == section.section_name.id:
                #         variable.is_active = False
                for material in self.material_estimation_wiz:
                    if material.project_scope.id == section.project_scope.id \
                        and material.section_name.id == section.section_name.id:
                        material.is_active = False
                for labour in self.labour_estimation_wiz:
                    if labour.project_scope.id == section.project_scope.id \
                        and labour.section_name.id == section.section_name.id:
                        labour.is_active = False
                for overhead in self.overhead_estimation_wiz:
                    if overhead.project_scope.id == section.project_scope.id \
                        and overhead.section_name.id == section.section_name.id:
                        overhead.is_active = False
                for asset in self.internal_asset_wiz:
                    if asset.project_scope.id == section.project_scope.id \
                        and asset.section_name.id == section.section_name.id:
                        asset.is_active = False
                for equipment in self.equipment_estimation_wiz:
                    if equipment.project_scope.id == section.project_scope.id \
                        and equipment.section_name.id == section.section_name.id:
                        equipment.is_active = False
                for subcon in self.subcon_estimation_wiz:
                    if subcon.project_scope.id == section.project_scope.id \
                        and subcon.section_name.id == section.section_name.id:
                        subcon.is_active = False
            else:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == section.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                

    # @api.onchange('variable_wiz')
    # def _onchange_variable_wiz(self):
    #     for variable in self.variable_wiz:
    #         if not variable.is_active:
    #             for material in self.material_estimation_wiz:
    #                 if material.project_scope.id == variable.project_scope.id \
    #                     and material.section_name.id == variable.section_name.id \
    #                     and material.variable_ref.id == variable.variable_name.id:
    #                     material.is_active = False
    #             for labour in self.labour_estimation_wiz:
    #                 if labour.project_scope.id == variable.project_scope.id \
    #                     and labour.section_name.id == variable.section_name.id \
    #                     and labour.variable_ref.id == variable.variable_name.id:
    #                     labour.is_active = False
    #             for overhead in self.overhead_estimation_wiz:
    #                 if overhead.project_scope.id == variable.project_scope.id \
    #                     and overhead.section_name.id == variable.section_name.id \
    #                     and overhead.variable_ref.id == variable.variable_name.id:
    #                     overhead.is_active = False
    #             for asset in self.internal_asset_wiz:
    #                 if asset.project_scope.id == variable.project_scope.id \
    #                     and asset.section_name.id == variable.section_name.id \
    #                     and asset.variable_ref.id == variable.variable_name.id:
    #                     asset.is_active = False
    #             for equipment in self.equipment_estimation_wiz:
    #                 if equipment.project_scope.id == variable.project_scope.id \
    #                     and equipment.section_name.id == variable.section_name.id \
    #                     and equipment.variable_ref.id == variable.variable_name.id:
    #                     equipment.is_active = False
    #             for subcon in self.subcon_estimation_wiz:
    #                 if subcon.project_scope.id == variable.project_scope.id \
    #                     and subcon.section_name.id == variable.section_name.id \
    #                     and subcon.variable_ref.id == variable.variable_name.id:
    #                     subcon.is_active = False
    #         else:
    #             for scope in self.project_scope_wiz:
    #                 if scope.project_scope.id == variable.project_scope.id and scope.is_active == False:
    #                     raise ValidationError(_(f"Project scope '{scope.project_scope.name}' in the project scope tab is inactive. You need to activate it first."))
    #             for section in self.section_wiz:
    #                 if section.project_scope.id == variable.project_scope.id \
    #                     and section.section_name.id == variable.section_name.id and section.is_active == False:
    #                     raise ValidationError(_(f"Section '{section.section_name.name}' in the section tab is inactive. You need to activate it first."))

                
    
    @api.onchange('material_estimation_wiz')
    def _onchange_material_estimation_wiz(self):
        for material in self.material_estimation_wiz:
            if material.is_active:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == material.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == material.project_scope.id \
                        and section.section_name.id == material.section_name.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == material.project_scope.id \
                #         and variable.section_name.id == material.section_name.id \
                #         and variable.variable_name.id == material.variable_ref.id and variable.is_active == False:
                #         raise ValidationError(_(f"Variable '{variable.variable_name.name}' in the variable tab is inactive. You need to activate it first."))
    
    @api.onchange('labour_estimation_wiz')
    def _onchange_labour_estimation_wiz(self):
        for labour in self.labour_estimation_wiz:
            if labour.is_active:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == labour.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == labour.project_scope.id \
                        and section.section_name.id == labour.section_name.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == labour.project_scope.id \
                #         and variable.section_name.id == labour.section_name.id \
                #         and variable.variable_name.id == labour.variable_ref.id and variable.is_active == False:
                #         raise ValidationError(_(f"Variable '{variable.variable_name.name}' in the variable tab is inactive. You need to activate it first."))
    
    @api.onchange('overhead_estimation_wiz')
    def _onchange_overhead_estimation_wiz(self):
        for overhead in self.overhead_estimation_wiz:
            if overhead.is_active:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == overhead.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == overhead.project_scope.id \
                        and section.section_name.id == overhead.section_name.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == overhead.project_scope.id \
                #         and variable.section_name.id == overhead.section_name.id \
                #         and variable.variable_name.id == overhead.variable_ref.id and variable.is_active == False:
                #         raise ValidationError(_(f"Variable '{variable.variable_name.name}' in the variable tab is inactive. You need to activate it first."))

    @api.onchange('internal_asset_wiz')
    def _onchange_internal_asset_wiz(self):
        for asset in self.internal_asset_wiz:
            if asset.is_active:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == asset.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == asset.project_scope.id \
                        and section.section_name.id == asset.section_name.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == asset.project_scope.id \
                #         and variable.section_name.id == asset.section_name.id \
                #         and variable.variable_name.id == asset.variable_ref.id and variable.is_active == False:
                #         raise ValidationError(_(f"Variable '{variable.variable_name.name}' in the variable tab is inactive. You need to activate it first."))
    
    @api.onchange('equipment_estimation_wiz')
    def _onchange_equipment_estimation_wiz(self):
        for equipment in self.equipment_estimation_wiz:
            if equipment.is_active:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == equipment.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == equipment.project_scope.id \
                        and section.section_name.id == equipment.section_name.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == equipment.project_scope.id \
                #         and variable.section_name.id == equipment.section_name.id \
                #         and variable.variable_name.id == equipment.variable_ref.id and variable.is_active == False:
                #         raise ValidationError(_(f"Variable '{variable.variable_name.name}' in the variable tab is inactive. You need to activate it first."))
    
    @api.onchange('subcon_estimation_wiz')
    def _onchange_subcon_estimation_wiz(self):
        for subcon in self.subcon_estimation_wiz:
            if subcon.is_active:
                for scope in self.project_scope_wiz:
                    if scope.project_scope.id == subcon.project_scope.id and scope.is_active == False:
                        raise ValidationError(_("Project scope '%s' in the project scope tab is inactive. You need to activate it first.") % scope.project_scope.name)
                for section in self.section_wiz:
                    if section.project_scope.id == subcon.project_scope.id \
                        and section.section_name.id == subcon.section_name.id and section.is_active == False:
                        raise ValidationError(_("Section '%s' in the section tab is inactive. You need to activate it first.") % section.section_name.name)
                # for variable in self.variable_wiz:
                #     if variable.project_scope.id == subcon.project_scope.id \
                #         and variable.section_name.id == subcon.section_name.id \
                #         and variable.variable_name.id == subcon.variable_ref.id and variable.is_active == False:
                #         raise ValidationError(_(f"Variable '{variable.variable_name.name}' in the variable tab is inactive. You need to activate it first."))

    def action_confirm(self, is_set_projects_type=False, project_template_id=False):
        ctx = self._context
        if self.contract_category == 'main':
            for rec in self:
                is_wizard = True
                sale_order_cons = rec.so_cons_id
                project_scope_ids = []
                section_ids = []
                # variable_ids = []
                material_line_ids = []
                labour_line_ids = []
                overhead_line_ids = []
                internal_asset_line_ids = []
                equipment_line_ids = []
                subcon_line_ids = []

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

                # if rec.variable_wiz:
                #     for variable in rec.variable_wiz.filtered(lambda x: x.is_active):
                #         variable_ids.append(
                #             (0, 0,
                #             {
                #                 # "job_estimate_id": variable.job_estimate_id.id,
                #                 "project_scope": variable.project_scope.id or False,
                #                 "section": variable.section_name.id or False,
                #                 "variable": variable.variable_name.id or False,
                #                 "quantity": variable.variable_quantity,
                #                 "uom_id": variable.variable_uom.id or False,
                #                 "subtotal_variable": variable.subtotal,
                #             },
                #             )
                #         )

                if rec.material_estimation_wiz:
                    for material in rec.material_estimation_wiz.filtered(lambda x: x.is_active):
                        material_line_ids.append(
                            (0, 0,
                            {
                                "project_scope": material.project_scope.id or False,
                                "section_name": material.section_name.id or False,
                                # "variable_ref": material.variable_ref.id or False,
                                "type": "material",
                                "group_of_product": material.group_of_product.id or False,
                                "material_id": material.product_id.id or False,
                                "description": material.description,
                                "analytic_idz": [(6, 0, material.analytic_ids.ids)] or False,
                                'budget_quantity': material.budget_quantity,
                                "current_quantity": material.current_quantity,
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
                                # "variable_ref": labour.variable_ref.id or False,
                                "type": "labour",
                                "group_of_product": labour.group_of_product.id or False,
                                "labour_id": labour.product_id.id or False,
                                "description": labour.description,
                                "analytic_idz": [(6, 0, labour.analytic_ids.ids)] or False,
                                "budget_contractors": labour.budget_contractors,
                                "budget_time": labour.budget_time,
                                "current_contractors": labour.current_contractors,
                                "current_time": labour.current_time,
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
                                # "variable_ref": subcon.variable_ref.id or False,
                                "type": "subcon",
                                "subcon_id": subcon.variable.id or False,
                                "description": subcon.description,
                                "analytic_idz": [(6, 0, subcon.analytic_ids.ids)] or False,
                                'budget_quantity': subcon.budget_quantity,
                                "current_quantity": subcon.current_quantity,
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
                                # "variable_ref": internal_asset.variable_ref.id or False,
                                "type": "asset",
                                "asset_category_id": internal_asset.asset_category_id.id or False,
                                "asset_id": internal_asset.asset_id.id or False,
                                "description": internal_asset.description,
                                "analytic_idz": [(6, 0, internal_asset.analytic_ids.ids)] or False,
                                'budget_quantity': internal_asset.budget_quantity,
                                "current_quantity": internal_asset.current_quantity,
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
                                # "variable_ref": equipment.variable_ref.id or False,
                                "type": "equipment",
                                "group_of_product": equipment.group_of_product.id or False,
                                "equipment_id": equipment.product_id.id or False,
                                "description": equipment.description,
                                "analytic_idz": equipment.analytic_ids and [(6, 0, equipment.analytic_ids.ids)] or False,
                                'budget_quantity': equipment.budget_quantity,
                                "current_quantity": equipment.current_quantity,
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
                                # "variable_ref": overhead.variable_ref.id or False,
                                "type": "overhead",
                                "group_of_product": overhead.group_of_product.id or False,
                                "overhead_id": overhead.product_id.id or False,
                                "description": overhead.description,
                                "analytic_idz": [(6, 0, overhead.analytic_ids.ids)] or False,
                                'budget_quantity': overhead.budget_quantity,
                                "current_quantity": overhead.current_quantity,
                                "quantity": overhead.quantity,
                                "uom_id": overhead.uom_id.id or False,
                                "unit_price": overhead.unit_price,
                                "subtotal": overhead.subtotal,
                                "overhead_catagory": overhead.overhead_catagory,
                            },
                            )
                        )

                if sale_order_cons:
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
                    # variable_copy = copy.deepcopy(variable_ids)
                    # for i in variable_copy:
                    #     target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                    #     target_section = self.env['section.line'].search([('id', '=', i[2]['section'])])
                    #     target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable'])])
                    #     i[2]['project_scope'] = target_scope.name
                    #     i[2]['section'] = target_section.name
                    #     i[2]['variable'] = target_variable.name
                    material_copy = copy.deepcopy(material_line_ids)
                    for i in material_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        # target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        # i[2]['variable_ref'] = target_variable.name
                    labour_copy = copy.deepcopy(labour_line_ids)
                    for i in labour_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        # target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        # i[2]['variable_ref'] = target_variable.name
                    overhead_copy = copy.deepcopy(overhead_line_ids)
                    for i in overhead_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        # target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        # i[2]['variable_ref'] = target_variable.name
                    internal_copy = copy.deepcopy(internal_asset_line_ids)
                    for i in internal_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        # target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        # i[2]['variable_ref'] = target_variable.name
                    equipment_copy = copy.deepcopy(equipment_line_ids)
                    for i in equipment_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        # target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        # i[2]['variable_ref'] = target_variable.name
                    subcon_copy = copy.deepcopy(subcon_line_ids)
                    for i in subcon_copy:
                        target_scope = self.env['project.scope.line'].search([('id', '=', i[2]['project_scope'])])
                        target_section = self.env['section.line'].search([('id', '=', i[2]['section_name'])])
                        # target_variable = self.env['variable.template'].search([('id', '=', i[2]['variable_ref'])])
                        i[2]['project_scope'] = target_scope.name
                        i[2]['section_name'] = target_section.name
                        # i[2]['variable_ref'] = target_variable.name
                    scope_values = list(map(lambda x: (x[2].pop('subtotal_scope'), x[2])[1], project_scope_copy))
                    section_values = list(map(lambda x: (x[2].pop('subtotal_section'), x[2].pop('quantity'), x[2])[-1], section_copy))
                    # variable_values = list(map(lambda x: (x[2].pop('subtotal_variable'), x[2].pop('quantity'), x[2])[-1], variable_copy))
                    material_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], material_copy))
                    labour_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], labour_copy))
                    overhead_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], overhead_copy))
                    internal_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], internal_copy))
                    equipment_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], equipment_copy))
                    subcon_values = list(map(lambda x: (x[2].pop('subtotal'), x[2].pop('quantity'), x[2].pop('analytic_idz'), x[2])[-1], subcon_copy))

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

                        # exist_var_idx = []
                        # for var in sale_order_cons.variable_ids:
                        #     value = {
                        #         "project_scope": var.project_scope.name,
                        #         "section": var.section.name,
                        #         "variable": var.variable.name,
                        #         "uom_id": var.uom_id.id
                        #     }
                        #     for i in range(len(variable_values)):
                        #         if value == variable_values[i]:
                        #             var.subtotal_variable += variable_ids[i][2]['subtotal_variable']
                        #             var.quantity += variable_ids[i][2]['quantity']
                        #             if i not in exist_var_idx:
                        #                 exist_var_idx.append(i)
                        # exist_var_idx.sort(reverse=True)
                        # for j in exist_var_idx:
                        #     del variable_ids[j]

                        exist_mat_idx = []
                        for mat in sale_order_cons.material_line_ids:
                            value = {
                                "project_scope": mat.project_scope.name,
                                "section_name": mat.section_name.name,
                                # "variable_ref": mat.variable_ref.name,
                                "type": "material",
                                "group_of_product": mat.group_of_product.id,
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
                            value = {
                                "project_scope": lab.project_scope.name,
                                "section_name": lab.section_name.name,
                                # "variable_ref": lab.variable_ref.name,
                                "type": "labour",
                                "group_of_product": lab.group_of_product.id,
                                "labour_id": lab.labour_id.id,
                                "description": lab.description,
                                "contractors": lab.contractors,
                                "time": lab.time,
                                "uom_id": lab.uom_id.id,
                                "unit_price": labour.unit_price
                            }
                            for i in range(len(labour_values)):
                                if value == labour_values[i]:
                                    if value['unit_price'] > labour_line_ids[i][2]['unit_price']:
                                        labour_line_ids[i][2]['unit_price'] = value['unit_price']

                                    lab.subtotal += labour_line_ids[i][2]['subtotal']
                                    lab.quantity += labour_line_ids[i][2]['quantity']
                                    if i not in exist_lab_idx:
                                        exist_lab_idx.append(i)
                        exist_lab_idx.sort(reverse=True)
                        for j in exist_lab_idx:
                            del labour_line_ids[j]

                        exist_ov_idx = []
                        for ov in sale_order_cons.overhead_line_ids:
                            value = {
                                "project_scope": ov.project_scope.name,
                                "section_name": ov.section_name.name,
                                # "variable_ref": ov.variable_ref.name,
                                "type": "overhead",
                                "group_of_product": ov.group_of_product.id,
                                "overhead_id": ov.overhead_id.id,
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
                            value = {
                                "project_scope": asset.project_scope.name,
                                "section_name": asset.section_name.name,
                                # "variable_ref": asset.variable_ref.name,
                                "type": "asset",
                                "asset_category_id": asset.asset_category_id.id,
                                "asset_id": asset.asset_id.id,
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
                            value = {
                                "project_scope": eq.project_scope.name,
                                "section_name": eq.section_name.name,
                                # "variable_ref": eq.variable_ref.name,
                                "type": "equipment",
                                "group_of_product": eq.group_of_product.id,
                                "equipment_id": eq.equipment_id.id,
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
                            value = {
                                "project_scope": sub.project_scope.name,
                                "section_name": sub.section_name.name,
                                # "variable_ref": sub.variable_ref.name,
                                "type": "subcon",
                                "subcon_id": sub.subcon_id.id,
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
                        # if variable_ids:
                        #     sale_order_cons.variable_ids = variable_ids
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
                                'quotation_id': sale_order_cons,
                            })
                        context = ({'is_wizard': is_wizard})
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

                        # inexist_variable = []
                        # for var in sale_order_cons.variable_ids:
                        #     value = {
                        #         "project_scope": var.project_scope.name,
                        #         "section": var.section.name,
                        #         "variable": var.variable.name,
                        #         "uom_id": var.uom_id.id
                        #     }
                        #     if value not in variable_values:
                        #         inexist_variable.append((0, 0,
                        #         {
                        #             # "job_estimate_id": variable.job_estimate_id.id,
                        #             "project_scope": var.project_scope.id or False,
                        #             "section": var.section.id or False,
                        #             "variable": var.variable.id or False,
                        #             "quantity": var.quantity,
                        #             "uom_id": var.uom_id.id or False,
                        #             "subtotal_variable": var.subtotal_variable,
                        #         }))
                        #     else:
                        #         i = variable_values.index(value)
                        #         variable_ids[i][2]['subtotal_variable'] += var.subtotal_variable
                        #         variable_ids[i][2]['quantity'] += var.quantity
                        # variable_ids.extend(inexist_variable)

                        inexist_material = []
                        for mat in sale_order_cons.material_line_ids:
                            value = {
                                "project_scope": mat.project_scope.name,
                                "section_name": mat.section_name.name,
                                # "variable_ref": mat.variable_ref.name,
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
                                    # "variable_ref": mat.variable_ref.id or False,
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
                        material_line_ids.extend(inexist_material)

                        inexist_labour = []
                        for lab in sale_order_cons.labour_line_ids:
                            value = {
                                "project_scope": lab.project_scope.name,
                                "section_name": lab.section_name.name,
                                # "variable_ref": lab.variable_ref.name,
                                "type": "labour",
                                "group_of_product": lab.group_of_product.id,
                                "labour_id": lab.labour_id.id,
                                "description": lab.description,
                                "contractors": lab.contractors,
                                "time": lab.time,
                                "uom_id": lab.uom_id.id,
                                "unit_price": labour.unit_price
                            }
                            if value not in labour_values:
                                inexist_labour.append((0, 0,
                                {
                                    "project_scope": lab.project_scope.id or False,
                                    "section_name": lab.section_name.id or False,
                                    # "variable_ref": lab.variable_ref.id or False,
                                    "type": "labour",
                                    "group_of_product": lab.group_of_product.id or False,
                                    "labour_id": lab.labour_id.id or False,
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
                        labour_line_ids.extend(inexist_labour)

                        inexist_overhead = []
                        for ov in sale_order_cons.overhead_line_ids:
                            value = {
                                "project_scope": ov.project_scope.name,
                                "section_name": ov.section_name.name,
                                # "variable_ref": ov.variable_ref.name,
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
                                    # "variable_ref": ov.variable_ref.id or False,
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
                                # "variable_ref": asset.variable_ref.name,
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
                                    # "variable_ref": asset.variable_ref.id or False,
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
                                # "variable_ref": eq.variable_ref.name,
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
                                    # "variable_ref": eq.variable_ref.id or False,
                                    "type": "equipment",
                                    "group_of_product": eq.group_of_product.id or False,
                                    "equipment_id": eq.equipment_id.id or False,
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
                            value = {
                                "project_scope": sub.project_scope.name,
                                "section_name": sub.section_name.name,
                                # "variable_ref": sub.variable_ref.name,
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
                                    # "variable_ref": sub.variable_ref.id or False,
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
                            'default_job_references':[(4, rec.job_estimate_id.id)] + [(4, job.id) for job in sale_order_cons.job_references],
                            'default_project_id': rec.project_id.id,
                            'default_partner_id': rec.customer_id.id,
                            'default_project_scope_ids': project_scope_ids,
                            'default_section_ids': section_ids,
                            # 'default_variable_ids': variable_ids,
                            'default_material_line_ids': material_line_ids,
                            'default_labour_line_ids': labour_line_ids,
                            'default_overhead_line_ids': overhead_line_ids,
                            'default_internal_asset_line_ids': internal_asset_line_ids,
                            'default_equipment_line_ids': equipment_line_ids,
                            'default_subcon_line_ids': subcon_line_ids,
                            'default_is_wizard': is_wizard,
                            'default_job_count': len(sale_order_cons.job_references) + 1,
                            'default_analytic_account_id': rec.project_id.analytic_account_id.id,
                            'default_total_variation_order': rec.total_variation_order,
                            'default_total_variation_order_material': rec.total_variation_order_material,
                            'default_total_variation_order_labour': rec.total_variation_order_labour,
                            'default_total_variation_order_overhead': rec.total_variation_order_overhead,
                            'default_total_variation_order_asset': rec.total_variation_order_asset,
                            'default_total_variation_order_equipment': rec.total_variation_order_equipment,
                            'default_total_variation_order_subcon': rec.total_variation_order_subcon,
                            'default_is_over_budget_ratio': rec.job_estimate_id.is_over_budget_ratio,
                            'default_ratio_value': rec.job_estimate_id.ratio_value,
                        }

                else:
                    context = {
                        'is_wizard': is_wizard,
                        'default_is_set_projects_type': is_set_projects_type,
                        'default_project_template_id': project_template_id,
                        'default_job_references': [(4, rec.job_estimate_id.id)],
                        'default_project_id': rec.project_id.id,
                        'default_partner_id': rec.customer_id.id,
                        'default_project_scope_ids': project_scope_ids,
                        'default_section_ids': section_ids,
                        # 'default_variable_ids': variable_ids,
                        'default_material_line_ids': material_line_ids,
                        'default_labour_line_ids': labour_line_ids,
                        'default_overhead_line_ids': overhead_line_ids,
                        'default_internal_asset_line_ids': internal_asset_line_ids,
                        'default_equipment_line_ids': equipment_line_ids,
                        'default_subcon_line_ids': subcon_line_ids,
                        'default_is_wizard': is_wizard,
                        'default_job_count': 1,
                        'default_analytic_account_id': rec.project_id.analytic_account_id.id,
                        'default_total_variation_order': rec.total_variation_order,
                        'default_total_variation_order_material': rec.total_variation_order_material,
                        'default_total_variation_order_labour': rec.total_variation_order_labour,
                        'default_total_variation_order_overhead': rec.total_variation_order_overhead,
                        'default_total_variation_order_asset': rec.total_variation_order_asset,
                        'default_total_variation_order_equipment': rec.total_variation_order_equipment,
                        'default_total_variation_order_subcon': rec.total_variation_order_subcon,
                        'default_is_over_budget_ratio': rec.job_estimate_id.is_over_budget_ratio,
                        'default_ratio_value': rec.job_estimate_id.ratio_value,
                    }

                return {
                    "name": "Quotation",
                    "type": "ir.actions.act_window",
                    "res_model": "sale.order.const",
                    "res_id": sale_order_cons.id if sale_order_cons and not ctx.get('create_new') else False,
                    "context": context,
                    "view_mode": 'form',
                    "target": "current",
                }


    # def default_get(self, fields_list):

    #     def array_are_same(arr):
    #         first = arr[0]
    #         for i in range(1, len(arr)):
    #             if arr[i] != first:
    #                 return False
    #         return True

    #     res = super(JobEstimateExistingQuotation, self).default_get(fields_list)
    #     context = self._context
    #     active_ids = context.get('active_ids', [])
    #     if active_ids:
    #         project_ids = []
    #         customer_ids = []
    #         type_estimate = []
    #         job_estimate_id = self.env['job.estimate'].browse(active_ids)
    #         for job in job_estimate_id:
    #             # if job.contract_category != 'main':
    #             #     raise UserError(_('You must select only main contract.'))
    #             if job.state_new != 'approved' or job.sale_state == 'quotation':
    #                 raise UserError(_('You can not create quotation from this BOQ. Please check the approval '
    #                                   'matrix state and sale state.'))
    #             project_ids.append(job.project_id.id)
    #             customer_ids.append(job.partner_id.id)
    #             type_estimate.append(job.contract_category)
    #         # Check Project and Customer
    #         if not array_are_same(project_ids) \
    #             or not array_are_same(customer_ids)\
    #             or not array_are_same(type_estimate):
    #             raise UserError(_('You can not create quotation from this BOQ. because it is not same '
    #                               'project or customer.'))
    #         res.update({
    #             'job_estimate_id': job_estimate_id.id,
    #             'project_id': job_estimate_id[0].project_id.id,
    #             'customer_id': job_estimate_id[0].partner_id.id,
    #         })
    #     return res


class JobEstimateExistingQuotationScope(models.TransientModel):
    _name = "job.estimate.existing.line.scope"
    _description = "BOQ Existing Quotation Scope"
    _order = 'sequence'

    is_active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one('job.estimate', string="BOQ", ondelete='cascade')
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    description = fields.Text(string='Description')
    subtotal = fields.Float(string='Subtotal', compute='_amount_total')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")

    @api.depends('is_active', 'wiz_id.material_estimation_wiz', 'wiz_id.labour_estimation_wiz',
                 'wiz_id.overhead_estimation_wiz', 'wiz_id.subcon_estimation_wiz',
                 'wiz_id.equipment_estimation_wiz', 'wiz_id.internal_asset_wiz',
                 'wiz_id.material_estimation_wiz.subtotal', 'wiz_id.labour_estimation_wiz.subtotal',
                 'wiz_id.overhead_estimation_wiz.subtotal', 'wiz_id.subcon_estimation_wiz.subtotal',
                 'wiz_id.equipment_estimation_wiz.subtotal', 'wiz_id.internal_asset_wiz.subtotal')
    def _amount_total(self):
        for scope in self:
            total_subtotal = 0.0
            if scope.is_active:
                material_ids = scope.wiz_id.material_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == scope.project_scope.id and m.is_active == True)
                for mat in material_ids:
                    total_subtotal += mat.subtotal
                labour_ids = scope.wiz_id.labour_estimation_wiz.filtered(
                    lambda l: l.project_scope.id == scope.project_scope.id and l.is_active == True)
                for lab in labour_ids:
                    total_subtotal += lab.subtotal
                overhead_ids = scope.wiz_id.overhead_estimation_wiz.filtered(
                    lambda o: o.project_scope.id == scope.project_scope.id and o.is_active == True)
                for ove in overhead_ids:
                    total_subtotal += ove.subtotal
                subcon_ids = scope.wiz_id.subcon_estimation_wiz.filtered(
                    lambda s: s.project_scope.id == scope.project_scope.id and s.is_active == True)
                for sub in subcon_ids:
                    total_subtotal += sub.subtotal
                asset_ids = scope.wiz_id.internal_asset_wiz.filtered(
                    lambda e: e.project_scope.id == scope.project_scope.id and e.is_active == True)
                for ass in asset_ids:
                    total_subtotal += ass.subtotal
                equipment_ids = scope.wiz_id.equipment_estimation_wiz.filtered(
                    lambda e: e.project_scope.id == scope.project_scope.id and e.is_active == True)
                for equ in equipment_ids:
                    total_subtotal += equ.subtotal
            
            scope.subtotal = total_subtotal

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.project_scope_wiz', 'wiz_id.project_scope_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.project_scope_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationSection(models.TransientModel):
    _name = "job.estimate.existing.line.section"
    _description = "BOQ Existing Quotation Section"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    is_active = fields.Boolean(string="Active", default=True)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    subtotal = fields.Float(string='Subtotal', compute='_amount_total_section')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")

    @api.depends('is_active', 'wiz_id.material_estimation_wiz', 'wiz_id.labour_estimation_wiz',
                 'wiz_id.overhead_estimation_wiz', 'wiz_id.subcon_estimation_wiz',
                 'wiz_id.equipment_estimation_wiz', 'wiz_id.internal_asset_wiz',
                 'wiz_id.material_estimation_wiz.subtotal', 'wiz_id.labour_estimation_wiz.subtotal',
                 'wiz_id.overhead_estimation_wiz.subtotal', 'wiz_id.subcon_estimation_wiz.subtotal',
                 'wiz_id.equipment_estimation_wiz.subtotal', 'wiz_id.internal_asset_wiz.subtotal')
    def _amount_total_section(self):
        for section in self:
            total_subtotal = 0.0
            if section.is_active:
                material_ids = section.wiz_id.material_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == section.project_scope.id and
                            m.section_name.id == section.section_name.id
                            and m.is_active == True)
                for mat in material_ids:
                    total_subtotal += mat.subtotal
                labour_ids = section.wiz_id.labour_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == section.project_scope.id and
                            m.section_name.id == section.section_name.id
                            and m.is_active == True)
                for lab in labour_ids:
                    total_subtotal += lab.subtotal
                overhead_ids = section.wiz_id.overhead_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == section.project_scope.id and
                            m.section_name.id == section.section_name.id
                            and m.is_active == True)
                for ove in overhead_ids:
                    total_subtotal += ove.subtotal
                subcon_ids = section.wiz_id.subcon_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == section.project_scope.id and
                            m.section_name.id == section.section_name.id
                            and m.is_active == True)
                for sub in subcon_ids:
                    total_subtotal += sub.subtotal
                asset_ids = section.wiz_id.internal_asset_wiz.filtered(
                    lambda m: m.project_scope.id == section.project_scope.id and
                            m.section_name.id == section.section_name.id
                            and m.is_active == True)
                for ass in asset_ids:
                    total_subtotal += ass.subtotal
                equipment_ids = section.wiz_id.equipment_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == section.project_scope.id and
                            m.section_name.id == section.section_name.id
                            and m.is_active == True)
                for equ in equipment_ids:
                    total_subtotal += equ.subtotal

            section.subtotal = total_subtotal

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.section_wiz', 'wiz_id.section_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.section_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationVariable(models.TransientModel):
    _name = "job.estimate.existing.line.variable"
    _description = "BOQ Existing Quotation Variable"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    is_active = fields.Boolean(string="Active", default=True)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_name = fields.Many2one('variable.template', string='Variable')
    variable_quantity = fields.Float(string='Quantity')
    variable_uom = fields.Many2one('uom.uom', string='Unit Of Measure')
    subtotal = fields.Float(string='Subtotal', compute='_amount_total_variable')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")

    @api.depends('is_active', 'wiz_id.material_estimation_wiz', 'wiz_id.labour_estimation_wiz',
                 'wiz_id.overhead_estimation_wiz', 'wiz_id.subcon_estimation_wiz',
                 'wiz_id.equipment_estimation_wiz', 'wiz_id.internal_asset_wiz',
                 'wiz_id.material_estimation_wiz.subtotal', 'wiz_id.labour_estimation_wiz.subtotal',
                 'wiz_id.overhead_estimation_wiz.subtotal', 'wiz_id.subcon_estimation_wiz.subtotal',
                 'wiz_id.equipment_estimation_wiz.subtotal', 'wiz_id.internal_asset_wiz.subtotal')
    def _amount_total_variable(self):
        for variable in self:
            total_subtotal = 0.0
            if variable.is_active:
                material_ids = variable.wiz_id.material_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == variable.project_scope.id and
                            m.section_name.id == variable.section_name.id and
                            m.variable_ref.id == variable.variable_name.id
                            and m.is_active == True)
                for mat in material_ids:
                    total_subtotal += mat.subtotal
                labour_ids = variable.wiz_id.labour_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == variable.project_scope.id and
                            m.section_name.id == variable.section_name.id and
                            m.variable_ref.id == variable.variable_name.id
                            and m.is_active == True)
                for lab in labour_ids:
                    total_subtotal += lab.subtotal
                overhead_ids = variable.wiz_id.overhead_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == variable.project_scope.id and
                            m.section_name.id == variable.section_name.id and
                            m.variable_ref.id == variable.variable_name.id
                            and m.is_active == True)
                for ove in overhead_ids:
                    total_subtotal += ove.subtotal
                subcon_ids = variable.wiz_id.subcon_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == variable.project_scope.id and
                            m.section_name.id == variable.section_name.id and
                            m.variable_ref.id == variable.variable_name.id and
                            m.is_active == True)
                for sub in subcon_ids:
                    total_subtotal += sub.subtotal
                equipment_ids = variable.wiz_id.equipment_estimation_wiz.filtered(
                    lambda m: m.project_scope.id == variable.project_scope.id and
                            m.section_name.id == variable.section_name.id and
                            m.variable_ref.id == variable.variable_name.id and
                            m.is_active == True)
                for equ in equipment_ids:
                    total_subtotal += equ.subtotal
                asset_ids = variable.wiz_id.internal_asset_wiz.filtered(
                    lambda m: m.project_scope.id == variable.project_scope.id and
                            m.section_name.id == variable.section_name.id and
                            m.variable_ref.id == variable.variable_name.id
                            and m.is_active == True)
                for ass in asset_ids:
                    total_subtotal += ass.subtotal

            variable.subtotal = total_subtotal

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.variable_wiz', 'wiz_id.variable_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.variable_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingLineMaterial(models.TransientModel):
    _name = "job.estimate.existing.line.material"
    _description = "BOQ Existing Quotation Material"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    is_active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    current_quantity = fields.Float(string='Available Budget Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.material_estimation_wiz', 'wiz_id.material_estimation_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.material_estimation_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationLabour(models.TransientModel):
    _name = "job.estimate.existing.line.labour"
    _description = "BOQ Existing Quotation Labour"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    is_active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    contractors = fields.Integer('Contractors')    
    time = fields.Integer('Time')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    current_time = fields.Float(string='Available Budget Time')
    current_contractors = fields.Integer(string='Available Budget Contractors')
    budget_time = fields.Float(string='Budget Time')
    budget_contractors = fields.Integer(string='Budget Contractors')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.labour_estimation_wiz', 'wiz_id.labour_estimation_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.labour_estimation_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationSubcon(models.TransientModel):
    _name = "job.estimate.existing.line.subcon"
    _description = "BOQ Existing Quotation Subcon"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    is_active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Subcon')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    current_quantity = fields.Float(string='Available Budget Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.subcon_estimation_wiz', 'wiz_id.subcon_estimation_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.subcon_estimation_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationInternalAsset(models.TransientModel):
    _name = "job.estimate.existing.line.asset"
    _description = "BOQ Existing Quotation Internal Asset"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    is_active = fields.Boolean(string="Active", default=True)
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    asset_category_id = fields.Many2one('maintenance.equipment.category', string='Asset Category')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    current_quantity = fields.Float(string='Available Budget Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.internal_asset_wiz', 'wiz_id.internal_asset_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.internal_asset_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationEquipment(models.TransientModel):
    _name = "job.estimate.existing.line.equipment"
    _description = "BOQ Existing Quotation Equipment"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    is_active = fields.Boolean(string="Active", default=True)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    current_quantity = fields.Float(string='Available Budget Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.equipment_estimation_wiz', 'wiz_id.equipment_estimation_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.equipment_estimation_wiz:
                no += 1
                l.sr_no = no


class JobEstimateExistingQuotationFinancial(models.TransientModel):
    _name = "job.estimate.existing.line.overhead"
    _description = "BOQ Existing Quotation Overhead"
    _order = 'sequence'

    wiz_id = fields.Many2one("job.estimate.existing.quotation.const", string="Wizard", ondelete="cascade")
    job_estimate_id = fields.Many2one("job.estimate", string="BOQ")
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    is_active = fields.Boolean(string="Active", default=True)
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity')
    uom_id = fields.Many2one('uom.uom', 'Unit Of Measure')
    unit_price = fields.Float(string='Unit Price')
    subtotal = fields.Float(string='Subtotal')
    analytic_ids = fields.Many2many('account.analytic.tag', string='Analytic Tag')
    currency_id = fields.Many2one("res.currency", compute='get_currency_id', string="Currency")
    overhead_catagory = fields.Selection([
                          ('product', 'Product'),
                          ('petty cash', 'Petty Cash'),
                          ('cash advance', 'Cash Advance'),
                          ('fuel', 'Fuel'),
                          ], string='Overhead Category')
    current_quantity = fields.Float(string='Available Budget Quantity')
    budget_quantity = fields.Float(string='Budget Quantity')

    def get_currency_id(self):
        user_id = self.env.uid
        res_user_id = self.env['res.users'].browse(user_id)
        for line in self:
            line.currency_id = res_user_id.company_id.currency_id

    @api.depends('wiz_id.overhead_estimation_wiz', 'wiz_id.overhead_estimation_wiz.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.wiz_id.overhead_estimation_wiz:
                no += 1
                l.sr_no = no
