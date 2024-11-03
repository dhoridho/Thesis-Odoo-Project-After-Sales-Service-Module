# -*- coding: utf-8 -*-

import base64
import json
import logging

import odoo
from odoo.tools import image_process
from odoo.modules import get_module_path, get_resource_path
from odoo import http, tools
from odoo.http import content_disposition, dispatch_rpc, request, serialize_exception as _serialize_exception, Response

_logger = logging.getLogger(__name__)



class PosEmenuController(http.Controller):
    
    def _format_currency_amount(self, amount, currency_id):
        pre = currency_id.position == 'before'
        symbol = u'{symbol}'.format(symbol=currency_id.symbol or '')
        amount = round(amount)
        amount = f'{amount:,}'
        return u'{pre} {0} {post}'.format(amount, pre=symbol if pre else '', post=symbol if not pre else '')

    @staticmethod
    def emenu_placeholder(image='placeholder.png'):
        image_path = image.lstrip('/').split('/') if '/' in image else ['web', 'static', 'src', 'img', image]
        with tools.file_open(get_resource_path(*image_path), 'rb') as fd:
            return fd.read()

    @http.route([ 
        '/emenu/content/<string:ttype>/<int:id>/<string:field>/<string:filename>'
    ], type='http', auth="public")
    def content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                      filename_field='name', unique=None, filename=None, mimetype=None,
                      download=None, width=0, height=0, crop=False, access_token=None, ttype=None,
                      **kwargs):

        if ttype not in ['product', 'outlet_image']:
            return request.not_found()

        if ttype == 'product':
            model = 'product.template'
        if ttype == 'outlet_image':
            model = 'pos.emenu.outlet.image'

        # other kwargs are ignored on purpose
        res = self._content_image(xmlid=xmlid, model=model, id=id, field=field,
            filename_field=filename_field, unique=unique, filename=filename, mimetype=mimetype,
            download=download, width=width, height=height, crop=crop,
            quality=int(kwargs.get('quality', 0)), access_token=access_token) 
        return res

    def _content_image(self, xmlid=None, model='ir.attachment', id=None, field='datas',
                       filename_field='name', unique=None, filename=None, mimetype=None,
                       download=None, width=0, height=0, crop=False, quality=0, access_token=None,
                       placeholder=None, **kwargs):
        status, headers, image_base64 = request.env['ir.http'].sudo().binary_content(
            xmlid=xmlid, model=model, id=id, field=field, unique=unique, filename=filename,
            filename_field=filename_field, download=download, mimetype=mimetype,
            default_mimetype='image/png', access_token=access_token) 

        return PosEmenuController._content_image_get_response(
            status, headers, image_base64, model=model, id=id, field=field, download=download,
            width=width, height=height, crop=crop, quality=quality,
            placeholder=placeholder)

    @staticmethod
    def _content_image_get_response(
            status, headers, image_base64, model='ir.attachment', id=None,
            field='datas', download=None, width=0, height=0, crop=False,
            quality=0, placeholder='placeholder.png'):
        if status in [301, 304] or (status != 200 and download):
            return request.env['ir.http']._response_by_status(status, headers, image_base64)
        if not image_base64:
            if placeholder is None and model in request.env:
                # Try to browse the record in case a specific placeholder
                # is supposed to be used. (eg: Unassigned users on a task)
                record = request.env[model].sudo().browse(int(id)) if id else request.env[model].sudo()
                placeholder_filename = record._get_placeholder_filename(field=field)
                placeholder_content = PosEmenuController.emenu_placeholder(image=placeholder_filename)
            else:
                placeholder_content = PosEmenuController.emenu_placeholder()
            # Since we set a placeholder for any missing image, the status must be 200. In case one
            # wants to configure a specific 404 page (e.g. though nginx), a 404 status will cause
            # troubles.
            status = 200
            image_base64 = base64.b64encode(placeholder_content)

            if not (width or height):
                width, height = odoo.tools.image_guess_size_from_field_name(field)

        try:
            image_base64 = image_process(image_base64, size=(int(width), int(height)), crop=crop, quality=int(quality))
        except Exception:
            return request.not_found()

        content = base64.b64decode(image_base64)
        headers = http.set_safe_image_headers(headers, content)
        response = request.make_response(content, headers)
        response.status_code = status
        return response
    
    def get_access_token_data(self, access):
        access = access.split('.')
        data = { 'emenu_order_id': False}
        try:
            data['pos_session_id'] = int(access[1].split(':')[0])
            data['pos_config_id'] = int(access[2].split(':')[0])
            data['emenu_order_id'] = int(access[3].split(':')[0])
            data['table_id'] = int(access[4].split(':')[0])
            data['floor_id'] = int(access[5].split(':')[0])
        except Exception as e:
            print('Exception: ', e)
        return data

    def NotFound(self):
        return request.render('equip3_pos_emenu.emenu_page_404', {}) 

    @http.route('/emenu', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def emenu(self, **post):
        return request.redirect('/emenu-404')

    @http.route(['/emenu/redirect/<string:access_token>'], type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def redirect_home(self, access_token=None, **post):
        if not access_token:
            return self.NotFound()

        data = self.get_access_token_data(access_token) 
        domain = [('id','=',data['emenu_order_id'])]
        emenu_order = request.env['pos.emenu.order'].sudo().search(domain, limit=1) 
        if not emenu_order:
            return self.NotFound()

        values = {
            'redirect_url': f'/emenu/home/{access_token}'
        }
        return request.render('equip3_pos_emenu.redirect_home', values)

    @http.route('/emenu/home/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def home(self, access_token, search='', **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()

        data = self.get_access_token_data(access_token) 
        domain = [('id','=',data['emenu_order_id'])]
        emenu_order = PosEmenuOrder.search(domain, limit=1)

        #TODO: IF session is not Open then redirect to Page Not Found (404)
        if emenu_order.pos_session_id.state != 'opened':
            return request.redirect('/emenu-404')

        #TODO: IF status already To Pay then redirect to payment_done page
        if emenu_order.state == 'to_pay':
            return request.redirect(f'/emenu/payment/done/{access_token}')

        pos_config = emenu_order.pos_config_id

        banner_images = [i.url for i in pos_config.emenu_outlet_images_ids]

        categories, products_by_categories = self.get_products_by_categories(pos_config, search)

        has_orders = self.get_lines_by_order_numbers(emenu_order, check=True)

        values = {
            'title': pos_config.name,
            'outlet_name': pos_config.name,
            'banner_images': banner_images,
            'table_name': emenu_order.table_id.name,
            'categories': categories,
            'products_by_categories': products_by_categories,
            'url': f'/emenu/home/{access_token}',
            'search': search,
            'emenu_order': emenu_order,
            'emenu_order_id': emenu_order.id,
            'cart_info': self.cart_info(emenu_order),
            'access_token': access_token,
            'has_orders': has_orders, 
        }

        return request.render('equip3_pos_emenu.emenu_home', values)

    def cart_info(self, emenu_order):
        amount_total = emenu_order.with_context(ctx_state='created').amount_total
        cart_info = {
            'item_count': len(emenu_order.line_ids.filtered(lambda r: r.state == 'created')),
            'amount_total': amount_total,
            'format_amount_total' : self._format_currency_amount(amount_total, emenu_order.currency_id),
        }
        return cart_info

    def get_products_by_categories(self, pos_config, search=''):
        category_ids, products_by_categories = [], []
        PosCategory = request.env['pos.category'].sudo()
        ProductTemplate = request.env['product.template'].sudo().with_context(_emenu_pricelist=pos_config.pricelist_id)

        domain = []
        if pos_config.limit_categories:
            domain += [('id','in', pos_config.iface_available_categ_ids.ids)]
        categ_ids = [x['id'] for x in PosCategory.search_read(domain, ['id'])]

        search_product_ids = []
        search = search.strip()
        if search:
            domain = [('name','ilike', search)]
            search_product_ids = [x['id'] for x in ProductTemplate.search_read(domain, ['id'])]

        if categ_ids:
            select_product_q = '''
                SELECT ARRAY_AGG(pt.id)
                FROM product_template AS pt 
                WHERE pt.pos_categ_id = pc.id
                    AND pt.active = 't' AND pt.available_in_pos = 't'
            '''
            if search:
                if search_product_ids:
                    select_product_q += ' AND pt.id IN (%s) ' % str(search_product_ids)[1:-1]
                else:
                    select_product_q += ' AND pt.id = -1 '
            select_product_q += f' LIMIT 10' # only show 10 products for each category

            request._cr.execute( '''
                SELECT t.categ_id, t.categ_name, t.product_tmpl_ids
                FROM (
                    SELECT
                        pc.id AS categ_id,
                        pc.name AS categ_name,
                        ({select_product_q}) AS product_tmpl_ids
                    FROM pos_category AS pc
                    WHERE pc.id IN ({categ_ids})
                ) AS t
                WHERE t.product_tmpl_ids IS NOT NULL
            '''.format(select_product_q=select_product_q, 
                categ_ids=str(categ_ids)[1:-1]))
            results = request._cr.fetchall()

            for result in results:
                category_id = result[0]
                category_name = result[1]
                product_tmpl_ids = result[2]
                if product_tmpl_ids:
                    products = ProductTemplate.search([('id','in', product_tmpl_ids)])
                    category_ids += [category_id]
                    products_by_categories += [{
                        'category_id': category_id,
                        'category_name': category_name,
                        'products': products,
                    }]

        categories = PosCategory.search([('id','in', category_ids)])

        return categories, products_by_categories

    @http.route('/emenu/product/<string:emenu_order_id>/<string:product_tmpl_id>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def product(self, emenu_order_id, product_tmpl_id, **post):
        emenu_order = request.env['pos.emenu.order'].sudo().search([('id','=',emenu_order_id)], limit=1) 
        pos_config = emenu_order.pos_config_id
        ProductTemplate = request.env['product.template'].sudo().with_context(_emenu_pricelist=emenu_order.pricelist_id)
        product = ProductTemplate.search([('id','=',product_tmpl_id)], limit=1)
        combination = product._get_first_possible_combination()
        combination_info = product._get_emenu_combination_info(combination, pricelist=pos_config.pricelist_id, pos_config=pos_config)
        values = {
            'title': product.name,
            'product': product,
            'emenu_order_id': emenu_order_id,
            'combination_info': combination_info,
        }
        return request.render('equip3_pos_emenu.emenu_product', values)

    @http.route('/emenu/get_product_variant_combination', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def get_product_variant_combination(self, combination):
        values = {
            'combination': combination
        }
        query = '''
            SELECT t.product_product_id, t.combination
            FROM (
                SELECT 
                    product_product_id,
                    ARRAY_AGG(product_template_attribute_value_id) AS combination
                FROM product_variant_combination
                GROUP BY product_product_id
            ) t
            WHERE combination = '{%s}'
        ''' % str(combination)
        request._cr.execute(query)
        result = request._cr.fetchone()
        if result:
            values['product_id'] = result[0]
        return json.dumps(values)

    @http.route('/emenu/cart/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def cart(self, access_token, **post):
        data = self.get_access_token_data(access_token) 
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        emenu_order = PosEmenuOrder.search([('id','=',data['emenu_order_id'])], limit=1) 

        lines_by_categories = self.get_order_line_by_categories_in_cart(emenu_order)
        values = {
            'title': 'Cart',
            'home_url': f'/emenu/home/{access_token}',
            'emenu_order': emenu_order,
            'pos_config': emenu_order.pos_config_id,
            'lines_by_categories': lines_by_categories,
            'process_order_url': f'/emenu/process-order/submit/{emenu_order.id}',
            'access_token': access_token,
        }
        return request.render('equip3_pos_emenu.emenu_cart', values)

    def get_order_line_by_categories_in_cart(self, emenu_order):
        lines_by_categories = []
        PosCategory = request.env['pos.category'].sudo()
        PosEmenuOrderLine = request.env['pos.emenu.order.line'].sudo()
 
        request._cr.execute( '''
            SELECT
                pt.pos_categ_id, ARRAY_AGG(l.id) AS order_line_ids
            FROM pos_emenu_order_line AS l
            INNER JOIN product_product AS pp ON pp.id = l.product_id
            INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
            WHERE l.state = 'created'
                AND l.order_id = {emenu_order_id}
            GROUP by pt.pos_categ_id
        '''.format(emenu_order_id=emenu_order.id, ))
        results = request._cr.fetchall()

        for result in results:
            category_id = result[0]
            line_ids = result[1]
            lines_by_categories += [{
                'pos_categ': PosCategory.search([('id','=',category_id)]),
                'lines': PosEmenuOrderLine.search([('id','in',line_ids)]),
            }]
        return lines_by_categories

    @http.route('/emenu/cart/<string:emenu_order_id>/add', type='json', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def cart_add(self, emenu_order_id, **kw):
        data = json.loads(request.httprequest.data) 
        emenu_order = request.env['pos.emenu.order'].sudo().search([('id','=',int(emenu_order_id))], limit=1)
        ProductProduct = request.env['product.product'].with_context(_emenu_pricelist=emenu_order.pricelist_id).sudo()
        product_id = data['product_id']
        note = data.get('note','').strip()
        is_exist = False
        for line in emenu_order.line_ids:
            if line.product_id.id == product_id and (not line.order_number):
                product = ProductProduct.browse(product_id)
                is_exist = True
                line.write({
                    'price': product.emenu_price,
                    'qty': line.qty + data['qty'],
                    'note': note,
                })

        if not is_exist:
            product = ProductProduct.browse(product_id)
            tax_ids = []
            for tax in product.product_tmpl_id.taxes_id:
                tax_ids += [(4, tax.id)]

            values = {
                'order_id': emenu_order.id,
                'order_number': False,
                'product_id': product_id,
                'qty': data['qty'],
                'price': product.emenu_price,
                'tax_ids': tax_ids,
                'note': note,
                'state': 'created',
                'created_from': 'emenu'
            }
            line = request.env['pos.emenu.order.line'].sudo().create(values)

        request.env.cr.commit()
        cart_info = self.cart_info(emenu_order)
        return {
            'status': 'success',
            'cart_info': cart_info,
        }

    @http.route('/emenu/cart/<string:emenu_order_id>/update', type='json', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def cart_update(self, emenu_order_id, **kw):
        data = json.loads(request.httprequest.data)
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        PosEmenuOrderLine = request.env['pos.emenu.order.line'].sudo()
        emenu_order = PosEmenuOrder.search([('id','=',emenu_order_id)], limit=1)
        pos_config = emenu_order.pos_config_id
        currency_id = emenu_order.currency_id
        if not emenu_order:
            return {'status': 'failed'}
        line = PosEmenuOrderLine.search([('id','=',data['emenu_order_line_id'])], limit=1)

        if not line or (line and line.order_id.id != emenu_order.id):
            return {'status': 'failed'}
        
        deleted = False
        qty = int(data['qty'])
        if qty <= 0:
            line.unlink()
            deleted = True
        else:
            line.write({'qty': qty})

        cart_info = {}
        if not deleted:
            cart_info = self.cart_info(emenu_order)
            cart_info['format_subtotal_incl'] = pos_config.emenu_format_currency(line.subtotal_incl, currency_id)

        return {
            'status': 'success', 
            'data': {
                'qty': qty,
                'amount_total' : emenu_order.amount_total,
                'format_amount_total' : self._format_currency_amount(emenu_order.amount_total, currency_id),
                'cart_info': cart_info,
            }
        }

    @http.route('/emenu/process-order/submit/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def process_order_submit(self, access_token, **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        PosEmenuOrderLine = request.env['pos.emenu.order.line'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()

        domain = [('order_id','=',emenu_order.id), ('state','=','created')]
        domain += [('id','in', post['lines'].split(','))]
        lines = PosEmenuOrderLine.search(domain)
        for line in lines:
            line.write({ 
                'state': 'new_order',
                'order_number': emenu_order.next_order_number,
            })
        emenu_order.write({ 'state': 'new_order' })

        values = {
            'access_token': access_token,
            'emenu_order': emenu_order,
            'type': 'submit',
            'title': 'Submitting your order...',
            'message_title': 'Submitting your order',
            'message_subtitle': 'Do not navigate away from this page!',
            'pageName': 'submit_order',
            'lines': post.get('lines',''),
        }
        return request.render('equip3_pos_emenu.emenu_process_order', values)

    @http.route('/emenu/process-order/submit/check/<string:access_token>', type='json', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def process_order_submit_check(self, access_token, **kw):
        data = json.loads(request.httprequest.data)
        access = self.get_access_token_data(access_token) 
        PosEmenuOrderLine = request.env['pos.emenu.order.line'].sudo()
        validated = True

        domain = [('order_id','=',access['emenu_order_id'])]
        domain += [('id','in', [int(x) for x in data['lines'].split(',')] )]
        lines = PosEmenuOrderLine.search(domain)
        for line in lines:
            if line.state != 'received':
                validated = False
                break

        return {
            'validated': validated,  
        }

    @http.route('/emenu/process-order/processed/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def process_order_processed(self, access_token, **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()

        values = {
            'access_token': access_token,
            'emenu_order': emenu_order,
            'type': 'processed',
            'title': 'Your order is being processed...',
            'message_title': 'Your order is being processed',
            'message_subtitle': 'Please wait until (we serve it to you)',
            'pageName': 'processed_order',
        }
        return request.render('equip3_pos_emenu.emenu_process_order', values)

    @http.route('/emenu/bill/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def bill(self, access_token, **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()

        #TODO: IF session is not Open then redirect to Page Not Found (404)
        if emenu_order.pos_session_id.state != 'opened':
            return request.redirect('/emenu-404')

        #TODO: IF status already To Pay then redirect to payment_done page
        if emenu_order.state == 'to_pay':
            return request.redirect(f'/emenu/payment/done/{access_token}')

        values = {
            'title': 'Order Overview',
            'access_token': access_token,
            'emenu_order': emenu_order,
            'pos_config': emenu_order.pos_config_id,
            'lines_by_order_numbers': self.get_lines_by_order_numbers(emenu_order),
            'url': f'/emenu/bill/{access_token}',
            'home_url': f'/emenu/home/{access_token}',
        }
        return request.render('equip3_pos_emenu.emenu_bill', values)

    def get_lines_by_order_numbers(self, emenu_order, check=False):
        lines_by_order_numbers = []
        PosCategory = request.env['pos.category'].sudo()
        PosEmenuOrderLine = request.env['pos.emenu.order.line'].sudo()
 
        request._cr.execute( '''
            SELECT
                l.order_number , ARRAY_AGG(l.id) AS order_line_ids
            FROM pos_emenu_order_line AS l
            INNER JOIN product_product AS pp ON pp.id = l.product_id
            INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
            WHERE l.state IN ('received', 'to_pay')
                AND l.order_id = {emenu_order_id}
            GROUP by l.order_number
        '''.format(emenu_order_id=emenu_order.id, ))
        results = request._cr.fetchall()
        
        if check:
            if results:
                return True
            return False

        for result in results:
            lines = PosEmenuOrderLine.search([('id','in',result[1])])
            value = {
                'order_number': result[0],
                'lines': lines,
                'created_from': '',
            }
            if lines:
                value['created_from'] = lines[0].created_from

            lines_by_order_numbers += [value]
        return lines_by_order_numbers


    @http.route('/emenu/payment/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def payment(self, access_token, **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()


        #TODO: IF session is not Open then redirect to Page Not Found (404)
        if emenu_order.pos_session_id.state != 'opened':
            return request.redirect('/emenu-404')

        #TODO: IF status already To Pay then redirect to payment_done page
        if emenu_order.state == 'to_pay':
            return request.redirect(f'/emenu/payment/done/{access_token}')

        values = {
            'title': 'Payment',
            'access_token': access_token,
            'emenu_order': emenu_order,
            'bill_url': f'/emenu/bill/{access_token}',
        }
        return request.render('equip3_pos_emenu.emenu_payment', values)

    @http.route('/emenu/payment/submit/<string:access_token>', type='json', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def payment_submit(self, access_token, **kw):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()

        emenu_order.write({ 'state': 'to_pay' })
        request.env.cr.commit()
        return {
            'status': 'success',
        }

    @http.route('/emenu/payment/done/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def payment_done(self, access_token, **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()

        values = {
            'title': 'Payment',
            'access_token': access_token,
            'emenu_order': emenu_order,
            'status': 'done',
            'pageName': 'payment_done',
        }
        
        #TODO: IF status already Paid then redirect to thank you page "payment_done_paid"
        if emenu_order.state == 'paid':
            return request.redirect(f'/emenu/payment/done/paid/{access_token}')

        return request.render('equip3_pos_emenu.emenu_payment', values)

    @http.route('/emenu/payment/done/check/<string:access_token>', type='json', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def payment_done_check(self, access_token, **kw):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        data = json.loads(request.httprequest.data)
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        
        is_already_paid = False
        if emenu_order and emenu_order.state == 'paid':
            is_already_paid = True

        return {
            'is_already_paid': is_already_paid,  
        }

    @http.route('/emenu/payment/done/paid/<string:access_token>', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def payment_done_paid(self, access_token, **post):
        PosEmenuOrder = request.env['pos.emenu.order'].sudo()
        access = self.get_access_token_data(access_token) 
        emenu_order = PosEmenuOrder.search([('id','=',access['emenu_order_id'])], limit=1)
        if not emenu_order:
            return self.NotFound()

        values = {
            'title': 'Payment Success',
            'access_token': access_token,
            'emenu_order': emenu_order,
            'status': 'paid',
        }
        return request.render('equip3_pos_emenu.emenu_payment_paid', values)

    @http.route('/emenu-404', type='http', auth='public', website=True, sitemap=False, csrf=False, methods=['GET','POST'])
    def emenu_404(self, **post):
        values = {
            'title': 'Page not found',
        }
        return request.render('equip3_pos_emenu.emenu_page_404', values)