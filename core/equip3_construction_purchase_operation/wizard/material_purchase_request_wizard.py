from ast import Store
from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import Warning, ValidationError


class PurchaseRequestWizard(models.TransientModel):
    _inherit = 'purchase.request.wizard'

    material_request = fields.Many2one('material.request', string='Material Request')
    pr_wizard_line = fields.One2many('purchase.request.wizard.line', 'mr_pr_wizard')

    def prepare_line(self, line):
        vals = super(PurchaseRequestWizard, self).prepare_line(line)
        vals.update({
            'type' : line.type,
            'project_scope' : line.project_scope.id,
            'section' : line.section.id,
            'variable' : line.variable_ref.id,
            'group_of_product' : line.group_of_product.id,
            'product_id' : line.product_id.id,
            'name' : line.description,
            'product_uom_id' : line.uom_id.id,
            'product_qty' : line.qty_purchase,
            'budget_quantity' : line.qty_purchase,
            'is_goods_orders': True,
            'date_required' : line.request_date,
            'company_id' : line.mr_id.company_id.id,
            'dest_loc_id': line.mr_id.destination_warehouse_id.id,
            'analytic_account_group_ids': [(6, 0, self.material_request.analytic_account_group_ids.ids)],
        })
        return vals
    
    def prepare_pr(self):
        vals = super(PurchaseRequestWizard, self).prepare_pr()
        vals.update({
            'is_goods_orders': True,
            'is_orders': True, 
            'origin': self.pr_wizard_line and self.pr_wizard_line[-1].mr_id.name or '',
            'project': self.pr_wizard_line.mr_id.project.id,
            'cost_sheet': self.pr_wizard_line.mr_id.job_cost_sheet.id,
            'project_budget': self.pr_wizard_line.mr_id.project_budget.id,
            'branch_id': self.pr_wizard_line.mr_id.branch_id.id,
            'analytic_account_group_ids': [(6, 0, self.material_request.analytic_account_group_ids.ids)],
            'material_request': self.pr_wizard_line.mr_id.id,
            'picking_type_id': self.material_request.destination_warehouse_id.in_type_id.id
        })
        return vals

    def create_pr(self):
        res = super(PurchaseRequestWizard, self).create_pr()
        res._onchange_line_ids()
        return res
    

class PurchaseRequestWizardLine(models.TransientModel):
    _inherit = 'purchase.request.wizard.line'

    cs_material_id = fields.Many2one('material.material', 'CS Material ID', Store="1")
    cs_labour_id = fields.Many2one('material.labour', 'CS Labour ID', Store="1")
    cs_overhead_id = fields.Many2one('material.overhead', 'CS Overhead ID', Store="1")
    cs_equipment_id = fields.Many2one('material.equipment', 'CS Equipment ID', Store="1")
    bd_material_id = fields.Many2one('budget.material', 'BD Material ID', Store="1")
    bd_labour_id = fields.Many2one('budget.labour', 'BD Labour ID', Store="1")
    bd_overhead_id = fields.Many2one('budget.overhead', 'BD Overhead ID', Store="1")
    bd_equipment_id = fields.Many2one('budget.equipment', 'BD equipment ID', Store="1")
    type = fields.Selection([('material','Material'),
                            ('labour','Labour'),
                            ('overhead','Overhead'),
                            ('equipment','Equipment')],
                            string = "Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope', required=True)
    section = fields.Many2one('section.line', string='Section')
    variable_ref = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')


    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequestWizardLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'pr_wizard_line' in context_keys:
                if len(self._context.get('pr_wizard_line')) > 0:
                    next_sequence = len(self._context.get('pr_wizard_line')) + 1
            res.update({'no': next_sequence})
        return res