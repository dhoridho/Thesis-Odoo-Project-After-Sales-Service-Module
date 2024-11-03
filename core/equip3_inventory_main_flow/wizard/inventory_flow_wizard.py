from odoo import api, models, fields

class InventoryFlowWizard(models.TransientModel):
    _name = 'inventory.flow.wizard'
    _description = 'Inventory Flow Wizard'
    name = fields.Char(string='Name', default='Inventory Main Flow')

    def button_warehouse(self):
        action = self.env.ref('stock.action_warehouse_form').read()[0]
        return action

    def button_location(self):
        action = self.env.ref('stock.action_location_form').read()[0]
        return action

    def button_reordering_rules(self):
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'kanban,tree,form',
            'name': ('Reordering Rules'),
            'res_model': 'stock.warehouse.orderpoint',
            'view_id': False,
        }
        return action

    def button_replenishment(self):
        action = self.env.ref('stock.action_replenishment').read()[0]
        return action

    def button_products(self):
        action = self.env.ref('stock.product_template_action_product').read()[0]
        return action

    def button_inventory(self):
        action = self.env.ref('equip3_inventory_reports.action_stock_per_wh').read()[0]
        return action

    def button_stock_count(self):
        action = self.env.ref('stock.action_inventory_form').read()[0]
        return action

    def button_material_request(self):
        action = self.env.ref('equip3_inventory_operation.material_request_action').read()[0]
        return action

    def button_all_transfer_operation(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        return action

    def button_itr(self):
        action = self.env.ref('equip3_inventory_operation.action_internal_transfer_request').read()[0]
        return action

    def button_interwarehouse_tf_out(self):
        action = self.env.ref('equip3_inventory_operation.action_internal_transfer_out').read()[0]
        return action

    def button_interwarehouse_tf_in(self):
        action = self.env.ref('equip3_inventory_operation.action_internal_transfer_in').read()[0]
        return action

    def button_receiving_notes(self):
        action = self.env.ref('equip3_inventory_operation.stock_picking_receiving_note').read()[0]
        return action

    def button_packages(self):
        action = self.env.ref('stock.action_package_view').read()[0]
        return action

    def button_return_request_of_purchase_order(self):
        action = self.env.ref('dev_rma.action_dev_rma_rma').read()[0]
        return action

    def button_delivery(self):
        action = self.env.ref('equip3_inventory_operation.action_delivery_order').read()[0]
        return action

    def button_return_request_of_sale_order(self):
        action = self.env.ref('equip3_inventory_operation.action_dev_rma_rma_so').read()[0]
        return action

    def button_batch_picking(self):
        action = self.env.ref('stock_picking_batch.stock_picking_batch_action').read()[0]
        return action

    def button_fee_head(self):
        action = self.env.ref('sale.action_orders').read()[0]
        return action