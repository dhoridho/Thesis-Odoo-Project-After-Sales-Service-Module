from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date

from odoo.addons.equip3_construction_sales_operation.models.job_estimate import ESTIMATES_DICT

# ESTIMATES_DICT = {
#     'material_estimation_ids': 'product_id',
#     'labour_estimation_ids': 'product_id',
#     'subcon_estimation_ids': 'variable',
#     'overhead_estimation_ids': 'product_id',
#     'equipment_estimation_ids': 'product_id',
#     'internal_asset_ids': 'asset_id'
# }


class JobEstimate(models.Model):
    _inherit = 'job.estimate'

    cost_sheet_ref = fields.Many2one('job.cost.sheet', 'Cost Sheet',
                                     domain="[('state', '=', 'approved'), ('company_id', '=', company_id)]")
    budgeting_period = fields.Selection(related='cost_sheet_ref.budgeting_period', string='Budgeting Method')
    project_budget_id = fields.Many2one('project.budget', 'Project Budget',
                                        domain="[('cost_sheet', '=', cost_sheet_ref),('state', '=', 'in_progress')]")
    project_budget_ids = fields.Many2many('project.budget', 'boq_project_budget_rel',
                                          'boq_id', 'budget_id', string='Periodical Budgets',
                                          domain="[('cost_sheet', '=', cost_sheet_ref),('state', '=', 'in_progress')]")
    is_set_projects_type = fields.Boolean(string="Set Project Type", default=False)
    project_template_id = fields.Many2one('templates.project', 'Project Template')

    def _compute_remarks(self):
        for rec in self:
            rec.remarks = ''
            if rec.contract_category == 'var':
                rec.remarks = 'You can input negative value for decreasing quantities (ex: -32, -1.2), or just input number for increasing quantities (ex: 32, 1.2). For unit price, just input the desired price (ex: 300, 20000)'

    # override _compute_total_variation_order from construction_sales_operation
    @api.depends('material_estimation_ids', 'labour_estimation_ids', 'subcon_estimation_ids', 'overhead_estimation_ids',
                 'equipment_estimation_ids', 'internal_asset_ids')
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
                for material in rec.material_estimation_ids:
                    # using first formula will result in correct number in any known case
                    # temporarily using logic just to be safe
                    if material.budget_unit_price != material.unit_price:
                        total_material += (material.budget_quantity + material.quantity) * (
                                    (material.unit_price - material.budget_unit_price) + material.budget_unit_price) - (
                                                      material.budget_quantity * material.budget_unit_price)
                    else:
                        total_material += material.unit_price * material.quantity
                for labour in rec.labour_estimation_ids:
                    # redeclare to not repeat the labour. stuff
                    budget_contractors = labour.budget_contractors
                    budget_time = labour.budget_time
                    contractors = labour.contractors
                    time = labour.time
                    unit_price = labour.unit_price
                    budget_unit_price = labour.budget_unit_price
                    if labour.budget_unit_price != labour.unit_price:
                        total_labour += ((budget_contractors + contractors) * (budget_time + time) * unit_price) - (
                                    budget_contractors * budget_time * budget_unit_price)
                    else:
                        total_labour += ((budget_contractors + contractors) * (budget_time + time) * unit_price) - (
                                    budget_contractors * budget_time * budget_unit_price)
                for subcon in rec.subcon_estimation_ids:
                    if subcon.budget_unit_price != subcon.unit_price:
                        total_subcon += (subcon.budget_quantity + subcon.quantity) * (
                                    (subcon.unit_price - subcon.budget_unit_price) + subcon.budget_unit_price) - (
                                                    subcon.budget_quantity * subcon.budget_unit_price)
                    else:
                        total_subcon += subcon.unit_price * subcon.quantity

                for overhead in rec.overhead_estimation_ids:
                    if overhead.budget_unit_price != overhead.unit_price:
                        total_overhead += (overhead.budget_quantity + overhead.quantity) * (
                                    (overhead.unit_price - overhead.budget_unit_price) + overhead.budget_unit_price) - (
                                                      overhead.budget_quantity * overhead.budget_unit_price)
                    else:
                        total_overhead += overhead.unit_price * overhead.quantity

                for equipment in rec.equipment_estimation_ids:
                    if equipment.budget_unit_price != equipment.unit_price:
                        total_equipment += (equipment.budget_quantity + equipment.quantity) * ((
                                                                                                           equipment.unit_price - equipment.budget_unit_price) + equipment.budget_unit_price) - (
                                                       equipment.budget_quantity * equipment.budget_unit_price)
                    else:
                        total_equipment += equipment.unit_price * equipment.quantity

                for asset in rec.internal_asset_ids:
                    if asset.budget_unit_price != asset.unit_price:
                        total_internal_assets += (asset.budget_quantity + asset.quantity) * (
                                    (asset.unit_price - asset.budget_unit_price) + asset.budget_unit_price) - (
                                                             asset.budget_quantity * asset.budget_unit_price)
                    else:
                        total_internal_assets += asset.unit_price * asset.quantity

                total = total_material + total_labour + total_subcon + total_overhead + total_equipment + total_internal_assets
            rec.total_variation_order = total
            rec.total_variation_order_material = total_material
            rec.total_variation_order_labour = total_labour
            rec.total_variation_order_subcon = total_subcon
            rec.total_variation_order_overhead = total_overhead
            rec.total_variation_order_equipment = total_equipment
            rec.total_variation_order_asset = total_internal_assets

    def exist_main_contract(self, is_from_create=False):
        res = super(JobEstimate, self).exist_main_contract()
        if not is_from_create:
            for rec in self:
                if rec.project_budget_id:
                    if rec.project_budget_id.project_id.id != rec.project_id._origin.id:
                        rec.project_budget_id = False
                variables = []
                for boq in rec.main_contract_ref.job_references:
                    variables.append(boq.variable_ids)
                if len(variables) > 0:
                    rec.get_variation_order_line_variable()
                else:
                    rec.get_variation_order_line()

        return res

    @api.onchange('project_budget_ids')
    def onchange_project_budget_ids(self):
        for rec in self:
            if len(rec.project_budget_ids) > 0:
                variables = []
                for boq in rec.main_contract_ref.job_references:
                    variables.append(boq.variable_ids)
                if len(variables) > 0:
                    rec.get_variation_order_line_variable()
                else:
                    rec.get_variation_order_line()
            elif len(rec.project_budget_ids) == 0 and rec.budgeting_period in ['monthly', 'custom']:
                rec.project_scope_ids = False
                rec.section_ids = False
                rec.variable_ids = False
                rec.material_estimation_ids = False
                rec.labour_estimation_ids = False
                rec.overhead_estimation_ids = False
                rec.internal_asset_ids = False
                rec.equipment_estimation_ids = False
                rec.subcon_estimation_ids = False

    def get_variation_order_line(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.cost_sheet_ref = rec.project_id.cost_sheet
                rec.project_scope_ids = False
                rec.section_ids = False
                rec.material_estimation_ids = False
                rec.labour_estimation_ids = False
                rec.overhead_estimation_ids = False
                rec.internal_asset_ids = False
                rec.equipment_estimation_ids = False
                rec.subcon_estimation_ids = False

                if rec.cost_sheet_ref and len(rec.project_budget_ids) == 0 and rec.budgeting_period == 'project':
                    cost_sheet = rec.cost_sheet_ref
                    project_scopes = [(5, 0, 0)]
                    sections = [(5, 0, 0)]
                    materials = [(5, 0, 0)]
                    labours = [(5, 0, 0)]
                    overheads = [(5, 0, 0)]
                    equipments = [(5, 0, 0)]
                    internal_assets = [(5, 0, 0)]
                    subcons = [(5, 0, 0)]

                    for scope in cost_sheet.project_scope_cost_ids:
                        project_scopes.append((0, 0, {
                            'project_scope': scope.project_scope_id.id,
                            'is_vo_generated': True,
                        }))

                    for section in cost_sheet.section_cost_ids:
                        sections.append((0, 0, {
                            'project_scope': section.project_scope_id.id,
                            'section_name': section.section_id.id,
                            'is_vo_generated': True,
                        }))

                    for material in cost_sheet.material_ids:
                        materials.append((0, 0, {
                            'cs_material_id': material.id,
                            'is_vo_generated': True,
                            'project_scope': material.project_scope.id,
                            'section_name': material.section_name.id,
                            'group_of_product': material.group_of_product.id,
                            'product_id': material.product_id.id,
                            'description': material.description,
                            'quantity': 0,
                            'unit_price': material.price_unit,
                            'uom_id': material.uom_id.id,
                        }))

                    for labour in cost_sheet.material_labour_ids:
                        labours.append((0, 0, {
                            'cs_labour_id': labour.id,
                            'is_vo_generated': True,
                            'project_scope': labour.project_scope.id,
                            'section_name': labour.section_name.id,
                            'group_of_product': labour.group_of_product.id,
                            'product_id': labour.product_id.id,
                            'description': labour.description,
                            'quantity': 0,
                            'time': 0,
                            'contractors': 0,
                            'unit_price': labour.price_unit,
                            'uom_id': labour.uom_id.id,
                        }))

                    for overhead in cost_sheet.material_overhead_ids:
                        overheads.append((0, 0, {
                            'cs_overhead_id': overhead.id,
                            'is_vo_generated': True,
                            'project_scope': overhead.project_scope.id,
                            'section_name': overhead.section_name.id,
                            'overhead_catagory': overhead.overhead_catagory,
                            'group_of_product': overhead.group_of_product.id,
                            'product_id': overhead.product_id.id,
                            'description': overhead.description,
                            'quantity': 0,
                            'unit_price': overhead.price_unit,
                            'uom_id': overhead.uom_id.id,
                        }))

                    for asset in cost_sheet.internal_asset_ids:
                        internal_assets.append((0, 0, {
                            'cs_internal_asset_id': asset.id,
                            'is_vo_generated': True,
                            'project_scope': asset.project_scope.id,
                            'section_name': asset.section_name.id,
                            'asset_category_id': asset.asset_category_id.id,
                            'asset_id': asset.asset_id.id,
                            'description': asset.description,
                            'quantity': 0,
                            'unit_price': asset.price_unit,
                            'uom_id': asset.uom_id.id,
                        }))

                    for equipment in cost_sheet.material_equipment_ids:
                        equipments.append((0, 0, {
                            'cs_equipment_id': equipment.id,
                            'is_vo_generated': True,
                            'project_scope': equipment.project_scope.id,
                            'section_name': equipment.section_name.id,
                            'group_of_product': equipment.group_of_product.id,
                            'product_id': equipment.product_id.id,
                            'description': equipment.description,
                            'quantity': 0,
                            'unit_price': equipment.price_unit,
                            'uom_id': equipment.uom_id.id,
                        }))

                    for subcon in cost_sheet.material_subcon_ids:
                        subcons.append((0, 0, {
                            'cs_subcon_id': subcon.id,
                            'is_vo_generated': True,
                            'project_scope': subcon.project_scope.id,
                            'section_name': subcon.section_name.id,
                            'variable': subcon.variable.id,
                            'description': subcon.description,
                            'quantity': 0,
                            'unit_price': subcon.price_unit,
                            'uom_id': subcon.uom_id.id,
                        }))

                    rec.update({
                        'project_scope_ids': project_scopes,
                        'section_ids': sections,
                        'material_estimation_ids': materials,
                        'labour_estimation_ids': labours,
                        'overhead_estimation_ids': overheads,
                        'internal_asset_ids': internal_assets,
                        'equipment_estimation_ids': equipments,
                        'subcon_estimation_ids': subcons,
                    })

                    cost_sheet_section_ids = rec.cost_sheet_ref.contract_history_ids[-1].contract_history.section_ids
                    for section in cost_sheet_section_ids:
                        boq_section = rec.section_ids.filtered(lambda x: x.project_scope.id == section.project_scope.id and x.section_name.id == section.section.id and x.is_vo_generated is True)
                        if boq_section:
                            boq_section[0].write({
                                'quantity': section.quantity,
                                'uom_id': section.uom_id.id,
                            })

                    for material in rec.material_estimation_ids:
                        material.onchange_quantity()
                    for labour in rec.labour_estimation_ids:
                        labour.onchange_quantity()
                    for overhead in rec.overhead_estimation_ids:
                        overhead.onchange_quantity()
                    for asset in rec.internal_asset_ids:
                        asset.onchange_quantity()
                    for equipment in rec.equipment_estimation_ids:
                        equipment.onchange_quantity()
                    for subcon in rec.subcon_estimation_ids:
                        subcon.onchange_quantity()
                elif rec.cost_sheet_ref and len(rec.project_budget_ids) > 0 and rec.budgeting_period != 'project':
                    project_scopes = []
                    sections = []
                    project_scope_update = [[(5, 0, 0)]]
                    section_update = [[(5, 0, 0)]]
                    materials = [(5, 0, 0)]
                    labours = [(5, 0, 0)]
                    overheads = [(5, 0, 0)]
                    equipments = [(5, 0, 0)]
                    internal_assets = [(5, 0, 0)]
                    subcons = [(5, 0, 0)]
                    for project_budget in rec.project_budget_ids:
                        # project_budget = rec.project_budget_id
                        # Since there is no project scope and section table in project budget, we need to get the value from
                        # all estimation table in project budget
                        for material in project_budget.budget_material_ids:
                            materials.append((0, 0, {
                                'cs_material_id': material.cs_material_id.id,
                                'bd_material_id': material._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': material.project_scope.id,
                                'section_name': material.section_name.id,
                                'group_of_product': material.group_of_product.id,
                                'product_id': material.product_id.id,
                                'description': material.description,
                                'quantity': 0,
                                'unit_price': material.amount,
                                'uom_id': material.uom_id.id,
                            }))
                            project_scopes.append(material.project_scope.id)
                            scope_key = 'project_scope_' + str(material.project_scope.id)
                            section_key = 'section_' + str(material.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: material.project_scope.id,
                                             section_key: material.section_name.id})

                        for labour in project_budget.budget_labour_ids:
                            labours.append((0, 0, {
                                'cs_labour_id': labour.cs_labour_id.id,
                                'bd_labour_id': labour._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': labour.project_scope.id,
                                'section_name': labour.section_name.id,
                                'group_of_product': labour.group_of_product.id,
                                'product_id': labour.product_id.id,
                                'description': labour.description,
                                'quantity': 0,
                                'time': 0,
                                'contractors': 0,
                                'unit_price': labour.amount,
                                'uom_id': labour.uom_id.id,
                            }))
                            project_scopes.append(labour.project_scope.id)
                            scope_key = 'project_scope_' + str(labour.project_scope.id)
                            section_key = 'section_' + str(labour.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: labour.project_scope.id,
                                             section_key: labour.section_name.id})

                        for overhead in project_budget.budget_overhead_ids:
                            overheads.append((0, 0, {
                                'cs_overhead_id': overhead.cs_overhead_id.id,
                                'bd_overhead_id': overhead._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': overhead.project_scope.id,
                                'section_name': overhead.section_name.id,
                                'overhead_catagory': overhead.overhead_catagory,
                                'group_of_product': overhead.group_of_product.id,
                                'product_id': overhead.product_id.id,
                                'description': overhead.description,
                                'quantity': 0,
                                'unit_price': overhead.amount,
                                'uom_id': overhead.uom_id.id,
                            }))
                            project_scopes.append(overhead.project_scope.id)
                            scope_key = 'project_scope_' + str(overhead.project_scope.id)
                            section_key = 'section_' + str(overhead.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: overhead.project_scope.id,
                                             section_key: overhead.section_name.id})

                        for asset in project_budget.budget_internal_asset_ids:
                            internal_assets.append((0, 0, {
                                'cs_internal_asset_id': asset.cs_internal_asset_id.id,
                                'bd_internal_asset_id': asset._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': asset.project_scope_line_id.id,
                                'section_name': asset.section_name.id,
                                'asset_category_id': asset.asset_category_id.id,
                                'asset_id': asset.asset_id.id,
                                'description': asset.asset_id.display_name,
                                'quantity': 0,
                                'unit_price': asset.price_unit,
                                'uom_id': asset.uom_id.id,
                            }))
                            project_scopes.append(asset.project_scope_line_id.id)
                            scope_key = 'project_scope_' + str(asset.project_scope_line_id.id)
                            section_key = 'section_' + str(asset.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: asset.project_scope_line_id.id,
                                             section_key: asset.section_name.id})

                        for equipment in project_budget.budget_equipment_ids:
                            equipments.append((0, 0, {
                                'cs_equipment_id': equipment.cs_equipment_id.id,
                                'bd_equipment_id': equipment._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': equipment.project_scope.id,
                                'section_name': equipment.section_name.id,
                                'group_of_product': equipment.group_of_product.id,
                                'product_id': equipment.product_id.id,
                                'description': equipment.description,
                                'quantity': 0,
                                'unit_price': equipment.amount,
                                'uom_id': equipment.uom_id.id,
                            }))
                            project_scopes.append(equipment.project_scope.id)
                            scope_key = 'project_scope_' + str(equipment.project_scope.id)
                            section_key = 'section_' + str(equipment.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: equipment.project_scope.id,
                                             section_key: equipment.section_name.id})

                        for subcon in project_budget.budget_subcon_ids:
                            subcons.append((0, 0, {
                                'cs_subcon_id': subcon.cs_subcon_id.id,
                                'bd_subcon_id': subcon._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': subcon.project_scope.id,
                                'section_name': subcon.section_name.id,
                                'variable': subcon.subcon_id.id,
                                'description': subcon.description,
                                'quantity': 0,
                                'unit_price': subcon.amount,
                                'uom_id': subcon.uom_id.id,
                            }))
                            project_scopes.append(subcon.project_scope.id)
                            scope_key = 'project_scope_' + str(subcon.project_scope.id)
                            section_key = 'section_' + str(subcon.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: subcon.project_scope.id,
                                             section_key: subcon.section_name.id})

                    for scope in list(set(project_scopes)):
                        project_scope_update.append((0, 0, {
                            'project_scope': scope,
                            'is_vo_generated': True,
                        }))

                    for section in list({v['id']: v for v in sections}.values()):
                        values = list(section.values())
                        project_scope = values[1]
                        section_name = values[2]
                        section_update.append((0, 0, {
                            'project_scope': project_scope,
                            'section_name': section_name,
                            'is_vo_generated': True,
                        }))

                    rec.update({
                        'project_scope_ids': project_scope_update,
                        'section_ids': section_update,
                        'material_estimation_ids': materials,
                        'labour_estimation_ids': labours,
                        'overhead_estimation_ids': overheads,
                        'internal_asset_ids': internal_assets,
                        'equipment_estimation_ids': equipments,
                        'subcon_estimation_ids': subcons,
                    })

                    cost_sheet_section_ids = rec.cost_sheet_ref.contract_history_ids[-1].contract_history.section_ids
                    for section in cost_sheet_section_ids:
                        boq_section = rec.section_ids.filtered(lambda x: x.project_scope.id == section.project_scope.id and x.section_name.id == section.section.id and x.is_vo_generated is True)
                        if boq_section:
                            boq_section[0].write({
                                'quantity': section.quantity,
                                'uom_id': section.uom_id.id,
                            })

                    for material in rec.material_estimation_ids:
                        material.onchange_quantity()
                    for labour in rec.labour_estimation_ids:
                        labour.onchange_quantity()
                    for overhead in rec.overhead_estimation_ids:
                        overhead.onchange_quantity()
                    for asset in rec.internal_asset_ids:
                        asset.onchange_quantity()
                    for equipment in rec.equipment_estimation_ids:
                        equipment.onchange_quantity()
                    for subcon in rec.subcon_estimation_ids:
                        subcon.onchange_quantity()

    def get_variation_order_line_variable(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.cost_sheet_ref = rec.project_id.cost_sheet
                rec.project_scope_ids = False
                rec.section_ids = False
                rec.variable_ids = False
                rec.material_estimation_ids = False
                rec.labour_estimation_ids = False
                rec.overhead_estimation_ids = False
                rec.internal_asset_ids = False
                rec.equipment_estimation_ids = False
                rec.subcon_estimation_ids = False

                variable_list = []

                if rec.cost_sheet_ref and len(rec.project_budget_ids) == 0 and rec.budgeting_period == 'project':
                    cost_sheet = rec.cost_sheet_ref
                    project_scopes = [(5, 0, 0)]
                    sections = [(5, 0, 0)]
                    variables = [(5, 0, 0)]
                    materials = [(5, 0, 0)]
                    labours = [(5, 0, 0)]
                    overheads = [(5, 0, 0)]
                    equipments = [(5, 0, 0)]
                    internal_assets = [(5, 0, 0)]
                    subcons = [(5, 0, 0)]

                    for scope in cost_sheet.project_scope_cost_ids:
                        project_scopes.append((0, 0, {
                            'project_scope': scope.project_scope_id.id,
                            'is_vo_generated': True,
                        }))

                    for section in cost_sheet.section_cost_ids:
                        sections.append((0, 0, {
                            'project_scope': section.project_scope_id.id,
                            'section_name': section.section_id.id,
                            'is_vo_generated': True,
                        }))

                    for material in cost_sheet.material_ids:
                        materials.append((0, 0, {
                            'cs_material_id': material.id,
                            'is_vo_generated': True,
                            'project_scope': material.project_scope.id,
                            'section_name': material.section_name.id,
                            'group_of_product': material.group_of_product.id,
                            'product_id': material.product_id.id,
                            'description': material.description,
                            'quantity': 0,
                            'unit_price': material.price_unit,
                            'uom_id': material.uom_id.id,
                        }))

                    for labour in cost_sheet.material_labour_ids:
                        labours.append((0, 0, {
                            'cs_labour_id': labour.id,
                            'is_vo_generated': True,
                            'project_scope': labour.project_scope.id,
                            'section_name': labour.section_name.id,
                            'group_of_product': labour.group_of_product.id,
                            'product_id': labour.product_id.id,
                            'description': labour.description,
                            'quantity': 0,
                            'time': 0,
                            'contractors': 0,
                            'unit_price': labour.price_unit,
                            'uom_id': labour.uom_id.id,
                        }))

                    for overhead in cost_sheet.material_overhead_ids:
                        overheads.append((0, 0, {
                            'cs_overhead_id': overhead.id,
                            'is_vo_generated': True,
                            'project_scope': overhead.project_scope.id,
                            'section_name': overhead.section_name.id,
                            'overhead_catagory': overhead.overhead_catagory,
                            'group_of_product': overhead.group_of_product.id,
                            'product_id': overhead.product_id.id,
                            'description': overhead.description,
                            'quantity': 0,
                            'unit_price': overhead.price_unit,
                            'uom_id': overhead.uom_id.id,
                        }))

                    for asset in cost_sheet.internal_asset_ids:
                        internal_assets.append((0, 0, {
                            'cs_internal_asset_id': asset.id,
                            'is_vo_generated': True,
                            'project_scope': asset.project_scope.id,
                            'section_name': asset.section_name.id,
                            'asset_category_id': asset.asset_category_id.id,
                            'asset_id': asset.asset_id.id,
                            'description': asset.description,
                            'quantity': 0,
                            'unit_price': asset.price_unit,
                            'uom_id': asset.uom_id.id,
                        }))

                    for equipment in cost_sheet.material_equipment_ids:
                        equipments.append((0, 0, {
                            'cs_equipment_id': equipment.id,
                            'is_vo_generated': True,
                            'project_scope': equipment.project_scope.id,
                            'section_name': equipment.section_name.id,
                            'group_of_product': equipment.group_of_product.id,
                            'product_id': equipment.product_id.id,
                            'description': equipment.description,
                            'quantity': 0,
                            'unit_price': equipment.price_unit,
                            'uom_id': equipment.uom_id.id,
                        }))

                    for subcon in cost_sheet.material_subcon_ids:
                        subcons.append((0, 0, {
                            'cs_subcon_id': subcon.id,
                            'is_vo_generated': True,
                            'project_scope': subcon.project_scope.id,
                            'section_name': subcon.section_name.id,
                            'variable': subcon.variable.id,
                            'description': subcon.description,
                            'quantity': 0,
                            'unit_price': subcon.price_unit,
                            'uom_id': subcon.uom_id.id,
                        }))

                    rec.update({
                        'project_scope_ids': project_scopes,
                        'section_ids': sections,
                        'material_estimation_ids': materials,
                        'labour_estimation_ids': labours,
                        'overhead_estimation_ids': overheads,
                        'internal_asset_ids': internal_assets,
                        'equipment_estimation_ids': equipments,
                        'subcon_estimation_ids': subcons,
                    })

                    cost_sheet_section_ids = rec.cost_sheet_ref.contract_history_ids[-1].contract_history.section_ids
                    for section in cost_sheet_section_ids:
                        boq_section = rec.section_ids.filtered(lambda x: x.project_scope.id == section.project_scope.id and x.section_name.id == section.section.id and x.is_vo_generated is True)
                        if boq_section:
                            boq_section[0].write({
                                'quantity': section.quantity,
                                'uom_id': section.uom_id.id,
                            })

                    contract_histories = rec.cost_sheet_ref.contract_history_ids.filtered(
                        lambda x: x.contract_history.state == "sale").mapped('contract_history')
                    job_estimates = contract_histories[-1].job_references

                    # estimation with variable, used dict to minimize avg time complexity
                    main_boq_material_value = {(str(material.project_scope.id)+str(material.section_name.id)+str(material.product_id.id)): material for material in job_estimates.material_estimation_ids if len(material.variable_ref) > 0}
                    main_boq_labour_value = {(str(labour.project_scope.id)+str(labour.section_name.id)+str(labour.product_id.id)): labour for labour in job_estimates.labour_estimation_ids if len(labour.variable_ref) > 0}
                    main_boq_overhead_value = {(str(overhead.project_scope.id)+str(overhead.section_name.id)+str(overhead.product_id.id)): overhead for overhead in job_estimates.overhead_estimation_ids if len(overhead.variable_ref) > 0}
                    main_boq_equipment_value = {(str(equipment.project_scope.id)+str(equipment.section_name.id)+str(equipment.product_id.id)): equipment for equipment in job_estimates.equipment_estimation_ids if len(equipment.variable_ref) > 0}
                    main_boq_subcon_value = {(str(subcon.project_scope.id)+str(subcon.section_name.id)+str(subcon.variable.id)): subcon for subcon in job_estimates.subcon_estimation_ids if len(subcon.variable_ref) > 0}
                    main_boq_asset_value = {(str(asset.project_scope.id)+str(asset.section_name.id)+str(asset.asset_id.id)): asset for asset in job_estimates.internal_asset_ids if len(asset.variable_ref) > 0}

                    for material in rec.material_estimation_ids:
                        material_key = str(material.project_scope.id)+str(material.section_name.id)+str(material.product_id.id)
                        if material_key in main_boq_material_value:
                            main_boq_material = main_boq_material_value[material_key]
                            material.variable_ref = main_boq_material.variable_ref
                            if [material.project_scope, material.section_name, main_boq_material.variable_ref] not in variable_list:
                                variable_list.append([material.project_scope, material.section_name, main_boq_material.variable_ref])
                        material.onchange_quantity()
                    for labour in rec.labour_estimation_ids:
                        labour_key = str(labour.project_scope.id) + str(labour.section_name.id) + str(labour.product_id.id)
                        if labour_key in main_boq_labour_value:
                            main_boq_labour = main_boq_labour_value[labour_key]
                            labour.variable_ref = main_boq_labour.variable_ref
                            if [labour.project_scope, labour.section_name,
                                main_boq_labour.variable_ref] not in variable_list:
                                variable_list.append(
                                    [labour.project_scope, labour.section_name, main_boq_labour.variable_ref])
                        labour.onchange_quantity()
                    for overhead in rec.overhead_estimation_ids:
                        overhead_key = str(overhead.project_scope.id) + str(overhead.section_name.id) + str(overhead.product_id.id)
                        if overhead_key in main_boq_overhead_value:
                            main_boq_overhead = main_boq_overhead_value[overhead_key]
                            overhead.variable_ref = main_boq_overhead.variable_ref
                            if [overhead.project_scope, overhead.section_name,
                                main_boq_overhead.variable_ref] not in variable_list:
                                variable_list.append(
                                    [overhead.project_scope, overhead.section_name, main_boq_overhead.variable_ref])
                        overhead.onchange_quantity()
                    for asset in rec.internal_asset_ids:
                        asset_key = str(asset.project_scope.id) + str(asset.section_name.id) + str(asset.asset_id.id)
                        if asset_key in main_boq_asset_value:
                            main_boq_asset = main_boq_asset_value[asset_key]
                            asset.variable_ref = main_boq_asset.variable_ref
                            if [asset.project_scope, asset.section_name,
                                main_boq_asset.variable_ref] not in variable_list:
                                variable_list.append(
                                    [asset.project_scope, asset.section_name, main_boq_asset.variable_ref])
                        asset.onchange_quantity()
                    for equipment in rec.equipment_estimation_ids:
                        equipment_key = str(equipment.project_scope.id) + str(equipment.section_name.id) + str(equipment.product_id.id)
                        if equipment_key in main_boq_equipment_value:
                            main_boq_equipment = main_boq_equipment_value[equipment_key]
                            equipment.variable_ref = main_boq_equipment.variable_ref
                            if [equipment.project_scope, equipment.section_name,
                                main_boq_equipment.variable_ref] not in variable_list:
                                variable_list.append(
                                    [equipment.project_scope, equipment.section_name, main_boq_equipment.variable_ref])
                        equipment.onchange_quantity()
                    for subcon in rec.subcon_estimation_ids:
                        subcon_key = str(subcon.project_scope.id) + str(subcon.section_name.id) + str(subcon.variable.id)
                        if subcon_key in main_boq_subcon_value:
                            main_boq_subcon = main_boq_subcon_value[subcon_key]
                            subcon.variable_ref = main_boq_subcon.variable_ref
                            if [subcon.project_scope, subcon.section_name,
                                main_boq_subcon.variable_ref] not in variable_list:
                                variable_list.append(
                                    [subcon.project_scope, subcon.section_name, main_boq_subcon.variable_ref])
                        subcon.onchange_quantity()

                    main_boq_variable_value = {(str(variable.project_scope.id)+str(variable.section_name.id)+str(variable.variable_name.id)): variable for variable in job_estimates.variable_ids}
                    for variable in variable_list:
                        variable_key = str(variable[0].id)+str(variable[1].id)+str(variable[2].id)
                        if variable_key in main_boq_variable_value:
                            value = main_boq_variable_value[variable_key]
                            variables.append((0, 0, {
                                'project_scope': value.project_scope.id,
                                'section_name': value.section_name.id,
                                'variable_name': value.variable_name.id,
                                'variable_quantity': value.variable_quantity,
                                'variable_uom': value.variable_uom.id,
                                'is_vo_generated': True
                            }))
                    rec.variable_ids = variables

                elif rec.cost_sheet_ref and len(rec.project_budget_ids) > 0 and rec.budgeting_period != 'project':
                    project_scopes = []
                    sections = []
                    project_scope_update = [[(5, 0, 0)]]
                    section_update = [[(5, 0, 0)]]
                    variables = [(5, 0, 0)]
                    materials = [(5, 0, 0)]
                    labours = [(5, 0, 0)]
                    overheads = [(5, 0, 0)]
                    equipments = [(5, 0, 0)]
                    internal_assets = [(5, 0, 0)]
                    subcons = [(5, 0, 0)]
                    for project_budget in rec.project_budget_ids:
                        # project_budget = rec.project_budget_id
                        # Since there is no project scope and section table in project budget, we need to get the value from
                        # all estimation table in project budget
                        for material in project_budget.budget_material_ids:
                            materials.append((0, 0, {
                                'cs_material_id': material.cs_material_id.id,
                                'bd_material_id': material._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': material.project_scope.id,
                                'section_name': material.section_name.id,
                                'group_of_product': material.group_of_product.id,
                                'product_id': material.product_id.id,
                                'description': material.description,
                                'quantity': 0,
                                'unit_price': material.amount,
                                'uom_id': material.uom_id.id,
                            }))
                            project_scopes.append(material.project_scope.id)
                            scope_key = 'project_scope_' + str(material.project_scope.id)
                            section_key = 'section_' + str(material.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: material.project_scope.id,
                                             section_key: material.section_name.id})

                        for labour in project_budget.budget_labour_ids:
                            labours.append((0, 0, {
                                'cs_labour_id': labour.cs_labour_id.id,
                                'bd_labour_id': labour._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': labour.project_scope.id,
                                'section_name': labour.section_name.id,
                                'group_of_product': labour.group_of_product.id,
                                'product_id': labour.product_id.id,
                                'description': labour.description,
                                'quantity': 0,
                                'time': 0,
                                'contractors': 0,
                                'unit_price': labour.amount,
                                'uom_id': labour.uom_id.id,
                            }))
                            project_scopes.append(labour.project_scope.id)
                            scope_key = 'project_scope_' + str(labour.project_scope.id)
                            section_key = 'section_' + str(labour.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: labour.project_scope.id,
                                             section_key: labour.section_name.id})

                        for overhead in project_budget.budget_overhead_ids:
                            overheads.append((0, 0, {
                                'cs_overhead_id': overhead.cs_overhead_id.id,
                                'bd_overhead_id': overhead._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': overhead.project_scope.id,
                                'section_name': overhead.section_name.id,
                                'overhead_catagory': overhead.overhead_catagory,
                                'group_of_product': overhead.group_of_product.id,
                                'product_id': overhead.product_id.id,
                                'description': overhead.description,
                                'quantity': 0,
                                'unit_price': overhead.amount,
                                'uom_id': overhead.uom_id.id,
                            }))
                            project_scopes.append(overhead.project_scope.id)
                            scope_key = 'project_scope_' + str(overhead.project_scope.id)
                            section_key = 'section_' + str(overhead.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: overhead.project_scope.id,
                                             section_key: overhead.section_name.id})

                        for asset in project_budget.budget_internal_asset_ids:
                            internal_assets.append((0, 0, {
                                'cs_internal_asset_id': asset.cs_internal_asset_id.id,
                                'bd_internal_asset_id': asset._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': asset.project_scope_line_id.id,
                                'section_name': asset.section_name.id,
                                'asset_category_id': asset.asset_category_id.id,
                                'asset_id': asset.asset_id.id,
                                'description': asset.asset_id.display_name,
                                'quantity': 0,
                                'unit_price': asset.price_unit,
                                'uom_id': asset.uom_id.id,
                            }))
                            project_scopes.append(asset.project_scope_line_id.id)
                            scope_key = 'project_scope_' + str(asset.project_scope_line_id.id)
                            section_key = 'section_' + str(asset.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: asset.project_scope_line_id.id,
                                             section_key: asset.section_name.id})

                        for equipment in project_budget.budget_equipment_ids:
                            equipments.append((0, 0, {
                                'cs_equipment_id': equipment.cs_equipment_id.id,
                                'bd_equipment_id': equipment._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': equipment.project_scope.id,
                                'section_name': equipment.section_name.id,
                                'group_of_product': equipment.group_of_product.id,
                                'product_id': equipment.product_id.id,
                                'description': equipment.description,
                                'quantity': 0,
                                'unit_price': equipment.amount,
                                'uom_id': equipment.uom_id.id,
                            }))
                            project_scopes.append(equipment.project_scope.id)
                            scope_key = 'project_scope_' + str(equipment.project_scope.id)
                            section_key = 'section_' + str(equipment.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: equipment.project_scope.id,
                                             section_key: equipment.section_name.id})

                        for subcon in project_budget.budget_subcon_ids:
                            subcons.append((0, 0, {
                                'cs_subcon_id': subcon.cs_subcon_id.id,
                                'bd_subcon_id': subcon._origin.id,
                                'project_budget_id': project_budget._origin.id,
                                'is_vo_generated': True,
                                'project_scope': subcon.project_scope.id,
                                'section_name': subcon.section_name.id,
                                'variable': subcon.subcon_id.id,
                                'description': subcon.description,
                                'quantity': 0,
                                'unit_price': subcon.amount,
                                'uom_id': subcon.uom_id.id,
                            }))
                            project_scopes.append(subcon.project_scope.id)
                            scope_key = 'project_scope_' + str(subcon.project_scope.id)
                            section_key = 'section_' + str(subcon.section_name.id)
                            dict_id = scope_key + '_' + section_key
                            sections.append({'id': dict_id, scope_key: subcon.project_scope.id,
                                             section_key: subcon.section_name.id})

                    for scope in list(set(project_scopes)):
                        project_scope_update.append((0, 0, {
                            'project_scope': scope,
                            'is_vo_generated': True,
                        }))

                    for section in list({v['id']: v for v in sections}.values()):
                        values = list(section.values())
                        project_scope = values[1]
                        section_name = values[2]
                        section_update.append((0, 0, {
                            'project_scope': project_scope,
                            'section_name': section_name,
                            'is_vo_generated': True,
                        }))

                    rec.update({
                        'project_scope_ids': project_scope_update,
                        'section_ids': section_update,
                        'material_estimation_ids': materials,
                        'labour_estimation_ids': labours,
                        'overhead_estimation_ids': overheads,
                        'internal_asset_ids': internal_assets,
                        'equipment_estimation_ids': equipments,
                        'subcon_estimation_ids': subcons,
                    })

                    cost_sheet_section_ids = rec.cost_sheet_ref.contract_history_ids[-1].contract_history.section_ids
                    for section in cost_sheet_section_ids:
                        boq_section = rec.section_ids.filtered(lambda x: x.project_scope.id == section.project_scope.id and x.section_name.id == section.section.id and x.is_vo_generated is True)
                        if boq_section:
                            boq_section[0].write({
                                'quantity': section.quantity,
                                'uom_id': section.uom_id.id,
                            })

                    contract_histories = rec.cost_sheet_ref.contract_history_ids.filtered(lambda x: x.contract_history.state == "sale").mapped('contract_history')
                    job_estimates = contract_histories[-1].job_references

                    # estimation with variable, used dict to minimize avg time complexity
                    main_boq_material_value = {(str(material.project_scope.id) + str(
                        material.section_name.id) + str(material.product_id.id)): material for material in
                                               job_estimates.material_estimation_ids
                                               if len(material.variable_ref) > 0}
                    main_boq_labour_value = {(str(labour.project_scope.id) + str(labour.section_name.id) + str(
                        labour.product_id.id)): labour for labour in
                                             job_estimates.labour_estimation_ids if
                                             len(labour.variable_ref) > 0}
                    main_boq_overhead_value = {(str(overhead.project_scope.id) + str(
                        overhead.section_name.id) + str(overhead.product_id.id)): overhead for overhead in
                                               job_estimates.overhead_estimation_ids
                                               if len(overhead.variable_ref) > 0}
                    main_boq_equipment_value = {(str(equipment.project_scope.id) + str(
                        equipment.section_name.id) + str(equipment.product_id.id)): equipment for equipment in
                                                job_estimates.equipment_estimation_ids
                                                if len(equipment.variable_ref) > 0}
                    main_boq_subcon_value = {(str(subcon.project_scope.id) + str(subcon.section_name.id) + str(
                        subcon.variable.id)): subcon for subcon in
                                             job_estimates.subcon_estimation_ids if
                                             len(subcon.variable_ref) > 0}
                    main_boq_asset_value = {(str(asset.project_scope.id) + str(asset.section_name.id) + str(
                        asset.asset_id.id)): asset for asset in
                                            job_estimates.internal_asset_ids if
                                            len(asset.variable_ref) > 0}

                    for material in rec.material_estimation_ids:
                        material_key = str(material.project_scope.id) + str(material.section_name.id) + str(
                            material.product_id.id)
                        if material_key in main_boq_material_value:
                            main_boq_material = main_boq_material_value[material_key]
                            material.variable_ref = main_boq_material.variable_ref
                            if [material.project_scope, material.section_name,
                                main_boq_material.variable_ref] not in variable_list:
                                variable_list.append(
                                    [material.project_scope, material.section_name, main_boq_material.variable_ref])
                        material.onchange_quantity()
                    for labour in rec.labour_estimation_ids:
                        labour_key = str(labour.project_scope.id) + str(labour.section_name.id) + str(
                            labour.product_id.id)
                        if labour_key in main_boq_labour_value:
                            main_boq_labour = main_boq_labour_value[labour_key]
                            labour.variable_ref = main_boq_labour.variable_ref
                            if [labour.project_scope, labour.section_name,
                                main_boq_labour.variable_ref] not in variable_list:
                                variable_list.append(
                                    [labour.project_scope, labour.section_name, main_boq_labour.variable_ref])
                        labour.onchange_quantity()
                    for overhead in rec.overhead_estimation_ids:
                        overhead_key = str(overhead.project_scope.id) + str(overhead.section_name.id) + str(
                            overhead.product_id.id)
                        if overhead_key in main_boq_overhead_value:
                            main_boq_overhead = main_boq_overhead_value[overhead_key]
                            overhead.variable_ref = main_boq_overhead.variable_ref
                            if [overhead.project_scope, overhead.section_name,
                                main_boq_overhead.variable_ref] not in variable_list:
                                variable_list.append(
                                    [overhead.project_scope, overhead.section_name, main_boq_overhead.variable_ref])
                        overhead.onchange_quantity()
                    for asset in rec.internal_asset_ids:
                        asset_key = str(asset.project_scope.id) + str(asset.section_name.id) + str(asset.asset_id.id)
                        if asset_key in main_boq_asset_value:
                            main_boq_asset = main_boq_asset_value[asset_key]
                            asset.variable_ref = main_boq_asset.variable_ref
                            if [asset.project_scope, asset.section_name,
                                main_boq_asset.variable_ref] not in variable_list:
                                variable_list.append(
                                    [asset.project_scope, asset.section_name, main_boq_asset.variable_ref])
                        asset.onchange_quantity()
                    for equipment in rec.equipment_estimation_ids:
                        equipment_key = str(equipment.project_scope.id) + str(equipment.section_name.id) + str(
                            equipment.product_id.id)
                        if equipment_key in main_boq_equipment_value:
                            main_boq_equipment = main_boq_equipment_value[equipment_key]
                            equipment.variable_ref = main_boq_equipment.variable_ref
                            if [equipment.project_scope, equipment.section_name,
                                main_boq_equipment.variable_ref] not in variable_list:
                                variable_list.append(
                                    [equipment.project_scope, equipment.section_name, main_boq_equipment.variable_ref])
                        equipment.onchange_quantity()
                    for subcon in rec.subcon_estimation_ids:
                        subcon_key = str(subcon.project_scope.id) + str(subcon.section_name.id) + str(
                            subcon.variable.id)
                        if subcon_key in main_boq_subcon_value:
                            main_boq_subcon = main_boq_subcon_value[subcon_key]
                            subcon.variable_ref = main_boq_subcon.variable_ref
                            if [subcon.project_scope, subcon.section_name,
                                main_boq_subcon.variable_ref] not in variable_list:
                                variable_list.append(
                                    [subcon.project_scope, subcon.section_name, main_boq_subcon.variable_ref])
                        subcon.onchange_quantity()

                    main_boq_variable_value = {(str(variable.project_scope.id) + str(variable.section_name.id) + str(
                        variable.variable_name.id)): variable for variable in
                                               job_estimates.variable_ids}
                    for variable in variable_list:
                        variable_key = str(variable[0].id) + str(variable[1].id) + str(variable[2].id)
                        if variable_key in main_boq_variable_value:
                            value = main_boq_variable_value[variable_key]
                            variables.append((0, 0, {
                                'project_scope': value.project_scope.id,
                                'section_name': value.section_name.id,
                                'variable_name': value.variable_name.id,
                                'variable_quantity': value.variable_quantity,
                                'variable_uom': value.variable_uom.id,
                                'is_vo_generated': True
                            }))
                    rec.variable_ids = variables

    def action_cost_sheet(self):
        job_sheet = self.env['job.cost.sheet'].search([('project_id', '=', self.project_id.id)], limit=1)
        action = job_sheet.get_formview_action()
        return action

    def job_confirm(self):
        res = super(JobEstimate, self).job_confirm()

        if self.department_type == 'department':
            if self.contract_category == 'main':
                line = self.env['job.cost.sheet'].create({
                    'cost_sheet_name': self.project_id.name,
                    'project_id': self.project_id.id,
                    'branch_id': self.branch_id.id,
                    'job_reference': [(4, self.id)],
                })
                line.onchange_approving_matrix_lines()

                if line:
                    line.sudo()._onchange_job_reference()
                    self.project_id.sudo()._inprogress_project_warehouse()
                    line.set_scope_section_table()
                    line.sudo()._get_customer()

                    budget_period = self.env['project.budget.period'].create({
                        'name': self.project_id.name,
                        'project': self.project_id.id,
                        'start_date': self.start_date,
                        'end_date': self.end_date,
                        'branch_id': self.project_id.branch_id.id,
                    })
                    budget_period.sudo().action_create_period()
                    budget_period.sudo().action_open()

            else:
                self.cost_sheet_ref.write({
                    'job_reference': [(4, self.id)]
                })

                job_id = self.id
                self.cost_sheet_ref.sudo()._variation_order_job(job_id)
                self.cost_sheet_ref.set_scope_section_table()

        return res

    def get_report_data(self, print_level_option):
        scope_sect_prod_dict = {}
        job_estimate_id = self
        cost_sheet_id = self.cost_sheet_ref
        contract_category = job_estimate_id.contract_category

        char_inc = 'A'
        for i, item in enumerate(job_estimate_id.project_scope_ids):
            scope_sect_prod_dict[item.project_scope.name] = {
                'field': 'scope',
                'no': chr(ord(char_inc) + i),
                'name': item.project_scope.name,
                'qty_before': '',
                'qty': '',
                'contractor_before': '',
                'contractor': '',
                'time_before': '',
                'time': '',
                'uom_before': '',
                'coefficient': '',
                'uom': '',
                'unit_price_before': '',
                'unit_price': '',
                'total_before': '',
                'total': '',
                'children': {},
                'counter': 1,
                '_subtotal': {
                    'field': 'scope',
                    'no': '',
                    'name': 'Subtotal ' + job_estimate_id.getRoman(i + 1),
                    'qty_before': '',
                    'qty': '',
                    'contractor_before': '',
                    'contractor': '',
                    'time_before': '',
                    'time': '',
                    'uom_before': '',
                    'coefficient': '',
                    'uom': '',
                    'unit_price_before': '',
                    'unit_price': '',
                    'total_before': item.subtotal,
                    'total': item.subtotal,
                    'children': {},
                    'counter': 1,
                },
            }

        for i, item in enumerate(job_estimate_id.section_ids):
            if scope_sect_prod_dict.get(item.project_scope.name, False):
                scope_sect_prod_dict[item.project_scope.name]['children'][item.section_name.name] = {
                    'field': 'section',
                    'no': scope_sect_prod_dict[item.project_scope.name]['counter'],
                    'name': item.section_name.name,
                    'qty_before': item.quantity,
                    'qty': item.quantity,
                    'contractor_before': '',
                    'contractor': '',
                    'time_before': '',
                    'time': '',
                    'uom_before': '',
                    'coefficient': '',
                    'uom': item.uom_id.name,
                    'unit_price_before': '',
                    'unit_price': '',
                    'total_before': item.subtotal,
                    'total': item.subtotal,
                    'children': {},
                    'counter': 'a',
                }
                scope_sect_prod_dict[item.project_scope.name]['counter'] += 1

        if print_level_option == '3_level':
            for field, key in ESTIMATES_DICT.items():
                item_dict = {}

                for x in job_estimate_id[field]:
                    item_key = str(x.project_scope.name) + '_' + str(x.section_name.name) + '_' + str(x[key].name)
                    if item_dict.get(item_key, False):
                        item_dict[item_key]['qty'] = item_dict[item_key]['qty_before'] + x.quantity
                        item_dict[item_key]['uom'] = x.uom_id.name
                        item_dict[item_key]['unit_price_before'] = x.budget_unit_price
                        item_dict[item_key]['unit_price'] = x.unit_price
                        item_dict[item_key]['total'] = x.subtotal
                    else:
                        item_dict[item_key] = {
                            'field': field,
                            'name': x[key].name,
                            'qty_before': x.budget_quantity if field != 'labour_estimation_ids' else 0,
                            'qty': x.quantity_after if field != 'labour_estimation_ids' else 0,
                            'contractor_before': x.budget_contractors if field == 'labour_estimation_ids' else 0,
                            'contractor': x.contractors_after if field == 'labour_estimation_ids' else 0,
                            'time_before': x.budget_time if field == 'labour_estimation_ids' else 0,
                            'time': x.time_after if field == 'labour_estimation_ids' else 0,
                            'uom_before': '',
                            'coefficient': x.coefficient,
                            'uom': x.uom_id.name,
                            'unit_price_before': x.budget_unit_price,
                            'unit_price': x.unit_price,
                            'total_before': 0,
                            'total': x.subtotal,
                            'children': {},
                        }

                for key, item in item_dict.items():
                    key_arr = key.split('_')
                    scope = key_arr[0]
                    section = key_arr[1]
                    product = key_arr[2]

                    if contract_category == 'var':
                        if item['field'] != 'labour_estimation_ids':
                            if item['qty_before'] == 0 and item['qty'] == 0: continue
                        else:
                            if item['contractor_before'] == 0 and item['contractor'] == 0 and item[
                                'time_before'] == 0 and item['time'] == 0: continue

                    try:
                        char_inc = scope_sect_prod_dict[scope]['children'][section]['counter']
                        scope_sect_prod_dict[scope]['children'][section]['children'][product] = {
                            'field': item['field'],
                            'no': char_inc,
                            'name': product,
                            'qty_before': item['qty_before'],
                            'qty': item['qty'],
                            'contractor_before': item['contractor_before'],
                            'contractor': item['contractor'],
                            'time_before': item['time_before'],
                            'time': item['time'],
                            'uom_before': item['uom_before'],
                            'coefficient': item['coefficient'],
                            'uom': item['uom'],
                            'unit_price_before': item['unit_price_before'],
                            'unit_price': item['unit_price'],
                            'total_before': item['total_before'],
                            'total': item['total'],
                            'children': {},
                        }
                        scope_sect_prod_dict[scope]['children'][section]['counter'] = chr(ord(char_inc) + 1)

                    except Exception as e:
                        continue

        return scope_sect_prod_dict

    def create_quotation(self):
        res = super(JobEstimate, self).create_quotation()
        if self.contract_category == 'var':
            context = {
                'default_job_estimate_id': self.id,
                'default_customer_id': self.partner_id.id,
                'default_project_id': self.project_id.id,
                'default_branch_id': self.branch_id.id,
                'default_cost_sheet_id': self.cost_sheet_ref.id,
                'default_project_budget_id': self.project_budget_id.id or False,
            }

            return {
                'type': 'ir.actions.act_window',
                'name': 'Create Quotation',
                'res_model': 'job.estimate.existing.quotation.const',
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
        return res

    @api.onchange('variable_ids')
    def update_material(self):
        # In variation order, this method only run when the variable_ids is newly added data
        if self.contract_category == "var":
            variable_list = []

            for rec in self.variable_ids.filtered(lambda x: x.is_vo_generated == False):
                material = []
                labour = []
                subcon = []
                overhead = []
                equip = []
                asset = []

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
                                        'uom_id': mat.uom_id.id,
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
                                        'uom_id': lab.uom_id.id,
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
                                        'uom_id': sub.uom_id.id,
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
                                        'uom_id': over.uom_id.id,
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
                                        'uom_id': eqp.uom_id.id,
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
                                for asse in self.internal_asset_ids:
                                    if asse.project_scope != False and asse.section_name != False and len(
                                            asse.variable_ref) != 0:
                                        if asse.project_scope == scope and asse.section_name == section and asse.variable_ref == variable:
                                            self.internal_asset_ids = [(2, asse.id)]
                                for ass in variable.asset_variable_ids:
                                    assx = (0, 0, {
                                        'asset_category_id': ass.asset_category_id.id,
                                        'asset_id': ass.asset_id.id,
                                        'quantity': var_quantity * ass.quantity,
                                        'subtotal': ass.unit_price * (var_quantity * ass.quantity),
                                        'unit_price': ass.unit_price,
                                        'uom_id': ass.uom_id.id,
                                        'project_scope': scope.id,
                                        'section_name': section.id,
                                        'variable_ref': variable.id,
                                        'description': ass.description,
                                    })
                                    asset.append(assx)
                                self.internal_asset_ids = asset
                        variable_list.append((scope.name, section.name, variable.name))

            for mat in self.material_estimation_ids:
                if not mat.is_vo_generated:
                    if mat.project_scope != False and mat.section_name != False and len(mat.variable_ref) != 0:
                        if (mat.project_scope.name, mat.section_name.name, mat.variable_ref.name) not in variable_list:
                            self.material_estimation_ids = [(2, mat.id)]
            for lab in self.labour_estimation_ids:
                if not lab.is_vo_generated:
                    if lab.project_scope != False and lab.section_name != False and len(lab.variable_ref) != 0:
                        if (lab.project_scope.name, lab.section_name.name, lab.variable_ref.name) not in variable_list:
                            self.labour_estimation_ids = [(2, lab.id)]
            for ov in self.overhead_estimation_ids:
                if not ov.is_vo_generated:
                    if ov.project_scope != False and ov.section_name != False and len(ov.variable_ref) != 0:
                        if (ov.project_scope.name, ov.section_name.name, ov.variable_ref.name) not in variable_list:
                            self.overhead_estimation_ids = [(2, ov.id)]
            for asset in self.internal_asset_ids:
                if not asset.is_vo_generated:
                    if asset.project_scope != False and asset.section_name != False and len(asset.variable_ref) != 0:
                        if (
                        asset.project_scope.name, asset.section_name.name, asset.variable_ref.name) not in variable_list:
                            self.internal_asset_ids = [(2, asset.id)]
            for eq in self.equipment_estimation_ids:
                if not eq.is_vo_generated:
                    if eq.project_scope != False and eq.section_name != False and len(eq.variable_ref) != 0:
                        if (eq.project_scope.name, eq.section_name.name, eq.variable_ref.name) not in variable_list:
                            self.equipment_estimation_ids = [(2, eq.id)]
            for sub in self.subcon_estimation_ids:
                if not sub.is_vo_generated:
                    if sub.project_scope != False and sub.section_name != False and len(sub.variable_ref) != 0:
                        if (sub.project_scope.name, sub.section_name.name, sub.variable_ref.name) not in variable_list:
                            self.subcon_estimation_ids = [(2, sub.id)]
        else:
            return super(JobEstimate, self).update_material()

    @api.onchange('material_estimation_ids')
    def _check_exist_group_of_product_material(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_material = []
            for line in self.material_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_material):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_material.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_material()

    @api.constrains('material_estimation_ids')
    def _check_exist_group_of_product_material_2(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_material = []
            for line in self.material_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_material):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_material.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_material_2()

    @api.onchange('labour_estimation_ids')
    def _check_exist_group_of_product_labour(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_labour1 = []
            for line in self.labour_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_labour1):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_labour1.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_labour()

    @api.constrains('labour_estimation_ids')
    def _check_exist_group_of_product_labour_2(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_labour1 = []
            for line in self.labour_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_labour1):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_labour1.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_labour_2()

    @api.onchange('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_overhead = []
            for line in self.overhead_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_overhead):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_overhead.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_overhead()

    @api.constrains('overhead_estimation_ids')
    def _check_exist_group_of_product_overhead_2(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_overhead = []
            for line in self.overhead_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_overhead):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_overhead.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_overhead()

    @api.onchange('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_equipment1 = []
            for line in self.equipment_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_equipment1):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_equipment1.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_equipment()

    @api.constrains('equipment_estimation_ids')
    def _check_exist_group_of_product_equipment_2(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_equipment1 = []
            for line in self.equipment_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.product_id.id)
                if (same in exist_section_group_list_equipment1):
                    raise ValidationError(
                        _('The product "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Product selected.' % (
                            (line.product_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_equipment1.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_equipment_2()

    @api.onchange('internal_asset_ids')
    def _check_exist_group_of_product_asset(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_asset1 = []
            for line in self.internal_asset_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.asset_id.id)
                if (same in exist_section_group_list_asset1):
                    raise ValidationError(
                        _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                            (line.asset_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_asset1.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_asset()

    @api.constrains('internal_asset_ids')
    def _check_exist_group_of_product_asset_2(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_group_list_asset1 = []
            for line in self.internal_asset_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.asset_id.id)
                if (same in exist_section_group_list_asset1):
                    raise ValidationError(
                        _('The Asset "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Asset selected.' % (
                            (line.asset_id.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_group_list_asset1.append(same)
        else:
            return super(JobEstimate, self)._check_exist_group_of_product_asset_2()

    @api.onchange('subcon_estimation_ids')
    def _check_exist_subcon(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_subcon_list_subcon = []
            for line in self.subcon_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.variable.id)
                if (same in exist_section_subcon_list_subcon):
                    raise ValidationError(
                        _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                            (line.variable.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_subcon_list_subcon.append(same)
        else:
            return super(JobEstimate, self)._check_exist_subcon()

    @api.constrains('subcon_estimation_ids')
    def _check_exist_subcon_2(self):
        if self.contract_category == 'var' and len(self.project_budget_ids) > 0:
            exist_section_subcon_list_subcon = []
            for line in self.subcon_estimation_ids:
                same = str(line.project_budget_id.id) + ' - ' + str(line.project_scope.id) + ' - ' + str(
                    line.section_name.id) + ' - ' + str(line.variable.id)
                if (same in exist_section_subcon_list_subcon):
                    raise ValidationError(
                        _('The Job Subcon "%s" already exists in project scope "%s" and section "%s", please change the Project Scope or Section or Job Subcon selected.' % (
                            (line.variable.name), (line.project_scope.name), (line.section_name.name))))
                exist_section_subcon_list_subcon.append(same)
        else:
            return super(JobEstimate, self)._check_exist_subcon_2()


class ProjectScopeEstimate(models.Model):
    _inherit = 'project.scope.estimate'

    is_vo_generated = fields.Boolean('Is VO Generated', default=False)


class SectionEstimate(models.Model):
    _inherit = 'section.estimate'

    is_vo_generated = fields.Boolean('Is VO Generated', default=False)


class VariableEstimate(models.Model):
    _inherit = "variable.estimate"

    is_vo_generated = fields.Boolean('Is VO Generated', default=False)


class MaterialEstimate(models.Model):
    _inherit = "material.estimate"

    current_quantity = fields.Float('Current Quantity', compute="_onchange_current_qty", store=True)
    budget_quantity = fields.Float('Budget Quantity', compute="_onchange_current_qty", store=True)
    cost_sheet_ref = fields.Many2one(related="material_id.cost_sheet_ref", string='Cost Sheet')
    project_budget_ids = fields.Many2many(related="material_id.project_budget_ids")
    project_budget_id = fields.Many2one('project.budget', string='Project Budget',)
    budget_unit_price = fields.Float('Budget Unit Price', compute="_onchange_current_qty", store=True)
    quantity_after = fields.Float('Quantity After', compute="_compute_quantity_after")
    is_vo_generated = fields.Boolean('Is VO Generated', default=False)
    cs_material_id = fields.Many2one('material.material', string='Cost Sheet Material')
    bd_material_id = fields.Many2one('budget.material', string='Budget Material')

    @api.depends('quantity')
    def _compute_quantity_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.quantity_after = rec.budget_quantity + rec.quantity
            else:
                rec.quantity_after = rec.quantity

    # removed to reduce load
    # def _compute_budget_unit_price(self):
    #     for rec in self:
    #         rec.budget_unit_price = 0
    #         if rec.contract_category == 'var':
    #             for cost in rec.cost_sheet_ref:
    #                 estimate_items = cost.material_ids.filtered(lambda x: x.project_scope.id == rec.project_scope._origin.id and x.section_name.id == rec.section_name._origin.id and x.group_of_product.id == rec.group_of_product._origin.id and x.product_id.id == rec.product_id._origin.id)
    #                 for estimate_item in estimate_items:
    #                     rec.budget_unit_price = estimate_item.price_unit

    def _get_quantity(self):
        for rec in self:
            rec.current_quantity = 0
            rec.budget_quantity = 0
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref and len(rec.project_budget_id) == 0:
                    if rec.cs_material_id:
                        rec.current_quantity = rec.cs_material_id.budgeted_qty_left
                        rec.budget_quantity = rec.cs_material_id.product_qty
                        rec.budget_unit_price = rec.cs_material_id.price_unit
                elif rec.cost_sheet_ref and rec.project_budget_id:
                    if rec.bd_material_id:
                        rec.current_quantity = rec.bd_material_id.qty_left
                        rec.budget_quantity = rec.bd_material_id.quantity
                        rec.budget_unit_price = rec.bd_material_id.cs_material_id.price_unit

    @api.depends('contract_category', 'project_scope', 'section_name', 'group_of_product', 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()
        # self._compute_budget_unit_price()

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        res = super(MaterialEstimate, self).onchange_quantity()
        for rec in self:
            if rec.contract_category == 'var':
                if rec.current_quantity + rec.quantity < 0:
                    raise ValidationError(_('You want to reduce quantity of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                else:
                    subtotal = (rec.budget_quantity + rec.quantity) * rec.unit_price
                    rec.subtotal = subtotal
        return res


class LabourEstimate(models.Model):
    _inherit = "labour.estimate"

    current_quantity = fields.Float('Current Quantity', compute="_onchange_current_qty", store=True)
    current_time = fields.Float('Current Time', compute="_onchange_current_qty", store=True)
    budget_time = fields.Float('Budget Time', compute="_onchange_current_qty", store=True)
    budget_contractors = fields.Float('Budget Contractors', compute="_onchange_current_qty", store=True)
    current_contractors = fields.Float('Current Contractors', compute="_onchange_current_qty", store=True)
    cost_sheet_ref = fields.Many2one(related="labour_id.cost_sheet_ref", string='Cost Sheet')
    project_budget_ids = fields.Many2many(related="labour_id.project_budget_ids")
    project_budget_id = fields.Many2one('project.budget', string='Project Budget', )
    budget_unit_price = fields.Float('Budget Unit Price', compute="_get_quantity", store=True)
    time_after = fields.Float('Quantity After', compute="_compute_time_after")
    contractors_after = fields.Integer('Contractors After', compute="_compute_contractors_after")
    is_vo_generated = fields.Boolean('Is VO Generated', default=False)
    cs_labour_id = fields.Many2one('material.labour', string='Cost Sheet Labour')
    bd_labour_id = fields.Many2one('budget.labour', string='Budget Labour')

    @api.depends('time')
    def _compute_time_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.time_after = rec.budget_time + rec.time
            else:
                rec.time_after = rec.time

    @api.depends('contractors')
    def _compute_contractors_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.contractors_after = rec.budget_contractors + rec.contractors
            else:
                rec.contractors_after = rec.contractors

    # removed to reduce load
    # def _compute_budget_unit_price(self):
    #     for rec in self:
    #         rec.budget_unit_price = 0
    #         if rec.contract_category == 'var':
    #             for cost in rec.cost_sheet_ref:
    #                 estimate_items = cost.material_labour_ids.filtered(lambda x: x.project_scope.id == rec.project_scope._origin.id and x.section_name.id == rec.section_name._origin.id and x.group_of_product.id == rec.group_of_product._origin.id and x.product_id.id == rec.product_id._origin.id)
    #                 for estimate_item in estimate_items:
    #                     rec.budget_unit_price = estimate_item.price_unit

    def _get_quantity(self):
        for rec in self:
            rec.write({'current_quantity': 0})
            rec.current_time = 0
            rec.current_contractors = 0
            rec.budget_time = 0
            rec.budget_contractors = 0
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref and len(rec.project_budget_id) == 0:
                    if rec.cs_labour_id:
                        rec.write({'current_quantity': rec.cs_labour_id.budgeted_qty_left})
                        rec.current_time = rec.cs_labour_id.time_left
                        rec.current_contractors = rec.cs_labour_id.contractors_left
                        rec.budget_time = rec.cs_labour_id.time
                        rec.budget_contractors = rec.cs_labour_id.contractors
                        rec.budget_unit_price = rec.cs_labour_id.price_unit
                elif rec.cost_sheet_ref and rec.project_budget_id:
                    if rec.bd_labour_id:
                        rec.write({'current_quantity': rec.bd_labour_id.qty_left})
                        rec.current_time = rec.bd_labour_id.time_left
                        rec.current_contractors = rec.bd_labour_id.contractors_left
                        rec.budget_time = rec.bd_labour_id.time
                        rec.budget_contractors = rec.bd_labour_id.contractors
                        rec.budget_unit_price = rec.bd_labour_id.cs_labour_id.price_unit

    @api.depends('contract_category', 'project_scope', 'section_name', 'group_of_product', 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()
        # self._compute_budget_unit_price()

    @api.onchange('contract_category', 'quantity', 'unit_price', 'contractors', 'time')
    def onchange_quantity(self):
        res = super(LabourEstimate, self).onchange_quantity()
        for rec in self:
            if rec.contract_category == 'var':
                if rec.current_contractors + rec.contractors < 0:
                    raise ValidationError(_('You want to reduce contractors of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                elif rec.current_time + rec.time < 0:
                    raise ValidationError(_('You want to reduce time of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                else:
                    subtotal = (rec.budget_time + rec.time) * (
                                rec.budget_contractors + rec.contractors) * rec.unit_price
                    rec.subtotal = subtotal
        return res


class OverheadEstimate(models.Model):
    _inherit = "overhead.estimate"

    current_quantity = fields.Float('Current Quantity', compute="_onchange_current_qty", store=True)
    budget_quantity = fields.Float('Budget Quantity', compute="_onchange_current_qty", store=True)
    cost_sheet_ref = fields.Many2one(related="overhead_id.cost_sheet_ref", string='Cost Sheet')
    project_budget_ids = fields.Many2many(related="overhead_id.project_budget_ids")
    project_budget_id = fields.Many2one('project.budget', string='Project Budget', )
    budget_unit_price = fields.Float('Budget Unit Price', compute="_get_quantity", store=True)
    quantity_after = fields.Float('Quantity After', compute="_compute_quantity_after")
    is_vo_generated = fields.Boolean('Is VO Generated', default=False)
    cs_overhead_id = fields.Many2one('material.overhead', string='Cost Sheet Overhead')
    bd_overhead_id = fields.Many2one('budget.overhead', string='Budget Overhead')

    @api.depends('quantity')
    def _compute_quantity_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.quantity_after = rec.budget_quantity + rec.quantity
            else:
                rec.quantity_after = rec.quantity

    # def _compute_budget_unit_price(self):
    #     for rec in self:
    #         rec.budget_unit_price = 0
    #         if rec.contract_category == 'var':
    #             for cost in rec.cost_sheet_ref:
    #                 estimate_items = cost.material_overhead_ids.filtered(lambda x: x.project_scope.id == rec.project_scope._origin.id and x.section_name.id == rec.section_name._origin.id and x.overhead_catagory == rec.overhead_catagory and x.group_of_product.id == rec.group_of_product._origin.id and x.product_id.id == rec.product_id._origin.id)
    #                 for estimate_item in estimate_items:
    #                     rec.budget_unit_price = estimate_item.price_unit

    def _get_quantity(self):
        for rec in self:
            rec.current_quantity = 0
            rec.budget_quantity = 0
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref and len(rec.project_budget_id) == 0:
                    if rec.cs_overhead_id:
                        rec.current_quantity = rec.cs_overhead_id.budgeted_qty_left
                        rec.budget_quantity = rec.cs_overhead_id.product_qty
                        rec.budget_unit_price = rec.cs_overhead_id.price_unit
                elif rec.cost_sheet_ref and rec.project_budget_id:
                    if rec.bd_overhead_id:
                        rec.current_quantity = rec.bd_overhead_id.qty_left
                        rec.budget_quantity = rec.bd_overhead_id.quantity
                        rec.budget_unit_price = rec.bd_overhead_id.cs_overhead_id.price_unit

    @api.depends('contract_category', 'project_scope', 'section_name', 'overhead_catagory', 'group_of_product',
                 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()
        # self._compute_budget_unit_price()

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        res = super(OverheadEstimate, self).onchange_quantity()
        for rec in self:
            if rec.contract_category == 'var':
                if rec.current_quantity + rec.quantity < 0:
                    raise ValidationError(_('You want to reduce quantity of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                else:
                    subtotal = (rec.budget_quantity + rec.quantity) * rec.unit_price
                    rec.subtotal = subtotal
        return res


class SubconEstimate(models.Model):
    _inherit = "subcon.estimate"

    current_quantity = fields.Float('Current Quantity', compute="_onchange_current_qty", store=True)
    budget_quantity = fields.Float('Budget Quantity', compute="_onchange_current_qty", store=True)
    cost_sheet_ref = fields.Many2one(related="subcon_id.cost_sheet_ref", string='Cost Sheet')
    project_budget_ids = fields.Many2many(related="subcon_id.project_budget_ids")
    project_budget_id = fields.Many2one('project.budget', string='Project Budget', )
    budget_unit_price = fields.Float('Budget Unit Price', compute="_onchange_current_qty", store=True)
    quantity_after = fields.Float('Quantity After', compute="_compute_quantity_after")
    is_vo_generated = fields.Boolean('Is VO Generated', default=False)
    cs_subcon_id = fields.Many2one('material.subcon', string='Cost Sheet Subcon')
    bd_subcon_id = fields.Many2one('budget.subcon', string='Budget Subcon')

    @api.depends('quantity')
    def _compute_quantity_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.quantity_after = rec.budget_quantity + rec.quantity
            else:
                rec.quantity_after = rec.quantity

    # def _compute_budget_unit_price(self):
    #     for rec in self:
    #         rec.budget_unit_price = 0
    #         if rec.contract_category == 'var':
    #             for cost in rec.cost_sheet_ref:
    #                 estimate_items = cost.material_subcon_ids.filtered(lambda x: x.project_scope.id == rec.project_scope._origin.id and x.section_name.id == rec.section_name._origin.id and x.variable.id == rec.variable._origin.id)
    #                 for estimate_item in estimate_items:
    #                     rec.budget_unit_price = estimate_item.price_unit

    def _get_quantity(self):
        for rec in self:
            rec.current_quantity = 0
            rec.budget_quantity = 0
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref and len(rec.project_budget_id) == 0:
                    if rec.cs_subcon_id:
                        rec.current_quantity = rec.cs_subcon_id.budgeted_qty_left
                        rec.budget_quantity = rec.cs_subcon_id.product_qty
                        rec.budget_unit_price = rec.cs_subcon_id.price_unit
                elif rec.cost_sheet_ref and rec.project_budget_id:
                    if rec.bd_subcon_id:
                        rec.current_quantity = rec.bd_subcon_id.qty_left
                        rec.budget_quantity = rec.bd_subcon_id.quantity
                        rec.budget_unit_price = rec.bd_subcon_id.cs_subcon_id.price_unit

    @api.depends('contract_category', 'project_scope', 'section_name', 'variable', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()
        # self._compute_budget_unit_price()

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        res = super(SubconEstimate, self).onchange_quantity()
        for rec in self:
            if rec.contract_category == 'var':
                if rec.current_quantity + rec.quantity < 0:
                    raise ValidationError(_('You want to reduce quantity of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                else:
                    subtotal = (rec.budget_quantity + rec.quantity) * rec.unit_price
                    rec.subtotal = subtotal
        return res


class EquipmentEstimate(models.Model):
    _inherit = "equipment.estimate"

    current_quantity = fields.Float('Current Quantity', compute="_onchange_current_qty", store=True)
    budget_quantity = fields.Float('Budget Quantity', compute="_onchange_current_qty", store=True)
    cost_sheet_ref = fields.Many2one(related="equipment_id.cost_sheet_ref", string='Cost Sheet')
    project_budget_ids = fields.Many2many(related="equipment_id.project_budget_ids")
    project_budget_id = fields.Many2one('project.budget', string='Project Budget', )
    budget_unit_price = fields.Float('Budget Unit Price', compute="_onchange_current_qty", store=True)
    quantity_after = fields.Float('Quantity After', compute="_compute_quantity_after")
    is_vo_generated = fields.Boolean('Is VO Generated', default=False)
    cs_equipment_id = fields.Many2one('material.equipment', string='Cost Sheet Equipment')
    bd_equipment_id = fields.Many2one('budget.equipment', string='Budget Equipment')

    @api.depends('quantity')
    def _compute_quantity_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.quantity_after = rec.budget_quantity + rec.quantity
            else:
                rec.quantity_after = rec.quantity

    # def _compute_budget_unit_price(self):
    #     for rec in self:
    #         rec.budget_unit_price = 0
    #         if rec.contract_category == 'var':
    #             for cost in rec.cost_sheet_ref:
    #                 estimate_items = cost.material_equipment_ids.filtered(lambda x: x.project_scope.id == rec.project_scope._origin.id and x.section_name.id == rec.section_name._origin.id and x.group_of_product.id == rec.group_of_product._origin.id and x.product_id.id == rec.product_id._origin.id)
    #                 for estimate_item in estimate_items:
    #                     rec.budget_unit_price = estimate_item.price_unit

    def _get_quantity(self):
        for rec in self:
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref and len(rec.project_budget_id) == 0:
                    if rec.cs_equipment_id:
                        rec.current_quantity = rec.cs_equipment_id.budgeted_qty_left
                        rec.budget_quantity = rec.cs_equipment_id.product_qty
                        rec.budget_unit_price = rec.cs_equipment_id.price_unit
                elif rec.cost_sheet_ref and rec.project_budget_id:
                    if rec.bd_equipment_id:
                        rec.current_quantity = rec.bd_equipment_id.qty_left
                        rec.budget_quantity = rec.bd_equipment_id.quantity
                        rec.budget_unit_price = rec.bd_equipment_id.cs_equipment_id.price_unit

    @api.depends('contract_category', 'project_scope', 'section_name', 'group_of_product', 'product_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()
        # self._compute_budget_unit_price()

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        res = super(EquipmentEstimate, self).onchange_quantity()
        for rec in self:
            if rec.contract_category == 'var':
                if rec.current_quantity + rec.quantity < 0:
                    raise ValidationError(_('You want to reduce quantity of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                else:
                    subtotal = (rec.budget_quantity + rec.quantity) * rec.unit_price
                    rec.subtotal = subtotal
        return res


class InternalAssets(models.Model):
    _inherit = "internal.assets"

    current_quantity = fields.Float('Current Quantity', compute="_onchange_current_qty", store=True)
    budget_quantity = fields.Float('Budget Quantity', compute="_onchange_current_qty", store=True)
    cost_sheet_ref = fields.Many2one(related="asset_job_id.cost_sheet_ref", string='Cost Sheet')
    project_budget_ids = fields.Many2many(related="asset_job_id.project_budget_ids")
    project_budget_id = fields.Many2one('project.budget', string='Project Budget', )
    budget_unit_price = fields.Float('Budget Unit Price', compute="_onchange_current_qty", store=True)
    quantity_after = fields.Float('Quantity After', compute="_compute_quantity_after")
    is_vo_generated = fields.Boolean('Is VO Generated', default=False)
    cs_internal_asset_id = fields.Many2one('internal.asset', string='Cost Sheet Internal Assets')
    bd_internal_asset_id = fields.Many2one('budget.internal.asset', string='Budget Internal Assets')

    @api.depends('quantity')
    def _compute_quantity_after(self):
        for rec in self:
            if rec.contract_category == 'var':
                rec.quantity_after = rec.budget_quantity + rec.quantity
            else:
                rec.quantity_after = rec.quantity

    # def _compute_budget_unit_price(self):
    #     for rec in self:
    #         rec.budget_unit_price = 0
    #         if rec.contract_category == 'var':
    #             for cost in rec.cost_sheet_ref:
    #                 estimate_items = cost.internal_asset_ids.filtered(lambda x: x.project_scope.id == rec.project_scope._origin.id and x.section_name.id == rec.section_name._origin.id and x.asset_category_id.id == rec.asset_category_id._origin.id and x.asset_id.id == rec.asset_id._origin.id)
    #                 for estimate_item in estimate_items:
    #                     rec.budget_unit_price = estimate_item.price_unit

    def _get_quantity(self):
        for rec in self:
            rec.current_quantity = 0
            rec.budget_quantity = 0
            if rec.contract_category == 'var':
                if rec.cost_sheet_ref and len(rec.project_budget_id) == 0:
                    if rec.cs_internal_asset_id:
                        rec.current_quantity = rec.cs_internal_asset_id.budgeted_qty_left
                        rec.budget_quantity = rec.cs_internal_asset_id.budgeted_qty
                        rec.budget_unit_price = rec.cs_internal_asset_id.price_unit
                elif rec.cost_sheet_ref and rec.project_budget_id:
                    if rec.bd_internal_asset_id:
                        rec.current_quantity = rec.bd_internal_asset_id.budgeted_qty_left
                        rec.budget_quantity = rec.bd_internal_asset_id.budgeted_qty
                        rec.budget_unit_price = rec.bd_internal_asset_id.cs_internal_asset_id.price_unit

    @api.depends('contract_category', 'project_scope', 'section_name', 'asset_category_id', 'asset_id', 'description',
                 'cost_sheet_ref')
    def _onchange_current_qty(self):
        self._get_quantity()
        # self._compute_budget_unit_price()

    @api.onchange('contract_category', 'quantity', 'unit_price')
    def onchange_quantity(self):
        res = super(InternalAssets, self).onchange_quantity()
        for rec in self:
            if rec.contract_category == 'var':
                if rec.current_quantity + rec.quantity < 0:
                    raise ValidationError(_('You want to reduce quantity of this product '
                                            'and it exceeds the Budgeted Quantity on Job Cost Sheet.'))
                else:
                    subtotal = (rec.budget_quantity + rec.quantity) * rec.unit_price
                    rec.subtotal = subtotal
        return res
