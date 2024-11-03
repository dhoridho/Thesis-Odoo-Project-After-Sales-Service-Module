from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MrpPlanLineWizard(models.TransientModel):
    _name = 'mrp.plan.line.wizard'
    _description = 'Production Plan Line Wizard'

    line_id = fields.Many2one('mrp.plan.line', string='Production Plan Line', required=True)
    product_id = fields.Many2one('product.product', related='line_id.product_id')
    bom_id = fields.Many2one('mrp.bom', related='line_id.bom_id')
    line_uom_id = fields.Many2one('uom.uom', related='line_id.uom_id', string='Line Unit of Measure')
    line_uom_category_id = fields.Many2one('uom.category', related='line_uom_id.category_id')

    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    remaining_qty = fields.Float(string='Remaining', related='line_id.remaining_qty')
    produced_qty = fields.Float(string='Produced', related='line_id.produced_qty')
    to_produce_qty = fields.Float(string='To Produce', digits='Product Unit of Measure', required=True)
    no_of_order = fields.Integer(default=1, string='Number of Production Order', required=True)

    @api.onchange('line_id')
    def _onchange_line_id(self):
        self.uom_id = self.line_id.uom_id.id

    @api.constrains('to_produce_qty', 'no_of_order')
    def _check_to_produce_qty(self):
        for record in self:
            to_produce_qty = record.to_produce_qty * record.no_of_order
            if to_produce_qty <= 0.0:
                raise ValidationError(_('To Produce must be positive!'))
            if to_produce_qty > record.remaining_qty:
                raise ValidationError(_('To Produce cannot be greater than remaining!'))
    
    def action_confirm(self):
        self.ensure_one()
        to_produce_qty = self.uom_id._compute_quantity(self.to_produce_qty, self.line_uom_id)
        return self.line_id.action_confirm(to_produce_qty, self.no_of_order)
