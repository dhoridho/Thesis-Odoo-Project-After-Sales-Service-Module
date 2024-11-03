
from odoo import api , fields , models, _, tools
from datetime import datetime, date
import requests
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
headers = {'content-type': 'application/json'}
from odoo.exceptions import ValidationError, AccessError, UserError, RedirectWarning, Warning
import logging
_logger = logging.getLogger(__name__)
from lxml import etree
import json as simplejson
import pytz



class LimitRequest(models.Model):
    _name = 'limit.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = "Create Limit Request"   


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False




    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)

    name = fields.Char(string='Sequence', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    limit_type = fields.Selection([('credit_limit','Credit Limit'), ('credit_limit_brand','Credit Limit Brand'), ('open_invoice_limit', 'Number of Open Invoices Limit'), ('max_invoice_overdue_days','Max Invoice Overdue (Days)')],
                                      string="Limit Type", tracking=True)
    limit_type_old = fields.Selection([('credit_limit','Credit Limit'), ('open_invoice_limit', 'Number of Open Invoices Limit'), ('max_invoice_overdue_days','Max Invoice Overdue (Days)')],
        default = "credit_limit",
        string="Limit Type Credit Limit", tracking=False)
    limit_type_new = fields.Selection([('credit_limit_brand','Credit Limit Brand'), ('open_invoice_limit', 'Number of Open Invoices Limit'), ('max_invoice_overdue_days','Max Invoice Overdue (Days)')],
                                  default = "credit_limit_brand",
                                  string="Limit Type Credit Limit Brand", tracking=False)
    credit_amount = fields.Float("New Credit Limit Amount",store=True, tracking=True)
    last_credit_limit = fields.Float("Last Credit Limit Amount", tracking=True, compute='_compute_last_limit', store=True)
    open_inv_no = fields.Float("New Number of Open Invoices Limit",store=True, tracking=True)
    last_open_inv_no = fields.Float("Last Number of Open Invoices Limit", tracking=True, compute='_compute_last_limit', store=True)
    new_max_invoice = fields.Float("New Max Invoice Overdue (Days)",store=True, tracking=True)
    last_max_invoice = fields.Float("Last Max Invoice Overdue (Days)", tracking=True, compute='_compute_last_limit', store=True)
    description = fields.Text("Description",store=True, tracking=True)
    state = fields.Selection([("draft","Draft"),
        ("waiting_approval","Waiting For Approval"),
        ("confirmed","Request Approved"),
        ("rejected","Request Rejected")
    ], string='State', default="draft", tracking=True)
    state1 = fields.Selection(related="state", tracking=False)
    state2 = fields.Selection(related="state", tracking=False)
    # branch_id = fields.Many2one('res.branch', string="Branch", required=True, domain=lambda self: [('id', 'in', self.env.branches.ids)], store=True)
    limit_approval_matrix = fields.Many2one('limit.approval.matrix', string="Approval Matrix", compute="_get_limit_matrix")
    approval_ids = fields.One2many('credit.limit.approval', 'credit_id', 'Approval Lines', tracking=True)
    approval_matrix_line_id = fields.Many2one('credit.limit.approval', compute='_get_approve_button', store=False)
    user_approval_ids = fields.Many2many('res.users', string="User")
    current_user = fields.Many2one('res.users')
    approval = fields.Boolean("Approval")
    approval2 = fields.Boolean(compute="_get_approval")
    new_amount = fields.Float(compute="_get_new_amount",store=True)
    last_amount = fields.Float(compute="_get_last_amount",store=True)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    user_id = fields.Many2one('res.users', related='create_uid')
    is_credit_limit_brand = fields.Boolean(related='partner_id.set_customer_credit_limit_per_brand')
    product_brand_ids = fields.One2many('credit.limit.product.brand', 'limit_request_id', string="Products", tracking=True)
    brand_ids = fields.Many2many('product.brand', string='Brand', compute='set_brand_ids', store=True)
    is_external_link = fields.Boolean('Is External Link', default=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(LimitRequest, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                      submenu=submenu)
        is_external_link = self.env.context.get("default_is_external_link")
        doc = etree.XML(res['arch'])
        if is_external_link and view_type == 'form':
            for node in doc.xpath("//field"):
                modifiers = simplejson.loads(node.get("modifiers"))
                modifiers['readonly'] = True
                node.set('modifiers', simplejson.dumps(modifiers))
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


    @api.depends('partner_id','product_brand_ids')
    def set_brand_ids(self):
        for rec in self:
            if rec.product_brand_ids:
                brand_ids=[]
                for line in rec.product_brand_ids:
                    if line.brand_id:
                        brand_ids.append(line.brand_id.id)
                rec.brand_ids = [(6, 0, brand_ids)]    

    @api.onchange('is_credit_limit_brand','limit_type_old','limit_type_new')
    def set_limit_type(self):
        for rec in self:
            if rec.is_credit_limit_brand:
                limit_type = rec.limit_type_new
            else:
                limit_type = rec.limit_type_old
            rec.limit_type = limit_type
            if rec.limit_type != 'credit_limit_brand':
                rec.product_brand_ids = [(6, 0, [])]
            else:
                if not rec.product_brand_ids and rec.is_credit_limit_brand:
                    line_ids = []
                    for limit_brand in rec.partner_id.product_brand_ids:
                        line_ids.append(
                            (0,0, {'sequence': limit_brand.sequence, 'brand_id': limit_brand.brand_id.id, 'last_credit_limit_amount': limit_brand.customer_credit_limit}),
                        )
                    rec.product_brand_ids = [(6, 0, [])]
                    rec.product_brand_ids = line_ids


    def _domain_company(self):
        return [('id','=',self.env.company.id)]
    company_id = fields.Many2one('res.company', string="Company", domain=_domain_company,  required=True, default=lambda self: self.env.company)

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approval_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if self.env.user.id in matrix_line_id.user_ids.ids and self.env.user.id != matrix_line_id.last_approved.id:
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False
            else:
                record.is_approve_button = False
                record.approval_matrix_line_id = False

    @api.depends('last_amount','last_credit_limit','last_open_inv_no','last_max_invoice')
    def _get_last_amount(self):
        for res in self:
            if res.limit_type == 'credit_limit':
                res.last_amount = res.last_credit_limit
            elif res.limit_type == 'open_invoice_limit':
                res.last_amount = res.last_open_inv_no
            elif res.limit_type == 'max_invoice_overdue_days':
                res.last_amount = res.last_max_invoice

    @api.depends('new_amount','credit_amount','open_inv_no','new_max_invoice')
    def _get_new_amount(self):
        for res in self:
            if res.limit_type == 'credit_limit':
                res.new_amount = res.credit_amount
            elif res.limit_type == 'open_invoice_limit':
                res.new_amount = res.open_inv_no
            elif res.limit_type == 'max_invoice_overdue_days':
                res.new_amount = res.new_max_invoice

    @api.depends('approval')
    def _get_approval(self):
        for res in self:
            if self.env.user in res.approval_ids.mapped('user_ids'):
                res.approval2 = True
            else:
                res.approval2 = False

    @api.constrains('user_approval_ids','current_user')
    def _show_approval(self):
        for res in self:
            if self.env.user in res.user_approval_ids:
                res.approval = True
            else:
                res.approval = False

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
                            # 	line.status += "\n%s: Rejected - %s" % (res.current_user.name, line.time)
                            # else:
                            # 	line.status = "%s: Rejected - %s" % (res.current_user.name, line.time)
                            if line.status:
                                line.status += "\n%s: Rejected" % (res.current_user.name)
                            else:
                                line.status = "%s: Rejected" % (res.current_user.name)
                            line.feedback = reason

    def action_reject_approval(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rejected Reason'),
            'res_model': 'cancel.credit.limit',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_limit_id': self.id,
            },
        }

    def request_approve(self):
        self.ensure_one()
        self.state = 'confirmed'
        if self.limit_type == 'credit_limit':
            self.partner_id.cust_credit_limit = self.credit_amount
        if self.limit_type == 'max_invoice_overdue_days':
            self.partner_id.customer_max_invoice_overdue = self.new_max_invoice
        if self.limit_type == 'open_invoice_limit':
            self.partner_id.no_open_inv_limit = self.open_inv_no
        if self.product_brand_ids and self.is_credit_limit_brand and self.limit_type_new == 'credit_limit_brand':
            latest_product_brand = self.product_brand_ids
            self.partner_id.write({'product_brand_ids': [(6, 0, latest_product_brand.ids)]})
            for line in self.product_brand_ids:
                line_partner = self.partner_id.product_brand_ids.filtered(lambda l: l.brand_id == line.brand_id)
                line_partner.customer_credit_limit = line.new_credit_limit_amount

    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.user_id.partner_id.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
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
        self.ensure_one()
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
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.user_id.partner_id.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.user_id.partner_id.name)
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


    def request_approval(self):
        is_email_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_email_notification_customer_credit')
        is_whatsapp_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_whatsapp_notification_customer_credit')
        for record in self:
            approver = False
            data = []
            action_id = self.env.ref('equip3_sale_other_operation.action_credit_limit_request')
            template_id = self.env.ref('equip3_sale_other_operation.email_template_customer_limit')
            wa_template_id = self.env.ref('equip3_sale_other_operation.whatsapp_customer_credit')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=limit.request'
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
                    if is_email_notification_customer_credit:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_whatsapp_notification_customer_credit:
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
                if is_email_notification_customer_credit:
                    template_id.with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_customer_credit:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            record.state = 'waiting_approval'

    # def action_approve_approval(self):
    #     is_email_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_email_notification_customer_credit')
    #     is_whatsapp_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_whatsapp_notification_customer_credit')
    #     for record in self:
    #         base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #         data = []
    #         action_id = self.env.ref('equip3_sale_other_operation.action_credit_limit_request')
    #         url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=limit.request'
    #         template_id = self.env.ref('equip3_sale_other_operation.email_template_customer_limit_approval')
    #         approved_template_id = self.env.ref('equip3_sale_other_operation.email_template_customer_limit_approved')
    #         wa_template_id = self.env.ref('equip3_sale_other_operation.whatsapp_customer_credit_approval')
    #         wa_approved_template_id = self.env.ref('equip3_sale_other_operation.whatsapp_customer_credit_approved')
    #         user = self.env.user
    #         user_tz = pytz.timezone(self.env.user.tz or 'UTC')
    #         today = pytz.utc.localize(datetime.now()).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')
    #         if record.is_approve_button and record.approval_matrix_line_id:
    #             approval_matrix_line_id = record.approval_matrix_line_id
    #             if user.id in approval_matrix_line_id.user_ids.ids and \
    #                 user.id not in approval_matrix_line_id.user_approved_ids.ids:
    #                 name = approval_matrix_line_id.status or ''
    #                 if name != '':
    #                     name += "\n • %s: Approved" % (self.env.user.name)
    #                 else:
    #                     name += "• %s: Approved" % (self.env.user.name)

    #                 approval_matrix_line_id.write({
    #                     'last_approved': self.env.user.id, 'status': name,
    #                     'user_approved_ids': [(4, user.id)]})
    #                 if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.user_approved_ids.ids):
    #                     approval_matrix_line_id.write({'time': today, 'approved': True})
    #                     next_approval_matrix_line_id = sorted(record.approval_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
    #                     approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
    #                     if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
    #                         for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
    #                             ctx = {
    #                                 'email_from': self.env.user.company_id.email,
    #                                 'email_to': approving_matrix_line_user.partner_id.email,
    #                                 'user_name': approving_matrix_line_user.name,
    #                                 'approver_name' : approving_matrix_line_user.name,
    #                                 'url': url,
    #                                 'date': today,
    #                                 'submitter' : approver_name,
    #                                 'product_lines': data,
    #                             }
    #                             if is_email_notification_customer_credit:
    #                                 template_id.sudo().with_context(ctx).send_mail(record.id, True)
    #                             if is_whatsapp_notification_customer_credit:
    #                                 phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
    #                                 # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
    #                                 record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)
    #                     else:
    #                         if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
    #                             ctx = {
    #                                 'email_from': self.env.user.company_id.email,
    #                                 'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
    #                                 'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
    #                                 'approver_name': next_approval_matrix_line_id[0].user_ids[0].name,
    #                                 'url': url,
    #                                 'date': today,
    #                                 'submitter' : approver_name,
    #                                 'product_lines': data,
    #                             }
    #                             if is_email_notification_customer_credit:
    #                                 template_id.sudo().with_context(ctx).send_mail(record.id, True)
    #                             if is_whatsapp_notification_customer_credit:
    #                                 phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
    #                                 # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
    #                                 record._send_qiscus_whatsapp_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
    #         if len(record.approval_ids) == len(record.approval_ids.filtered(lambda r:r.approved)):
    #             record.request_approve()
    #             ctx = {
    #                 'email_from' : self.env.user.company_id.email,
    #                 'email_to' : record.user_id.partner_id.email,
    #                 'date': date.today(),
    #                 'approver_name' : record.name,
    #                 'url' : url,
    #             }
    #             if is_email_notification_customer_credit:
    #                 approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
    #             if is_whatsapp_notification_customer_credit:
    #                 phone_num = str(record.user_id.partner_id.mobile) or str(record.user_id.partner_id.phone)
    #                 # record._send_whatsapp_message_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)
    #                 record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)
    
    
    def action_approve_approval(self):
        is_email_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_email_notification_customer_credit')
        is_whatsapp_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_whatsapp_notification_customer_credit')

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        action_id = self.env.ref('equip3_sale_other_operation.action_credit_limit_request')
        template_id = self.env.ref('equip3_sale_other_operation.email_template_customer_limit_approval')
        approved_template_id = self.env.ref('equip3_sale_other_operation.email_template_customer_limit_approved')
        wa_template_id = self.env.ref('equip3_sale_other_operation.whatsapp_customer_credit_approval')
        wa_approved_template_id = self.env.ref('equip3_sale_other_operation.whatsapp_customer_credit_approved')
        user = self.env.user
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        today = pytz.utc.localize(datetime.now()).astimezone(user_tz).strftime('%Y-%m-%d %H:%M:%S')

        for record in self:
            url = f"{base_url}/web#id={record.id}&action={action_id.id}&view_type=form&model=limit.request"
            data = []

            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and user.id not in approval_matrix_line_id.user_approved_ids.ids:
                    name = f"{approval_matrix_line_id.status}\n • {self.env.user.name}: Approved" if approval_matrix_line_id.status else f"• {self.env.user.name}: Approved"
                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id,
                        'status': name,
                        'user_approved_ids': [(4, user.id)]
                    })
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.user_approved_ids):
                        approval_matrix_line_id.write({'time': today, 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approval_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))

                        if next_approval_matrix_line_id:
                            approving_matrix_line_user = next_approval_matrix_line_id[0].user_ids[0]
                            ctx = {
                                'email_from': self.env.user.company_id.email,
                                'email_to': approving_matrix_line_user.partner_id.email,
                                'user_name': approving_matrix_line_user.name,
                                'approver_name': approving_matrix_line_user.name,
                                'url': url,
                                'date': today,
                                'submitter': approver_name,
                                'product_lines': data,
                            }
                            if is_email_notification_customer_credit:
                                template_id.sudo().with_context(ctx).send_mail(record.id, True)
                            if is_whatsapp_notification_customer_credit:
                                phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                record._send_qiscus_whatsapp_approval(wa_template_id, approving_matrix_line_user, phone_num, url, submitter=approver_name)

            if len(record.approval_ids) == len(record.approval_ids.filtered(lambda r:r.approved)):
                record.request_approve()
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': record.user_id.partner_id.email,
                    'date': today,
                    'approver_name': record.name,
                    'url': url,
                }
                if is_email_notification_customer_credit:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_customer_credit:
                    phone_num = str(record.user_id.partner_id.mobile) or str(record.user_id.partner_id.phone)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.user_id.partner_id, phone_num, url)

    def set_user_approval(self):
        for res in self:
            for line in res.approval_ids:
                if not line.approved:
                    res.user_approval_ids = [(6, 0, line.user_ids.ids)]
                    break

    @api.depends('branch_id', 'credit_amount',
                'new_max_invoice', 'limit_type', 'open_inv_no', 'product_brand_ids.new_credit_limit_amount')
    def _get_limit_matrix(self):
        for res in self:
            # tidak digunakan (?)
            # res.current_user = self.env.user
            if res.limit_type == 'credit_limit':
                amount = res.credit_amount
            elif res.limit_type == "open_invoice_limit":
                amount = res.open_inv_no
            elif res.limit_type == 'credit_limit_brand':
                amount = 0
                if res.product_brand_ids:
                    for line in res.product_brand_ids:
                        if amount < line.new_credit_limit_amount:
                            amount = line.new_credit_limit_amount
            else:
                amount = res.new_max_invoice
            if res.branch_id:
                approval_id = self.env['limit.approval.matrix'].search([('minimum_amt', '<=', amount), ('maximum_amt', '>=', amount), ('branch_id', '=', res.branch_id.id), ('config', '=', res.limit_type)], limit=1)
                if approval_id:
                    res.limit_approval_matrix = approval_id
                    self._get_approver_matrix()
                else:
                    res.limit_approval_matrix = False
                    res.approval_ids = [(6,0,[])]
            else:
                res.limit_approval_matrix = False
                res.approval_ids = [(6,0,[])]
                
    def _get_approver_matrix(self):
        for rec in self:
            if rec.limit_approval_matrix and rec.state == 'draft':
                approval_matrix_line = [
                    (0, 0, {
                        'sequence': line.sequence,
                        'user_ids': [(6, 0, line.user_name_ids.ids)],
                        'minimum_approver': line.minimum_approver,
                    }) for line in rec.limit_approval_matrix.approver_matrix_line_ids
                ]
                
                rec.approval_ids = [(5, 0)] + approval_matrix_line

    # @api.onchange('limit_approval_matrix')
    # def create_approval(self):
    #     for res in self:
    #         if res.state not in ("waiting_approval","confirmed","rejected") and res.limit_approval_matrix:
    #             user = []
    #             approval_id = res.limit_approval_matrix
    #             approval_matrix_line = []
    #             for line in approval_id.approver_matrix_line_ids:
    #                 approval_matrix_line.append((0, 0, {
    #                     'sequence': line.sequence,
    #                     'user_ids': [(6, 0, line.user_name_ids.ids)],
    #                     'minimum_approver': line.minimum_approver,
    #                 }))
    #                 user.extend(line.user_name_ids.ids)
    #             if approval_matrix_line:
    #                 res.approval_ids = approval_matrix_line
    #             if user:
    #                 res.user_approval_ids = user

    @api.onchange('limit_type')
    def _onchange_limit_type(self):
        if self.limit_type == 'credit_limit':
            self.credit_amount = 0.0
            self.new_max_invoice = False
            self.open_inv_no = False
        if self.limit_type == 'max_invoice_overdue_days':
            self.credit_amount = False
            self.new_max_invoice = 0.0
            self.open_inv_no = False
        if self.limit_type == 'open_invoice_limit':
            self.credit_amount = False
            self.new_max_invoice = False
            self.open_inv_no = 0.0

    @api.depends('partner_id', 'limit_type')
    def _compute_last_limit(self):
        for record in self:
            last_credit_limit = 0
            last_max_invoice = 0
            last_open_inv_no = 0
            if record.partner_id:
                last_credit_limit = record.partner_id.cust_credit_limit
                last_max_invoice = record.partner_id.customer_max_invoice_overdue
                last_open_inv_no = record.partner_id.no_open_inv_limit
            record.last_credit_limit = last_credit_limit
            record.last_max_invoice = last_max_invoice
            record.last_open_inv_no = last_open_inv_no

    def request_confirm(self):
        self.ensure_one()
        if self.limit_type == 'credit_limit' and self.credit_amount < self.last_credit_limit:
            return{
                'name': "Credit Limit",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'limit.request.wizard',
                'target': 'new',
            }
        elif self.limit_type == 'max_invoice_overdue_days' and self.new_max_invoice < self.last_max_invoice:
            return {
                'name': "Credit Limit",
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'limit.request.wizard',
                'target': 'new',
            }
        else:
            self.state = 'confirmed'
            if self.limit_type == 'credit_limit':
                self.partner_id.cust_credit_limit = self.credit_amount
            if self.limit_type == 'max_invoice_overdue_days':
                self.partner_id.customer_max_invoice_overdue = self.new_max_invoice

    @api.model
    def create(self, vals):
        if not vals.get('approval_ids'):
            raise Warning(_("There is no approval matrix for this credit limit."))
        vals['name'] = "CLR/" + datetime.strftime(datetime.today(), "%y/%m/%d/") + self.env['ir.sequence'].next_by_code('limit.sequences')
        return super(LimitRequest, self).create(vals)

