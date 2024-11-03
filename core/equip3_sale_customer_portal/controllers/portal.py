# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.osv import expression
from collections import OrderedDict
from odoo.osv.expression import OR
from odoo.tools import groupby as groupbyelem
from operator import itemgetter
import pytz
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import logging
_logger = logging.getLogger(__name__)

class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', partner.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        StockPicking = request.env['stock.picking']
        if 'picking_count' in counters:
            values['picking_count'] = StockPicking.search_count([
                ('partner_id', 'in', partner_id_list), ('picking_type_code', '=', 'outgoing')
            ]) if StockPicking.check_access_rights('read', raise_exception=False) else 0
        SaleOrder = request.env['sale.order']
        approval_matrix = request.env['ir.config_parameter'].sudo().get_param('is_customer_approval_matrix')
        if partner.customer_rank > 0:
            if 'quotation_count' in counters:
                values['quotation_count'] = SaleOrder.sudo().search_count([
                    ('partner_id', 'in', partner_id_list),
                    ('state', 'not in', ['sale', 'done'])
                ]) if SaleOrder.sudo().check_access_rights('read', raise_exception=False) else 0
            if 'order_count' in counters:
                values['order_count'] = SaleOrder.sudo().search_count([
                    ('partner_id', 'in', partner_id_list),
                    ('state', 'in', ['sale', 'done'])
                ]) if SaleOrder.sudo().check_access_rights('read', raise_exception=False) else 0
            if 'invoice_count' in counters:
                values['invoice_count'] = request.env['account.move'].sudo().search_count([
                    ('partner_id', 'in', partner_id_list),
                    ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
                    ('state', '=', 'posted'),
                    ('payment_state', 'in', ['not_paid', 'partial', 'paid', 'reversed', 'in_payment']),
                ]) if request.env['account.move'].check_access_rights('read', raise_exception=False) else 0
        else:
            if 'quotation_count' in counters:
                if approval_matrix == "True":
                    values['quotation_count'] = SaleOrder.sudo().search_count([
                        ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                        ('state', 'in', ['quotation_approved', 'sent', 'cancel'])
                    ]) if SaleOrder.sudo().check_access_rights('read', raise_exception=False) else 0
                else:
                    values['quotation_count'] = SaleOrder.sudo().search_count([
                        ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                        ('state', 'in', ['sent', 'cancel'])
                    ]) if SaleOrder.sudo().check_access_rights('read', raise_exception=False) else 0
            if 'order_count' in counters:
                values['order_count'] = SaleOrder.sudo().search_count([
                    ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                    ('state', 'in', ['sale', 'done'])
                ]) if SaleOrder.sudo().check_access_rights('read', raise_exception=False) else 0
        return values

    def _prepare_portal_layout_values(self):

        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['is_customer'] = request.env.user.partner_id.is_customer
        values['is_partner_customer'] = request.env.user.partner_id.is_customer
        return values

    @http.route(['/my/delivery_orders', '/my/delivery_orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_delivery_orders(self, page=1, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        StockPicking = request.env['stock.picking']

        partner_id_list = []
        partner_id_list.append(partner.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', partner.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        domain = [
            ('partner_id', 'in', partner_id_list), ('picking_type_code', '=', 'outgoing')
        ]

        # count for pager
        picking_count = StockPicking.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/delivery_orders",
            total=picking_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        do = StockPicking.search(domain, order=False, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'orders': do.sudo(),
            'page_name': 'delivery_order',
            'pager': pager,
            'default_url': '/my/delivery_orders',
        })
        return request.render("equip3_sale_customer_portal.portal_my_delivery_order", values)

    @http.route(['/my/delivery_orders_details/<int:picking_id>'], type='http', auth="public", website=True)
    def portal_delivery_order_page(self, picking_id, access_token=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access('stock.picking', picking_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        if order_sudo:
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_quote_%s' % order_sudo.id)
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_quote_%s' % order_sudo.id] = now
                body = _('Delivery Order viewed by customer %s', order_sudo.partner_id.name)
                _message_post_helper(
                    "stock.picking",
                    order_sudo.id,
                    body,
                    token=order_sudo.access_token,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=order_sudo.user_id.sudo().partner_id.ids,
                )
        picking_id = request.env['stock.picking'].sudo().browse(picking_id)
        state = dict(picking_id.fields_get(
                allfields=['state'])['state']['selection'])[picking_id.state]
        values = {
            'picking': picking_id,
            'state': state,
            'is_portal_user': request.env.user.has_group('base.group_portal'),
            'report_type': 'html',
        }
        values['message'] = message
        return request.render('equip3_sale_customer_portal.delivery_order_portal_template', values)

    @http.route(['/my/quotes', '/my/quotes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_quotes(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']
        approval_matrix = request.env['ir.config_parameter'].sudo().get_param('is_customer_approval_matrix')

        partner_id_list = []
        partner_id_list.append(partner.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', partner.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        if partner.customer_rank > 0:
            domain = [
                ('partner_id', 'in', partner_id_list),
                ('state', 'not in', ['sale', 'done'])
            ]
        else:
            domain = [
                ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
                ('state', 'not in', ['sale', 'done'])
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
        quotation_count = SaleOrder.sudo().search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/quotes",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        quotations = SaleOrder.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_quotations_history'] = quotations.ids[:100]

        values.update({
            'date': date_begin,
            'quotations': quotations.sudo(),
            'page_name': 'quote',
            'pager': pager,
            'default_url': '/my/quotes',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("sale.portal_my_quotations", values)

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ]

        if partner.customer_rank > 0:
            partner_id_list = []
            partner_id_list.append(partner.id)
            partner_obj = request.env['res.partner'].search([('parent_id', '=', partner.id)])
            for child_id in partner_obj:
                partner_id_list.append(child_id.id)

            domain = [
                ('partner_id', 'in', partner_id_list),
                ('state', 'in', ['sale', 'done'])
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
        order_count = SaleOrder.sudo().search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        orders = SaleOrder.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
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

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']
        partner = request.env.user.partner_id

        domain = [('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt'))]

        if partner.customer_rank > 0:
            partner_id_list = []
            partner_id_list.append(partner.id)
            partner_obj = request.env['res.partner'].search([('parent_id', '=', partner.id)])
            for child_id in partner_obj:
                partner_id_list.append(child_id.id)

            domain = [
                ('partner_id', 'in', partner_id_list),
                ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial', 'paid', 'reversed', 'in_payment'])
            ]

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        
        searchbar_inputs = {
            'all': {'input':  'all', 'label': _('Search')},
            'name': {'input': 'name', 'label':   _('Search Invoice')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'payment_state': {'input': 'payment_state', 'label': _('Status')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Invoice Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Invoice Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Invoice Date By Year')},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if partner.is_customer and partner.is_vendor:
            searchbar_filters = {
                'all': {'label': _('All'), 'domain': []},
                'invoices': {'label': _('Invoices'), 'domain': [('move_type', '=', ('out_invoice', 'out_refund'))]},
                'bills': {'label': _('Bills'), 'domain': [('move_type', '=', ('in_invoice', 'in_refund'))]},
            }
            # default filter by value
            if not filterby:
                filterby = 'all'

        elif partner.is_customer and not partner.is_vendor:
            searchbar_filters = {
                'invoices': {'label': _('Invoices'), 'domain': [('move_type', '=', ('out_invoice', 'out_refund'))]},
            }
            # default filter by value
            if not filterby:
                filterby = 'invoices'

        elif not partner.is_customer and partner.is_vendor:
            searchbar_filters = {
                'bills': {'label': _('Bills'), 'domain': [('move_type', '=', ('in_invoice', 'in_refund'))]},
            }
            # default filter by value
            if not filterby:
                filterby = 'bills'

        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]
            
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
        domain += search_domain

        # count for pager
        invoice_count = AccountInvoice.sudo().search_count(domain)
        _logger.info("===========================================================")
        _logger.info(domain)
        _logger.info(invoice_count)
        _logger.info("===========================================================")
        # pager
        pager = portal_pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        
        if groupby == 'payment_state':
            order = "payment_state, %s" % order
        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "invoice_date desc, %s" % order

        # content according to pager and archive selected
        invoices = AccountInvoice.sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])

        grouped_invoices = []
        if groupby == 'payment_state':
            grouped_invoices = [invoices.concat(*g) for _, g in groupbyelem(invoices, itemgetter('payment_state'))]
        elif groupby == 'period_by_day':
            inv_sorted = invoices
            old_formatdate=False
            for inv_rec in inv_sorted:
                formatdate = inv_rec.invoice_date or '-'
                if formatdate:
                    formatdate =  inv_rec.invoice_date.strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_invoices.append([inv_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_invoices)
                        grouped_invoices[len_group-1].append(inv_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_invoices.append([inv_rec])
        elif groupby == 'period_by_month':
            inv_sorted = invoices
            old_formatdate=False
            for inv_rec in inv_sorted:
                formatdate = inv_rec.invoice_date or '-'
                if formatdate:
                    formatdate =  inv_rec.invoice_date.strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_invoices.append([inv_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_invoices)
                        grouped_invoices[len_group-1].append(inv_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_invoices.append([inv_rec])
        elif groupby == 'period_by_year':
            inv_sorted = invoices
            old_formatdate=False
            for inv_rec in inv_sorted:
                formatdate = inv_rec.invoice_date or '-'
                if formatdate:
                    formatdate =  inv_rec.invoice_date.strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_invoices.append([inv_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_invoices)
                        grouped_invoices[len_group-1].append(inv_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_invoices.append([inv_rec])
        else:

            grouped_invoices = [invoices]


        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'grouped_invoices': grouped_invoices,
            'pager': pager,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby':filterby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'search': search,
            'search_in': search_in,
        })
        return request.render("account.portal_my_invoices", values)
