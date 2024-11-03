from odoo import models, _
from odoo.exceptions import UserError


class WizardMPDoneConfirm(models.TransientModel):
    _inherit = 'mp.done.confirm.wizard'

    def mark_done(self):
        mrp_plan = self.env["mrp.plan"].browse(self._context.get("active_id"))
        if mrp_plan and mrp_plan.workorder_ids:
            for workorder in mrp_plan.workorder_ids:
                if workorder.state == 'pause':
                    raise UserError(_("Please finish Work Order %s first!") % workorder.workorder_id)
        mrp_plan.mrp_order_ids.with_context(skip_all_wo_done=True).button_mark_done()
        mrp_plan.state = 'done'
