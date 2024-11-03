# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.

import base64
from odoo import fields, models, api, tools, _
from odoo.modules import get_module_resource
from odoo.exceptions import ValidationError

standard_template = [
    ('advanced', 'Advanced'),
    ('custom', 'Contemporary'),
    ('creative', 'Creative'),
    ('elegant', 'Elegant'),
    ('exclusive', 'Exclusive'),
    ('incredible', 'Incredible'),
    ('innovative', 'Innovative'),
    ('professional', 'Professional'),
]

template = {
    'custom': {
        'theme_color': '#a24689',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#a24689',
    },
    'elegant': {
        'theme_color': '#eb5554',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#eb5554',
    },
    'creative': {
        'theme_color': '#0692C3',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#0692C3',
    },
    'professional': {
        'theme_color': '#FF6340',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#FF6340',
    },
    'advanced': {
        'theme_color': '#3D50A5',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#3D50A5',
    },
    'exclusive': {
        'theme_color': '#46A764',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#46A764',
    },
    'incredible': {
        'theme_color': '#0692C3',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#0692C3',
    },
    'innovative': {
        'theme_color': '#0692C3',
        'theme_text_color': '#FFFFFF',
        'text_color': '#000000',
        'company_color': '#6F8192',
        'customer_color': '#000000',
        'company_address_color': '#6F8192',
        'customer_address_color': '#000000',
        'odd_party_color': '#FFFFFF',
        'even_party_color': '#e6e8ed',
        'watermark_text_color': '#0692C3',
    },
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _default_report_template(self):
        # code is inser for ir.rule (issue in upgrade module)
        ir_rule_id = self.env['ir.rule'].search(
            [('name', '=', 'res_partner: portal/public: read access on my commercial partner')])
        if ir_rule_id:
            ir_rule_id.unlink()

        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search([('model', '=', 'account.move'), (
            'report_name', '=', 'general_template.report_invoice_template_custom_exclusive')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'account.move')])[0]
        return report_id

    @api.depends('partner_id')
    def _default_report_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search([('model', '=', 'account.move'), (
            'report_name', '=', 'general_template.report_invoice_template_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'account.move')])[0]
        if self.report_template_id and self.report_template_id.id < report_id.id:
            self.write(
                {'report_template_id': report_id and report_id.id or False})
        self.report_template_id1 = report_id and report_id.id or False

    @api.model
    def _default_report_po_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.order'), ('report_name', '=', 'general_template.report_purchase_custom_exclusive')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.order')])[0]
        return report_id

    @api.depends('partner_id')
    def _default_report_po_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'purchase.order'), ('report_name', '=', 'general_template.report_purchase_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search(
                [('model', '=', 'purchase.order')])[0]
        if self.report_po_template_id and self.report_po_template_id.id < report_id.id:
            self.write(
                {'report_po_template_id': report_id and report_id.id or False})
        if self.report_rfq_template_id and self.report_rfq_template_id.id < report_id.id:
            self.write(
                {'report_rfq_template_id': report_id and report_id.id or False})
        self.report_po_template_id1 = report_id and report_id.id or False

    @api.model
    def _default_report_delivery_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'stock.picking'), ('report_name', '=', 'general_template.report_delivery_custom_exclusive')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'stock.picking')])[0]
        return report_id

    @api.depends('partner_id')
    def _default_report_delivery_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'stock.picking'), ('report_name', '=', 'general_template.report_delivery_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'stock.picking')])[0]
        if self.report_delivery_template_id and self.report_delivery_template_id.id < report_id.id:
            self.write(
                {'report_delivery_template_id': report_id and report_id.id or False})
        if self.report_picking_template_id and self.report_picking_template_id.id < report_id.id:
            self.write(
                {'report_picking_template_id': report_id and report_id.id or False})
        self.report_delivery_template_id1 = report_id and report_id.id or False

    @api.model
    def _default_report_sale_template(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'sale.order'), ('report_name', '=', 'general_template.report_sale_order_custom_exclusive')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'sale.order')])[0]
        return report_id

    @api.depends('partner_id')
    def _default_report_sale_template1(self):
        report_obj = self.env['ir.actions.report']
        report_id = report_obj.search(
            [('model', '=', 'sale.order'), ('report_name', '=', 'general_template.report_sale_order_custom')])
        if report_id:
            report_id = report_id[0]
        else:
            report_id = report_obj.search([('model', '=', 'sale.order')])[0]
        if self.report_sale_template_id and self.report_sale_template_id.id < report_id.id:
            self.write(
                {'report_sale_template_id': report_id and report_id.id or False})
        self.report_sale_template_id1 = report_id and report_id.id or False

    @api.model
    def _get_default_image(self, is_company, colorize=False):
        img_path = get_module_resource(
            'general_template', 'static/src/img', 'avatar.png')
        with open(img_path, 'rb') as f:
            image = f.read()
        return base64.b64encode(image)

    def template_print1(self):
        """ Print the invoice and mark it as sent, so that we can see more
            easily the next step of the workflow
        """
        self.ensure_one()
        # report_obj = self.env['report']
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': '/report/html/%s/%s?enable_editor' % ('general_template.report_demo_template_main', self.id),
        }

    @api.onchange('standard_template')
    def _onchange_sale_order(self):
        if self.standard_template:
            template_value = template.get(str(self.standard_template))
            self.theme_color = template_value.get('theme_color', '#000000')
            self.theme_text_color = template_value.get(
                'theme_text_color', '#FFFFFF')
            self.text_color = template_value.get('text_color', '#000000')
            self.company_color = template_value.get('company_color', '#000000')
            self.company_address_color = template_value.get(
                'company_address_color', '#000000')
            self.customer_color = template_value.get(
                'customer_color', '#000000')
            self.customer_address_color = template_value.get(
                'customer_address_color', '#000000')
            self.odd_party_color = template_value.get(
                'odd_party_color', '#000000')
            self.even_party_color = template_value.get(
                'even_party_color', '#000000')
            self.watermark_text_color = template_value.get(
                'watermark_text_color', '#000000')
        if self.standard_template and self.standard_template == "exclusive":
            self.theme_color = "#3f3f3f"
        return

    def _get_font(self):
        return self.env['report.fonts'].search([('family', '=', 'Roboto'), ('mode', '=', 'all')], limit=1)

    def act_discover_fonts(self):
        self.ensure_one()
        return self.env["report.fonts"].font_scan()

    # @api.onchange('is_show_signature')
    # def onchange_signature(self):
    #     if not self.is_show_signature:
    #         self.signature = False

    theme_color = fields.Char(string="Template Base Color", required=True,
                              help="Please set Hex color for Template.", default="#a24689")
    theme_text_color = fields.Char(
        string="Template Text Color", required=True, help="Please set Hex color for Template Text.", default="#FFFFFF")
    text_color = fields.Char(string="General Text Color", required=True,
                             help="Please set Hex color for General Text.", default="#000000")
    company_color = fields.Char(string="Company Name Color", required=True,
                                help="Please set Hex color for Company Name.", default="#6F8192")
    customer_color = fields.Char(string="Customer Name Color", required=True,
                                 help="Please set Hex color for Customer Name.", default="#000000")
    company_address_color = fields.Char(
        string="Company Address Color", required=True, help="Please set Hex color for Company Address.", default="#6F8192")
    customer_address_color = fields.Char(
        string="Customer Address Color", required=True, help="Please set Hex color for Customer Address.", default="#000000")
    odd_party_color = fields.Char(string="Table Odd Parity Color", required=True,
                                  help="Please set Hex color for Table Odd Parity.", default="#FFFFFF")
    even_party_color = fields.Char(string="Table Even Parity Color", required=True,
                                   help="Please set Hex color for Table Even Parity.", default="#e6e8ed")
    report_template_id1 = fields.Many2one('ir.actions.report', string="Invoice Template1", compute='_default_report_template1',
                                          help="Please select Template report for Invoice", domain=[('model', '=', 'account.move')])
    report_template_id = fields.Many2one('ir.actions.report', string="Invoice Template", default=_default_report_template,
                                         help="Please select Template report for Invoice", domain=[('model', '=', 'account.move')])
    report_sale_template_id1 = fields.Many2one('ir.actions.report', string="Quotation/Order Template1",
                                               compute='_default_report_sale_template1', help="Please select Template report for Sale Order", domain=[('model', '=', 'sale.order')])
    report_sale_template_id = fields.Many2one('ir.actions.report', string="Quotation/Order Template",
                                              default=_default_report_sale_template, help="Please select Template report for Sale Order", domain=[('model', '=', 'sale.order')])
    report_po_template_id1 = fields.Many2one('ir.actions.report', string="Purchase Order Template1", compute='_default_report_po_template1',
                                             help="Please select Template report for Purchase Order", domain=[('model', '=', 'purchase.order')])
    report_po_template_id = fields.Many2one('ir.actions.report', string="Purchase Order Template",  default=_default_report_po_template,
                                            help="Please select Template report for Purchase Order", domain=[('model', '=', 'purchase.order')])
    report_rfq_template_id = fields.Many2one('ir.actions.report', string="RFQ Template", default=_default_report_po_template,
                                             help="Please select Template report for RFQ", domain=[('model', '=', 'purchase.order')])
    report_delivery_template_id1 = fields.Many2one('ir.actions.report', string="Delivery Note Template1",
                                                   compute='_default_report_delivery_template1', help="Please select Template report for Delivery Note ", domain=[('model', '=', 'stock.picking')])
    report_delivery_template_id = fields.Many2one('ir.actions.report', string="Delivery Note Template",
                                                  default=_default_report_delivery_template, help="Please select Template report for Delivery Note ", domain=[('model', '=', 'stock.picking')])
    report_picking_template_id = fields.Many2one('ir.actions.report', string="Picking List Template",
                                                 default=_default_report_delivery_template, help="Please select Template report for Picking List", domain=[('model', '=', 'stock.picking')])
    invoice_logo = fields.Binary("Report Logo", attachment=True, required=False, default=lambda self: self._get_default_image(False, True),
                                 help="This field holds the image used as Logo for Invoice template report")
    is_description = fields.Boolean(string="Display Product Description", default=True,
                                    help="Please check it if you want to show product description in report.")
    watermark_logo = fields.Binary("Report Watermark Logo", default=lambda self: self._get_default_image(
        False, True), help="Please set Watermark Logo for Report.")
    is_company_bold = fields.Boolean(
        string="Display Company Name in Bold", default=False, help="Please check it if you want to show Company Name in Bold.")
    is_customer_bold = fields.Boolean(
        string="Display Customer Name in Bold", default=False, help="Please check it if you want to show Customer Name in Bold.")
    standard_template = fields.Selection(standard_template, string="Standard Template Configuration", required=True,
                                         default='exclusive', help="Please select your choice Standard Color Configuration for all Template.")
    add_product_image = fields.Boolean(
        string="Display Product Image", default=False, help="Please check it if you want to Product Image")
    add_amount_in_words = fields.Boolean(
        string="Display Amount In Word", default=True, help="Please unchecked if you want to hide amount in words")

    # add field to show watermarks
    is_show_watermark = fields.Boolean(
        string="Display Watermark?", help="Please check if want to display watermark")

    watermark = fields.Selection(selection=[('logo', 'Logo'), ('text', 'Text'), ('status', 'Status')], required=True,
                                 string="Display Watermark", default='text',
                                 help='We can choose watermark for pdf either logo or text or status.')
    watermark_text = fields.Char(string="Watermark Text",
                                 default='WatermarkText', help="Please enter watermark text")
    watermark_text_color = fields.Char(string="Watermark Text Color", required=[(
        'watermark', '!=', 'logo')], help="Please set Hex color for Watermark text.", default="#2b4e99")
    watermark_text_font_size = fields.Integer(
        'Watermark Text Font Size(em)', default=4, help="Please set watermark text font size")
    report_footer_selection = fields.Selection(selection=[('standard', 'Standard'), ('multi_columns', 'Multi Columns Footer')], default='standard',
                                               string="Select Report Footer", help="Select footer style if you want to show in report",)
    font_id = fields.Many2one('report.fonts', string="Report Font", default=lambda self: self._get_font(),
                              domain=[
        ('mode', 'in', ('Normal', 'Regular', 'all', 'Book'))],
        help="Set the font into the report header, it will be used as default font in the clever reports of the user company")
    font_size = fields.Integer(
        'Report Font Size(px)', default=12, required=True)
    is_show_signature = fields.Boolean(
        string='Display Signature', default=False, help="Please check it if you want to show signature in PDF.")
    signature = fields.Binary(string="Signature", default=lambda self: self._get_default_image(
        False, True), help="Please upload signature image to display in report")
    logo_footer = fields.Binary("Report Footer Logo", compute='_compute_logo_footer',
                                store=True, help="Please set Footer Logo for Report.")
    is_show_bank_details = fields.Boolean(
        string='Display Bank Details', default=False, help="Please check it if you want to show Bank details in PDF.")
    report_bank_id = fields.Many2one('res.partner.bank', string="Banks")
    is_show_notes = fields.Boolean(string="Display Notes", default=False,
                                   help="Please check it if you want to show Invoice, Sale, Purchase Notes in pdf.")
    is_show_payment_notes = fields.Boolean(
        string="Display Payment Notes", default=False, help="Please check it if you want to show Payment Notes in pdf.")
    is_show_payment_description = fields.Boolean(
        string="Display Payment Description", default=False, help="Please check it if you want to show Payment Description in pdf.")
    is_show_barcode = fields.Boolean(string='Display Report Barcode', default=False,
                                     help="Please check it if you want to show report barcode in pdf.")

    @api.model
    def _assign_templates(self):
        companies = self.search([])
        for company in companies:
            company.report_sale_template_id = self._default_report_sale_template()
            self._default_report_sale_template1()
            company.report_po_template_id = self._default_report_po_template()
            self._default_report_po_template1()
            company.report_template_id = self._default_report_template()
            self._default_report_template1()
            company.report_delivery_template_id = self._default_report_delivery_template()
            company.report_picking_template_id = self._default_report_delivery_template()
            self._default_report_delivery_template1()
            company.standard_template = "exclusive"
            company.theme_color = "#3f3f3f"

    def action_view_report_extra_content(self):
        action = self.env.ref(
            'general_template.action_report_extracontent').read()[0]
        action['domain'] = [('company_id', '=', self.id)]
        return action

    @api.depends('partner_id', 'partner_id.image_1920')
    def _compute_logo_footer(self):
        for company in self:
            company.logo_footer = company.partner_id.image_1920

    @api.constrains('font_size', 'watermark_text_font_size')
    def check_font_size(self):
        if self.watermark_text_font_size <= 0 or self.watermark_text_font_size > 10:
            raise ValidationError(
                _('Please input watermark text font size is greater than 0 and lower than 10, otherwise your report will very massive.'))
        if self.font_size <= 10 or self.font_size >= 25:
            raise ValidationError(
                _('Please input font size is greater than 10 and lower than 25, otherwise your report will very massive.'))
