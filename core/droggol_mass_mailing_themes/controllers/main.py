# -*- coding: utf-8 -*-

import json

from odoo import http, fields
from odoo.http import request

from odoo.osv import expression
import babel

from odoo.tools import posix_to_ldml


class DroggolMassMailingThemes(http.Controller):

    @http.route('/droggol_mass_mailing_themes/get_module_state', type='json', auth='user')
    def get_module_state(self, module_name='', **post):
        is_installed = self.module_is_installed(module_name)
        extra_info = {}
        def_name = '_extra_info_' + module_name
        if is_installed and hasattr(self, def_name):
            extra_info = getattr(self, def_name)()
        return {
            'is_installed': is_installed,
            'extra_info': extra_info
        }

    def module_is_installed(self, module_name):
        if module_name:
            domain = [('name', '=', module_name)]
            module = request.env['ir.module.module'].sudo().search(domain)
            if module and module.state in ['installed', 'to install', 'to upgrade']:
                return True
        return False

    def _extra_info_sale(self):
        return {
            'has_pricelist': request.env.user.has_group('product.group_sale_pricelist'),
            'pricelists': request.env['product.pricelist'].search_read([], ['name', 'id']),
            'is_website_sale_installed': self.module_is_installed('website_sale')
        }

    def _get_events(self, domain):
        order = None
        is_website_event = self.module_is_installed('website_event')
        if is_website_event:
            order = 'is_published desc'
        events = request.env['event.event'].search(domain, limit=25, order=order)
        result = events.with_context(lang=request.env.user.lang).read(['name', 'organizer_id', 'date_begin', 'date_end', 'address_id', 'event_type_id', 'website_url'])
        for res_event, event in zip(result, events):
            res_event['start_month'] = res_event.get('date_begin').strftime('%b')
            res_event['start_year'] = res_event.get('date_begin').strftime('%Y')
            res_event['start_day'] = res_event.get('date_begin').strftime('%d')
            # res_event['date_begin'] = tools.format_date(request.env, res_event.get('date_begin').strftime(DEFAULT_SERVER_DATETIME_FORMAT), date_format="DD MMM ")
            # res_event['date_end'] = tools.format_date(request.env, res_event.get('date_end').strftime(DEFAULT_SERVER_DATETIME_FORMAT), date_format="D MMM YY")

            res_event['date_begin'] = self.format_user_lang(res_event.get('date_begin'))
            res_event['date_end'] = self.format_user_lang(res_event.get('date_end'))
            if res_event.get('event_type_id'):
                res_event['event_type'] = res_event.get('event_type_id')[1]
            if res_event.get('organizer_id'):
                res_event['organizer_name'] = res_event.get('organizer_id')[1]
            if event.address_id.country_id:
                res_event['country_name'] = event.address_id.country_id.name
                res_event['street'] = event.address_id.street
                res_event['address'] = event.address_id.name
            if is_website_event:
                cover_properties = json.loads(event.cover_properties)
                res_event['cover_img'] = cover_properties.get('background-image', 'none')[4:-1].strip("'")
        return result

    def format_user_lang(self, value):
        if not value:
            return ''

        lang_code = request.env.user._context.get('lang') or 'en_US'
        lang = request.env['res.lang']._lang_get(lang_code)
        locale = babel.Locale.parse(lang.code)

        value = fields.Datetime.from_string(value)
        value = fields.Datetime.context_timestamp(request.env.user, value)
        strftime_pattern = (u"%s %s" % (lang.date_format, lang.time_format))
        pattern = posix_to_ldml(strftime_pattern, locale=locale)
        pattern = pattern.replace(":ss", "").replace(":s", "")
        return babel.dates.format_datetime(value, format=pattern, locale=locale)

    @http.route('/droggol_mass_mailing_themes/get_event_by_name', type='http', website=True)
    def get_event_by_name(self, term='', **post):
        domain = [('name', 'ilike', (term or ''))]
        if self.module_is_installed('website_event'):
            domain.append(('website_published', '=', True))
        result = self._get_events(domain)
        return json.dumps(result)

    @http.route('/droggol_mass_mailing_themes/get_events_info', type='json', auth='public', website=True)
    def get_events_info(self, domain):
        return {
            'items': self._get_events(domain)
        }

    def _get_blogs(self, domain):
        blogs = request.env['blog.post'].search(domain, limit=25, order='is_published desc')
        result = blogs.with_context(lang=request.env.user.lang).read(['name', 'author_id', 'website_url', 'teaser', 'post_date', 'visits'])
        for res_blog, blog in zip(result, blogs):
            cover_properties = json.loads(blog.cover_properties)
            res_blog['blog_img'] = cover_properties.get('background-image', 'none')[4:-1].strip("'")
            if res_blog.get('author_id'):
                res_blog['author_img'] = '/web/image/blog.post/'+str(blog.id)+'/author_avatar'
                res_blog['author_name'] = res_blog.get('author_id')[1]
                res_blog['post_date'] = res_blog.get('post_date').strftime('%b-%Y')
        return result

    @http.route('/droggol_mass_mailing_themes/get_blog_by_name', type='http', website=True)
    def get_blog_by_name(self, term='', **post):
        domain = [('website_published', '=', True), ('name', 'ilike', (term or ''))]
        result = self._get_blogs(domain)
        return json.dumps(result)

    @http.route('/droggol_mass_mailing_themes/get_blogs_info', type='json', auth='public', website=True)
    def get_blogs_info(self, domain):
        return {
            'items': self._get_blogs(domain)
        }

    def _get_produts_fields(self):
        fields_to_fetch = ['id', 'name', 'display_name', 'description_sale', 'default_code']
        if self.module_is_installed('website_sale'):
            fields_to_fetch.extend(['website_url', 'is_published'])
        return fields_to_fetch

    def get_products(self, domain, order=None, pricelist_id=None):
        PriceListModel = request.env['product.pricelist']
        if pricelist_id:
            pricelist = PriceListModel.browse(pricelist_id)
        else:
            pricelist = PriceListModel.search([], limit=1)
        Model = request.env['product.template'].with_context(pricelist=pricelist.id)
        products = Model.search(domain, limit=25,)
        fields_to_fetch = self._get_produts_fields()
        products_data = products.with_context(lang=request.env.user.lang).read(fields_to_fetch)
        FieldMonetary = request.env['ir.qweb.field.monetary']
        monetary_options = {
            'display_currency': pricelist.currency_id,
        }
        is_rating_active = False
        if self.module_is_installed('website_sale'):
            is_rating_active = request.website.viewref('website_sale.product_comment').active

        for res_product, product in zip(products_data, products):
            combination_info = product._get_combination_info(only_template=True, pricelist=pricelist)
            res_product.update(combination_info)
            res_product['price'] = FieldMonetary.value_to_html(res_product['price'], monetary_options)
            description = res_product.get('description_sale')
            if description and len(description) > 180:
                res_product['description_sale'] = description[:180] + '...'
            elif description:
                res_product['description_sale'] = description
            else:
                res_product['description_sale'] = ''
            if is_rating_active:
                res_product['rating'] = product.rating_get_stats()
            if 'website_url' in fields_to_fetch and not res_product.get('is_published'):
                res_product.pop('website_url', None)
        return products_data

    @http.route('/droggol_mass_mailing_themes/get_product_by_name', type='http', website=True)
    def get_product_by_name(self, term='', **post):
        domains = []
        order = None
        try:
            pricelist_id = int(post['pricelist_id'])
        except ValueError:
            pricelist_id = False
        if self.module_is_installed('website_sale'):
            domains = [request.website.sale_product_domain()]
            if post.get('only_published') == 'published':
                domains.append([('website_published', '=', True)])
            order = 'website_sequence ASC, id desc'
        subdomains = [
            [('name', 'ilike', (term or ''))],
            [('product_variant_ids.default_code', 'ilike', (term or ''))]
        ]
        domains.append(expression.OR(subdomains))
        result = self.get_products(expression.AND(domains), order=order, pricelist_id=pricelist_id)
        return json.dumps(result)

    @http.route('/droggol_mass_mailing_themes/get_products_info', type='json', auth='public', website=True)
    def get_snippet_product_info(self, domain, pricelist_id=None):
        return {
            'items': self.get_products(domain, pricelist_id=pricelist_id),
        }
