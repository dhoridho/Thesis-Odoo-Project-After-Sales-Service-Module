
import pytz
from pytz import timezone, UTC
from odoo import api, fields, models, _, tools
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import requests
from odoo.exceptions import UserError , ValidationError
import logging
import json
_logger = logging.getLogger(__name__)

headers = {'content-type': 'application/json'}

PURCHASE_REQUISITION_STATES = [
    ('to_approve', 'Waiting for Approval'),
    ('approved', 'Blanket Order Approved'),
    ('rejected', 'Rejected'),
    ('blanket_order', 'Blanket Order'),
    ('ongoing',)
]

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange('destination_warehouse')
    def set_dest(self):
        for res in self:
            if res.destination_warehouse:
                res.picking_type_id = res.destination_warehouse.in_type_id.id

    def _get_type_id(self):
        return self.env.ref('purchase_requisition.type_single').id

    @api.model
    def _default_domain(self):
        if self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix'):
        # if self.env.company.is_vendor_approval_matrix:
            return [('state2', '=', 'approved'), ('supplier_rank', '>', 0), ('is_vendor', '=', True),('branch_id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)]
        else:
            return [('supplier_rank', '>', 0), ('is_vendor', '=', True),('branch_id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)]

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else False


    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        string="Branch",
        required=True,
        tracking=True,
        domain=lambda self: "[('id', 'in', %s), ('company_id','=', company_id)]" % self.env.branches.ids,
        default = _default_branch,
        readonly=False)

    type_id = fields.Many2one('purchase.requisition.type', string="Agreement Type", required=False, default=_get_type_id)

    purchase_request_id = fields.Many2one('purchase.request', string='Blanket Order')

    # branch_id = fields.Many2one('res.branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    def _domain_analytic_group(self):
        return [('company_id','=',self.env.company.id)]
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_bo_rel', 'bo_id', 'tag_id', string="Analytic Group", domain=_domain_analytic_group)
    analytic_accounting = fields.Boolean("Analyic Account", compute="get_analytic_accounting", store=True)
    destination_warehouse = fields.Many2one('stock.warehouse', string="Destination", domain="[('company_id', '=', company_id),('branch_id','=',branch_id)]")
    date_end = fields.Datetime(string='Agreement Deadline', compute="get_analytic_accounting", tracking=True, store=True)
    schedule_date = fields.Date('Schedule Date', tracking=True)
    set_single_delivery_date = fields.Boolean("Single Delivery Date")
    set_single_delivery_destination = fields.Boolean("Single Delivery Destination")
    approval_matrix_id = fields.Many2one('approval.matrix.blanket.order', string="Blanket Order Approval Matrix", compute='_get_approval_matrix')
    is_blanket_order_approval_matrix = fields.Boolean(string="Blanket Order", compute='_get_approve_button_from_config')
    approved_matrix_ids = fields.One2many('approval.matrix.blanket.order.line', 'bo_matrix_id', compute="_compute_approving_matrix_lines_bo", store=True, string="Approved Matrix")
    approval_matrix_line_id = fields.Many2one('approval.matrix.blanket.order.line', string='Blanket Approval Matrix Line', compute='_get_approve_button', store=False)
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    state = fields.Selection(selection_add=PURCHASE_REQUISITION_STATES, string="Status", tracking=False, default='draft', ondelete={'to_approve': 'set default','approved': 'set default','rejected': 'set default','blanket_order': 'set default'})
    bo_state = fields.Selection([
    ('pending_order', 'Pending Order'),
    ('ongoing', 'Ongoing'),
    ('close', 'Closed'),
    ('cancel', 'Cancel')], 'Bo Status', tracking=True)
    bo_state1 = fields.Selection(related='bo_state', tracking=False)
    state1 = fields.Selection(related='state', tracking=True)
    state2 = fields.Selection(related='state', tracking=False)
    bo_state2 = fields.Selection([
        ('draft', 'Draft'),
        ('ongoing', 'Ongoing'),
        ('to_approve', 'Waiting for Approval'),
        ('approved', 'Blanket Order Approved'),
        ('rejected', 'Rejected'),
        ('blanket_order', 'Blanket Order'),
        ('in_progress', 'Confirmed'),
        ('open', 'Bid Selection'),
        ('done', 'Closed'),
        ('close', 'Closed'),
        ('pending_order', 'Pending Order'),
        ('cancel', 'Cancelled')]
        , compute="_compute_bo_state", store=True, string="State")
    state_blanket_order = fields.Selection(selection_add=PURCHASE_REQUISITION_STATES, compute='_set_state')
    partner_id = fields.Many2one('res.partner', string='Vendor', related='vendor_id')
    is_bo_confirm = fields.Boolean(string='Is BO Confirm', compute='_compute_is_bo_confirm', store=False)
    vendor_id = fields.Many2one('res.partner', string="Vendor", domain=_default_domain)
    show_analytic_tags = fields.Boolean("Show Analytic Tags", compute="compute_analytic_tags", store=True)
    amount_total = fields.Float(string='Total', compute='_compute_amount_total', store=True)
    filter_destination_warehouse = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)

    @api.depends('company_id', 'branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            allowed_warehouse = self.env.user.warehouse_ids
            rec.filter_destination_warehouse = json.dumps([('branch_id', '=', rec.branch_id.id), ('company_id', '=', rec.company_id.id), ('id', 'in', allowed_warehouse.ids)])

    @api.onchange('branch_id','company_id')
    def set_warehouse(self):
        for res in self:
            stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
            res.destination_warehouse = stock_warehouse or False

    @api.depends('line_ids.price_unit', 'line_ids.product_qty')
    def _compute_amount_total(self):
        for requisition in self:
            total = 0.0
            for line in requisition.line_ids:
                total += line.price_unit * line.product_qty
            requisition.amount_total = total

    @api.depends('company_id')
    def compute_analytic_tags(self):
        for rec in self:
            rec.show_analytic_tags = self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags')

    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, prev_approver_name, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${prev_approver_name}" in string_test:
                string_test = string_test.replace("${prev_approver_name}", prev_approver_name)
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

    def _send_qiscus_whatsapp_approval(self, template_id, approver, phone, url, prev_approver_name, submitter=False):
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
            if "${prev_approver_name}" in string_test:
                string_test = string_test.replace("${prev_approver_name}", prev_approver_name)
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
                _logger.info(
                    "\nNotification Whatsapp --> Request for Approval:\n-->Header: %s \n-->Parameter: %s \n-->Result: %s" % (
                    headers, params, request_server.json()))
                # if request_server.status_code != 200:
                #     data = request_server.json()
                #     raise ValidationError(f"""{data["error"]["error_data"]["details"]}""")
            except ConnectionError:
                raise ValidationError("Not connect to API Chat Server. Limit reached or not active!")

    @api.depends('state', 'bo_state', 'state_blanket_order')
    def _compute_bo_state(self):
        for record in self:
            if record.state == 'blanket_order':
                record.bo_state2 = record.bo_state
            else:
                record.bo_state2 = record.state
    
    def _compute_is_bo_confirm(self):
        user = self.env.user
        for record in self:
            record.is_bo_confirm = False
            if (user.id == record.user_id.id or user.has_group('base.group_system') \
                or user.has_group('sh_po_tender_management.sh_purchase_tender_manager')):
                record.is_bo_confirm = True
            if (not record.is_blanket_order_approval_matrix or not record.approval_matrix_id) and record.state != 'draft':
                record.is_bo_confirm = False

    def action_bo_close(self):
        for record in self:
            record.write({'bo_state': 'close'})

    def action_bo_cancel(self):
        for record in self:
            record.write({'bo_state': 'cancel'})

    @api.depends('user_id')
    def get_analytic_accounting(self):
        for res in self:
            res.analytic_accounting = self.user_has_groups('analytic.group_analytic_accounting')
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            bo_expiry_date = IrConfigParam.get_param('equip3_purchase_other_operation.bo_expiry_date')
            bo_goods_order_expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_goods_order_expiry_date')
            bo_service_order_expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.bo_service_order_expiry_date')
            # bo_expiry_date = self.env.company.bo_expiry_date
            # bo_goods_order_expiry_date = self.env.company.bo_goods_order_expiry_date
            # bo_service_order_expiry_date = self.env.company.bo_service_order_expiry_date
            context = dict(self.env.context) or {}
            if context.get('goods_order') and bo_goods_order_expiry_date:
                expiry_date = datetime.now() + timedelta(days=int(bo_goods_order_expiry_date))
                res.write({
                    'date_end': expiry_date,
                })
            elif context.get('services_good') and bo_service_order_expiry_date:    
                expiry_date = datetime.now() + timedelta(days=int(bo_service_order_expiry_date))
                res.write({
                    'date_end': expiry_date,
                })
            else:
                if not res.date_end:
                    res.date_end = datetime.now() + timedelta(days=int(bo_expiry_date))

    @api.depends('branch_id')
    def _get_approval_matrix(self):
        for record in self:
            matrix_id = False
            if record.is_goods_orders:
                matrix_id = self.env['approval.matrix.blanket.order'].search([('branch_id', '=', record.branch_id.id), ('order_type', '=', 'goods_order')], limit=1)
            elif record.is_services_orders:
                matrix_id = self.env['approval.matrix.blanket.order'].search([('branch_id', '=', record.branch_id.id), ('order_type', '=', 'services_order')], limit=1)
            else:
                matrix_id = self.env['approval.matrix.blanket.order'].search([('branch_id', '=', record.branch_id.id)], limit=1, order='id desc')
            record.approval_matrix_id = matrix_id

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
    def _compute_approving_matrix_lines_bo(self):
        data = [(5, 0, 0)]
        for record in self:
            counter = 1
            record.approved_matrix_ids = []
            for line in record.approval_matrix_id.approval_matrix_blanket_order_line_ids:
                data.append((0, 0, {
                    'sequence' : counter,
                    'user_ids' : [(6, 0, line.user_ids.ids)],
                    'minimum_approver' : line.minimum_approver,
                }))
                counter += 1
            record.approved_matrix_ids = data

    def _get_approve_button_from_config(self):
        is_blanket_order_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_blanket_order_approval_matrix')
        # is_blanket_order_approval_matrix = self.env.company.is_blanket_order_approval_matrix
        for record in self:
            record.is_blanket_order_approval_matrix = is_blanket_order_approval_matrix

    def bo_request_for_approval(self):
        if not self.line_ids:
            raise UserError(_("You cannot confirm Purchase Blanket Order '%s' because there is no product line.", self.name))

        is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_bo')
        is_whatsapp_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_bo')
        # is_email_notification_tender = self.env.company.is_email_notification_bo
        # is_whatsapp_notification_tender = self.env.company.is_whatsapp_notification_bo
        for record in self:
            approver = False
            for line in record.line_ids:
                if line.price_unit == 0.0:
                    raise UserError(_('You cannot confirm the blanket order without price.'))
            data = []
            blanket_order_deadline = record.date_end
            agreement_deadline_timezone = pytz.timezone(self.env.user.tz)
            blanket_order_deadline_local_datetime = blanket_order_deadline.replace(tzinfo=pytz.utc)
            blanket_order_deadline_local_datetime = blanket_order_deadline_local_datetime.astimezone(agreement_deadline_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            template_id = self.env.ref('equip3_purchase_other_operation.email_template_bo_request')
            wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_bo_request_wa')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(record.id) + '&view_type=form&model=purchase.requisition'
            if is_email_notification_tender:
                if record.approved_matrix_ids and len(record.approved_matrix_ids[0].user_ids) > 1:
                    for approved_matrix_id in record.approved_matrix_ids[0].user_ids:
                        if is_email_notification_tender:
                            approver = approved_matrix_id
                            ctx = {
                                'email_from' : self.env.user.company_id.email,
                                'email_to' : approver.partner_id.email,
                                'approver_name' : approver.name,
                                'requested_by' : self.env.user.name,
                                'product_lines' : data,
                                'url' : url,
                                'date': date.today(),
                                "date_end": blanket_order_deadline_local_datetime,
                                "author_id": self.user_id.partner_id.id,
                            }
                            template_id.with_context(ctx).send_mail(record.id, True)
                        if is_whatsapp_notification_tender:
                            phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                            # record._send_whatsapp_message_approval(wa_template_id, approver.partner_id, phone_num, url, False)
                            record._send_qiscus_whatsapp_approval(wa_template_id, approver.partner_id, phone_num, url,
                                                                   False)
                else:
                    if is_email_notification_tender:
                        approver = record.approved_matrix_ids[0].user_ids[0]
                        ctx = {
                            'email_from': self.env.user.company_id.email,
                            'email_to': approver.partner_id.email,
                            'approver_name': approver.name,
                            "date_end": blanket_order_deadline_local_datetime,
                            "author_id": self.user_id.partner_id.id,
                            'requested_by': self.env.user.name,
                            'product_lines': data,
                            'url': url,
                            'date': date.today(),
                        }
                        template_id.with_context(ctx).send_mail(record.id, True)
                    if is_whatsapp_notification_tender:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # record._send_whatsapp_message_approval(wa_template_id, approver.partner_id, phone_num, url, False)
                        record._send_qiscus_whatsapp_approval(wa_template_id, approver.partner_id, phone_num, url,
                                                               False)
            record.write({'state': 'to_approve'})

    def bo_approving(self):
        is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_bo')
        is_whatsapp_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_bo')
        # is_email_notification_tender = self.env.company.is_email_notification_bo
        # is_whatsapp_notification_tender = self.env.company.is_whatsapp_notification_bo
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(record.id) + '&view_type=form&model=purchase.requisition'
            data = []
            blanket_order_deadline = record.date_end
            agreement_deadline_timezone = pytz.timezone(self.env.user.tz)
            blanket_order_deadline_local_datetime = blanket_order_deadline.replace(tzinfo=pytz.utc)
            blanket_order_deadline_local_datetime = blanket_order_deadline_local_datetime.astimezone(agreement_deadline_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            template_id = self.env.ref('equip3_purchase_other_operation.email_template_reminder_for_bo_approval')
            wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_reminder_for_bo_approval_wa')
            req_approved_template_id = self.env.ref('equip3_purchase_other_operation.email_template_bo_approval_approved')
            req_wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_bo_approval_approved_wa')
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.approved_users.ids:
                    name = approval_matrix_line_id.state_char or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({ 
                        'last_approved': self.env.user.id, 'state_char': name, 
                        'approved_users': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.approved_users.ids):
                        approval_matrix_line_id.write({'time_stamp': datetime.now(), 'approved': True, 'approver_state': 'approved'})
                        next_approval_matrix_line_id = sorted(record.approved_matrix_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if len(approval_matrix_line_id[0].approved_users) > 1:
                            j = 1
                            for name in approval_matrix_line_id[0].approved_users:
                                if j == 1:
                                    approver_name = name.name
                                elif j != len(approval_matrix_line_id.approved_users) and j != 1:
                                    approver_name += ", " + name.name
                                else:
                                    approver_name += " and " + name.name
                                j += 1
                        else:
                            approver_name = approval_matrix_line_id[0].approved_users[0].name
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                if is_email_notification_tender:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': approving_matrix_line_user.partner_id.email,
                                        'user_name': approving_matrix_line_user.name,
                                        'approver_name': approver_name,
                                        'url': url,
                                        "date_end": blanket_order_deadline_local_datetime,
                                        'date': date.today(),
                                        "author_id": self.user_id.partner_id.id,
                                        'product_lines': data,
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_tender:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user.partner_id, phone_num, url, approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           approving_matrix_line_user.partner_id,
                                                                           phone_num, url, approver_name)
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                if is_email_notification_tender:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                        'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                        'approver_name': approver_name,
                                        'url': url,
                                        "date_end": blanket_order_deadline_local_datetime,
                                        "author_id": self.user_id.partner_id.id,
                                        'product_lines': data,
                                        'date': date.today(),
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_tender:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0].partner_id, phone_num, url, approver_name)
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           next_approval_matrix_line_id[0].user_ids[
                                                                               0].partner_id, phone_num, url,
                                                                           approver_name)
                    else:
                        approval_matrix_line_id.write({'approver_state': 'pending'})
            if len(record.approved_matrix_ids) == len(record.approved_matrix_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.user_id.partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_notification_tender:
                    req_approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_tender:
                    phone_num = str(record.user_id.partner_id.mobile) or str(record.user_id.partner_id.phone)
                    # record._send_whatsapp_message_approval(req_wa_template_id, record.user_id.partner_id, phone_num, url, False)
                    record._send_qiscus_whatsapp_approval(req_wa_template_id, record.user_id.partner_id, phone_num,
                                                           url, False)

    def bo_reject(self):
        for record in self:
            return {
                    'type': 'ir.actions.act_window',
                    'name': 'Reject Reason',
                    'res_model': 'bo.request.matrix.reject',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'target': 'new',
                }
    
    @api.onchange('destination_warehouse')
    def onchange_destination_warehouse(self):
        for res in self:
            for line in res.line_ids:
                if res.set_single_delivery_destination:
                    line.destination_warehouse = res.destination_warehouse.id

    @api.onchange('set_single_delivery_date', 'set_single_delivery_destination')
    def set_single_date_destination(self):
        for res in self:
            if res.set_single_delivery_destination:
                stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
                res.destination_warehouse = stock_warehouse
            if res.set_single_delivery_date:
                res.schedule_date = datetime.now().date() + timedelta(days=14)
            for line in res.line_ids:
                if res.set_single_delivery_date:
                    line.schedule_date = res.schedule_date

    @api.onchange('user_id')
    def onchage_user_id(self):
        self._get_approve_button_from_config()
        self._compute_is_bo_confirm()

    def action_new_blanket_order_quotation(self):
        context = dict(self.env.context) or {}
        action = self.env["ir.actions.actions"]._for_xml_id("purchase_requisition.action_purchase_requisition_to_so")
        self.write({'bo_state': 'ongoing'})
        action['context'] = {
            "default_requisition_id": self.id,
            "default_user_id": False,
            "default_analytic_account_group_ids": [(6, 0, self.account_tag_ids.ids)],
        }
        if context.get('goods_order'):
            action['context'].update({
                'default_is_goods_orders': True,
            })
        return action

    def action_in_progress(self):
        if not self.line_ids:
            raise UserError(_("You cannot confirm Purchase Blanket Order '%s' because there is no product line.", self.name))

        res = super(PurchaseRequisition, self).action_in_progress()
        ordering_date1 = fields.Date.today()
        for record in self:
            # if record.is_quantity_copy == 'none':
            #     record.name = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new')
            record.write({'state': 'blanket_order', 'bo_state': 'pending_order', 'ordering_date': ordering_date1})
        return res

    def auto_cancel_pbo(self):
        bo = self.env['purchase.requisition'].search([('date_end', '!=', False)])
        for res in bo:
            if res.date_end.date() <= datetime.today().date():
                if res.bo_state =='ongoing':
                    res.bo_state = 'close'
                elif res.bo_state == 'pending_order':
                    res.bo_state = 'cancel'

    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.g')
        elif context.get('services_good'):
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new.s')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition.blanket.order.new')
        return super(PurchaseRequisition, self).create(vals)


    @api.onchange('account_tag_ids', 'company_id')
    def set_account_tag(self):
        for res in self:
            for line in res.line_ids:
                line.account_tag_ids = res.account_tag_ids

    @api.onchange('user_id')
    def _onchange_user_id(self):
        if self.user_id.id:
            self.account_tag_ids = [(6, 0, self.user_id.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)] # ini yang jalan

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequisition, self).default_get(fields)
        analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
        for analytic_priority in analytic_priority_ids:
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                res.update({
                    'account_tag_ids': [(6, 0, self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)] # ketimpa sama onchange user_id
                })
                break
            elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                res.update({
                    'account_tag_ids': [(6, 0, self.env.user.branch_id.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)] # ketimpa sama onchange user_id
                })
                break
        return res

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

class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    product_description_variants = fields.Text('Description')
    set_single_delivery_date = fields.Boolean("Single Delivery Date", related='requisition_id.set_single_delivery_date')
    set_single_delivery_destination = fields.Boolean("Single Delivery Destination", related='requisition_id.set_single_delivery_destination')
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence')
    sequence2 = fields.Integer(
            string="No",
            related="sequence",
            readonly=True,
            store=True,
    )

    def unlink(self):
        approval = self.requisition_id
        res = super(PurchaseRequisitionLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def default_get(self, fields):
        res = super(PurchaseRequisitionLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'line_ids' in context_keys:
                if len(self._context.get('line_ids')) > 0:
                    next_sequence = len(self._context.get('line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res
    
    @api.model
    def create(self,vals):
        res = super(PurchaseRequisitionLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.requisition_id._reset_sequence()
        return res

    @api.onchange('price_unit')
    def _check_price_unit_blanket_order(self):
        for line in self:
            if line.price_unit < 0:
                raise ValidationError('Please input valid amount for unit price')

    @api.onchange("product_id", "requisition_id.schedule_date", "requisition_id.destination_warehouse")
    def onchange_product_id(self):
        if self.product_id:
            self.product_description_variants = self.product_id.display_name
            if self.product_id.description_purchase:
                display_name = self.product_id.display_name
                description_name = self.product_id.description_purchase
                name = display_name + '\n' + description_name
                self.product_description_variants = name 
        if self.requisition_id.set_single_delivery_date:
            self.schedule_date = self.requisition_id.schedule_date
        if self.requisition_id.set_single_delivery_destination:
            self.destination_warehouse = self.requisition_id.destination_warehouse.id
        else:
            stock_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id),('branch_id', '=', self.env.user.branch_id.id)], order="id", limit=1)
            if stock_warehouse:
                self.destination_warehouse = stock_warehouse

    # @api.depends('company_id')
    # def compute_analytic(self):
    #     for rec in self:
    #         rec.account_tag_ids = rec.requisition_id.account_tag_ids

    @api.depends('company_id')
    def compute_destination(self):
        for res in self:
            if res.requisition_id.set_single_delivery_destination:
                res.destination_warehouse = res.requisition_id.destination_warehouse
            else:
                res.destination_warehouse = False

    @api.depends('company_id')
    def compute_date(self):
        for res in self:
            if res.requisition_id.set_single_delivery_date:
                res.schedule_date = res.requisition_id.schedule_date
            else:
                res.schedule_date = False

    analytic_accounting = fields.Boolean("Analyic Account", related="requisition_id.analytic_accounting")
    destination_warehouse = fields.Many2one('stock.warehouse', string="Destination")
    schedule_date = fields.Date(string='Scheduled Date')
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_bo_line_rel', 'bo_line_id', 'tag_id', string="Analytic Group")
    qty_received = fields.Float('Receiving Quantities', compute='_get_qty_received', store=False)
    qty_ordered = fields.Float('Ordered Quantities', compute='_get_qty_received', store=False)
    qty_remaining = fields.Float('Remaining Quantities', compute='_get_qty_received', store=False)
    qty_invoiced = fields.Float('Billed Quantities', compute='_get_qty_received', store=False)
    vendor_id = fields.Many2one('res.partner', string="Vendor", related='requisition_id.vendor_id')
    is_goods_orders = fields.Boolean(string="Goods Orders", related='requisition_id.is_goods_orders')
    is_services_orders = fields.Boolean(string="Services Orders", default=False, related='requisition_id.is_services_orders')
    order_count = fields.Integer(string='RFQs/Orders', readonly=True, related='requisition_id.order_count')
    filter_destination_warehouse_line = fields.Char(string="Filter Destination Warehouse",compute='_compute_filter_destination', store=False)

    @api.depends('company_id', 'requisition_id.branch_id')
    def _compute_filter_destination(self):
        for rec in self:
            allowed_warehouse = self.env.user.warehouse_ids
            rec.filter_destination_warehouse_line = json.dumps([('branch_id', '=', rec.requisition_id.branch_id.id), ('company_id', '=', rec.company_id.id), ('id', 'in', allowed_warehouse.ids)])

    @api.onchange('product_qty', 'qty_received')
    def set_analytic(self):
        for res in self:
            if not res.account_tag_ids:
                res.account_tag_ids = [(6, 0, res.requisition_id.account_tag_ids.ids)]

    def write(self, vals):
        if 'destination_warehouse' in vals:
            if self.requisition_id.set_single_delivery_destination:
                vals['destination_warehouse'] = self.requisition_id.destination_warehouse
        if 'schedule_date' in vals:
            if self.requisition_id.set_single_delivery_date:
                vals['schedule_date'] = self.requisition_id.schedule_date
        return super(PurchaseRequisitionLine, self).write(vals)

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty=product_qty, price_unit=price_unit, taxes_ids=taxes_ids)
        res['destination_warehouse_id'] = self.destination_warehouse.id
        res['date_planned'] = self.schedule_date
        res['product_qty'] = self.product_qty
        res['price_unit'] = self.price_unit
        res['requisition_line_id'] = self.id
        return res

    def _get_qty_received(self):
        for record in self:
            requisition_line = self.env['purchase.order.line'].search([('requisition_line_id', '=', record.id)])
            record.qty_received = sum(requisition_line.mapped('qty_received'))
            record.qty_invoiced = sum(requisition_line.mapped('qty_invoiced'))
            # record.qty_remaining = record.product_qty - record.qty_received
            # record.qty_remaining = record.product_qty - record.order_count

            req_qty = record.product_qty
            rfq_qty = 0
            for rfq_id in requisition_line:
                if rfq_id.order_id.state != 'cancel':
                    rfq_qty = rfq_qty + rfq_id.product_qty

            record.qty_ordered = rfq_qty
            record.qty_remaining = req_qty - rfq_qty


class Mail(models.Model):
    _inherit = "mail.mail"

    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if context.get('author_id'):
            vals['author_id'] = context.get('author_id')
        return super(Mail, self).create(vals)
