from typing import Collection
from odoo import models, fields, api, exceptions, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError


class TargetCommision(models.Model):
    _name = 'sh.target.commision'

    name = fields.Char(readonly=True)
    user_id = fields.Many2one('res.users', string="User", required=True)
    type = fields.Selection([
        ('product', 'Product'),
        ('category', 'Category')
    ], string="Type", default='product')

    product_ids = fields.Many2many('product.product', string="Products")
    category_ids = fields.Many2many('product.category', string="Category")

    commision_calculator = fields.Selection([
        ('amount', 'Amount'),
        ('percentage', 'Percentage'),
    ], string="Commision Calculator", default='amount', required=True)
    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    target_on = fields.Selection([
        ('amount', 'Amount'),
        ('qty', 'Quantity'),

    ], string="Target On", default="amount", required=True)

    percentage_on = fields.Selection([
        ('sales', 'Sales Amount'),
        ('collection', 'Collection Amount'),
    ])

    commision_detail_line = fields.One2many(
        'sh.commision.detail', 'target_commision_id')

    achieved_sales_target = fields.Float(
        string="Achieved Sales Target", compute="compute_targets")
    achieved_collection_target = fields.Float(
        string="Achieved Collection Target", compute="compute_targets")
    remaining_sales_target = fields.Float(
        string="Remaining Sales Target", compute="compute_targets")
    remaining_collection_target = fields.Float(
        string="Remaining Collection Target", compute="compute_targets")

    sales_target_achieved = fields.Boolean(
        string="Sales Target Achieved", compute="compute_targets",search='search_sales_target_achieved')
    collection_target_achieved = fields.Boolean(
        string="Collection Target Achieved", compute="compute_targets",search='search_collection_target_achieved')
    active = fields.Boolean(default=True)
    bill_count = fields.Integer(compute = "compute_bill_count")
    bill_ids = fields.Many2many('account.move',compute = "compute__bill_ids")
    
    company_id = fields.Many2one('res.company',string = "Company",required=True)

    def search_sales_target_achieved(self,operator, value):
        listt = []
        if value:
            targets = self.search([])
            for target in targets:
                if target.achieved_sales_target >= 100:
                    listt.append(target.id)
            return [('id', 'in', listt)]

    def search_collection_target_achieved(self,operator, value):
        listt = []
        if value:
            targets = self.search([])
            for target in targets:
                if target.achieved_collection_target >= 100:
                    listt.append(target.id)
            return [('id', 'in', listt)]

    @api.model
    def create(self, vals):
        vals.update(
            {'name': self.env['ir.sequence'].next_by_code('commission.seq')})
        res = super(TargetCommision, self).create(vals)
        return res

    @api.constrains('user_id', 'from_date', 'to_date')
    def check_user_id(self):
        if self.search([('id', '!=', self.id), ('user_id', '=', self.user_id.id), ('from_date', '>=', self.from_date), ('to_date',
                                                                                                                        '<=', self.to_date)]):
            raise UserError(
                _('For this user and time period, Target & Commission Already Created'))

    def compute_targets(self):
        sale_orders = self.env['sale.order'].search([
            ('user_id', '=', self.user_id.id),
            ('state', '=', 'sale'),
            ('company_id','=',self.company_id.id)
        ])
        releted_sale_orders = sale_orders.filtered(lambda x: str(x.date_order.date()) >= str(
            self.from_date) and str(x.date_order.date()) <= str(self.to_date))

        product_wise_sales = 0.0
        category_wise_sales = 0.0
        product_wise_collection_amount = 0.0
        product_wise_return_amount = 0.0
        product_wise_net_amount = 0.0
        category_wise_collection_amount = 0.0
        category_wise_return_amount = 0.0
        category_wise_net_amount = 0.0

        if self.target_on == 'amount':

            if self.type == 'product':
                listt = []
                so_ids = []

                for sale_order in releted_sale_orders:
                    for line in sale_order.order_line:
                        if line.product_id.id in self.product_ids.ids:
                            product_wise_sales = product_wise_sales + line.price_total
                            listt.append(sale_order.id)

                for so_id in listt:
                    if so_id not in so_ids:
                        so_ids.append(so_id)
                model_sale_orders = self.env['sale.order'].browse(so_ids)

                for sale_order in model_sale_orders:
                    if sale_order.invoice_ids:
                        for invoice in sale_order.invoice_ids:
                            if invoice.state == 'posted' and invoice.move_type == 'out_invoice':
                                product_wise_collection_amount = product_wise_collection_amount + \
                                    (invoice.amount_total -
                                     invoice.amount_residual)

                            if invoice.state == 'posted' and invoice.move_type == 'out_refund':
                                product_wise_return_amount = product_wise_return_amount + \
                                    (invoice.amount_total -
                                     invoice.amount_residual)
                          
                product_wise_net_amount = product_wise_collection_amount - product_wise_return_amount     

                if self.commision_detail_line and self.commision_detail_line[0].sales_amount:
                    self.achieved_sales_target = (
                        product_wise_sales * 100)/(self.commision_detail_line[0].sales_amount)

                    if self.achieved_sales_target >= 100:
                        self.sales_target_achieved = True
                    else:
                        self.sales_target_achieved = False

                    if self.achieved_sales_target <= 100:
                        self.remaining_sales_target = 100 - self.achieved_sales_target

                    else:
                        self.remaining_sales_target = 0.0

                else:
                    self.sales_target_achieved = False
                    self.achieved_sales_target = 0.0
                    self.remaining_sales_target = 0.0

                if self.commision_detail_line and self.commision_detail_line[0].collection_amount:
                    self.achieved_collection_target = (
                        product_wise_net_amount * 100)/(self.commision_detail_line[0].collection_amount)

                    if self.achieved_collection_target >= 100:
                        self.collection_target_achieved = True

                    else:
                        self.collection_target_achieved = False

                    if self.achieved_collection_target <= 100:
                        self.remaining_collection_target = 100 - self.achieved_collection_target

                    else:
                        self.remaining_collection_target = 0.0

                else:
                    self.collection_target_achieved = False
                    self.achieved_collection_target = 0.0
                    self.remaining_collection_target = 0.0

            else:
                listt = []
                so_ids = []
                for sale_order in releted_sale_orders:
                    for line in sale_order.order_line:
                        if line.product_id.categ_id.id in self.category_ids.ids:
                            category_wise_sales = category_wise_sales + line.price_total
                            listt.append(sale_order.id)

                for so_id in listt:
                    if so_id not in so_ids:
                        so_ids.append(so_id)
                model_sale_orders = self.env['sale.order'].browse(so_ids)

                for sale_order in model_sale_orders:
                    if sale_order.invoice_ids:
                        for invoice in sale_order.invoice_ids:
                            if invoice.state == 'posted' and invoice.move_type == 'out_invoice':
                                category_wise_collection_amount = category_wise_collection_amount + \
                                    (invoice.amount_total -
                                     invoice.amount_residual)

                            if invoice.state == 'posted' and invoice.move_type == 'out_refund':
                                category_wise_return_amount = category_wise_return_amount + \
                                    (invoice.amount_total -
                                     invoice.amount_residual)
                
                category_wise_net_amount = category_wise_collection_amount - category_wise_return_amount  

                if self.commision_detail_line and self.commision_detail_line[0].sales_amount:
                    self.achieved_sales_target = (
                        category_wise_sales * 100)/(self.commision_detail_line[0].sales_amount)
                    if self.achieved_sales_target >= 100:
                        self.sales_target_achieved = True
                    else:
                        self.sales_target_achieved = False

                    if self.achieved_sales_target <= 100:
                        self.remaining_sales_target = 100 - self.achieved_sales_target

                    else:
                        self.remaining_sales_target = 0.0

                else:
                    self.sales_target_achieved = False
                    self.achieved_sales_target = 0.0
                    self.remaining_sales_target = 0.0

                if self.commision_detail_line and self.commision_detail_line[0].collection_amount:
                    self.achieved_collection_target = (
                        category_wise_net_amount * 100)/(self.commision_detail_line[0].collection_amount)

                    if self.achieved_collection_target >= 100:
                        self.collection_target_achieved = True
                    else:
                        self.collection_target_achieved = False

                    if self.achieved_collection_target <= 100:
                        self.remaining_collection_target = 100 - self.achieved_collection_target

                    else:
                        self.remaining_collection_target = 0.0

                else:
                    self.collection_target_achieved = False
                    self.achieved_collection_target = 0.0
                    self.remaining_collection_target = 0.0

        else:
            self.achieved_collection_target = 0.0
            self.remaining_collection_target = 0.0
            self.collection_target_achieved = False

            product_wise_quantity = 0.0
            category_wise_quantity = 0.0

            if self.type == 'product':
                for sale_order in releted_sale_orders:
                    for line in sale_order.order_line:
                        if line.product_id.id in self.product_ids.ids:
                            product_wise_quantity = product_wise_quantity + line.product_uom_qty

                if self.commision_detail_line and self.commision_detail_line[0].sales_amount:
                    self.achieved_sales_target = (
                        product_wise_quantity * 100)/(self.commision_detail_line[0].sales_amount)

                    if self.achieved_sales_target >= 100:
                        self.sales_target_achieved = True
                    else:
                        self.sales_target_achieved = False

                    if self.achieved_sales_target <= 100:
                        self.remaining_sales_target = 100 - self.achieved_sales_target

                    else:
                        self.remaining_sales_target = 0.0

                else:
                    self.sales_target_achieved = False
                    self.achieved_sales_target = 0.0
                    self.remaining_sales_target = 0.0

            else:
                for sale_order in releted_sale_orders:
                    for line in sale_order.order_line:
                        if line.product_id.categ_id.id in self.category_ids.ids:
                            category_wise_quantity = category_wise_quantity + line.product_uom_qty

                if self.commision_detail_line and self.commision_detail_line[0].sales_amount:
                    self.achieved_sales_target = (
                        category_wise_quantity * 100)/(self.commision_detail_line[0].sales_amount)

                    if self.achieved_sales_target >= 100:
                        self.sales_target_achieved = True
                    else:
                        self.sales_target_achieved = False

                    if self.achieved_sales_target <= 100:
                        self.remaining_sales_target = 100 - self.achieved_sales_target

                    else:
                        self.remaining_sales_target = 0.0

                else:
                    self.sales_target_achieved = False
                    self.achieved_sales_target = 0.0
                    self.remaining_sales_target = 0.0

    def create_bill(self):
        if self.commision_calculator == 'percentage' and self.percentage_on == 'sales':
            if self.commision_detail_line and self.commision_detail_line[0].sales_amount:
                commission_amount_based_sales = (
                    self.commision_detail_line[0].sales_amount * self.commision_detail_line[0].commision)/100

        if self.commision_calculator == 'percentage' and self.percentage_on == 'collection':
            if self.commision_detail_line and self.commision_detail_line[0].collection_amount:
                commission_amount_based_collection = (
                    self.commision_detail_line[0].collection_amount * self.commision_detail_line[0].commision)/100

        if self.commision_detail_line and self.commision_detail_line[0].commision :
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.user_id.partner_id.id,
                'invoice_date': date.today(),
                'date': date.today(),
                'target_commission_id' : self.id,
                'invoice_line_ids': [(0, 0, ({
                    'name': 'commission',
                    'quantity': 1,
                    'price_unit': self.commision_detail_line[0].commision if self.commision_calculator == 'amount' else (commission_amount_based_sales if self.percentage_on == 'sales' else commission_amount_based_collection)

                }))]
            })

            if bill:
                form_view = self.env.ref('account.view_move_form')
                return {
                    "name":"Bill",
                    "type": "ir.actions.act_window",
                    "res_model": "account.move",
                    "res_id" :bill.id,
                    'views': [(form_view.id, 'form')],
                    "target": "current",                    
                        }    
        else:
            raise UserError("Please Add Commission Related Information!!")            
    
    def compute__bill_ids(self):
        self.bill_ids = False
        target_related_bills = self.env['account.move'].search([('target_commission_id', '=',self.id)])
        if target_related_bills:
            self.bill_ids = [(6,0,target_related_bills.ids)]

    def open_bills(self):
        [action] = self.env.ref('account.action_move_in_invoice_type').read()
        action['domain'] = [('id', 'in',self.bill_ids.ids)]
        return action

    def compute_bill_count(self):
        for rec in self:
            rec.bill_count = len(self.bill_ids.ids)