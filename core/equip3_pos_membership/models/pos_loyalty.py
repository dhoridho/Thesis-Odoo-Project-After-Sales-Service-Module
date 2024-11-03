# -*- coding: utf-8 -*-
import json
from odoo import fields, api, models, api, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta
from odoo.http  import request  
from lxml import etree

class PosLoyaltyRewardProduct(models.Model):
    _name = 'pos.loyalty.reward.product'
    _description = 'Loyalties Reward Product'
    _rec_name = 'product_id'

    gift_reward_id = fields.Many2one('pos.loyalty.reward', string='Loyalty Reward')
    product_id = fields.Many2one('product.product', string='Product', domain=[('available_in_pos', '=', True)])
    redeem_point = fields.Integer('Redeem Point', help='How many point is needed to get the product')
    default_code = fields.Char('Product Code', compute='_compute_values')
    list_price = fields.Float('Sale Price', compute='_compute_values')
    uom_id = fields.Many2one('uom.uom', string='Unit of measure', compute='_compute_values')
    sh_qr_code = fields.Char('QR Code', compute='_compute_values')

    @api.depends('product_id')
    def _compute_values(self):
        for rec in self:
            rec.default_code = rec.product_id and rec.product_id.default_code or False
            rec.list_price = rec.product_id and rec.product_id.list_price or False
            rec.uom_id = rec.product_id and rec.product_id.uom_id or False
            rec.sh_qr_code = rec.product_id and rec.product_id.sh_qr_code or False

