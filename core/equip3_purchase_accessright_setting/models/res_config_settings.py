
from odoo import api , fields , models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    is_vendor_approval_matrix = fields.Boolean(string="Vendor Approval Matrix")
    is_purchase_order_approval_matrix = fields.Boolean(string="Purchase Order Approval Matrix")
    is_purchase_request_approval_matrix = fields.Boolean(string="Purchase Request Approval Matrix")
    is_vendor_pricelist_approval_matrix = fields.Boolean(string="Vendor Pricelist Approval Matrix")
    is_purchase_tender_approval_matrix = fields.Boolean(string="Purchase Tender Approval Matrix")
    purchase_approval_matrix = fields.Boolean(string="Approval Matrix")
    is_blanket_order_approval_matrix = fields.Boolean(string="Blanket Order Approval Matrix")
    is_good_services_order = fields.Boolean(string="Goods Order, Services Order and Assets Order Menu")
    is_purchase_tender = fields.Boolean(string="Purchase Request to Purchase Tender")
    is_blanket_order = fields.Boolean(string="Purchase Request to Blanket Order")
    is_direct_purchase_approval_matrix = fields.Boolean(string="Direct Purchase Approval Matrix")
    is_pr_department = fields.Boolean(string="Purchase Request Department")
    is_price_ratting_rfq_tender = fields.Boolean(string="Price Rating RFQ Tender")
    retail = fields.Boolean(string="Retail")
    module_equip3_purchase_rental = fields.Boolean(string='Purchase Rental Orders')
    is_product_brand_filter = fields.Boolean(string='Product Brand Filter')
    is_product_vendor_pricelist_filter = fields.Boolean(string='Product Vendor Pricelist Filter')
    is_service_work_order = fields.Boolean(string='Service Work Order')
    is_purchase_request_assign_user = fields.Boolean(string='Purchase Request Assign Representative')
    group_create_purchase_request_direct = fields.Boolean(string='Purchase Request to Direct Purchase', implied_group='equip3_purchase_accessright_setting.group_create_purchase_request_direct')
    
    @api.onchange('purchase_show_signature')
    def _onchange_purchase_show_signature(self):
        self.purchase_enable_other_sign_option = self.purchase_show_signature

    # @api.onchange('module_equip3_purchase_rental')
    # def _onchange_purchase_rental(self):
    #     if not self._origin.module_equip3_purchase_rental and self.module_equip3_purchase_rental:
    #         message = "If this boolean is active, equip3_purchase_rental will be installed."
    #         warning_mess = {
    #             'message': (message),
    #             'title': "Warning"
    #         }
    #         return {'warning': warning_mess}

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'is_vendor_approval_matrix': IrConfigParam.get_param('is_vendor_approval_matrix', False),
            'is_purchase_order_approval_matrix': IrConfigParam.get_param('is_purchase_order_approval_matrix', False),
            'is_purchase_request_approval_matrix': IrConfigParam.get_param('is_purchase_request_approval_matrix', False),
            'is_vendor_pricelist_approval_matrix': IrConfigParam.get_param('is_vendor_pricelist_approval_matrix', False),
            'is_purchase_tender_approval_matrix': IrConfigParam.get_param('is_purchase_tender_approval_matrix', False),
            # 'purchase_approval_matrix': IrConfigParam.get_param('purchase_approval_matrix', False),
            'is_blanket_order_approval_matrix': IrConfigParam.get_param('is_blanket_order_approval_matrix', False),
            'is_good_services_order': IrConfigParam.get_param('is_good_services_order', False),
            'is_purchase_tender': self.env['ir.config_parameter'].sudo().get_param('is_purchase_tender', False),
            'is_direct_purchase_approval_matrix': self.env['ir.config_parameter'].sudo().get_param('is_direct_purchase_approval_matrix', False),
            'is_pr_department': IrConfigParam.get_param('is_pr_department', False), 
            'is_price_ratting_rfq_tender': IrConfigParam.get_param('is_price_ratting_rfq_tender', False), 
            'retail': self.env['ir.config_parameter'].sudo().get_param('retail', False),
            'is_product_brand_filter': self.env['ir.config_parameter'].sudo().get_param('is_product_brand_filter', False),
            'is_product_vendor_pricelist_filter': self.env['ir.config_parameter'].sudo().get_param('is_product_vendor_pricelist_filter', False),
            'is_service_work_order': self.env['ir.config_parameter'].sudo().get_param('is_service_work_order', False),
            'is_purchase_request_assign_user': self.env['ir.config_parameter'].sudo().get_param('is_purchase_request_assign_user', False),
            'group_create_purchase_request_direct': self.env['ir.config_parameter'].sudo().get_param('group_create_purchase_request_direct', False),
        })
        return res

    def set_values(self):
        # if self.purchase == False:
        #     self.update({
        #         'purchase_approval_matrix': False,
        #     })
        if self.purchase == False:
            self.update({
                'is_vendor_approval_matrix': False,
                'is_purchase_order_approval_matrix': False,
                'is_purchase_request_approval_matrix': False,
                'is_vendor_pricelist_approval_matrix': False,
                'is_purchase_tender_approval_matrix': False,
                'is_blanket_order_approval_matrix': False,
                'is_good_services_order': False,
                'is_purchase_tender': False,
                'is_direct_purchase_approval_matrix': False,
                'is_price_ratting_rfq_tender': False,
                'retail': False,
                'is_product_brand_filter': False,
                'is_product_vendor_pricelist_filter': False,
                'is_service_work_order': False,
                'is_purchase_request_assign_user': False,

            })
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('is_vendor_approval_matrix', self.is_vendor_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_order_approval_matrix', self.is_purchase_order_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_request_approval_matrix', self.is_purchase_request_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_vendor_pricelist_approval_matrix', self.is_vendor_pricelist_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_tender_approval_matrix', self.is_purchase_tender_approval_matrix)
        # self.env['ir.config_parameter'].sudo().set_param('purchase_approval_matrix', self.purchase_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_blanket_order_approval_matrix', self.is_blanket_order_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_good_services_order', self.is_good_services_order)
        self.env['ir.config_parameter'].sudo().set_param('is_pr_department', self.is_pr_department)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_tender', self.is_purchase_tender)
        self.env['ir.config_parameter'].sudo().set_param('is_direct_purchase_approval_matrix', self.is_direct_purchase_approval_matrix)
        self.env['ir.config_parameter'].sudo().set_param('is_price_ratting_rfq_tender', self.is_price_ratting_rfq_tender)
        self.env['ir.config_parameter'].sudo().set_param('retail', self.retail)
        self.env['ir.config_parameter'].sudo().set_param('is_product_brand_filter', self.is_product_brand_filter)
        self.env['ir.config_parameter'].sudo().set_param('is_product_vendor_pricelist_filter', self.is_product_vendor_pricelist_filter)
        self.env['ir.config_parameter'].sudo().set_param('is_service_work_order', self.is_service_work_order)
        self.env['ir.config_parameter'].sudo().set_param('is_purchase_request_assign_user', self.is_purchase_request_assign_user)
        self.env['ir.config_parameter'].sudo().set_param('group_create_purchase_request_direct', self.group_create_purchase_request_direct)
        if self.is_purchase_tender:
            self.env.ref('equip3_purchase_accessright_setting.action_purchase_request_tender_line').create_action()
        else:
            self.env.ref('equip3_purchase_accessright_setting.action_purchase_request_tender_line').unlink_action()
