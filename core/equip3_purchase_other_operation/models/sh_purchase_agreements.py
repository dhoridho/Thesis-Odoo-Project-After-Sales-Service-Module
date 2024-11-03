
import pytz
from pytz import timezone, UTC
from odoo import models, fields, api, _
from datetime import datetime, timedelta, date
from odoo.exceptions import UserError , ValidationError
from odoo import tools
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.http import request
import requests
import logging

_logger = logging.getLogger(__name__)
headers = {'content-type': 'application/json'}

class ShPurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement'
    _order = 'id desc'

    sh_order_date = fields.Date('Ordering Date', tracking=True, default=fields.Date.today)
    sh_delivery_date = fields.Date('Schedule Date', tracking=True)
    state = fields.Selection(selection_add=[('waiting_approval', 'Waiting for Approval'), ('confirm', 'Purchase Tender'), ('pending', 'Pending'), ('bid_submission', 'Bid Submission'), ('bid_selection', 'Bid Selection'), (
        'closed', 'Closed'),('reject', 'Rejected'), ('cancel', 'Cancelled'), ('tender_approved', 'Tender Approved')], string="State", default='draft', tracking=True)
    state1 = fields.Selection([('draft', 'Draft'), ('waiting_approval', 'Waiting for Approval'), ('confirm', 'Purchase Tender')])
    state4 = fields.Selection([('draft', 'Draft'), ('waiting_approval', 'Waiting for Approval'), ('reject', 'Rejected'), ('tender_approved', 'Tender Approved'),('confirm', 'Purchase Tender')])
    state2 = fields.Selection([('pending', 'Pending'),('bid_submission', 'Bid Submission'), ('bid_selection', 'Bid Selection'), ('closed', 'Closed'), ('cancel', 'Cancelled')])
    pt_state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Purchase Tender'),
        ('reject', 'Rejected'),
        ('waiting_approval', 'Waiting for Approval'),
        ('pending', 'Pending'),
        ('bid_submission', 'Bid Submission'),
        ('bid_selection', 'Bid Selection'),
        ('closed', 'Closed'),
        ('cancel', 'Cancelled'),
        ('tender_approved', 'Tender Approved')]
        , compute="_compute_pt_state", store=True, string="State")
    state3 = fields.Selection(related='state2', tracking=False)
    state5 = fields.Selection(related='state4', tracking=False)
    approval_matrix = fields.Many2one('purchase.agreement.approval.matrix', string="Approval Matrix", compute="_get_approval_matrix", store=True)
    amount = fields.Float('Amount', compute="_get_amount")
    approval_matrix_line_ids = fields.One2many('purchase.agreement.approval.matrix.lines', 'approval_matrix', string='Approving Matrix')
    user_approval_ids = fields.Many2many('res.users', string="User")
    current_user = fields.Many2one('res.users', compute='_get_current_user')
    partner_id = fields.Many2one('res.partner', string='Vendor', related='sh_purchase_user_id.partner_id')
    approver = fields.Boolean('Approver')
    line_approve = fields.Integer('Approved')
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('purchase.agreement.approval.matrix.lines', string='Blanket Approval Matrix Line', compute='_get_approve_button', store=False)
    sh_bid_agreement_deadline = fields.Datetime('Submission Expiry Date', tracking=True)
    sh_bid_selection_agreement_deadline = fields.Datetime('Selection Expiry Date', tracking=True)
    is_purchase_tender_approval_matrix = fields.Boolean(string="Agreement Approval Matrix", compute='_get_approve_button_from_config')
    term_condition = fields.Many2one('term.condition', string="Terms and Conditions: ", tracking=True)
    term_condition_box = fields.Text("Terms and Conditions")
    sh_notes = fields.Text("Terms & Conditions")
    sh_partner_id = fields.Many2one('res.partner', string='Vendor', related='sh_purchase_user_id.partner_id', store=True)

    @api.depends('state', 'state1', 'state4', 'state2')
    def _compute_pt_state(self):
        for record in self:
            if record.state == "confirm":
                record.pt_state = record.state2
            else:
                record.pt_state = record.state

    def action_confirm_pt(self):
        for record in self:
            record.state4 = "confirm"
            record.state = "confirm"

    @api.onchange('term_condition')
    def _set_term_condition_box(self):
        for res in self:
            if res.term_condition:
                res.term_condition_box = res.term_condition.term_condition
                # res.sh_notes = res.term_condition.term_condition
            else:
                res.term_condition_box = False
                # res.sh_notes = False

    def _get_approve_button_from_config(self):
        is_purchase_tender_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_tender_approval_matrix')
        # is_purchase_tender_approval_matrix = self.env.company.is_purchase_tender_approval_matrix
        for record in self:
            record.is_purchase_tender_approval_matrix = is_purchase_tender_approval_matrix

    def set_notes(self):
        res_text = ""
        for res in self:
            if res.term_condition_box:
                res_text = res.term_condition_box
        return res_text

    @api.onchange('sh_purchase_user_id')
    def onchage_user_id(self):
        self._get_approve_button_from_config()

    @api.model
    def get_agreement_data(self):
        data = {}
        tender_ids = self.search([])
        total_tender_ids = tender_ids.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and (r.state4 in ('draft', 'waiting_approval', 'tender_approved', 'confirm') or r.state2 in ('bid_submission', 'bid_selection', 'closed')))
        active_tender = tender_ids.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and r.state2 in ('bid_submission', 'bid_selection'))
        today_tender = tender_ids.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and r.create_date.date() == date.today())
        data.update({
            'total_tender': len(total_tender_ids),
            'active_tender': len(active_tender),
            'today_tender': len(today_tender),
        })
        purchase_order_ids = self.env['purchase.order'].search([('is_submit_quotation', '=', True), ('agreement_id', '!=', False)])
        purchase_order_data = [{
            'name': order.name,
            'message': order.partner_id.name + ' have submitted Documents for ' + order.agreement_id.name,
        } for order in purchase_order_ids]
        data.update({
            'notifications': purchase_order_data
        })
        return data

    @api.model
    def show_total_tender(self):
        tender_ids = self.search([])
        total_tender_ids = tender_ids.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and (r.state4 in ('draft', 'waiting_approval', 'tender_approved', 'confirm') or r.state2 in ('bid_submission', 'bid_selection', 'closed')))
        return {
            "name": "Total Tender",
            "type": "ir.actions.act_window",
            "res_model": "purchase.agreement",
            "view_mode": "list",
            "views": [[False, 'list'],[False, 'form']],
            "domain": [('id', 'in', total_tender_ids.ids)],
            "target": "current",
        }

    @api.model
    def show_active_tender(self):
        tender_ids = self.search([])
        active_tender = tender_ids.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and r.state2 in ('bid_submission', 'bid_selection'))
        return {
            "name": "Total Tender",
            "type": "ir.actions.act_window",
            "res_model": "purchase.agreement",
            "view_mode": "list",
            "views": [[False, 'list'],[False, 'form']],
            "domain": [('id', 'in', active_tender.ids)],
            "target": "current",
        }

    @api.model
    def show_today_tender(self):
        tender_ids = self.search([])
        today_tender = tender_ids.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and r.create_date.date() == date.today())
        return {
            "name": "Total Tender",
            "type": "ir.actions.act_window",
            "res_model": "purchase.agreement",
            "view_mode": "list",
            "views": [[False, 'list'],[False, 'form']],
            "domain": [('id', 'in', today_tender.ids)],
            "target": "current",
        }

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(record.approval_matrix_line_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
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

    @api.onchange('account_tag_ids')
    def set_account_tag(self):
        for res in self:
            for line in res.sh_purchase_agreement_line_ids:
                line.analytic_tag_ids = res.account_tag_ids

    @api.onchange('sh_delivery_date', 'destination_warehouse_id')
    def set_dest_date_line(self):
        for record in self:
            for line in record.sh_purchase_agreement_line_ids:
                line.schedule_date = record.sh_delivery_date
                line.dest_warehouse_id = record.destination_warehouse_id.id

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

    def action_new_quotation2(self):
        context = dict(self._context or {})
        context.update({'default_agreement_id': self.id, 'default_partner_ids': self.partner_ids.ids})
        return {
            'name': _('New Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.quotation.agreement',
            'view_id': self.env.ref('equip3_purchase_other_operation.wizard_quotation_agreement_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_analyze_rfq(self):
        res = super(ShPurchaseAgreement, self).action_analyze_rfq()
        context = dict(self._context or {})
        res['context'].update(context)
        return res

    def create_new_rfq(self, vendors):
        context = dict(self._context or {})
        for rec in self:
            po_obj = self.env['purchase.order']
            line_ids = []
            current_date = None
            # is_goods_orders = False
            # if rec.is_goods_orders:
            #     is_goods_orders = True
            for rec_line in rec.sh_purchase_agreement_line_ids:
                picking = rec_line.picking_type_id.id
                line_vals = {
                    'product_id': rec_line.sh_product_id.id,
                    'name': rec_line.sh_product_id.name,
                    'date_planned': rec_line.schedule_date,
                    'product_qty': rec_line.sh_qty,
                    'analytic_tag_ids': rec_line.analytic_tag_ids.ids,
                    'status': 'draft',
                    'agreement_line_id': rec_line.id,
                    'sh_product_description': rec_line.sh_product_description,
                    'agreement_id': rec.id,
                    # 'is_goods_orders': is_goods_orders,
                    'product_uom': rec_line.sh_product_uom_id.id,
                    'price_unit': rec_line.sh_price_unit,
                    'destination_warehouse_id': rec_line.dest_warehouse_id.id,
                    'picking_type_id':rec_line.picking_type_id.id,
                    'base_quantity': rec_line.sh_qty,
                }
                if context.get('services_good'):
                    line_vals.update({'is_services_orders': True})
                elif context.get('goods_order'):
                    line_vals.update({'is_goods_orders': True})
                elif context.get('assets_orders'):
                    line_vals.update({'is_assets_orders': True})
                elif context.get('rentals_orders'):
                    line_vals.update({'is_rental_orders': True})
                line_ids.append(line_vals)
            i = 0
            for vendor in vendors:
                vals = {
                    'partner_id': vendor.id,
                    'agreement_id': rec.id,
                    'origin': rec.name,
                    'analytic_account_group_ids': rec.account_tag_ids.ids,
                    'branch_id': rec.branch_id.id,
                    'user_id': rec.sh_purchase_user_id.id,
                    'picking_type_id': picking or False,
                    # 'order_line': line_ids
                    'is_single_delivery_destination': rec.set_single_delivery_destination,
                    'is_delivery_receipt': rec.set_single_delivery_date,
                    'date_planned': rec.sh_delivery_date,
                    'destination_warehouse_id': rec.destination_warehouse_id.id,
                }
                if context.get('services_good'):
                    vals.update({'is_services_orders': True})
                elif context.get('goods_order'):
                    vals.update({'is_goods_orders': True})
                elif context.get('assets_orders'):
                    vals.update({'is_assets_orders': True})
                elif context.get('rentals_orders'):
                    vals.update({'is_rental_orders': True})
                    vals['rent_duration'] = rec.rent_duration  
                    vals['rent_duration_unit'] = rec.rent_duration_unit
                if rec.is_assets_orders:
                    vals['date_order'] = datetime.now()
                elif rec.is_services_orders:
                    rfq_exp_date_services = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_services')
                    # rfq_exp_date_services = self.env.company.rfq_exp_date_services
                    vals['date_order'] = datetime.now() + timedelta(days=int(rfq_exp_date_services))
                else:
                    rfq_exp_date_goods = self.env['ir.config_parameter'].get_param('equip3_purchase_operation.rfq_exp_date_goods')
                    # rfq_exp_date_goods = self.env.company.rfq_exp_date_goods
                    vals['date_order'] = datetime.now() + timedelta(days=int(rfq_exp_date_goods))
                purchase_id = po_obj.with_context(context).create(vals)
                purchase_id._onchange_partner_invoice_id()
                for line in line_ids:
                    line.update({'order_id': purchase_id.id})
                    self.env['purchase.order.line'].create(line)
                i += 1
            if i and rec.state2 == 'pending':
                rec.state = 'bid_submission'

    def auto_bid_selection_pr(self):
        pt = self.env['purchase.agreement'].search([('sh_bid_agreement_deadline', '<=', datetime.now()), ('state', '=', 'bid_submission')])
        for res in pt:
            res.state = 'bid_selection'

    def auto_done_closed_pt(self):
        pt = self.env['purchase.agreement'].search([('sh_bid_selection_agreement_deadline', '<=', datetime.now()), ('state', '=', 'bid_selection')])
        for res in pt:
            # rfq = self.env['purchase.order'].sudo().search([('agreement_id', '=', res.id), ('state', 'in', ['purchase']), ('selected_order', '=', False)])
            # if rfq:
            res.action_close()
            # else:
            #     res.action_cancel()

    @api.constrains('state')
    def set_expiry_date_bid(self):
        expiry = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_expiry_date')
        # expiry = self.env.company.pt_expiry_date
        for res in self:
            if expiry:
                expiry_date = datetime.now() + timedelta(days=int(expiry))
                if res.state == 'bid_submission':
                    res.sh_bid_agreement_deadline = expiry_date
                elif res.state == 'bid_selection':
                    res.sh_bid_selection_agreement_deadline = expiry_date
            else:
                res.write({
                    'sh_bid_agreement_deadline': datetime.now(),
                    'sh_bid_selection_agreement_deadline': datetime.now()
                })


    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
        # if self.env.company.is_good_services_order:
            if context.get('goods_order'):
                if 'tender_scope' in vals:
                    if vals['tender_scope'] == 'open_tender':
                        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.g.open')
                    else:
                        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.g')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.g')
            elif context.get('services_good'):
                if 'tender_scope' in vals:
                    if vals['tender_scope'] == 'open_tender':
                        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.s.open')
                    else:
                        vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.s')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.s')
        else:
            if 'tender_scope' in vals:
                if vals['tender_scope'] == 'open_tender':
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.open')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs')
            else:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs')
        return super(ShPurchaseAgreement, self).create(vals)

    def write(self, vals):
        if 'name' in vals:
            vals['name'] = self.name
        res = super(ShPurchaseAgreement, self).write(vals)
        return res

    def action_set_to_draft(self):
        self.ensure_one()
        res = super(ShPurchaseAgreement, self).action_set_to_draft()
        self.create_approval()
        return res

    @api.onchange('amount', 'approval_matrix', 'line_approve', 'user_approval_ids')
    def _get_user_approval(self):
        for res in self:
            if res.approval_matrix:
                user = []
                for line in res.approval_matrix_line_ids:
                    if not line.approved:
                        user.extend(line.user_ids.ids)
                        break
                res.user_approval_ids = [(6, 0, user)]
                res.current_user = self.env.user
                if res.current_user in res.user_approval_ids:
                    res.approver = True
                else:
                    res.approver = False

    @api.depends('sh_purchase_agreement_line_ids.sh_price_unit')
    def _get_current_user(self):
        for rec in self:
            rec.current_user = self.env.user
            if rec.current_user in rec.user_approval_ids:
                rec.approver = True
            else:
                rec.approver = False

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Purchase Tender'),
            'res_model': 'cancel.tender.memory',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_tender_id': self.id,
            },
        }

    def action_rejected(self, reason):
        is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_tender')
        is_whatsapp_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_tender')
        # is_email_notification_tender = self.env.company.is_email_notification_tender
        # is_whatsapp_notification_tender = self.env.company.is_whatsapp_notification_tender
        for res in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(res.id) + '&view_type=form&model=purchase.agreement'
            if res.current_user in res.user_approval_ids:
                for line in res.approval_matrix_line_ids:
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
                            res.state = 'reject'
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
                            template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_approval_rejected')
                            if is_email_notification_tender:
                                ctx = {
                                    'email_from' : self.env.user.company_id.email,
                                    'email_to' : res.sh_purchase_user_id.partner_id.email,
                                    'date': date.today(),
                                    'url' : url,
                                }
                                template_id.sudo().with_context(ctx).send_mail(res.id, True)
                            if is_whatsapp_notification_tender:
                                req_wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_approval_rejected_wa')
                                phone_num = str(res.sh_purchase_user_id.partner_id.mobile) or str(res.sh_purchase_user_id.partner_id.phone)
                                # res._send_whatsapp_message_approval(req_wa_template_id, res.sh_purchase_user_id.partner_id, phone_num, url, line)
                                res._send_qiscus_whatsapp_approval(req_wa_template_id,
                                                                    res.sh_purchase_user_id.partner_id, phone_num, url,
                                                                    line)
                            break


    def _send_whatsapp_message_approval(self, template_id, approver, phone, url, previous_approval, submitter=False):
        for record in self:
            string_test = str(tools.html2plaintext(template_id.body_html))
            if "${date}" in string_test:
                string_test = string_test.replace("${date}", date.today().strftime(DEFAULT_SERVER_DATE_FORMAT))
            if "${approver_name}" in string_test:
                string_test = string_test.replace("${approver_name}", approver.name)
            if "${name}" in string_test:
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.partner_id.name)
            if "${previous_approver_name}" in string_test:
                if previous_approval:
                    if len(previous_approval.user_approved_ids) > 1:
                        j = 1
                        for name in previous_approval.user_approved_ids:
                            if j == 1:
                                approver_name = name.name
                            elif j != len(previous_approval.user_approved_ids) and j != 1:
                                approver_name += ", " + name.name
                            else:
                                approver_name += " and " + name.name
                            j += 1
                    else:
                        approver_name = previous_approval.user_approved_ids[0].name
                    string_test = string_test.replace("${previous_approver_name}", approver_name)
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

    def _send_qiscus_whatsapp_approval(self, template_id, approver, phone, url, previous_approval, submitter=False):
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
                string_test = string_test.replace("${name}", record.name)
            if "${partner_name}" in string_test:
                string_test = string_test.replace("${partner_name}", record.partner_id.name)
            if "${previous_approver_name}" in string_test:
                if previous_approval:
                    if len(previous_approval.user_approved_ids) > 1:
                        j = 1
                        for name in previous_approval.user_approved_ids:
                            if j == 1:
                                approver_name = name.name
                            elif j != len(previous_approval.user_approved_ids) and j != 1:
                                approver_name += ", " + name.name
                            else:
                                approver_name += " and " + name.name
                            j += 1
                    else:
                        approver_name = previous_approval.user_approved_ids[0].name
                    string_test = string_test.replace("${previous_approver_name}", approver_name)
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

    def action_approved(self):
        is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_tender')
        is_whatsapp_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_tender')
        # is_email_notification_tender = self.env.company.is_email_notification_tender
        # is_whatsapp_notification_tender = self.env.company.is_whatsapp_notification_tender
        for record in self:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id='+ str(record.id) + '&view_type=form&model=purchase.agreement'
            data = []
            template_id = self.env.ref('equip3_purchase_other_operation.email_template_reminder_for_purchase_tender_approval')
            wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_reminder_for_purchase_tender_approval_wa')
            req_approved_template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_approval_approved')
            req_wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_approval_approved_wa')
            user = self.env.user
            sh_agreement_deadline = record.sh_agreement_deadline
            agreement_deadline_timezone = pytz.timezone(self.env.user.tz)
            sh_agreement_deadline_local_datetime = sh_agreement_deadline.replace(tzinfo=pytz.utc)
            sh_agreement_deadline_local_datetime = sh_agreement_deadline_local_datetime.astimezone(agreement_deadline_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if user.id in approval_matrix_line_id.user_ids.ids and \
                    user.id not in approval_matrix_line_id.user_approved_ids.ids:
                    name = approval_matrix_line_id.status or ''
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                    if name != '':
                        name += "\n • %s: Approved - %s" % (self.env.user.name, local_datetime)
                    else:
                        name += "• %s: Approved - %s" % (self.env.user.name, local_datetime)

                    approval_matrix_line_id.write({
                        'last_approved': self.env.user.id, 'status': name,
                        'user_approved_ids': [(4, user.id)]})
                    if approval_matrix_line_id.minimum_approver == len(approval_matrix_line_id.user_approved_ids.ids):
                        approval_matrix_line_id.write({'time': datetime.now(), 'approved': True})
                        next_approval_matrix_line_id = sorted(record.approval_matrix_line_ids.filtered(lambda r: not r.approved), key=lambda r:r.sequence)
                        if len(approval_matrix_line_id[0].user_approved_ids) > 1:
                            j = 1
                            for name in approval_matrix_line_id[0].user_approved_ids:
                                if j == 1:
                                    approver_name = name.name
                                elif j != len(approval_matrix_line_id.user_approved_ids) and j != 1:
                                    approver_name += ", " + name.name
                                else:
                                    approver_name += " and " + name.name
                                j += 1
                        else:
                            approver_name = approval_matrix_line_id[0].user_approved_ids[0].name
                        if next_approval_matrix_line_id and len(next_approval_matrix_line_id[0].user_ids) > 1:
                            for approving_matrix_line_user in next_approval_matrix_line_id[0].user_ids:
                                if is_email_notification_tender:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': approving_matrix_line_user.partner_id.email,
                                        'user_name': approving_matrix_line_user.name,
                                        'approver_name': approver_name,
                                        'url': url,
                                        "author_id": record.partner_id.id,
                                        "date_end": sh_agreement_deadline_local_datetime,
                                        'product_lines': data,
                                        'date': date.today(),
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_tender:
                                    phone_num = str(approving_matrix_line_user.partner_id.mobile) or str(approving_matrix_line_user.partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, approving_matrix_line_user.partner_id, phone_num, url, approval_matrix_line_id[0])
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           approving_matrix_line_user.partner_id,
                                                                           phone_num, url, approval_matrix_line_id[0])
                        else:
                            if next_approval_matrix_line_id and next_approval_matrix_line_id[0].user_ids:
                                if is_email_notification_tender:
                                    ctx = {
                                        'email_from': self.env.user.company_id.email,
                                        'email_to': next_approval_matrix_line_id[0].user_ids[0].partner_id.email,
                                        'user_name': next_approval_matrix_line_id[0].user_ids[0].name,
                                        'approver_name': approver_name,
                                        'url': url,
                                        "author_id": record.partner_id.id,
                                        "date_end": sh_agreement_deadline_local_datetime,
                                        'product_lines': data,
                                        'date': date.today(),
                                    }
                                    template_id.sudo().with_context(ctx).send_mail(record.id, True)
                                if is_whatsapp_notification_tender:
                                    phone_num = str(next_approval_matrix_line_id[0].user_ids[0].partner_id.mobile) or str(next_approval_matrix_line_id[0].user_ids[0].partner_id.phone)
                                    # record._send_whatsapp_message_approval(wa_template_id, next_approval_matrix_line_id[0].user_ids[0].partner_id, phone_num, url, approval_matrix_line_id[0])
                                    record._send_qiscus_whatsapp_approval(wa_template_id,
                                                                           next_approval_matrix_line_id[0].user_ids[
                                                                               0].partner_id, phone_num, url,
                                                                           approval_matrix_line_id[0])
            if len(record.approval_matrix_line_ids) == len(record.approval_matrix_line_ids.filtered(lambda r:r.approved)):
                record.write({'state': 'tender_approved', 'state4': 'tender_approved'})
                ctx = {
                    'email_from' : self.env.user.company_id.email,
                    'email_to' : record.sh_purchase_user_id.partner_id.email,
                    'date': date.today(),
                    'url' : url,
                }
                if is_email_notification_tender:
                    req_approved_template_id.sudo().with_context(ctx).send_mail(record.id, True)
                if is_whatsapp_notification_tender:
                    phone_num = str(record.partner_id.mobile) or str(record.partner_id.phone)
                    # record._send_whatsapp_message_approval(req_wa_template_id, record.sh_purchase_user_id.partner_id, phone_num, url, False)
                    record._send_qiscus_whatsapp_approval(req_wa_template_id, record.sh_purchase_user_id.partner_id,
                                                           phone_num, url, False)

    def action_request(self):
        if not self.sh_purchase_agreement_line_ids:
            raise UserError(_("You cannot confirm Purchase Tender '%s' because there is no product line.", self.name))

        for res in self:
            is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_tender')
            is_whatsapp_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_whatsapp_notification_tender')
            # is_email_notification_tender = self.env.company.is_email_notification_tender
            # is_whatsapp_notification_tender = self.env.company.is_whatsapp_notification_tender
            approver = False
            res.state = 'waiting_approval'
            for vals in res.sh_purchase_agreement_line_ids:
                if vals.sh_qty <= 0 :
                    raise UserError("You cannot confirm purchase tender without quantity.")
            data = []
            sh_agreement_deadline = res.sh_agreement_deadline
            agreement_deadline_timezone = pytz.timezone(self.env.user.tz)
            sh_agreement_deadline_local_datetime = sh_agreement_deadline.replace(tzinfo=pytz.utc)
            sh_agreement_deadline_local_datetime = sh_agreement_deadline_local_datetime.astimezone(agreement_deadline_timezone).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_request')
            wa_template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_request_wa')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url + '/web#id=' + str(res.id) + '&view_type=form&model=purchase.agreement'
            if res.approval_matrix_line_ids and len(res.approval_matrix_line_ids[0].user_ids) > 1:
                for approved_matrix_id in res.approval_matrix_line_ids[0].user_ids:
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
                            "date_end": sh_agreement_deadline_local_datetime,
                            "author_id": res.partner_id.id,
                        }
                        template_id.with_context(ctx).send_mail(res.id, True)
                    if is_whatsapp_notification_tender:
                        phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                        # res._send_whatsapp_message_approval(wa_template_id, approver.partner_id, phone_num, url, False)
                        res._send_qiscus_whatsapp_approval(wa_template_id, approver.partner_id, phone_num, url, False)
            elif res.approval_matrix_line_ids:
                approver = res.approval_matrix_line_ids[0].user_ids[0]
                if is_email_notification_tender:
                    ctx = {
                        'email_from': self.env.user.company_id.email,
                        'email_to': approver.partner_id.email,
                        'approver_name': approver.name,
                        'requested_by': self.env.user.name,
                        'product_lines': data,
                        'date': date.today(),
                        "date_end": sh_agreement_deadline_local_datetime,
                        "author_id": res.partner_id.id,
                        'url': url,
                    }
                    template_id.with_context(ctx).send_mail(res.id, True)
                if is_whatsapp_notification_tender:
                    phone_num = str(approver.partner_id.mobile) or str(approver.partner_id.phone)
                    # res._send_whatsapp_message_approval(wa_template_id, approver.partner_id, phone_num, url, False)
                    res._send_qiscus_whatsapp_approval(wa_template_id, approver.partner_id, phone_num, url, False)

    @api.depends('sh_purchase_agreement_line_ids.sh_price_unit')
    def _get_amount(self):
        for res in self:
            amount = 0
            for line in res.sh_purchase_agreement_line_ids:
                amount += line.sh_price_unit
            res.amount = amount
            res._get_user_approval()

    @api.depends('branch_id', 'sh_agreement_type', 'amount')
    def _get_approval_matrix(self):
        set_approval_matrix = self.env['ir.config_parameter'].sudo().get_param('is_purchase_tender_approval_matrix')
        is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
        # set_approval_matrix = self.env.company.is_purchase_tender_approval_matrix
        # is_good_services_order = self.env.company.is_good_services_order
        for res in self:
            res.approval_matrix = False
            if set_approval_matrix:
                approval_id = False
                if res.is_goods_orders and is_good_services_order:
                    approval_id = self.env['purchase.agreement.approval.matrix'].search([('branch_id', '=', res.branch_id.id), ('order_type', '=', 'goods_order')], limit=1, order='id desc')
                elif res.is_services_orders and is_good_services_order:
                    approval_id = self.env['purchase.agreement.approval.matrix'].search([('branch_id', '=', res.branch_id.id), ('order_type', '=', 'services_order')], limit=1, order='id desc')
                else:
                    approval_id = self.env['purchase.agreement.approval.matrix'].search([('branch_id', '=', res.branch_id.id)], limit=1, order='id desc')
                res.approval_matrix = approval_id

    @api.onchange('approval_matrix','branch_id','sh_agreement_type','state')
    def create_approval(self):
        for res in self:
            if res.state == "draft":
                approval = self.env['purchase.agreement.approval.matrix.lines']
                # approval_matrix = res.approval_matrix
                approval_ids = approval.search([('approval_matrix', '=', res.id)])
                approval_ids.sudo().unlink()
                # res.approval_matrix = approval_matrix
                user = []
                approval_matrix_line = []
                for line in res.approval_matrix.approval_matrix_purchase_agreement_line_ids:
                    lines = approval.create({
                        'sequence': line.sequence,
                        'user_ids': [(6, 0, line.user_ids.ids)],
                        'minimum_approver': line.minimum_approver,
                    })
                    approval_matrix_line.append(lines.id)
                    user.extend(line.user_ids.ids)
                if approval_matrix_line:
                    res.approval_matrix_line_ids = [(6, 0, approval_matrix_line)]
                if user:
                    res.user_approval_ids = [(6, 0, user)]

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def _reset_sequence2(self):
        for rec in self:
            current_sequence = 1
            for line in rec.sh_purchase_agreement_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(ShPurchaseAgreement, self.with_context(keep_line_sequence=True)).copy(default)
        return res

    @api.constrains('state')
    def set_state3(self):
        for res in self:
            if res.state == 'draft':
                res.state1 = 'draft'
                res.state2 = False
                res.state4 = 'draft'
            elif res.state == 'waiting_approval':
                res.state1 = 'waiting_approval'
                res.state4 = 'waiting_approval'
            elif res.state == 'confirm':
                res.state1 = 'confirm'
                res.state2 = 'pending'
                res.state4 = 'confirm'
            elif res.state == 'bid_submission':
                res.state2 = 'bid_submission'
            elif res.state == 'bid_selection':
                res.state2 = 'bid_selection'
                res.set_not_editable()
            elif res.state == 'closed':
                res.state2 = 'closed'
            elif res.state == 'cancel':
                res.state2 = 'cancel'
            elif res.state == 'reject':
                res.state4 = 'reject'
    def set_not_editable(self):
        for res in self:
            purchase = self.env['purchase.order'].sudo().search([('agreement_id', '=', res.id), ('selected_order', '=', False)])
            for rec in purchase:
                rec.not_editable = True

    def action_validate(self):
        for res in self:
            po_ids = self.env['purchase.order'].search([('agreement_id', '=', res.id)])
            for po_id in po_ids:
                po_id.write({'not_editable': True, 'is_editable': True})
            if not res.rfq_count:
                raise ValidationError(_("There is no quotation document."))
            else:
                res.state = 'bid_selection'

    def _compute_order_count(self):
        res = super(ShPurchaseAgreement, self)._compute_order_count()
        purchase_orders = self.env['purchase.order'].sudo().search(
            [('agreement_id', '=', self.id), ('state', 'in', ['purchase'])])
        if purchase_orders:
            self.order_count = len(purchase_orders.ids)
        else:
            self.order_count = 0
        return res

    def action_view_order(self):
        return {
            'name': _('Selected Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('agreement_id', '=', self.id), ('state', 'in', ['purchase'])],
            'target': 'current'
        }

class ShPurchaseAgreementLine(models.Model):
    _inherit = 'purchase.agreement.line'

    @api.model
    def default_get(self, fields):
        res = super(ShPurchaseAgreementLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'sh_purchase_agreement_line_ids' in context_keys:
                if len(self._context.get('sh_purchase_agreement_line_ids')) > 0:
                    next_sequence = len(self._context.get('sh_purchase_agreement_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )

    analytic_accounting = fields.Boolean("Analyic Account", related="agreement_id.analytic_accounting")
    sh_product_description = fields.Text('Description')
    sh_product_uom_id = fields.Many2one('uom.uom', string='UoM', domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='sh_product_id.uom_id.category_id')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_tender_rel', 'tender_id', 'tag_id', string="Analytic Group")
    date_order = fields.Date(related='agreement_id.sh_order_date', string='Order Date', readonly=True)
    dest_warehouse_id = fields.Many2one('stock.warehouse', string="Destination", required=True, domain="[('company_id', '=', company_id),('branch_id','=',branch_id)]")
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type', compute='compute_picking_type')
    set_single_delivery_date = fields.Boolean(related='agreement_id.set_single_delivery_date')
    set_single_delivery_destination = fields.Boolean(related='agreement_id.set_single_delivery_destination')
    request_line_id = fields.Many2one('purchase.request.line', string='Purchase Request Line')
    branch_id = fields.Many2one(comodel_name='res.branch', string='Branch', related="agreement_id.branch_id", store=True)
    

    def unlink(self):
        approval = self.agreement_id
        res = super(ShPurchaseAgreementLine, self).unlink()
        approval._reset_sequence2()
        return res

    @api.model
    def create(self, vals):
        res = super(ShPurchaseAgreementLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.agreement_id._reset_sequence2()
        return res

    @api.onchange('sequence')
    def set_analytic(self):
        for res in self:
            if not res.analytic_tag_ids:
                res.analytic_tag_ids = [(6, 0, res.agreement_id.account_tag_ids.ids)]

    @api.onchange("sh_product_id", "agreement_id.schedule_date", "agreement_id.destination_warehouse_id")
    def onchange_product_id(self):
        if self.sh_product_id:
            self.sh_product_uom_id = self.sh_product_id.uom_po_id.id
            self.sh_product_description = self.sh_product_id.display_name
            if self.sh_product_id.description_purchase:
                display_name = self.sh_product_id.display_name
                description_name = self.sh_product_id.description_purchase
                name = display_name + '\n' + description_name
                self.sh_product_description = name
        if self.agreement_id.set_single_delivery_date:
            self.schedule_date = self.agreement_id.sh_delivery_date
        if self.agreement_id.set_single_delivery_destination:
            self.dest_warehouse_id = self.agreement_id.destination_warehouse_id.id
        else:
            stock_warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id),('branch_id', '=', self.env.user.branch_id.id)], order="id", limit=1)
            if stock_warehouse:
                self.dest_warehouse_id = stock_warehouse

    @api.constrains('sh_price_unit')
    def _check_sh_price_unit(self):
        for line in self:
            if line.sh_price_unit < 0:
                raise ValidationError('Please input a valid amount for unit Price!')

    @api.depends('dest_warehouse_id')
    def compute_picking_type(self):
        for res in self:
            if res.dest_warehouse_id:
                picking_type = self.env['stock.picking.type'].search([('warehouse_id', '=', res.dest_warehouse_id.id), ('code', '=', 'incoming')], limit=1)
                if picking_type:
                    res.picking_type_id = picking_type
                else:
                    raise ValidationError("Picking type for destination location does not exist.")
            else:
                res.picking_type_id = False

class PurchaseAgreementApprovalMatrixLine(models.Model):
    _name = "purchase.agreement.approval.matrix.lines"
    _description = "Purchase Agreement Approval Matrix Line"

    @api.model
    def default_get(self, fields):
        res = super(PurchaseAgreementApprovalMatrixLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", domain="[('id', '!=', user_ids_domain)]", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    status = fields.Char("Approval Status")
    time = fields.Datetime("Time Stamp")
    feedback = fields.Text("Feedback")
    approved = fields.Boolean("Approved")
    approval = fields.Integer("Approval")
    user_approved_ids = fields.Many2many('res.users', string="User Approved", relation='supplier_approval_tender_rel')
    approval_matrix = fields.Many2one('purchase.agreement', string="Approval Matrix")
    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    user_ids_domain = fields.Many2many('res.users', string="User", compute="_compute_user_domain")
    last_approved = fields.Many2one('res.users', string='Users')


    @api.depends('user_ids')
    def _compute_user_domain(self):
        for rec in self:
            lines = []
            for line in rec.approval_matrix.approval_matrix_line_ids:
                lines.extend(line.user_ids.ids)
            rec.user_ids_domain = self.env['res.users'].browse(lines)

    def unlink(self):
        approval = self.approval_matrix
        res = super(PurchaseAgreementApprovalMatrixLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(PurchaseAgreementApprovalMatrixLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix._reset_sequence()
        return res

class CanselTender(models.TransientModel):
    _name = 'cancel.tender.memory'
    _description = "Cancel Tender"

    tender_id = fields.Many2one('purchase.agreement', 'Source', required=True)
    reason = fields.Text("Reason", required=True)

    def action_cancel_tender(self):
        """
        Reject the specified Tender.
        :return:
        """
        self.tender_id.action_rejected(self.reason)
