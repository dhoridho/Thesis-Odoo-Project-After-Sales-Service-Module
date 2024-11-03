# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError

class PosPromotion(models.Model):
    _name = "pos.promotion"
    _description = "Management Promotion on pos"
    _order = "sequence"

    sequence = fields.Integer(help="Gives the sequence promotion when displaying a list of promotions active")
    name = fields.Char('Name', required=1)
    active = fields.Boolean('Active', default=1)
    start_date = fields.Datetime('Start Date', default=fields.Datetime.now(), required=1)
    end_date = fields.Datetime('Expired Date', required=1)
    amount_total = fields.Float('Amount Total')
    type = fields.Selection([
        ('1_discount_total_order', '1. Total order discount'),
        ('2_discount_category', '2. POS Category discount'),
        ('3_discount_by_quantity_of_product', '3. Discount for different Quantity of Product'),
        ('4_pack_discount', '4. Discount if bought certain product'),
        ('5_pack_free_gift', '5. Free item if bought certain products'),
        ('6_price_filter_quantity', '6. Sale off all Products'),
        ('7_special_category', '7. Discount or free gift for selected categories'),
        ('8_discount_lowest_price', '8. Discount lowest Price'),
        ('9_multi_buy', '9. New Price if bought certain products'),
        ('10_buy_x_get_another_free', '10. Buy 10A get 1A, Buy 15A get 1A, Buy 20A get 2A'),
        ('11_first_order', '11. Discount % first Order'),
        ('12_buy_total_items_free_items', '12. Buy total Items free some Items'),
        ('13_gifts_filter_by_total_amount', '13. Free gift from total amount order'),
        ('14_tebus_murah_by_total_amount', '14. Tebus Murah by total amount order'),
        ('15_tebus_murah_by_specific_product', '15. Tebus Murah by specific product'),
        ('16_free_item_brands', '16. Free Items Brand'),
        ('17_tebus_murah_by_selected_brand', '17. Tebus Murah Selected Brands'),
    ], 'Type',
        default='1_discount_total_order',
        required=1,
        help=
        '1:  Order total Amount bigger than or equal 100 EUR discount 10%, bigger than or equal 200 EUR discount 20% ... \n'
        '2:  Drink discount 10%, Food discount 20% ... \n'
        '3:  Buy 3A discount 10%, Buy 6A discount 20%, Buy 10A discount 35% ....\n'
        '4:  Buy 10A + 10B discount X, Y, Z .. OR Buy 10A or 10B discount X and Y and Z\n'
        '5:  Buy 10A + 10B free X,Y,Z OR Buy 10A or 10B free X and Y and Z \n'
        '6:  Buy smaller than 10A price 10 EUR, Buy bigger than 20A price 15 EUR ....\n'
        '7:  Discount or free gift when customer buy product of category selected \n'
        '8:  Set discount on product lowest price of list products customer buy\n'
        '9:  Allow set multi Product with Quantity and multi Price\n'
        '10: Set Minimum Quantities is 10, Buy 10A get 1A, Buy 15A get 1A, Buy 20A get 2A\n'
        '11. Discount first Order of Customer \n'
        '12. If total items in Cart bigger than or equal X (quantities) will free some items.\n'
        ' Example Set Minimum Quantities is 10, will free 1A + 2B,\n'
        ' if Quantities smaller than or equal 20 free 2A + 4B \n'
        '13. Free Gifts filter by Total Amount Order, Exp: Total Amount bigger than 500 EUR free 1 coca\n'
        '14. Tebus murah / Cheap Redemption by Total Amount Order\n'
        '13. Tebus murah / Cheap Redemption by Specific Product\n')

    method = fields.Selection([
        ('only_one', 'OR'),
        ('all', 'AND')
    ],
        default='only_one',
        string='Condition Or / And',
        help='- Only One (or) : Buy 10A or  10B free 1X \n'
             '- All      (and): Buy 10A and 10B free 1X')
    discount_first_order = fields.Float('Discount First Order %')
    product_id = fields.Many2one(
        'product.product',
        'Product Service',
        help='It a product master data for Reward Program, please dont set Product Available in POS is false',
        domain=[('available_in_pos', '=', True)])
    discount_order_ids = fields.One2many(
        'pos.promotion.discount.order',
        'promotion_id',
        'Discounts')
    discount_category_ids = fields.One2many(
        'pos.promotion.discount.category',
        'promotion_id',
        'Categories Discounts')
    discount_quantity_ids = fields.One2many(
        'pos.promotion.discount.quantity',
        'promotion_id',
        'Quantities Discounts')
    gift_condition_ids = fields.One2many(
        'pos.promotion.gift.condition',
        'promotion_id',
        'Gifts condition')
    gift_free_ids = fields.One2many(
        'pos.promotion.gift.free',
        'promotion_id',
        'Gifts apply')
    discount_condition_ids = fields.One2many(
        'pos.promotion.discount.condition',
        'promotion_id',
        'Discounts condition')
    discount_apply_ids = fields.One2many(
        'pos.promotion.discount.apply',
        'promotion_id',
        'Discounts Apply')
    multilevel_condition_ids = fields.One2many(
        'pos.promotion.multilevel.condition',
        'promotion_id',
        'Multi Level: Gifts condition')
    multilevel_gift_ids = fields.One2many(
        'pos.promotion.multilevel.gift',
        'promotion_id',
        'Multi Level: Gifts apply')
    price_ids = fields.One2many(
        'pos.promotion.price',
        'promotion_id',
        'Prices')
    special_category_ids = fields.One2many(
        'pos.promotion.special.category',
        'promotion_id',
        'Special Category')
    discount_lowest_price = fields.Float(
        'Discount (%)',
        help='Discount n (%) of product lowest price of order lines')
    max_discount_amount_lowest_price  = fields.Float('Max. Discount Amount lowest price ')
    multi_buy_ids = fields.One2many(
        'pos.promotion.multi.buy',
        'promotion_id',
        'Multi Buy')
    promotion_specific_product_ids = fields.One2many(
        'pos.promotion.specific.product',
        'promotion_id',
        'Multi Specific Product')
    tebus_murah_product_ids = fields.One2many(
        'pos.promotion.tebus.murah',
        'promotion_id',
        'Tebus Murah Product')

    product_ids = fields.Many2many(
        'product.product',
        'promotion_product_rel',
        'promotion_id',
        'product_id',
        string='Products group',
        domain=[('available_in_pos', '=', True)]
    )

    minimum_items = fields.Integer(
        'Total Qty bigger than or equal',
        help='Minimum Items have in Cart for apply Promotion'
    )
    special_customer_ids = fields.Many2many(
        'res.partner',
        'promotion_partner_rel',
        'promotion_id',
        'partner_id',
        string='Special customer',
        help='Only customers added will apply promotion'
    )
    promotion_birthday = fields.Boolean('Promotion Birthday')
    promotion_birthday_type = fields.Selection([
        ('day', 'Birthday same Day'),
        ('week', 'Birthday in Week'),
        ('month', 'Birthday in Month')
    ],
        string='Time Apply',
        default='week'
    )
    promotion_group = fields.Boolean('Promotion Groups')
    promotion_group_ids = fields.Many2many(
        'res.partner.group',
        'pos_promotion_partner_group_rel',
        'promotion_id',
        'group_id',
        string='Customer Groups')
    state = fields.Selection([
        ('active', 'Active'),
        ('disable', 'Disable')
    ], string='State', default='active')
    no_of_usage = fields.Integer("No Of Usage", default=0)
    no_of_used = fields.Integer("No Of Used", compute='get_total_number_used')
    pos_branch_ids = fields.Many2many(
        'res.branch',
        'promotion_pos_branch_rel',
        'promotion_id',
        'branch_id',
        string='Branches Applied')
    payment_method_ids = fields.Many2many('pos.payment.method', string="Selected Payment Methods")
    special_days = fields.Boolean('Special Days')
    is_payment_method = fields.Boolean('Payment Methods')
    monday = fields.Boolean('Monday')
    tuesday = fields.Boolean('Tuesday')
    wednesday = fields.Boolean('Wednesday')
    thursday = fields.Boolean('Thursday')
    friday = fields.Boolean('Friday')
    saturday = fields.Boolean('Saturday')
    sunday = fields.Boolean('Sunday')

    special_times = fields.Boolean('Special Times')
    from_time = fields.Float('From Time')
    to_time = fields.Float('To Time')
    # product_brand_id = fields.Many2one('product.brand', string="Product Brand")
    is_stack = fields.Boolean(string="Stack Promotions")
    pos_apply = fields.Many2many(comodel_name='pos.config', string="Apply in POS")
    is_card_payment = fields.Boolean('Card Payment')
    card_payment_id = fields.Many2one('card.payment', string="Card Payment")
    card_payment_ids = fields.Many2many('card.payment',
        'pos_promotion_card_payment_rel', 'promotion_id', 'card_payment_id', string='Card Payment')

    new_type = fields.Selection([
        ('Discount Percentage','Discount Percentage (%)'), 
        ('Discount Fixed Amount','Discount Fixed Amount'),
        ('Free Item','Free Item'),
        ('Tebus Murah','Tebus murah / Cheap Redemption')
    ], string="New Type")
    new_based_on = fields.Selection([('All Product','All Product'), 
        ('Product category','POS Category'),
        ('Specific product','Specific product'),
        ('lowest price','lowest price'),
        ('first order','first order'),
        ], string="New Based On")
    tebus_murah_selected_brand_apply_and_or = fields.Selection([('And','And'), ('Or','Or')], string="Tebus Murah Selected Brand Apply And Or", default='And')
    tebus_murah_total_order_apply_and_or = fields.Selection([('And','And'), ('Or','Or')], string="Tebus Murah Total Order Apply And Or", default='And')
    new_based_on_free_item = fields.Selection([('All Product','All Product'), 
        ('Product category','POS Category'),
        ('Specific product','Specific product'),
        ('Selected Brand','Selected Brand'),
        ], string="New Based On Free Item")
    new_based_on_tebus_murah = fields.Selection([ 
        ('Total order','Total order'),
        ('Specific product','Specific product'),
        ('Selected Brand','Selected Brand')
        ], string="New Based On Tebus Murah")

    new_discount = fields.Float("New Discount")
    discount_fixed_amount_lp = fields.Float("Fixed Amount Discount Lowest Price")
    discount_fixed_amount_fo = fields.Float("Fixed Amount Discount First Order")
    company_id = fields.Many2one('res.company','Company',default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch','Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])
    promotion_based_on_brand_ids = fields.One2many('pos.promotion.selected.brand','promotion_id','Promotion Based On Brands')
    tebus_murah_selected_brand_ids = fields.One2many('pos.promotion.tebus.murah.selected.brand','promotion_id','Tebus Murah Selected Brand')
    tebus_murah_brand_gift_based_on = fields.Selection([
        ('min_amount', 'Min. Amount'),
        ('min_qty', 'Min. QTY'),

    ], default='min_amount', string='Tebus murah brand Gift Based On', required=1)

    tebus_murah_brand_min_amount_qty = fields.Float('Tebus murah brand Min Amount / QTY', default=1)
    tebus_murah_total_order_min_qty = fields.Integer('Tebus murah total order Min QTY')
    tebus_murah_brand_min_amount =  fields.Float('Tebus murah brand Min Amount ')
    tebus_murah_brand_min_qty=  fields.Float('Tebus murah brand Min Qty ')
    tebus_murah_brand_ids = fields.Many2many(
        'product.brand',
        'tebus_murah_brand_ids_rel',
        'promotion_id',
        'brand_id',
        string='Tebus Brand')

    discount_apply_and_or = fields.Selection([('And','And'), ('Or','Or')], string="Discount Apply And Or", default='And')
    discount_apply_min_amount = fields.Float('Discount Apply Min Amount')
    discount_apply_min_qty = fields.Float('Discount Apply Min Qty')
    discount_fix_amount_all_product = fields.Float('Discount Fix Amount All product')

    free_item_apply_and_or = fields.Selection([('And','And'), ('Or','Or')], string="Free item Apply And Or", default='And')
    free_item_apply_min_amount = fields.Float('Free item Apply Min Amount')
    free_item_apply_min_qty = fields.Float('Free item Apply Min Qty')


    tebus_murah_apply_and_or = fields.Selection([('And','And'), ('Or','Or')], string="Tebus Murah Apply And Or", default='And')
    tebus_murah_apply_min_amount = fields.Float('Tebus Murah Apply Min Amount')
    tebus_murah_apply_min_qty = fields.Float('Tebus Murah Apply Min Qty')


    is_multi_level_promotion = fields.Boolean('Multi Level Promotion',help='Activate to use multi-level promotion\ncan be applied to : Discount Percentage and Free Item')
    promotion_product_discount_id = fields.Many2one('product.product', 'Discount Account / Services', help='Product used to specify discount account only for this promotion')


    @api.onchange('is_multi_level_promotion')
    def _onchange_is_multi_level_promotion(self):
        self.ensure_one()
        for l in self.discount_order_ids:
            l.discount = 0
            l.multi_discount = False
        for l in self.discount_category_ids:
            l.discount = 0
            l.multi_discount = False
        for l in self.discount_quantity_ids:
            l.discount = 0
            l.multi_discount = False

    

    @api.onchange('new_type','new_based_on','new_based_on_free_item','new_based_on_tebus_murah')
    def onchange_new_type(self):
        if (self.new_type == 'Discount Percentage' or self.new_type == 'Discount Fixed Amount') and self.new_based_on=='All Product':
            self.type = "1_discount_total_order"
        elif (self.new_type == 'Discount Percentage' or self.new_type == 'Discount Fixed Amount') and self.new_based_on=='Product category':
            self.type = "2_discount_category"
        elif (self.new_type == 'Discount Percentage' or self.new_type == 'Discount Fixed Amount') and self.new_based_on=='Product pack':
            self.type = "4_pack_discount"
        elif (self.new_type == 'Discount Percentage' or self.new_type == 'Discount Fixed Amount') and self.new_based_on=='Specific product':
            self.type = "3_discount_by_quantity_of_product"
        elif (self.new_type == 'Discount Percentage' or self.new_type == 'Discount Fixed Amount') and self.new_based_on=='lowest price':
            self.type = "8_discount_lowest_price"
        elif (self.new_type == 'Discount Percentage' or self.new_type == 'Discount Fixed Amount') and self.new_based_on=='first order':
            self.type = "11_first_order"
        elif self.new_type == 'Free Item'  and self.new_based_on_free_item=='All Product':
            self.type = "13_gifts_filter_by_total_amount"
        elif self.new_type == 'Free Item'  and self.new_based_on_free_item=='Selected Brand':
            self.type = "16_free_item_brands"
        elif self.new_type == 'Free Item'  and self.new_based_on_free_item=='Product category':
            self.type = "7_special_category"
        elif self.new_type == 'Free Item'  and self.new_based_on_free_item=='Product pack':
            self.type = "5_pack_free_gift"
        elif self.new_type == 'Free Item'  and self.new_based_on_free_item=='Specific product':
            self.type = "10_buy_x_get_another_free"
        if self.new_type == 'Tebus Murah' and self.new_based_on_tebus_murah =='Total order':
            self.type = "14_tebus_murah_by_total_amount"
        if self.new_type == 'Tebus Murah' and self.new_based_on_tebus_murah =='Specific product':
            self.type = "15_tebus_murah_by_specific_product"
        if self.new_type == 'Tebus Murah' and self.new_based_on_tebus_murah =='Selected Brand':
            self.type = "17_tebus_murah_by_selected_brand"

        


    @api.onchange('is_payment_method')
    def _onchange_is_payment_method(self):
        if self.is_payment_method:
            self.payment_method_ids = [(6, 0, [])]
        else:
            self.payment_method_ids = [(6, 0, self.env['pos.payment.method'].search([]).ids)]

    def apply_to_selected_pos(self):
        if not self.pos_apply:
            raise UserError('No POS selected!')

        for pos_config in self.pos_apply:
            values = { 'promotion_ids': [(4, self.id)] }
            pos_config.with_context(apply_to_selected_pos=True).write(values)


        for pos_config in self.env['pos.config'].sudo().search([('promotion_ids','in',self.id)]):
            if pos_config.id not in self.pos_apply.ids:
                values = { 'promotion_ids': [(3, self.id)] }
                pos_config.with_context(apply_to_selected_pos=True).write(values)
                
        return True


    def sync_promotion_all_pos_online(self):
        sessions = self.env['pos.session'].sudo().search([
            ('state', '=', 'opened')
        ])
        for session in sessions:
            self.env['bus.bus'].sendmany(
                [[(self.env.cr.dbname, 'pos.sync.promotions', session.user_id.id), {}]])
        return True

    @api.model
    def default_get(self, fields):
        res = super(PosPromotion, self).default_get(fields)
        service_product = self.env['product.product'].search([('name','=','Promotion service')], limit=1)
        if service_product:
            res.update({'product_id': service_product.id})

        company = self.env.company
        if company and company.pos_product_discount1_id:
            res.update({'promotion_product_discount_id': company.pos_product_discount1_id.id})
            
        return res

    @api.model
    def create(self, vals):
        promotion = super(PosPromotion, self).create(vals)
        if promotion.type == '1_discount_total_order' and promotion.new_type == 'Discount Percentage':
            if len(promotion.discount_order_ids) > 1:
                raise UserError('Discount percentage based on all product only have 1 line discount counfiguration.')
        if promotion and promotion.product_id and not promotion.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')

        promotion._validate_condition()
        promotion.apply_to_selected_pos()
        promotion.sync_promotion_all_pos_online()
        return promotion

    def write(self, vals):
        res = super(PosPromotion, self).write(vals)
        for promotion in self:
            if promotion.type == '1_discount_total_order' and promotion.new_type == 'Discount Percentage':
                if len(promotion.discount_order_ids) > 1:
                    raise UserError('Discount percentage based on all product only have 1 line discount counfiguration.')
            if promotion and promotion.product_id and not promotion.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
    
            promotion._validate_condition()
            promotion.apply_to_selected_pos()
            promotion.sync_promotion_all_pos_online()
        return res

    def _validate_condition(self):
        self.ensure_one()
        if self.new_type == 'Discount Percentage':
            if self.new_based_on in 'All Product':
                if not self.discount_order_ids:
                    raise UserError('Required Condition: Discounts each Order Total')
            if self.new_based_on in 'Product category': # POS Category
                if not self.discount_category_ids:
                    raise UserError('Required Applied: Discounts each Pos Category')
            if self.new_based_on in 'Specific product':
                if not self.discount_quantity_ids:
                    raise UserError('Required Applied: Discounts each Quantity of Product')

        if self.new_type == 'Discount Fixed Amount':
            if self.new_based_on in 'Product category': # POS Category
                if not self.discount_category_ids:
                    raise UserError('Required Applied: Discounts each Pos Category')
            if self.new_based_on in 'Specific product':
                if not self.discount_quantity_ids:
                    raise UserError('Required Applied: Discounts each Quantity of Product')

        if self.new_type == 'Free Item':
            if self.new_based_on_free_item in 'All Product':
                if not self.gift_free_ids:
                    raise UserError('Required Applied: Free Products')
            if self.new_based_on_free_item in 'Product category': # POS Category
                if not self.special_category_ids:
                    raise UserError('Required Condition: Products each Special Category')
            if self.new_based_on_free_item in 'Specific product':
                if not self.promotion_specific_product_ids and self.is_multi_level_promotion == False:
                    raise UserError('Required Condition: Buy Products')
            if self.new_based_on_free_item in 'Selected Brand':
                if not self.promotion_based_on_brand_ids:
                    raise UserError('Required Condition: Products each Based On Brand')

        if self.new_type == 'Tebus Murah':
            if self.new_based_on_tebus_murah in ['Total order', 'Specific product']:
                if not self.tebus_murah_product_ids:
                    raise UserError('Required Applied: Tebus Murah Products')
            if self.new_based_on_tebus_murah == 'Selected Brand':
                if not self.tebus_murah_selected_brand_ids:
                    raise UserError('Required Applied: Tebus Murah Selected Brand')


