
from odoo import _, api, fields, models

class ProductReplenish(models.TransientModel):
    _inherit = 'product.replenish'

    action_to_take = fields.Selection([
                    ('no_action', 'No Action'),
                    ('create_pr', 'Create Purchase Request'),
                    ('create_rfq', 'Create Request For Quotation'),
                    ('create_itr', 'Create Internal Transfer Request'),
                    ('create_mr', 'Create Material Request'),
    ], default='create_rfq')
    location_id = fields.Many2one('stock.location', string='Location')
    filter_location_ids = fields.Many2many('stock.location', compute='_get_filter_locations', store=False)
    supplier_id = fields.Many2one('product.supplierinfo', string="Vendor")
    source_location_id = fields.Many2one('stock.location', string="Source Location")

    @api.depends('warehouse_id')
    def _get_filter_locations(self):
        location_ids = []
        for record in self:
            if record.warehouse_id:
                location_obj = self.env['stock.location']
                store_location_id = record.warehouse_id.view_location_id.id
                addtional_ids = location_obj.search([('location_id', 'child_of', store_location_id), ('usage', '=', 'internal')])
                for location in addtional_ids:
                    if location.location_id.id not in addtional_ids.ids:
                        location_ids.append(location.id)
                child_location_ids = self.env['stock.location'].search([('id', 'child_of', location_ids), ('id', 'not in', location_ids)]).ids
                final_location = child_location_ids + location_ids
                record.filter_location_ids = [(6, 0, final_location)]
            else:
                record.filter_location_ids = [(6, 0, [])]


    def action_replenish(self):
        product_id = self.product_id
        action_to_take = self.action_to_take
        location_id = self.location_id
        warehouse_id = self.warehouse_id
        vendor_id = self.supplier_id.name
        if action_to_take == 'create_mr':
            product_line_data = [(0, 0, {
                'product' : self.product_id.id,
                'description' : self.product_id.name,
                'quantity' : self.quantity,
                'destination_warehouse_id': warehouse_id.id,
                'product_unit_measure' : self.product_id.uom_id.id,
                'destination_location_id' : location_id.id,
                'request_date' : self.date_planned,
            })]
            vals={
                'requested_by' : self.env.user.id,
                'schedule_date' : self.date_planned,
                'destination_location_id' : location_id.id,
                'product_line' : product_line_data,
                'destination_warehouse_id': warehouse_id.id,
            }
            material_request = self.env['material.request'].create(vals)
        elif action_to_take == 'create_pr':
            product_line_data = [(0, 0, {
                'product_id' : self.product_id.id,
                'name' : self.product_id.name,
                'product_qty' : self.quantity,
                'product_uom_id' : self.product_id.uom_id.id,
                'dest_loc_id': warehouse_id.id,
                'date_required': self.date_planned
            })]
            vals = {
                'requested_by' : self.env.user.id,
                'is_goods_orders' : True,
                'request_date': self.date_planned,
                'line_ids' : product_line_data,
            }
            purchase_request = self.env['purchase.request'].create(vals)
        elif action_to_take == 'create_rfq':
            product_line_data = [(0, 0, {
                'product_id' : self.product_id.id,
                'name' : self.product_id.name,
                'price_unit': 1.0,
                'display_type': False,
                'date_planned': self.date_planned,
                'product_qty' : self.quantity,
                'product_uom' : self.product_id.uom_id.id,
                'destination_warehouse_id' : warehouse_id.id,
            })]
            vals = {
                'partner_id' : vendor_id.id,
                'is_goods_orders' : True,
                'order_line' : product_line_data,
                'picking_type_id': warehouse_id.int_type_id.id,
                'date_planned': self.date_planned
            }
            purchase_order = self.env['purchase.order'].create(vals)
        elif action_to_take == 'create_itr':
            product_line_data = [(0, 0, {
                'sequence': 1,
                'product_id' : self.product_id.id,
                'description': self.product_id.display_name,
                'qty' : self.quantity,
                'scheduled_date' : self.date_planned,
                'uom' : self.product_id.uom_id.id,
                'source_location_id': self.source_location_id.id,
                'destination_location_id': self.location_id.id,
            })]
            vals={
                'source_warehouse_id': warehouse_id.id,
                'destination_location_id' : self.location_id.id,
                'scheduled_date' : self.date_planned,
                'product_line_ids' : product_line_data,
            }
            internal_transfer = self.env['internal.transfer'].create(vals)
            internal_transfer._onchange_warehouse_id_for_location()
