from odoo import api, models, fields


class RentalOrderFeedbackWiazrd(models.TransientModel):
    _name = "rental.order.feedback.wizard"
    _description = "Rental Order Feedback Wizard"

    name = fields.Text("Reasons")

    def submit(self):
        self.ensure_one()
        rental_order = self.env["rental.order"].browse(
            self._context.get("active_ids", [])
        )
        if rental_order:
            rental_order.action_reject(self.name)