# 1_discount_total_order
class PosPromotionDiscountOrder(models.Model):
    _name = "pos.promotion.discount.order"
    _order = "minimum_amount"
    _description = "Promotion each total order"

    active = fields.Boolean('Active', default=True)
    minimum_amount = fields.Float('Order Amount bigger than or equal', required=0)
    discount = fields.Float('Discount %', required=0)
    discount2 = fields.Float('Discount % 2', required=0)
    multi_discount = fields.Char('Multi Discount')
    max_discount_amount = fields.Float('Max. Discount Amount')
    discount_fixed_amount = fields.Float("Fixed Amount Discount")
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    def update_discount(self,percentage,residual_pecentage):
        # self.ensure_one()
        new_percentage= (percentage * residual_pecentage)/100
        return (residual_pecentage - new_percentage)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        # self.ensure_one()
        if self.multi_discount:
            splited_discounts = self.multi_discount.split("+")
            residual_pecentage = 100
            for discount in splited_discounts:
                try:
                    residual_pecentage = self.update_discount(float(discount),residual_pecentage)
                except:
                    raise UserError("Please Enter Valid Multi Discount")

            new_percentage = 100 - residual_pecentage
            if 0 < new_percentage < 100:
                self.discount = new_percentage
            else:
                raise UserError("Please Enter Valid Multi Discount")
        # return True


