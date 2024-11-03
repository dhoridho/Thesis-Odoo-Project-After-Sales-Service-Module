from odoo import models, fields, api, _, tools
from odoo.exceptions import ValidationError, Warning
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import requests
headers = {'content-type': 'application/json'}
import logging
_logger = logging.getLogger(__name__)


class SupplierInfo(models.Model):
    _name = "product.supplierinfo"
    _inherit = ['product.supplierinfo', 'mail.thread', 'mail.activity.mixin', 'portal.mixin']

    # ////////////////////////////////

    name = fields.Many2one(
        'res.partner', 'Vendor',
        ondelete='cascade', required=True,
        help="Vendor of this product", check_company=True, tracking=True, domain="[('is_vendor', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_name = fields.Char(
        'Vendor Product Name', tracking=True,
        help="This vendor's product name will be used when printing a request for quotation. Keep empty to use the internal one.")
    product_code = fields.Char(
        'Vendor Product Code', tracking=True,
        help="This vendor's product code will be used when printing a request for quotation. Keep empty to use the internal one.")
    sequence = fields.Integer(
        'Sequence', default=1, help="Assigns the priority to the list of product vendor.")
    product_uom = fields.Many2one(
        'uom.uom', 'Unit of Measure', related='product_uom_new',
        help="This comes from the product form.")
    product_uom_category_id = fields.Many2one(related='product_tmpl_id.uom_id.category_id')
    product_uom_new = fields.Many2one(
        'uom.uom', 'Unit of Measure', domain="[('category_id', '=', product_uom_category_id)]",
        help="This comes from the product form.")
    vendor_uom = fields.Char('Vendor Unit of Measure')
    min_qty = fields.Float(
        'Minimal Quantity', default=1.0, required=True, digits="Product Unit Of Measure", tracking=True,
        help="The quantity to purchase from this vendor to benefit from the price, expressed in the vendor Product Unit of Measure if not any, in the default unit of measure of the product otherwise.")
    price = fields.Float(
        'Price', default=0.0, digits='Product Price', tracking=True,
        required=True, help="The price to purchase a product")
    company_id = fields.Many2one(
        'res.company', 'Company', tracking=True,
        default=lambda self: self.env.company.id, index=1)
    currency_id = fields.Many2one(
        'res.currency', 'Currency',
        default=lambda self: self.env.company.currency_id.id,
        required=True)
    date_start = fields.Date('Start Date', tracking=True, help="Start date for this vendor price")
    date_end = fields.Date('End Date', tracking=True, help="End date for this vendor price")
    product_id = fields.Many2one(
        'product.product', 'Product Variant', check_company=True, tracking=True,
        help="If not set, the vendor price will apply to all variants of this product.")
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product Template', tracking=True, check_company=True,
        index=True, ondelete='cascade', required=True, domain="[('purchase_ok','=',True)]")
    product_variant_count = fields.Integer('Variant Count', related='product_tmpl_id.product_variant_count')
    delay = fields.Integer(
        'Delivery Lead Time', tracking=True, default=1, required=True,
        help="Lead time in days between the confirmation of the purchase order and the receipt of the products in your warehouse. Used by the scheduler for automatic computation of the purchase order planning.")
    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')
    # ////////////////////////////////

    state = fields.Selection([
        ("req_amendment","Request for Amendment"),
        ("draft","Draft"),
        ("waiting_approval","Waiting For Approval"),
        ("approved","Approved"),
        ("rejected","Rejected"),
        ("expire","Expired"),
    ], string='State', default="draft", tracking=True)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    vendor_pricelist_approval_matrix = fields.Many2one('vendor.pricelist.approval.matrix', string="Vendor Pricelist Approval Matrix", compute="_get_vendor_price", store=True)
    approval_ids = fields.One2many('product.supplierinfo.approval', 'supplier_id', 'Approval Lines', tracking=True)
    user_approval_ids = fields.Many2many('res.users', string="User")
    current_user = fields.Many2one('res.users', compute='_get_current_user')
    is_vendor_pricelist_approval_matrix = fields.Boolean(string="Approving Matrix Vendor Pricelist", store=True)
    branch_id = fields.Many2one('res.branch',"Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    changes = fields.Boolean('Changes', default=False)
    changes_id = fields.Integer('Changes ID', default=0)
    approval_matrix_line_id = fields.Many2one('product.supplierinfo.approval', string='Vendor Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    # //history

    name_old = fields.Many2one(
        'res.partner', 'Vendor',
        ondelete='cascade')
    product_name_old = fields.Char(
        'Vendor Product Name')
    product_code_old = fields.Char(
        'Vendor Product Code')
    delay_old = fields.Integer(
        'Delivery Lead Time')
    branch_id_old = fields.Many2one('res.branch',"Branch")
    date_old = fields.Datetime("Created on")
    product_id_old = fields.Many2one(
        'product.product', 'Product Variant')
    product_tmpl_id_old = fields.Many2one(
        'product.template', 'Product Template')
    product_uom_old = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        related='product_tmpl_id_old.uom_po_id')
    min_qty_old = fields.Float(
        'Minimal Quantity', default=0.0)
    price_old = fields.Float(
        'Price', default=0.0)
    company_id_old = fields.Many2one(
        'res.company', 'Company')
    currency_id_old = fields.Many2one(
        'res.currency', 'Currency')
    date_start_old = fields.Date('Start Date', tracking=True, help="Start date for this vendor price")
    date_end_old = fields.Date('End Date', tracking=True, help="End date for this vendor price")
    vendor_pricelist_approval_matrix_old = fields.Many2one('vendor.pricelist.approval.matrix', string="Vendor Pricelist Approval Matrix")

    edit_button_state = fields.Html(sanitize=False, compute='_compute_edit_button', store=False)
    
    @api.constrains('name', 'branch_id', 'product_tmpl_id', 'currency_id', 'product_uom_new', 'company_id')
    def _check_unique(self):
        for record in self:
            domain = [
                ('id', '!=', record.id),
                ('name', '=', record.name.id),
                ('branch_id', '=', record.branch_id.id),
                ('product_tmpl_id', '=', record.product_tmpl_id.id),
                ('product_id', '=', record.product_id.id),
                ('currency_id', '=', record.currency_id.id),
                ('product_uom_new', '=', record.product_uom_new.id),
                ('company_id', '=', record.company_id.id),
                ('price', '=', record.price),
                ('min_qty', '=', record.min_qty),
                ('vendor_uom', '=', record.vendor_uom),
                ('delay', '=', record.delay),
                ('date_start', '=', record.date_start),
                ('date_end', '=', record.date_end),
                ('state', '=', record.state)
            ]

            existing_records = self.env['product.supplierinfo'].search(domain, limit=1)
            if existing_records:
                if existing_records.purchase_requisition_id and record.purchase_requisition_id:
                    existing_records.unlink()
                else:
                    raise Warning("Duplicate values found for the specified fields")

    def default_get(self, fields):
        res = super(SupplierInfo, self).default_get(fields)
        is_vendor_pricelist_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_vendor_pricelist_approval_matrix', False)
        # is_vendor_pricelist_approval_matrix = self.env.company.is_vendor_pricelist_approval_matrix
        res.update({'is_vendor_pricelist_approval_matrix': is_vendor_pricelist_approval_matrix})
        return res

    def _compute_edit_button(self):
        for rec in self:
            if rec.vendor_pricelist_approval_matrix:
                if rec.state == 'approved' or rec.state == 'waiting_approval':
                    rec.edit_button_state = '<style>.o_form_button_edit {display: none !important;}</style>'
                else:
                    rec.edit_button_state = False
            else:
                rec.edit_button_state = False

    def _get_approve_button(self):
        for record in self:
            matrix_line = record.approval_ids.filtered(lambda r: not r.approved).sorted(key=lambda r: r.sequence)

            if not matrix_line:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            else:
                matrix_line_id = matrix_line[0]
                is_user_in_matrix = self.env.user.id in matrix_line_id.user_ids.ids
                is_user_last_approved = self.env.user.id != matrix_line_id.last_approved.id

                if is_user_in_matrix and is_user_last_approved:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False

    @api.onchange('product_tmpl_id')
    def set_uom(self):
        for res in self:
            if res.product_tmpl_id:
                res.product_uom_new = res.product_tmpl_id.uom_po_id

    @api.model
    def create(self, vals):
        if vals.get('is_vendor_pricelist_approval_matrix'):
            if not vals.get('approval_ids'):
                raise ValidationError("Please set the Vendor Pricelist Approval Matrix!")
        if vals.get('min_qty') == 0:
            vals['min_qty'] = 1
        res = super(SupplierInfo, self).create(vals)
        if res.product_tmpl_id:
            res.product_uom_new = res.product_tmpl_id.uom_po_id.id
        if not res.is_vendor_pricelist_approval_matrix:
            res.state = 'approved'
        if res.changes_id > 0:
            id = self.env['product.supplierinfo'].search([('id', '=', res.changes_id)])
            if id:
                res.update({
                    'name_old': id.name.id or False,
                    'product_name_old': id.product_name or False,
                    'product_code_old': id.product_code_old or False,
                    'delay_old': id.delay or False,
                    'branch_id_old': id.branch_id.id or False,
                    'date_old': id.create_date or False,
                    'product_id_old':  id.product_id.id or False,
                    'product_tmpl_id_old': id.product_tmpl_id.id or False,
                    'min_qty_old': id.min_qty or False,
                    'price_old': id.price or False,
                    'company_id_old': id.company_id.id or False,
                    'currency_id_old': id.currency_id.id or False,
                    'date_start_old': id.date_start or False,
                    'date_end_old': id.date_end or False,
                    'product_uom_old': id.product_uom or False,
                    'product_uom': id.product_uom or False,
                    'vendor_pricelist_approval_matrix_old': id.vendor_pricelist_approval_matrix or False,
                })
        return res

    def req_amendment_process(self):
        self.state = 'req_amendment'
        self.changes_id = self.id
        id = self.env['product.supplierinfo'].search([('id', '=', self.changes_id)])
        if id:
            self.update({
                'name_old': id.name.id or False,
                'product_name_old': id.product_name or False,
                'product_code_old': id.product_code_old or False,
                'delay_old': id.delay or False,
                'branch_id_old': id.branch_id.id or False,
                'date_old': id.create_date or False,
                'product_id_old':  id.product_id.id or False,
                'product_tmpl_id_old': id.product_tmpl_id.id or False,
                'min_qty_old': id.min_qty or False,
                'price_old': id.price or False,
                'company_id_old': id.company_id.id or False,
                'currency_id_old': id.currency_id.id or False,
                'date_start_old': id.date_start or False,
                'date_end_old': id.date_end or False,
                'product_uom_old': id.product_uom or False,
                'product_uom': id.product_uom or False,
                'vendor_pricelist_approval_matrix_old': id.vendor_pricelist_approval_matrix or False,
            })
        self.changes = True


    def set_confirm_change(self):
        self.state = 'draft'

    @api.depends('price')
    def _get_current_user(self):
        for rec in self:
            rec.current_user = self.env.user

    @api.constrains('min_qty')
    def _check_min_qty(self):
        for record in self:
            if record.min_qty <= 0:
                raise ValidationError("Minimal Qty should be greater then zero.")

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for record in self:
            if record.date_end < record.date_start:
                raise ValidationError("End Date should be greater then Start Date.")

    @api.depends('price', 'is_vendor_pricelist_approval_matrix', 'branch_id')
    def _get_vendor_price(self):
        for res in self:
            if res.is_vendor_pricelist_approval_matrix:
                approval_id = self.env['vendor.pricelist.approval.matrix'].search([('branch_id', '=', res.branch_id.id)], limit=1)
                if approval_id:
                    res.vendor_pricelist_approval_matrix = approval_id
                    res.create_approval(approval_id)
                else:
                    res.vendor_pricelist_approval_matrix = False
                    res.approval_ids = False
            else:
                res.vendor_pricelist_approval_matrix = False
                res.approval_ids = False

    def create_approval(self, approval_id):
        for res in self:
            if res.state not in ("waiting_approval","approved","rejected"):
                approval = self.env['product.supplierinfo.approval']
                approval_matrix = res.vendor_pricelist_approval_matrix
                approval_ids = approval.search([('supplier_id', '=', res.id)])
                approval_ids.sudo().unlink()
                res.vendor_pricelist_approval_matrix = approval_matrix
                user = []
                approval_matrix_line = []
                for line in approval_id.approval_matrix_line_ids:
                    lines = approval.create({
                        'sequence': line.sequence,
                        'user_ids': [(6, 0, line.user_ids.ids)],
                        'minimum_approver': line.minimum_approver,
                    })
                    approval_matrix_line.append(lines.id)
                    user.extend(line.user_ids.ids)
                if approval_matrix_line:
                    res.approval_ids = [(6, 0, approval_matrix_line)]
                if user:
                    res.user_approval_ids = [(6, 0, user)]

    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.name.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "")
            param = {'body': string_test, 'phone': phone_num, 'previewBase64': '', 'title': ''}
            domain = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
            token = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
            try:
                request_server = requests.post(f'{domain}/sendMessage?token={token}', params=param, headers=headers, verify=True)
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active")

    def _send_qiscus_whatsapp_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            broadcast_template_id = self.env['qiscus.wa.template.content'].search([
                ('language', '=', 'en'),
                ('template_id.name', '=', 'hm_sale_notification_1')
            ], limit=1)
            if not broadcast_template_id:
                raise ValidationError(_("Cannot find Whatsapp template with name = 'hm_sale_notification_1'!"))
            domain = self.env['ir.config_parameter'].get_param('qiscus.api.url')
            token = self.env['ir.config_parameter'].get_param('qiscus.api.secret_key')
            app_id = self.env['ir.config_parameter'].get_param('qiscus.api.appid')
            channel_id = self.env['ir.config_parameter'].get_param('qiscus.api.channel_id')

            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.name.name)
            if "${submitter_name}" in string_test:
                string_test = string_test.replace("${submitter_name}", submitter)
            if "${br}" in string_test:
                string_test = string_test.replace("${br}", f"\n")
            if "${url}" in string_test:
                string_test = string_test.replace("${url}", url)
            # message = re.sub(r'\n+', ', ', string_test)
            messages = string_test.split(f'\n')
            message_obj = []
            for pesan in messages:
                message_obj.append({
                    'type': 'text',
                    'text': pesan
                })
            phone_num = phone
            if "+" in phone_num:
                phone_num = phone_num.replace("+", "").replace(" ", "").replace("-", "")
            headers = {
                'content-type': 'application/json',
                'Qiscus-App-Id': app_id,
                'Qiscus-Secret-Key': token
            }
            url = f'{domain}{app_id}/{channel_id}/messages'
            params = {
                "to": phone_num,
                "type": "template",
                "template": {
                    "namespace": broadcast_template_id.template_id.namespace,
                    "name": broadcast_template_id.template_id.name,
                    "language": {
                        "policy": "deterministic",
                        "code": 'en'
                    },
                    "components": [{
                        "type": "body",
                        "parameters": message_obj
                    }]
                }
            }
            try:
                request_server = requests.post(url, json=params, headers=headers, verify=True)
                _logger.info("\nNotification Whatsapp --> Request for Approval:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (headers, params, request_server.json()))
                # if request_server.status_code != 200:
                #     data = request_server.json()
                #     raise ValidationError(f"""{data["error"]["error_data"]["details"]}""")
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")

    def action_request_for_approval(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_vendor_pricelist_approval_email = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_email')
        is_vendor_pricelist_approval_whatsapp = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_whatsapp')
        for record in self:
            data = []
            record.request_partner_id = self.env.user.partner_id.id
            action_id = self.env.ref('product.product_supplierinfo_type_action')
            template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_pricelist')
            wa_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_pricelist_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=product.supplierinfo'
            if record.approval_ids and len(record.approval_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approval_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from' : self.env.user.company_id.email,
                        'email_to' : approver.partner_id.email,
                        'approver_name' : approver.name,
                        'requested_by' : self.env.user.name,
                        'product_lines' : data,
                        'date': date.today(),
                        'url' : url,
                    }
                    if is_vendor_pricelist_approval_email:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_vendor_pricelist_approval_whatsapp:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            else:
                approver = record.approval_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'requested_by': self.env.user.name,
                    'product_lines': data,
                    'date': date.today(),
                    'url': url,
                }
                if is_vendor_pricelist_approval_email:
                    template_id.with_context(ctx).send_mail(record.id, True)
                if is_vendor_pricelist_approval_whatsapp:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            record.state = 'waiting_approval'
            return True

    @api.model
    def _vendor_price_list_expire(self):
        today_date = datetime.today()
        vendor_pricelist_ids = self.env['product.supplierinfo'].search([('state', 'in', ('draft', 'waiting_approval', 'approved')), ('date_end', '!=', False), ('date_end', '<', today_date)])
        vendor_pricelist_ids.write({'state': 'expire'})

    @api.model
    def action_vendors_pricelists_menu(self):
        # Vendor menu invisible conditionally
        irconfigparam_1 = self.env['ir.config_parameter'].sudo()
        is_vendor_approval_matrix = irconfigparam_1.get_param('is_vendor_approval_matrix', False)
        # is_vendor_approval_matrix = self.env.company.is_vendor_approval_matrix
        self.env.ref('equip3_purchase_masterdata.menu_procurement_vendor_main').active = True
        if is_vendor_approval_matrix:
            self.env.ref('purchase.menu_procurement_management_supplier_name').active = False
        else:
            self.env.ref('purchase.menu_procurement_management_supplier_name').active = True

        # Vendor Pricelists menu invisible conditionally
        irconfigparam_2 = self.env['ir.config_parameter'].sudo()
        is_vendor_pricelist_approval_matrix = irconfigparam_2.get_param('is_vendor_pricelist_approval_matrix', False)
        # is_vendor_pricelist_approval_matrix = self.env.company.is_vendor_pricelist_approval_matrix
        if is_vendor_pricelist_approval_matrix:
            self.env.ref('purchase.menu_product_pricelist_action2_purchase').active = False
            self.env.ref('equip3_purchase_masterdata.menu_product_purchase_vendor_pricelists_main').active = True
        else:
            self.env.ref('purchase.menu_product_pricelist_action2_purchase').active = True
            self.env.ref('equip3_purchase_masterdata.menu_product_purchase_vendor_pricelists_main').active = False
            
    def action_draft(self):
        for record in self:
            if record.state == 'rejected':
                record.state = 'draft'
        return True


    def action_approved(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_vendor_pricelist_approval_email = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_email')
        is_vendor_pricelist_approval_whatsapp = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_whatsapp')
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            data = []
            action_id = self.env.ref('product.product_supplierinfo_type_action')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=product.supplierinfo'
            template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_pricelist_approval')
            wa_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_pricelist_template_approval')
            wa_approved_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_pricelist_template_approved')
            approved_template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_pricelist_approved')
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.user_approved_ids.ids:
                    name = approval_matrix_line_id.status or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)
                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'status': name,
                        'user_approved_ids': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.user_approved_ids.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approval_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'user_name': approving_matrix_line_user.name,
                                    'approver_name' : approving_matrix_line_user.name,
                                    'url': url,
                                    'date': date.today(),
                                    'submitter' : approver_name,
                                    'product_lines': data,
                                }
                                if is_vendor_pricelist_approval_email:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_vendor_pricelist_approval_whatsapp:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user,
                                                                           phone_num, url, submitter=approver_name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                    'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'approver_name' : next_approval_matrix_line_id[0].user_ids[0].name,
                                    'url': url,
                                    'date': date.today(),
                                    'submitter' : approver_name,
                                    'product_lines': data,
                                }
                                if is_vendor_pricelist_approval_email:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_vendor_pricelist_approval_whatsapp:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           next_approval_matrix_line_id[0].user_ids[0],
                                                                           phone_num, url, submitter=approver_name)
            if len(record.approval_ids) == len(record.approval_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'date': date.today(),
                    'approver_name' : record.name,
                    'url' : url,
                }
                if is_vendor_pricelist_approval_email:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_vendor_pricelist_approval_whatsapp:
                    phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.request_partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.request_partner_id,
                                                           phone_num, url)

    def action_reject_supplier(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Vendor Pricelist'),
            'res_model': 'cancel.supplier.memory',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_supplier_id': self.id,
            },
        }

    def action_rejected(self, reason):
        for res in self:
            if res.current_user in res.user_approval_ids:
                for line in res.approval_ids:
                    if res.current_user in line.user_ids:
                        if res.current_user not in line.user_approved_ids:
                            user = []
                            user.extend(line.user_approved_ids.ids)
                            user.extend(res.current_user.ids)
                            # line.user_approved_ids = [(6, 0, user)]
                            line.approval += 1
                            # line.approved = False
                            line.update({
                                'user_approved_ids': [(6, 0, user)],
                                'approved': False
                            })
                            res.state = 'rejected'
                            line.time = datetime.strftime(datetime.now(), "%Y-%m-%d %H:%M:%S")
                            # if line.status:
                            #   line.status += "\n%s: Rejected - %s" % (res.current_user.name, line.time)
                            # else:
                            #   line.status = "%s: Rejected - %s" % (res.current_user.name, line.time)
                            if line.status:
                                line.status += "\n%s: Rejected" % (res.current_user.name)
                            else:
                                line.status = "%s: Rejected" % (res.current_user.name)
                            line.feedback = reason


