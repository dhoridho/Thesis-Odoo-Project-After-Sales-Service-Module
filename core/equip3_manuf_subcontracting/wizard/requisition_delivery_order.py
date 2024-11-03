from odoo import models, fields, _
from odoo.exceptions import UserError


class RequisitionDeliveryOrder(models.TransientModel):
    _name = 'requisition.delivery.order'
    _description = 'Requisition Delivery Order'

    requisition_id = fields.Many2one('purchase.requisition', string='Blanket Order', required=True)
    line_ids = fields.One2many(related='requisition_id.line_ids', readonly=False)

    def action_confirm(self):
        self.ensure_one()
        line_without_bom = self.line_ids.filtered(lambda l: not l.bom_id)
        if line_without_bom:
            list_product = '\n'.join(['- %s' % l.product_id.name for l in line_without_bom])
            raise UserError(_('Please fill Bill of Material for products:\n%s' % list_product))

        return self.requisition_id.with_context(skip_wizard=True).action_create_delivery_order()