# 2_discount_category
class PosPromotionDiscountCategory(models.Model):
    _name = "pos.promotion.discount.category"
    _order = "discount"
    _description = "Promotion each product categories"

    active = fields.Boolean('Active', default=True)
    category_id = fields.Many2one('pos.category', 'POS Category')
    category_ids = fields.Many2many(
        'pos.category', 
        'pos_promotion_discount_category_pos_category_rel', 
        'pos_promotion_discount_category_id', 
        'pos_category_id', 
        string='POS Categories')

    discount = fields.Float('Discount %', required=0)
    min_qty = fields.Float('Min QTY', default=1)
    discount2 = fields.Float('Discount % 2', required=0)
    multi_discount = fields.Char('Multi Discount')
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')
    discount_fixed_amount = fields.Float("Fixed Amount Discount")
    max_discount_amount = fields.Float('Max. Discount Amount')


    _sql_constraints = [
        ('category_id_uniq', 'unique(category_id)', 'one category only one rule!'),
    ]


    def update_discount(self,percentage,residual_pecentage):
        # self.ensure_one()
        new_percentage= (percentage * residual_pecentage)/100
        return (residual_pecentage - new_percentage)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        # self.ensure_one()
        if self.multi_discount:
            splited_discounts = self.multi_discount.split("+")
            residual_pecentage = 100
            for discount in splited_discounts:
                try:
                    residual_pecentage = self.update_discount(float(discount),residual_pecentage)
                except:
                    raise UserError("Please Enter Valid Multi Discount")

            new_percentage = 100 - residual_pecentage
            if 0 < new_percentage < 100:
                self.discount = new_percentage
            else:
                raise UserError("Please Enter Valid Multi Discount")
        # return True