class PosLoyaltyCategory(models.Model):
    _name = "pos.loyalty.category"
    _description = "Member loyalty type"
    _order = "from_point asc, to_point asc"

    name = fields.Char('Name', required=1)
    code = fields.Char('Code', required=False)
    active = fields.Boolean('Active', default=1)
    from_point = fields.Float('Point From', required=1)
    to_point = fields.Float('Point To', required=1)
    coefficient = fields.Float('Coefficient ratio', required=1,
                               help='1 point converted to 10 USD, the input value is 10,\n'
                                    '1 point converted to 100 USD, the input value is 100\n'
                                    '1 point converted to 1000 USD, the input value is 1000.',
                               default=1, digits=(16, 2))
    member_card = fields.Selection([('barcode','Barcode'), ('qrcode','QR')], string="Member Card", 
                                    default="barcode")
    card_template_barcode = fields.Binary('Upload Image - Barcode', help="Image size: 953 x 615 px" )
    card_template_qrcode = fields.Binary('Upload Image - QrCode', help="Image size: 1032 x 578 px" )
    card_template_barcode_name = fields.Char('Card Template - Barcode filename')
    card_template_qrcode_name = fields.Char('Card Template - QrCode filename')
    member_card_preview = fields.Char('Member Card Preview', compute='_compute_member_card_preview')
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)


   
    @api.model
    def create(self, vals):
        if vals.get('from_point') <= 0 and vals.get('name') != 'Default':
            raise UserError('You can not set "Point From" smaller than or equal 0. Please set bigger than 0')
        if vals.get('to_point') < vals.get('from_point'):
            raise UserError('You can not set "Point To" smaller than "Point From". Please set bigger than "Point From"')

        if 'member_card' in vals:
            vals['member_card'] = 'barcode'
            
        res =  super(PosLoyaltyCategory, self).create(vals)
        res.check_intersects()
        return res

    def write(self, vals):
        if 'member_card' in vals:
            vals['member_card'] = 'barcode'

        res =  super(PosLoyaltyCategory, self).write(vals)
        self.check_intersects()
        
        if self.to_point < self.from_point:
            raise UserError('You can not set "Point To" smaller than "Point From". Please set bigger than "Point From"')
        return res

    def check_intersects(self):
        for rec in self:
            has_intersect = False
            domain = [('from_point','<=',rec.from_point), ('to_point','>=',rec.from_point), ('id','!=',rec.id)]
            domain += ['|', ('from_point','<=',rec.to_point), ('to_point','>=',rec.to_point), ('id','!=',rec.id)]
            if self.env[self._name].search_read(domain, ['name','from_point','to_point'], limit=1):
                has_intersect = True

            if not has_intersect:
                for _type in self.env[self._name].search_read([('id','!=',rec.id)], ['name','from_point','to_point']):
                    if rec.from_point <= _type['from_point'] <= rec.to_point or rec.from_point <= _type['to_point'] <= rec.to_point:
                        has_intersect = True
                        break

            if has_intersect:
                raise UserError('The value in "Point From" / "Point To" is intersects, please change the value!')
        return True
    
    @api.depends('member_card', 'card_template_barcode', 'card_template_qrcode')
    def _compute_member_card_preview(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            rec.member_card_preview = json.dumps({
                'barcode_card': rec.get_member_card_barcode('HERLINA SUSANTO','0429170123010'),
                'qrcode_card': rec.get_member_card_qrcode('HERLINA SUSANTO','0429170123010'),
            })

    def get_member_card_barcode(self, name, code):
        background_url = ''
        nocache = datetime.now().strftime('%Y%m%d%H%M%S')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        code_url = f'{base_url}/report/barcode?type=Code128&value={code}&width=600&height=120&humanreadable=1'

        if not self.card_template_barcode:
            background_url = f'{base_url}/equip3_pos_membership/static/src/img/DefaultBarcodeCard.png'
            # return '<div class="no-image-msg">Upload image to view member card</div>'
        elif self.card_template_barcode:
            background_url = f'{base_url}/web/image?model=pos.loyalty.category&field=card_template_barcode&id={self.id}&nocache={nocache}'

        return f'''
        <div class="member-card member-card-barcode" style="position: relative;overflow: hidden;display: block;width: 643px;height: 415px;border: none;background: url({background_url}) no-repeat;background-position: center;background-size: 100% 100%;">
            <div class="member-card-name" style="z-index: 5;position: absolute;bottom: 49%;left: 47px;color: white;font-size: 30px;text-transform: uppercase;width: 86%;display: block;text-overflow: ;word-break: break-all;line-height: 1;font-family: sans-serif;font-weight: bold;">
                <span>{name}</span>
            </div>
            <div class="member-card-code" style="z-index: 2;position: absolute;bottom: 65px;right: 0;color: black;height: 94px;width: 100%;">
                <img style="display: block;width: auto;height: 100%;margin: auto;" src="{code_url}"/>
            </div>
        </div>
        '''

    def get_member_card_qrcode(self, name, code):
        background_url = ''
        nocache = datetime.now().strftime('%Y%m%d%H%M%S')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        code_url = '/equip3_pos_membership/static/src/img/qrcode.png'


        if not self.card_template_qrcode:
            background_url = f'{base_url}/equip3_pos_membership/static/src/img/DefaultQRCard.png'
        elif self.card_template_qrcode:
            background_url = f'{base_url}/web/image?model=pos.loyalty.category&field=card_template_qrcode&id={self.id}&nocache={nocache}'

        return f'''
        <div class="member-card member-card-qrcode" style="position: relative;overflow: hidden;display: block;width: 643px;height: 415px;border: none;background: url({background_url}) no-repeat;background-position: center;background-size: 100% 100%;">
            <div class="member-card-name" style=" z-index: 5; position: absolute; bottom: 47px; left: 43px; color: white; font-size: 30px; font-weight: bold; text-transform: uppercase; width: 55%; display: block; text-overflow: ellipsis; word-break: break-all; line-height: 1; font-family: sans-serif;">
                <span>{name}</span>
                <br/>
                <span>{code}</span>
            </div>
            <div class="member-card-code" style=" z-index: 2; position: absolute; bottom: 81px; right: 59.5px; color: black; height: 160px; width: 160px; ">
                <img style="display: block;width: auto;height: 100%;margin: auto;" src="{code_url}"/>
            </div>
        </div>
        '''
    
    # @api.constrains('from_point', 'to_point')
    # def _check_existing_record(self):
    #     for record in self:
    #         pos_loyalty_categ_id = self.search([('id', '!=', record.id),
    #                                         '&', ('from_point', '<=', record.from_point), ('to_point', '>=', record.from_point),
    #                                         '&', ('from_point', '<=', record.to_point), ('to_point', '>=', record.to_point),
    #                                         '&', ('from_point', '>=', record.from_point), ('to_point', '<=', record.to_point)], limit=1)
    #         if pos_loyalty_categ_id:
    #             raise ValidationError("The minimum and maximum range of this member type is intersects with other member type [%s]. Please change the minimum and maximum range" % (pos_loyalty_categ_id.name))

class PosLoyalty(models.Model):
    _name = "pos.loyalty"
    _description = "Loyalties Program, on this object we define loyalty program, included rules of plus points and rules of redeem points"

    name = fields.Char('Loyalty Name', required=1)
    rule_ids = fields.One2many(
        'pos.loyalty.rule', 'loyalty_id', 'Rules', help='Rules for plus points to customer')
    reward_ids = fields.One2many(
        'pos.loyalty.reward', 'loyalty_id', 'Rewards',
        help='Rules for redeem points when customer use points on order')
    product_redeem_ids = fields.One2many(
        'pos.loyalty.reward', 'product_redeem_loyalty_id', 'Redeem Product',
        help='Rules for redeem points when customer use points on order')
    reward_redeem_ids = fields.One2many(
        'pos.loyalty.reward', 'reward_redeem_loyalty_id', 'Redeem Rewards',
        help='Rules for redeem points when customer use points on order')
    count_product_redeem = fields.Integer('Count - Redeem Product', compute='_compute_count_product_redeem')
    state = fields.Selection([
        ('running', 'Running'),
        ('stop', 'Stop')
    ], string='State', default='running')
    type = fields.Selection([
        ('plus point', 'Plus Point'), 
        ('redeem','Redeem Point')
    ], string='Type')
    product_loyalty_id = fields.Many2one(
        'product.product',
        string='Product Reward Service',
        help='When you add Reward to cart, this product use for add to cart with price reward amount',
        domain=[('available_in_pos', '=', True)],
        required=1)
    rounding = fields.Float(
        string='Rounding Points', default=1,
        help="This is rounding ratio for rounding plus points \n"
             "when customer purchase products, compute like rounding of currency")
    rounding_down = fields.Boolean(
        string='Rounding Down Total', default=0,
        help="Rounding down total points plus, example when customer purchase order,\n"
             "Total points plus is 7,9 pos will rounding to 7 points, and if 7,1 points become to 7")
    config_ids = fields.One2many('pos.config', 'pos_loyalty_id', string='Pos Setting Applied')
    pos_config_ids = fields.Many2many('pos.config',
        'pos_loyalty_pos_config_rel', 'loyalty_id', 'pos_config_id', string='Selected POS')
    period_expired = fields.Integer(
        'Period Time Expired (day)',
        required=1,
        help='All points coming from this program will expired if out of date this period days. \n'
             'Example: You set is 30 days, any plus points will have life times is 30 days\n'
             'And out of 30 days, points auto expired and reduce points of customer',
        default=30)
    start_date = fields.Datetime('Start Date')
    end_date = fields.Datetime('End Date')
    company_id = fields.Many2one('res.company', string='Company',default=lambda self: self.env.company.id)

    # pos_loyalty_category_ids = fields.Many2many('pos.loyalty.category', string='Member Type')



    @api.constrains('type', 'rule_ids','reward_redeem_ids')
    def _check_correct_value_rules_plus(self):
        for data in self:
            if data.type == 'plus point':
                for rule in data.rule_ids:
                    if rule.coefficient <= 0:
                        raise UserError('You can not set coefficient smaller than or equal 0. Please set bigger than 0')
                    if rule.min_amount < 0:
                        raise UserError('You can not set min amount smaller than 0. Please set bigger than or equal 0')
                    if rule.expired_period_value <= 0 and rule.is_expired_period:
                        raise UserError('You can not set Expired Period smaller than or equal 0. Please set bigger than 0')
            if data.type == 'redeem':
                for rule in data.reward_redeem_ids:
                    if rule.redeem_coefficient <= 0:
                        raise UserError('You can not set Redeem coefficient smaller than or equal 0. Please set bigger than 0')
                    if rule.min_amount < 0:
                        raise UserError('You can not set min amount smaller than 0. Please set bigger than or equal 0')


    @api.constrains('start_date', 'end_date')
    def _check_correct_value_date(self):
        for data in self:
            if data.start_date and data.end_date:
                if data.end_date <= data.start_date:
                    raise UserError('You can not set End date smaller than or equal Start date. Please set bigger than Start date')


    @api.model
    def create(self, vals):
        if vals.get('period_expired', None) and vals.get('period_expired', None) <= 0:
            raise UserError(
                'You can not set period expired days of points smaller than or equal 0. Please set bigger than 0')
        res = super(PosLoyalty, self).create(vals)
        if not self._context.get('action_applied_to_selected_loyalty_pos'):
            res.action_applied_to_selected_pos()
        # for loyalty in res:
        #     if loyalty.type == 'redeem' and len(loyalty.product_redeem_ids) > 1: 
        #         raise UserError('You can not set more than one Product redeem rule!')
        return res

    def write(self, vals):
        if vals.get('period_expired', None) and vals.get('period_expired', None) <= 0:
            raise UserError(
                'You can not set period expired days of points smaller than or equal 0. Please set bigger than 0')
        res = super(PosLoyalty, self).write(vals)
        if not self._context.get('action_applied_to_selected_loyalty_pos'):
            for data in self:
                data.action_applied_to_selected_pos()
        # for loyalty in self:
        #     if loyalty.type == 'redeem' and len(loyalty.product_redeem_ids) > 1: 
        #         raise UserError('You can not set more than one Product redeem rule!')
        return res

    @api.model
    def default_get(self, default_fields):
        res = super(PosLoyalty, self).default_get(default_fields)
        products = self.env['product.product'].search([('default_code', '=', 'Rs')])
        if products:
            res.update({'product_loyalty_id': products[0].id})
        return res

    def active_all_pos(self):
        configs = self.env['pos.config'].search([])
        for loyalty in self:
            if loyalty.state == 'running':
                configs.write({'pos_loyalty_id': loyalty.id})
            else:
                raise UserError('Loyalty program required state is running')
        return True

    def action_applied_to_selected_pos(self):
        self.ensure_one()
        for pos_config in self.pos_config_ids:
            values = { 'pos_loyalty_ids': [(4, self.id)] }
            pos_config.with_context(action_applied_to_selected_pos=True).write(values)

        for pos_config in self.env['pos.config'].sudo().search([('pos_loyalty_ids','in',self.id)]):
            if pos_config.id not in self.pos_config_ids.ids:
                values = { 'pos_loyalty_ids': [(3, self.id)] }
                pos_config.with_context(action_applied_to_selected_pos=True).write(values)
        return True


    def get_point_plus_loyalty(self,partner,orders):
        plus_point = 0
        for data in self:
            if data.type == 'plus point':
                for rule in data.rule_ids:
                    if partner.pos_loyalty_type and partner.pos_loyalty_type.id in rule.pos_loyalty_category_ids.ids:
                        for order in orders:
                            if rule.type == 'order_amount':
                                if rule.min_amount <= order.amount_total:
                                     plus_point+= rule.coefficient * order.amount_total
                            else:
                                sum_amount_total_get = 0
                                for line in order.lines:
                                    if line.product_id.id in rule.product_ids.ids and rule.type == 'products':
                                        sum_amount_total_get += line.price_subtotal_incl
                                    if line.product_id.pos_categ_id.id in rule.category_ids.ids and rule.type == 'categories':
                                        sum_amount_total_get += line.price_subtotal_incl
                                if rule.min_amount <= sum_amount_total_get:
                                     plus_point+= rule.coefficient * sum_amount_total_get
        return plus_point

    @api.depends('product_redeem_ids')
    def _compute_count_product_redeem(self):
        for loyalty in self:
            loyalty.count_product_redeem = len(loyalty.product_redeem_ids)

class PosLoyaltyRule(models.Model):
    _name = "pos.loyalty.rule"
    _rec_name = 'loyalty_id'
    _description = "Loyalties rule plus points"
    _order = 'sequence asc'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=1)
    active = fields.Boolean('Active', default=1)
    loyalty_id = fields.Many2one('pos.loyalty', 'Loyalty', required=1)
    pos_loyalty_category_ids = fields.Many2many('pos.loyalty.category', string='Member Type')
    coefficient = fields.Float('Coefficient ratio', required=1,
                               help=' 10    USD covert to 1 point input value is 0.1,\n'
                                    ' 100   USD covert to 1 point input value is 0.01\n'
                                    ' 1000  USD covert to 1 point input value is 0.001.',
                               default=1, digits=(16, 6))
    type = fields.Selection([
        ('products', 'Selected Products'),
        ('categories', 'Selected Categories'),
        ('order_amount', 'Total Amount')
    ], string='Type', required=1, default='products')
    product_ids = fields.Many2many('product.product', 'loyalty_rule_product_rel', 'rule_id', 'product_id',
                                   string='Products', domain=[('available_in_pos', '=', True)])
    category_ids = fields.Many2many('pos.category', 'loyalty_rule_pos_categ_rel', 'rule_id', 'categ_id',
                                    string='Categories')
    categories = fields.Char(string='POS Categories', compute='_compute_categories', store=False)
    min_amount = fields.Float('Min amount', required=1, help='This condition min amount of order can apply rule')
    coefficient_note = fields.Text(compute='_get_coefficient_note', string='Coefficient note')
    is_multi = fields.Boolean('Is Multi') 
    calc_point_without_point_as_payment = fields.Boolean('Calculate point without point as payment')
    state = fields.Selection([
        ('running', 'Running'),
        ('stop', 'Stop')
    ], string='State', default='running')
    is_expired_period = fields.Boolean('Use Expired Period ?')
    expired_period = fields.Selection([
        ('Day', 'Day'),
        ('Month', 'Month'),
        ('Year', 'Year')
    ], string='Expired Period', default='Year')
    expired_period_value = fields.Integer('Expired Period Value',default=1)


    @api.model
    def create(self, vals):
        if vals.get('coefficient', None) and vals.get('coefficient', None) <= 0:
            raise UserError(
                'You can not set Coefficient smaller than or equal 0. Please set bigger than 0')
        return super(PosLoyaltyRule, self).create(vals)

    def write(self, vals):
        if vals.get('coefficient', None) and vals.get('coefficient', None) <= 0:
            raise UserError(
                'You can not set Coefficient smaller than or equal 0. Please set bigger than 0')
        return super(PosLoyaltyRule, self).write(vals)

    @api.onchange('coefficient')
    def _get_coefficient_note(self):
        for rule in self:
            if rule.coefficient:
                rule_coefficient = 1/rule.coefficient
                decimal_comma = 2
                rule_coefficient = round(rule_coefficient, decimal_comma)
                check_rule_coefficient = str(rule_coefficient).split('.')
                if len(check_rule_coefficient) > 1 and len(check_rule_coefficient[1]) < decimal_comma:
                    rule_coefficient = str(rule_coefficient) + '0'
                rule.coefficient_note = 'Every Purchase of %s Will Get 1 Point' % (rule_coefficient)
            else:
                rule.coefficient_note = False

    @api.onchange('type')
    def onchange_type(self):
        if self.type != 'order_amount':
            self.calc_point_without_point_as_payment = False

    @api.depends('category_ids')
    def _compute_categories(self):
        def find_childs(categ):
            if not categ.child_id:
                return [categ.id]

            nodes = []
            for child in categ.child_id:
                nodes += [child.id]
                if child.child_id:
                    nodes += find_childs(child)
            return nodes

        for rule in self:
            ids = []
            for category in rule.category_ids:
                ids += [category.id]
                ids += find_childs(category)
            rule.categories = str(list(set(ids)))

