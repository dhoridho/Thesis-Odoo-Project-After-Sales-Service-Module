from odoo import fields, models


class PurchaseOrderReport(models.TransientModel):
    _name = "manufacturing.work.center.wizard"

    user_id = fields.Many2one(
        'res.users', "User",
        default=lambda self: self.env.uid)
    loss_id = fields.Many2one(
        'mrp.workcenter.productivity.loss', "Loss Reason",
        ondelete='restrict')
    description = fields.Text('Description')

    def button_block(self):
        work_center_obj = self.env['mrp.workcenter'].browse(self._context.get('active_id'))
        work_center_obj.time_ids = False
        work_center_obj.loss_id = self.loss_id.id
        work_center_obj.description = self.description
        return True