class SupplierInfoApproval(models.Model):
    _name = "product.supplierinfo.approval"
    _description = "Supplier Info Approval"

    @api.model
    def default_get(self, fields):
        res = super(SupplierInfoApproval, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_ids' in context_keys:
                if len(self._context.get('approval_ids')) > 0:
                    next_sequence = len(self._context.get('approval_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    sequence2 = fields.Integer(
        string="Sequence",
        related="sequence",
        readonly=True,
        store=True
    )
    user_ids = fields.Many2many('res.users', string="User")
    minimum_approver = fields.Integer(string="Minimum Approver")
    status = fields.Text("Approval Status")
    time = fields.Char("Time Stamp")
    feedback = fields.Text("Feedback")
    approved = fields.Boolean("Approved")
    approval = fields.Integer("Approval")
    last_approved = fields.Many2one('res.users', string='Users')
    time_stamp = fields.Datetime(string='TimeStamp')
    user_approved_ids = fields.Many2many('res.users', string="User Approved", relation='supplier_approval_supplier_rel')
    supplier_id = fields.Many2one('product.supplierinfo', string="Supplier", domain="[('state1', '=', 'approved')]")

class CanselSupplier(models.TransientModel):
    _name = 'cancel.supplier.memory'
    _description = "Cansel Supplier"

    supplier_id = fields.Many2one('product.supplierinfo', 'Source', domain="[('state1', '=', 'approved')]")
    reason = fields.Text("Reason", required=True)

    def action_cancel_supplier(self):
        product_supplierinfo_id = self.env['product.supplierinfo'].browse(self._context.get('active_ids'))
        user = self.env.user
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_vendor_pricelist_approval_email = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_email')
        is_vendor_pricelist_approval_whatsapp = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_pricelist_approval_whatsapp')
        approving_matrix_line = sorted(product_supplierinfo_id.approval_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        action_id = self.env.ref('product.product_supplierinfo_type_action')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(product_supplierinfo_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=product.supplierinfo'
        rejected_template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_pricelist_approval_rejected')
        wa_rejected_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_pricelist_template_rejected')
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.status or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'status': name, 'time_stamp': datetime.now(), 'feedback': self.reason})
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : product_supplierinfo_id.request_partner_id.email,
                'date': date.today(),
                'url' : url,
            }
            if is_vendor_pricelist_approval_email:
                rejected_template_id.sudo().with_context(ctx).send_mail(product_supplierinfo_id.id, True)
            if is_vendor_pricelist_approval_whatsapp:
                phone_num = str(product_supplierinfo_id.request_partner_id.mobile) or str(product_supplierinfo_id.request_partner_id.phone)
                # product_supplierinfo_id._send_whatsapp_message_approval(wa_rejected_template_id, product_supplierinfo_id.request_partner_id, phone_num, url)
                product_supplierinfo_id._send_qiscus_whatsapp_approval(wa_rejected_template_id,
                                                                        product_supplierinfo_id.request_partner_id,
                                                                        phone_num, url)
        product_supplierinfo_id.write({'state' : 'rejected'})
        return True