class PosLoyaltyReward(models.Model):
    _name = "pos.loyalty.reward"
    _description = "Loyalties rule redeem points"
    _order = 'sequence asc'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=1)
    active = fields.Boolean('Active', default=1)
    loyalty_id = fields.Many2one('pos.loyalty', 'Loyalty', required=False)
    product_redeem_loyalty_id = fields.Many2one('pos.loyalty', 'Loyalty')
    reward_redeem_loyalty_id = fields.Many2one('pos.loyalty', 'Loyalty')

    redeem_point = fields.Float('Redeem Point', help='This is total point get from customer when cashier Reward')
    type = fields.Selection([
        ('use_point_payment', 'Use points as payment'),
        ('discount_products', 'Discount Products'),
        ('discount_categories', 'Discount Categories'),
        ('gift', 'Free Gift'),
    ], string='Type of Reward', required=1, help="""
        Discount Products: Will discount list products filter by products\n
        Discount categories: Will discount products filter by categories \n
        Gift: Will free gift products to customers \n
        Use point payment : covert point to discount price \n
    """)
    coefficient = fields.Float('Coefficient Ratio', required=1,
                               help=' 1     point  covert to 1 USD input value is 1,\n'
                                    ' 10    points covert to 1 USD input value is 0.1\n'
                                    ' 1000  points cover to 1 USD input value is 0.001.',
                               default=1, digits=(16, 6))
    redeem_coefficient = fields.Float('Redeem Coefficient', required=1,
                               help=' 1     point  covert to 1 USD input value is 1,\n'
                                    ' 10    points covert to 1 USD input value is 0.1\n'
                                    ' 1000  points cover to 1 USD input value is 0.001.',
                               default=1, digits=(16, 6))
    discount = fields.Float('Discount %', required=False, help='Discount %', default=0.0)
    discount_product_ids = fields.Many2many('product.product', 'reward_product_rel', 'reward_id', 'product_id',
                                            string='Products', domain=[('available_in_pos', '=', True)])
    discount_category_ids = fields.Many2many('pos.category', 'reward_pos_categ_rel', 'reward_id', 'categ_id',
                                             string='POS Categories')
    min_amount = fields.Float('Min Amount', required=False, default=0.0,
                              help='Required Amount Total of Order bigger than or equal for apply this Reward')
    gift_product_rule_ids = fields.One2many('pos.loyalty.reward.product', 'gift_reward_id', string='Gift Products')
    resale_product_ids = fields.Many2many('product.product', 'reward_resale_product_product_rel', 'reward_id',
                                          'resale_product_id',
                                          string='Resale Products', domain=[('available_in_pos', '=', True)])
    gift_product_ids = fields.Many2many('product.product', 'reward_gift_product_product_rel', 'reward_id',
                                        'gift_product_id',
                                        string='Gift Products', domain=[('available_in_pos', '=', True)])
    gift_quantity = fields.Float('Gift Quantity', default=1)
    price_resale = fields.Float('Price of resale')
    coefficient_note = fields.Text(compute='_get_coefficient_note', string='Coefficient note')
    state = fields.Selection([
        ('running', 'Running'),
        ('stop', 'Stop')
    ], string='State', default='running')
    line_ids = fields.One2many('pos.order.line', 'reward_id', 'POS order lines')
    pos_loyalty_category_ids = fields.Many2many('pos.loyalty.category', string='Member Type')
    discount_child_category_ids = fields.Many2many('pos.category', string='POS Categories (Child)')

    @api.model
    def create(self, vals):

        if self.discount_category_ids:
            for rule in self:
                all_child_categories = []
                for category_list in self.discount_category_ids:
                    child_categories = category_list.get_all_child_categories(category_list)
                    for child_categ in child_categories:
                        if child_categ.id not in all_child_categories:
                            all_child_categories.append(child_categ.id)

                vals['discount_child_category_ids'] = [(6, 0, all_child_categories)]

        if vals.get('coefficient', None) and vals.get('coefficient', None) <= 0:
            raise UserError(
                'You can not set Coefficient smaller than or equal 0. Please set bigger than 0')
        return super(PosLoyaltyReward, self).create(vals)

    def write(self, vals):

        if self.discount_category_ids:
            for rule in self:
                all_child_categories = []
                for category_list in self.discount_category_ids:
                    child_categories = category_list.get_all_child_categories(category_list)
                    for child_categ in child_categories:
                        if child_categ.id not in all_child_categories:
                            all_child_categories.append(child_categ.id)

                vals['discount_child_category_ids'] = [(6, 0, all_child_categories)]

        if vals.get('coefficient', None) and vals.get('coefficient', None) <= 0:
            raise UserError(
                'You can not set Coefficient smaller than or equal 0. Please set bigger than 0')
        return super(PosLoyaltyReward, self).write(vals)



    def _get_coefficient_note(self):
        for rule in self:
            if rule.type != 'gift':
                rule.coefficient_note = '1 point will cover to %s %s with condition min amount total order bigger than: %s' % (
                    rule.coefficient, self.env.user.company_id.currency_id.name, rule.min_amount)
            else:
                rule.coefficient_note = '%s (points) will give 1 quantity of each product bellow' % (rule.coefficient)




