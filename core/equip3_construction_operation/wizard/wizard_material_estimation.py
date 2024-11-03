from odoo import fields, models, api, _
from num2words import num2words
import datetime


class WizardMaterialEstimations(models.TransientModel):
    _name = 'wizard.material.estimation'
    _description = "Budget Carry Over Wizard Material Estimation"
    _rec_name = "date"

    sr_no = fields.Integer('No.', compute="_sequence_ref")
    bd_material_id = fields.Many2one('budget.material', string="Budget Material")
    carry_id = fields.Many2one('wizard.budget.carry.over', string="Budget Carry Over", ondelete='cascade')
    date = fields.Datetime(string='Date', default=fields.Datetime.now)
    project_scope_id = fields.Many2one('project.scope.line', string="Project Scope ", required=True)
    section_name_id = fields.Many2one('section.line', string="Section", required=True)
    variable_id = fields.Many2one('variable.template', string="Variable")
    group_of_product_id = fields.Many2one('group.of.product', string="Group of Product ", required=True)
    product_id = fields.Many2one('product.product', string="Product", required=True)
    uom_id = fields.Many2one('uom.uom', string="UOM", required=True)
    unit_price = fields.Float(string="Unit Price")
    description = fields.Text(string="Description")
    quantity = fields.Float(string="Budget Quantity")
    amount = fields.Float(string="Budget Amount")
    total_amount = fields.Float(string="Total Amount")

    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.carry_id.wizard_material_estimation_ids:
                no += 1
                l.sr_no = no

    @api.onchange('quantity', 'unit_price')
    def _onchange_total_amount(self):
        for rec in self:
            rec.total_amount = rec.quantity * rec.unit_price