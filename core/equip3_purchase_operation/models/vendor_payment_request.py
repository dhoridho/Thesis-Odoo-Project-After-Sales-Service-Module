
from odoo import api, fields, models, _


class VendorPaymentRequest(models.Model):
    _name = 'vendor.payment.request'
    _description = 'Vendor Payment Request'
    _order = 'name desc, id desc'

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
        readonly=False)
    name = fields.Char(string='Reference', readonly=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    description = fields.Char(string="Description")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
    # branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    component_line_id = fields.One2many('vendor.payment.request.line', 'payment_request_id', string='Component Line')
    state = fields.Selection(string='State', selection=[('draft', 'Draft'), ('in_progress', 'In Progress'),('done','Done'), ('cancel', 'Cancelled')], default="draft")
    amount_total = fields.Float(string='Amount Total', compute='_compute_amount_total', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency', related='company_id.currency_id', store=True)

    @api.depends('component_line_id', 'component_line_id.amount_total')
    def _compute_amount_total(self):
        for record in self:
            record.amount_total = sum(record.component_line_id.mapped('payable_amount'))

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('vendor.payment.id.sequence')
        return super(VendorPaymentRequest, self).create(vals)

    def button_confirm(self):
        for record in self:
            record.write({'state': 'in_progress'})

    def button_done(self):
        for record in self:
            record.write({'state': 'done'})

    def button_cancel(self):
        for record in self:
            record.write({'state': 'cancel'})

class VendorPaymentRequestLine(models.Model):
    _name = 'vendor.payment.request.line'
    _description = 'Vendor Payment Request Line'

    payment_request_id = fields.Many2one('vendor.payment.request', string="Payment Request")
    sequence = fields.Integer(string="No")
    purchase_order_id = fields.Many2one('purchase.order', string="Order", domain="[('state', '=', 'purchase')]")
    description = fields.Char(string="Description")
    amount_total = fields.Monetary(string="Amount", related='purchase_order_id.amount_total', store=True)
    currency_id = fields.Many2one('res.currency', related="purchase_order_id.currency_id", store=True)
    payable_amount = fields.Float(string='Payable Amount')
    attachment_file = fields.Binary('Attachment File')
    file_name = fields.Char('File Name')

    @api.model
    def default_get(self, fields):
        res = super(VendorPaymentRequestLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'component_line_id' in context_keys:
                if len(self._context.get('component_line_id')) > 0:
                    next_sequence = len(self._context.get('component_line_id')) + 1
            res.update({'sequence': next_sequence})
        return res

    @api.onchange('purchase_order_id')
    def _onchage_payable_amount(self):
        for record in self:
            record.payable_amount = record.purchase_order_id.amount_total

    def view_bill(self):
        return {
            'name': self.purchase_order_id.name+' - Bills',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,kanban,calendar,form',
            'domain': [('move_type', '=', 'in_invoice'), ('invoice_origin', '=', self.purchase_order_id.name)],
            'context': {'default_move_type': 'in_invoice', 'is_ppn_invisible': True, 'def_invisible': False},
            'target': 'current',
        }
