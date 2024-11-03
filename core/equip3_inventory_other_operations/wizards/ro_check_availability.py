from odoo import fields, models


class CheckAvailabilityWizard(models.TransientModel):
    _name = 'ro.check_availability'
    _description = 'RO Check Availability'
    
    message_id = fields.Text()
    repair_order_id = fields.Many2one('repair.order')

    def action_validate(self):
        self.repair_order_id.check_parts_availability = True
