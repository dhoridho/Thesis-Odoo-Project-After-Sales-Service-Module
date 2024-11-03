# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class MrpWorkcenterInnheritKiosk(models.Model):
    _inherit = "mrp.workcenter"
    _description = "Workcenter"

    def get_workcenter(self):
        form_view_ref = self.env.ref(
            "equip3_manuf_kiosk.mrp_workcenter_view_kiosk_kanban"
        )
        kanban_view_ref = self.env.ref("equip3_manuf_kiosk.workcenter_line_kanban_kiosk", False)
        return {
            "name": _("Work Orders"),
            "type": "ir.actions.act_window",
            "view_mode": "kanban",
            "res_model": "mrp.workorder",
            "domain": [
                ["state", "in", ["ready", "progress", "pending"]],
                ["workcenter_id.id", "=", self.id],
            ],
            "views": [(kanban_view_ref.id, "kanban")],
            "target": "current",
            "res_id": self.id,
        }

    def action_work_order_kiosk(self):
        action = self.env["ir.actions.actions"]._for_xml_id("equip3_manuf_kiosk.action_work_orders_kiosk")
        action['domain'] = [['workcenter_id', '=', self.id]]
        return action


class MrpWorOrderInheritKiosk(models.Model):
    _inherit = "mrp.workorder"

    def kiosk_start_workorder(self, wo_id):
        if wo_id:
            curr_wo = self.search([('id', '=', wo_id)])
            curr_wo.button_start()
        return str(curr_wo.duration)

    def kiosk_pause_workorder(self, wo_id):
        if wo_id:
            curr_wo = self.search([('id', '=', wo_id)])
            curr_wo.button_pending()
        return str(curr_wo.duration)

    def kiosk_done_workorder(self, wo_id):
        if wo_id:
            curr_wo = self.search([('id', '=', wo_id)])
            curr_wo.button_finish()
        return str(curr_wo.duration)

    def kiosk_unblock_workorder(self, wo_id):
        if wo_id:
            curr_wo = self.search([('id', '=', wo_id)])
            curr_wo.workcenter_id.unblock()
        return True

    # def kiosk_block_workorder(self, wo_id):
    #     print('\n\n\n------------------------------', wo_id)
    #     if wo_id:
    #         curr_wo = self.search([('id', '=', wo_id)])
    #         curr_wo.order_ids.end_all()
    #     return wo_id

    # def kiosk_block_workorder(self, wo_id):
    #     # view_id = self.mrp.act_mrp_block_workcenter_wo.ids
    #     return {
    #         'res_model': 'mrp.workcenter.productivity',
    #         'type': 'ir.actions.act_window',
    #         'name': _("Block Workcenter"),
    #         'view_mode': 'form',
    #         'view_id': self.env.ref('mrp.act_mrp_block_workcenter_wo').id,
    #         'target': 'new',
    #     }



class MrpWorkCenterProductivityInheir(models.Model):
    _inherit = 'mrp.workcenter.productivity'
    
    # Update user_id based on current login employee_id from workorder
    @api.constrains('workorder_id')
    def _update_user_id(self):
        wo_id = self.workorder_id.id
        self.user_id = self.env['mrp.workorder'].browse(wo_id).employee_id.user_id.id or self.env.uid
