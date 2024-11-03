from odoo import models, fields

# class ResCompany(models.Model):
#   _inherit = 'res.company'
#
#   pr_expiry_notification = fields.Boolean("Expiry Notification")

class ResConfigSetting(models.TransientModel):
    _inherit = 'res.config.settings'
    
    pr_expiry_notification = fields.Boolean(
        string="Expiry Notification")
    pr_on_date_notify = fields.Boolean(
        string="On Date Notification")
    pr_enter_before_first_notify = fields.Integer(
        string="Notify Before Expiry Date", default=3)
    pr_enter_after_first_notify = fields.Integer(
        string="Notify After Expiry Date", default=1)
    pr_expiry_date = fields.Integer(
        string="Purchase Request Expiry Date"
    )
    pr_expiry_date_goods = fields.Integer(
        string="Purchase Request Goods Order Expiry Date"
    )
    pr_expiry_date_services = fields.Integer(
        string="Purchase Request Services Order Expiry Date"
    )
    vendor_purchase_limit = fields.Float(string="Vendor Purchase Limit")
    rfq_exp_date = fields.Integer(string="RFQ Expiry Date")
    po_exp_date = fields.Integer(string="PO Expiry Date")
    rfq_exp_date_goods = fields.Integer(string="RFQ Goods Order Expiry Date")
    rfq_exp_date_services = fields.Integer(string="RFQ Services Order Expiry Date")
    po_exp_date_goods = fields.Integer(string="PO Goods Order Expiry Date")
    po_exp_date_services = fields.Integer(string="PO Services Order Expiry Date")
    max_percentage = fields.Integer(string="Purchase Request Quantity limit in Purchase Order")
    pr_qty_limit = fields.Selection([('no_limit', 'Don’t Limit'), ('percent', 'Percentage'),('fix','Strictly Limit by Purchase Request')], default='no_limit', string='Purchase Request Overlimit Quantity in Purchase Order and Purchase Tender')
    multilevel_disc = fields.Boolean(string="Multi Level Discount")
    
    is_email_notification_req = fields.Boolean(string="Email Notification for Purchase Request Approval")
    is_whatsapp_notification_req = fields.Boolean(string="Whatsapp Notification for Purchase Request Approval")
    log_po = fields.Boolean(string="Log Purchase Order")
    

    def set_values(self):
        super(ResConfigSetting, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_expiry_date', self.pr_expiry_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_expiry_date_goods', self.pr_expiry_date_goods)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_expiry_date_services', self.pr_expiry_date_services)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_expiry_notification', self.pr_expiry_notification)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_on_date_notify', self.pr_on_date_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.is_email_notification_req', self.is_email_notification_req)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.is_whatsapp_notification_req', self.is_whatsapp_notification_req)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_enter_before_first_notify', self.pr_enter_before_first_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_enter_after_first_notify', self.pr_enter_after_first_notify)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.rfq_exp_date', self.rfq_exp_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.rfq_exp_date_goods', self.rfq_exp_date_goods)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.rfq_exp_date_services', self.rfq_exp_date_services)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.po_exp_date', self.po_exp_date)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.po_exp_date_goods', self.po_exp_date_goods)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.po_exp_date_services', self.po_exp_date_services)
        self.env['ir.config_parameter'].sudo().set_param('vendor_purchase_limit', self.vendor_purchase_limit)
        self.env['ir.config_parameter'].sudo().set_param('max_percentage', self.max_percentage)
        self.env['ir.config_parameter'].sudo().set_param('pr_qty_limit', self.pr_qty_limit)
        self.env['ir.config_parameter'].sudo().set_param('multilevel_disc', self.multilevel_disc)
        self.env['ir.config_parameter'].sudo().set_param('log_po', self.log_po)

        if self.is_good_services_order:
            self.env.ref("equip3_purchase_operation.menu_purchase_services_goods").active = True
            self.env.ref("purchase.menu_procurement_management").active = True
            self.env.ref("equip3_purchase_operation.menu_orders").active = False
        else:
            self.env.ref("equip3_purchase_operation.menu_purchase_services_goods").active = False
            self.env.ref("purchase.menu_procurement_management").active = False
            self.env.ref("equip3_purchase_operation.menu_orders").active = True

        if self.is_service_work_order:
            self.env.ref("equip3_purchase_operation.menu_services_purchase_service_work_order").active = True
            self.env.ref("equip3_purchase_operation.menu_swo_orders").active = True
            self.env.ref("equip3_purchase_operation.milestone_contract_template_menu_act").active = True
        else:
            self.env.ref("equip3_purchase_operation.menu_services_purchase_service_work_order").active = False
            self.env.ref("equip3_purchase_operation.menu_swo_orders").active = False
            self.env.ref("equip3_purchase_operation.milestone_contract_template_menu_act").active = False

        if self.is_purchase_request_assign_user:
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_categ").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_assigned").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_not_assigned").active = True
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_categ").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_assigned").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_not_assigned").active = True
            # self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_categ").active = True
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line").active = False
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_assigned").active = True
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_not_assigned").active = True
        else:
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_categ").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_assigned").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_line_orders_not_assigned").active = False
            # self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_categ").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines").active = True
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_assigned").active = False
            self.env.ref("equip3_purchase_operation.menu_purchase_request_lines_not_assigned").active = False
            # self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_categ").active = False
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line").active = True
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_assigned").active = False
            self.env.ref("equip3_purchase_operation.good_menu_purchase_request_line_not_assigned").active = False

    def get_values(self):
        res = super(ResConfigSetting, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'vendor_purchase_limit': IrConfigParam.get_param('vendor_purchase_limit', 0.00),
            'max_percentage': IrConfigParam.get_param('max_percentage', 0),
            'pr_qty_limit': IrConfigParam.get_param('pr_qty_limit', "no_limit"),
            'pr_expiry_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date') or 30,
            'pr_expiry_date_goods':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date_goods') or 30,
            'pr_expiry_date_services':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date_services') or 30,
            'pr_expiry_notification':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_notification'),
            'pr_on_date_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_on_date_notify'),
            'is_email_notification_req':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_email_notification_req'),
            'is_whatsapp_notification_req':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_whatsapp_notification_req'),
            'pr_enter_before_first_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_enter_before_first_notify') or 3,
            'pr_enter_after_first_notify':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_enter_after_first_notify') or 1,
            'rfq_exp_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date') or 0,
            'rfq_exp_date_goods':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods') or 0,
            'rfq_exp_date_services':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services') or 0,
            'po_exp_date':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.po_exp_date') or 0,
            'po_exp_date_goods':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.po_exp_date_goods') or 0,
            'po_exp_date_services':  self.env['ir.config_parameter'].get_param('equip3_purchase_operation.po_exp_date_services') or 0,
            'multilevel_disc': IrConfigParam.get_param('multilevel_disc'),
            'log_po': IrConfigParam.get_param('log_po'),
        })
        return res