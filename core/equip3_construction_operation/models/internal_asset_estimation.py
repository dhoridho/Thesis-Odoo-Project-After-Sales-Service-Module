from odoo import fields, models, api, _
from num2words import num2words
import datetime


class InternalAssetEstimations(models.Model):
    _name = 'internal.asset.estimation'
    _description = "Internal Asset Estimation"
    _rec_name = "date"

    sr_no = fields.Integer('No.', compute="_sequence_ref")
    bd_internal_asset_id = fields.Many2one('budget.internal.asset', string="Budget Internal Asset")
    budget_carry_over_id = fields.Many2one('project.budget.carry', string="Budget Carry Over")
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    project_scope_id = fields.Many2one('project.scope.line', string="Project Scope ", required=True)
    section_name_id = fields.Many2one('section.line', string="Section", required=True)
    variable_id = fields.Many2one('variable.template', string="Variable")
    group_of_product_id = fields.Many2one('group.of.product', string="Group of Product ")
    asset_category_id = fields.Many2one('maintenance.equipment.category', string="Asset Category", required=True)
    asset_id = fields.Many2one('maintenance.equipment', string="Asset", required=True)
    uom_id = fields.Many2one('uom.uom', string="UOM", required=True)
    unit_price = fields.Float(string="Unit Price")
    contractors = fields.Float(string="Contractors")
    description = fields.Text(string="Description")
    quantity = fields.Float(string="Budget Quantity")
    amount = fields.Float(string="Budget Amount Left")
    total_amount = fields.Float(string="Total Amount")

    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.budget_carry_over_id.budget_carry_internal_asset_ids:
                no += 1
                l.sr_no = no