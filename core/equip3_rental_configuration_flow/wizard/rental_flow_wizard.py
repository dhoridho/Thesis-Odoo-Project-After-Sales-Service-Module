from odoo import api, models, fields, _

class RentalFlowWizard(models.TransientModel):
    _name = 'rental.flow.wizard'

    name = fields.Char(string='Name', default='Rental Configuration Flow')

    def button_customer(self):
        action = self.env.ref('base.action_partner_customer_form').read()[0]
        return action

    def button_rental_product(self):
        action = self.env.ref('browseinfo_rental_management.product_normal_action_rental').read()[0]
        return action

    def button_checklist_item(self):
        action = self.env.ref('equip3_rental_operation.action_rental_order_checklist_item').read()[0]
        return action

    def button_product_availability(self):
        action = self.env.ref('equip3_rental_availability.create_rental_booking_action').read()[0]
        return action
        
    def button_rental_orders(self):
        action = self.env.ref('browseinfo_rental_management.action_rental_orders').read()[0]
        return action

    def button_delivery_order(self):
        action = self.env.ref('equip3_inventory_operation.action_delivery_order').read()[0]
        return action

    def button_return(self):
        action = self.env.ref('equip3_inventory_operation.stock_picking_receiving_note').read()[0]
        return action

    def button_invoice(self):
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        return action

    def button_reporting(self):
        pass