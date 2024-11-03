
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, date

class ApprovalMatrixDirectPurchase(models.Model):
    _name = "approval.matrix.direct.purchase"
    _description = "Approval Matrix Direct Purchase"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(string="Name", required=True, tracking=True)
    company_id = fields.Many2one('res.company', string="Company", required=True, tracking=True, readonly=True, default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    minimum_amt = fields.Float(string="Minimum Amount", tracking=True, required=True)
    maximum_amt = fields.Float(string="Maximum Amount", tracking=True, required=True)
    approval_matrix_direct_purchase_line_ids = fields.One2many('approval.matrix.direct.purchase.line', 'approval_matrix_direct_purchase', string='Approving Matrix Direct Purchase')
    order_type = fields.Selection([
                ("goods_order","Goods Order"),
                ("services_order","Services Order")
                ], string='Order Type', default="goods_order")
    is_good_services_order = fields.Boolean(string="Orders", compute="_compute_is_good_services_order")
    
    def _compute_is_good_services_order(self):
        for record in self:
            is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
            # is_good_services_order = self.env.company.is_good_services_order
            record.is_good_services_order = is_good_services_order

    @api.constrains('approval_matrix_direct_purchase_line_ids')
    def _check_validation_minimum_approver(self):
        for record in self:
            for approval_matrix_line in record.approval_matrix_direct_purchase_line_ids:
                approving_matrix_usrs = approval_matrix_line.user_ids
                approving_matrix_min_approver = approval_matrix_line.minimum_approver

                if approving_matrix_min_approver <= 0 or approving_matrix_min_approver > len(approving_matrix_usrs):
                    raise ValidationError("Minimum approver should be greater than 0 and cannot greater than the total approver")

    @api.constrains('branch_id', 'minimum_amt', 'maximum_amt')
    def _check_existing_record(self):
        for record in self:
            if record.is_good_services_order:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id), ('order_type', '=', record.order_type),
                                                  '|', '|',
                                                  '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                  '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                  '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("There are the other approval matrix %s in same Branch, Order Type and minimum / maximum Amount. Please change branch , order type or minimum and maximum amount." % (approval_matrix_id.name))
            else:
                approval_matrix_id = self.search([('branch_id', '=', record.branch_id.id), ('id', '!=', record.id),
                                                  '|', '|',
                                                  '&', ('minimum_amt', '<=', record.minimum_amt), ('maximum_amt', '>=', record.minimum_amt),
                                                  '&', ('minimum_amt', '<=', record.maximum_amt), ('maximum_amt', '>=', record.maximum_amt),
                                                  '&', ('minimum_amt', '>=', record.minimum_amt), ('maximum_amt', '<=', record.maximum_amt)], limit=1)
                if approval_matrix_id:
                    raise ValidationError("The minimum and maximum range of this approval matrix is intersects with other approval matrix %s in same branch. Please change the minimum and maximum range" % (approval_matrix_id.name))

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.approval_matrix_direct_purchase_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    @api.onchange('company_id')
    def onchange_company_id(self):
        self.branch_id = False
        self._compute_is_good_services_order()


class ApprovalMatrixDirectPurchaseLine(models.Model):
    _name = "approval.matrix.direct.purchase.line"
    _description = "Approval Matrix Direct Purchase Line"

    @api.model
    def default_get(self, fields):
        res = super(ApprovalMatrixDirectPurchaseLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'approval_matrix_direct_purchase_line_ids' in context_keys:
                if len(self._context.get('approval_matrix_direct_purchase_line_ids')) > 0:
                    next_sequence = len(self._context.get('approval_matrix_direct_purchase_line_ids')) + 1
            res.update({'sequence': next_sequence})
        return res

    sequence = fields.Integer(string="Sequence")
    user_ids = fields.Many2many('res.users', string="User", required=True)
    minimum_approver = fields.Integer(string="Minimum Approver", default=1, required=True)
    approval_matrix_direct_purchase = fields.Many2one('approval.matrix.direct.purchase', string="Approval Matrix")

    sequence2 = fields.Integer(
        string="No.",
        related="sequence",
        readonly=True,
        store=True
    )
    approved_users = fields.Many2many('res.users', 'approved_users_direct_purchase_patner_rel', 'order_id', 'user_id', string='Users')
    state_char = fields.Text(string='Approval Status')
    time_stamp = fields.Datetime(string='TimeStamp')
    feedback = fields.Char(string='Feedback')
    last_approved = fields.Many2one('res.users', string='Users')
    approved = fields.Boolean('Approved')
    order_id = fields.Many2one('purchase.order', string="Purchase Order")
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")

    def unlink(self):
        approval = self.approval_matrix_direct_purchase
        res = super(ApprovalMatrixDirectPurchaseLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self, vals):
        res = super(ApprovalMatrixDirectPurchaseLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.approval_matrix_direct_purchase._reset_sequence()
        return res

class ApprovalReject(models.TransientModel):
    _inherit = "approval.reject"

    def action_reject(self):
        res = super(ApprovalReject, self).action_reject()
        purchase_id = self.env['purchase.order'].browse(self._context.get('active_ids'))
        is_email_notification_direct_purchase = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_email_notification_direct_purchase')
        is_whatsapp_notification_direct_purchase = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation_cont.is_whatsapp_notification_direct_purchase')
        # is_email_notification_direct_purchase = self.env.company_id.is_email_notification_direct_purchase
        # is_whatsapp_notification_direct_purchase = self.env.company_id.is_whatsapp_notification_direct_purchase
        user = self.env.user
        approving_matrix_line = sorted(purchase_id.approved_matrix_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
        action_id = self.env.ref('equip3_purchase_other_operation_cont.action_direct_purchase')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        url = base_url + '/web#id=' + str(purchase_id.id) + '&action='+ str(action_id.id) + '&view_type=form&model=purchase.order'
        rejected_template_id = self.env.ref('equip3_purchase_other_operation_cont.email_template_direct_purchase_approval_rejected')
        wa_rejected_template_id = self.env.ref('equip3_purchase_other_operation_cont.whatsapp_direct_purchase_rejected')
        if purchase_id and purchase_id.dp:
            user = self.env.user
            approving_matrix_line = sorted(purchase_id.approved_matrix_direct_ids.filtered(lambda r:not r.approved), key=lambda r:r.sequence)
            if approving_matrix_line:
                matrix_line = approving_matrix_line[0]
                name = matrix_line.state_char or ''
                if name != '':
                    name += "\n • %s: Rejected" % (user.name)
                else:
                    name += "• %s: Rejected" % (user.name)
                matrix_line.write({'state_char': name, 'time_stamp': datetime.now(), 'feedback': self.reason, 'approver_state': 'refuse'})
                purchase_id.state = 'reject'
                ctx = {
                'email_from' : self.env.user.company_id.email,
                'email_to' : purchase_id.request_partner_id.email,
                'date': date.today(),
                'url' : url,
            }
            if is_email_notification_direct_purchase:
                rejected_template_id.sudo().with_context(ctx).send_mail(purchase_id.id, True)
            if is_whatsapp_notification_direct_purchase:
                phone_num = str(purchase_id.request_partner_id.mobile) or str(purchase_id.request_partner_id.phone)
                purchase_id._send_whatsapp_message_approval(wa_rejected_template_id, purchase_id.request_partner_id, phone_num, url)
        return res
