
from odoo import models, fields, api, _
from odoo.tools import float_compare


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def _default_categs(self):
        categ = self.env['product.category'].search([('stock_type', '=', 'consu')], limit=1)
        return categ.id

    company_id = fields.Many2one(default=lambda self: self.env.company)
    sell_ids = fields.Many2many('product.supplierinfo', 'Vendor Pricelists', compute="_compute_vendor_pricelists", help="Define vendor pricelists.")
    is_approve = fields.Boolean(string="Approve", compute="_compute_approve", store=False)
    template_purchase_price_history_line_ids = fields.Many2many(
        "purchase.price.history",
        string="Price History Lines",
        compute="_compute_get_product_supplier_price_template"
    )
    can_be_direct = fields.Boolean(
        string='Can be Direct Purchased',
        copy=True,
    )
    is_vendor_pricelist = fields.Boolean(string="Vendor Price List", compute="_compute_vendor_pricelist", store=False)
    categ_id = fields.Many2one('product.category', default=_default_categs)
    # product_limit = fields.Selection([('no_limit',"Don't Limit"),('limit_per','Limit by Precentage %'),('limit_amount','Limit by Amount'),('str_rule','Strictly Limit by Purchase Order')],
	# 	string='Receiving Limit', tracking=True, default='no_limit')
    min_val = fields.Integer('Minimum Value')
    max_val = fields.Integer('Maximum Value')

    def _compute_vendor_pricelists(self):
        for rec in self:
            rec.sell_ids = [(6, 0, rec.seller_ids.filtered(lambda x: x.state == 'approved').ids)]

    @api.onchange('name')
    def _onchange_name(self):
        self._compute_vendor_pricelist()

    @api.onchange('type')
    def _onchange_type(self):
        if self.type == 'service':
            self.purchase_method = 'purchase'

    def _compute_vendor_pricelist(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        self.is_vendor_pricelist = IrConfigParam.get_param('is_vendor_pricelist_approval_matrix', False)
        # self.is_vendor_pricelist = self.env.company.is_vendor_pricelist_approval_matrix

    def _compute_get_product_supplier_price_template(self):
        for rec in self:
            rec.template_purchase_price_history_line_ids = []
            if rec and rec.id:
                if self.env.user.company_id:

                    cond = self.env.user.company_id.record_based_on_purchase
                    itm_limit = self.env.user.company_id.item_limit_purchase
                    purchase_price_line = []

                    if cond == "both":
                        purchase_line_obj = self.env["purchase.order.line"].sudo().search(
                            [("product_id", "in", rec.product_variant_ids.ids),
                             ("state", "in", ("purchase", "done"))],
                            limit=itm_limit,
                            order="create_date desc"
                        )
                    else:
                        # override record_based_on_purchase selection malah nambah value (?)
                        if cond == 'done':
                            cond = 'closed'
                        ###########################
                        purchase_line_obj = self.env["purchase.order.line"].sudo().search(
                            [("product_id", "in", rec.product_variant_ids.ids),
                             ("state", "=", str(cond))],
                            limit=itm_limit,
                            order="create_date desc"
                        )

                    if purchase_line_obj:
                        for record in purchase_line_obj:

                            vals = {}
                            vals.update({"name": record.id})

                            if record.partner_id:
                                vals.update({"partner_id": record.partner_id.id})

                            if record.product_id:
                                vals.update({"variant_id": record.product_id.id})
                            if record.order_id:
                                vals.update(
                                    {"purchase_order_id": record.order_id.id})

                            if record.order_id.date_order:
                                vals.update(
                                    {"order_date": record.order_id.date_order})
                            if record.product_qty:
                                vals.update({"quantity": record.product_qty})
                            if record.price_unit:
                                vals.update({"purchase_price": record.price_unit})
                            if record.price_subtotal:
                                vals.update({"total_price": record.price_subtotal})

                            if vals:
                                purchase_price_obj = self.env["purchase.price.history"].create(
                                    vals)

                                if purchase_price_obj:
                                    purchase_price_line.append(
                                        purchase_price_obj.id)

                    rec.template_purchase_price_history_line_ids = purchase_price_line

    def _compute_approve(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            record.is_approve = IrConfigParam.get_param('is_vendor_approval_matrix', False)
            # record.is_approve = self.env.company.is_vendor_approval_matrix
    
    @api.onchange('categ_id')
    def set_receive_limit1(self):
        for res in self:
            res._compute_approve()
            # if res.categ_id:
            #     res.update({
            #         'product_limit': res.categ_id.product_limit,
            #         'min_val': res.categ_id.min_val,
            #         'max_val': res.categ_id.max_val
            #     })
    
    @api.model
    def create(self, vals):
        if 'categ_id' in vals:
            categ_id = self.env['product.category'].browse(vals.get('categ_id'))
            if categ_id:
                # vals['product_limit'] = categ_id.product_limit
                vals['min_val'] = categ_id.min_val
                vals['max_val'] = categ_id.max_val
        return super(ProductTemplate, self).create(vals)
    
    def write(self, vals):
        if 'categ_id' in vals:
            categ_id = self.env['product.category'].browse(vals['categ_id'])
            if categ_id:
                # vals['product_limit'] = categ_id.product_limit
                vals['min_val'] = categ_id.min_val
                vals['max_val'] = categ_id.max_val
        return super(ProductTemplate, self).write(vals)

class ProductProduct(models.Model):
    _inherit = "product.product"

    purchase_price = fields.Float(
        string="Purchase Price",
        readonly=True,
        copy=False,
    )
    purchase_price_totals = fields.Float(
        string="Purchase Subtotal",
        compute="_get_purchase_price_total",
        store=True,
        copy=False,
    )

    @api.depends('purchase_order_line_ids','purchase_order_line_ids.state', 'purchase_order_line_ids.price_subtotal')
    def _get_purchase_price_total(self):
        for rec in self:
            line_ids = rec.purchase_order_line_ids.filtered(lambda x: x.state in ['purchase', 'done'])
            rec.purchase_price_totals = sum(line.price_subtotal for line in line_ids)
    
    def _select_seller(self, partner_id=False, quantity=0.0, date=None, uom_id=False, params=False):
        self.ensure_one()
        if date is None:
            date = fields.Date.context_today(self)
        if not date:
            date = fields.Date.context_today(self)
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        
        res = self.env['product.supplierinfo']
        sellers = self._prepare_sellers(params)
        sellers = sellers.filtered(lambda s: not s.company_id or s.company_id.id == self.env.company.id)
        for seller in sellers:
            # Set quantity in UoM of seller
            quantity_uom_seller = quantity
            if quantity_uom_seller and uom_id and uom_id != seller.product_uom:
                quantity_uom_seller = uom_id._compute_quantity(quantity_uom_seller, seller.product_uom, raise_if_failure=False)

            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if partner_id and seller.name not in [partner_id, partner_id.parent_id]:
                continue
            if float_compare(quantity_uom_seller, seller.min_qty, precision_digits=precision) == -1:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            if not res or res.name == seller.name:
                res |= seller
        return res.sorted('price')[:1]

class PurchaseProductTemplate(models.Model):
    _inherit = 'purchase.product.template'

    order_type = fields.Selection([
                ("goods_order","Goods Order"),
                ("services_order","Services Order"),
                ("assets_order","Assets Order"),
                ("rental_order","Rental Order")
                ], string='Order Type')

    is_good_services_order = fields.Boolean(compute="_compute_order", string="Orders")
    branch_id = fields.Many2one('res.branch', "Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], readonly=False)
    company_id = fields.Many2one('res.company', "Company", default=lambda self:self.env.company.id, readonly=True)
    
    @api.depends('name')
    def _compute_order(self):
        is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        self.is_good_services_order = is_good_services_order

class PurchaseProductTemplateLine(models.Model):
    _inherit = 'purchase.product.template.line'

    @api.onchange('purchase_template_id.order_type', 'name')
    def set_available_product_ids(self):
        for i in self:
            domain = [('company_id','=',self.purchase_template_id.company_id.id)]
            if self.purchase_template_id.order_type == 'goods_order':
                domain += [('type', 'in', ('consu','product'))]
            elif self.purchase_template_id.order_type == 'services_order':
                domain += [('type', '=', 'service')]
            elif self.purchase_template_id.order_type == 'assets_order':
                domain+= [('type', '=', 'asset')]
            elif self.purchase_template_id.order_type == 'rental_order':
                domain += [('is_rented', '=', True)]

            available_products = self.env['product.product'].sudo().search(domain)
            return {'domain': {'name': [('id', 'in', available_products.ids)]}}