class CreditLimitApproval(models.Model):
    _name = "credit.limit.approval"
    _description = "Credit Limit Approval"

    @api.model
    def default_get(self, fields):
        res = super(CreditLimitApproval, self).default_get(fields)
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
    time = fields.Char("Timestamp")
    feedback = fields.Text("Feedback")
    approved = fields.Boolean("Approved")
    approval = fields.Integer("Approval")
    user_approved_ids = fields.Many2many('res.users', string="User Approved", relation='credit_approval_credit_rel')
    credit_id = fields.Many2one('limit.request', string="Credit Limit Customer")
    last_approved = fields.Many2one('res.users', string='Users')

    @api.constrains('approved')
    def set_user_approval(self):
        for res in self:
            if res.approved:
                res.credit_id.set_user_approval()

class CanselCreditLimit(models.TransientModel):
    _name = 'cancel.credit.limit'
    _description = "Cancel Credit Limit"

    limit_id = fields.Many2one('limit.request', 'Source', required=True)
    reason = fields.Text("Reason", required=True)

    def action_cancel_limit(self):
        is_email_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_email_notification_customer_credit')
        is_whatsapp_notification_customer_credit = self.env['ir.config_parameter'].sudo().get_param('equip3_sale_other_operation.is_whatsapp_notification_customer_credit')
        limit_request_id = self.env['limit.request'].browse(self._context.get('active_ids'))
        user = self.env.user
        approving_matrix_line = sorted(limit_request_id.approval_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        action_id = self.env.ref('equip3_sale_other_operation.action_credit_limit_request')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(limit_request_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=limit.request'
        rejected_template_id = self.env.ref('equip3_sale_other_operation.email_template_customer_limit_approval_rejected')
        wa_rejected_template_id = self.env.ref('equip3_sale_other_operation.whatsapp_customer_credit_rejected')
        if approving_matrix_line:
            matrix_line = approving_matrix_line[0]
            name = matrix_line.status or ''
            if name != '':
                name += "\n • %s: Rejected" % (user.name)
            else:
                name += "• %s: Rejected" % (user.name)
            matrix_line.write({'status': name, 'time': datetime.now(), 'feedback': self.reason})
            ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : limit_request_id.user_id.partner_id.email,
                'date': date.today(),
                'url' : url,
            }
            if is_email_notification_customer_credit:
                rejected_template_id.sudo().with_context(ctx).send_mail(limit_request_id.id, True)
            if is_whatsapp_notification_customer_credit:
                phone_num = str(limit_request_id.user_id.partner_id.mobile) or str(limit_request_id.user_id.partner_id.phone)
                # limit_request_id._send_whatsapp_message_approval(wa_rejected_template_id, limit_request_id.user_id.partner_id, phone_num, url)
                limit_request_id._send_qiscus_whatsapp_approval(wa_rejected_template_id, limit_request_id.user_id.partner_id, phone_num, url)
        limit_request_id.write({'state' : 'rejected'})
        self.limit_id.action_rejected(self.reason)
