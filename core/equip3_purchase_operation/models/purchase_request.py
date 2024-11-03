from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT, float_compare
import requests
from odoo.http import request
import logging
from odoo.addons.equip3_approval_hierarchy.models.approval_hierarchy import ApprovalHierarchy
_logger = logging.getLogger(__name__)
import json

headers = {'content-type': 'application/json'}

_STATES = [
    ("draft", "Draft"),
    ("to_approve", "Waiting For Approval"),
    ("approved", "Purchase Request Approved"),
    ("purchase_request", "Purchase Request"),
    ("rejected", "Rejected"),
    ("done", "Done"),
]

class PurchaseRequest(models.Model):
    _inherit = 'purchase.request'


    def _domain_analytic_group(self):
        return [('company_id','=',self.env.company.id)]

    @api.model
    def _get_default_requested_by(self):
        return self.env["res.users"].browse(self.env.uid)

    @api.model
    def _company_get(self):
        return self.env["res.company"].browse(self.env.company.id)

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=lambda self: "[('id', 'in', %s), ('company_id','=', company_id)]" % self.env.branches.ids,
        default = _default_branch,
        required = True,
        readonly=False)

    name = fields.Char(
        string="Request Reference",
        required=False,
        default=False,
        tracking=True,
    )
    state = fields.Selection(
        selection_add=_STATES,
        string="Status",
        index=True,
        required=True,
        copy=False,
        default="draft",
        tracking=True,
        ondelete={
            'purchase_request': 'set default'
        }
    )
    pr_state = fields.Selection(related='state')
    purchase_req_state = fields.Selection([('pending', 'Pending'), ('in_progress', 'In Progress'), ('done', 'Done'), ('close', 'Closed'), ('cancel', 'Cancelled')], tracking=True)
    purchase_req_state_1 = fields.Selection(related='purchase_req_state')
    purchase_req_state_2 = fields.Selection(related='purchase_req_state')
    origin = fields.Char(string="Source Document", tracking=True)
    is_goods_orders = fields.Boolean(string="Goods Orders", default=False)
    date_start = fields.Date(
        string="Creation date",
        help="Date when the user initiated the request.",
        tracking=True,
        default=fields.Date.context_today,
    )
    requested_by = fields.Many2one(
        comodel_name="res.users",
        string="Requested by",
        required=True,
        copy=False,
        tracking=True,
        default=_get_default_requested_by,
        index=True,
    )
    assigned_to = fields.Many2one(
        comodel_name="res.users",
        string="Approver",
        tracking=True,
        domain=lambda self: [
            (
                "groups_id",
                "in",
                [self.env.ref("purchase_request.group_purchase_request_user").id,self.env.ref("purchase_request.group_purchase_request_manager").id],
            )
        ],
        index=True,
    )
    description = fields.Text(string="Description", tracking=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        required=True,
        default=_company_get,
        tracking=True,
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Picking Type",
        required=True,
        tracking=True,
    )
    group_id = fields.Many2one(
        comodel_name="procurement.group",
        string="Procurement Group",
        copy=False,
        tracking=True,
        index=True,
    )
    expiry_date = fields.Date('Expiry Date', tracking=True)
    # branch_id = fields.Many2one('res.branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], string="Branch", tracking=True, required=True)
    days_left = fields.Integer("Days Left", tracking=True)
    is_goods_orders = fields.Boolean(string="Goods Orders", default=False)
    is_services_orders = fields.Boolean(string="Services Orders", default=False)
    approval_matrix_id = fields.Many2one('approval.matrix.purchase.request',string="Approval Matrix", compute="_compute_approval_matrix_request", store=True)
    department_id = fields.Many2one(related='requested_by.department_id', string="Department", readonly=True)
    is_approval_matrix_request = fields.Boolean(compute="_compute_is_approval_matrix_request", string="Approving Matrix")
    price_total = fields.Float(string="Price Total", compute="_compute_price_total")
    approved_matrix_ids = fields.One2many('approval.matrix.purchase.request.line', 'request_id', compute="_compute_approving_matrix_lines", store=True, string="Approved Matrix")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('approval.matrix.purchase.request.line', string='Purchase Request Approval Matrix Line', compute='_get_approve_button', store=False)

    analytic_account_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Group', domain=_domain_analytic_group)
    request_date = fields.Date(string="Expected Date")
    pr_request_date = fields.Date(string="Request Date", readonly=True)
    is_single_request_date = fields.Boolean(string="Single Request Date")
    destination_warehouse = fields.Many2one('stock.warehouse', string="Destination")
    is_single_delivery_destination = fields.Boolean(string="Single Delivery Destination")
    analytic_accounting = fields.Boolean("Analyic Account", compute="get_analytic_accounting", store=True)
    partner_id = fields.Many2one(related="requested_by.partner_id", string='Partner')
    report_template_id = fields.Many2one('ir.actions.report', string="Purchase Request Template",
                                         help="Please select Template report for Purchase Request", domain=[('model', '=', 'purchase.request')])
    request_partner_id = fields.Many2one('res.partner', string='Requesting Partner')
    is_requested_by = fields.Boolean(string="Is Requested By", compute="_compute_is_requested")
    is_purchase_request_department = fields.Boolean(string="PR Department", compute="_is_pr_department")

    is_revision_pr = fields.Boolean(string="Revision PR")
    is_revision_created = fields.Boolean(string='Revision Created', copy=False)
    revision_request_id = fields.Many2one('purchase.request', string='Revision Request')
    sh_pr_number = fields.Integer('PR Number', copy=False, default=1)
    sh_purchase_request_id = fields.Many2one('purchase.request', 'PurchaseRequest', copy=False)
    pr = fields.Boolean('PR')
    pr_count = fields.Integer('Quality Checks', compute='_compute_get_pr_count')
    sh_purchase_request_revision_config = fields.Boolean("Enable Purchase Request Revisions")
    sh_revision_pr_id = fields.Many2many("purchase.request",
                                         relation="purchase_request_revision_request_rel",
                                         column1="pr_id",
                                         column2="revision_id",
                                         string="")
    purchase_ids = fields.Many2many('purchase.order', string='Purchase')
    show_analytic_tags = fields.Boolean("Show Analytic Tags", compute="compute_analytic_tags", store=True)
    creation_date = fields.Date(string='Creation Date', default=datetime.today())
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)
    show_confirm = fields.Boolean('Hide Confirm', compute='_compute_show_confirm')
    filter_destination_warehouse = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)

    @api.depends('company_id', 'branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            allowed_warehouse = self.env.user.warehouse_ids
            stock_warehouse = self.env['stock.warehouse'].search([('company_id', '=', rec.company_id.id),('branch_id', '=', rec.branch_id.id), ('id', 'in', allowed_warehouse.ids)])
            rec.filter_destination_warehouse = json.dumps([('id', 'in', stock_warehouse.ids)])
        
            # rec.filter_destination_warehouse = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id), ('id', 'in', allowed_warehouse.ids)])

    @api.depends('state','is_approval_matrix_request','approval_matrix_id')
    def _compute_show_confirm(self):
        for rec in self:
            show_confirm = False
            if not rec.is_approval_matrix_request and rec.state == 'draft':
                show_confirm = True
            elif rec.is_approval_matrix_request and not rec.approval_matrix_id:
                show_confirm = True
            elif rec.is_approval_matrix_request and rec.approval_matrix_id and rec.state == 'approved':
                show_confirm = True
            elif rec.state == 'approved':
                show_confirm = True
            rec.show_confirm = show_confirm

    @api.depends("state", "line_ids.product_qty", "line_ids.cancelled")
    def _compute_to_approve_allowed(self):
        for rec in self:
            if rec.state == "draft":
                rec.to_approve_allowed = rec.state == "draft" and any(
                    [not line.cancelled and line.product_qty for line in rec.line_ids]
                )
            else:
                rec.to_approve_allowed = any(
                    [not line.cancelled and line.product_qty for line in rec.line_ids]
                )

    @api.onchange('branch_id','company_id')
    def set_warehouse(self):
        for res in self:
            stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
            res.destination_warehouse = stock_warehouse or False
    @api.depends('company_id')
    def compute_analytic_tags(self):
        for rec in self:
            rec.show_analytic_tags = self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags')

    @api.depends('requested_by','company_id')
    def _compute_branch(self):
        for rec in self:
            user = self.env['res.users'].browse(self.env.uid)
            if user.has_group('branch.group_multi_branch'):
                branch_id = self.env['res.branch'].search([('id', 'in', self.env.context['allowed_branch_ids'])])
            else:
                if user.branch_id:
                    branch_id = user.branch_id
                else:
                    branch_id = False
            rec.branch_id = self.env.branch

    def sh_quotation_revision(self, default=None):
        if self:
            self.ensure_one()
            self.is_revision_created = True
            if default is None:
                default = {}
            if self.is_revision_pr:
                pr_count = self.search([("revision_request_id", '=', self.revision_request_id.id), ('is_revision_pr', '=', True)])
                split_name = self.name.split('/')
                if split_name[-1].startswith('R'):
                    split_name[-1] = 'R%d' % (len(pr_count) + 1)
                else:
                    split_name.append('R%d' % (len(pr_count) + 1))
                name = '/'.join(split_name)
            else:
                pr_count = self.search([("revision_request_id", '=', self.id), ('is_revision_pr', '=', True)])
                name = _('%s/R%d') % (self.name, len(pr_count) + 1)
            if 'name' not in default:
                default['state'] = 'draft'
                default['origin'] = self.name
                default['sh_purchase_request_id'] = self.id
                default['is_revision_pr'] = True
                default['pr'] = False
                default['line_ids'] = False
                default['purchase_req_state'] = None
                default['pr_request_date'] = datetime.now()

                if self.is_revision_pr:
                    default['revision_request_id'] = self.revision_request_id.id
                else:
                    default['revision_request_id'] = self.id
                default['is_revision_created'] = False
                self.sh_pr_number += 1
            default['is_goods_orders'] = self.is_goods_orders
            new_purchase_id = self.copy(default=default)
            for line in self.line_ids:
                line.copy({
                    'request_id': new_purchase_id.id,
                    'dest_loc_id': line.dest_loc_id.id
                })
            if name.startswith('PR'):
                new_purchase_id.name = name
            if self.is_revision_pr:
                new_purchase_id.sh_revision_pr_id = [(6, 0, self.revision_request_id.ids + pr_count.ids)]
            else:
                new_purchase_id.sh_revision_pr_id = [(6, 0, self.ids)]
        return self.open_quality_check()

    def open_quality_check(self):
        pr = self.env['purchase.request'].search(
            [('sh_purchase_request_id', '=', self.id)])
        action = self.env.ref(
            'equip3_purchase_operation.purchase_request_revision_action').read()[0]
        action['context'] = {
            'domain': [('id', 'in', pr.ids)]
        }
        action['domain'] = [('id', 'in', pr.ids)]
        return action

    def _compute_get_pr_count(self):
        if self:
            for rec in self:
                rec.pr_count = 0
                qc = self.env['purchase.request'].search(
                    [('sh_purchase_request_id', '=', rec.id)])
                rec.pr_count = len(qc.ids)

    def _is_pr_department(self):
        is_pr_department = self.env['ir.config_parameter'].sudo().get_param('is_pr_department', False)
        # is_pr_department = self.env.company.is_pr_department
        for record in self:
            record.is_purchase_request_department = False
            if is_pr_department:
                record.is_purchase_request_department = True

    def _compute_is_requested(self):
        user = self.env.user
        for record in self:
            record.is_requested_by = False
            if user.has_group('purchase_request.group_purchase_request_manager'):
                record.is_requested_by = True

    @api.onchange('analytic_account_group_ids', 'company_id')
    def set_account_tag(self):
        for res in self:
            for line in res.line_ids:
                line.analytic_account_group_ids = res.analytic_account_group_ids

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.line_ids:
                line.sequence = current_sequence
                line.sequence2 = current_sequence
                current_sequence += 1

    def button_confirm_pr(self):
        for record in self:
            for line in record.line_ids:
                if line.product_qty <= 0:
                    raise ValidationError("Quantity should be greater then 0!")
            if not record.line_ids:
                raise ValidationError("Please Enter Lines Data!")
            else:
                record.write({'state': 'purchase_request'})

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
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.partner_id.name)
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
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.partner_id.name)
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

    def send_email_request_approval(self):
        is_email_notification_req = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_email_notification_req')
        is_whatsapp_notification_req = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_whatsapp_notification_req')
        for record in self:
            approver = False
            for line in record.line_ids:
                if line.product_qty <= 0 :
                    raise ValidationError("Quantity should be greater then 0!")
            data = []
            action_id = self.env.ref('purchase_request.purchase_request_form_action')
            template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_request')
            wa_template_id = self.env.ref('equip3_purchase_operation.wa_purchase_req_template')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.request'
            record.request_partner_id = self.env.user.partner_id.id
            if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
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
                    if is_email_notification_req:
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_whatsapp_notification_req:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)
            else:
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
                if is_email_notification_req:
                    template_id.with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_req:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_template_id, approver, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_template_id, approver, phone_num, url)

    def button_to_approve(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval =  IrConfigParam.get_param('is_purchase_request_approval_matrix')
        if approval:
            context = dict(self.env.context) or {}
            for record in self:
                if not record.approval_matrix_id or not record.approved_matrix_ids:
                    raise UserError(_('Please set approval matrix for Purchase Request first!'))

        self.send_email_request_approval()
        return super(PurchaseRequest, self).button_to_approve()

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequest, self).default_get(fields)
        new_date = datetime.now().date() + timedelta(days=14)
        res['sh_purchase_request_revision_config'] = self.env.ref('equip3_purchase_accessright_setting.purchase_setting_1').purchase_revision
        res['request_date'] = new_date
        res['pr_request_date'] = datetime.now().date()
        context = dict(self.env.context) or {}
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
            # if self.env.company.is_good_services_order:
            if context.get('goods_order'):
                expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date_goods') or 0
                # expiry_date = self.env.company.pr_expiry_date or 0
            elif context.get('services_good'):
                expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date_services') or 0
                # expiry_date = self.env.company.pr_expiry_date or 0
            else:
                expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date') or 0
                # expiry_date = self.env.company.pr_expiry_date or 0
        else:
            expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date') or 0
            # expiry_date = self.env.company.pr_expiry_date or 0
        res.update({
            'expiry_date': datetime.now() + timedelta(days=int(expiry_date))
        })
        analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
        for analytic_priority in analytic_priority_ids:
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                res.update({
                    'analytic_account_group_ids': [(6, 0, self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
            elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                res.update({
                    'analytic_account_group_ids': [(6, 0, self.env.user.branch_id.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
        return res

    @api.depends('company_id')
    def get_analytic_accounting(self):
        for res in self:
            res.analytic_accounting = self.user_has_groups('analytic.group_analytic_accounting')

    @api.onchange('request_date', 'is_single_request_date')
    def onchange_request_date(self):
        for record in self:
            for line in record.line_ids:
                if record.is_single_request_date and record.request_date:
                    line.date_required = record.request_date

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.onchange('destination_warehouse','is_single_delivery_destination')
    def _onchange_destination_warehouse(self):
        for res in self:
            for line in res.line_ids:
                if res.is_single_delivery_destination:
                    line.dest_loc_id = res.destination_warehouse.id

    @api.onchange('is_single_delivery_destination')
    def onchange_destination_warehouse(self):
        for record in self:
            if record.is_single_delivery_destination:
                stock_warehouse = record.env['stock.warehouse'].search([('company_id', '=', record.company_id.id),('branch_id', '=', record.branch_id.id)], order="id", limit=1)
                record.destination_warehouse = stock_warehouse

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
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


    @api.depends('approval_matrix_id')
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 0
            record.approved_matrix_ids = []
            hierarchy = ApprovalHierarchy()
            for line in record.approval_matrix_id.approval_matrix_purchase_request_line_ids:
                if line.approver_types == "specific_approver":
                    counter += 1
                    data.append((0, 0, {
                        'sequence' : counter,
                        'user_ids' : [(6, 0, line.user_ids.ids)],
                        'minimum_approver' : line.minimum_approver,
                    }))
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data_seq = 0
                    approvers = hierarchy.get_hierarchy(self, self.requested_by.employee_id, data_seq, manager_ids, seq,
                                                        line.minimum_approver)
                    for user in approvers:
                        counter += 1
                        data.append((0, 0, {
                            'sequence': counter,
                            'user_ids': [(6, 0, [user])],
                            'minimum_approver': 1,
                        }))
            record.approved_matrix_ids = data

    @api.depends('line_ids', 'line_ids.price_total')
    def _compute_price_total(self):
        for record in self:
            record.price_total = sum(record.line_ids.mapped('price_total'))

    def _compute_is_approval_matrix_request(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        approval =  IrConfigParam.get_param('is_purchase_request_approval_matrix')
        # approval = self.env.company.is_purchase_request_approval_matrix
        for record in self:
            record.is_approval_matrix_request = approval

    @api.onchange('requested_by')
    def onchange_purchase_name(self):
        self._compute_is_approval_matrix_request()
        self._is_pr_department()
        self._compute_is_requested()

    @api.depends('branch_id', 'company_id', 'department_id')
    def _compute_approval_matrix_request(self):
        for record in self:
            record.approval_matrix_id = False
            if record.is_approval_matrix_request:
                if record.is_goods_orders and record.is_approval_matrix_request and record.is_purchase_request_department:
                    approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                        ('branch_id', '=', record.branch_id.id),
                        ('company_id', '=', record.company_id.id),
                        ('department_id', '=', record.department_id.id),
                        ('order_type', '=', "goods_order")], limit=1)
                    record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                elif record.is_services_orders and record.is_approval_matrix_request and record.is_purchase_request_department:
                    approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                        ('branch_id', '=', record.branch_id.id),
                        ('company_id', '=', record.company_id.id),
                        ('department_id', '=', record.department_id.id),
                        ('order_type', '=', "services_order")], limit=1)
                    record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                elif record.is_goods_orders and record.is_approval_matrix_request:
                    approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                        ('branch_id', '=', record.branch_id.id),
                        ('company_id', '=', record.company_id.id),
                        ('order_type', '=', "goods_order")], limit=1)
                    record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                elif record.is_services_orders and record.is_approval_matrix_request:
                    approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                        ('branch_id', '=', record.branch_id.id),
                        ('company_id', '=', record.company_id.id),
                        ('order_type', '=', "services_order")], limit=1)
                    record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                else:
                    if record.is_purchase_request_department:
                        approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                            ('branch_id', '=', record.branch_id.id),
                            ('department_id', '=', record.department_id.id),
                            ('company_id', '=', record.company_id.id)], limit=1)
                        record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
                    else:
                        approval_matrix_id = self.env['approval.matrix.purchase.request'].search([
                            ('branch_id', '=', record.branch_id.id),
                            ('company_id', '=', record.company_id.id)], limit=1)
                        record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False

    def action_request_approval(self):
        pass

    def action_approve(self):
        pass

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Rejected Reason',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'approval.request.reject',
            'target': 'new',
        }

    def action_confirm_purchase_request(self):
        for record in self:
            for line in record.line_ids:
                if line.product_qty <= 0:
                    raise ValidationError("Quantity should be greater then 0!")
            if not record.line_ids:
                raise ValidationError("Please Enter Lines Data!")
            else:
                record.write({'state': 'approved', 'purchase_req_state': 'pending'})





    # @api.model
    # def _default_picking_type(self):
    #     type_obj = self.env["stock.picking.type"]
    #     company_id = self.env.context.get("company_id") or self.env.company.id
    #     types = type_obj.search(
    #         [("code", "=", "incoming"), ("warehouse_id.company_id", "=", company_id)]
    #     )
    #     if not types:
    #         types = type_obj.search(
    #             [("code", "=", "incoming"), ("warehouse_id", "=", False)]
    #         )
    #     return types[:1]




    def button_draft(self):
        res = super(PurchaseRequest, self).button_draft()
        for record in self:
            record.write({'purchase_req_state': 'pending'})
        return res

    def auto_cancel_pr(self):
        pr = self.env['purchase.request'].search([
            ('expiry_date','<',date.today()),
            '|',
            ('state', 'in', ('draft','to_approve','approved')),
            ('purchase_req_state', '=', 'pending')])
        if pr:
            pr.write({'purchase_req_state': 'cancel'})

        pr = self.env['purchase.request'].search([('expiry_date','<',date.today()),('purchase_req_state', '=', 'in_progress')])
        for request in pr:
            tender_ids = self.env['purchase.agreement'].search([
                ('purchase_request_id','=',request.id),
                ('state','!=','cancel'),
            ])
            if not request.mapped("line_ids.purchase_lines.order_id").filtered(lambda p:p.state1 != 'cancel') and not tender_ids:
                request.write({'purchase_req_state': 'cancel'})



    def send_email(self):
        template_before = self.env.ref('equip3_purchase_operation.email_template_pr_expiry_reminder')
        template_after = self.env.ref('equip3_purchase_operation.email_template_pr_expiry_reminder_after')
        notif = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_notification')
        on_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_on_date_notify')
        before_exp = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_enter_before_first_notify') or 3
        after_exp = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_enter_after_first_notify') or 1
        # notif = self.env.company.pr_expiry_notification
        # on_date = self.env.company.pr_on_date_notify
        # before_exp = self.env.company.pr_enter_before_first_notify
        # after_exp = self.env.company.pr_enter_after_first_notify
        pr = self.env['purchase.request'].search(['|',('state', 'not in', ('approved', 'done', 'rejected')),('purchase_req_state', '!=', 'done')])

        if notif:
            for res in pr:
                if res.expiry_date:
                    if str(res.expiry_date) == datetime.strftime(datetime.now() + timedelta(days=int(before_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                        # Before Expiry Date
                        res.days_left = int(before_exp)
                        template_before.send_mail(
                            res.id, force_send=True)
                    elif str(res.expiry_date) == datetime.strftime(datetime.now() - timedelta(days=int(after_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                        # After Expiry Date
                        template_after.send_mail(
                            res.id, force_send=True)


    def get_full_url(self):
        for res in self:
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (res.id, res._name)
            return base_url

    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if not context.get('default_is_rental_orders'):
            if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
                if vals.get('is_goods_orders'):
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.req.seqs.goods')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.req.seqs.services')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.req.seqs')
        # exp_date = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.pr_expiry_date') or 30
        # vals['expiry_date'] = datetime.now() + timedelta(days=int(exp_date))
        return super(PurchaseRequest, self).create(vals)

    def button_approved(self):
        for record in self:
            is_email_notification_req = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_email_notification_req')
            is_whatsapp_notification_req = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.is_whatsapp_notification_req')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            data = []
            action_id = self.env.ref('purchase_request.purchase_request_form_action')
            url = base_url + '/web#id=' + str(record.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.request'
            template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_request_approve')
            approved_template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_req_approval_approved')
            wa_template_id = self.env.ref('equip3_purchase_operation.email_template_reminder_for_purchase_req_approval_wa')
            wa_approved_template_id = self.env.ref('equip3_purchase_operation.email_template_purchase_req_approval_approved_wa')
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
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        approver_name = ' and '.join(approval_matrix_line_id.mapped('user_ids.name'))
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                ctx = {
                                    'email_from': self.env.user.company_id.email,
                                    'email_to': approving_matrix_line_user.partner_id.email,
                                    'user_name': approving_matrix_line_user.name,
                                    'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                                    'url': url,
                                    'submitter' : approver_name,
                                    'product_lines': data,
                                    'date': date.today(),
                                }
                                if is_email_notification_req:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_req:
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
                                    'approver_name': ','.join(approval_matrix_line_id.user_ids.mapped('name')),
                                    'url': url,
                                    'submitter' : approver_name,
                                    'product_lines': data,
                                    'date': date.today(),
                                }
                                if is_email_notification_req:
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_req:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0], phone_num, url, submitter=approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                          next_approval_matrix_line_id[0].user_ids[0],
                                                                          phone_num, url, submitter=approver_name)

                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'purchase_req_state': 'pending', 'state': 'approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.request_partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_notification_req:
                    approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_req:
                    phone_num = str(record.request_partner_id.mobile) or str(record.request_partner_id.phone)
                    # record._send_whatsapp_message_approval(wa_approved_template_id, record.request_partner_id, phone_num, url)
                    record._send_qiscus_whatsapp_approval(wa_approved_template_id, record.request_partner_id,
                                                          phone_num, url)

    def button_done_pr(self):
        for record in self:
            if record.purchase_count <= 0:
                raise ValidationError(_("Please create RFQ"))
            else:
                record.write({'purchase_req_state': 'done'})

    def button_close_pr(self):
        for record in self:
            record.write({'purchase_req_state': 'close'})

    def button_cancel_pr(self):
        for record in self:
            purchase_order_ids = record.mapped("line_ids.purchase_lines.order_id")
            for order in purchase_order_ids:
                if order.state in ('purchase', 'done'):
                    raise ValidationError(_("Purchase Request cannot be cancelled. Purchase Order to vendor has been created for this Purchase Request."))
                if order.state != 'cancel':
                    raise ValidationError(_("There is Active RFQ. If you want to cancel Purchase Request please cancel the RFQ."))
            record.write({'purchase_req_state': 'cancel'})


class PurchaseRequestLine(models.Model):
    _inherit = 'purchase.request.line'

    currency_id = fields.Many2one(related="request_id.currency_id", readonly=True)

    def check_line(self):
        for res in self:
            res_line = res.request_id.line_ids.filtered(lambda x: x.product_id.id == res.product_id.id and x.date_required == res.date_required and x.dest_loc_id.id == res.dest_loc_id.id)
            if res_line:
                seq = []
                for i in res_line:
                    if not seq:
                        seq.append(i.sequence)
                    else:
                        if i.sequence not in seq:
                            raise ValidationError('You have the same record in line %s!' % str(seq[0]))

    @api.onchange('dest_loc_id')
    def set_destination(self):
        for res in self:
            if res.request_id.is_single_delivery_destination:
                res.dest_loc_id = res.request_id.destination_warehouse
            else:
                if not res.dest_loc_id:
                    res.dest_loc_id = False
                else:
                    res.check_line()

    @api.onchange('estimated_cost')
    def _check_price_unit(self):
        for line in self:
            if line.price_total < 0:
                raise ValidationError('Please input a valid amount for unit price')

    @api.onchange('date_required')
    def set_receipt(self):
        for res in self:
            if res.request_id.is_single_request_date:
                res.date_required = res.request_id.request_date
            else:
                if not res.date_required:
                    res.date_required = False
                else:
                    res.check_line()

    @api.onchange('product_id')
    def check_product(self):
        for res in self:
            res.check_line()
