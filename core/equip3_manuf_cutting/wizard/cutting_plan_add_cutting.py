from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CuttingPlanAddCutting(models.TransientModel):
    _name = 'cutting.plan.add.cutting.wizard'
    _description = 'Cutting Plan Add Cutting Wizard'

    cutting_plan_id = fields.Many2one('cutting.plan', string='Cutting Plan', required=True)
    line_ids = fields.One2many(
        comodel_name='cutting.plan.add.cutting.line', 
        inverse_name='wizard_id', 
        string='Wizard Lines')

    def action_confirm(self):
        self.ensure_one()
        plan_id = self.cutting_plan_id
        company_id = plan_id.company_id
        branch_id = plan_id.branch_id

        approval_matrix_id = self.env['mrp.approval.matrix']
        if company_id.is_cutting_order:
            approval_matrix_id = self.env['mrp.approval.matrix'].search([
                ('company_id', '=', company_id.id),
                ('branch_id', '=', branch_id.id),
                ('matrix_type', '=', 'co')
            ], limit=1)
            if not approval_matrix_id:
                raise ValidationError(_('Please set approval matrix for Cutting Order first!'))

        order_ids = self.env['cutting.order']
        for line in self.line_ids:
            values = {
                'cutting_plan_id' : plan_id.id,
                'company_id': company_id.id,
                'branch_id': branch_id.id,
                'product_id' : line.product_id.id,
                'approval_matrix_id': approval_matrix_id.id,
                'workcenter_id' : line.work_center_id.id,
                'location_id': line.work_center_id.location_id.id,
                'finished_location_id': line.work_center_id.location_finished_id.id,
                'byproduct_location_id': line.work_center_id.location_byproduct_id.id,
                'fixed_length' : line.fixed_length,
                'fixed_width' : line.fixed_width,
                'fixed_height' : line.fixed_height
            }

            order_id = self.env['cutting.order'].create(values)

            lot_values = []
            for lot in line.lot_ids:
                lot_values += [(0, 0, {
                    'cutting_lot_id': order_id.id,
                    'lot_id': lot.id
                })]

            order_id.lot_ids = lot_values
            order_id.onchange_fixed_fields()

            for line_lot in order_id.lot_ids:
                line_lot.onchange_lot_id()

            order_ids |= order_id

        memento = plan_id.memento_cutting_order
        order_names = ','.join([order.name for order in order_ids])
        plan_id.write({
            'memento_cutting_order': memento and '%s - %s' % (memento, order_names) or order_names
        })

class CuttingPlanAddCuttingLine(models.TransientModel):
    _name = 'cutting.plan.add.cutting.line'
    _description = 'Cutting Plan Add Cutting Line for Wizard'

    @api.depends('product_id')
    def _compute_allowed_lots(self):
        lot = self.env['stock.production.lot']
        for record in self:
            domain = [('product_id', '=', record.product_id.id)]
            lot_ids = lot.search(domain)
            allowed_lot_ids = []
            for lot_id in lot_ids:
                quants = lot_id.quant_ids.filtered(
                    lambda q: q.location_id.usage == 'internal' or
                              (q.location_id.usage == 'transit' and q.location_id.company_id)
                )
                if sum(quants.mapped('quantity')):
                    allowed_lot_ids.append(lot_id.id)
            record.allowed_lot_ids = [(6, 0, allowed_lot_ids)]

    allowed_lot_ids = fields.Many2many('stock.production.lot', compute=_compute_allowed_lots)

    wizard_id = fields.Many2one(
        comodel_name='cutting.plan.add.cutting.wizard',
        string='Wizard',
    )

    product_id = fields.Many2one(
        comodel_name='product.product',
        string='Product',
        required=True,
        domain="[('is_cutting_product', '=', True)]",
    )

    work_center_id = fields.Many2one(
        comodel_name='mrp.workcenter',
        required=True,
        string='Work Center')

    lot_ids = fields.Many2many(
        comodel_name='stock.production.lot', 
        string='Lot/Serial Number',
        domain="[('id', 'in', allowed_lot_ids)]",
        required=True
        )

    fixed_length = fields.Boolean(string='Fixed Length')
    fixed_width = fields.Boolean(string='Fixed Width')
    fixed_height = fields.Boolean(string='Fixed Height')
