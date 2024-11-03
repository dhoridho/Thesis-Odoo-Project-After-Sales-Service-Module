from odoo import api, fields, models, SUPERUSER_ID, tools, _
from odoo.exceptions import ValidationError, UserError, Warning

class PurchaseDownPayment(models.TransientModel):
    _inherit = 'purchase.down.payment'

    is_services_orders = fields.Boolean(string="Services Orders", default=False)
    is_service_work_order = fields.Boolean(string='Is Service Work Order', compute="_compute_is_service_work_order")
    
    swo_ids = fields.Many2many('service.work.order', string="Service Work Order")
    payable_progress = fields.Float("Payable Progress")

    @api.depends('purchase_id')
    def _compute_is_service_work_order(self):
        for i in self:
            i.is_service_work_order = bool(self.env['ir.config_parameter'].sudo().get_param('is_service_work_order'))
            # i.is_service_work_order = self.env.company.is_service_work_order

    @api.onchange('swo_ids')
    def set_payable(self):
        for rec in self:
            val = 0
            if rec.swo_ids:
                for swo in rec.swo_ids:
                    val += swo.contract_term
            else:
                val = 0
            rec.payable_progress = val

    @api.model
    def default_get(self, fields):
        res = super(PurchaseDownPayment, self).default_get(fields)
        context = dict(self.env.context) or {}
        if context.get('active_model') == "vendor.payment.request.line":
            pl_id = self.env['vendor.payment.request.line'].browse(context.get('active_ids'))
            purchase_id = self.env['purchase.order'].search([('id', '=', pl_id.purchase_order_id.id)])
            res['purchase_id'] = purchase_id.id
            order_line = purchase_id.order_line
            if all(line.product_id.purchase_method == 'purchase' for line in order_line) and \
                    not purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            elif purchase_id.invoice_ids and purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_billable'] = True
                res['down_payment_by_billable'] = 'deduct_down_payment'
            elif any(line.product_id.purchase_method == 'receive' and line.qty_received>0 for line in order_line):
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            else:
                res['is_down_payment_by_received'] = True
                res['down_payment_by_received'] = 'fixed'
        if context.get('active_model') == "purchase.order":
            purchase_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
            progress_paid = 0
            order_line = purchase_id.order_line
            if 'is_down_payment_by_ordered' in res:
                res['is_down_payment_by_ordered'] = False
            if 'is_down_payment_by_billable' in res:
                res['is_down_payment_by_billable'] = False
            if 'is_down_payment_by_received' in res:
                res['is_down_payment_by_received'] = False
            if 'down_payment_by_received' in res:
                res['down_payment_by_received'] = False
            if 'down_payment_by_ordered' in res:
                res['down_payment_by_ordered'] = False
            if 'down_payment_by_billable' in res:
                res['down_payment_by_billable'] = False

            if all(line.product_id.purchase_method == 'purchase' for line in order_line) and \
                not purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            elif all(line.product_id.purchase_method == 'receive' for line in order_line) and purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_billable'] = True
                res['down_payment_by_billable'] = 'deduct_down_payment'
            elif all(line.product_id.purchase_method == 'receive' and line.qty_received > 0 for line in order_line) and not purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            elif all(line.product_id.purchase_method == 'receive' for line in order_line):
                res['is_down_payment_by_received'] = True
                res['down_payment_by_received'] = 'fixed'
            elif purchase_id.invoice_ids and purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment):
                res['is_down_payment_by_billable'] = True
                res['down_payment_by_billable'] = 'deduct_down_payment'
            elif len(order_line.mapped('product_id.purchase_method')) > 1 and purchase_id.invoice_ids and purchase_id.invoice_ids.filtered(lambda r: not r.is_down_payment):
                res['is_down_payment_by_billable'] = True
                res['down_payment_by_billable'] = 'deduct_down_payment'
            elif len(order_line.mapped('product_id.purchase_method')) > 1:
                res['is_down_payment_by_ordered'] = True
                res['down_payment_by_ordered'] = 'fixed'
            else:
                res['is_down_payment_by_received'] = True
                res['down_payment_by_received'] = 'fixed'
            for line in purchase_id.milestone_purchase_ids:
                progress_paid += line.progress_paid
            res['purchase_id'] = purchase_id.id
            res['is_services_orders'] = purchase_id.is_services_orders
        return res

    def check_dp(self):
        order_id = self.purchase_id
        if self.down_payment_by == 'percentage':
            if self.amount + order_id.down_payment_amount_percentage >= 100:
                raise ValidationError("Down payment percentage cannot be greater than 100%")
        elif self.down_payment_by == 'fixed':
            if self.amount + order_id.down_payment_amount >= order_id.amount_total:
                raise ValidationError("Down payment amount cannot be greater than Total Amount")

    def create_bill2(self):
        if self.down_payment_by in ['fixed', 'percentage']:
            self.check_dp()
        self.purchase_id.down_payment_by = self.down_payment_by
        self.purchase_id.amount = self.amount
        context = dict(self.env.context) or {}
        payment = 0
        if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
            if self.amount <= 0:
                raise ValidationError(_('''Amount must be positive'''))
            if self.purchase_id.down_payment_by == 'percentage':
                payment = self.purchase_id.amount_total * self.purchase_id.amount / 100
            else:
                payment = self.amount

            if self.purchase_id.total_invoices_amount == 0:
                if payment > self.purchase_id.amount_total:
                    raise ValidationError(_('''You are trying to pay: %s, but\n You can not pay more than: %s''') % (payment, self.purchase_id.amount_total))
            # if self.purchase_id.total_invoices_amount == self.purchase_id.amount_total:
            #     raise ValidationError(_('''Bills worth %s already created for this purchase order, check attached bills''') % (self.purchase_id.amount_total))
            if self.purchase_id.total_invoices_amount > 0:
                remaining_amount = self.purchase_id.amount_total - self.purchase_id.total_invoices_amount
                if payment > remaining_amount:
                    raise ValidationError(_('''You are trying to pay: %s, but\n You have already paid: %s for purchase order worth: %s''') % (payment, self.purchase_id.total_invoices_amount, self.purchase_id.amount_total))
            if payment > self.purchase_id.amount_total:
                raise ValidationError(_('''You are trying to pay: %s, but\n You can not pay more than: %s''') % (payment, self.purchase_id.amount_total))

        product = self.purchase_id.company_id.down_payment_product_id
        journal_id = self.env['account.journal'].search([('type', '=', 'purchase'), ('company_id', '=', self.purchase_id.company_id.id)], limit=1)
        if journal_id:
            self.purchase_id.dp_journal_id = journal_id.id
        else:
            raise ValidationError(_('''Please configure at least one Purchase Journal for %s Company''') % (self.purchase_id.company_id.name))

        if not product:
            raise ValidationError(_('''Please configure Advance Payment Product into : Purchase > Settings'''))

        total_swo = 0
        swo = False
        if self.swo_ids:
            swo = True
            for swo in self.swo_ids:
                swo.invoiced = True
                total_swo += swo.contract_term
        total_swo = total_swo / 100 * self.purchase_id.total_down_payment_amount
        total_swo = total_swo * 100 / self.purchase_id.amount_total
        self.purchase_id.paid_swo += total_swo
        amount_swo = self.purchase_id.total_down_payment_amount * (100 - total_swo) / 100
        if self.down_payment_by != 'dont_deduct_down_payment':
            context.update({
                'down_payment': True,
                'down_payment_by': self.down_payment_by,
                'amount': self.amount,
                'swo': swo,
                'total_swo': total_swo,
                'amount_total': amount_swo,
                'swo_ids': self.swo_ids
            })
            if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
                context.update({
                    'dp_amount': payment
                })
        else:
            context.update({
                'down_payment_by': self.down_payment_by,
                'amount': self.amount,
                'swo': swo,
                'total_swo': total_swo,
                'amount_total': amount_swo,
                'swo_ids': self.swo_ids
            })
            if self.purchase_id.down_payment_by in ['fixed', 'percentage']:
                context.update({
                    'dp_amount': payment
                })
        invoice_ids = self.purchase_id.invoice_ids.filtered(lambda r: r.is_down_payment)
        purchase_line_ids = self.purchase_id.order_line.filtered(lambda r: r.product_id.purchase_method == 'receive' and not r.qty_received and not r.is_down_payment)
        if invoice_ids and purchase_line_ids:
            raise ValidationError('There are no invoiceable line, please receive the product!')
        if self.down_payment_by == 'deduct_down_payment':
            invoice_ids = self.purchase_id.invoice_ids
            purchase_line_ids = self.purchase_id.order_line.filtered(lambda r: r.product_id.purchase_method == 'receive' and not r.qty_received and not r.is_down_payment)
            if invoice_ids and purchase_line_ids:
                raise ValidationError('There are no invoiceable line, please receive the product!')

        return self.purchase_id.with_context(context).action_create_invoice()

