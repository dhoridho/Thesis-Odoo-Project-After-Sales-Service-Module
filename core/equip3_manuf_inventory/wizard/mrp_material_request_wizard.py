from odoo import models, fields, api, _


class MRPMaterialRequestWizard(models.TransientModel):
    _name = 'mrp.material.request.wizard'
    _description = 'MRP Material Request Wizard'

    plan_id = fields.Many2one('mrp.plan', string='Production Plan', required=True)
    line_ids = fields.One2many('mrp.material.request.wizard.line', 'wizard_id', string='Lines')
    action = fields.Selection(selection=[
        ('action_transfer_request', 'Create Internal Transfer'),
        ('action_material_request', 'Create Material Request')
    ], default='action_transfer_request', string='Action To Trigger', required=True)

    def _allowed_orders(self):
        if self.action == 'action_transfer_request':
            return self.plan_id.mrp_order_ids.filtered(lambda o: not o.is_transfer_requested)
        elif self.action == 'action_material_request':
            return self.plan_id.mrp_order_ids.filtered(lambda o: not o.is_material_requested)
        return self.env['mrp.production']

    @api.onchange('plan_id', 'action')
    def _onchange_plan_id(self):
        self.line_ids = [(5,)] + [(0, 0, {'production_id': order.id}) for order in self._allowed_orders()]

    def action_confirm(self):
        self.ensure_one()
        plan = self.plan_id.with_context(
            order_ids=self.line_ids.filtered(lambda o: o.is_checked).mapped('production_id'),
            skip_wizard=True,
            force_create=True)
        return getattr(plan, self.action)()


class MRPMaterialRequestWizard(models.TransientModel):
    _name = 'mrp.material.request.wizard.line'
    _description = 'MRP Material Request Wizard Line'

    wizard_id = fields.Many2one('mrp.material.request.wizard', required=True, ondelete='cascade')
    is_checked = fields.Boolean(default=True)
    production_id = fields.Many2one('mrp.production', string='Production Order')
    product_id = fields.Many2one('product.product', related='production_id.product_id', string='Finished Goods')
