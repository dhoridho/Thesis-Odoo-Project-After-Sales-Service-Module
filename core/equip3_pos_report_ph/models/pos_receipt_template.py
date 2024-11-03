# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class PosReceiptTemplate(models.Model):
    _inherit = "pos.receipt.template"


    is_ph_template = fields.Boolean('PH Template ?')
    is_ph_show_customer_information = fields.Boolean('PH Show Customer Information ?')
    is_ph_show_pos_information = fields.Boolean('PH Show POS Information ?')
    is_ph_show_company_information = fields.Boolean('PH Show Company Information ?')
    is_ph_vat_detail = fields.Boolean('PH VAT Detail')



    def receipt_template_dict_data(self):
        res = super(PosReceiptTemplate, self).receipt_template_dict_data()
        
        res['is_ph_template'] = self.is_ph_template
        res['is_ph_show_customer_information'] = self.is_ph_show_customer_information
        res['is_ph_show_pos_information'] = self.is_ph_show_pos_information
        res['is_ph_show_company_information'] = self.is_ph_show_company_information
        res['is_ph_vat_detail'] = self.is_ph_vat_detail

        return res