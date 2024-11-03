from odoo import api, models, fields


class CancelRentalOrderWiazrd(models.TransientModel):
    _name = "cancel.rental.order.wizard"
    _description = "Cancel Rental Order Wizard"

    name = fields.Text("Reasons")

    def submit(self):
        self.ensure_one()
        rental_order = self.env["rental.order"].browse(
            self._context.get("active_ids", [])
        )
        if rental_order:
            rental_order.action_cancel_rental_order(self.name)
