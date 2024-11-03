from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo import tools


class JobEstimateExistingQuotation(models.TransientModel):
    _inherit = 'job.estimate.existing.quotation.const'
    _description = 'Existing Quotation For Main Contract'

    cost_sheet_id = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    project_budget_id = fields.Many2one('project.budget', string='Project Budget')
    project_budget_ids = fields.Many2many(related='job_estimate_id.project_budget_ids', string='Project Budgets')
    budgeting_period = fields.Selection(related='cost_sheet_id.budgeting_period', string='Budgeting Period')

    @api.onchange('job_estimate_id')
    def _onchange_job_estimate_id(self):
        res = super(JobEstimateExistingQuotation, self)._onchange_job_estimate_id()
        if self.job_estimate_id and self.job_estimate_id.contract_category == 'var':
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

            material_lines = []
            self.material_estimation_wiz = False
            if job.material_estimation_ids:
                material_dict = {}
                for material in job.material_estimation_ids:
                    key_material = material.cs_material_id._origin.id
                    if material_dict.get(key_material, False):
                        material_dict[key_material]['material_boq_ids'].append((4, material.id))
                        # material_dict[key_material]['analytic_ids'].append((6, 0, material.analytic_idz.ids))
                        material_dict[key_material]['quantity'] += material.quantity
                        material_dict[key_material]['quantity_after'] += material.quantity
                        material_dict[key_material]['subtotal'] += material.quantity * material.unit_price
                    else:
                        material_dict[key_material] = {
                            'material_boq_ids': [(4, material.id)],
                            'cs_material_id': material.cs_material_id.id or False,
                            'bd_material_id': material.bd_material_id.id or False,
                            'project_scope': material.project_scope.id or False,
                            'section_name': material.section_name.id or False,
                            # 'variable_ref': material.variable_ref.id or False,
                            'group_of_product': material.group_of_product.id or False,
                            'product_id': material.product_id.id or False,
                            'description': material.description,
                            'analytic_ids': [(6, 0, material.analytic_idz.ids)] or False,
                            'budget_quantity': material.cs_material_id.product_qty,
                            'budget_unit_price': material.budget_unit_price,
                            'current_quantity': material.cs_material_id.budgeted_qty_left,
                            'quantity': material.quantity,
                            'uom_id': material.uom_id.id or False,
                            'unit_price': material.unit_price,
                            'subtotal': (material.cs_material_id.product_qty + material.quantity) * material.unit_price,
                            'quantity_after': material.cs_material_id.product_qty + material.quantity,
                        }
                    # material_lines.append((0, 0, {
                    #     'material_boq_ids': [(4, material.id)],
                    #     'cs_material_id': material.cs_material_id.id or False,
                    #     'bd_material_id': material.bd_material_id.id or False,
                    #     'project_scope': material.project_scope.id or False,
                    #     'section_name': material.section_name.id or False,
                    #     # 'variable_ref': material.variable_ref.id or False,
                    #     'group_of_product': material.group_of_product.id or False,
                    #     'product_id': material.product_id.id or False,
                    #     'description': material.description,
                    #     'analytic_ids': [(6, 0, material.analytic_idz.ids)] or False,
                    #     'budget_quantity': material.cs_material_id.product_qty,
                    #     'budget_unit_price': material.budget_unit_price,
                    #     'current_quantity': material.cs_material_id.budgeted_qty_left,
                    #     'quantity': material.quantity,
                    #     'uom_id': material.uom_id.id or False,
                    #     'unit_price': material.unit_price,
                    #     'subtotal': (material.cs_material_id.product_qty + material.quantity) * material.unit_price,
                    #     'quantity_after': material.quantity_after,
                    # }))
                material_lines = [(0, 0, item) for k, item in material_dict.items()]
            labour_lines = []
            self.labour_estimation_wiz = False
            if job.labour_estimation_ids:
                labour_dict = {}
                for labour in job.labour_estimation_ids:
                    key_labour = labour.cs_labour_id._origin.id
                    if labour_dict.get(key_labour, False):
                        labour_dict[key_labour]['labour_boq_ids'].append((4, labour.id))
                        # labour_dict[key_labour]['analytic_ids'].append((6, 0, labour.analytic_idz.ids))
                        labour_dict[key_labour]['time'] += labour.time
                        labour_dict[key_labour]['contractors'] += labour.contractors
                        labour_dict[key_labour]['time_after'] += labour.time
                        labour_dict[key_labour]['contractors_after'] += labour.contractors
                        labour_dict[key_labour]['subtotal'] += ((labour.cs_labour_id.contractors+labour.contractors)*(labour.cs_labour_id.time+labour.time)*labour.unit_price)-(labour.cs_labour_id.contractors*labour.time*labour.budget_unit_price)
                    else:
                        labour_dict[key_labour] = {
                            'labour_boq_ids': [(4, labour.id)],
                            'cs_labour_id': labour.cs_labour_id.id or False,
                            'bd_labour_id': labour.bd_labour_id.id or False,
                            'project_scope': labour.project_scope.id or False,
                            'section_name': labour.section_name.id or False,
                            # 'variable_ref': labour.variable_ref.id or False,
                            'group_of_product': labour.group_of_product.id or False,
                            'product_id': labour.product_id.id or False,
                            'description': labour.description,
                            'analytic_ids': [(6, 0, labour.analytic_idz.ids)] or False,
                            'budget_contractors': labour.cs_labour_id.contractors,
                            'budget_time': labour.cs_labour_id.time,
                            'budget_unit_price': labour.budget_unit_price,
                            'current_contractors': labour.cs_labour_id.contractors_left,
                            'current_time': labour.cs_labour_id.time_left,
                            'contractors': labour.contractors,
                            'time': labour.time,
                            'quantity': labour.quantity,
                            'uom_id': labour.uom_id.id or False,
                            'unit_price': labour.unit_price,
                            'subtotal': (labour.cs_labour_id.time + labour.time) * (labour.cs_labour_id.contractors + labour.contractors) * labour.unit_price,
                            'contractors_after': labour.contractors + labour.cs_labour_id.contractors,
                            'time_after': labour.cs_labour_id.time + labour.time,
                        }
                    # labour_lines.append((0, 0, {
                    #     'cs_labour_id': labour.cs_labour_id.id or False,
                    #     'bd_labour_id': labour.bd_labour_id.id or False,
                    #     'project_scope': labour.project_scope.id or False,
                    #     'section_name': labour.section_name.id or False,
                    #     # 'variable_ref': labour.variable_ref.id or False,
                    #     'group_of_product': labour.group_of_product.id or False,
                    #     'product_id': labour.product_id.id or False,
                    #     'description': labour.description,
                    #     'analytic_ids': [(6, 0, labour.analytic_idz.ids)] or False,
                    #     'budget_contractors': labour.cs_labour_id.contractors,
                    #     'budget_time': labour.cs_labour_id.time,
                    #     'budget_unit_price': labour.budget_unit_price,
                    #     'current_contractors': labour.cs_labour_id.contractors_left,
                    #     'current_time': labour.cs_labour_id.time_left,
                    #     'contractors': labour.contractors,
                    #     'time': labour.time,
                    #     'quantity': labour.quantity,
                    #     'uom_id': labour.uom_id.id or False,
                    #     'unit_price': labour.unit_price,
                    #     'subtotal': (labour.cs_labour_id.time + labour.time) * (labour.cs_labour_id.contractors + labour.contractors) * labour.unit_price,
                    #     'contractors_after': labour.contractors_after,
                    #     'time_after': labour.time_after,
                    # }))
                labour_lines = [(0, 0, item) for k, item in labour_dict.items()]
            overhead_lines = []
            self.overhead_estimation_wiz = False
            if job.overhead_estimation_ids:
                overhead_dict = {}
                for overhead in job.overhead_estimation_ids:
                    key_overhead = overhead.cs_overhead_id._origin.id
                    if overhead_dict.get(key_overhead, False):
                        overhead_dict[key_overhead]['overhead_boq_ids'].append((4, overhead.id))
                        # overhead_dict[key_overhead]['analytic_ids'].append((6, 0, overhead.analytic_idz.ids))
                        overhead_dict[key_overhead]['quantity'] += overhead.quantity
                        overhead_dict[key_overhead]['quantity_after'] += overhead.quantity
                        overhead_dict[key_overhead]['subtotal'] += overhead.quantity * overhead.unit_price
                    else:
                        overhead_dict[key_overhead] = {
                            'overhead_boq_ids': [(4, overhead.id)],
                            'cs_overhead_id': overhead.cs_overhead_id.id or False,
                            'bd_overhead_id': overhead.bd_overhead_id.id or False,
                            'project_scope': overhead.project_scope.id or False,
                            'section_name': overhead.section_name.id or False,
                            'overhead_catagory': overhead.overhead_catagory or False,
                            # 'variable_ref': overhead.variable_ref.id or False,
                            'group_of_product': overhead.group_of_product.id or False,
                            'product_id': overhead.product_id.id or False,
                            'description': overhead.description,
                            'analytic_ids': [(6, 0, overhead.analytic_idz.ids)] or False,
                            'budget_quantity': overhead.cs_overhead_id.product_qty,
                            'budget_unit_price': overhead.budget_unit_price,
                            'current_quantity': overhead.cs_overhead_id.budgeted_qty_left,
                            'quantity': overhead.quantity,
                            'uom_id': overhead.uom_id.id or False,
                            'unit_price': overhead.unit_price,
                            'subtotal': (overhead.cs_overhead_id.product_qty + overhead.quantity) * overhead.unit_price,
                            'quantity_after': overhead.cs_overhead_id.product_qty + overhead.quantity,
                        }
                    # overhead_lines.append((0, 0, {
                    #     'cs_overhead_id': overhead.cs_overhead_id.id or False,
                    #     'bd_overhead_id': overhead.bd_overhead_id.id or False,
                    #     'project_scope': overhead.project_scope.id or False,
                    #     'section_name': overhead.section_name.id or False,
                    #     'overhead_catagory': overhead.overhead_catagory or False,
                    #     # 'variable_ref': overhead.variable_ref.id or False,
                    #     'group_of_product': overhead.group_of_product.id or False,
                    #     'product_id': overhead.product_id.id or False,
                    #     'description': overhead.description,
                    #     'analytic_ids': [(6, 0, overhead.analytic_idz.ids)] or False,
                    #     'budget_quantity': overhead.cs_overhead_id.product_qty,
                    #     'budget_unit_price': overhead.budget_unit_price,
                    #     'current_quantity': overhead.cs_overhead_id.budgeted_qty_left,
                    #     'quantity': overhead.quantity,
                    #     'uom_id': overhead.uom_id.id or False,
                    #     'unit_price': overhead.unit_price,
                    #     'subtotal': (overhead.cs_overhead_id.product_qty + overhead.quantity) * overhead.unit_price,
                    #     'quantity_after': overhead.quantity_after,
                    # }))
                overhead_lines = [(0, 0, item) for k, item in overhead_dict.items()]
            asset_lines = []
            self.internal_asset_wiz = False
            if job.internal_asset_ids:
                asset_dict = {}
                for asset in job.internal_asset_ids:
                    key_asset = asset.cs_internal_asset_id._origin.id
                    if asset_dict.get(key_asset, False):
                        asset_dict[key_asset]['asset_boq_ids'].append((4, asset.id))
                        # asset_dict[key_asset]['analytic_ids'].append((6, 0, asset.analytic_idz.ids))
                        asset_dict[key_asset]['quantity'] += asset.quantity
                        asset_dict[key_asset]['quantity_after'] += asset.quantity
                        asset_dict[key_asset]['subtotal'] += asset.quantity * asset.unit_price
                    else:
                        asset_dict[key_asset] = {
                            'asset_boq_ids': [(4, asset.id)],
                            'cs_internal_asset_id': asset.cs_internal_asset_id.id or False,
                            'bd_internal_asset_id': asset.bd_internal_asset_id.id or False,
                            'project_scope': asset.project_scope.id or False,
                            'section_name': asset.section_name.id or False,
                            # 'variable_ref': asset.variable_ref.id or False,
                            'asset_category_id': asset.asset_category_id.id or False,
                            'asset_id': asset.asset_id.id or False,
                            'description': asset.description,
                            'analytic_ids': [(6, 0, asset.analytic_idz.ids)] or False,
                            'budget_quantity': asset.cs_internal_asset_id.budgeted_qty,
                            'budget_unit_price': asset.budget_unit_price,
                            'current_quantity': asset.cs_internal_asset_id.budgeted_qty_left,
                            'quantity': asset.quantity,
                            'uom_id': asset.uom_id.id or False,
                            'unit_price': asset.unit_price,
                            'subtotal': (asset.cs_internal_asset_id.budgeted_qty + asset.quantity) * asset.unit_price,
                            'quantity_after': asset.cs_internal_asset_id.budgeted_qty + asset.quantity,
                        }
                    # asset_lines.append((0, 0, {
                    #     'cs_internal_asset_id': asset.cs_internal_asset_id.id or False,
                    #     'bd_internal_asset_id': asset.bd_internal_asset_id.id or False,
                    #     'project_scope': asset.project_scope.id or False,
                    #     'section_name': asset.section_name.id or False,
                    #     # 'variable_ref': asset.variable_ref.id or False,
                    #     'asset_category_id': asset.asset_category_id.id or False,
                    #     'asset_id': asset.asset_id.id or False,
                    #     'description': asset.description,
                    #     'analytic_ids': [(6, 0, asset.analytic_idz.ids)] or False,
                    #     'budget_quantity': asset.cs_internal_asset_id.budgeted_qty,
                    #     'budget_unit_price': asset.budget_unit_price,
                    #     'current_quantity': asset.cs_internal_asset_id.budgeted_qty_left,
                    #     'quantity': asset.quantity,
                    #     'uom_id': asset.uom_id.id or False,
                    #     'unit_price': asset.unit_price,
                    #     'subtotal': (asset.cs_internal_asset_id.budgeted_qty + asset.quantity) * asset.unit_price,
                    #     'quantity_after': asset.quantity_after,
                    # }))
                asset_lines = [(0, 0, item) for k, item in asset_dict.items()]
            equipment_lines = []
            self.equipment_estimation_wiz = False
            if job.equipment_estimation_ids:
                equipment_dict = {}
                for equipment in job.equipment_estimation_ids:
                    key_equipment = equipment.cs_equipment_id._origin.id
                    if equipment_dict.get(key_equipment, False):
                        equipment_dict[key_equipment]['equipment_boq_ids'].append((4, equipment.id))
                        # equipment_dict[key_equipment]['analytic_ids'].append((6, 0, equipment.analytic_idz.ids))
                        equipment_dict[key_equipment]['quantity'] += equipment.quantity
                        equipment_dict[key_equipment]['quantity_after'] += equipment.quantity
                        equipment_dict[key_equipment]['subtotal'] += equipment.quantity * equipment.unit_price
                    else:
                        equipment_dict[key_equipment] = {
                            'equipment_boq_ids': [(4, equipment.id)],
                            'cs_equipment_id': equipment.cs_equipment_id.id or False,
                            'bd_equipment_id': equipment.bd_equipment_id.id or False,
                            'project_scope': equipment.project_scope.id or False,
                            'section_name': equipment.section_name.id or False,
                            # 'variable_ref': equipment.variable_ref.id or False,
                            'group_of_product': equipment.group_of_product.id or False,
                            'product_id': equipment.product_id.id or False,
                            'description': equipment.description,
                            'analytic_ids': [(6, 0, equipment.analytic_idz.ids)] or False,
                            'budget_quantity': equipment.cs_equipment_id.product_qty,
                            'budget_unit_price': equipment.budget_unit_price,
                            'current_quantity': equipment.cs_equipment_id.budgeted_qty_left,
                            'quantity': equipment.quantity,
                            'uom_id': equipment.uom_id.id or False,
                            'unit_price': equipment.unit_price,
                            'subtotal': (equipment.cs_equipment_id.product_qty + equipment.quantity) * equipment.unit_price,
                            'quantity_after': equipment.cs_equipment_id.product_qty + equipment.quantity,
                        }
                    # equipment_lines.append((0, 0, {
                    #     'cs_equipment_id': equipment.cs_equipment_id.id or False,
                    #     'bd_equipment_id': equipment.bd_equipment_id.id or False,
                    #     'project_scope': equipment.project_scope.id or False,
                    #     'section_name': equipment.section_name.id or False,
                    #     # 'variable_ref': equipment.variable_ref.id or False,
                    #     'group_of_product': equipment.group_of_product.id or False,
                    #     'product_id': equipment.product_id.id or False,
                    #     'description': equipment.description,
                    #     'analytic_ids': [(6, 0, equipment.analytic_idz.ids)] or False,
                    #     'budget_quantity': equipment.cs_equipment_id.product_qty,
                    #     'budget_unit_price': equipment.budget_unit_price,
                    #     'current_quantity': equipment.cs_equipment_id.budgeted_qty_left,
                    #     'quantity': equipment.quantity,
                    #     'uom_id': equipment.uom_id.id or False,
                    #     'unit_price': equipment.unit_price,
                    #     'subtotal': (equipment.cs_equipment_id.product_qty + equipment.quantity) * equipment.unit_price,
                    #     'quantity_after': equipment.quantity_after,
                    # }))
                equipment_lines = [(0, 0, item) for k, item in equipment_dict.items()]
            subcon_lines = []
            self.subcon_estimation_wiz = False
            if job.subcon_estimation_ids:
                subcon_dict = {}
                for subcon in job.subcon_estimation_ids:
                    key_subcon = subcon.cs_subcon_id._origin.id
                    if subcon_dict.get(key_subcon, False):
                        subcon_dict[key_subcon]['subcon_boq_ids'].append((4, subcon.id))
                        # subcon_dict[key_subcon]['analytic_ids'].append((6, 0, subcon.analytic_idz.ids))
                        subcon_dict[key_subcon]['quantity'] += subcon.quantity
                        subcon_dict[key_subcon]['quantity_after'] += subcon.quantity
                        subcon_dict[key_subcon]['subtotal'] += subcon.quantity * subcon.unit_price
                    else:
                        subcon_dict[key_subcon] = {
                            'subcon_boq_ids': [(4, subcon.id)],
                            'cs_subcon_id': subcon.cs_subcon_id.id or False,
                            'bd_subcon_id': subcon.bd_subcon_id.id or False,
                            'project_scope': subcon.project_scope.id or False,
                            'section_name': subcon.section_name.id or False,
                            # 'variable_ref': subcon.variable_ref.id or False,
                            'variable': subcon.variable.id or False,
                            'description': subcon.description,
                            'analytic_ids': [(6, 0, subcon.analytic_idz.ids)] or False,
                            'budget_quantity': subcon.cs_subcon_id.product_qty,
                            'budget_unit_price': subcon.budget_unit_price,
                            'current_quantity': subcon.cs_subcon_id.budgeted_qty_left,
                            'quantity': subcon.quantity,
                            'uom_id': subcon.uom_id.id or False,
                            'unit_price': subcon.unit_price,
                            'subtotal': (subcon.cs_subcon_id.product_qty + subcon.quantity) * subcon.unit_price,
                            'quantity_after': subcon.cs_subcon_id.product_qty + subcon.quantity,
                        }
                subcon_lines = [(0, 0, item) for k, item in subcon_dict.items()]

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

            if len(self.project_budget_ids) > 0:
                job = self.job_estimate_id
                cost_sheet = self.cost_sheet_id
                project_budget = self.project_budget_id
                cs_material_ids = self.material_estimation_wiz.mapped('cs_material_id').ids
                cs_labour_ids = self.labour_estimation_wiz.mapped('cs_labour_id').ids
                cs_subcon_ids = self.subcon_estimation_wiz.mapped('cs_subcon_id').ids
                cs_overhead_ids = self.overhead_estimation_wiz.mapped('cs_overhead_id').ids
                cs_internal_asset_ids = self.internal_asset_wiz.mapped('cs_internal_asset_id').ids
                cs_equipment_ids = self.equipment_estimation_wiz.mapped('cs_equipment_id').ids

                material_lines = []
                # self.material_estimation_wiz = False
                for material in cost_sheet.material_ids.filtered(lambda x: x.id not in cs_material_ids):
                    material_lines.append((0, 0, {
                        'cs_material_id': material.id or False,
                        'project_scope': material.project_scope.id or False,
                        'section_name': material.section_name.id or False,
                        # 'variable_ref': material.variable_ref.id or False,
                        'group_of_product': material.group_of_product.id or False,
                        'product_id': material.product_id.id or False,
                        'description': material.description,
                        # 'analytic_ids': [(6, 0, material.analytic_idz.ids)] or False,
                        'budget_quantity': material.product_qty,
                        'budget_unit_price': material.price_unit,
                        'current_quantity': material.budgeted_qty_left,
                        'quantity': 0,
                        'uom_id': material.uom_id.id or False,
                        'unit_price': material.price_unit,
                        'subtotal': material.material_amount_total,
                        'quantity_after': material.product_qty,
                    }))

                labour_lines = []
                # self.labour_estimation_wiz = False
                for labour in cost_sheet.material_labour_ids.filtered(lambda x: x.id not in cs_labour_ids):
                    if labour.id not in cs_labour_ids:
                        labour_lines.append((0, 0, {
                            'cs_labour_id': labour.id or False,
                            'project_scope': labour.project_scope.id or False,
                            'section_name': labour.section_name.id or False,
                            # 'variable_ref': labour.variable_ref.id or False,
                            'group_of_product': labour.group_of_product.id or False,
                            'product_id': labour.product_id.id or False,
                            'description': labour.description,
                            # 'analytic_ids': [(6, 0, labour.analytic_idz.ids)] or False,
                            'budget_contractors': labour.contractors,
                            'budget_time': labour.time,
                            'budget_unit_price': labour.price_unit,
                            'current_contractors': labour.contractors_left,
                            'current_time': labour.time_left,
                            'contractors': 0,
                            'time': 0,
                            'quantity': 0,
                            'uom_id': labour.uom_id.id or False,
                            'unit_price': labour.price_unit,
                            'subtotal': labour.labour_amount_total,
                            'contractors_after': labour.contractors,
                            'time_after': labour.time,
                        }))

                overhead_lines = []
                # self.overhead_estimation_wiz = False
                for overhead in cost_sheet.material_overhead_ids.filtered(lambda x: x.id not in cs_overhead_ids):
                    overhead_lines.append((0, 0, {
                        'cs_overhead_id': overhead.id or False,
                        'project_scope': overhead.project_scope.id or False,
                        'section_name': overhead.section_name.id or False,
                        'overhead_catagory': overhead.overhead_catagory or False,
                        # 'variable_ref': overhead.variable_ref.id or False,
                        'group_of_product': overhead.group_of_product.id or False,
                        'product_id': overhead.product_id.id or False,
                        'description': overhead.description,
                        # 'analytic_ids': [(6, 0, overhead.analytic_idz.ids)] or False,
                        'budget_quantity': overhead.product_qty,
                        'budget_unit_price': overhead.price_unit,
                        'current_quantity': overhead.budgeted_qty_left,
                        'quantity': 0,
                        'uom_id': overhead.uom_id.id or False,
                        'unit_price': overhead.price_unit,
                        'subtotal': overhead.overhead_amount_total,
                        'quantity_after': overhead.product_qty,
                    }))

                asset_lines = []
                # self.internal_asset_wiz = False
                for asset in cost_sheet.internal_asset_ids.filtered(lambda x: x.id not in cs_internal_asset_ids):
                    asset_lines.append((0, 0, {
                        'cs_internal_asset_id': asset.id or False,
                        'project_scope': asset.project_scope.id or False,
                        'section_name': asset.section_name.id or False,
                        # 'variable_ref': asset.variable_ref.id or False,
                        'asset_category_id': asset.asset_category_id.id or False,
                        'asset_id': asset.asset_id.id or False,
                        'description': asset.description,
                        # 'analytic_ids': [(6, 0, asset.analytic_idz.ids)] or False,
                        'budget_quantity': asset.budgeted_qty,
                        'budget_unit_price': asset.price_unit,
                        'current_quantity': asset.budgeted_qty_left,
                        'quantity': 0,
                        'uom_id': asset.uom_id.id or False,
                        'unit_price': asset.price_unit,
                        'subtotal': asset.budgeted_amt,
                        'quantity_after': asset.budgeted_qty,
                    }))

                equipment_lines = []
                # self.equipment_estimation_wiz = False
                for equipment in cost_sheet.material_equipment_ids.filtered(lambda x: x.id not in cs_equipment_ids):
                    equipment_lines.append((0, 0, {
                        'cs_equipment_id': equipment.id or False,
                        'project_scope': equipment.project_scope.id or False,
                        'section_name': equipment.section_name.id or False,
                        # 'variable_ref': equipment.variable_ref.id or False,
                        'group_of_product': equipment.group_of_product.id or False,
                        'product_id': equipment.product_id.id or False,
                        'description': equipment.description,
                        # 'analytic_ids': [(6, 0, equipment.analytic_idz.ids)] or False,
                        'budget_quantity': equipment.product_qty,
                        'budget_unit_price': equipment.price_unit,
                        'current_quantity': equipment.budgeted_qty_left,
                        'quantity': 0,
                        'uom_id': equipment.uom_id.id or False,
                        'unit_price': equipment.price_unit,
                        'subtotal': equipment.equipment_amount_total,
                        'quantity_after': equipment.product_qty,
                    }))

                subcon_lines = []
                # self.subcon_estimation_wiz = False
                for subcon in cost_sheet.material_subcon_ids.filtered(lambda x: x.id not in cs_subcon_ids):
                    subcon_lines.append((0, 0, {
                        'cs_subcon_id': subcon.id or False,
                        'project_scope': subcon.project_scope.id or False,
                        'section_name': subcon.section_name.id or False,
                        # 'variable_ref': subcon.variable_ref.id or False,
                        'variable': subcon.variable.id or False,
                        'description': subcon.description,
                        # 'analytic_ids': [(6, 0, subcon.analytic_idz.ids)] or False,
                        'budget_quantity': subcon.product_qty,
                        'budget_unit_price': subcon.price_unit,
                        'current_quantity': subcon.budgeted_qty_left,
                        'quantity': 0,
                        'uom_id': subcon.uom_id.id or False,
                        'unit_price': subcon.price_unit,
                        'subtotal': subcon.subcon_amount_total,
                        'quantity_after': subcon.product_qty,
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

                scope = []
                project_scope_ids = cost_sheet.contract_history_ids[-1].contract_history.project_scope_ids
                changed_scope = self.project_scope_wiz.mapped('project_scope').ids
                for sco in project_scope_ids.filtered(lambda x: x.project_scope.id not in changed_scope):
                    scope.append((0, 0, {
                        'project_scope': sco.project_scope.id or False,
                        'description': sco.description,
                        # 'subtotal': sco.subtotal,
                    }))

                if len(scope) > 0:
                    self.project_scope_wiz = scope

                section = []
                section_ids = cost_sheet.contract_history_ids[-1].contract_history.section_ids
                changed_section = self.section_wiz.mapped('section_name').ids
                for sec in section_ids.filtered(lambda x: x.section.id not in changed_section):
                    section.append((0, 0, {
                        'project_scope': sec.project_scope.id or False,
                        'section_name': sec.section.id or False,
                        'description': sec.description,
                        'quantity': sec.quantity,
                        'uom_id': sec.uom_id.id or False,
                        # 'subtotal': sec.subtotal,
                    }))

                if len(section) > 0:
                    self.section_wiz = section

        return res

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
                for material in rec.material_estimation_wiz:
                    if material.is_active:
                        if material.budget_unit_price != material.unit_price:
                            total_material += (material.budget_quantity + material.quantity) * ((material.unit_price - material.budget_unit_price) + material.budget_unit_price) - (
                                                          material.budget_quantity * material.budget_unit_price)
                        else:
                            total_material += material.unit_price * material.quantity
                for labour in rec.labour_estimation_wiz:
                    if labour.is_active:
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
                            total_labour += ((budget_contractors+contractors)*(budget_time+time)*unit_price)-(budget_contractors*budget_time*budget_unit_price)
                for subcon in rec.subcon_estimation_wiz:
                    if subcon.is_active:
                        if subcon.budget_unit_price != subcon.unit_price:
                            total_subcon += (subcon.budget_quantity + subcon.quantity) * ((subcon.unit_price - subcon.budget_unit_price) + subcon.budget_unit_price) - (subcon.budget_quantity * subcon.budget_unit_price)
                        else:
                            total_subcon += subcon.unit_price * subcon.quantity

                for overhead in rec.overhead_estimation_wiz:
                    if overhead.is_active:
                        if overhead.budget_unit_price != overhead.unit_price:
                            total_overhead += (overhead.budget_quantity + overhead.quantity) * ((overhead.unit_price - overhead.budget_unit_price) + overhead.budget_unit_price) - (
                                               overhead.budget_quantity * overhead.budget_unit_price)
                        else:
                            total_overhead += overhead.unit_price * overhead.quantity

                for equipment in rec.equipment_estimation_wiz:
                    if equipment.is_active:
                        if equipment.budget_unit_price != equipment.unit_price:
                            total_equipment += (equipment.budget_quantity + equipment.quantity) * ((equipment.unit_price - equipment.budget_unit_price) + equipment.budget_unit_price) - (
                                                equipment.budget_quantity * equipment.budget_unit_price)
                        else:
                            total_equipment += equipment.unit_price * equipment.quantity

                for asset in rec.internal_asset_wiz:
                    if asset.is_active:
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

    def action_confirm(self, is_set_projects_type=False, project_template_id=False):
        res = super(JobEstimateExistingQuotation, self).action_confirm(self.job_estimate_id.is_set_projects_type, self.job_estimate_id.project_template_id.id)
        ctx = self._context
        if self.contract_category == 'var':
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
                                 "material_boq_ids": [(6, 0, material.material_boq_ids.ids)] or False,
                                 "cs_material_id": material.cs_material_id.id or False,
                                 "bd_material_id": material.bd_material_id.id or False,
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
                                 "budget_unit_price": material.budget_unit_price,
                                 "quantity_after": material.quantity_after,
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
                                 "labour_boq_ids": [(6, 0, labour.labour_boq_ids.ids)] or False,
                                 "cs_labour_id": labour.cs_labour_id.id or False,
                                 "bd_labour_id": labour.bd_labour_id.id or False,
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
                                 "contractors_after": labour.contractors_after,
                                 "time_after": labour.time_after,
                                 "contractors": labour.contractors,
                                 "time": labour.time,
                                 "quantity": labour.quantity,
                                 "uom_id": labour.uom_id.id or False,
                                 "budget_unit_price": labour.budget_unit_price,
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
                                 "subcon_boq_ids": [(6, 0, subcon.subcon_boq_ids.ids)] or False,
                                 "cs_subcon_id": subcon.cs_subcon_id.id or False,
                                 "bd_subcon_id": subcon.bd_subcon_id.id or False,
                                 "project_scope": subcon.project_scope.id or False,
                                 "section_name": subcon.section_name.id or False,
                                 # "variable_ref": subcon.variable_ref.id or False,
                                 "type": "subcon",
                                 "subcon_id": subcon.variable.id or False,
                                 "description": subcon.description,
                                 "analytic_idz": [(6, 0, subcon.analytic_ids.ids)] or False,
                                 'budget_quantity': subcon.budget_quantity,
                                 "current_quantity": subcon.current_quantity,
                                 "budget_unit_price": subcon.budget_unit_price,
                                 "quantity_after": subcon.quantity_after,
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
                                 "internal_asset_boq_ids": [(6, 0, internal_asset.asset_boq_ids.ids)] or False,
                                 "cs_internal_asset_id": internal_asset.cs_internal_asset_id.id or False,
                                 "bd_internal_asset_id": internal_asset.bd_internal_asset_id.id or False,
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
                                 "budget_unit_price": internal_asset.budget_unit_price,
                                 "quantity_after": internal_asset.quantity_after,
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
                                 "equipment_boq_ids": [(6, 0, equipment.equipment_boq_ids.ids)] or False,
                                 "cs_equipment_id": equipment.cs_equipment_id.id or False,
                                 "bd_equipment_id": equipment.bd_equipment_id.id or False,
                                 "project_scope": equipment.project_scope.id or False,
                                 "section_name": equipment.section_name.id or False,
                                 # "variable_ref": equipment.variable_ref.id or False,
                                 "type": "equipment",
                                 "group_of_product": equipment.group_of_product.id or False,
                                 "equipment_id": equipment.product_id.id or False,
                                 "description": equipment.description,
                                 "analytic_idz": equipment.analytic_ids and [
                                     (6, 0, equipment.analytic_ids.ids)] or False,
                                 'budget_quantity': equipment.budget_quantity,
                                 "current_quantity": equipment.current_quantity,
                                 "budget_unit_price": equipment.budget_unit_price,
                                 "quantity_after": equipment.quantity_after,
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
                                 "overhead_boq_ids": [(6, 0, overhead.overhead_boq_ids.ids)] or False,
                                 "cs_overhead_id": overhead.cs_overhead_id.id or False,
                                 "bd_overhead_id": overhead.bd_overhead_id.id or False,
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
                                 "budget_unit_price": overhead.budget_unit_price,
                                 "quantity_after": overhead.quantity_after,
                                 "quantity": overhead.quantity,
                                 "uom_id": overhead.uom_id.id or False,
                                 "unit_price": overhead.unit_price,
                                 "subtotal": overhead.subtotal,
                                 "overhead_catagory": overhead.overhead_catagory,
                             },
                             )
                        )

                context = {
                    'is_wizard': is_wizard,
                    'default_job_references': [(4, rec.job_estimate_id.id)],
                    'default_project_id': rec.project_id.id,
                    'default_project_budget_ids': [(6, 0, rec.project_budget_ids.ids)],
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

        return res


class JobEstimateExistingLineMaterial(models.TransientModel):
    _inherit = "job.estimate.existing.line.material"

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_material_id = fields.Many2one('material.material', string='Cost Sheet Material')
    bd_material_id = fields.Many2one('budget.material', string='Budget Material')
    material_boq_ids = fields.Many2many('material.estimate', 'quotation_wizard_material_boq_rel', string='Material BOQ')


class JobEstimateExistingQuotationLabour(models.TransientModel):
    _inherit = "job.estimate.existing.line.labour"
    
    budget_unit_price = fields.Float('Budget Unit Price')
    contractors_after = fields.Float('Contractors After')
    time_after = fields.Float('Time After')
    cs_labour_id = fields.Many2one('material.labour', string='Cost Sheet Labour')
    bd_labour_id = fields.Many2one('budget.labour', string='Budget Labour')
    labour_boq_ids = fields.Many2many('labour.estimate', 'quotation_wizard_labour_boq_rel', string='Labour BOQ')


class JobEstimateExistingQuotationSubcon(models.TransientModel):
    _inherit = "job.estimate.existing.line.subcon"

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_subcon_id = fields.Many2one('material.subcon', string='Cost Sheet Subcon')
    bd_subcon_id = fields.Many2one('budget.subcon', string='Budget Subcon')
    subcon_boq_ids = fields.Many2many('subcon.estimate', 'quotation_wizard_subcon_boq_rel', string='Subcon BOQ')


class JobEstimateExistingQuotationInternalAsset(models.TransientModel):
    _inherit = "job.estimate.existing.line.asset"

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_internal_asset_id = fields.Many2one('internal.asset', string='Cost Sheet Asset')
    bd_internal_asset_id = fields.Many2one('budget.internal.asset', string='Budget Asset')
    asset_boq_ids = fields.Many2many('internal.assets', 'quotation_wizard_asset_boq_rel', string='Asset BOQ')


class JobEstimateExistingQuotationEquipment(models.TransientModel):
    _inherit = "job.estimate.existing.line.equipment"

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_equipment_id = fields.Many2one('material.equipment', string='Cost Sheet Equipment')
    bd_equipment_id = fields.Many2one('budget.equipment', string='Budget Equipment')
    equipment_boq_ids = fields.Many2many('equipment.estimate', 'quotation_wizard_equipment_boq_rel', string='Equipment BOQ')


class JobEstimateExistingQuotationFinancial(models.TransientModel):
    _inherit = "job.estimate.existing.line.overhead"

    budget_unit_price = fields.Float('Budget Unit Price')
    quantity_after = fields.Float('Quantity After')
    cs_overhead_id = fields.Many2one('material.overhead', string='Cost Sheet Overhead')
    bd_overhead_id = fields.Many2one('budget.overhead', string='Budget Overhead')
    overhead_boq_ids = fields.Many2many('overhead.estimate', 'quotation_wizard_overhead_boq_rel', string='Overhead BOQ')

