
from odoo import api , fields , models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    vendor_purchase_limit = fields.Float(string="Vendor Purchase Limit")
    is_email_notification = fields.Boolean(string="Email Notification for Purchase Order Approval")
    is_whatsapp_notification = fields.Boolean(string="Whatsapp Notification for Purchase Order Approval")
    pr_order_average_price = fields.Selection([
                                ("day","Day"),
                                ("week","Week"),
                                ("month","Month"),
                                ("year","Year"),
                                ], string='Purchase Order Average Price', default="day")
    is_purchase_vendor_rating_warning = fields.Boolean(string='Is Purchase Vendor Rating Warning')
    is_product_service_operation_receiving = fields.Boolean(string="Product Service Operation Receiving", help="When Active, All Service Type Products Automatically Will Create A Receiving Note After Confirming A Purchase. You Also Can Set Wheter The Product Will Create Operation Or Not On Each Product Template", default=False)
    reference_formatting = fields.Selection([
        ("revise","Revise Reference"),
        ("new","New Reference")
    ], string='Reference Formatting', default="revise", help=_("This default value is applied to any Revise Purchase Order created. Example: PO/G/YY/MM/DD/001/R01"))


    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'vendor_purchase_limit': IrConfigParam.get_param('vendor_purchase_limit', 0.00),
            'is_email_notification': IrConfigParam.get_param('equip3_purchase_operation.is_email_notification'),
            'is_whatsapp_notification': IrConfigParam.get_param('equip3_purchase_operation.is_whatsapp_notification'),
            'pr_order_average_price': IrConfigParam.get_param('equip3_purchase_operation.pr_order_average_price', "day"),
            'show_line_subtotals_tax_selection': IrConfigParam.get_param('show_line_subtotals_tax_selection', "tax_excluded"),
            'is_purchase_vendor_rating_warning': IrConfigParam.get_param('is_purchase_vendor_rating_warning', False),
            'reference_formatting': IrConfigParam.get_param('reference_formatting', "revise"),
        })
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('vendor_purchase_limit', self.vendor_purchase_limit)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.is_email_notification', self.is_email_notification)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.is_whatsapp_notification', self.is_whatsapp_notification)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_operation.pr_order_average_price', self.pr_order_average_price)
        self.env['ir.config_parameter'].sudo().set_param('show_line_subtotals_tax_selection', self.show_line_subtotals_tax_selection)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_vendor_rating_warning', self.is_purchase_vendor_rating_warning)
        self.env['ir.config_parameter'].sudo().set_param('reference_formatting', self.reference_formatting)
        
        if self.is_purchase_order_approval_matrix:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_order_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_order_configuration_menu').active = False
        if self.is_purchase_request_approval_matrix:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_request_configuration_menu').active = True
        else:
            self.env.ref('equip3_purchase_operation.approval_matrix_purchase_request_configuration_menu').active = False
        po_action = self.env.ref('equip3_purchase_operation.action_approval_matrix_purchase_order')
        pr_action = self.env.ref('equip3_purchase_operation.action_approval_matrix_purchase_request')
        if self.is_pr_department and not self.is_good_services_order:
            pr_action.write({
                'context': {'department_invisible': False}
            })
        elif self.is_good_services_order and not self.is_pr_department:
            po_action.write({
                'context': {'order_type_invisible': False}
            })
            pr_action.write({
                'context': {'order_type_invisible': False}
            })
        elif self.is_good_services_order and self.is_pr_department:
            po_action.write({
                'context': {'order_type_invisible': False}
            })
            pr_action.write({
                'context': {'order_type_invisible': False, 'department_invisible': False}
            })
        else:
            po_action.write({
                'context': {'order_type_invisible': True}
            })
            pr_action.write({
                'context': {'order_type_invisible': True, 'department_invisible': True}
            }) 

