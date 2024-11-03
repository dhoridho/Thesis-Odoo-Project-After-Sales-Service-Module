
from odoo import api, fields, models, _

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pt_expiry_notification = fields.Boolean(
        string="Expiry Notification")
    pt_on_date_notify = fields.Boolean(
        string="On Date Notification")
    pt_enter_before_first_notify = fields.Integer(
        string="Notify Before Expiry Date", default=3)
    pt_enter_after_first_notify = fields.Integer(
        string="Notify After Expiry Date", default=1)
    pt_expiry_date = fields.Integer(
        string="Purchase Tender Expiry Date"
    )

    bo_expiry_date = fields.Integer(
        string="Purchase Blanket Expiry Date"
    )
    bo_expiry_notification = fields.Boolean(
        string="Expiry Notification")
    bo_on_date_notify = fields.Boolean(
        string="On Date Notification")
    bo_enter_before_first_notify = fields.Integer(
        string="Notify Before Expiry Date", default=3)
    bo_enter_after_first_notify = fields.Integer(
        string="Notify After Expiry Date", default=1)
    pt_goods_order_expiry_date = fields.Integer(
        string="Tender Goods Order Expiry Date")
    pt_service_order_expiry_date = fields.Integer(
        string="Tender Services Order Expiry Date")
    bo_goods_order_expiry_date = fields.Integer(
        string="Blanket Goods Order Expiry Date")
    bo_service_order_expiry_date = fields.Integer(
        string="Blanket Services Order Expiry Date")

    is_email_notification_tender = fields.Boolean(string="Email Notification for Purchase Tender Approval")
    is_whatsapp_notification_tender = fields.Boolean(string="Whatsapp Notification for Purchase Tender Approval")

    is_email_notification_bo = fields.Boolean(string="Email Notification for Blanket Order Approval")
    is_whatsapp_notification_bo = fields.Boolean(string="Whatsapp Notification for Blanket Order Approval")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update({
            'pt_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_expiry_date') or 30,
            'pt_expiry_notification':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_expiry_notification'),
            'pt_on_date_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_on_date_notify'),
            'pt_enter_before_first_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_enter_before_first_notify') or 3,
            'pt_enter_after_first_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_enter_after_first_notify') or 1,

            'bo_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_expiry_date') or 30,
            'bo_expiry_notification':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_expiry_notification'),
            'bo_on_date_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_on_date_notify'),
            'bo_enter_before_first_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_enter_before_first_notify') or 3,
            'bo_enter_after_first_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_enter_after_first_notify') or 1,
            'pt_goods_order_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_goods_order_expiry_date') or 30,
            'pt_service_order_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_service_order_expiry_date') or 30,
            'bo_goods_order_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_goods_order_expiry_date') or 30,
            'bo_service_order_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_service_order_expiry_date') or 30,

            'is_email_notification_tender':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_tender'),
            'is_whatsapp_notification_tender':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_tender'),
            'is_email_notification_bo':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_bo'),
            'is_whatsapp_notification_bo':  self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_bo'),

        })
        return res


    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_expiry_date', self.pt_expiry_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_expiry_notification', self.pt_expiry_notification)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_on_date_notify', self.pt_on_date_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_enter_before_first_notify', self.pt_enter_before_first_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_enter_after_first_notify', self.pt_enter_after_first_notify)

        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_expiry_date', self.bo_expiry_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_expiry_notification', self.bo_expiry_notification)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_on_date_notify', self.bo_on_date_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_enter_before_first_notify', self.bo_enter_before_first_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_enter_after_first_notify', self.bo_enter_after_first_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_goods_order_expiry_date', self.pt_goods_order_expiry_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.pt_service_order_expiry_date', self.pt_service_order_expiry_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_goods_order_expiry_date', self.bo_goods_order_expiry_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.bo_service_order_expiry_date', self.bo_service_order_expiry_date)

        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.is_email_notification_tender', self.is_email_notification_tender)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.is_whatsapp_notification_tender', self.is_whatsapp_notification_tender)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.is_email_notification_bo', self.is_email_notification_bo)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_other_operation.is_whatsapp_notification_bo', self.is_whatsapp_notification_bo)

        if self.is_blanket_order_approval_matrix:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_blanket_order_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_blanket_order_configuration_menu').active = False
        if self.is_purchase_tender_approval_matrix:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_purchase_agreement_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_other_operation.approval_matrix_purchase_agreement_configuration_menu').active = False

        if self.is_purchase_order_approval_matrix:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_order_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_order_configuration_menu').active = False

        if self.is_purchase_request_approval_matrix:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_request_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_request_configuration_menu').active = False

        res_user_ids = self.env["res.users"].search([])    
        if self.is_purchase_tender:
            self.env.ref('equip3_purchase_other_operation.is_purchase_tender').users = [(6,0, res_user_ids.ids)]
         
        else:
            self.env.ref('equip3_purchase_other_operation.is_purchase_tender').users = [(3, user_id.id) for user_id in res_user_ids]
        pt_action = self.env.ref('equip3_purchase_other_operation.action_approval_matrix_purchase_agreement')
        bo_action = self.env.ref('equip3_purchase_other_operation.action_approval_matrix_blanket_order')
        if self.is_good_services_order:
            pt_action.write({
                'context': {'order_type_invisible': False}
            })
            bo_action.write({
                'context': {'order_type_invisible': False}
            })
        else:
            pt_action.write({
                'context': {'order_type_invisible': True}
            })
            bo_action.write({
                'context': {'order_type_invisible': True}
            })
