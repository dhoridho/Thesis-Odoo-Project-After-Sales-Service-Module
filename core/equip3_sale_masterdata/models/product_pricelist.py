from odoo import api, fields, models, tools, _
from datetime import datetime, date
from odoo.exceptions import UserError
from itertools import chain
from odoo.exceptions import ValidationError


class ProductPricelistHistory(models.Model):
    _name = "product.pricelist.history"

    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist", ondelete='cascade')
    logdate = fields.Datetime("Log Date")
    user_id = fields.Many2one('res.users', string="User")
    name = fields.Char("Applicable On")
    method = fields.Char("Method")
    description = fields.Char("Description")
    old_value_text = fields.Char("Old Value Text")
    new_value_text = fields.Char("New Value Text")
    category_id = fields.Many2one('product.category', 'Product Category')
    product_tmpl_id = fields.Many2one(
        'product.template', 'Product', ondelete='cascade')
    product_id = fields.Many2one(
        'product.product', 'Product Variant', ondelete='cascade')
    uom_id = fields.Many2one('uom.uom', 'UoM')
    model = fields.Char("Model")
    pl_id = fields.Integer("ID Pricelist")

    @api.model
    def create(self, vals):
        res = super(ProductPricelistHistory, self).create(vals)
        return res

class Pricelist(models.Model):
    _inherit = "product.pricelist"

    pricelist_history_ids = fields.One2many(
        'product.pricelist.history', 'pricelist_id', 'Pricelist History',
        copy=True)
    from_date = fields.Datetime("From Date")
    to_date = fields.Datetime("To Date")
    company_id = fields.Many2one('res.company', string="Company", readonly=True, default=lambda self: self.env.company)
    customer_category = fields.Many2one('customer.category', string="Customer Category")

    def default_get(self, fields):
        res = super(Pricelist, self).default_get(fields)
        res['company_id'] = self.env.company.id
        return res

    @api.model
    def create(self, vals):
        res = super(Pricelist, self).create(vals)
        if self._name == 'product.pricelist':
            history = self.env['product.pricelist.history'].search([('pricelist_id', '=', False),('model', '=', 'product.pricelist.item')])
            if history:
                for rec in history:
                    rec.pricelist_id = res.id
                    rec.pl_id = res.id
        return res

    def write(self,vals):
        res = super(Pricelist, self).write(vals)
        if self._name == 'product.pricelist':
            history = self.env['product.pricelist.history'].search([('pricelist_id', '=', False),('model', '=', 'product.pricelist.item')])
            if history:
                for rec in history:
                    rec.pricelist_id = self.id
                    rec.pl_id = self.id
        return res

    def unlink(self):
        if self._name == 'product.pricelist':
            if self.pricelist_history_ids:
                self.env.cr.execute("DELETE FROM product_pricelist_history WHERE id IN %s", [tuple(self.pricelist_history_ids.ids)])
        return super(Pricelist, self).unlink()

    def action_filter_history(self):
        history_obj = self.env['product.pricelist.history']
        for res in self:
            list = history_obj.search([('pl_id', '=', res.id)])
            for i in list:
                i.pricelist_id = res.id
            if res.from_date and res.to_date:
                list_history = history_obj.search([('pl_id', '=', res.id),'|',('logdate', '<', res.from_date),('logdate', '>', res.to_date)])
                for rec in list_history:
                    rec.pricelist_id = False

    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        context = dict(self.env.context) or {}
        if 'order_line' in context:
            self.ensure_one()
            if not date:
                date = self._context.get('date') or fields.Datetime.now()
            if not uom_id and self._context.get('uom'):
                uom_id = self._context['uom']
            elif not uom_id and not self._context.get('uom'):
                uom_id = [item[0].with_context(uom=uom_id) for item in products_qty_partner][0].uom_id.id
            if uom_id:
                # rebrowse with uom if given
                products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
                products_qty_partner = [(products[index], data_struct[1], data_struct[2]) for index, data_struct in enumerate(products_qty_partner)]
            else:
                products = [item[0] for item in products_qty_partner]

            if not products:
                return {}

            categ_ids = {}
            for p in products:
                categ = p.categ_id
                while categ:
                    categ_ids[categ.id] = True
                    categ = categ.parent_id
            categ_ids = list(categ_ids)

            is_product_template = products[0]._name == "product.template"
            if is_product_template:
                prod_tmpl_ids = [tmpl.id for tmpl in products]
                # all variants of all products
                prod_ids = [p.id for p in
                            list(chain.from_iterable([t.product_variant_ids for t in products]))]
            else:
                prod_ids = [product.id for product in products]
                prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

            items = self._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids)
            if items:
                items = items.filtered(lambda x:x.pricelist_uom_id.id == uom_id)

            results = {}
            for product, qty, partner in products_qty_partner:
                results[product.id] = 0.0
                suitable_rule = False

                # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
                # An intermediary unit price may be computed according to a different UoM, in
                # which case the price_uom_id contains that UoM.
                # The final price will be converted to match `qty_uom_id`.
                qty_uom_id = uom_id
                qty_in_product_uom = qty
                if qty_uom_id != product.uom_id.id:
                    try:
                        qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
                    except UserError:
                        # Ignored - incompatible UoM in context, use default product UoM
                        pass

                # if Public user try to access standard price from website sale, need to call price_compute.
                # TDE SURPRISE: product can actually be a template
                price = product.price_compute('list_price')[product.id]

                price_uom = self.env['uom.uom'].browse([qty_uom_id])
                for rule in items:
                    if rule.pricelist_uom_id:
                        if rule.pricelist_uom_id.id != price_uom.id:
                            continue
                    if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                        continue
                    if is_product_template:
                        if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                            continue
                        if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                            # product rule acceptable on template if has only one variant
                            continue
                    else:
                        if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                            continue
                        if rule.product_id and product.id != rule.product_id.id:
                            continue

                    if rule.categ_id:
                        cat = product.categ_id
                        while cat:
                            if cat.id == rule.categ_id.id:
                                break
                            cat = cat.parent_id
                        if not cat:
                            continue

                    if rule.base == 'pricelist' and rule.base_pricelist_id:
                        price_tmp = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], date, uom_id)[product.id][0]  # TDE: 0 = price, 1 = rule
                        price = rule.base_pricelist_id.currency_id._convert(price_tmp, self.currency_id, self.env.company, date, round=False)
                    else:
                        # if base option is public price take sale price else cost price of product
                        # price_compute returns the price in the context UoM, i.e. qty_uom_id
                        price = product.price_compute(rule.base)[product.id]

                    if price is not False:
                        price = product.currency_id._convert(price, self.currency_id, self.company_id, date)
                        price = rule._compute_price(price, price_uom, product, quantity=qty, partner=partner)
                        suitable_rule = rule
                    break
                # # Final price conversion into pricelist currency
                # if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                #     if suitable_rule.base == 'standard_price':
                #         cur = product.cost_currency_id
                #     else:
                #         cur = product.currency_id
                #     price = cur._convert(price, self.currency_id, self.env.company, date, round=False)
                #
                # if not suitable_rule:
                #     cur = product.currency_id
                #     price = cur._convert(price, self.currency_id, self.env.company, date, round=False)
                # if suitable_rule and suitable_rule.compute_price == 'fixed':
                #     price = suitable_rule.fixed_price
                results[product.id] = (price, suitable_rule and suitable_rule.id or False)
            return results
        else:
            return super(Pricelist, self)._compute_price_rule(products_qty_partner, date=date, uom_id=uom_id)

    @api.constrains('customer_category')
    def _check_existing_record(self):
        for record in self:
            if record.customer_category:
                pricelist_customer_category = self.search([('id', '!=', record.id), ('customer_category', 'ilike', record.customer_category.id)], limit=1)
                if pricelist_customer_category:
                    raise ValidationError("Data can't be the same like other pricelist !")

    @api.onchange('customer_category')
    def set_available_customer_category(self):
        domain = [('company_id','=', self.company_id.id)]
        available_category = self.env['customer.category'].sudo().search(domain)
        return {'domain': {'customer_category': [('id', 'in', available_category.ids)]}}


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    new_price = fields.Char("test")
    pricelist_uom_id = fields.Many2one('uom.uom', string="Pricelist UoM")
    type_surcharge = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed'),
    ], string="Type", default='fixed', required=True)
    base_price_info = fields.Monetary(currency_field="currency_id", string="Price", compute="_compute_base_price_info", store=True)
    min_quantity = fields.Float(
        'Min. Quantity', default=1, digits="Product Unit Of Measure",
        help="For the rule to apply, bought/sold quantity must be greater "
             "than or equal to the minimum quantity specified in this field.\n"
             "Expressed in the default unit of measure of the product.")

    @api.depends('base','applied_on','product_tmpl_id','product_id','pricelist_uom_id','currency_id','compute_price','base_pricelist_id','product_tmpl_id.standard_price','product_tmpl_id.list_price','product_id.standard_price','product_id.lst_price')
    def _compute_base_price_info(self):
        for rec in self:
            rec.base_price_info = 0
            date = fields.Datetime.now()
            qty = 1
            base_price_info = 0
            # for fixing issue master template
            if not rec.company_id and not rec.pricelist_id.company_id:
                rec.pricelist_id.company_id = self.env.company.id
                rec.pricelist_id.currency_id = self.env.company.currency_id.id
                rec.company_id = self.env.company.id
                rec.currency_id = self.env.company.currency_id.id
            ###################################
            if rec.applied_on == '1_product' and rec.product_tmpl_id and rec.compute_price == 'formula':
                if rec.pricelist_uom_id:
                    if rec.pricelist_uom_id.id != rec.product_tmpl_id.uom_id.id:
                        qty = rec.pricelist_uom_id._compute_quantity(1, rec.product_tmpl_id.uom_id)
                if rec.base == 'list_price':
                    base_price_info = rec.product_tmpl_id.currency_id._convert(rec.product_tmpl_id.list_price, rec.currency_id, rec.company_id, date)
                elif rec.base == 'standard_price':
                    base_price_info = rec.product_tmpl_id.currency_id._convert(rec.product_tmpl_id.standard_price, rec.currency_id, rec.company_id, date)
                else:
                    if rec.base_pricelist_id:
                        base_price_info = rec.base_pricelist_id.with_context(order_line=True)._compute_price_rule([(rec.product_tmpl_id, 1, self.env.user.partner_id)], date, rec.pricelist_uom_id or rec.product_tmpl_id.uom_id.id)[rec.product_tmpl_id.id][0]
                        if rec.base_pricelist_id.currency_id != rec.currency_id:
                            base_price_info = rec.base_pricelist_id.currency_id._convert(rec.base_price_info, rec.currency_id, rec.company_id, date)
                rec.base_price_info = base_price_info * qty
            if rec.applied_on == '0_product_variant' and rec.product_id and rec.compute_price == 'formula':
                if rec.pricelist_uom_id:
                    if rec.pricelist_uom_id.id != rec.product_id.uom_id.id:
                        qty = rec.pricelist_uom_id._compute_quantity(1, rec.product_id.uom_id)
                if rec.base == 'list_price':
                    base_price_info = rec.product_id.currency_id._convert(rec.product_id.lst_price, rec.currency_id, rec.company_id, date)
                elif rec.base == 'standard_price':
                    base_price_info = rec.product_id.currency_id._convert(rec.product_id.standard_price, rec.currency_id, rec.company_id, date)
                else:
                    if rec.base_pricelist_id:
                        base_price_info = rec.base_pricelist_id.with_context(order_line=True)._compute_price_rule([(rec.product_id, 1, self.env.user.partner_id)], date, rec.pricelist_uom_id or rec.product_id.uom_id.id)[rec.product_id.id][0]
                        if rec.base_pricelist_id.currency_id != rec.currency_id:
                            base_price_info = rec.base_pricelist_id.currency_id._convert(rec.base_price_info, rec.currency_id, rec.company_id, date)
                rec.base_price_info = base_price_info * qty




    @api.onchange('price_round')
    def _onchange_price_round(self):
        if self.price_round < 0 :
            raise ValidationError('Rounding method must be positive')
            
    @api.constrains('applied_on','pricelist_uom_id','min_quantity','date_start','date_end')
    def _check_same_pricelist_rule(self):
        for i in self:
            domain = [
                ('applied_on','=',i.applied_on),
                ('min_quantity','=',i.min_quantity),
                ('pricelist_id','=',i.pricelist_id.id),
                ('id','!=',i.id),
            ]
            if i.pricelist_uom_id:
                domain += [('pricelist_uom_id','=',i.pricelist_uom_id.id)]
            if i.applied_on == '0_product_variant':
                domain += [('product_id','=',i.product_id.id)]
            elif i.applied_on == '1_product':
                domain += [('product_tmpl_id','=',i.product_tmpl_id.id)]
            elif i.applied_on == '2_product_category':
                domain += [('categ_id','=',i.categ_id.id)]

            same_pricelist_rule = self.search(domain)
            if not i.date_start and not i.date_end:
                if same_pricelist_rule:
                    raise ValidationError(_("There are the same price rules that are running on the same date"))
            elif i.date_start and not i.date_end:
                if same_pricelist_rule.filtered(lambda p:not p.date_end or p.date_end >= i.date_start):
                    raise ValidationError(_("There are the same price rules that are running on the same date"))
            elif not i.date_start and i.date_end:
                if same_pricelist_rule.filtered(lambda p:not p.date_start or p.date_start <= i.date_end):
                    raise ValidationError(_("There are the same price rules that are running on the same date"))
            elif i.date_start and i.date_end:
                if same_pricelist_rule.filtered(
                    lambda p:
                        (p.date_start and p.date_end and p.date_end >= i.date_start and p.date_end <= i.date_end) or 
                        (p.date_start and p.date_end and p.date_start >= i.date_start and p.date_start <= i.date_end) or
                        (not p.date_start and p.date_end and p.date_end >= i.date_start) or 
                        (not p.date_end and p.date_start and p.date_start >= i.date_start) or
                        (not p.date_start and not p.date_end)
                    ):
                    raise ValidationError(_("There are the same price rules that are running on the same date"))

    @api.constrains('date_start','date_end')
    def _check_date_start_date_end(self):
        for i in self:
            if i.date_start and i.date_end:
                if i.date_start > i.date_end:
                    raise ValidationError(_("The start date should be before the end date"))

    @api.constrains('fixed_price', 'minimum_price', 'maximum_price')
    def _check_lower_greater_fixed_price(self):
        for i in self:
            if i.fixed_price and i.minimum_price and i.maximum_price:
                if i.fixed_price > i.maximum_price:
                    raise ValidationError('The Fixed price should be lower than the maximum price')
                if i.fixed_price < i.minimum_price:
                    raise ValidationError('The Fixed price should be greater than the minimum price')
            
            if i.minimum_price or i.maximum_price:
                if not i.minimum_price:
                    if i.fixed_price > i.maximum_price:
                        raise ValidationError('The Fixed price should be lower than the maximum price')
                if not i.maximum_price:
                    if i.fixed_price < i.minimum_price:
                        raise ValidationError('The Fixed price should be greater than the minimum price')
    
    @api.constrains('minimum_price', 'maximum_price')
    def _check_is_greater_minimum_price(self):
        for i in self:
            if i.minimum_price and i.maximum_price:
                if i.minimum_price > i.maximum_price:
                    raise ValidationError('The minimum price should be lower than the maximum price')

    @api.constrains('applied_on','pricelist_uom_id','min_quantity','date_start','date_end')
    def _check_same_pricelist_rule(self):
        for i in self:
            domain = [
                ('applied_on','=',i.applied_on),
                ('min_quantity','=',i.min_quantity),
                ('pricelist_id','=',i.pricelist_id.id),
                ('id','!=',i.id),
            ]
            if i.pricelist_uom_id:
                domain += [('pricelist_uom_id','=',i.pricelist_uom_id.id)]
            if i.applied_on == '0_product_variant':
                domain += [('product_id','=',i.product_id.id)]
            elif i.applied_on == '1_product':
                domain += [('product_tmpl_id','=',i.product_tmpl_id.id)]
            elif i.applied_on == '2_product_category':
                domain += [('categ_id','=',i.categ_id.id)]

            same_pricelist_rule = self.search(domain)
            if not i.date_start and not i.date_end:
                if same_pricelist_rule:
                    raise ValidationError(_("There are the same price rules that are running on the same date"))
            elif i.date_start and not i.date_end:
                if same_pricelist_rule.filtered(lambda p:not p.date_end or p.date_end >= i.date_start):
                    raise ValidationError(_("There are the same price rules that are running on the same date"))
            elif not i.date_start and i.date_end:
                if same_pricelist_rule.filtered(lambda p:not p.date_start or p.date_start <= i.date_end):
                    raise ValidationError(_("There are the same price rules that are running on the same date"))
            elif i.date_start and i.date_end:
                if same_pricelist_rule.filtered(
                    lambda p:
                        (p.date_start and p.date_end and p.date_end >= i.date_start and p.date_end <= i.date_end) or 
                        (p.date_start and p.date_end and p.date_start >= i.date_start and p.date_start <= i.date_end) or
                        (not p.date_start and p.date_end and p.date_end >= i.date_start) or 
                        (not p.date_end and p.date_start and p.date_start >= i.date_start) or
                        (not p.date_start and not p.date_end)
                    ):
                    raise ValidationError(_("There are the same price rules that are running on the same date"))

    @api.constrains('date_start','date_end')
    def _check_date_start_date_end(self):
        for i in self:
            if i.date_start and i.date_end:
                if i.date_start > i.date_end:
                    raise ValidationError(_("The start date should be before the end date"))

    @api.model
    def create(self, vals):
        res = super(ProductPricelistItem, self).create(vals)
        if self._name == 'product.pricelist.item':
            history_obj = self.env['product.pricelist.history']
            history_obj.create({
                "logdate": datetime.now(),
                "user_id": self.env.user.id,
                "name": res.name,
                "method": 'create',
                "description": 'Price',
                "old_value_text": "",
                "new_value_text": str(res.price),
                "model": 'product.pricelist.item',
            })
        return res

    def write(self, vals):
        if self._name == 'product.pricelist.item':
            condition = 'fixed_price' in vals or 'percent_price' in vals or 'price_discount' in vals or 'price_surcharge' in vals

            old_price_dict = {}

            if condition:
                for item in self:
                    old_price_dict[item.id] = item.price
            
            res = super(ProductPricelistItem, self).write(vals)

            if condition:
                for item in self:
                    if old_price_dict.get(item.id, '') == item.price:
                        continue
                    self.env['product.pricelist.history'].create({
                        "logdate": datetime.now(),
                        "user_id": self.env.user.id,
                        "name": item.name,
                        "method": 'write',
                        "description": 'Price',
                        "old_value_text": old_price_dict.get(item.id, ''),
                        "new_value_text": item.price,
                        "model": 'product.pricelist.item',
                    })
            return res
        return super(ProductPricelistItem, self).write(vals)

    def unlink(self):
        if self._name == 'product.pricelist.item':
            for res in self:
                name = res.name
                history_obj = self.env['product.pricelist.history']
                history_obj.create({
                    "logdate": datetime.now(),
                    "user_id": self.env.user.id,
                    "name": name,
                    "method": 'unlink',
                    "description": '',
                    "old_value_text": '',
                    "new_value_text": '',
                    "model": 'product.pricelist.item',
                })
        res = super(ProductPricelistItem, self).unlink()
        return res

    def _compute_price(self, price, price_uom, product, quantity=1.0, partner=False):
        """Compute the unit price of a product in the context of a pricelist application.
           The unused parameters are there to make the full context available for overrides.
        """
        self.ensure_one()
        product_price = price
        convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))
        if self.compute_price == 'fixed':
            price = self.fixed_price
        elif self.compute_price == 'percentage':
            price = (price - (price * (self.percent_price / 100))) or 0.0
        else:
            # complete formula
            price_limit = price
            price = (price - (price * (self.price_discount / 100))) or 0.0
            if self.price_round:
                price = tools.float_round(price, precision_rounding=self.price_round)

            if self.price_surcharge:
                price_surcharge = self.price_surcharge
                if self.type_surcharge == 'percentage':
                    price_surcharge = product_price * (self.price_surcharge/100)
                price_surcharge = convert_to_price_uom(price_surcharge)
                price += price_surcharge

            if self.price_min_margin:
                price_min_margin = convert_to_price_uom(self.price_min_margin)
                price = max(price, price_limit + price_min_margin)

            if self.price_max_margin:
                price_max_margin = convert_to_price_uom(self.price_max_margin)
                price = min(price, price_limit + price_max_margin)
        return price

    @api.depends('applied_on', 'categ_id', 'product_tmpl_id', 'product_id', 'compute_price', 'fixed_price', \
                 'pricelist_id', 'percent_price', 'price_discount', 'price_surcharge', 'type_surcharge')
    def _get_pricelist_item_name_price(self):
        res = super()._get_pricelist_item_name_price()
        for item in self:
            if item.compute_price == 'percentage':
                item.price = _("Sales Price - %s %% discount", item.percent_price)
            if item.compute_price == 'formula':
                if item.type_surcharge == 'percentage':
                    item.price = _("%(base)s + %(price)s %% surcharge", base=dict(self._fields['base'].selection).get(item.base), price=item.price_surcharge)
                else:
                    item.price = _("%(base)s + %(price)s surcharge", base=dict(self._fields['base'].selection).get(item.base), price=item.price_surcharge)

        return res

    @api.onchange('applied_on','product_tmpl_id','product_id')
    def set_product_uom(self):
        for rec in self:
            if rec.applied_on not in ('1_product','0_product_variant'):
                rec.pricelist_uom_id = False
            elif rec.applied_on == '1_product':
                if rec.product_id:
                    rec.product_id = False
                    rec.product_tmpl_id = False
                if rec.product_tmpl_id:
                    rec.pricelist_uom_id = rec.product_tmpl_id.uom_id.id
                else:
                    rec.pricelist_uom_id = False
            elif rec.applied_on == '0_product_variant':
                if rec.product_id:
                    rec.pricelist_uom_id = rec.product_id.uom_id.id
                else:
                    rec.pricelist_uom_id = False

    @api.onchange('compute_price')
    def set_default_base(self):
        # default py gak jalan, pakai default get jg sama
        for rec in self:
            if rec.compute_price == 'formula':
                rec.base = 'standard_price'
