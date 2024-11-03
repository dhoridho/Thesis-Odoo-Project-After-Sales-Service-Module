
from odoo import api , fields , models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    direct_control = fields.Boolean("Direct Purchase Budget Controller")
    qty_limit = fields.Float("Quantity Limit per Item")
    budget_limit = fields.Float("Budget Limit per Order")
    is_email_notification_direct_purchase = fields.Boolean(string="Email Notification for Direct purchase")
    is_whatsapp_notification_direct_purchase = fields.Boolean(string="Whatsapp Notification for Direct purchase")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'direct_control':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.direct_control'),
            'qty_limit':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.qty_limit'),
            'budget_limit':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.budget_limit'),
            'is_email_notification_direct_purchase': self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_email_notification_direct_purchase'),
            'is_whatsapp_notification_direct_purchase': self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_whatsapp_notification_direct_purchase'),
        })
        return res

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.direct_control', self.direct_control)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.is_email_notification_direct_purchase', self.is_email_notification_direct_purchase)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.is_whatsapp_notification_direct_purchase', self.is_whatsapp_notification_direct_purchase)
        direct_po_action = self.env.ref('equip3_purchase_other_operation_cont.action_approval_matrix_direct_purchase')
        if self.is_good_services_order:
            direct_po_action.write({
                'context': {'direct_order_type_invisible': False}
            })
        else:
            direct_po_action.write({
                'context': {'direct_order_type_invisible': True}
            })
        if self.direct_control:
            self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.qty_limit', self.qty_limit)
            self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.budget_limit', self.budget_limit)
        else:
            self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.qty_limit', 0)
            self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation_cont.budget_limit', 0)
        if self.is_direct_purchase_approval_matrix:
            self.env.ref('equip3_purchase_other_operation_cont.approval_matrix_direct_purchase_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_other_operation_cont.approval_matrix_direct_purchase_configuration_menu').active = False
        return res
