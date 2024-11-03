# -*- coding: utf-8 -*-
from collections import OrderedDict
from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.osv.expression import OR

class CustomerPortal(CustomerPortal):
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        sale_order_line = http.request.env['sale.order.line']
        purchase_order_line = http.request.env['purchase.order.line']
        stock_picking = request.env['stock.picking'].sudo().search([
            ('picking_type_code', '=', 'incoming'),
            ('state' ,'=', 'done'),
            ('owner_id', '=', partner.id)
            ])
        if partner.id == 3:
            domain = [
                ('order_id.is_consignment','!=',False)
            ]
            domain_po = [
                ('order_id.is_consignment','!=',False)
            ]
        else:
            domain = [
                ('order_id.is_consignment','!=',False),
                ('order_id.partner_id', '=', partner.id)
            ]
            domain_po = [
                ('order_id.is_consignment','!=',False),
                ('order_id.picking_ids', 'in', (stock_picking.ids))
            ]

        product_obj = request.env['product.product']
        line_ids = request.env['purchase.order.line'].sudo().search([
            ('order_id.is_consignment', '!=', False),
            ('state', 'in', ['purchase', 'done'])
        ])

        if line_ids:
            values['owner_count'] = purchase_order_line.sudo().search_count(domain_po)
            values['picking_count'] = sale_order_line.sudo().search_count(domain)
            values['consignment_products'] = len(list(line_ids))
            values['partner_id'] = partner
        else:
            values['owner_count'] = 0
            values['picking_count'] = 0
            values['consignment_products'] = 0
            values['partner_id'] = partner
        return values

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        sale_order_line = request.env['sale.order.line']
        if partner.id != 3:
            sale_order_line_count = sale_order_line.sudo().search_count([
                ('order_id.is_consignment','!=',False),
                ('partner_id_product', '=', partner.id)
            ])
        else:
            sale_order_line_count = sale_order_line.sudo().search_count([
                ('order_id.is_consignment','!=',False)
            ])
        product_obj = request.env['product.product']

        line_ids = request.env['purchase.order.line'].search([
            ('order_id.is_consignment', '=', True),
            ('state', 'in', ['purchase', 'done'])
        ])
        stock_picking = request.env['stock.picking'].sudo().search([
            ('picking_type_code', '=', 'incoming'),
            ('state' ,'=', 'done'),
            ('owner_id', '=', partner.id)
        ])
        consignment_owner = request.env['purchase.order.line'].sudo().search_count([
            ('order_id.is_consignment', '!=', False),
            ('state', 'in', ['purchase', 'done']),
            ('order_id.picking_ids', 'in', (stock_picking.ids))
        ])
        if line_ids:
            consignment_products = len(list(line_ids))
        else:
            consignment_products = 0
        values.update({
            'picking_count': sale_order_line_count,
            'consignment_products':consignment_products,
            'owner_count' : consignment_owner,
            'partner_id' : partner
        })
        return values

    @http.route(['/my/consignment_pickings', '/my/consignment_pickings/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_consignment_pickings(self, page=1, filterby=None, sortby=None, search=None, search_in='content', **kw):
#         response = super(CustomerPortal, self)
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        picking_obj = request.env['sale.order.line']
        if partner.id != 3:
            domain = [
                ('order_id.is_consignment','!=',False),
                ('order_id.partner_id', '=', partner.id)
            ]
        else:
            domain = [
                ('order_id.is_consignment','!=',False)
            ]
        # count for pager
        picking_count = picking_obj.sudo().search_count(domain)

       
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        
       

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'product_id': {'input': 'product_id', 'label': _('Search in Product')},
        }
        
        if search and search_in:
            search_domain = []
            if search_in in ('product_id', 'all'):
                search_domain = OR([search_domain, [('product_id', 'ilike', search)]])
            domain += search_domain
        # pager
        pager = portal_pager(
            url="/my/consignment_pickings",
            url_args={'sortby': sortby,'filterby': filterby},
            total=picking_count,
            page=page,
            step=self._items_per_page
        )

        print ("*************************",domain)
        # content according to pager and archive selected
        pickings = picking_obj.sudo().search(domain)
        values.update({
            'partner' : partner,
            'pickings': pickings,
            'page_name': 'consignment_picking',
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'filterby': filterby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'pager': pager,
            'default_url': '/my/consignment_pickings',
        })
        return request.render("odoo_consignment_process.display_stock_pickings_consignment", values)

    @http.route(['/my/consignment_owner', '/my/consignment_owner/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_consignment_owner(self, page=1, filterby=None, sortby=None, search=None, search_in='content', **kw):
#         response = super(CustomerPortal, self)
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        picking_obj = request.env['purchase.order.line']
        stock_picking = request.env['stock.picking'].sudo().search([
            ('picking_type_code', '=', 'incoming'),
            ('state' ,'=', 'done'),
            ('owner_id', '=', partner.id)
        ])
        if partner.id != 3:
            domain = [
                ('order_id.is_consignment','!=',False),
                ('order_id.picking_ids', 'in', (stock_picking.ids))
            ]
        else:
            domain = [
                ('order_id.is_consignment','!=',False)
            ]
        so_obj = request.env['sale.order.line']
        if partner.id != 3:
            domain_so = [
                ('order_id.is_consignment','!=',False),
                ('partner_id_product', '=', partner.id)
            ]
        else:
            domain_so = [
                ('order_id.is_consignment','!=',False)
            ]
        sale_order_line = so_obj.sudo().search(domain_so)
        # count for pager
        picking_count = picking_obj.sudo().search_count(domain)

       
        
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }
        
       

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'product_id': {'input': 'product_id', 'label': _('Search in Product')},
        }
        
        if search and search_in:
            search_domain = []
            if search_in in ('product_id', 'all'):
                search_domain = OR([search_domain, [('product_id', 'ilike', search)]])
            domain += search_domain
        # pager
        pager = portal_pager(
            url="/my/consignment_owner",
            url_args={'sortby': sortby,'filterby': filterby},
            total=picking_count,
            page=page,
            step=self._items_per_page
        )

        print ("*************************",domain)
        # content according to pager and archive selected
        pickings = picking_obj.sudo().search(domain)
        values.update({
            'sale_order_line' : sale_order_line,
            'partner' : partner,
            'pickings': pickings,
            'page_name': 'consignment_owner',
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'filterby': filterby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'pager': pager,
            'default_url': '/my/consignment_owner',
        })
        return request.render("odoo_consignment_process.display_stock_pickings_consignment_owner", values)
    
    @http.route(['/my/consignment_product_list', '/my/consignment_product_list/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_consigment_products(self, page=1, filterby=None, sortby=None, search=None, search_in='content', **kw):
#         response = super(CustomerPortal, self)
        values = self._prepare_portal_layout_values()        
        picking_obj = http.request.env['purchase.order.line']
        domain = [
            ('order_id.is_consignment','!=',False),
            ('state', 'in', ['purchase', 'done'])
        ]
        sol_object = request.env['sale.order.line']
        domain_sol = [('order_id.is_consignment','!=',False)]
        # count for pager
        picking_count = picking_obj.sudo().search_count(domain)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
        }

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'name': {'input': 'name', 'label': _('Search in Name')},
            'default_code': {'input': 'default_code', 'label': _('Search in Internal Reference')},
        }
        if search and search_in:
            search_domain = []
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('default_code', 'all'):
                search_domain = OR([search_domain, [('default_code','ilike',search)]])
            domain += search_domain


        # content according to pager and archive selected
        pager = portal_pager(
            url="/my/consignment_product_list",
            url_args={'sortby': sortby,'filterby': filterby},
            total=picking_count,
            page=page,
            step=self._items_per_page
        )


        # content according to pager and archive selected
        consignment_products = picking_obj.sudo().search(domain, limit=self._items_per_page, offset=pager['offset'])
        sol_items = sol_object.sudo().search(domain_sol)

        values.update({
            'consignment_products': consignment_products,
            'sol_items' : sol_items,
            'page_name': 'consignment_product_page',
            'searchbar_inputs': searchbar_inputs,
            'search_in': search_in,
            'filterby': filterby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'pager': pager,
            'default_url': '/my/consignment_product_list',
        })
        return request.render("odoo_consignment_process.display_consignment_product_consignment", values)

    @http.route(['/my/consignment_pickings/<model("purchase.order"):order>'], type='http', auth="user", website=True)
    def my_consignment_picking(self, order=None, access_token=None, **kw):
        return request.render("odoo_consignment_process.display_my_consignment_detail_consignment", {'order': order, 'token': access_token,})

    @http.route(['/my/sale_order/<model("sale.order"):sale_order>'], type='http', auth="user", website=True)
    def my_sale_order(self, sale_order=None, access_token=None, **kw):
        return request.render("odoo_consignment_process.display_sale_order_inherit", {'sale_order': sale_order, 'token': access_token,})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
