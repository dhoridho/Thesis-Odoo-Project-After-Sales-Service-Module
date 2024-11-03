
from odoo import api , fields , models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    is_vendor_approval_email = fields.Boolean(string="Email Notification for Vendor Approval")
    is_vendor_approval_whatsapp = fields.Boolean(string="Whatsapp Notification for Vendor Approval")
    is_vendor_pricelist_approval_email = fields.Boolean(string="Email Notification for Vendor Pricelist Approval")
    is_vendor_pricelist_approval_whatsapp = fields.Boolean(string="Whatsapp Notification for Vendor Pricelist Approval")
    
    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        res.update({
            'is_vendor_approval_email': IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_email'),
            'is_vendor_approval_whatsapp': IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_whatsapp'),
            'is_vendor_pricelist_approval_email': IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_email'),
            'is_vendor_pricelist_approval_whatsapp': IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_whatsapp'),
        })
        return res
    
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_masterdata.is_vendor_approval_email', self.is_vendor_approval_email)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_masterdata.is_vendor_approval_whatsapp', self.is_vendor_approval_whatsapp)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_email', self.is_vendor_pricelist_approval_email)
        self.env['ir.config_parameter'].sudo().set_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_whatsapp', self.is_vendor_pricelist_approval_whatsapp)
        self.env.ref('equip3_purchase_masterdata.menu_procurement_vendor_main').active = True
        if self.is_vendor_approval_matrix:
            self.env.ref('equip3_purchase_masterdata.approval_matrix_vendor_configuration_menu').active = True
            self.env.ref('equip3_purchase_masterdata.menu_vendor_to_approve').active = True
            self.env.ref('equip3_purchase_masterdata.menu_vendor_rejected').active = True
            self.env.ref('equip3_purchase_masterdata.menu_procurement_vendor_sub').active = True
            self.env.ref('purchase.menu_procurement_management_supplier_name').active = False
        else:
            self.env.ref('equip3_purchase_masterdata.approval_matrix_vendor_configuration_menu').active = False
            self.env.ref('equip3_purchase_masterdata.menu_vendor_to_approve').active = False
            # self.env.ref('equip3_purchase_masterdata.menu_procurement_vendor_main').active = False
            self.env.ref('equip3_purchase_masterdata.menu_vendor_rejected').active = False
            self.env.ref('equip3_purchase_masterdata.menu_procurement_vendor_sub').active = False
            self.env.ref('purchase.menu_procurement_management_supplier_name').active = True

        if self.is_vendor_pricelist_approval_matrix:
            self.env.ref('equip3_purchase_masterdata.approval_matrix_pricelist_vendor_configuration_menu').active = True
            self.env.ref('equip3_purchase_masterdata.menu_vendor_pricelist_to_approve').active = True
            self.env.ref('equip3_purchase_masterdata.menu_vendor_pricelist_changes_to_approve').active = True
            self.env.ref('equip3_purchase_masterdata.menu_product_purchase_vendor_pricelists_main').active = True
            self.env.ref('purchase.menu_product_pricelist_action2_purchase').active = False
        else:
            self.env.ref('equip3_purchase_masterdata.approval_matrix_pricelist_vendor_configuration_menu').active = False 
            self.env.ref('equip3_purchase_masterdata.menu_vendor_pricelist_to_approve').active = False
            self.env.ref('equip3_purchase_masterdata.menu_vendor_pricelist_changes_to_approve').active = False
            self.env.ref('equip3_purchase_masterdata.menu_product_purchase_vendor_pricelists_main').active = False
            self.env.ref('purchase.menu_product_pricelist_action2_purchase').active = True
