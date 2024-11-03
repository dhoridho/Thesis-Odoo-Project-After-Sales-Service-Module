from typing import Collection
from odoo import models, fields, api, exceptions, _
from datetime import datetime, date, timedelta
from odoo.exceptions import UserError, ValidationError

class TargetCommision(models.Model):
    _name = 'sh.target.commision'
    _description = "Target & Commission"
    _inherit = ['sh.target.commision', 'portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    
    sales_team = fields.Many2one('crm.team', string="Sales Team", domain="[('company_id', '=', company_id)]", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)

    name = fields.Char(readonly=True)
    def _domain_user_id(self):
        current_company_id = self.env.company.id
        available_users=self.env['res.users'].search([('share', '=', False)]).filtered(lambda u,current_company_id=current_company_id:current_company_id in u.company_ids.ids)
        return [('id','in',available_users.ids)]
    user_id = fields.Many2one('res.users', string="User", domain=_domain_user_id, required=True, tracking=True)
    type = fields.Selection(selection="_get_selection", string="Type", default='product', tracking=True)

    def _get_selection(self):
        product_brand_filter = bool(self.env['ir.config_parameter'].sudo().get_param('is_product_brand_filter'))
        if product_brand_filter:# your codnition to check
            return [
                ('product', 'Product'),
                ('category', 'Category'),
                ('total_amount', 'Total Amount'),
                ('brand', 'Brand')
            ]
        else:
            return [
                ('product', 'Product'),
                ('category', 'Category'),
                ('total_amount', 'Total Amount')
            ]
    
    product_ids = fields.Many2many('product.product', string="Products", tracking=True)
    category_ids = fields.Many2many('product.category', string="Category", tracking=True)
    brand_id = fields.Many2one('product.brand', string='Brand', tracking=True)

    commision_calculator = fields.Selection([
        ('amount', 'Amount'),
        ('percentage', 'Percentage'),
    ], string="Commision Calculator", default='amount', required=True, tracking=True)
    from_date = fields.Date(string="From Date", required=True, tracking=True)
    to_date = fields.Date(string="To Date", required=True, tracking=True)

    target_on = fields.Selection([
        ('amount', 'Amount'),
        ('qty', 'Quantity'),
    ], string="Target On", default="amount", required=True, tracking=True)

    percentage_on = fields.Selection([
        ('sales', 'Sales Amount'),
        ('collection', 'Collection Amount'),
    ], tracking=True)
    
    commision_detail_line = fields.One2many(
        'sh.commision.detail', 'target_commision_id', tracking=True)
    
    collection_target_achieved = fields.Boolean(
        string="Collection Target Achieved", compute="compute_targets",search='search_collection_target_achieved', tracking=True)

    sales_target = fields.Float("Sales Target")
    collection_target = fields.Float("Collection Target")
    sales_actual = fields.Float("Sales Actual")
    collection_actual = fields.Float("Collection Actual")
    deduction = fields.Float("Deduction", compute="_compute_deduction", store=False)

    main_traget = fields.Float(string="Main Target", required=True)
    current_achievement = fields.Float(string="Current Achievement", compute='_compute_curr_achieve', store=True)
    current_commission = fields.Float(string="Current Commission", compute='_compute_curr_achieve', store=True)
    curr_achieve = fields.Float(compute='_compute_curr_achieve', string='Data')
    current_achievement_formula = fields.Float(string="Current Achievement Formula")

    def _compute_curr_achieve(self):
        for rec in self:
            bill_data = self.env['account.move'].search(
                [('target_commission_id', '=', rec.ids[0]), ('state', '=', 'posted')])
            if bill_data:
                pass
            else:
                bill_data = self.env['account.move'].search(
                    [('target_commission_id', '=', self.ids[0]), ('state', '=', 'draft')])
                if bill_data:
                    pass
                else:
                    self.is_target_posted = False
                    rec._compute_achievement()
                    rec._compute_achievement_amount()
            total_current_achievement = 0
            if rec.type == 'total_amount':
                # self.target_on = 'amount'
                rec.target_based_on = rec.target_based_on2
            else:
                rec.target_based_on = rec.target_based_on1

            from_date_input = rec.from_date
            to_date_input = rec.to_date
            if rec.from_date:
                from_date_input = str(rec.from_date) + ' 00:00:00'

            if rec.to_date:
                to_date_input = str(rec.to_date) + ' 23:59:59'

            if rec.target_based_on == 'sales':
                tran_ids = self.env['sale.order'].search(
                    [('date_order', '>=', from_date_input), ('date_order', '<=', to_date_input),
                    ('user_id', '=', rec.user_id.id),
                    ('state', '=', 'sale')])

                if rec.type == 'brand':
                    product_template_ids = self.env['product.template'].search([('product_brand_ids', 'in', rec.brand_id.ids)])
                    product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])
                    detail_data = self.env['sale.order.line'].search(
                        [('order_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
                elif rec.type == 'product':
                    detail_data = self.env['sale.order.line'].search(
                        [('order_id', 'in', tran_ids.ids), ('product_id', 'in', rec.product_ids.ids)])
                elif rec.type == 'category':
                    product_template_ids = self.env['product.template'].search([('categ_id', 'in', rec.category_ids.ids)])
                    product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])
                    detail_data = self.env['sale.order.line'].search(
                        [('order_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
                else:
                    detail_data = tran_ids

            elif rec.target_based_on == 'invoice' or rec.target_based_on == 'collection':
                tran_ids = self.env['account.move'].search(
                    [('date', '>=', rec.from_date), ('date', '<=', rec.to_date),
                    ('invoice_user_id', '=', rec.user_id.id),
                    ('state', '=', 'posted')])

                if rec.type == 'brand':
                    product_template_ids = self.env['product.template'].search([('product_brand_ids', 'in', rec.brand_id.ids)])
                    product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])

                    detail_data = self.env['account.move.line'].search(
                        [('move_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
                elif rec.type == 'product':
                    detail_data = self.env['account.move.line'].search(
                        [('move_id', 'in', tran_ids.ids), ('product_id', 'in', rec.product_ids.ids)])
                elif rec.type == 'category':
                    product_template_ids = self.env['product.template'].search([('categ_id', 'in', rec.category_ids.ids)])
                    product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])

                    detail_data = self.env['account.move.line'].search(
                        [('move_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
                else:
                    detail_data = tran_ids

            if rec.type == 'product' and rec.target_on == 'amount' and rec.target_based_on == 'sales':
                for det_rec in detail_data:
                    total_current_achievement = total_current_achievement + det_rec.price_subtotal

            elif rec.type == 'product' and rec.target_on == 'amount' and rec.target_based_on == 'invoice':
                for det_rec in detail_data:
                    if det_rec.move_id.move_type == 'out_refund':
                        total_current_achievement = total_current_achievement - det_rec.price_subtotal
                    else:
                        total_current_achievement = total_current_achievement + det_rec.price_subtotal

            elif rec.type == 'product' and rec.target_on == 'qty' and rec.target_based_on == 'sales':
                for det_rec in detail_data:
                    total_current_achievement = total_current_achievement + det_rec.product_uom_qty

            elif rec.type == 'product' and rec.target_on == 'qty' and rec.target_based_on == 'invoice':
                for det_rec in detail_data:
                    if det_rec.move_id.move_type == 'out_refund':
                        total_current_achievement = total_current_achievement - det_rec.quantity
                    else:
                        total_current_achievement = total_current_achievement + det_rec.quantity

            elif rec.type == 'category' and rec.target_on == 'amount' and rec.target_based_on == 'sales':
                for det_rec in detail_data:
                    total_current_achievement = total_current_achievement + det_rec.price_subtotal

            elif rec.type == 'category' and rec.target_on == 'amount' and rec.target_based_on == 'invoice':
                for det_rec in detail_data:
                    if det_rec.move_id.move_type == 'out_refund':
                        total_current_achievement = total_current_achievement - det_rec.price_subtotal
                    else:
                        total_current_achievement = total_current_achievement + det_rec.price_subtotal

            elif rec.type == 'category' and rec.target_on == 'qty' and rec.target_based_on == 'sales':
                for det_rec in detail_data:
                    total_current_achievement = total_current_achievement + det_rec.product_uom_qty

            elif rec.type == 'category' and rec.target_on == 'qty' and rec.target_based_on == 'invoice':
                for det_rec in detail_data:
                    if det_rec.move_id.move_type == 'out_refund':
                        total_current_achievement = total_current_achievement - det_rec.quantity
                    else:
                        total_current_achievement = total_current_achievement + det_rec.quantity

            elif rec.type == 'total_amount' and rec.target_on == 'amount' and rec.target_based_on == 'sales':
                for det_rec in tran_ids:
                    total_current_achievement = total_current_achievement + det_rec.amount_untaxed

            elif rec.type == 'total_amount' and rec.target_on == 'amount' and rec.target_based_on == 'invoice':
                for det_rec in tran_ids:
                    total_current_achievement = total_current_achievement + det_rec.amount_untaxed_signed

            elif rec.type == 'total_amount' and rec.target_on == 'amount' and rec.target_based_on == 'collection':
                for det_rec in tran_ids:
                    total_current_achievement = total_current_achievement + (det_rec.amount_total_signed-det_rec.amount_residual_signed)
            # Brand
            elif rec.type == 'brand' and rec.target_on == 'amount' and rec.target_based_on == 'sales':
                for det_rec in detail_data:
                    total_current_achievement = total_current_achievement + det_rec.price_subtotal

            elif rec.type == 'brand' and rec.target_on == 'amount' and rec.target_based_on == 'invoice':
                for det_rec in detail_data:
                    if det_rec.move_id.move_type == 'out_refund':
                        total_current_achievement = total_current_achievement - det_rec.price_subtotal
                    else:
                        total_current_achievement = total_current_achievement + det_rec.price_subtotal

            elif rec.type == 'brand' and rec.target_on == 'qty' and rec.target_based_on == 'sales':
                for det_rec in detail_data:
                    total_current_achievement = total_current_achievement + det_rec.product_uom_qty

            elif rec.type == 'brand' and rec.target_on == 'qty' and rec.target_based_on == 'invoice':
                for det_rec in detail_data:
                    if det_rec.move_id.move_type == 'out_refund':
                        total_current_achievement = total_current_achievement - det_rec.quantity
                    else:
                        total_current_achievement = total_current_achievement + det_rec.quantity

            rec.curr_achieve = total_current_achievement
            rec.current_achievement = total_current_achievement
            current_commission = 0
            if rec.current_achievement > 0 and rec.commision_detail_line:
                res_commision_detail_line = sorted(rec.commision_detail_line, key=lambda k: k['sales_amount'])
                for line in res_commision_detail_line:
                    if line.sales_amount <= rec.current_achievement:
                        current_commission = line.commision
            rec.current_commission = current_commission
            target_left = rec.main_traget - rec.current_achievement
            if target_left < 0:
                rec.target_left = 0
            else:
                rec.target_left = target_left
            target = self.env['sh.target.commision.new'].search([('commission_id', '=', rec.id)])
            if target:
                target.write({'curr_achieve': rec.curr_achieve})

    target_left = fields.Float(string="Target Left", compute='_compute_curr_achieve')

    target_based_on = fields.Selection([
        ('sales', 'Sales'),
        ('invoice', 'Invoice'),
        ('collection', 'Collection')
    ], string="Target Based On", default='sales', required=True)

    # extra for use on type selection
    target_based_on1 = fields.Selection([
        ('sales', 'Sales'),
        ('invoice', 'Invoice')
    ], string="Target Based On", default='sales', required=True)

    # extra for use on type selection
    target_based_on2 = fields.Selection([
        ('sales', 'Sales'),
        ('invoice', 'Invoice'),
        ('collection', 'Collection')
    ], string="Target Based On", default='sales', required=True)

    is_target_posted = fields.Boolean(string="Is Record Posted", default=False)

    @api.onchange('target_based_on1')
    def set_target_based_on1(self):
        self.target_based_on = self.target_based_on1

    @api.onchange('target_based_on2')
    def set_target_based_on2(self):
        self.target_based_on = self.target_based_on2

    # @api.onchange('current_achievement', 'commision_detail_line')
    # def _compute_current_commission(self):
    #     current_commission = 0
    #     if self.current_achievement > 0 and self.commision_detail_line:
    #         for res in self:
    #             res_commision_detail_line = sorted(res.commision_detail_line, key=lambda k: k['sales_amount'])
    #             for line in res_commision_detail_line:
    #                 if line.sales_amount <= self.current_achievement:
    #                     current_commission = line.commision

    #     self.write({'current_commission': current_commission})

    # @api.onchange('target_on')
    # def show_target_on_error(self):
    #     if self.type == 'total_amount' and self.target_on == 'qty':
    #         raise UserError("Can't use quantity as parameter in Total Amount type !!")

    @api.onchange('type', 'target_on', 'target_based_on', 'from_date', 'to_date', 'user_id', 'product_ids', 'category_ids', 'curr_achieve', 'brand_id')
    def _compute_achievement(self):
        if self.ids:
            bill_data = self.env['account.move'].search(
                [('target_commission_id', '=', self.ids[0]), ('state', '=', 'posted')])
            if bill_data:
                raise UserError("Can't update the parameters. There is bill posted")
            else:
                bill_data = self.env['account.move'].search(
                    [('target_commission_id', '=', self.ids[0]), ('state', '=', 'draft')])
                if bill_data:
                    raise UserError("Can't update the parameters. There is bill posted")
                else:
                    self.is_target_posted = False

        total_current_achievement = 0
        if self.type == 'total_amount':
            # self.target_on = 'amount'
            self.target_based_on = self.target_based_on2
        else:
            self.target_based_on = self.target_based_on1

        from_date_input = self.from_date
        to_date_input = self.to_date
        if self.from_date:
            from_date_input = str(self.from_date) + ' 00:00:00'

        if self.to_date:
            to_date_input = str(self.to_date) + ' 23:59:59'

        if self.target_based_on == 'sales':
            tran_ids = self.env['sale.order'].search(
                [('date_order', '>=', from_date_input), ('date_order', '<=', to_date_input),
                 ('user_id', '=', self.user_id.id),
                 ('state', '=', 'sale')])

            if self.type == 'brand':
                product_template_ids = self.env['product.template'].search(
                    [('product_brand_ids', 'in', self.brand_id.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])
                detail_data = self.env['sale.order.line'].search(
                    [('order_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            elif self.type == 'product':
                detail_data = self.env['sale.order.line'].search(
                    [('order_id', 'in', tran_ids.ids), ('product_id', 'in', self.product_ids.ids)])
            elif self.type == 'category':
                product_template_ids = self.env['product.template'].search([('categ_id', 'in', self.category_ids.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])
                detail_data = self.env['sale.order.line'].search(
                    [('order_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            else:
                detail_data = tran_ids

        elif self.target_based_on == 'invoice' or self.target_based_on == 'collection':
            tran_ids = self.env['account.move'].search(
                [('date', '>=', self.from_date), ('date', '<=', self.to_date),
                 ('invoice_user_id', '=', self.user_id.id),
                 ('state', '=', 'posted')])

            if self.type == 'brand':
                product_template_ids = self.env['product.template'].search(
                    [('product_brand_ids', 'in', self.brand_id.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])

                detail_data = self.env['account.move.line'].search(
                    [('move_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            elif self.type == 'product':
                detail_data = self.env['account.move.line'].search(
                    [('move_id', 'in', tran_ids.ids), ('product_id', 'in', self.product_ids.ids)])
            elif self.type == 'category':
                product_template_ids = self.env['product.template'].search([('categ_id', 'in', self.category_ids.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])

                detail_data = self.env['account.move.line'].search(
                    [('move_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            else:
                detail_data = tran_ids

        if self.type == 'product' and self.target_on == 'amount' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                total_current_achievement = total_current_achievement + det_rec.price_subtotal

        elif self.type == 'product' and self.target_on == 'amount' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    total_current_achievement = total_current_achievement - det_rec.price_subtotal
                else:
                    total_current_achievement = total_current_achievement + det_rec.price_subtotal

        elif self.type == 'product' and self.target_on == 'qty' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                total_current_achievement = total_current_achievement + det_rec.product_uom_qty

        elif self.type == 'product' and self.target_on == 'qty' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                     total_current_achievement = total_current_achievement - det_rec.quantity
                else:
                    total_current_achievement = total_current_achievement + det_rec.quantity

        elif self.type == 'category' and self.target_on == 'amount' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                total_current_achievement = total_current_achievement + det_rec.price_subtotal

        elif self.type == 'category' and self.target_on == 'amount' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    total_current_achievement = total_current_achievement - det_rec.price_subtotal
                else:
                    total_current_achievement = total_current_achievement + det_rec.price_subtotal

        elif self.type == 'category' and self.target_on == 'qty' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                total_current_achievement = total_current_achievement + det_rec.product_uom_qty

        elif self.type == 'category' and self.target_on == 'qty' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    total_current_achievement = total_current_achievement - det_rec.quantity
                else:
                    total_current_achievement = total_current_achievement + det_rec.quantity

        elif self.type == 'total_amount' and self.target_on == 'amount' and self.target_based_on == 'sales':
            for det_rec in tran_ids:
                total_current_achievement = total_current_achievement + det_rec.amount_untaxed

        elif self.type == 'total_amount' and self.target_on == 'amount' and self.target_based_on == 'invoice':
            for det_rec in tran_ids:
                total_current_achievement = total_current_achievement + det_rec.amount_untaxed_signed

        elif self.type == 'total_amount' and self.target_on == 'amount' and self.target_based_on == 'collection':
            for det_rec in tran_ids:
                total_current_achievement = total_current_achievement + (det_rec.amount_total_signed-det_rec.amount_residual_signed)

        elif self.type == 'brand' and self.target_on == 'amount' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                total_current_achievement = total_current_achievement + det_rec.price_subtotal

        elif self.type == 'brand' and self.target_on == 'amount' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    total_current_achievement = total_current_achievement - det_rec.price_subtotal
                else:
                    total_current_achievement = total_current_achievement + det_rec.price_subtotal

        elif self.type == 'brand' and self.target_on == 'qty' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                total_current_achievement = total_current_achievement + det_rec.product_uom_qty

        elif self.type == 'brand' and self.target_on == 'qty' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    total_current_achievement = total_current_achievement - det_rec.quantity
                else:
                    total_current_achievement = total_current_achievement + det_rec.quantity

        # self.current_achievement = total_current_achievement
        self.write({'current_achievement': total_current_achievement})
        target = self.env['sh.target.commision.new'].search([('commission_id', '=', self.id)])
        if target:
            target.write({'current_achievement': total_current_achievement})

    @api.onchange('target_on')
    def _compute_achievement_amount(self):
        if self.ids:
            bill_data = self.env['account.move'].search(
                [('target_commission_id', '=', self.ids[0]), ('state', '=', 'posted')])
            if bill_data:
                raise UserError("Can't update the parameters. There is bill posted")
            else:
                bill_data = self.env['account.move'].search(
                    [('target_commission_id', '=', self.ids[0]), ('state', '=', 'draft')])
                if bill_data:
                    raise UserError("Can't update the parameters. There is bill posted")
                else:
                    self.is_target_posted = False

        current_achievement_formula = 0
        if self.type == 'total_amount':
            # self.target_on = 'amount'
            self.target_based_on = self.target_based_on2
        else:
            self.target_based_on = self.target_based_on1

        from_date_input = self.from_date
        to_date_input = self.to_date
        if self.from_date:
            from_date_input = str(self.from_date) + ' 00:00:00'

        if self.to_date:
            to_date_input = str(self.to_date) + ' 23:59:59'

        if self.target_based_on == 'sales':
            tran_ids = self.env['sale.order'].search(
                [('date_order', '>=', from_date_input), ('date_order', '<=', to_date_input),
                 ('user_id', '=', self.user_id.id),
                 ('state', '=', 'sale')])

            if self.type == 'brand':
                product_template_ids = self.env['product.template'].search(
                    [('product_brand_ids', 'in', self.brand_id.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])
                detail_data = self.env['sale.order.line'].search(
                    [('order_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            elif self.type == 'product':
                detail_data = self.env['sale.order.line'].search(
                    [('order_id', 'in', tran_ids.ids), ('product_id', 'in', self.product_ids.ids)])
            elif self.type == 'category':
                product_template_ids = self.env['product.template'].search([('categ_id', 'in', self.category_ids.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])
                detail_data = self.env['sale.order.line'].search(
                    [('order_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            else:
                detail_data = tran_ids

        elif self.target_based_on == 'invoice' or self.target_based_on == 'collection':
            tran_ids = self.env['account.move'].search(
                [('date', '>=', self.from_date), ('date', '<=', self.to_date),
                 ('invoice_user_id', '=', self.user_id.id),
                 ('state', '=', 'posted')])

            if self.type == 'brand':
                product_template_ids = self.env['product.template'].search(
                    [('product_brand_ids', 'in', self.brand_id.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])

                detail_data = self.env['account.move.line'].search(
                    [('move_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            elif self.type == 'product':
                detail_data = self.env['account.move.line'].search(
                    [('move_id', 'in', tran_ids.ids), ('product_id', 'in', self.product_ids.ids)])
            elif self.type == 'category':
                product_template_ids = self.env['product.template'].search([('categ_id', 'in', self.category_ids.ids)])
                product_ids = self.env['product.product'].search([('product_tmpl_id', 'in', product_template_ids.ids)])

                detail_data = self.env['account.move.line'].search(
                    [('move_id', 'in', tran_ids.ids), ('product_id', 'in', product_ids.ids)])
            else:
                detail_data = tran_ids

        target_on_value = 'amount'

        if self.type == 'product' and target_on_value == 'amount' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                current_achievement_formula = current_achievement_formula + det_rec.price_subtotal

        elif self.type == 'product' and target_on_value == 'amount' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    current_achievement_formula = current_achievement_formula - det_rec.price_subtotal
                else:
                    current_achievement_formula = current_achievement_formula + det_rec.price_subtotal

        elif self.type == 'category' and target_on_value == 'amount' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                current_achievement_formula = current_achievement_formula + det_rec.price_subtotal

        elif self.type == 'category' and target_on_value == 'amount' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    current_achievement_formula = current_achievement_formula - det_rec.price_subtotal
                else:
                    current_achievement_formula = current_achievement_formula + det_rec.price_subtotal

        elif self.type == 'total_amount' and target_on_value == 'amount' and self.target_based_on == 'sales':
            for det_rec in tran_ids:
                current_achievement_formula = current_achievement_formula + det_rec.amount_untaxed

        elif self.type == 'total_amount' and target_on_value == 'amount' and self.target_based_on == 'invoice':
            for det_rec in tran_ids:
                current_achievement_formula = current_achievement_formula + det_rec.amount_untaxed_signed

        elif self.type == 'total_amount' and target_on_value == 'amount' and self.target_based_on == 'collection':
            for det_rec in tran_ids:
                current_achievement_formula = current_achievement_formula + (det_rec.amount_total_signed-det_rec.amount_residual_signed)
        # Brand
        elif self.type == 'brand' and self.target_on == 'amount' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                current_achievement_formula = current_achievement_formula + det_rec.price_subtotal

        elif self.type == 'brand' and self.target_on == 'amount' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    current_achievement_formula = current_achievement_formula - det_rec.price_subtotal
                else:
                    current_achievement_formula = current_achievement_formula + det_rec.price_subtotal

        elif self.type == 'brand' and self.target_on == 'qty' and self.target_based_on == 'sales':
            for det_rec in detail_data:
                current_achievement_formula = current_achievement_formula + det_rec.product_uom_qty

        elif self.type == 'brand' and self.target_on == 'qty' and self.target_based_on == 'invoice':
            for det_rec in detail_data:
                if det_rec.move_id.move_type == 'out_refund':
                    current_achievement_formula = current_achievement_formula - det_rec.quantity
                else:
                    current_achievement_formula = current_achievement_formula + det_rec.quantity

        # self.current_achievement = current_achievement_formula
        self.write({'current_achievement_formula': current_achievement_formula})
        target = self.env['sh.target.commision.new'].search([('commission_id', '=', self.id)])
        if target:
            target.write({'current_achievement_formula': current_achievement_formula})

    def _compute_deduction(self):
        for record in self:
            deduction_ids = self.env['sale.order'].search([('date_order', '>=', record.from_date), ('date_order', '<=', record.to_date),
                                                        ('user_id', '=' , record.user_id.id), ('company_id', '=', record.company_id.id), ('state','=','sale')])
            total_deduction = sum(deduction_ids.mapped('deduction_ids').mapped('product_total'))
            record.deduction = total_deduction    

    # @api.constrains('commision_detail_line')
    # def _check_commision_detail_line(self):
    #     for record in self:
    #         if len(record.commision_detail_line) > 1:
    #             raise ValidationError("Commission Detail Cannot have more then one line.")

    @api.constrains('type')
    def check_type(self):
        for record in self:
            if record.type == 'brand' and not record.brand_id:
                raise ValidationError("Brand must be selected")

            elif record.type == 'category' and not record.category_ids:
                raise ValidationError("Category must be selected")

            elif record.type == 'product' and not record.product_ids:
                raise ValidationError("Product must be selected")

    @api.constrains('target_on', 'type')
    def check_target_on(self):
        for record in self:
            if record.type == 'total_amount' and record.target_on != 'amount':
                raise ValidationError("Can't use quantity as parameter in Total Amount Type")

    @api.constrains('achieved_sales_target', 'achieved_collection_target', 'commision_detail_line')
    def compute_target(self):
        for res in self:
            sales_target = 0
            collection_target = 0
            for line in res.commision_detail_line:
                sales_target += line.sales_amount
                collection_target += line.collection_amount
            res.write({
                'sales_target': sales_target,
                'collection_target': collection_target,
                'sales_actual': sales_target * res.achieved_sales_target / 100,
                'collection_actual': collection_target * res.achieved_collection_target / 100,
            })

    @api.onchange('sales_team')
    def onchange_partner_id(self):
        for rec in self:
            rec.user_id = False
            if rec.sales_team:
                return {'domain': {'user_id': ['|', ('sale_team_id', '=', rec.sales_team.id), ('id', '=', rec.sales_team.user_id.id)]}}
    
    @api.onchange('company_id')
    def onchange_sales_team_id(self):
        for res in self:
            res.sales_team = False

    def create_bill(self):
        if self.to_date > date.today():
            raise UserError("Period has not been expired yet !!")

        bill_data = self.env['account.move'].search(
            [('target_commission_id', '=', self.id), ('state', '=', 'posted')])
        if bill_data:
            raise UserError('Bill already has been created and posted')
        else:
            bill_data = self.env['account.move'].search(
                [('target_commission_id', '=', self.id), ('state', '=', 'draft')])
            if bill_data:
                raise UserError('Bill already has been created and posted and in draft state')

        if self.commision_calculator == 'percentage' and self.percentage_on == 'sales':
            if self.commision_detail_line and self.commision_detail_line[0].sales_amount:
                commission_amount_based_sales = (
                    self.commision_detail_line[0].sales_amount * self.commision_detail_line[0].commision)/100

        if self.commision_calculator == 'percentage' and self.percentage_on == 'collection':
            if self.commision_detail_line and self.commision_detail_line[0].collection_amount:
                commission_amount_based_collection = (
                    self.commision_detail_line[0].collection_amount * self.commision_detail_line[0].commision)/100

        price_unit = ((self.current_achievement_formula - self.deduction) * self.current_commission) / 100

        if self.commision_detail_line and self.commision_detail_line[0].commision:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.user_id.partner_id.id,
                'invoice_user_id': self.user_id.id,
                'invoice_date': date.today(),
                'date': date.today(),
                'target_commission_id': self.id,
                'invoice_line_ids': [(0, 0, ({
                    'name': 'commission',
                    'quantity': 1,
                    'price_unit': price_unit
                }))]
                # , (0, 0, ({
                #     'name': 'Deduction',
                #     'quantity': 1,
                #     'price_unit': -(self.deduction),
                # }))
            })

            if bill:
                self.update({'is_target_posted': True})
                form_view = self.env.ref('account.view_move_form')
                return {
                    "name": "Bill",
                    "type": "ir.actions.act_window",
                    "res_model": "account.move",
                    "res_id": bill.id,
                    'views': [(form_view.id, 'form')],
                    "target": "current",
                }
        else:
            raise UserError("Please Add Commission Related Information!!")


    @api.model
    def create(self, vals):
        res = super(TargetCommision, self).create(vals)
        self.env['sh.target.commision.new'].create({
            'commission_id': res.id,
            'name': res.name,
            'user_id': res.user_id.id,
            'main_target': res.main_traget,
            'current_achievement': res.current_achievement,
            'target_based_on': res.target_based_on,
            'target_on': res.target_on,
            'to_date': res.to_date,
            'type': res.type
        })
        return res

    def write(self, vals):
        res = super(TargetCommision, self).write(vals)
        targets = self.env['sh.target.commision.new'].search([('commission_id', 'in', self.ids)])
        if targets:
            # targets.unlink()
            # self.env['sh.target.commision.new'].create({
            #     'commission_id': self.id,
            #     'name': self.name,
            #     'user_id': self.user_id.id,
            #     'main_target': self.main_traget,
            #     'current_achievement': self.current_achievement,
            #     'target_based_on': self.target_based_on,
            #     'target_on': self.target_on,
            #     'to_date': self.to_date,
            #     'type': self.type
            # })
            for target in targets:
                self.env['sh.target.commision.new'].write({
                    'name': target.name,
                    'user_id': target.user_id.id,
                    'main_target': target.main_target,
                    'current_achievement': target.current_achievement,
                    'target_based_on': target.target_based_on,
                    'target_on': target.target_on,
                    'to_date': target.to_date,
                    'type': target.type
                })
        return res


class AccountMoveCommission(models.Model):
    _inherit = 'account.move'

    def button_cancel(self):
        # OVERRIDE to update Target posted value to False.
        res = super(AccountMoveCommission, self).button_cancel()
        for move in self:
            if move.move_type == 'in_invoice':
                self.env['sh.target.commision'].search([
                    ('id', 'in', move.mapped('target_commission_id').ids)
                ]).write({'is_target_posted': False})
        return res


class TargetCommisionNew(models.Model):
    _name = 'sh.target.commision.new'
    _description = "Sh Target Commission New"
    
    commission_id = fields.Many2one('sh.target.commision', string="Target Commission", ondelete="cascade")
    name = fields.Char(readonly=True)
    user_id = fields.Many2one('res.users')
    main_target = fields.Float(string="Main Target")
    current_achievement = fields.Float(string="Current Achievement")
    current_achievement_formula = fields.Float(string="Current Achievement Formula")
    curr_achieve = fields.Float(string='Data')
    target_based_on = fields.Selection([
        ('sales', 'Sales'),
        ('invoice', 'Invoice'),
        ('collection', 'Collection')
    ], string="Target Based On")
    target_on = fields.Selection([
        ('amount', 'Amount'),
        ('qty', 'Quantity'),
    ], string="Target On")
    to_date = fields.Date(string="To Date")
    type = fields.Selection([
        ('product', 'Product'),
        ('category', 'Category'),
        ('total_amount', 'Total Amount'),
        ('brand', 'Brand')
    ], string="Type")