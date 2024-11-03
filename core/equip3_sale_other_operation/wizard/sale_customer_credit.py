
from odoo import api , models, fields
from datetime import datetime, date
class SaleOrderPartnredit(models.TransientModel):
    _inherit = 'sale.order.partner.credit'

    invoice_number = fields.Char(string="Invioce Overdue", readonly=True)
    customer_max_invoice_overdue = fields.Float(string="Customer Max Invoice Overdue Days", readonly=True)
    is_set_customer_on_hold = fields.Boolean(string="Set Customer On Hold (Invoice overdue)", readonly=True)
    avl_open_inv_limt = fields.Float(string="Available Open Invoices Quota", readonly=True)
    customer_on_hold_open_invoice = fields.Boolean(string="Customer On Hold If Number Open Invoice Exceed")
    cust_credit_limit = fields.Float('Customer Credit Limit')
    is_credit_limit = fields.Boolean('Is Credit Limit', related='name.is_credit_limit')

    @api.model
    def default_get(self, fields):
        res = super(SaleOrderPartnredit, self).default_get(fields)
        context = dict(self.env.context) or {}
        res.update({
            'customer_max_invoice_overdue': context.get('customer_max_invoice_overdue'),
            'is_set_customer_on_hold': context.get('is_set_customer_on_hold'),
            'invoice_number': context.get('invoice_number'),
            'avl_open_inv_limt': context.get('avl_open_inv_limt'),
            'customer_on_hold_open_invoice': context.get('customer_on_hold_open_invoice'),
        })
        if self._context.get('active_id', False) and self._context.get('active_model', False) == 'sale.order':
            sale_obj = self.env['sale.order'].search(
                [('id', '=', self._context.get('active_id'))], limit=1)
            if sale_obj:
                so_pend = ''
                inv_pend = ''
                ord_cnt = 0
                ord_amt = 0
                inv_cnt = 0
                inv_amt = 0
                so_pend_obj = self.env['sale.order'].search(
                    [('state', 'not in', ['done', 'cancel']), ('partner_id', '=', sale_obj.partner_id.id)])
                inv_pend_obj = self.env['account.move'].search([('move_type','=','out_invoice'),
                    ('payment_state','!=','paid'),('state','not in',['cancel']),('partner_id','=',sale_obj.partner_id.id )])
                for rec in so_pend_obj:
                    ord_cnt += 1
                    ord_amt += rec.amount_total
                if ord_cnt > 0:
                    so_pend = str(ord_cnt) + \
                        ' Sales Order(s) (Amt) : ' + '{:,}'.format(round(ord_amt, 2))
                    res.update({'sale_orders_cnt_amt': so_pend})
                for rec in inv_pend_obj:
                    inv_cnt += 1
                    inv_amt += rec.amount_total
                if inv_cnt > 0:
                    inv_pend = str(inv_cnt) + \
                        ' Invoice(s) (Amt) : ' + '{:,}'.format(round(inv_amt, 2))
                    res.update({'cust_invoice_cnt_amt': inv_pend})
                if not sale_obj.partner_id.set_customer_credit_limit_per_brand:
                    res.update({
                        'customer_credit_limit': sale_obj.partner_id.customer_credit_limit
                    })
                else:
                    if sale_obj.brand and sale_obj.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == sale_obj.brand.id):
                        res.update({
                            'customer_credit_limit': sum(sale_obj.partner_id.product_brand_ids.filtered(lambda r: r.brand_id.id == sale_obj.brand.id).mapped('customer_avail_credit_limit'))
                        })
                    else:
                        res.update({
                            'customer_credit_limit': 0.0
                        })
                res.update({
                    'cust_credit_limit': sale_obj.partner_id.cust_credit_limit
                })
        return res

    def confirm_sale_order(self):
        if self and self.name and self.order_partner:
            partner_obj = self.env['res.partner'].search(
                [('id', '=', self.order_partner.id)], limit=1)
            partner_obj.write(
                {'set_customer_onhold': self.set_customer_onhold})
            sale_obj = self.env['sale.order'].search(
                [('id', '=', self.name.id)])
            sale_obj.write({'partner_credit_conform': True})
            sale_obj.with_context({'sale_confirm': True}).action_confirm()

    def ok_credit_and_invoice_limit(self):
        context = dict(self.env.context) or {}
        context.update({'double_overlimit_check': True, 'not_send_mail': True})
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        over_credit_limit_sequence = IrConfigParam.get_param('over_credit_limit_sequence', 0)
        invoice_overdue_sequence = IrConfigParam.get_param('invoice_overdue_sequence', 0)
        is_send_mail = False
        if int(over_credit_limit_sequence) < int(invoice_overdue_sequence):
            is_send_mail = True     
            self.with_context(context).ok_sale_customer_credit()
            self.with_context(context).ok_invoice_overdue()
        else:
            is_send_mail = True
            self.with_context(context).ok_invoice_overdue()
            self.with_context(context).ok_sale_customer_credit()
        if not self.name.approving_matrix_limit_id and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not self.name.approving_matrix_limit_id:
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            self.name.action_request_for_approval_limit()
        if is_send_mail:
            self.name.action_request_approval_overlimit_mail()

    def ok_invoice_overdue(self):
        context = dict(self.env.context) or {}
        default_max_days = self.name.partner_id.customer_max_invoice_overdue
        invoices = self.env['account.move'].search([('partner_id', '=', self.name.partner_id.id), ('state', '=', 'posted'),('payment_state','in',('not_paid','in_payment','partial')),('move_type', '=', 'out_invoice'),
            ('invoice_date_due', '<', datetime.now().date())])
        inv = []
        if invoices:
            today_date = datetime.now().date()
            for invoice in invoices:
                deviation = today_date - invoice.invoice_date_due
                if deviation.days > default_max_days:
                    inv.append(deviation.days)
        total_days = sum(inv)
        matrix_limit_id = self.env['limit.approval.matrix'].search([('minimum_amt', '<=', total_days), ('maximum_amt', '>=', total_days),
            ('config', '=', 'max_invoice_overdue_days'), ('branch_id','=',self.name.branch_id.id), ('company_id', '=', self.name.company_id.id)], limit=1)
        is_send_mail = False
        if matrix_limit_id:
            is_send_mail = True
            self.name.approving_matrix_limit_id = [(4, matrix_limit_id.id)]
            self.name.write({'state': 'waiting_for_over_limit_approval'})
        elif not context.get('double_overlimit_check') and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not context.get('double_overlimit_check'):
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            self.name.action_request_for_approval_limit()
        if is_send_mail and not context.get('not_send_mail'):
            self.name.action_request_approval_overlimit_mail()

    def ok_sale_customer_over(self):
        context = dict(self.env.context) or {}
        over_limit = abs(self.current_order - self.cust_credit_limit)
        matrix_limit_id = self.env['limit.approval.matrix'].search([('minimum_amt', '<=', over_limit), ('maximum_amt', '>=', over_limit),
                                                                    ('config', '=', 'over_limit'), ('branch_id','=',self.name.branch_id.id), ('company_id', '=', self.name.company_id.id)], limit=1)
        is_send_mail = False
        if matrix_limit_id:
            is_send_mail = True
            self.name.approving_matrix_limit_id = [(4, matrix_limit_id.id)]
            self.name.write({'state': 'waiting_for_over_limit_approval'})
            if not self.name.is_over_limit_validation:
                self.name.write({'state': 'over_limit_approved','partner_credit_conform': True})
                self.name.action_request_for_approval_limit()
        elif not context.get('double_overlimit_check') and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            # self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not context.get('double_overlimit_check'):
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            if not self.name.is_credit_limit:
                self.name.write({'partner_credit_conform': True})
                self.name.action_request_for_approval_limit()
        if is_send_mail and not context.get('not_send_mail'):
            self.name.action_request_approval_overlimit_mail()
        # self.name.is_over_limit = False

    def ok_sale_customer_credit(self):
        context = dict(self.env.context) or {}
        available_credit_limit = abs(self.customer_credit_limit - self.current_order)
        matrix_limit_id = self.env['limit.approval.matrix'].search([('minimum_amt', '<=', available_credit_limit), ('maximum_amt', '>=', available_credit_limit),
            ('config', '=', 'credit_limit'), ('branch_id','=',self.name.branch_id.id), ('company_id', '=', self.name.company_id.id)], limit=1)
        is_send_mail = False
        if matrix_limit_id:
            is_send_mail = True
            self.name.approving_matrix_limit_id = [(4, matrix_limit_id.id)]
            self.name.write({'state': 'waiting_for_over_limit_approval'})
            if not self.name.is_over_limit_validation:
                self.name.write({'state': 'over_limit_approved','partner_credit_conform': True})
                self.name.action_request_for_approval_limit()
        elif not context.get('double_overlimit_check') and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            # self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not context.get('double_overlimit_check'):
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved','partner_credit_conform': True})
            self.name.action_request_for_approval_limit()
        if is_send_mail and not context.get('not_send_mail'):
            self.name.action_request_approval_overlimit_mail()
        self.name.is_credit_limit = False

    def ok_invoice_open(self):
        context = dict(self.env.context) or {}
        available_open_invoice_limit = abs(self.avl_open_inv_limt - 1)
        matrix_limit_id = self.env['limit.approval.matrix'].search([('minimum_amt', '<=', available_open_invoice_limit), ('maximum_amt', '>=', available_open_invoice_limit),
            ('config', '=', 'open_invoice_limit'), ('branch_id','=',self.name.branch_id.id), ('company_id', '=', self.name.company_id.id)], limit=1)
        is_send_mail = False
        if matrix_limit_id:
            is_send_mail = True
            self.name.approving_matrix_limit_id = [(4, matrix_limit_id.id)]
            self.name.write({'state': 'waiting_for_over_limit_approval'})
        elif not context.get('double_overlimit_check') and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not context.get('double_overlimit_check'):
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            self.name.action_request_for_approval_limit()
        if is_send_mail and not context.get('not_send_mail'):
            self.name.action_request_approval_overlimit_mail()

    def ok_credit_invoice_open_limit(self):
        context = dict(self.env.context) or {}
        context.update({'double_overlimit_check': True, 'not_send_mail': True})
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        open_invoice_limit_sequence = IrConfigParam.get_param('open_invoice_limit_sequence', 0)
        over_credit_limit_sequence = IrConfigParam.get_param('over_credit_limit_sequence', 0)
        is_send_mail = False
        if int(over_credit_limit_sequence) < int(open_invoice_limit_sequence):
            is_send_mail = True
            self.with_context(context).ok_sale_customer_credit()
            self.with_context(context).ok_invoice_open()
        else:
            is_send_mail = True
            self.with_context(context).ok_invoice_open()
            self.with_context(context).ok_sale_customer_credit()
        if not self.name.approving_matrix_limit_id and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not self.name.approving_matrix_limit_id:
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            self.name.action_request_for_approval_limit()
        if is_send_mail:
            self.name.action_request_approval_overlimit_mail()

    def ok_invoice_overdue_open_limit(self):
        context = dict(self.env.context) or {}
        context.update({'double_overlimit_check': True, 'not_send_mail': True})
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        open_invoice_limit_sequence = IrConfigParam.get_param('open_invoice_limit_sequence', 0)
        invoice_overdue_sequence = IrConfigParam.get_param('invoice_overdue_sequence', 0)
        is_send_mail = False
        if int(invoice_overdue_sequence) < int(open_invoice_limit_sequence):
            is_send_mail = True
            self.with_context(context).ok_invoice_overdue()
            self.with_context(context).ok_invoice_open()
        else:
            is_send_mail = True
            self.with_context(context).ok_invoice_open()
            self.with_context(context).ok_invoice_overdue()
        if not self.name.approving_matrix_limit_id and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not self.name.approving_matrix_limit_id:
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            self.name.action_request_for_approval_limit()
        if is_send_mail:
            self.name.action_request_approval_overlimit_mail()

    def ok_credit_overdue_open_limit(self):
        context = dict(self.env.context) or {}
        context.update({'double_overlimit_check': True, 'not_send_mail': True})
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        over_credit_limit_sequence = IrConfigParam.get_param('over_credit_limit_sequence', 0)
        open_invoice_limit_sequence = IrConfigParam.get_param('open_invoice_limit_sequence', 0)
        invoice_overdue_sequence = IrConfigParam.get_param('invoice_overdue_sequence', 0)
        data = [
                {'sequence': over_credit_limit_sequence, 'config': 'over_limit'},
                {'sequence': open_invoice_limit_sequence, 'config': 'open_invoice'},
                {'sequence': invoice_overdue_sequence, 'config': 'invoice_overdue'},
            ]
        sorted_data = sorted(data, key=lambda r:r['sequence'])
        is_send_mail = False
        for line in sorted_data:
            if line.get('config') == 'over_limit':
                is_send_mail = True
                self.with_context(context).ok_sale_customer_credit()
            elif line.get('config') == 'open_invoice':
                is_send_mail = True
                self.with_context(context).ok_invoice_open()
            elif line.get('config') == 'invoice_overdue':
                is_send_mail = True
                self.with_context(context).ok_invoice_overdue()
        if not self.name.approving_matrix_limit_id and not self.name.is_customer_approval_matrix:
            is_send_mail = True
            self.name.order_confirm()
        elif self.name.is_customer_approval_matrix and not self.name.approving_matrix_limit_id:
            is_send_mail = True
            self.name.write({'state': 'over_limit_approved'})
            self.name.action_request_for_approval_limit()
        if is_send_mail:
            self.name.action_request_approval_overlimit_mail()
