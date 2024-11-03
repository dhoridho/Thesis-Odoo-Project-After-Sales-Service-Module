
from odoo import api, fields, models, _, tools
from datetime import timedelta, datetime, date
from odoo.http import request
from odoo.exceptions import UserError


class PurchaseAgreement(models.Model):
    _inherit = 'purchase.agreement'

    @api.model
    def _default_domain(self):
        if self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix'):
        # if self.env.company.is_vendor_approval_matrix:
            return [('state2', '=', 'approved'), ('supplier_rank', '>', 0), ('is_vendor', '=', True), ('branch_id', 'in', self.env.branches.ids),('company_id','=', self.env.company.id)]
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

    purchase_request_id = fields.Many2one('purchase.request', string='Purchase Tender')
    sh_purchase_user_id = fields.Many2one(
        'res.users', 'Purchase Representative', tracking=True, default=lambda self: self.env.user)
    sh_agreement_type = fields.Many2one(
        'purchase.agreement.type', 'Tender Type', required=False, tracking=True)
    partner_ids = fields.Many2many(
        'res.partner', string='Vendors', tracking=True, required=False, domain=_default_domain)
    days_left = fields.Integer("Days Left")
    analytic_accounting = fields.Boolean("Analyic Account", compute="get_analytic_accounting", store=True)
    def _domain_analytic_group(self):
        return [('company_id','=',self.env.company.id)]
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_pt_rel', 'pt_id', 'tag_id', string="Analytic Group", domain=_domain_analytic_group)
    # branch_id = fields.Many2one('res.branch', string="Branch", required=True, tracking=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    destination_warehouse_id = fields.Many2one('stock.warehouse', string="Destination", domain="[('company_id', '=', company_id),('branch_id','=',branch_id)]")
    set_single_delivery_destination = fields.Boolean("Single Delivery Destination")
    set_single_delivery_date = fields.Boolean("Single Delivery Date")
    comparison_ids = fields.One2many('purchase.agreement.comparison', 'agreement_id', string='Vendor Comparison')
    partner_id = fields.Many2one(related='user_id.partner_id')
    tender_scope = fields.Selection(string='Tender Scope', selection=[('invitation_tender', 'Invitation Tender'), ('open_tender', 'Open Tender'),],default='invitation_tender',required=True)
    tender_name = fields.Char(string='Tender Name')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company.id)
    currency_id = fields.Many2one(related='company_id.currency_id', store=True, string='Currency', readonly=True)
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_total')
    is_price_ratting_rfq_tender = fields.Boolean(string='Price Rating RFQ Tender', default=False)
    show_analytic_tags = fields.Boolean("Show Analytic Tags", compute="compute_analytic_tags", store=True)


    @api.onchange('branch_id','company_id')
    def set_warehouse_id(self):
        for res in self:
            stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
            res.destination_warehouse_id = stock_warehouse or False

    @api.depends('company_id')
    def compute_analytic_tags(self):
        for rec in self:
            rec.show_analytic_tags = self.env['ir.config_parameter'].sudo().get_param('group_analytic_tags')
    
    
    @api.depends('sh_purchase_agreement_line_ids.sh_qty','sh_purchase_agreement_line_ids.sh_price_unit')
    def _amount_total(self):
        for order in self:
            amount_total=0
            for line in order.sh_purchase_agreement_line_ids:
                amount_total += line.sh_qty*line.sh_price_unit
            order.update({
                'amount_total': amount_total,
            })

    @api.onchange('destination_warehouse_id')
    def _onchange_destination_warehouse(self):
        for res in self:
            for line in res.sh_purchase_agreement_line_ids:
                if res.set_single_delivery_destination:
                    line.dest_warehouse_id = res.destination_warehouse_id.id
                    
    @api.onchange('set_single_delivery_destination', 'set_single_delivery_date')
    def set_single_date_destination(self):
        for res in self:
            if res.set_single_delivery_destination:
                stock_warehouse = res.env['stock.warehouse'].search([('company_id', '=', res.company_id.id),('branch_id', '=', res.branch_id.id)], order="id", limit=1)
                res.destination_warehouse_id = stock_warehouse
            if res.set_single_delivery_date:
                res.sh_delivery_date = datetime.now().date() + timedelta(days=14)
            for line in res.sh_purchase_agreement_line_ids:
                if res.set_single_delivery_date:
                    line.schedule_date = res.sh_delivery_date

    def action_confirm(self):
        if self:
            for rec in self:
                seq = self.env['ir.sequence'].next_by_code(
                    'purchase.agreement')
                rec.name = seq
                rec.state = 'confirm'
                if not rec.sh_purchase_agreement_line_ids:
                    raise UserError(_("You cannot confirm Purchase Tender '%s' because there is no product line.", rec.name))

                for vals in rec.sh_purchase_agreement_line_ids:
                    if vals.sh_qty <= 0 :
                        raise UserError("You cannot confirm purchase tender without quantity.")

    @api.onchange('account_tag_ids')
    def set_analytic(self):
        for res in self:
            for line in res.sh_purchase_agreement_line_ids:
                line.analytic_tag_ids = res.account_tag_ids

    @api.depends('sh_purchase_user_id')
    def get_analytic_accounting(self):
        for res in self:
            res.analytic_accounting = self.user_has_groups('analytic.group_analytic_accounting')
    
    def action_new_quotation(self):
        res = super(PurchaseAgreement, self).action_new_quotation()
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            res['context'].update({'default_is_goods_orders' : True})
        return res
    
    @api.onchange('company_id')
    def set_expiry_date(self):
        pt_expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_expiry_date')
        pt_goods_order_expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_goods_order_expiry_date')
        pt_service_order_expiry_date = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_service_order_expiry_date')
        # pt_expiry_date = self.env.company.pt_expiry_date
        # pt_goods_order_expiry_date = self.env.company.pt_goods_order_expiry_date
        # pt_service_order_expiry_date = self.env.company.pt_service_order_expiry_date
        context = dict(self.env.context) or {}
        if context.get('goods_order') and pt_goods_order_expiry_date:
            for res in self:
                expiry_date = datetime.now() + timedelta(days=int(pt_goods_order_expiry_date))
                res.write({
                    'sh_agreement_deadline': expiry_date,
                })
        elif context.get('services_good') and pt_service_order_expiry_date:
            for res in self:
                expiry_date = datetime.now() + timedelta(days=int(pt_service_order_expiry_date))
                res.write({
                    'sh_agreement_deadline': expiry_date,
                })
        else:
            for res in self:
                if pt_expiry_date:
                    expiry_date = datetime.now() + timedelta(days=int(pt_expiry_date))
                    res.write({
                        'sh_agreement_deadline': expiry_date,
                    })

    def auto_cancel_pr(self):
        pr = self.env['purchase.agreement'].search([
            ('sh_agreement_deadline','<',datetime.now()),
            '|',
            ('state','in',('draft','waiting_approval','tender_approved')),
            '&',
            ('state','=','confirm'),
            ('state2','=','pending'),
            ])
        pr.write({'state':'cancel'})
                        

    def send_email(self):
        template_before = self.env.ref('equip3_purchase_other_operation.email_template_pt_expiry_reminder')
        template_after = self.env.ref('equip3_purchase_other_operation.email_template_pt_expiry_reminder_after')

        notif = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_expiry_notification')
        expiry = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_expiry_date')
        on_date = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_on_date_notify')
        before_exp = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_enter_before_first_notify') or 3
        after_exp = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.pt_enter_after_first_notify') or 1

        # notif = self.env.company.pt_expiry_notification
        # expiry = self.env.company.pt_expiry_date
        # on_date = self.env.company.pt_on_date_notify
        # before_exp = self.env.company.pt_enter_before_first_notify or 3
        # after_exp = self.env.company.pt_enter_after_first_notify or 1
        pr = self.env['purchase.agreement'].search([
            '|',
            ('state', 'in', ('draft','waiting_approval','tender_approved','bid_submission','bid_selection')),
            '&',
            ('state','=','confirm'),
            ('state2','=','pending'),
            ])

        if notif:
            for res in pr:
                if res.state == 'bid_submission':
                    if res.sh_bid_agreement_deadline:
                        expiry_date = datetime.strftime(res.sh_bid_agreement_deadline, tools.DEFAULT_SERVER_DATE_FORMAT)
                        if expiry_date == datetime.strftime(datetime.now() + timedelta(days=int(before_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # Before Expiry Date
                            res.days_left = int(before_exp)
                            template_before.send_mail(
                                res.id, force_send=True)
                        elif expiry_date == datetime.strftime(datetime.now() - timedelta(days=int(after_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # After Expiry Date
                            template_after.send_mail(
                                res.id, force_send=True)
                        elif on_date:
                            if expiry_date == datetime.strftime(datetime.now(), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # On Date
                                template_after.send_mail(
                                    res.id, force_send=True)
                elif res.state == 'bid_selection':
                    if res.sh_bid_selection_agreement_deadline:
                        expiry_date = datetime.strftime(res.sh_bid_selection_agreement_deadline, tools.DEFAULT_SERVER_DATE_FORMAT)
                        if expiry_date == datetime.strftime(datetime.now() + timedelta(days=int(before_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # Before Expiry Date
                            res.days_left = int(before_exp)
                            template_before.send_mail(
                                res.id, force_send=True)
                        elif expiry_date == datetime.strftime(datetime.now() - timedelta(days=int(after_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # After Expiry Date
                            template_after.send_mail(
                                res.id, force_send=True)
                        elif on_date:
                            if expiry_date == datetime.strftime(datetime.now(), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # On Date
                                template_after.send_mail(
                                    res.id, force_send=True)
                elif res.state in ('draft','waiting_approval','tender_approved') or (res.state == 'confirm' and res.state2 == 'pending'):
                    if res.sh_agreement_deadline:
                        expiry_date = datetime.strftime(res.sh_agreement_deadline, tools.DEFAULT_SERVER_DATE_FORMAT)
                        if expiry_date == datetime.strftime(datetime.now() + timedelta(days=int(before_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # Before Expiry Date
                            res.days_left = int(before_exp)
                            template_before.send_mail(
                                res.id, force_send=True)
                        elif expiry_date == datetime.strftime(datetime.now() - timedelta(days=int(after_exp)), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # After Expiry Date
                            template_after.send_mail(
                                res.id, force_send=True)
                        elif on_date:
                            if expiry_date == datetime.strftime(datetime.now(), tools.DEFAULT_SERVER_DATE_FORMAT):
                            # On Date
                                template_after.send_mail(
                                    res.id, force_send=True)

    def get_full_url(self):
        for res in self:
            base_url = request.env['ir.config_parameter'].get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (res.id, res._name)
            return base_url

    @api.onchange('partner_ids')
    def set_comparison(self):
        for res in self:
            res.comparison_ids = [(6, 0, [])]
            for vendor in res.partner_ids:
                self.env['purchase.agreement.comparison'].create({
                    'partner_id': vendor.id.origin,
                    'agreement_id': res.id
                })

    @api.model
    def default_get(self, fields):
        res = super(PurchaseAgreement, self).default_get(fields)
        analytic_priority_ids = self.env['analytic.priority'].search([], order="priority")
        for analytic_priority in analytic_priority_ids:
            if analytic_priority.object_id == 'user' and self.env.user.analytic_tag_ids:
                res.update({
                    'account_tag_ids': [(6, 0, self.env.user.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
            elif analytic_priority.object_id == 'branch' and self.env.user.branch_id.analytic_tag_ids:
                res.update({
                    'account_tag_ids': [(6, 0, self.env.user.branch_id.analytic_tag_ids.filtered(lambda a:a.company_id and a.company_id.id == self.env.company.id).ids)]
                })
                break
        return res

    def print_purchase_tender(self):
        context = dict(self.env.context) or {}
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print RFQ Comparison',
            'view_mode': 'form',
            'res_model': 'print.purchase.tender.report',
            'domain' : [],
            'context': context,
            'target': 'new'
        }

    def _get_vendors(self):
        purchase_order_lines = self.env['purchase.order.line'].search([('agreement_id', '=', self.id), ('state', 'not in', ['cancel']), ('order_id.selected_order', '=', False)])
        vendor_ids = purchase_order_lines.mapped('partner_id')
        counter = 0
        vendors_data = []
        temp_vendor = []
        for vendor in vendor_ids:
            counter += 1
            temp_vendor.append(vendor)
            if counter == 5:
                counter = 0
                vendors_data.append(temp_vendor)
                temp_vendor = []
        if temp_vendor:
            vendors_data.append(temp_vendor)
        return vendors_data

    def _get_vendors_name(self):
        purchase_order_lines = self.env['purchase.order.line'].search([('agreement_id', '=', self.id), ('state', 'not in', ['cancel']), ('order_id.selected_order', '=', False)])
        vendor_ids = purchase_order_lines.mapped('partner_id')
        return ', '.join(vendor_ids.mapped('name'))

    def _get_purchase_vendor_lines(self, vendors):
        vendor_ids = [vendor_id.id for vendor_id in vendors]
        purchase_order_lines = self.env['purchase.order.line'].search([('agreement_id', '=', self.id), ('state', 'not in', ['cancel']), ('order_id.selected_order', '=', False), ('partner_id', 'in', vendor_ids)])
        temp_data = []
        final_line = []
        for line in purchase_order_lines:
            if {'product_id': line.product_id.id} in temp_data:
                filter_product_line = list(filter(lambda r:r.get('product_id') == line.product_id.id, final_line))
                if filter_product_line:
                    final_vendor_line = list(filter(lambda r:r.get('vendor_id') == line.partner_id.id, filter_product_line[0]['vendor_lines']))
                    if final_vendor_line:
                        final_vendor_line[0]['quantity'] += line.product_qty
                        final_vendor_line[0]['unit_price'] += line.price_unit
                    else:
                        filter_product_line[0]['vendor_lines'].append({
                            'vendor_id': line.partner_id.id,
                            'vendor_name': line.partner_id.name,
                            'quantity': line.product_qty,
                            'unit_price': line.price_unit, 
                        })
            else:
                temp_data.append({'product_id': line.product_id.id})
                final_line.append({
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'vendor_lines': [{
                        'vendor_id': line.partner_id.id,
                        'vendor_name': line.partner_id.name,
                        'quantity': line.product_qty,
                        'unit_price': line.price_unit,
                    }]
                    })
        return final_line

    def action_open_purchase_tender(self):
        self.write({'state2': 'bid_submission'})

class PurchaseAgreementComparison(models.Model):
    _name = 'purchase.agreement.comparison'
    _description = "Purchase Agreement Comparison"


    point = [
        ('0', 'Not Use'),
        ('1', 'Poor'),
        ('2', 'Fair'),
        ('3', 'Satisfied'),
        ('4', 'Good'),
        ('5', 'Excellent')
    ]

    agreement_id = fields.Many2one('purchase.agreement', string="Tender")
    partner_id = fields.Many2one('res.partner', string='Vendor')
    on_time_rate = fields.Float(string='Delivery on Schedule (%)', compute='_get_fulfillment', store=True)
    fulfillment = fields.Float(string="Fulfillment (%)", compute='_get_fulfillment', store=True)
    final_point = fields.Float(readonly=True, store=True, string="Final Point")
    final_star = fields.Selection(point, string="Vendor Rate", readonly=True)

    @api.depends('partner_id')
    def _get_fulfillment(self):
        for rec in self:
            rec.on_time_rate = 0
            rec.fulfillment = 0
            rec.final_point = 0
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            vendor_eval = self.env['vendor.evaluation'].search([
                        ('vendor', '=', rec.partner_id.id),
                        ('period_start', '>=', start_date),
                        ('period_end', '<=', end_date),
                        ('state', '=', 'approved')
                    ])
            if len(vendor_eval) > 0:
                total_fullfillment = sum(vendor_eval.mapped('fulfillment')) / len(vendor_eval)
                total_on_time_rate = sum(vendor_eval.mapped('on_time_rate')) / len(vendor_eval)
                total_final_point = sum(vendor_eval.mapped('final_point')) / len(vendor_eval)
                rec.fulfillment = total_fullfillment if total_fullfillment > 0 else 0
                rec.on_time_rate = total_on_time_rate if total_on_time_rate > 0 else 0
                rec.final_point = total_final_point if total_final_point > 0 else 0
                rec.final_star = str(round(rec.final_point))
