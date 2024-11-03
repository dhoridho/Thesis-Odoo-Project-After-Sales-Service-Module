# -*- coding: utf-8 -*-
import logging
import werkzeug

from odoo import fields, models, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import slug
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.main import Website
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.addons.sale.controllers.portal import CustomerPortal


logger = logging.getLogger(__name__)
OPG = 5


class OrderDisplay(Website):
    @http.route(['/page/order/display', '/page/order/display/page/<int:page>'], type='http', auth="user", website=True)
    def order_display(self, page=0, search='', opg=False, domain=None, **post):
        # only order display screen access control user should access the page 'Orders'
        if not request.env.user.has_group('pragmatic_odoo_website_order_display.group_order_display_screen'):
            raise werkzeug.exceptions.NotFound()

        if domain is None:
            domain = []
        if opg:
            try:
                opg = int(opg)
            except ValueError:
                opg = OPG
            post["ppg"] = opg
        else:
            opg = OPG

        so = request.env['sale.order'].sudo()
        # usr = request.env['res.users'].sudo().browse(request.uid)

        domain.append(('state', 'in', ['sale', 'progress']))
        url = "/page/order/display"
        so_count = so.search_count(domain)
        pager = request.website.pager(url=url, total=so_count, page=page, step=opg, scope=7, url_args=post)
        orders = so.search(domain, limit=opg, offset=pager['offset'], order="id asc")
        # warehouses = http.request.env['stock.warehouse'].sudo().search_read(domain=[], fields=['name'])
        values = {
            'pager': pager,
            'search_count': so_count,  # common for all searchbox
            'orders': orders,
            # 'warehouses': warehouses,
            # 'wh_id': usr.warehouse_id.id
        }
        return request.render('pragmatic_odoo_website_order_display.order_display', values)

    @http.route('/order/update', type='json', auth='public')
    def order_update(self, order_id, state='sale'):
        so = request.env['sale.order'].sudo()
        so.browse(order_id).update({'state': state})
        return order_id

class CustomerPortalInherit(CustomerPortal):

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done', 'progress', 'ready', 'picked', 'delivered'])
        ]

        searchbar_sortings = {
            'date': {'label': _('Order Date'), 'order': 'date_order desc'},
            'name': {'label': _('Reference'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'state'},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        orders = SaleOrder.search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'default_url': '/my/orders',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("sale.portal_my_orders", values)



