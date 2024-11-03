# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import markupsafe
from bs4 import BeautifulSoup

class DictToObject:
    def __init__(self, d=None):
        if d is not None:
            for key, value in d.items():
                setattr(self, key, value)

class PosReceiptTemplate(models.Model):
    _name = "pos.receipt.template"
    _description = "POS Receipt Template"

    name = fields.Char("Name")
    is_default = fields.Boolean("Default Receipt",copy=False,default=False)
    size = fields.Selection(
        selection=[('58mm', '58 mm'), ('80mm', '80 mm'), ('custom', 'Custom')],
        string="Receipt Size",
        default="58mm")
    custom_size = fields.Float("Custom Size")
    is_need_header = fields.Boolean("Need Header")
    receipt_header_text = fields.Text("Custom Header Text")
    is_need_footer = fields.Boolean("Need Footer")
    receipt_footer_text = fields.Text("Custom Footer Text")
    is_receipt_disc_in_orderline = fields.Boolean('Discount in orderline')
    is_receipt_tax_include_orderline = fields.Boolean('Product price Include taxes')
    is_receipt_serial_lot_info = fields.Boolean('Include serial or lot number')
    is_receipt_savings_summary = fields.Boolean('Include savings summary', help='This will add the saving summary message template, add () to state where the amount would be placed')
    savings_summary_text = fields.Text('Savings summary Text', help='This will add the saving summary message template, add () to state where the amount would be placed')
    is_receipt_product_code = fields.Boolean('Include Product Code')
    preview_receipt = fields.Html(compute='_compute_preview_receipt', sanitize=False)
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    voucher_receipt_display = fields.Selection(
        selection=[('Barcode', 'Barcode'), ('QR Code', 'QR Code')],
        string="Voucher Receipt Display")
    generate_voucher_id = fields.Many2one('generate.pos.voucher','Generate Voucher')
    is_voucher_receipt = fields.Boolean('Is Voucher Receipt')
    is_show_discount_detail = fields.Boolean('Show Discount Detail')
 
    def receipt_template_dict_data(self):
        width = 0
        if self.size:
            if self.size == 'custom':
                width = self.custom_size
            else:
                width = int(self.size.replace('mm',''))

        if width>=80:
            element_id = 'receipt_template_c_big_size'
        else:
            element_id = 'receipt_template_c_small_size'
        company = self.env.company
        branch = self.env.user.branch_id
        currency = company.currency_id
        price = 'Rp 1000'
        if currency.position == 'after':
            price = 'xxxxx ' + currency.symbol
        else:
            price = currency.symbol + ' xxxxx'
        orderlines = [
        DictToObject({
            'full_product_name':'[ST-008] Product Sample 1',
            'product_only_name':'Product Sample 1',
            'lot_sn':'XNV-0909',
            'quantity':1,
            'unit_name':'PCS',
            'price':price
        }),
        DictToObject({
            'full_product_name':'[ST-009] Product Sample 2',
            'product_only_name':'Product Sample 2',
            'lot_sn':'XNV-0808',
            'quantity':1,
            'unit_name':'PCS',
            'price':price
        })
        ]
        
        savings_summary_text = ''
        if self.savings_summary_text:
            savings_summary_text = self.savings_summary_text.replace('()', price)

        return {
            'name':self.name,
            'logo':'/web/image?model=res.company&id='+str(company.id)+'&field=logo',
            'is_default':self.is_default,
            'size':self.size,
            'element_id':element_id,
            'company':company,
            'width':str(width)+'mm',
            'is_need_header':self.is_need_header,
            'receipt_header_text':self.receipt_header_text,
            'is_need_footer':self.is_need_footer,
            'receipt_footer_text':self.receipt_footer_text,
            'is_receipt_disc_in_orderline':self.is_receipt_disc_in_orderline,
            'is_show_discount_detail':self.is_show_discount_detail,
            'is_receipt_tax_include_orderline':self.is_receipt_tax_include_orderline,
            'is_receipt_serial_lot_info':self.is_receipt_serial_lot_info,
            'is_receipt_product_code':self.is_receipt_product_code,
            'is_voucher_receipt':self.is_voucher_receipt,
            'voucher_receipt_display':self.voucher_receipt_display,
            'company_name':company.name,
            'pos_branch_name':branch.name,
            'branch_street':branch.street,
            'branch_street_2':branch.street_2,
            'branch_telephone':branch.telephone,
            'date':'12 Oct 2023 10:55 AM',
            'order_name':'XXXXXXXX',
            'cashier':'XXXXXX',
            'orderlines':orderlines,
            'price':price,
            'is_receipt_savings_summary':self.is_receipt_savings_summary,
            'savings_summary_text': savings_summary_text,
        }

    def _compute_preview_receipt(self):
        styles = self.env['base.document.layout']._get_asset_style()
        for rec in self:
            preview_css = markupsafe.Markup(self.env['base.document.layout']._get_css_for_preview(styles,rec.id))
            receipt_template = DictToObject(rec.receipt_template_dict_data())
            values =  {
                'receipt': rec,
                'receipt_template': receipt_template,
                'docs': self,
                'company': self.env.company, 
                'preview_css': preview_css
            }
            render_template = self.env['ir.ui.view']._render_template('equip3_pos_masterdata.receipt_template_overview_report', values)
            soup = BeautifulSoup(render_template, 'html.parser')
            rec.preview_receipt = soup.find("div", {"class": "pos-receipt-custom_template"})