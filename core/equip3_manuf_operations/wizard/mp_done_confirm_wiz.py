# -*- coding: utf-8 -*-
from odoo import fields, models, tools, api, _
from odoo.exceptions import UserError


class WizardMPDoneConfirm(models.TransientModel):
    _name = 'mp.done.confirm.wizard'
    _description = 'MP Done Confirmation Wizard'

    def mark_done(self):
        mrp_plan = self.env["mrp.plan"].browse(self._context.get("active_id"))
        if mrp_plan and mrp_plan.workorder_ids:
            for workorder in mrp_plan.workorder_ids:
                if workorder.state == 'pause':
                    raise UserError(_("Please finish Work Order %s first!") % workorder.workorder_id)
                if workorder.state == 'progress' and workorder.is_user_working:
                    raise UserError(_("Please Cancel or Done the running work order first!."))
                elif workorder.state == 'pending':
                    workorder.sudo().write({
                    'state': 'cancel',
                    'date_planned_start': False,
                    'date_planned_finished': False,
                })
                elif workorder.state == 'progress' and not workorder.is_user_working:
                    workorder.sudo().button_finish()
                else:
                    workorder.sudo().button_finish()
        if mrp_plan and mrp_plan.mrp_order_ids:
            mrp_plan.mrp_order_ids.sudo().button_mark_done()
        mrp_plan.sudo().write({'state': 'done'})