class PosLoyaltyPoint(models.Model):
    _name = 'pos.loyalty.point'
    _rec_name = 'partner_id'
    _order = 'id desc'
    _description = 'Model Management all points pluus or redeem of customer'

    partner_id = fields.Many2one('res.partner', 'Member', required=1, index=1)
    member_point = fields.Float('Member Points',related='partner_id.pos_loyalty_point')
    member_phone = fields.Char(string='Member Phone', related='partner_id.phone')
    member_type = fields.Many2one('pos.loyalty.category', string='Member type', related='partner_id.pos_loyalty_type')
    member_type_code = fields.Char(string='Member type Code', related='member_type.code')
    point = fields.Float('Reward Point')
    point_no_rounding = fields.Float('Point (No Rounding)')
    redeemed_point = fields.Float('Redeemed' , help='Deduct Plus Point')
    order_id = fields.Many2one('pos.order', 'Order Ref', index=1, ondelete='cascade')
    end_date = fields.Datetime('Expired Date')
    type = fields.Selection([
        ('import', 'Manual import'),
        ('plus', 'Plus'),
        ('redeem', 'Redeem Point'), # will deduct point
        ('void', 'Void'), # will deduct point | from void order
        ('return', 'Refund'), # will deduct point | from Return order
    ], string='Type', default='import', required=1)
    state = fields.Selection([
        ('ready', 'Ready to use'),
        ('expired', 'Expired')
    ], string='State', default='ready')
    description = fields.Char('Description')

    is_return = fields.Boolean('Is Return', readonly=1)
    is_rounding = fields.Boolean('Is Rounding')
    loyalty_id = fields.Many2one('pos.loyalty', 'Loyalty Program')
    product_redeemed_ids = fields.Many2many('product.product',
        'pos_loyalty_point_product_product_rel', 'loyalty_point_id', 'product_id', string='Product Redeemed')

    loyalty_reward_id = fields.Many2one('pos.loyalty.reward','Loyalty Reward')
    loyalty_rule_id = fields.Many2one('pos.loyalty.rule','Loyalty Rule')
    is_all_redeemed = fields.Boolean('All redeemed ?',copy=False)
    remaining_point = fields.Float('Remaining Point',compute='_compute_remaining_point')
    company_id = fields.Many2one('res.company','Company',related="partner_id.company_id")
    branch_id = fields.Many2one('res.branch','Branch',related="partner_id.pos_branch_id")

    def _compute_remaining_point(self):
        for loyalty in self:
            remaining_point = 0
            not_expired = (not loyalty.end_date or fields.Datetime.now() < loyalty.end_date)
            if not_expired and loyalty.type == 'plus':
                remaining_point = loyalty.point - loyalty.redeemed_point
            if loyalty.type in ['void', 'return']:
                remaining_point -= loyalty.point
            loyalty.remaining_point = remaining_point

    @api.model
    def create(self, vals):
        point_obj = self.env['pos.loyalty.point']
        loyalty_program = self.env['pos.loyalty'].browse(vals.get('loyalty_id'))
        res = super(PosLoyaltyPoint, self).create(vals)
        for rec in res:
            if not rec.end_date and rec.type == 'plus':
                if rec.loyalty_rule_id.is_expired_period and rec.loyalty_rule_id.expired_period_value and rec.loyalty_rule_id.expired_period :
                    if rec.loyalty_rule_id.expired_period == 'Day':
                        rec.end_date = rec.create_date + relativedelta(days=rec.loyalty_rule_id.expired_period_value)
                    if rec.loyalty_rule_id.expired_period == 'Month':
                        rec.end_date = rec.create_date + relativedelta(months=rec.loyalty_rule_id.expired_period_value)
                    if rec.loyalty_rule_id.expired_period == 'Year':
                        rec.end_date = rec.create_date + relativedelta(years=rec.loyalty_rule_id.expired_period_value)
            
            # trigger update member point
            rec.partner_id._get_point()

            if rec.type == 'redeem':
                total_point_cut = rec.point
                domain = [('type', 'in', ['plus', 'import']),('partner_id','=',rec.partner_id.id),('is_all_redeemed','=',False),('state','!=','expired')]
                point_plus_rec = point_obj.search(domain, order='create_date desc')
                if point_plus_rec:

                    #Redeem priority to closer expired
                    point_plus_closer_rec = point_plus_rec.filtered(lambda l: l.end_date).sorted(key=lambda x: x.end_date)
                    residual_point_cut = point_plus_closer_rec.set_redeem_in_plus_point(total_point_cut)
                    if residual_point_cut:
                        point_plus_not_closer_rec = point_plus_rec.filtered(lambda l: not l.end_date)
                        point_plus_not_closer_rec.set_redeem_in_plus_point(residual_point_cut)

        return res

    def write(self, vals):
        res = super(PosLoyaltyPoint, self).write(vals)
        for rec in self:
            # trigger update member point
            rec.partner_id._get_point()
        return res

    def cron_expired_points(self):
        domain = [('end_date', '<=', fields.Datetime.now()), ('type', 'in', ['plus', 'import'])]
        domain += [('end_date','!=', False),('state','!=','expired')]
        loyalty_points = self.search(domain)
        if loyalty_points:
            loyalty_points.write({'state': 'expired'})
        return True

    def set_expired(self):
        return self.write({'state': 'expired'})

    def set_ready(self):
        return self.write({'state': 'ready'})

    def set_redeem_in_plus_point(self,total_point_cut):
        for point_plus in self:
            point_residual = point_plus.point - point_plus.redeemed_point
            if total_point_cut < point_residual:
                point_plus.write({ 
                    'redeemed_point': total_point_cut+point_plus.redeemed_point
                })
                total_point_cut = 0
                if point_plus.point == point_plus.redeemed_point:
                    point_plus.write({ 'is_all_redeemed':True })
                break
            else:
                point_cut = point_residual
                if point_cut <= 0:
                    continue

                point_plus.write({
                    'redeemed_point': point_plus.redeemed_point+point_cut
                })
                total_point_cut-= point_cut
                if point_plus.point == point_plus.redeemed_point:
                    point_plus.write({ 'is_all_redeemed':True })
            if not total_point_cut:
                break
        return total_point_cut



