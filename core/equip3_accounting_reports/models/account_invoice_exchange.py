from odoo import api, fields, models, tools, _
from odoo.exceptions import Warning

class AccountInvoiceExchange(models.Model):
    _name = 'account.invoice.exchange'


    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    @api.model
    def _domain_partner_id(self):
        domain = [('company_id','in',[self.env.company.id, False])]
        exchange_type = self._context.get('default_exchange_type') or False
        if exchange_type:
            if exchange_type == 'invoice':
                domain += [('is_customer','=',True)]
            elif exchange_type == 'bill':
                domain += [('is_vendor','=',True)]
        return domain

    branch_id = fields.Many2one(
        'res.branch',
        check_company=True,
        domain=_domain_branch,
        default = _default_branch,
        readonly=False)

    name = fields.Char(string='Name', copy=False, default=lambda self: _('/'), store=True, index=True, tracking=True)
    partner_id = fields.Many2one('res.partner', tracking=True, string='Partner', domain=_domain_partner_id)
    date = fields.Date(string='Date', index=True)
    # receive_date = fields.Date(string='Receive Date', index=True)
    move_ids = fields.Many2many('account.move', string="Invoices")
    filter_move_ids = fields.Many2many('account.move', compute='_compute_filter_move_ids', store=False)
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', 'Company', index=True, store=True, default=lambda self: self.env.company)
    exchange_type = fields.Selection(selection=[
            ('invoice', 'Invoice'),
            ('bill', 'Bill'),
        ], string='Type', required=True, store=True, index=True, tracking=True,
        default="invoice", change_default=True)
    stage = fields.Selection(selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ], string='Stage', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    # exchange_line_ids = fields.One2many('account.invoice.exchange.line', 'exchange_id', string='Exchange Lines')
    reason = fields.Text(string='Reason')


    @api.model
    def create(self, vals):
        if vals.get('exchange_type'):
            if vals['exchange_type'] == 'invoice':
                code = 'invoice.exchange'
            elif vals['exchange_type'] == 'bill':
                code = 'bill.exchange'

            vals['name'] = self.env['ir.sequence'].next_by_code(code) or _('/')

        result = super(AccountInvoiceExchange, self).create(vals)

        for move in result.move_ids:
            move.exchange_id = result.id

        return result


    def write(self, values):
        for move in self.move_ids:
            move.exchange_id = False

        result = super(AccountInvoiceExchange, self).write(values)

        for move in self.move_ids:
            move.exchange_id = self.id

        return result


    @api.depends('exchange_type','partner_id')
    def _compute_filter_move_ids(self):
        for record in self:
            domain = []
            if record.exchange_type == 'invoice':
                domain = [('move_type', '=', 'out_invoice'),('partner_id', '=', record.partner_id.id),('state', '=', 'posted'),('payment_state','=','not_paid'),('exchange_id','=',False)]
            elif record.exchange_type == "bill":
                domain = [('move_type', '=', 'in_invoice'),('partner_id', '=', record.partner_id.id),('state', '=', 'posted'),('payment_state','=','not_paid'),('exchange_id','=',False)]

            move_ids_obj = self.env['account.move'].search(domain)
            record.filter_move_ids = [(6, 0, move_ids_obj.ids)]


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


    def action_confirm(self):
        for rec in self:
            rec.stage = "confirm"


    def action_approve(self):
        for rec in self:
            if not rec.date:
                raise Warning(_('Warning: Date must be filled in. Please make sure to provide the correct date in the designated field before proceeding.'))
            else:
                rec.stage = "approved"


    def action_reject(self):
        for rec in self:
            rec.stage = "rejected"


    def action_wizard_reject(self):
        for rec in self:
            if not rec.date:
                raise Warning(_('Warning: Date must be filled in. Please make sure to provide the correct date in the designated field before proceeding.'))
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.invoice.exchange.approval.wizard',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'name': "Confirmation Message",
                    'context': {'is_approve': False},
                    'target': 'new',
                }


# class AccountInvoiceExchangeLine(models.Model):
#     _name = "account.invoice.exchange.line"

#     exchange_id = fields.Many2one('account.invoice.exchange', string='Invoice Exchange')
#     move_id = fields.Many2one('account.move', string="Invoice/Bill Number")
#     filter_move_ids = fields.Many2many('account.move', compute='_compute_filter_move_ids', store=False)
#     invoice_date = fields.Date(string='Invoice/Bill Date', related='move_id.invoice_date')
#     invoice_date_due = fields.Date(string='Due Date', related='move_id.invoice_date_due')
#     period_id = fields.Many2one('sh.account.period', string="Period", related='move_id.period_id')
#     fiscal_year = fields.Many2one('sh.fiscal.year', string="Fiscal Year", related='move_id.fiscal_year')
#     l10n_id_tax_number = fields.Char(string="Tax Number", related='move_id.l10n_id_tax_number')
#     amount_untaxed = fields.Float(string='Subtotal', related='move_id.amount_untaxed')
#     currency_id = fields.Many2one('res.currency', string='Currency', related='move_id.currency_id')
#     amount_total = fields.Monetary(string='Grand Total', related='move_id.amount_total', currency_field='currency_id')


#     @api.depends('exchange_id.exchange_type','exchange_id.partner_id')
#     def _compute_filter_move_ids(self):
#         for record in self:
#             domain = []
#             if record.exchange_id.exchange_type == 'invoice':
#                 domain = [('move_type', '=', 'out_invoice'),('partner_id', '=', record.exchange_id.partner_id.id)]
#             elif record.exchange_id.exchange_type == "bill":
#                 domain = [('move_type', '=', 'in_invoice'),('partner_id', '=', record.exchange_id.partner_id.id)]

#             AccountMove = self.env['account.move'].search(domain)
#             record.filter_move_ids = [(6, 0, AccountMove.ids)]