# 3_discount_by_quantity_of_product
class PosPromotionDiscountQuantity(models.Model):
    _name = "pos.promotion.discount.quantity"
    _order = "product_id"
    _description = "Promotion discount each product quantities"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one('product.product', 'Product', domain=[('available_in_pos', '=', True)]) 
    discount2 = fields.Float('Discount % 2', required=0)
    product_ids = fields.Many2many(
        'product.product', 
        'pos_promotion_discount_quantity_product_product_rel', 
        'pos_promotion_discount_quantity_id', 
        'product_id', 
        string='Products', domain=[('available_in_pos', '=', True)])
    quantity = fields.Float('Qty bigger than or equal', required=0)
    discount = fields.Float('Discount %', required=0)
    discount_fixed_amount = fields.Float("Fixed Amount Discount")
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')
    max_discount_amount = fields.Float('Max. Discount Amount')
    multi_discount = fields.Char('Multi Discount')

    @api.model
    def create(self, vals):
        record = super(PosPromotionDiscountQuantity, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionDiscountQuantity, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res


    def update_discount(self,percentage,residual_pecentage):
        # self.ensure_one()
        new_percentage= (percentage * residual_pecentage)/100
        return (residual_pecentage - new_percentage)

    @api.onchange('multi_discount')
    def _onchange_multi_discount(self):
        # self.ensure_one()
        if self.multi_discount:
            splited_discounts = self.multi_discount.split("+")
            residual_pecentage = 100
            for discount in splited_discounts:
                try:
                    residual_pecentage = self.update_discount(float(discount),residual_pecentage)
                except:
                    raise UserError("Please Enter Valid Multi Discount")

            new_percentage = 100 - residual_pecentage
            if 0 < new_percentage < 100:
                self.discount = new_percentage
            else:
                raise UserError("Please Enter Valid Multi Discount")
        # return True


# 5_pack_free_gift
class PosPromotionGiftCondition(models.Model):
    _name = "pos.promotion.gift.condition"
    _order = "product_id, minimum_quantity"
    _description = "Promotion gift condition"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one(
        'product.product',
        domain=[('available_in_pos', '=', True)],
        string='Product',
        required=1)
    minimum_quantity = fields.Float('Qty bigger than or equal', required=1, default=1.0)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    @api.model
    def create(self, vals):
        record = super(PosPromotionGiftCondition, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionGiftCondition, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res

# 5_pack_free_gift
# 12_buy_total_items_free_items
# 13_gifts_filter_by_total_amount
class PosPromotionGiftFree(models.Model):
    _name = "pos.promotion.gift.free"
    _order = "product_id"
    _description = "Promotion give gift to customer"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one(
        'product.product',
        domain=[('available_in_pos', '=', True)],
        string='Product gift',
        required=0)
    quantity_free = fields.Float('Qty Free', required=1, default=1.0)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')
    type_apply = fields.Selection([
        ('selected_product', 'Selected Product'),
        ('same_product', 'Same Product'),
        ('same_lower_price', 'Same / Lower Price'),
    ], default='selected_product', string='Type Apply', required=1)
    product_ids = fields.Many2many(
        'product.product',
        'promotion_gift_free_product_rel',
        'promotion_gift_free_id',
        'product_id',
        domain=[('available_in_pos', '=', True),('type','not in',['service','asset'])],
        string='Products gift',
    )

    @api.model
    def create(self, vals):
        record = super(PosPromotionGiftFree, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionGiftFree, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res

    @api.onchange('type_apply')
    def onchange_type_apply(self):
        self.product_ids = False

    @api.constrains('promotion_id','type_apply')
    def check_type_apply(self):
        promotion_gift_free_obj = self.env['pos.promotion.gift.free']
        check_data = promotion_gift_free_obj.search([('type_apply','=',self.type_apply),('promotion_id','=',self.promotion_id.id),('id','!=',self.id)],limit=1)
        if check_data:
            raise UserError("Promotion can't have same type apply for free product.")

# 4_pack_discount
class PosPromotionDiscountCondition(models.Model):
    _name = "pos.promotion.discount.condition"
    _order = "product_id, minimum_quantity"
    _description = "Promotion discount condition"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one(
        'product.product',
        domain=[('available_in_pos', '=', True)],
        string='Product',
        required=1)
    minimum_quantity = fields.Float('Qty bigger than or equal', required=1, default=1.0)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    @api.model
    def create(self, vals):
        record = super(PosPromotionDiscountCondition, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionDiscountCondition, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res

# 4_pack_discount
class PosPromotionDiscountApply(models.Model):
    _name = "pos.promotion.discount.apply"
    _order = "product_id"
    _description = "Promotion discount apply"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one(
        'product.product',
        domain=[('available_in_pos', '=', True)],
        string='Product',
        required=1)
    type = fields.Selection([
        ('one', 'Discount only one quantity'),
        ('all', 'Discount all quantity'),
    ], string='Type', default='one')
    discount = fields.Float('Discount %', required=0, default=1.0)
    discount_fixed_amount = fields.Float("Fixed Amount Discount")
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    @api.model
    def create(self, vals):
        record = super(PosPromotionDiscountApply, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionDiscountApply, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res

# 6_price_filter_quantity
class PosPromotionPrice(models.Model):
    _name = "pos.promotion.price"
    _order = "product_id, minimum_quantity"
    _description = "Promotion sale off"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one('product.product', domain=[('available_in_pos', '=', True)], string='Product',
                                 required=1)
    minimum_quantity = fields.Float('Qty bigger than or equal', required=1, default=1)
    price_down = fields.Float('Price Discount', required=1)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    @api.model
    def create(self, vals):
        product = self.env['product.product'].browse(vals['product_id'])
        if vals['price_down'] > product.lst_price:
            raise UserError('Price down could not bigger than product price %s' % product.lst_price)
        if not product.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return super(PosPromotionPrice, self).create(vals)

    def write(self, vals):
        for record in self:
            if vals.get('price_down') and (vals.get('price_down') > record.product_id.lst_price):
                raise UserError('Price down could not bigger than product price %s' % record.product_id.lst_price)
            if not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return super(PosPromotionPrice, self).write(vals)

# 7_special_category
class PosPromotionSpecialCategory(models.Model):
    _name = "pos.promotion.special.category"
    _order = "type"
    _description = "Promotion for special categories"

    active = fields.Boolean('Active', default=True)
    category_id = fields.Many2one('pos.category', 'POS Category', required=1)
    type = fields.Selection([
        ('discount', 'Discount'),
        ('free', 'Free gift')
    ], string='Type', required=1, default='free')
    product_ids = fields.Many2many(
        'product.product',
        'promotion_special_category_to_product_rel',
        'promotion_special_category_id',
        'product_id',
        domain=[('available_in_pos', '=', True),('type','not in',['service','asset'])],
        string='Products gift',
    )
    category_ids = fields.Many2many(
        'pos.category',
        'promotion_special_category_to_category_rel',
        'promotion_special_category_id',
        'category_id',
        string='Categories gift',
    )
    type_apply = fields.Selection([
        ('selected_category', 'Selected Category'),
        ('same_category', 'Same Category'),
        ('selected_product', 'Selected Product'),
    ], default='selected_product', string='Type Apply', required=1)
    count = fields.Integer('Count', help='How many product the same category will apply')
    discount = fields.Float('Discount %', required=0)
    discount_fixed_amount = fields.Float("Fixed Amount Discount")
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')
    product_id = fields.Many2one('product.product', 'Product', domain=[('available_in_pos', '=', True)])
    qty_free = fields.Float('Qty Gift', default=1)

    @api.onchange('type_apply')
    def onchange_type_apply(self):
        self.product_ids = False
        self.category_ids = False


    @api.model
    def create(self, vals):
        record = super(PosPromotionSpecialCategory, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionSpecialCategory, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res

# 9_multi_buy
class PosPromotionMultiBuy(models.Model):
    _name = "pos.promotion.multi.buy"
    _description = "Promotion for Multi Buy"

    active = fields.Boolean('Active', default=True)
    product_ids = fields.Many2many(
        'product.product',
        'promotion_multi_by_product_rel',
        'multi_by_id',
        'product_id',
        domain=[('available_in_pos', '=', True)],
        string='Products',
        required=1
    )
    promotion_id = fields.Many2one(
        'pos.promotion',
        'Promotion',
        required=1,
        ondelete='cascade'
    )
    list_price = fields.Float(
        'Sale Price',
        required=1
    )
    qty_apply = fields.Float(
        'Qty bigger than or qual',
        required=1,
        default=1
    )

    @api.model
    def create(self, vals):
        res = super(PosPromotionMultiBuy, self).create(vals)
        if vals.get('qty_apply') <= 0 or vals.get('list_price') <= 0:
            raise UserError('Promotion Price could not smaller than or equal 0')
        return res

    def write(self, vals):
        if (vals.get('qty_apply', None) and vals.get('qty_apply') <= 0) or (
                vals.get('list_price', None) and vals.get('list_price') <= 0):
            raise UserError('Promotion Price could not smaller than or equal 0')
        return super(PosPromotionMultiBuy, self).write(vals)



#10_buy_x_get_another_free
class PosPromotionSpecificProduct(models.Model):
    _name = "pos.promotion.specific.product"
    _description = "Promotion for specific product"


    active = fields.Boolean('Active', default=True)
    type_apply = fields.Selection([
        ('same_product', 'Same Product'),
        ('selected_product', 'Selected Product'),
    ], default='selected_product', string='Type Apply', required=1)
    qty_free = fields.Float('Qty Gift', default=1)
    product_id = fields.Many2one('product.product', 'Product', domain=[('available_in_pos', '=', True)])
    product_ids = fields.Many2many(
        'product.product',
        'promotion_specific_product_rel',
        'promotion_specific_product_id',
        'product_id',
        domain=[('available_in_pos', '=', True),('type','not in',['service','asset'])],
        string='Products gift',
    )
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')


    @api.onchange('type_apply')
    def onchange_type_apply(self):
        self.product_ids = False


    @api.model
    def create(self, vals):
        record = super(PosPromotionSpecificProduct, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionSpecificProduct, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res


# 15_tebus_murah_by_specific_product
class PosPromotionTebusMurah(models.Model):
    _name = 'pos.promotion.tebus.murah'
    _description = 'Promotion for Tebus Murah'

    active = fields.Boolean('Active', default=True)
    promotion_id = fields.Many2one( 'pos.promotion', 'Promotion', required=1, ondelete='cascade' )
    product_id = fields.Many2one('product.product', string='Tebus Murah Product', domain=[('available_in_pos', '=', True)], required=1)
    price = fields.Float('Price Tebus Murah', required=1)
    quantity = fields.Integer('Quantity', required=1, default=1)
    product_ids = fields.Many2many(
        'product.product',
        'pos_promotion_tebus_murah_specific_product_rel',
        'pos_promotion_tebus_murah_id',
        'product_id',
        domain=[('available_in_pos', '=', True),('type','not in',['service','asset'])],
        string='Products',
    )

    @api.model
    def create(self, vals):
        res = super(PosPromotionTebusMurah, self).create(vals)
        if vals.get('quantity') <= 0 or vals.get('price') <= 0:
            raise UserError('Promotion Price could not smaller than or equal 0')
        return res

    def write(self, vals):
        if (vals.get('quantity', None) and vals.get('quantity') <= 0) or (
                vals.get('price', None) and vals.get('price') <= 0):
            raise UserError('Promotion Price could not smaller than or equal 0')
        return super(PosPromotionTebusMurah, self).write(vals)




# 16_free_item_brands
class PosPromotionSelectedBrand(models.Model):
    _name = "pos.promotion.selected.brand"
    _order = "type_apply"
    _description = "Promotion for selected brand"

    active = fields.Boolean('Active', default=True)
    brand_ids = fields.Many2many('product.brand',
        'pos_promotion_selected_brand_brand_rel',
        'pos_promotion_selected_brand_id',
        'brand_id',
        string='Brands')
    type_apply = fields.Selection([
        ('same_brand', 'Same Brand'),
        ('selected_product', 'Selected Product'),
    ], default='same_brand', string='Type Apply', required=1)

    gift_based_on = fields.Selection([
        ('min_amount', 'Min. Amount'),
        ('min_qty', 'Min. QTY'),

    ], default='min_amount', string='Gift Based On', required=1)

    min_amount_qty = fields.Float('Min Amount / QTY', default=1)
    qty_qift = fields.Float('Qty Gift', default=1)

    product_ids = fields.Many2many(
        'product.product',
        'pos_promotion_selected_brand_product_rel',
        'pos_promotion_selected_brand_id',
        'product_id',
        domain=[('available_in_pos', '=', True),('type','not in',['service','asset'])],
        string='Products gift',
    )
    brand_gift_ids = fields.Many2many('product.brand',
        'pos_promotion_selected_brand_brand_gift_rel',
        'pos_promotion_selected_brand_id',
        'brand_id',
        string='Brands Gift')
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')


    @api.onchange('type_apply')
    def onchange_type_apply(self):
        self.product_ids = False
        self.brand_gift_ids = False


# 17_tebus_murah_by_selected_brand
class PosPromotionTebusMurahSelectedBrand(models.Model):
    _name = "pos.promotion.tebus.murah.selected.brand"
    _order = "type_apply"
    _description = "Promotion Tebus Murah Selected Brand"

    active = fields.Boolean('Active', default=True)
    type_apply = fields.Selection([
        ('same_brand', 'Same Brand'),
        ('selected_product', 'Selected Product'),
    ], default='same_brand', string='Type Apply', required=1)

    qty_qift = fields.Float('Qty Gift', default=1)
    tebus_murah_price = fields.Float('Tebus Murah Price')

    product_ids = fields.Many2many(
        'product.product',
        'pos_promotion_tebus_murah_selected_brand_product_rel',
        'pos_promotion_tebus_murah_selected_brand_id',
        'product_id',
        domain=[('available_in_pos', '=', True),('type','not in',['service','asset'])],
        string='Products gift',
    )

    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')


    @api.onchange('type_apply')
    def onchange_type_apply(self):
        self.product_ids = False


# 10_buy_x_get_another_free and Multi Level Promotion
class PosPromotionMultilevelCondition(models.Model):
    _name = "pos.promotion.multilevel.condition"
    _order = "product_id, minimum_quantity"
    _description = "Promotion Multi Level condition"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one(
        'product.product',
        domain=[('available_in_pos', '=', True)],
        string='Product',
        required=1)
    minimum_quantity = fields.Float('Product QTY', required=1, default=1.0)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    @api.model
    def create(self, vals):
        record = super(PosPromotionMultilevelCondition, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionMultilevelCondition, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res

# 10_buy_x_get_another_free and Multi Level Promotion
class PosPromotionMultilevelGift(models.Model):
    _name = "pos.promotion.multilevel.gift"
    _order = "product_id"
    _description = "Promotion Multi Level Gift"

    active = fields.Boolean('Active', default=True)
    product_id = fields.Many2one(
        'product.product',
        domain=[('available_in_pos', '=', True)],
        string='Product gift',
        required=1)
    quantity_free = fields.Float('Gift QTY', required=1, default=1.0)
    promotion_id = fields.Many2one('pos.promotion', 'Promotion', required=1, ondelete='cascade')

    @api.model
    def create(self, vals):
        record = super(PosPromotionMultilevelGift, self).create(vals)
        if record and record.product_id and not record.product_id.available_in_pos:
            raise UserError('Product service not available in POS. \n'
                            'Please go to product and check to checkbox available in pos / save')
        return record

    def write(self, vals):
        res = super(PosPromotionMultilevelGift, self).write(vals)
        for record in self:
            if record and record.product_id and not record.product_id.available_in_pos:
                raise UserError('Product service not available in POS. \n'
                                'Please go to product and check to checkbox available in pos / save')
        return res