class PosLoyaltyUpdatePoint(models.Model):
    _name = "pos.loyalty.update.point"
    _description = "POS Loyalty Update Point"

    name = fields.Char('Name',default=lambda self: _('New'), required=1)
    type_apply = fields.Selection([('plus', 'Plus'),('redeem', 'Redeem')], string='Type', required=1,default='plus')
    state = fields.Selection([('draft', 'Draft'),('confirmed', 'Confirmed')], string='State', default='draft')
    member_id = fields.Many2one('res.partner','Member', required=1)
    pos_order_ids = fields.Many2many('pos.order',string='Order Reference')
    is_orders = fields.Boolean('Orders ?',help='Based on existing order')
    total_orders = fields.Float('Total Orders')
    current_point = fields.Float('Current Points')
    reward_point = fields.Float('Rewards Points')
    total_point = fields.Float('Total Points')
    history_ids = fields.One2many('pos.loyalty.history.update.point','parent_id','Histories')
    is_editable_point = fields.Boolean(default=True)

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=False, submenu=False):
        res = super(PosLoyaltyUpdatePoint, self).fields_view_get(
            view_id=view_id, view_type=view_type)
        if  not request.session.debug:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            res['arch'] = etree.tostring(root)
        return res

    def act_confirm(self):
        self.ensure_one()
        point_obj = self.env['pos.loyalty.point']
        loyalty_obj = self.env['pos.loyalty']
        point = 0
        redeem = 0

        point = self.reward_point

        if self.type_apply == 'redeem' and self.is_orders:
            raise UserError("Can't redeem point with orders.")

        dict_create = {
            'partner_id':self.member_id.id,
            'type':self.type_apply,
        }
        if not self.is_orders:
            dict_create['point'] = point
            point_obj.create(dict_create)
        else:
            date_now = fields.Datetime.to_string(datetime.now())
            domain = [('state','=','running'),('type','=','plus point'),('start_date','<=',date_now)]
            domain += ['|',('end_date','=',False),('end_date','>',date_now)]
            loyaltys = loyalty_obj.search(domain)
            for o in self.pos_order_ids:
                dict_create['point'] = loyaltys.get_point_plus_loyalty(self.member_id,o)
                dict_create['order_id'] = o.id
                point_obj.create(dict_create)
        self.state = 'confirmed'
        return True


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pos.loyalty.update.point')
        result = super(PosLoyaltyUpdatePoint, self).create(vals)
        return result





    @api.onchange('member_id','reward_point','is_orders','pos_order_ids','type_apply')
    def onchange_all(self):
        loyalty_obj = self.env['pos.loyalty']
        self.ensure_one()
        data = self
        total_orders = 0
        current_point = 0
        is_editable_point = True

        if data.member_id:
            current_point = data.member_id.pos_loyalty_point
        if data.type_apply == 'plus':
            total_point = current_point + data.reward_point
        else:
            total_point = current_point - data.reward_point

        if data.is_orders:
            for order in data.pos_order_ids:
                total_orders+=order.amount_total
        else:
            data.pos_order_ids = False

        if data.type_apply == 'plus' and data.is_orders:
            is_editable_point = False
            
            reward_point = 0
            date_now = fields.Datetime.to_string(datetime.now())
            domain = [('state','=','running'),('type','=','plus point'),('start_date','<=',date_now)]
            domain += ['|',('end_date','=',False),('end_date','>',date_now)]
            loyaltys = loyalty_obj.search(domain)
            if data.pos_order_ids and data.member_id:
                reward_point = loyaltys.get_point_plus_loyalty(data.member_id,data.pos_order_ids)
            data.reward_point = reward_point
        data.total_orders = total_orders
        data.current_point = current_point
        data.total_point = total_point
        data.is_editable_point = is_editable_point

        return {'readonly':{'reward_point':1}}


    @api.onchange('member_id')
    def onchange_member(self):
        update_obj = self.env['pos.loyalty.update.point']
        for data in self:
            history_ids = []
            if data.member_id:
                recs = update_obj.search([('member_id','=',data.member_id.id),('state','=','confirmed')])
                for rec in recs:
                    history_ids.append((0,0,{
                        'type_apply':rec.type_apply,
                        'total_orders':rec.total_orders,
                        'total_point':rec.total_point,
                        'pos_order_ids':rec.pos_order_ids,
                    }))
            data.history_ids = history_ids


class PosLoyaltyHistoryUpdatePoint(models.Model):
    _name = "pos.loyalty.history.update.point"
    _description = "POS Loyalty History Update Point"

    type_apply = fields.Selection([('plus', 'Plus'),('redeem', 'Redeem')], string='Type', required=1,default='plus')
    total_orders = fields.Float('Total Orders')
    total_point = fields.Float('Total Points')
    pos_order_ids = fields.Many2many('pos.order',string='Order Reference')
    parent_id = fields.Many2one('pos.loyalty.update.point','Parent')