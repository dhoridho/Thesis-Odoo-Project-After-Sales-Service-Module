from odoo import models, fields, api, _


class MrpBomTools(models.Model):
    _name = 'mrp.bom.tools'
    _description = 'MRP BoM Tools'

    @api.depends('bom_id')
    def _compute_allowed_operation_ids(self):
        for tool in self:
            if not tool.bom_id.operation_ids:
                tool.allowed_operation_ids = self.env['mrp.routing.workcenter']
            else:
                operation_domain = [
                    ('id', 'in', tool.bom_id.operation_ids.ids),
                    '|',
                        ('company_id', '=', tool.company_id.id),
                        ('company_id', '=', False)
                ]
                tool.allowed_operation_ids = self.env['mrp.routing.workcenter'].search(operation_domain)

    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True, ondelete='cascade')
    company_id = fields.Many2one(related='bom_id.company_id', store=True, index=True, readonly=True)
    workorder_id = fields.Many2one('mrp.workorder', string='Work Order', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    operation_id = fields.Many2one('mrp.routing.workcenter', string='Used in Operation', required=False, domain="[('id', 'in', allowed_operation_ids)]")
    allowed_operation_ids = fields.Many2many('mrp.routing.workcenter', compute='_compute_allowed_operation_ids')

    operation_two_ids = fields.Many2many('mrp.bom.operation', related='bom_id.operation_two_ids', string='Operations Two')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Operation Two', domain="[('id', 'in', operation_two_ids)]")

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = self.product_id and self.product_id.uom_id.id or False
