# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from email.policy import default
import string
from odoo import api, fields, models, tools,http, _
from odoo.addons.website.models import ir_http
from datetime import datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import requests
from odoo.exceptions import ValidationError, UserError
import json
headers = {'content-type': 'application/json'}
import logging
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False


    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        default = _default_branch,
        readonly=False)

    filter_branch = fields.Char("filter branch", compute='_compute_filter_branch', store=False)

    vendor_sequence = fields.Char("Vendor ID", readonly=True, copy=False)
    is_vendor = fields.Boolean(string="Is a Vendor")
    state = fields.Selection([("draft", "Draft"),
                              ("waiting_approval", "Waiting For Approval"),
                              ("approved", "Approved"),
                              ("rejected", "Rejected"),
                              ("blacklisted", "Blacklisted"),
                              ], string='State', default="draft")
    state1 = fields.Selection(related="state")
    state2 = fields.Selection(related="state")
    state3 = fields.Selection(related="state")
    is_approving_matrix_vendor = fields.Boolean(compute="_compute_approving_matrix", string="Approving Matrix Vendor")
    approved_user_ids = fields.Many2many('res.users', 'approved_res_user_rel', 'user_id', 'line_id', string="Approved User")
    approving_matrix_vendor_id = fields.Many2one('approval.matrix.vendor', string="Approval Matrix", compute="_compute_matrix", store=True)
    approved_matrix_ids = fields.One2many('approval.matrix.vendor.line', 'app_matrix_id', compute="_compute_approving_matrix_lines", store=True, string="Approved Matrix")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.vendor.line', string='Vendor Approval Matrix Line', compute='_get_approve_button', store=False)
    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')
    capital_revenue = fields.Float('Capital Revenue')
    company_size = fields.Integer('Company Size')
    company_size2 = fields.Integer('Company Size2')
    is_similiar = fields.Boolean(string='Is Similiar', compute="_compute_is_similiar")
    similiar_partner_count = fields.Integer(string='Similiar Partner Count', compute="_compute_is_similiar")
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female')
    ], 'Gender')
    place = fields.Char("Place of Birth")
    birthdate = fields.Date("Date of Birth")
    blacklist_history_ids = fields.One2many(comodel_name='partner.blacklist.history', inverse_name='partner_id', string='Blacklist History')
    vendor_creation_date = fields.Date(string='Vendor Creation Date', readonly=True)
    last_state = fields.Char(string='Last State Vendors')
    last_state_customer = fields.Char(string='Last State Customer')

    def export_data(self, fields_to_export):
        default_fields_to_export = ['vendor_sequence', 'customer_sequence', 'display_name', 'phone', 'email', 'rfm_segment_id', 'user_id', 'activity_ids', 'city', 'country_id', 'branch_id', 'company_id']
        if fields_to_export == default_fields_to_export:
            # update context untuk pengecekan model ketika print header excel
            ctx = (http.request.context.copy())
            ctx.update(res_partner=True)
            http.request.context = ctx
            # merubah field yg akan di export pada customer dan vendor
            fields_to_export = ['id','display_name', 'phone', 'mobile', 'email', 'country_id', 'city', 'company_id', 'is_vendor', 'is_customer']
        else:
            # update context untuk skip perubahan
            ctx = (http.request.context.copy())
            ctx.update(skip=True)
        res = super().export_data(fields_to_export)
        return res

    @api.depends('company_id')
    def _compute_filter_branch(self):
        for rec in self:
            rec.filter_branch = json.dumps([('id', 'in', self.env.branches.ids), ('company_id','=', self.company_id.id)])

    @api.onchange('is_vendor')
    def onchange_vendor_creation_date(self):
        if self.is_vendor == True:
            self.vendor_creation_date = fields.Date.today()
        if self.is_vendor == False:
            self.vendor_creation_date = False

    def action_blacklisted(self):
        for partner in self:
            if partner.is_vendor:
                # Untuk vendor, gunakan state
                partner.write({
                    'last_state': partner.state,
                    'state': 'blacklisted',
                    'active': False
                })

            if partner.is_customer:
                partner.write({
                    'last_state_customer': partner.state_customer,
                    'state_customer': 'blacklisted',
                    'active': False
                })

    def action_whitelisted(self):
        is_vendor_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix',
                                                                                      'False') == 'True'
        is_customer_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_customer_approval_matrix',
                                                                                        'False') == 'True'

        for partner in self:
            if partner.is_vendor:
                if is_vendor_approving_matrix:
                # Kembalikan state untuk vendor
                    if partner.last_state:
                        partner.write({
                            'state': partner.last_state,
                            'active': True
                        })
                    else:
                        raise ValidationError(_("Previous state is not found for unblacklisting."))
                else:
                    partner.write({
                        'state': 'approved',
                        'active': True
                    })

            if partner.is_customer:
                if is_customer_approving_matrix:
                # Kembalikan state_customer untuk customer
                    if partner.last_state_customer:
                        partner.write({
                            'state_customer': partner.last_state_customer,
                            'state': partner.last_state_customer,
                            'active': True
                        })
                    else:
                        raise ValidationError(_("Previous state is not found for unblacklisting."))
                else:
                    partner.write({
                        'state_customer': partner.last_state_customer,
                        'state': partner.last_state_customer,
                        'active': True
                    })
            partner._compute_approving_matrix_lines()

    def find_partner_similiar(self, name,phone='',mobile='',vat='',my_id=False):
        where_params = ''
        id_params = ''
        query = """
            SELECT id, name
            FROM res_partner
            WHERE (lower(name) = lower('{}'){}){}
        """
        if phone:
            where_params += " or phone = '{}'".format(phone)
        if mobile:
            where_params += " or mobile = '{}'".format(mobile)
        if vat:
            where_params += " or vat = '{}'".format(vat)
        if my_id:
            id_params += " and id != {}".format(my_id)
        if name:
            name = name.replace("'","''")
        self.env.cr.execute(query.format(name, where_params, id_params))
        query_result = self.env.cr.dictfetchall()
        return query_result

    @api.depends('name','phone','mobile')
    def _compute_is_similiar(self):
        for i in self:
            is_similiar = False
            similiar_partner_count = 0
            get_partners = self.find_partner_similiar(i.name,i.phone,i.mobile,i.vat,my_id=i.id)
            if len(get_partners) > 0:
                is_similiar = True
                similiar_partner_count = len(get_partners)
            i.is_similiar = is_similiar
            i.similiar_partner_count = similiar_partner_count

    def action_open_similiar_partner(self):
        get_partners = self.find_partner_similiar(self.name,self.phone,self.mobile,self.vat,my_id=self.id,)
        partner_ids = []
        for partner in get_partners:
            partner_ids.append(partner['id'])
        action = {
            'name': _('Similar Vendor'),
            'view_mode': 'tree,form',
            'res_model': 'res.partner',
            'type': 'ir.actions.act_window',
            'domain': [('id', 'in', partner_ids)],
        }
        return action

    @api.model
    def create(self, values):
        res = super(ResPartner, self).create(values)
        if 'email' in values:
            cek_email = self.env['res.partner'].sudo().search([('email', '=', res.email)])
        if (res.parent_id and res.parent_id.vendor_sequence) or not res.parent_id:
            if 'is_vendor' in values:
                if values.get('is_vendor', False):
                    sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
                    res.vendor_sequence = sequence
                    res.supplier_rank = 1
                else:
                    res.supplier_rank = 0

        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval = IrConfigParam.get_param('is_vendor_approval_matrix')
        # approval = self.env.company.is_vendor_approval_matrix
        if not approval:
            res.state = "approved"
            if res.is_vendor and not res.vendor_sequence:
                if res.parent_id and res.parent_id.is_vendor and not res.parent_id.vendor_sequence:
                    sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
                    res.parent_id.vendor_sequence = sequence
                    res.supplier_rank = 1
                # Auto is Vendor Child ids nya
                if res.parent_id and (res.parent_id.is_vendor or res.parent_id.vendor_sequence):
                    res.is_vendor = True
                # sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
                # res.vendor_sequence = sequence
                # res.supplier_rank = 1
        elif approval and res.is_vendor:
            # Auto is Vendor Child ids nya
            if res.parent_id and (res.parent_id.is_vendor or res.parent_id.vendor_sequence):
                res.is_vendor = True
                res.vendor_sequence = ""
        return res

    def write(self, values):
        if values.get('is_vendor') == True and self.is_vendor == False:
            sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
            values.update({'vendor_sequence': sequence})
            values.update({'supplier_rank': 1})
        elif values.get('is_vendor') == False and self.is_vendor == True:
            res = super(ResPartner, self).write(values)
            if self.create_date != self.write_date:
                is_data_exist = 0
                res_data = self.env['purchase.order'].search([('partner_id', '=', self.ids[0])], limit=1)
                if len(res_data) > 0:
                    is_data_exist = 1

                if is_data_exist == 0:
                    res_data = self.env['account.move'].search([('partner_id', '=', self.ids[0])], limit=1)
                    if len(res_data) > 0:
                        is_data_exist = 1

                if is_data_exist == 1:
                    # values.update({'is_vendor': True})
                    pass
                else:
                    # values.update({'is_vendor': False})
                    values.update({'vendor_sequence': None})
                    values.update({'supplier_rank': 0})
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval = IrConfigParam.get_param('is_vendor_approval_matrix')
        # approval = self.env.company.is_vendor_approval_matrix
        if "is_vendor" in values and "vendor_sequence" in values:
            if not approval:
                if values['is_vendor'] and not values['vendor_sequence']:
                    sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
                    values['vendor_sequence'] = sequence
                    values['supplier_rank'] = 1
        res = super(ResPartner, self).write(values)
        return res

    @api.depends('branch_id')
    def _compute_matrix(self):
        for res in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            approval = IrConfigParam.get_param('is_vendor_approval_matrix')
            # approval = self.env.company.is_vendor_approval_matrix
            res.approving_matrix_vendor_id = False
            if approval:
                matrix_id = self.env['approval.matrix.vendor'].search([('branch_id', '=', res.branch_id.id)], limit=1)
                if matrix_id:
                    res.approving_matrix_vendor_id = matrix_id

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = dict(self.env.context) or {}
        domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
        return super(ResPartner, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = dict(self.env.context) or {}
        domain.extend(['|',('branch_id', '=', False), ('branch_id', 'in', self.env.branches.ids)])
        is_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix', False)
        # is_approving_matrix = self.env.company.is_vendor_approval_matrix
        if is_approving_matrix and context.get('default_is_vendor'):
            domain.extend([('state', '=', 'approved')])
        return super(ResPartner, self).read_group(domain, fields, groupby, offset=offset, limit=limit,orderby=orderby, lazy=lazy)

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
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

    @api.depends('approving_matrix_vendor_id', 'branch_id')
    def _compute_approving_matrix_lines(self):
        for record in self:
            data = [(5, 0, 0)]
            counter = 1
            record.approved_matrix_ids = []
            for line in record.approving_matrix_vendor_id.approval_matrix_line_ids:
                data.append((0, 0, {
                    'sequence': counter,
                    'user_ids': [(6, 0, line.user_ids.ids)],
                    'minimum_approver': line.minimum_approver,
                }))
                counter += 1
            record.approved_matrix_ids = data

    def _compute_approving_matrix(self):
        is_approving_matrix = self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix')
        # is_approving_matrix = self.env.company.is_vendor_approval_matrix
        for record in self:
            record.is_approving_matrix_vendor = is_approving_matrix

    @api.onchange('branch_id')
    def _onchange_branch(self):
        self._compute_approving_matrix()
        self._get_approve_button()
        self._compute_matrix()

    # @api.model
    # def create(self, values):
    #     res = super(ResPartner, self).create(values)
    #     if res.supplier_rank == 1:
    #         sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
    #         res.vendor_sequence = sequence
    #     else:
    #         res.state = 'approved'
    #     return res

    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.vendor_sequence)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.name)
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
            if "${requester_name}" in string_test:
                string_test = string_test.replace("${requester_name}", record.request_partner_id.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.vendor_sequence)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.name)
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
        is_vendor_approval_email = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_email')
        is_vendor_approval_whatsapp = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_whatsapp')
        for record in self:
            data = []
            action_id = self.env.ref('equip3_purchase_masterdata.action_vendor_to_approval')
            template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor')
            wa_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(action_id.id) + '&view_type=form&model=res.partner'
            record.request_partner_id = self.env.user.partner_id.id
            if not record.approved_matrix_ids:
                raise ValidationError(_("Please set the Vendor Approval Matrix!"))
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                    approver = approved_matrix_id
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'requested_by': self.env.user.name,
                        'product_lines': data,
                        'date': date.today(),
                        'url': url,
                    }
                    if is_vendor_approval_email:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_vendor_approval_whatsapp:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            elif record.approved_matrix_ids:
                approver = record.approved_matrix_ids[0].user_ids[0]
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': approver.partner_id.email,
                    'approver_name': approver.name,
                    'requested_by': self.env.user.name,
                    'product_lines': data,
                    'date': date.today(),
                    'url': url,
                }
                if is_vendor_approval_email:
                    template_id.with_context(ctx).send_mail(record.id, True)
                if is_vendor_approval_whatsapp:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            record.write({'state': 'waiting_approval'})

    def action_approved(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_vendor_approval_email = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_email')
        is_vendor_approval_whatsapp = IrConfigParam.get_param('equip3_purchase_masterdata.is_vendor_approval_whatsapp')
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            data = []
            action_id = self.env.ref('equip3_purchase_masterdata.action_vendor_to_approval')
            url = base_url + '/web#id=' + str(record.id) + '&action=' + str(action_id.id) + '&view_type=form&model=res.partner'
            template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_approval')
            approved_template_id = self.env.ref('equip3_purchase_masterdata.email_template_vendor_approved')
            wa_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_template_approval')
            wa_approved_template_id = self.env.ref('equip3_purchase_masterdata.whatsapp_vendor_template_approved')
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                        user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    if name != '':
                        name += "\n • %s: Approved" % (self.env.user.name)
                    else:
                        name += "• %s: Approved" % (self.env.user.name)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'state_char': name,
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r: r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'user_name': approving_matrix_line_user.name,
                                    'approver_name': approving_matrix_line_user.name,
                                    'url': url,
                                    'date': date.today(),
                                    'submitter': approver_name,
                                    'product_lines': data,
                                }
                                if is_vendor_approval_email:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_vendor_approval_whatsapp:
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
                                    'approver_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                    'url': url,
                                    'date': date.today(),
                                    'submitter': approver_name,
                                    'product_lines': data,
                                }
                                if is_vendor_approval_email:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_vendor_approval_whatsapp:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           next_approval_matrix_line_id[0].user_ids[0],
                                                                           phone_num, url, submitter=approver_name)
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r: r.approved)):
                record.write({'state': 'approved'})
                if not record.vendor_sequence:
                    sequence = self.env['ir.sequence'].next_by_code('vendor.id.sequence')
                    record.vendor_sequence = sequence
                    record.supplier_rank = 1
                ctx = {
                    'email_from': self.env.user.company_id.email,
                    'email_to': record.request_partner_id.email,
                    'date': date.today(),
                    'approver_name': record.name,
                    'url': url,
                }
                if is_vendor_approval_email:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_vendor_approval_whatsapp:
                    phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.request_partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.request_partner_id,
                                                           phone_num, url)

    def action_rejected(self):
        for record in self:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Reject Reason',
                'res_model': 'approval.matrix.vendor.reject',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }

    def action_set_to_draft(self):
        for rec in self:
            rec.write({
                'state': 'draft',
                'active': True
            })

    @api.model
    def _fill_empty_company(self):
        partner_sudo = self.sudo()
        company_sudo = self.env['res.company'].sudo()
        any_company = company_sudo.search([], order="id asc", limit=1)
        partner_ids = partner_sudo.search([('company_id', '=', False)])
        for partner_id in partner_ids:
            company_id = company_sudo.search([('partner_id', '=', partner_id.id)], limit=1)
            if company_id:
                company = company_id
            else:
                if partner_id.user_ids and partner_id.user_ids[0].company_id:
                    company = partner_id.user_ids[0].company_id
                else:
                    company = any_company
            partner_id.write({'company_id': company.id})

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Customers'),
            'template': '/equip3_purchase_masterdata/static/xls/res_partner.xls'
        }]
