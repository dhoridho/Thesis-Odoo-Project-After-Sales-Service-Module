# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'
 
    emenu_description = fields.Text('Description')
    emenu_price = fields.Float(string='Emenu Price', compute='_compute_emenu_price')

    def _compute_emenu_price(self):
        pricelist = self._context.get('_emenu_pricelist')
        quantity_1 = 1
        partner = False
        for product in self:
            price = product.list_price
            if pricelist:
                price = pricelist._get_emenu_product_price(product, quantity_1, partner)
            product.emenu_price = price

    def _get_emenu_combination_info(self, combination=False, product_id=False, add_qty=1, pricelist=False, parent_combination=False, only_template=False, pos_config=False):
       
        self.ensure_one()
        # get the name before the change of context to benefit from prefetch
        display_name = self.display_name

        quantity = self.env.context.get('quantity', add_qty)
        context = dict(self.env.context, 
                quantity=quantity, 
                pricelist=pricelist.id if pricelist else False, 
                _emenu_pricelist=pos_config.pricelist_id)
        product_template = self.with_context(context)
        combination = combination or product_template.env['product.template.attribute.value']
        if not product_id and not combination and not only_template:
            combination = product_template._get_first_possible_combination(parent_combination)

        if only_template:
            product = product_template.env['product.product']
        elif product_id and not combination:
            product = product_template.env['product.product'].browse(product_id)
        else:
            product = product_template._get_variant_for_combination(combination)

        if product:
            # We need to add the price_extra for the attributes that are not
            # in the variant, typically those of type no_variant, but it is
            # possible that a no_variant attribute is still in a variant if
            # the type of the attribute has been changed after creation.
            no_variant_attributes_price_extra = [
                ptav.price_extra for ptav in combination.filtered(
                    lambda ptav:
                        ptav.price_extra and
                        ptav not in product.product_template_attribute_value_ids
                )
            ]
            if no_variant_attributes_price_extra:
                product = product.with_context(
                    no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra)
                )
            list_price = product.price_compute('list_price')[product.id]
            price = product.emenu_price if pricelist else list_price
            display_name = product.display_name
        else:
            product_template = product_template.with_context(current_attributes_price_extra=[v.price_extra or 0.0 for v in combination])
            list_price = product_template.price_compute('list_price')[product_template.id]
            price = product_template.emenu_price if pricelist else list_price

            combination_name = combination._get_combination_name()
            if combination_name:
                display_name = "%s (%s)" % (display_name, combination_name)

        if pricelist and pricelist.currency_id != product_template.currency_id:
            list_price = product_template.currency_id._convert(
                list_price, pricelist.currency_id, product_template._get_current_company(pricelist=pricelist),
                fields.Date.today()
            )

        price_without_discount = list_price if pricelist and pricelist.discount_policy == 'without_discount' else price
        has_discounted_price = (pricelist or product_template).currency_id.compare_amounts(price_without_discount, price) == 1

        combination_info =  {
            'product_id': product.id,
            'product_template_id': product_template.id,
            'display_name': display_name,
            'price': price,
            'list_price': list_price,
            'has_discounted_price': has_discounted_price,
        }

        partner = self.env.user.partner_id
        company_id = pos_config.company_id
        product = self.env['product.product'].browse(combination_info['product_id']) or self

        tax_display = pos_config.display_sale_price_within_tax and 'total_included' or 'total_excluded'
        fpos = self.env['account.fiscal.position'].get_fiscal_position(partner.id).sudo()
        taxes = fpos.map_tax(product.sudo().taxes_id.filtered(lambda x: x.company_id == company_id), product, partner)

        # The list_price is always the price of one.
        quantity_1 = 1
        combination_info['price'] = self.env['account.tax']._fix_tax_included_price_company(combination_info['price'], product.sudo().taxes_id, taxes, company_id)
        prices = taxes._emenu_compute_all(combination_info['price'], pricelist.currency_id, quantity_1, product, partner)
        price = prices[tax_display]
        if pricelist.discount_policy == 'without_discount':
            combination_info['list_price'] = self.env['account.tax']._fix_tax_included_price_company(combination_info['list_price'], product.sudo().taxes_id, taxes, company_id)
            
            list_price = taxes._emenu_compute_all(combination_info['list_price'], pricelist.currency_id, quantity_1, product, partner)[tax_display]
        else:
            list_price = price
        has_discounted_price = pricelist.currency_id.compare_amounts(list_price, price) == 1

        combination_info.update(
            price=price,
            list_price=list_price,
            has_discounted_price=has_discounted_price,
            price_formated=pos_config.emenu_format_currency(price, currency=pricelist.currency_id)
        )

        return combination_info


class ProductProduct(models.Model):
    _inherit = 'product.product'
 
    emenu_price = fields.Float(string='Emenu Price', compute='_compute_emenu_price')

    def _compute_emenu_price(self):
        pricelist = self._context.get('_emenu_pricelist')
        quantity_1 = 1
        partner = False
        for product in self:
            price = product.list_price
            if pricelist:
                price = pricelist._get_emenu_product_price(product, quantity_1, partner)
            product.emenu_price = price