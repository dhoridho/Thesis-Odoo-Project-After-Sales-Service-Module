# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import http, fields
from odoo.http import request, Response, route
import json
import base64
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.website.controllers.main import Website
from odoo.tools import date_utils, groupby as groupbyelem

from odoo import fields, api, SUPERUSER_ID, _
from xlrd import open_workbook
from dateutil.relativedelta import relativedelta
from odoo.osv.expression import AND,OR
from operator import itemgetter
from collections import OrderedDict
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo.addons.purchase.controllers.portal import CustomerPortal
from odoo.addons.sh_po_tender_portal.controllers.portal import TenderRFQPOrtal
# from ...equip3_purchase_other_operation.controllers.portal import PurchaseRFQPortal
from ...sh_rfq_portal.controllers.portal import PurchaseRFQPortal
from ...sh_po_tender_portal.controllers.portal import TenderPortal
import base64
import csv
import io
import os
from io import BytesIO, TextIOWrapper
from odoo import models, fields, api, _
from odoo.exceptions import Warning, AccessError, MissingError, UserError, ValidationError
from datetime import datetime, date, timedelta
from odoo.addons.sh_vendor_signup.controllers.main import CreateVendor
import pytz

class Website(Website):
    def _login_redirect(self, uid, redirect=None):
        res = super()._login_redirect(uid, redirect=redirect)
        if request.params.get('login_success') and res in ['/web','/shop','/my']:
            user_id = request.env['res.users'].sudo().browse(uid)
            partner_id = user_id.partner_id
            if not partner_id.is_customer and partner_id.is_vendor:
                return '/tender/dashboard'
        return res

class ChangeVendorPricelist(http.Controller):

    @http.route(['/vendor_pricelist/<int:quote_id>'], type='http', auth="public", website=True)
    def portal_my_vendor_pricelist_form(self, quote_id, report_type=None, access_token=None, message=False,
                                        download=False, **kw):
        quote_sudo = request.env['product.supplierinfo'].sudo().browse(quote_id)
        values = {
            'token': access_token,
            'vendor_pricelist': quote_sudo,
            'vp_id': True,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.name.id,
            'report_type': 'html',
        }
        return request.render('equip3_purchase_vendor_portal.vendor_pricelist_form_view_new', values)


class CreateVendorPricelist(http.Controller):

    @http.route(['/vendor_pricelist'], type='http', auth="public", website=True)
    def create_vendor_pricelist(self, **post):
        quote_msg = {}
        emails = []
        image = 0
        multi_users_value = [0]
        contacts = []

        if post:
            changes = post.get('changes', False)
            changes_id = post.get('changes_id', False)
            vendor_product_name = post.get('vendor_product_name', False)
            vendor_product_code = post.get('vendor_product_code', False)
            delay = post.get('delivery_lead_time', False)
            qty = post.get('quantity', False)
            unit_price = post.get('unit_price', False)
            validity_start = post.get('validity_start', False)
            validity_end = post.get('validity_end', False)
            vendor_uom = post.get('vendor_uom', False)
            branch_id = post.get('branch_id', False)
            old_id = request.env['product.supplierinfo'].search([('id', '=', changes_id)])
            vendor_pric = {
                'product_name': vendor_product_name,
                'product_code': vendor_product_code,
                'delay': delay,
                'branch_id': branch_id,
                'vendor_uom': vendor_uom,
                'min_qty': qty,
                'price': unit_price,
                'date_start': validity_start,
                'date_end': validity_end,
                'changes_id': changes_id,
                'changes': changes,
                'product_id': old_id.product_id.id or False,
                'product_tmpl_id': old_id.product_tmpl_id.id or False,
                'product_uom': old_id.product_uom.id or False,
            }
            vendor_id = request.env['product.supplierinfo'].sudo().create(vendor_pric)
            if vendor_id:
                quote_msg = {
                    'success': 'Vendor Pricelist ' + vendor_product_name + ' created successfully.'
                }

        values = {
            'page_name': 'vendor_pricelist_form_page',
            'default_url': '/vendor_pricelist',
            'quote_msg': quote_msg,
        }
        return request.render("equip3_purchase_vendor_portal.vendor_pricelist_form_view", values)


class VendorPricelistPortal(CustomerPortal):

    @route(['/my/purchase/home'], type='http', auth="user", website=True)
    def PurchaseHome(self, **kw):
        values = self._prepare_portal_layout_values()
        return request.render("equip3_purchase_vendor_portal.purchase_portal_my_home", values)


    def _vendor_pricelist_get_page_view_values(self, current, access_token, **kwargs):
        access_url = '/my/vendor_pricelist/'
        ids = request.session['my_vendor_pricelist_history']
        if current.id in ids and (hasattr(current, 'website_url') or hasattr(current, 'access_url')):
            attr_name = 'access_url' if hasattr(current, 'access_url') else 'website_url'
            idx = ids.index(current.id)
            return {
                'prev_record': idx != 0 and access_url + str(current.browse(ids[idx - 1]).id),
                'next_record': idx < len(ids) - 1 and access_url + str(current.browse(ids[idx + 1]).id),
            }
        return {}

    def _prepare_portal_layout_values(self):

        values = super(VendorPricelistPortal, self)._prepare_portal_layout_values()

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        vendor_pricelist_obj = request.env['product.supplierinfo']
        vendor_pricelist = vendor_pricelist_obj.sudo().search([('name', 'in', partner_id_list), ('is_vendor_pricelist_approval_matrix', '=', True)])
        vendor_pricelist_count = vendor_pricelist_obj.sudo().search_count([('name', 'in', partner_id_list), ('is_vendor_pricelist_approval_matrix', '=', True)])

        blanket_order_obj = request.env['purchase.requisition'].sudo()
        blanket_order = blanket_order_obj.sudo().search([('vendor_id', 'in', partner_id_list), ('state', '=', 'blanket_order')])
        blanket_order_count = blanket_order_obj.sudo().search_count([('vendor_id', 'in', partner_id_list), ('state', '=', 'blanket_order')])

        values['blanket_order'] = blanket_order
        values['blanket_order_count'] = blanket_order_count

        values['vendor_pricelist_count'] = vendor_pricelist_count
        values['vendor_pricelist'] = vendor_pricelist
        values['is_vendor'] = request.env.user.partner_id.is_vendor
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        portal_values = self._prepare_portal_layout_values()
        if 'vendor_pricelist_count' in counters:
            values['vendor_pricelist_count'] = portal_values['vendor_pricelist_count']
        if 'blanket_order_count' in counters:
            values['blanket_order_count'] = portal_values['blanket_order_count']
        return values

    @http.route(['/my/vendor_pricelist/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_vendor_pricelist_form(self, quote_id, report_type=None, access_token=None, message=False,
                                        download=False, **kw):
        quote_sudo = request.env['product.supplierinfo'].sudo().browse(quote_id)
        values1 = {
            'token': access_token,
            'vendor_pricelist': quote_sudo,
            'vp_id': True,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.name.id,
            'report_type': 'html',
        }
        values2 = self._vendor_pricelist_get_page_view_values(quote_sudo, access_token, **kw)

        values = {**values1, **values2}
        return request.render('equip3_purchase_vendor_portal.portal_vendor_pricelist_form_template', values)

    def vendor_pricelist_import(self, data):
        for line in data:
            product_name = line[0]
            product_id = request.env['product.product'].search([('name', 'ilike', product_name)], limit=1)
            product_uom = line[5]
            product_uom_id = request.env['uom.uom'].search([('name', 'ilike', product_uom)], limit=1)
            vailidity = line[6]
            vailidity_date = vailidity.split(",")
            branch_ids = line[7]
            branch_id = request.env['res.branch'].search([('name', 'ilike', branch_ids)], limit=1)
            vals = {
                'product_id': product_id.id,
                'product_name': product_name,
                'product_tmpl_id': product_id.product_tmpl_id.id,
                'product_code': line[1],
                'delay': line[2],
                'min_qty': line[3],
                'price': line[4],
                'product_uom_new': product_uom_id.id,
                'date_start': datetime.strptime(vailidity_date[0], '%m/%d/%Y').date(),
                'date_end': datetime.strptime(vailidity_date[1], '%m/%d/%Y').date(),
                'branch_id': branch_id.id,
            }
            pricelist_id = request.env['product.supplierinfo'].create(vals)

    @http.route(['/check/user'], type='http', auth='user', website=True, csrf=False)
    def portal_user_select(self, **kw):
        user = request.env.user
        html_response = request.env['ir.ui.view'].sudo()._render_template('equip3_purchase_vendor_portal.user_select_vendor_customer')
        values = {
            'is_customer': user.has_group('equip3_purchase_vendor_portal.group_customer_user'),
            'is_vendor': user.has_group('equip3_purchase_vendor_portal.group_vendor_user'),
            'html': html_response.decode('UTF-8'),
        }
        return json.dumps(values)

    @http.route(['/change/user/type'], type='http', auth='user', website=True, csrf=False)
    def portal_user_change(self, **kw):
        user = request.env.user
        customer_group = request.env.ref('equip3_purchase_vendor_portal.group_customer_user')
        vendor_group = request.env.ref('equip3_purchase_vendor_portal.group_vendor_user')
        vendor_menus = [
            "/tender/dashboard",
            "/vendor_sign_up",
            "/vendor_pricelist",
            "/open_tender",
        ]
        customer_menus = [
            "/shop",
        ]
        vendor_menu = request.website.menu_id.child_id.filtered(lambda r: 
            r.url in vendor_menus and vendor_group.id not in r.group_ids.ids)
        for v_menu in vendor_menu:
            v_menu.sudo().write({
                'group_ids': [(6, 0, vendor_group.ids)]
            })
        customer_menu = request.website.menu_id.child_id.filtered(lambda r: 
            r.url in customer_menus and customer_group.id not in r.group_ids.ids)
        for c_menu in customer_menu:
            c_menu.sudo().write({
                'group_ids': [(6, 0, customer_group.ids)]
            })
        if kw.get('is_vendor'):
            vendor_group.sudo().write({
                'users': [(4, user.id)]
            })
            customer_group.sudo().write({
                'users': [(3, user.id)]
            })
        else:
            customer_group.sudo().write({
                'users': [(4, user.id)]
            })
            vendor_group.sudo().write({
                'users': [(3, user.id)]
            })
        return json.dumps({})

    @http.route(['/my/vendor_pricelist_import'], type='json', auth="user", website=True)
    def portal_vendor_pricelist_import_form(self, file, file_name, **kw):
        fileformat = os.path.splitext(file_name)[1]
        data = []
        if fileformat == ".csv":
            decoded_datas = base64.b64decode(file)
            file = TextIOWrapper(BytesIO(decoded_datas))
            sniffer = csv.Sniffer()
            sniffer.preferred = [';', ',']
            dialect = sniffer.sniff(file.read())
            file.seek(0)
            csvreader = csv.reader(file)
            fields = next(csvreader)
            for row in csvreader:
                data.append(row)
            self.vendor_pricelist_import(data)
        elif fileformat == ".xls":
            xlDecoded = base64.b64decode(file)
            workbook = open_workbook(file_contents=xlDecoded)
            data = []
            for sheet in workbook.sheets():
                for count in range(1, sheet.nrows):
                    line = sheet.row_values(count)
                    data.append(line)
            self.vendor_pricelist_import(data)
        else:
            return {'message': "Please select xls or csv file and try again!"}

    @http.route(['/my/vendor_pricelist', '/my/vendor_pricelist/page/<int:page>'], type='http', auth="user",
                website=True)
    def portal_my_home_vendor_pricelist(self, page=1, step=20, sortby=None, filterby=None, search=None, search_in='all',
                                        groupby='none', **kw):
        values = self._prepare_portal_layout_values()

        searchbar_sortings = {
            'product_name': {'label': _('Product Name A-Z'), 'order': 'product_name asc'},
            'product_name1': {'label': _('Product Name Z-A'), 'order': 'product_name desc'},
            'product_code': {'label': _('Product Code A-Z'), 'order': 'product_code asc'},
            'product_code1': {'label': _('Product Code Z-A'), 'order': 'product_code desc'},
            'delay': {'label': _('Delivery Lead Time'), 'order': 'delay asc'},
            'date_end': {'label': _('Expiry Date'), 'order': 'date_end asc'},
            'state1': {'label': _('Status'), 'order': 'state asc'},
            'date': {'label': _('Date'), 'order': 'create_date desc'},
        }
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search')},
            'name': {'input': 'name', 'label':   _('Search Vendor Product Name')},
            'code': {'input': 'code', 'label':   _('Search Vendor Product Code')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'state': {'input': 'state', 'label': _('Status')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Created Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Created Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Created Date By Year')},
        }
   
        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('name', 'in', partner_id_list), ('is_vendor_pricelist_approval_matrix', '=', True)]},
            'waiting': {'label': _('Waiting for Approval'), 'domain': [("state1", "=", "waiting_approval")]},
            'approved': {'label': _('Approved'), 'domain': [("state1", "=", "approved")]},
            'rejected': {'label': _('Rejected'), 'domain': [("state1", "=", "rejected")]},
            'expired': {'label': _('Expired'), 'domain': [("state1", "=", "expire")]},
        }

        domain = []

        if not sortby:
            sortby = 'product_name'
        order = searchbar_sortings[sortby]['order']

        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('product_name', 'ilike', search)]])
            if search_in in ('code', 'all'):
                search_domain = OR([search_domain, [('product_code', 'ilike', search)]])
        domain += search_domain

        vendor_pricelist_obj = request.env['product.supplierinfo']
        vendor_pricelist_count = vendor_pricelist_obj.sudo().search_count(domain)

        pager = portal_pager(
            url="/my/vendor_pricelist",
            url_args={'sortby': sortby, 'search_in': search_in,
                      'search': search, 'filterby': filterby, 'groupby': groupby},
            total=vendor_pricelist_count,
            page=page,
            step=step,
        )
        
        if groupby == 'state':
            order = "state, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "create_date desc, %s" % order
        
        vendor_pricelist = vendor_pricelist_obj.search(domain, order=order, limit=self._items_per_page,
                                                       offset=pager['offset'])
        
        # grouped_vendor_pricelist = [vendor_pricelist] if groupby != 'state' else [vendor_pricelist.concat(*g) for _, g in groupbyelem(vendor_pricelist, itemgetter('state'))]
        grouped_vendor_pricelist = []
        if groupby == 'state':
            vendor_priclist_sorted = sorted(vendor_pricelist, key=lambda x: x.state)
            for state, group in groupbyelem(vendor_priclist_sorted, itemgetter('state')):
                grouped_vendor_pricelist.append(group)
        elif groupby == 'period_by_day':
            vendor_priclist_sorted = vendor_pricelist
            old_formatdate=False
            for vp_rec in vendor_priclist_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = vp_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_vendor_pricelist.append([vp_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_vendor_pricelist)
                        grouped_vendor_pricelist[len_group-1].append(vp_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_vendor_pricelist.append([vp_rec])
        elif groupby == 'period_by_month':
            vendor_priclist_sorted = vendor_pricelist
            old_formatdate=False
            for vp_rec in vendor_priclist_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = vp_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_vendor_pricelist.append([vp_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_vendor_pricelist)
                        grouped_vendor_pricelist[len_group-1].append(vp_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_vendor_pricelist.append([vp_rec])
        elif groupby == 'period_by_year':
            vendor_priclist_sorted = vendor_pricelist
            old_formatdate=False
            for vp_rec in vendor_priclist_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = vp_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_vendor_pricelist.append([vp_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_vendor_pricelist)
                        grouped_vendor_pricelist[len_group-1].append(vp_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_vendor_pricelist.append([vp_rec])
        else:
            grouped_vendor_pricelist.append(vendor_pricelist)
        
        
        request.session['my_vendor_pricelist_history'] = vendor_pricelist.ids[:100]
        values.update({
            'vendor_pricelist': vendor_pricelist,
            'page_name': 'vendor_pricelist',
            'grouped_vendor_pricelist': grouped_vendor_pricelist,
            'pager': pager,
            'default_url': '/my/vendor_pricelist',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'search': search,
            'search_in': search_in,
        })

        return request.render("equip3_purchase_vendor_portal.portal_my_vendor_pricelist", values)

    @http.route(['/my/blanket/order', '/my/blanket/order/page/<int:page>'], type='http', auth="user",
                website=True)
    def portal_my_home_blanket_order(self, page=1, step=20, sortby=None, filterby=None, search=None, search_in='all',
                                        groupby='none', **kw):
        values = self._prepare_portal_layout_values()

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        domain = [('vendor_id', 'in', partner_id_list), ('state', '=', 'blanket_order')]

        blanket_order_obj = request.env['purchase.requisition']
        blanket_order_count = blanket_order_obj.sudo().search_count(domain)
        
        searchbar_inputs = {
            'all': {'input':  'all', 'label': _('Search in All')},
            'name': {'input': 'name', 'label':   _('Search Blanket Order Name')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'bo_state2': {'input': 'bo_state2', 'label': _('Status')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Order Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Order Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Order Date By Year')},
        }
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
        }
        
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = AND([search_domain, [('name', 'ilike', search)]])

        pager = portal_pager(
            url="/my/blanket/order",
            url_args={'sortby': sortby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=blanket_order_count,
            page=page,
            step=step,
        )
        
        if groupby == 'bo_state2':
            order = "bo_state2, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "ordering_date desc, %s" % order
        
            
            
        blanket_order = blanket_order_obj.sudo().search(domain, order=order, limit=self._items_per_page,
                                                       offset=pager['offset'])
        # grouped_blanket_order = [blanket_order] if groupby != 'bo_state2' else [blanket_order.concat(*g) for _, g in groupbyelem(blanket_order, itemgetter('bo_state2'))]
        
        grouped_blanket_order = []
        if groupby == 'bo_state2':
            blanket_sorted = sorted(blanket_order, key=lambda x: x.bo_state2)
            for bo_state2, group in groupbyelem(blanket_sorted, itemgetter('bo_state2')):
                grouped_blanket_order.append(group)
        elif groupby == 'period_by_day':
            blanket_sorted = blanket_order
            old_formatdate=False
            for bso_rec in blanket_sorted:
                formatdate = bso_rec.ordering_date or '-'
                if bso_rec.ordering_date:
                    formatdate = bso_rec.ordering_date.strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_blanket_order.append([bso_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_blanket_order)
                        grouped_blanket_order[len_group-1].append(bso_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_blanket_order.append([bso_rec])
        elif groupby == 'period_by_month':
            blanket_sorted = blanket_order
            old_formatdate=False
            for bso_rec in blanket_sorted:
                formatdate = bso_rec.ordering_date or '-'
                if bso_rec.ordering_date:
                    formatdate = bso_rec.ordering_date.strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_blanket_order.append([bso_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_blanket_order)
                        grouped_blanket_order[len_group-1].append(bso_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_blanket_order.append([bso_rec])
        elif groupby == 'period_by_year':
            blanket_sorted = blanket_order
            old_formatdate=False
            for bso_rec in blanket_sorted:
                formatdate = bso_rec.ordering_date or '-'
                if bso_rec.ordering_date:
                    formatdate = bso_rec.ordering_date.strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_blanket_order.append([bso_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_blanket_order)
                        grouped_blanket_order[len_group-1].append(bso_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_blanket_order.append([bso_rec])
        else:
            grouped_blanket_order.append(blanket_order)

        request.session['my_blanket_order_history'] = blanket_order.ids[:100]
        
        values.update({
            'blanket_order': blanket_order,
            'page_name': 'blanket_order',
            'grouped_blanket_order': grouped_blanket_order,
            'pager': pager,
            'default_url': '/my/blanket/order',
            'sortby': sortby,
            'groupby': groupby,
            'search': search,
            'search_in': search_in,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_sortings': searchbar_sortings,
        })

        return request.render("equip3_purchase_vendor_portal.portal_my_blanket_order", values)

    def _blanket_order_page_with_values(self, order, access_token, **kwargs):
        values = {
            'page_name': 'blanket_order',
            'blanket_order': order,
            'bo_id': order,
        }
        return self._get_page_view_values(order, access_token, values, 'blanket_order', False, **kwargs)

    @http.route(['/my/blanket/order/<int:blanket_order_id>'], type='http', auth="public", website=True)
    def portal_my_blanket_order_detail(self, blanket_order_id, access_token=None, report_type=None, download=False, **kw):
        blanket_order_sudo = request.env['purchase.requisition'].sudo().browse(blanket_order_id)

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=blanket_order_sudo, report_type=report_type, report_ref='purchase_requisition.action_report_purchase_requisitions', download=download)

        values = self._blanket_order_page_with_values(blanket_order_sudo, access_token, **kw)

        return request.render("equip3_purchase_vendor_portal.portal_blanket_order_page", values)

class CustomPurchaseRFQPOrtal(TenderRFQPOrtal):

    @http.route(['/rfq/retreat'], type='http', auth="user", website=True, csrf=False)
    def custom_rfq_retreat(self, access_token=None,is_rfq_tender=False,is_rfq_open_tender=False, **kw):
        if kw.get('order_id'):
            purchase_order = request.env['purchase.order'].sudo().browse(int(kw.get('order_id')))
            purchase_order.sudo().write({
                'state': 'retreat'
            })
        url = '/my/rfq/update/' + str(kw.get('order_id')) 
        if is_rfq_tender:
            url += "?is_rfq_tender=True" 
        elif is_rfq_open_tender:
            url += "?is_rfq_open_tender=True" 
        return url

    @http.route(['/purchase/vendor/document/upload'], type='http', auth="user", website=True, csrf=False)
    def vendor_upload_invoice_document(self, **post):
        if post.get('purchase_id') and post.get('file_data') and post.get('file_data') != '':
            file_data = json.loads(post.get('file_data'))
            for attachment in file_data:
                vals = {
                    'name': attachment.get('name'),
                    'store_fname': attachment.get('name'),
                    'datas': attachment.get('data'),
                    'res_model': 'purchase.order',
                    'type': 'binary',
                    'res_id': int(post.get('purchase_id')),
                    'sh_is_publish_in_portal': True,
                    'sh_is_notify': False,
                    'website_id': False,
                }
                attachment_id = request.env['ir.attachment'].with_user(SUPERUSER_ID).create(vals)
        return json.dumps({})

    @http.route(['/purchase/attachment'], type='http', auth="user", website=True, csrf=False)
    def purchase_attachments(self, **post):
        if post.get('purchase_id'):
            purchase_id = request.env['purchase.order'].sudo().browse(int(post.get('purchase_id')))
            attachment_ids = request.env['ir.attachment'].sudo().search(
                [('res_id', '=', purchase_id.id), ('res_model', '=', purchase_id._name), ('sh_is_publish_in_portal', '=', True)])
            attachment_urls = []
            for attachment in attachment_ids:
                if not attachment.access_token:
                    attachment.generate_access_token()
                url = '/web/content/ir.attachment/%d/datas?access_token=%s&amp;download=true' % (attachment.id, attachment.access_token)
                attachment_urls.append({'url': url, 'name': attachment.name})
            return json.dumps({'urls': attachment_urls})

    @http.route(['/rfq/update'], type='http', auth="user", website=True, csrf=False)
    def custom_rfq_update(self, access_token=None, is_rfq_tender=False,is_rfq_open_tender=False,**kw):
        if kw.get('order_id'):
            purchase_order = request.env['purchase.order'].sudo().search(
                [('id', '=', int(kw.get('order_id')))], limit=1)
            if kw.get('vendor_payment_terms'):
                purchase_order.sudo().write({'vendor_payment_terms': str(kw.get('vendor_payment_terms'))})
                kw.pop('vendor_payment_terms')

            elif kw.get('vendor_payment_terms') == None:
                purchase_order.sudo().write({'vendor_payment_terms': str(kw.get('vendor_payment_terms'))})
                kw.pop('vendor_payment_terms')

            if purchase_order and purchase_order.agreement_id.state != 'closed':
                if purchase_order.order_line:
                    for k, v in kw.items():
                        if k != 'order_id' and '_' not in k and k != 'rfq_note' and k != 'agreement_note' and 'qty' not in k and k.isdigit():
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', k)], limit=1)
                            if purchase_order_line:
                                price = v
                                price_bef = purchase_order_line.price_unit
                                if ',' in price:
                                    price = price.replace(",", "")
                                purchase_order_line.sudo().write({
                                    'price_unit': float(price),
                                })
                                # if str(price_bef) != price:
                                #     message = "Unit Price: %s becomes %s" % (price_bef, price)
                                #     purchase_order.message_post(body=message, subtype_xmlid="mail.mt_comment", author_id=request.env.user.partner_id.id, type="comment")
                        if k != 'order_id' and '_' in k and k != 'rfq_note' and k != 'agreement_note' and 'qty' not in k:
                            notes = True
                            order_line = k.split("_note")
                            if "_" in order_line[0]:
                                order_line = order_line[0].split("_qty")
                                notes = False
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', int(order_line[0]))], limit=1)
                            if purchase_order_line:
                                if notes:
                                    note = v
                                    note_bef = purchase_order_line.sh_tender_note
                                    purchase_order_line.sudo().write({
                                        'sh_tender_note': note,
                                    })
                                    # if str(note_bef) != notes:
                                    #     message = "Notes: %s becomes %s" % (note_bef, notes)
                                    #     purchase_order.message_post(body=message, subtype_xmlid="mail.mt_comment", author_id=request.env.user.partner_id.id, type="comment")
                        if 'qty' in k:
                            purchase_order_line = request.env['purchase.order.line'].sudo().search(
                                [('order_id', '=', purchase_order.id), ('id', '=', k.split('_')[0])], limit=1)
                            qty = v
                            qty_bef = purchase_order_line.product_qty
                            purchase_order_line.sudo().write({
                                'product_qty': qty,
                            })
                            # if str(qty_bef) != qty:
                            #     message = "Quantity: %s becomes %s" % (qty_bef, qty)
                            #     purchase_order.message_post(body=message, subtype_xmlid="mail.mt_comment", author_id=request.env.user.partner_id.id, type="comment")

                        if k == 'rfq_note':
                            purchase_order.sudo().write({
                                'term_condition_box': kw.get(k),
                            })
                        if k == 'agreement_note':
                            purchase_order.sudo().write({
                                'service_level_agreement_box': kw.get(k),
                            })
        url = '/my/rfq/update/' + str(kw.get('order_id'))
        if is_rfq_tender:
            url+= "?is_rfq_tender=True"
        elif is_rfq_open_tender:
            url+= "?is_rfq_open_tender=True"
        return request.redirect(url)


class PurchaseRFQPortal(PurchaseRFQPortal):
    def _rfq_get_page_view_values(self, order, access_token, **kwargs):

        values = {
            'order': order,
        }
        return self._get_page_view_values(order, access_token, values, 'my_quotes_history', False, **kwargs)

    def _prepare_portal_layout_values(self):
        values = super(PurchaseRFQPortal, self)._prepare_portal_layout_values()

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)
        values['rfq_count'] = request.env['purchase.order'].search_count([('state', 'in', ['draft', 'sent', 'cancel', 'waiting_for_approve', 'reject', 'rfq_approved']), ('po', '=', False), ('is_goods_orders', '=', True), ('agreement_id','=',False), ('partner_id', 'in', partner_id_list)])
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'rfq_count' in counters:
            partner_id_list = []
            partner_id_list.append(request.env.user.partner_id.id)
            partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
            for child_id in partner_obj:
                partner_id_list.append(child_id.id)
            values['rfq_count'] = request.env['purchase.order'].search_count([('state', 'in', ['draft', 'sent', 'cancel', 'waiting_for_approve', 'reject', 'rfq_approved']), ('po', '=', False), ('is_goods_orders', '=', True), ('agreement_id','=',False), ('partner_id', 'in', partner_id_list)])
        return values

    @http.route(['/my/rfq', '/my/rfq/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rfq(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        domain = [('dp','=',False)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        
        searchbar_inputs = {
            'all': {'input':  'all', 'label': _('Search')},
            'name': {'input': 'name', 'label':   _('Search RFQ')},
        }

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Order Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Order Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Order Date By Year')},
        }
        
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft', 'sent', 'cancel', 'waiting_for_approve', 'reject', 'rfq_approved']), ('po', '=', False), ('agreement_id','=',False), ('partner_id', 'in', partner_id_list)]},
            'draft': {'label': _('Request For Quotation'), 'domain': [('state', '=', 'draft'), ('partner_id', 'in', partner_id_list)]},
            'sent': {'label': _('Sent'), 'domain': [('state', 'in', ['sent']), ('partner_id', 'in', partner_id_list)]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
        domain += search_domain

        # count for pager
        rfq_count = PurchaseOrder.search_count(domain)

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "date_order desc, %s" % order

        # make pager
        pager = portal_pager(
            url="/my/rfq",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=rfq_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        rfqs = PurchaseOrder.sudo().search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )

        grouped_rfq = []
        if groupby == 'price_rating':
            # Assuming purchase orders have a 'price_rating' attribute
            rfqs_sorted = sorted(rfqs, key=lambda x: x.price_rating)
            for price_rating, group in groupbyelem(rfqs_sorted, itemgetter('price_rating')):
                grouped_rfq.append(group)
        elif groupby == 'period_by_day':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.date_order.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        elif groupby == 'period_by_month':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.date_order.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        elif groupby == 'period_by_year':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.date_order.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])

        else:
            grouped_rfq.append(rfqs)

        request.session['my_quotes_history'] = rfqs.ids[:100]

        values.update({
            'date': date_begin,
            'rfqs': rfqs,
            'grouped_rfq':grouped_rfq,
            'page_name': 'quotes',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/rfq',
            'searchbar_inputs': searchbar_inputs,
            'search': search,
            'search_in': search_in,
        })
        return request.render("sh_rfq_portal.sh_portal_my_rfqs", values)

    @http.route(['/my/rfq/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfq_form(self, quote_id, report_type=None, access_token=None, message=False, download=False, **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type,
                                     report_ref='purchase.report_purchase_quotation', download=download)
        values1 = {
            'token': access_token,
            'quotes': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }

        values2 = self._rfq_get_page_view_values(quote_sudo, access_token, **kw)
        values = {**values1, **values2}
        return request.render('equip3_purchase_vendor_portal.portal_rfq_form_templates', values)

    @http.route(['/my/rfq/update/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfqs_update(self, quote_id=None, report_type=None, access_token=None, message=False, download=False, is_rfq_tender=False,is_rfq_open_tender=False,
                              **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type,
                                     report_ref='purchase.report_purchase_quotation', download=download)

        values = {
            'token': access_token,
            'quotes': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
        }
        portal_template = "equip3_purchase_vendor_portal.sh_portal_my_rfq_order_update"
        if is_rfq_tender:
            values.update({
                'quotes':False,
                'rfq_tenders':quote_sudo,
                'rfq_tender':quote_sudo,
                'page_name':'rfq_tenders',
            })
            portal_template = "equip3_purchase_vendor_portal.sh_portal_my_rfq_tender_order_update"
        elif is_rfq_open_tender:
            values.update({
                'quotes':False,
                'rfq_open_tender':quote_sudo,
                'page_name':'rfq_open_tender',
            })
            portal_template = "equip3_purchase_vendor_portal.sh_portal_my_rfq_open_tender_order_update"

        return request.render(portal_template, values)
    
    @http.route(['/rfq/edit'], type='http', auth="user", website=True, csrf=False)
    def custom_rfq_edit(self,is_rfq_tender=False,is_rfq_open_tender=False, **kw):
        url = '/my/rfq/'+str(kw.get('order_id'))
        if is_rfq_tender:
            url = '/my/rfq-tender/'+str(kw.get('order_id'))+"?is_rfq_tender=True"
        elif is_rfq_open_tender:
            url = '/my/rfq-open-tender/'+str(kw.get('order_id'))+"?is_rfq_open_tender=True"
        return request.redirect(url)

class TenderPortal(TenderPortal):
    def _prepare_portal_layout_values(self):
        values = super(TenderPortal, self)._prepare_portal_layout_values()

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        tender_obj = request.env['purchase.agreement']
        tenders = tender_obj.sudo().search([
            '|',
            ('partner_ids', 'in', partner_id_list),
            ('partner_ids', '=', False)
        ])
        tender_count = tender_obj.sudo().search_count([
            '|',
            ('partner_ids', 'in', partner_id_list),
            ('partner_ids', '=', False)
        ])
        tender_count_filtered = 0
        # Sebenernya ada field rfq_count yang mungkin dijadikan acuan
        # tetapi karena tidak di store jadi gakbisa dijadikan domain
        # jadi harus difilter 1-1 pake looping
        for tender in tenders:
            rfq_submission = request.env['purchase.order'].sudo().search([
                ('agreement_id', '=', tender.id),
                ('selected_order', '=', False),
                ('state', 'in', ['draft'])
                ])
            if rfq_submission:
                tender_count_filtered +=1 

        values['tender_count'] = tender_count_filtered
        values['tenders'] = tenders
        return values

    def _tender_get_page_view_values(self, order, access_token, **kwargs):
        values = {
            'order': order,
        }
        return self._get_page_view_values(order, access_token, values, 'my_tender_history', False, **kwargs)

    # OVERRIDE
    @http.route(['/my/tender', '/my/tender/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_home_tender(self, page=1, step=20, sortby=None, filterby=None, search=None, search_in="all", groupby='none', **kw):
        # print('PURCHASE TENDER')
        values = self._prepare_portal_layout_values()
        tender_obj = request.env['purchase.agreement']

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        domain = [
            ('pt_state','not in',('draft','pending')),
            '|',
            ('partner_ids', 'in', partner_id_list),
            ('partner_ids', '=', False)
        ]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [("pt_state", "=", "draft")]},
            'waiting': {'label': _('Waiting for Approval'), 'domain': [("pt_state", "=", "waiting_approval")]},
            'pending': {'label': _('Pending'), 'domain': [("pt_state", "=", "pending")]},
            'bid_submission': {'label': _('Bid Submission'), 'domain': [("pt_state", "=", "bid_submission")]},
            'bid_selection': {'label': _('Bid Selection'), 'domain': [("pt_state", "=", "bid_selection")]},
            'closed': {'label': _('Closed'), 'domain': [("pt_state", "=", "closed")]},
            'cancel': {'label': _('Cancelled'), 'domain': [("pt_state", "=", "cancel")]},
        }
        searchbar_inputs = {
            'all': {'input':  'all', 'label': _('Search')},
            'name': {'input': 'name', 'label':   _('Search Tender')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'status': {'input': 'status', 'label': _('Status')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Created Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Created Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Created Date By Year')},
        }

        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        tender_count = tender_obj.sudo().search_count(domain)
        
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
        domain += search_domain
  
        pager = portal_pager(
            url="/my/tender",
            url_args={'sortby': sortby, 'filterby': filterby,
                      'search_in': search_in, 'search': search, 'groupby': groupby},
            total=tender_count,
            page=page,
            step=step,
        )
        
        if groupby == 'status':
            order = "pt_state, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "create_date desc, %s" % order

        tenders_all = tender_obj.sudo().search(
            domain, order=order, offset=pager['offset'])
        
        tenders = request.env['purchase.agreement'].sudo()
        count = 0
        limit=self._items_per_page
        # Sebenernya ada field rfq_count yang mungkin dijadikan acuan
        # tetapi karena tidak di store jadi gakbisa dijadikan domain
        # jadi harus difilter 1-1 pake looping
        for tender in tenders_all:
            if count <= limit:
                rfq_submission = request.env['purchase.order'].sudo().search([
                    ('agreement_id', '=', tender.id),
                    ('selected_order', '=', False),
                    ('state', 'in', ['draft'])
                    ])
                if rfq_submission:
                    tenders |= tender
                    count+=1
                    
        grouped_purchase_tender = []
        if groupby == 'status':
            tenders_all_sorted = sorted(tenders, key=lambda x: x.pt_state)
            for state, group in groupbyelem(tenders_all_sorted, itemgetter('pt_state')):
                grouped_purchase_tender.append(group)
        elif groupby == 'period_by_day':
            tenders_all_sorted = sorted(tenders, key=lambda x: x.create_date,reverse=True)
            old_formatdate=False
            for tnds_rec in tenders_all_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = tnds_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_purchase_tender.append([tnds_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_purchase_tender)
                        grouped_purchase_tender[len_group-1].append(tnds_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_purchase_tender.append([tnds_rec])
        elif groupby == 'period_by_month':
            tenders_all_sorted = sorted(tenders, key=lambda x: x.create_date,reverse=True)
            old_formatdate=False
            for tnds_rec in tenders_all_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = tnds_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_purchase_tender.append([tnds_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_purchase_tender)
                        grouped_purchase_tender[len_group-1].append(tnds_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_purchase_tender.append([tnds_rec])
        elif groupby == 'period_by_year':
            tenders_all_sorted = sorted(tenders, key=lambda x: x.create_date,reverse=True)
            old_formatdate=False
            for tnds_rec in tenders_all_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = tnds_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_purchase_tender.append([tnds_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_purchase_tender)
                        grouped_purchase_tender[len_group-1].append(tnds_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_purchase_tender.append([tnds_rec])
        else:
            grouped_purchase_tender.append(tenders)
        
        pager = portal_pager(
            url="/my/tender",
            url_args={'sortby': sortby, 'filterby': filterby,
                      'groupby': groupby, 'search': search, 'search_in': search_in},
            total=len(tenders),
            page=page,
            step=step,
        )

        request.session['my_tender_history'] = tenders.ids[:100]
        values.update({
            'tenders': tenders.sudo(),
            'page_name': 'tender',
            'grouped_purchase_tender': grouped_purchase_tender,
            'pager': pager,
            'default_url': '/my/tender',
            'tender_count': tender_count,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'search': search,
            'search_in': search_in,
        })
        # return request.render("sh_po_tender_portal.portal_my_tenders", values)
        return request.render("equip3_purchase_vendor_portal.portal_purchase_tender_template", values)

    @http.route(['/my/tender/<int:tender_id>'], type='http', auth="user", website=True)
    def portal_my_tender_form(self, tender_id, report_type=None, access_token=None, message=False, download=False,
                              **kw):
        tender_sudo = request.env['purchase.agreement'].sudo().search(
            [('id', '=', tender_id)], limit=1)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=tender_sudo, report_type=report_type,
                                     report_ref='sh_po_tender_management.action_report_purchase_tender',
                                     download=download)
        values1 = {
            'token': access_token,
            'tender': tender_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': tender_sudo.partner_id.id,
            'report_type': 'html',
            'purchase_order_id': tender_sudo.purchase_order_ids and tender_sudo.purchase_order_ids.filtered(lambda x: x.partner_id == request.env.user.partner_id) or False,
        }
        values2 = self._tender_get_page_view_values(tender_sudo, access_token, **kw)
        values = {**values1, **values2}
        return request.render('sh_po_tender_portal.portal_tender_form_template', values)

    @http.route(['/rfq/create'], type='http', auth='user', website=True, csrf=False)
    def portal_create_rfq(self, **kw):
        dic = {}
        purchase_tender = request.env['purchase.agreement'].sudo().search(
            [('id', '=', int(kw.get('tender_id')))], limit=1)

        purchase_order = request.env['purchase.order'].sudo().search(
            [('agreement_id', '=', purchase_tender.id), ('partner_id', '=', request.env.user.partner_id.id), ('state', 'in', ['draft'])])
        if purchase_order and len(purchase_order.ids) > 1:
            dic.update({
                'url': '/my/rfq'
            })
        elif purchase_order and len(purchase_order.ids) == 1:
            dic.update({
                'url': '/my/rfq/'+str(purchase_order.id)
            })
            if purchase_tender.tender_scope == 'open_tender':
                dic.update({
                    'url': '/my/rfq-open-tender/'+str(purchase_order.id)
                })
            elif purchase_tender.tender_scope == 'invitation_tender':
                dic.update({
                    'url': '/my/rfq-tender/'+str(purchase_order.id)
                })
        else:
            order_dic = {}
            order_dic.update({
                'partner_id': request.env.user.partner_id.id,
                'agreement_id': purchase_tender.id,
                'date_order': fields.Datetime.now(),
                'user_id': purchase_tender.sh_purchase_user_id.id,
                'state': 'draft',
            })
            if purchase_tender.sh_agreement_deadline:
                order_dic.update({
                    'date_planned': purchase_tender.sh_agreement_deadline,
                })
            else:
                order_dic.update({
                    'date_planned': fields.Datetime.now(),
                })
            purchase_order_id = request.env['purchase.order'].sudo().create(
                order_dic)
            line_ids = []
            for line in purchase_tender.sh_purchase_agreement_line_ids:
                line_vals = {
                    'order_id': purchase_order_id.id,
                    'product_id': line.sh_product_id.id,
                    'agreement_id': purchase_tender.id,
                    'status': 'draft',
                    'name': line.sh_product_id.name,
                    'product_qty': line.sh_qty,
                    'product_uom': line.sh_product_id.uom_id.id,
                    'price_unit': 0.0,
                }
                if purchase_tender.sh_agreement_deadline:
                    line_vals.update({
                        'date_planned': purchase_tender.sh_agreement_deadline,
                    })
                else:
                    line_vals.update({
                        'date_planned': fields.Datetime.now(),
                    })
                line_ids.append((0, 0, line_vals))
            purchase_order_id.order_line = line_ids
            dic.update({
                'url': '/my/rfq/'+str(purchase_order_id.id)
            })
            if purchase_tender.tender_scope == 'open_tender':
                dic.update({
                    'url': '/my/rfq-open-tender/'+str(purchase_order.id)
                })
            elif purchase_tender.tender_scope == 'invitation_tender':
                dic.update({
                    'url': '/my/rfq-tender/'+str(purchase_order.id)
                })
        return json.dumps(dic)

    @http.route(['/tender/dashboard'], type='http', auth='user', website=True)
    def open_tender_dashboard(self, **kw):
        values = {}
        partner_id = request.env.user.partner_id
        all_tenders = request.env['purchase.agreement'].sudo().search([('partner_ids', 'in', partner_id.ids)])
        values['active_tender'] = len(all_tenders.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and r.state2 in ('bid_submission', 'bid_selection')))
        values['total_tender'] = len(all_tenders.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender') and r.state2 in ('bid_submission', 'bid_selection', 'closed', 'cancel', 'pending')))
        values['document_submitted'] = len(all_tenders.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender')).mapped('purchase_order_ids').filtered(lambda r: r.partner_id.id == partner_id.id))
        values['won_tender'] = len(all_tenders.filtered(lambda r: r.tender_scope in ('open_tender', 'invitation_tender')).mapped('purchase_order_ids').filtered(lambda r: r.state in ('purchase', 'done') and r.partner_id.id == partner_id.id))
        today = date.today()
        request.session['is_both'] = True if partner_id.is_customer and partner_id.is_vendor else False
        week_start_date = today - timedelta(days=today.weekday())
        week_end_date = week_start_date + timedelta(days=6)
        start_week_date = datetime.strptime(week_start_date.strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT).replace(hour=0, minute=0, second=0)
        end_week_date = datetime.strptime(week_end_date.strftime(DEFAULT_SERVER_DATE_FORMAT), DEFAULT_SERVER_DATE_FORMAT).replace(hour=23, minute=59, second=59)
        week_tenders = request.env['purchase.agreement'].sudo().search([
                ('partner_ids', 'in', partner_id.ids),
                ('state2', 'in', ('bid_submission', 'bid_selection')),
                ('sh_agreement_deadline', '>=', start_week_date),
                ('sh_agreement_deadline', '<=', end_week_date),
            ], limit=5)
        values['week_tenders'] = week_tenders
        overdue_tenders = request.env['purchase.agreement'].sudo().search([
                ('partner_ids', 'in', partner_id.ids),
                ('state2', '=', 'bid_submission'),
                ('sh_agreement_deadline', '>=', datetime.now()),
            ], limit=5, order="sh_agreement_deadline")
        values['overdue_tenders'] = overdue_tenders
        return request.render('equip3_purchase_vendor_portal.tender_dashboard_form_view', values)

class CustomeCreateVendor(CreateVendor):

    @http.route(['/vendor_sign_up'], type='http', auth="public", website=True)
    def create_vendor(self, **post):
        quote_msg = {}
        emails = []
        image = 0
        multi_users_value = [0]
        contacts = []
        check_view = request.env.ref('sh_vendor_signup.vendor_sign_up_form_view')
        if check_view.key != check_view.xml_id:
            query_statement = """UPDATE ir_ui_view set key = %s WHERE id = %s """
            request.env.cr.execute(query_statement, [check_view.xml_id,check_view.id])
        if post:
            vendor_name = post.get('vendor_name', False)
            vendor_email = post.get('vendor_email', False)
            vendor_phone = post.get('vendor_phone', False)
            vendor_mobile = post.get('vendor_mobile', False)
            vendor_street = post.get('vendor_street', False)
            vendor_street2 = post.get('vendor_street2', False)
            vendor_website = post.get('vendor_website', False)
            vendor_zip_code = post.get('vendor_zip_code', False)
            vendor_city = post.get('vendor_city', False)
            vendor_country = post.get('country_id', False)
            vendor_state = post.get('state_id', False)
            vendor_type = post.get('vendor_type', False)
            vendor_comment = post.get('vendor_comment', False)
            vendor_note = post.get('vendor_note', False)
            company_size = post.get('company_size', False)
            company_size2 = post.get('company_size2', False)
            capital_revenue = post.get('capital_revenue', False)
            if post.get('vendor_image', False):
                img = post.get('vendor_image')
                image = base64.b64encode(img.read())
            multi_users_value = request.httprequest.form.getlist('category_section')
            for l in range(0, len(multi_users_value)):
                multi_users_value[l] = int(multi_users_value[l])
            country = 'country_id' in post and post['country_id'] != '' and request.env['res.country'].browse(
                int(post['country_id']))
            country = country and country.exists()
            vendor_dic = {
                'name': vendor_name,
                'street': vendor_street,
                'street2': vendor_street2,
                'phone': vendor_phone,
                'mobile': vendor_mobile,
                'email': vendor_email,
                'website': vendor_website,
                'zip': vendor_zip_code,
                'city': vendor_city,
                'country_id': int(vendor_country) if int(vendor_country) else False,
                'state_id': int(vendor_state) if int(vendor_state) else False,
                'company_type': vendor_type,
                'vendor_products': vendor_comment,
                'comment': vendor_note,
                'image_1920': image,
                'vendor_product_categ_ids': [(6, 0, multi_users_value)] or [],
                'customer_rank': 0,
                'supplier_rank': 1,
                'company_size': company_size,
                'company_size2': company_size2,
                'capital_revenue': capital_revenue,
            }
            is_valid = True
            PartnerObj = request.env['res.partner'].sudo()

            if is_valid:
                get_partners = PartnerObj.find_partner_similiar(vendor_name,vendor_phone,vendor_mobile)
                if len(get_partners) > 0:
                    quote_msg = {
                    'fail': "This vendor have a similar identity with another vendor"
                    }
                    is_valid = False

            if not is_valid:
                countries = request.env["res.country"].sudo().search([])
                indonesia_country = request.env["res.country"].sudo().search([('code', '=', 'ID')])
                country_states = indonesia_country.state_ids
                values = {
                    'page_name': 'vendor_sign_up_form_page',
                    'default_url': '/vendor_sign_up',
                    'quote_msg': quote_msg,
                    'country_states': country_states,
                    'countries': countries,
                }
                return request.render("sh_vendor_signup.vendor_sign_up_form_view", values)

            vendor_id = request.env['res.partner'].sudo().create(vendor_dic)

            if vendor_id:
                vendor_id.is_vendor = True
                quote_msg = {
                    'success': 'Vendor ' + vendor_name + ' created successfully.' + '<br/>' + 'Vendor Id: ' + str(vendor_id.id)
                }
                if request.website.is_enable_vendor_notification and request.website.sudo().user_ids.sudo():
                    for user in request.website.user_ids.sudo():
                        if user.sudo().partner_id.sudo() and user.sudo().partner_id.sudo().email:
                            emails.append(user.sudo().partner_id.sudo().email)
                email_values = {
                    'email_to': ','.join(emails),
                    'email_from': request.website.company_id.sudo().email,
                }
                url = ''
                base_url = request.env['ir.config_parameter'].sudo(
                ).get_param('web.base.url')
                url = base_url + "/web#id=" + \
                      str(vendor_id.id) + \
                      "&&model=res.partner&view_type=form"
                ctx = {
                    "customer_url": url,
                }
                template_id = request.env['ir.model.data'].get_object(
                    'sh_vendor_signup', 'sh_vendor_signup_email_notification')
                _ = request.env['mail.template'].sudo().browse(template_id.id).with_context(ctx).send_mail(
                    vendor_id.id, email_values=email_values, force_send=True)

            contact_dic = {k: v for k, v in post.items() if k.startswith('vendor_c_name_')}
            if vendor_id and contact_dic:
                for key, value in contact_dic.items():
                    vendor_dic = {}
                    if "vendor_c_name_" in key:
                        vendor_dic["name"] = value

                        numbered_key = key.replace("vendor_c_name_", "") or ''
                        email_key = 'vendor_c_email_' + numbered_key
                        phone_key = 'vendor_c_phone_' + numbered_key
                        mobile_key = 'vendor_c_mobile_' + numbered_key
                        title_key = 'vendor_c_title_' + numbered_key
                        job_position_key = 'vendor_c_job_position_' + numbered_key
                        notes_key = 'vendor_c_notes_' + numbered_key
                        gender_key = 'vendor_c_gender_' + numbered_key
                        place_key = 'vendor_c_place_' + numbered_key
                        birthdate_key = 'vendor_c_birth_' + numbered_key

                        if post.get(email_key, False):
                            vendor_dic["email"] = post.get(email_key)
                        if post.get(phone_key, False):
                            vendor_dic["phone"] = post.get(phone_key)
                        if post.get(title_key, False):
                            vendor_dic["title"] = post.get(title_key)
                        if post.get(mobile_key, False):
                            vendor_dic["mobile"] = post.get(mobile_key)
                        if post.get(job_position_key, False):
                            vendor_dic["function"] = post.get(job_position_key)
                        if post.get(notes_key, False):
                            vendor_dic["comment"] = post.get(notes_key)
                        if post.get(gender_key, False):
                            vendor_dic["gender"] = post.get(gender_key)
                        if post.get(place_key, False):
                            vendor_dic["place"] = post.get(place_key)
                        if post.get(birthdate_key, False):
                            vendor_dic["birthdate"] = post.get(birthdate_key)

                        vendor_dic["type"] = 'contact'
                        vendor_dic["is_vendor"] = True
                        vendor_dic["parent_id"] = vendor_id.id

                        # fill list:
                        contact_id = request.env["res.partner"].sudo().create(vendor_dic)
                        if contact_id:
                            contacts.append(contact_id.id)

            try:
                if request.website.is_enable_auto_portal_user:
                    if request.website.is_enable_company_portal_user:
                        user_id = request.env['res.users'].sudo().search([('partner_id', '=', vendor_id.id)], limit=1)
                        if not user_id and vendor_id:
                            portal_wizard_obj = request.env['portal.wizard']
                            created_portal_wizard = portal_wizard_obj.sudo().create({})
                            if created_portal_wizard and vendor_id.email and request.env.user:
                                portal_wizard_user_obj = request.env['portal.wizard.user']
                                wiz_user_vals = {
                                    'wizard_id': created_portal_wizard.id,
                                    'partner_id': vendor_id.id,
                                    'email': vendor_id.email,
                                    'in_portal': True,
                                }
                                created_portal_wizard_user = portal_wizard_user_obj.sudo().create(wiz_user_vals)
                                if created_portal_wizard_user:
                                    created_portal_wizard.sudo().with_user(SUPERUSER_ID).action_apply()
                    if request.website.is_enable_company_contact_portal_user:
                        if len(contacts) > 0:
                            for contact in contacts:
                                user_id = request.env['res.users'].sudo().search([('partner_id', '=', contact)],
                                                                                 limit=1)
                                partner = request.env['res.partner'].sudo().browse(contact)
                                if not user_id and partner:
                                    portal_wizard_obj = request.env['portal.wizard']
                                    created_portal_wizard = portal_wizard_obj.sudo().create({})
                                    if created_portal_wizard and vendor_id.email and request.env.user:
                                        portal_wizard_user_obj = request.env['portal.wizard.user']
                                        wiz_user_vals = {
                                            'wizard_id': created_portal_wizard.id,
                                            'partner_id': partner.id,
                                            'email': partner.email,
                                            'in_portal': True,
                                        }
                                        created_portal_wizard_user = portal_wizard_user_obj.sudo().create(wiz_user_vals)
                                        if created_portal_wizard_user:
                                            created_portal_wizard.sudo().with_user(SUPERUSER_ID).action_apply()
            except Exception as e:
                quote_msg = {
                    'fail': str(e)
                }

        countries = request.env["res.country"].sudo().search([])
        indonesia_country = request.env["res.country"].sudo().search([('code', '=', 'ID')])
        country_states = indonesia_country.state_ids
        values = {
            'page_name': 'vendor_sign_up_form_page',
            'default_url': '/vendor_sign_up',
            'quote_msg': quote_msg,
            'country_states': country_states,
            'countries': countries,
        }
        return request.render("sh_vendor_signup.vendor_sign_up_form_view", values)

    @http.route(['/vendor/title_infos'], auth='public', type='http',  methods=['GET'], csrf=True)
    def title_infos(self, **kw):
        titles = request.env['res.partner.title'].sudo().search([])
        return json.dumps({
            'data': [{'id':title.id,'name':title.name} for title in titles],
            })

    @http.route(['/check_email_vendor'], auth='public', type='http',  methods=['GET'], csrf=True)
    def vendor_email(self,vendor_email='', **kw):
        PartnerObj = request.env['res.partner'].sudo()
        datas = []
        if vendor_email:
            cek_email = PartnerObj.search([('email', '=', vendor_email)])
            datas = cek_email.ids
        return json.dumps({
            'data': datas,
            })

class VendorPortal(CustomerPortal):
    @http.route(['/my/purchase', '/my/purchase/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_purchase_orders(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        # print('PURCHASE ORDER')
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order'].sudo()

        domain = [('state', 'in', ('purchase','cancel'))]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': ['|',('state', 'in', ['purchase', 'done']),'&',('state','=','cancel'),('name','ilike','PO')]},
            'purchase': {'label': _('Purchase Order'), 'domain': [('state', '=', 'purchase')]},
            'cancel': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel'),('name','ilike','PO')]},
            'done': {'label': _('Locked'), 'domain': [('state', '=', 'done')]},
        }
        
        searchbar_inputs = {
            'all': {'input':  'all', 'label': _('Search')},
            'name': {'input': 'name', 'label':   _('Search Purchase Order')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'billing_status': {'input': 'billing_status', 'label': _('Billing Status')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Confirmation Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Confirmation Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Confirmation Date By Year')},
        }
        
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

    
        # count for pager
        purchase_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/purchase",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby,
                      'filterby': filterby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=purchase_count,
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
        domain += search_domain
                
        if groupby == 'billing_status':
            order = "invoice_status, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "date_approve desc, %s" % order
        
        purchase_orders = PurchaseOrder.search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        
        # grouped_purchase_order = [purchase_orders] if groupby != 'billing_status' else [purchase_orders.concat(*g) for _, g in groupbyelem(purchase_orders, itemgetter('state'))]
        
        grouped_purchase_order = []
        if groupby == 'billing_status':
            purchase_orders_sorted = sorted(purchase_orders, key=lambda x: x.invoice_status)
            for invoice_status, group in groupbyelem(purchase_orders_sorted, itemgetter('invoice_status')):
                grouped_purchase_order.append(group)
        elif groupby == 'period_by_day':
            purchase_orders_sorted = purchase_orders
            old_formatdate=False
            for po_rec in purchase_orders_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = po_rec.date_approve or '-----'
                if formatdate != '-----':
                    formatdate = po_rec.date_approve.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_purchase_order.append([po_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_purchase_order)
                        grouped_purchase_order[len_group-1].append(po_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_purchase_order.append([po_rec])
        elif groupby == 'period_by_month':
            purchase_orders_sorted = purchase_orders
            old_formatdate=False
            for po_rec in purchase_orders_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = po_rec.date_approve or '-----'
                if formatdate != '-----':
                    formatdate = po_rec.date_approve.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_purchase_order.append([po_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_purchase_order)
                        grouped_purchase_order[len_group-1].append(po_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_purchase_order.append([po_rec])
        elif groupby == 'period_by_year':
            purchase_orders_sorted = purchase_orders
            old_formatdate=False
            for po_rec in purchase_orders_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = po_rec.date_approve or '-----'
                if formatdate != '-----':
                    formatdate = po_rec.date_approve.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_purchase_order.append([po_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_purchase_order)
                        grouped_purchase_order[len_group-1].append(po_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_purchase_order.append([po_rec])
        else:
            grouped_purchase_order.append(purchase_orders)
        request.session['my_purchases_history'] = purchase_orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': purchase_orders,
            'page_name': 'purchase',
            'grouped_purchase_order': grouped_purchase_order,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'searchbar_groupby': searchbar_groupby,
            'filterby': filterby,
            'default_url': '/my/purchase',
            'searchbar_inputs': searchbar_inputs,
            'search': search,
            'search_in': search_in,
        })
        # return request.render("purchase.portal_my_purchase_orders", values)
        return request.render("equip3_purchase_vendor_portal.portal_my_purchase_orders_template", values)

    @http.route(['/my/purchase/<int:order_id>/update'], type='http', methods=['POST'], auth="public", website=True)
    def portal_my_purchase_order_update_dates(self, order_id=None, access_token=None, **kw):
        super(CustomerPortal, self).portal_my_purchase_order_update_dates()
        """User update scheduled date on purchase order line.
        """
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        if kw.get('vendor_payment_terms'):
            order_sudo.vendor_payment_terms = str(kw.get('vendor_payment_terms'))
        else:
            return request.redirect(order_sudo.get_portal_url())
        return Response(status=204)

class RFQTenderPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(RFQTenderPortal, self)._prepare_portal_layout_values()

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        values['rfq_tender_count'] = request.env['purchase.order'].search_count(
            ['&','&','|',('state', 'in', ['draft', 'sent', 'retreat']),'&',
             ('state','=','cancel'),
             ('name','ilike','RFQ'),
             ('partner_id', 'in', partner_id_list),
             ('agreement_id','!=',False),
             ('tender_scope','!=','open_tender')])
        values['rfq_open_tender_count'] = request.env['purchase.order'].search_count(
            [('state', 'in', ['draft', 'sent', 'retreat']), ('partner_id', 'in', partner_id_list), ('agreement_id', '!=', False),
             ('tender_scope', '=', 'open_tender')]
        )
        # [
        #     ('state', '!=', 'purchase'),
        #     ('partner_id', 'in', partner_id_list),
        #     ('agreement_id', '!=', False),
            # ('tender_scope', '=', 'open_tender'), ]
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)
        if 'rfq_open_tender_count' in counters:
            values['rfq_open_tender_count'] = request.env['purchase.order'].search_count(
                [('state', 'in', ['draft', 'sent', 'retreat']), ('partner_id', 'in', partner_id_list), ('agreement_id', '!=', False),
                 ('tender_scope', '=', 'open_tender')]
            )
        if 'rfq_tender_count' in counters:
            values['rfq_tender_count'] = request.env['purchase.order'].search_count(
                ['&','&','|',('state', 'in', ['draft', 'sent', 'retreat']),'&',
                 ('state','=','cancel'),
                 ('name','ilike','RFQ'),
                 ('partner_id', 'in', partner_id_list),
                 ('agreement_id','!=',False),
                 ('tender_scope','!=','open_tender')])
        return values

    def _rfq_tender_order_get_page_view_values(self, current, access_token, **kwargs):
        access_url = '/my/rfq-tender/'
        ids = []
        if request.session and 'my_rfq_tender_history' in request.session:
            ids = request.session['my_rfq_tender_history']
        if current.id in ids and (hasattr(current, 'website_url') or hasattr(current, 'access_url')):
            attr_name = 'access_url' if hasattr(current, 'access_url') else 'website_url'
            idx = ids.index(current.id)
            return {
                'prev_record': idx != 0 and access_url + str(current.browse(ids[idx - 1]).id),
                'next_record': idx < len(ids) - 1 and access_url + str(current.browse(ids[idx + 1]).id),
            }
        return {}

    @http.route(['/my/rfq-tender', '/my/rfq-tender/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rfq_tender(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        domain = [('dp','=',False)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': ['&','&','|',('state', 'in', ['draft', 'sent', 'retreat']),'&',('state','=','cancel'),('name','ilike','RFQ'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
            'draft': {'label': _('Request For Quotation'), 'domain': [('state', '=', 'draft'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
            'sent': {'label': _('Sent'), 'domain': [('state', 'in', ['sent']), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
        }
        
        searchbar_inputs = {
            'all': {'input':  'all', 'label': _('Search')},
            'name': {'input': 'name', 'label':   _('Search Purchase Order')},
            'tender': {'input': 'tender', 'label': _('Search Tender Name')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'price_rating': {'input': 'price_rating', 'label': _('Price Rating')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Created Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Created Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Created Date By Year')},
        }
        
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']
        
        search_domain = []
        if search and search_in:
            if search_in in ('name', 'all'):
                search_domain = OR([search_domain, [('name', 'ilike', search)]])
            if search_in in ('tender', 'all'):
                search_domain = OR([search_domain, [('agreement_id.name', 'ilike', search)]])
        domain += search_domain

        # count for pager
        rfq_count = PurchaseOrder.search_count(domain)
        # make pager
        pager = portal_pager(
            url="/my/rfq-tender",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'filterby': filterby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=rfq_count,
            page=page,
            step=self._items_per_page
        )
        
        if groupby == 'price_rating':
            order = "price_rating, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "create_date desc, %s" % order
        
        # search the purchase orders to display, according to the pager data
        rfqs = PurchaseOrder.sudo().search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        
        grouped_rfq = []
        if groupby == 'price_rating':
            # Assuming purchase orders have a 'price_rating' attribute
            rfqs_sorted = sorted(rfqs, key=lambda x: x.price_rating)
            for price_rating, group in groupbyelem(rfqs_sorted, itemgetter('price_rating')):
                grouped_rfq.append(group)
        elif groupby == 'period_by_day':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        elif groupby == 'period_by_month':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        elif groupby == 'period_by_year':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])

        else:
            grouped_rfq.append(rfqs)
        
        request.session['my_rfq_tender_history'] = rfqs.ids[:100]

        # Check boolean for show column price ratting
        IrConfigParam = request.env['ir.config_parameter'].sudo()
        is_price_ratting_rfq_tender = IrConfigParam.get_param('is_price_ratting_rfq_tender', False)

        values.update({
            'date': date_begin,
            'rfqs': rfqs,
            'page_name': 'rfq_tender',
            'grouped_rfq': grouped_rfq,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/rfq-tender',
            'is_price_ratting_rfq_tender':is_price_ratting_rfq_tender,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'search': search,
            'search_in': search_in,
        })
        return request.render("equip3_purchase_vendor_portal.rfq_tender_submission_portal_template", values)

    @http.route(['/my/rfq-tender/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfq_tender_form(self, quote_id, report_type=None, access_token=None, message=False, download=False, **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type,
                                     report_ref='purchase.report_purchase_quotation', download=download)
        values1 = {
            'token': access_token,
            'rfq_tenders': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
            'page_name':'rfq_tender',
        }

        values2 = self._rfq_tender_order_get_page_view_values(quote_sudo, access_token, **kw)
        values = {**values1, **values2}
        return request.render('equip3_purchase_vendor_portal.portal_rfq_tender_form_templates', values)

    def _rfq_open_tender_order_get_page_view_values(self, current, access_token, **kwargs):
        access_url = '/my/rfq-open-tender/'
        if request.session:
            ids = request.session['my_rfq_open_tender_history']
        if current.id in ids and (hasattr(current, 'website_url') or hasattr(current, 'access_url')):
            attr_name = 'access_url' if hasattr(current, 'access_url') else 'website_url'
            idx = ids.index(current.id)
            return {
                'prev_record': idx != 0 and access_url + str(current.browse(ids[idx - 1]).id),
                'next_record': idx < len(ids) - 1 and access_url + str(current.browse(ids[idx + 1]).id),
            }
        return {}

    @http.route(['/my/rfq-open-tender', '/my/rfq-open-tender/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_rfq_open_tender(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, search=None, search_in='all', groupby='none', **kw):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']

        domain = [('dp','=',False)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]
            
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search')},
        }
        
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'price_rating': {'input': 'price_rating', 'label': _('Price Rating')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Order Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Order Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Order Date By Year')},
        }
        
        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc, id desc'},
            'name': {'label': _('Name'), 'order': 'name asc, id asc'},
            'amount_total': {'label': _('Total'), 'order': 'amount_total desc, id desc'},
        }
        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': [('state', 'in', ['draft', 'sent', 'retreat']),('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','=','open_tender')]},
            'draft': {'label': _('Request For Quotation'), 'domain': [('state', '=', 'draft'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','=','open_tender')]},
            'sent': {'label': _('Sent'), 'domain': [('state', 'in', ['sent']), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','=','open_tender')]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        rfq_count = PurchaseOrder.search_count(domain)
        
        # if search and search in
        if search and search_in:
            domain = AND([domain, ['|', ('name', 'ilike', search), ('agreement_id.name', 'ilike', search)]])
        
        # make pager
        pager = portal_pager(
            url="/my/rfq-open-tender",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby, 'search_in': search_in, 'search': search, 'groupby': groupby},
            total=rfq_count,
            page=page,
            step=self._items_per_page
        )
        
        if groupby == 'price_rating':
            order = "price_rating, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "date_order desc, %s" % order
        
        # search the purchase orders to display, according to the pager data
        rfqs = PurchaseOrder.sudo().search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        # grouped_rfq = [rfqs] if groupby != 'price_rating' else [rfqs.concat(*g) for _, g in groupbyelem(rfqs, itemgetter('price_rating'))]
        grouped_rfq = []
        if groupby == 'price_rating':
            rfqs_sorted = sorted(rfqs, key=lambda x: x.price_rating)
            for price_rating, group in groupbyelem(rfqs_sorted, itemgetter('price_rating')):
                grouped_rfq.append(group)
        elif groupby == 'period_by_day':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.date_order.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        elif groupby == 'period_by_month':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.date_order.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        elif groupby == 'period_by_year':
            rfqs_sorted = rfqs
            old_formatdate=False
            for rfqs_rec in rfqs_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = rfqs_rec.date_order.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_rfq.append([rfqs_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_rfq)
                        grouped_rfq[len_group-1].append(rfqs_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_rfq.append([rfqs_rec])
        else:
            grouped_rfq.append(rfqs)
        request.session['my_rfq_open_tender_history'] = rfqs.ids[:100]

        # Check boolean for show column price ratting
        IrConfigParam = request.env['ir.config_parameter'].sudo()
        is_price_ratting_rfq_tender = IrConfigParam.get_param('is_price_ratting_rfq_tender', False)

        values.update({
            'date': date_begin,
            'rfq_open_tenders': rfqs,
            'grouped_rfq': grouped_rfq,
            'page_name': 'rfq_open_tender',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'search_in': search_in,
            'search': search,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'default_url': '/my/rfq-open-tender',
            'is_price_ratting_rfq_tender':is_price_ratting_rfq_tender,
        })
        return request.render("equip3_purchase_vendor_portal.rfq_open_tender_submission_portal_template", values)

    @http.route(['/my/rfq-open-tender/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_rfq_open_tender_form(self, quote_id, report_type=None, access_token=None, message=False, download=False, **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type,
                                     report_ref='purchase.report_purchase_quotation', download=download)
        values1 = {
            'token': access_token,
            'rfq_open_tender': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
            'page_name':'rfq_open_tender',
        }
        if 'my_rfq_open_tender_history' not in request.session:
            request.session['my_rfq_open_tender_history'] = quote_sudo.ids[:100]
        values2 = self._rfq_open_tender_order_get_page_view_values(quote_sudo, access_token, **kw)
        values = {**values1, **values2}
        return request.render('equip3_purchase_vendor_portal.portal_rfq_open_tender_form_templates', values)


class OpenTenderPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):

        values = super(OpenTenderPortal, self)._prepare_portal_layout_values()
        tender_obj = request.env['purchase.agreement']
        domain = [
            ('tender_scope', '=', 'open_tender'), 
            ('state', 'not in', ['draft', 'cancel']), 
            '|', 
            ('partner_ids', 'in', [request.env.user.partner_id.id]), 
            ('partner_ids', '=', False)
            ]
        tenders = tender_obj.sudo().search(domain)
        tender_count = tender_obj.sudo().search_count(domain)
        values['tender_count'] = tender_count
        values['tenders'] = tenders
        return values

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'tender_count' in counters:
            tender_obj = request.env['purchase.agreement']
            domain = [
                ('tender_scope', '=', 'open_tender'), 
                ('state', 'not in', ['draft', 'cancel']), 
                '|', 
                ('partner_ids', 'in', [request.env.user.partner_id.id]), 
                ('partner_ids', '=', False)
                ]
            tender_count = tender_obj.sudo().search_count(domain)
            values['tender_count'] = tender_count
        return values

    def _prepare_open_tender_public_values(self):
        values = {}
        tender_obj = request.env['purchase.agreement']
        domain = [
            ('tender_scope', '=', 'open_tender'), 
            ('state', 'not in', ['draft', 'cancel']), 
            '|', 
            ('partner_ids', 'in', [request.env.user.partner_id.id]), 
            ('partner_ids', '=', False)
            ]
        tenders = tender_obj.sudo().search(domain)
        tender_count = tender_obj.sudo().search_count(domain)
        values['tender_count'] = tender_count
        values['tenders'] = tenders
        return values

    @http.route(['/open_tender', '/open_tender/page/<int:page>'], type='http', auth="public", website=True)
    def portal_home_open_tender(self, page=1, sortby=None, filterby=None, search=None, search_in='all', groupby='none',tender_dashboard_selection=False, **kw):
        Tender_sudo = request.env['purchase.agreement'].sudo()
        values = self._prepare_open_tender_public_values()
        searchbar_sortings = {
            'create_date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Tender Ref'), 'order': 'name'},
        }
        searchbar_inputs = {
            'all': {'input': 'all', 'label': _('Search')},
        }

        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'status': {'input': 'status', 'label': _('Status')},
            'period_by_day': {'input': 'create_date_day', 'label': _('Created Date By Day')},
            'period_by_month': {'input': 'create_date_month', 'label': _('Created Date By Month')},
            'period_by_year': {'input': 'create_date_year', 'label': _('Created Date By Year')},
        }

        domain = [('tender_scope', '=', 'open_tender'), ('state', 'not in', ['draft', 'cancel']), ('state2', 'not in', ['pending', 'cancel'])]
        
        if tender_dashboard_selection == 'active_tender':
            domain = [('partner_ids', 'in', request.env.user.partner_id.ids),('tender_scope','in',('open_tender', 'invitation_tender')),('state2','in',('bid_submission', 'bid_selection'))]
        

        if tender_dashboard_selection == 'total_tender':
            domain = [('partner_ids', 'in', request.env.user.partner_id.ids),('tender_scope','in',('open_tender', 'invitation_tender')),('state2','in',('bid_submission', 'bid_selection', 'closed', 'cancel', 'pending'))]
        

        if tender_dashboard_selection == 'doc_submit_tender':
            domain = [('partner_ids', 'in', request.env.user.partner_id.ids),
            ('tender_scope','in',('open_tender', 'invitation_tender')),('purchase_order_ids.partner_id','=',request.env.user.partner_id.id)]


        if tender_dashboard_selection == 'won_tender':
            domain = [('partner_ids', 'in', request.env.user.partner_id.ids),
            ('tender_scope','in',('open_tender', 'invitation_tender')),('purchase_order_ids.partner_id','=',request.env.user.partner_id.id),('purchase_order_ids.state','in',('purchase','done'))]

        searchbar_filters = {
            'none': {'label': _('None'), 'domain': domain},
            'bid_submission': {'label': _('Bid Submission'), 'domain': [('state2', '=', 'bid_submission')]},
            'bid_selection': {'label': _('Bid Selection'), 'domain': [('state2', '=', 'bid_selection')]},
        }
        # default sort by value
        if not sortby:
            sortby = 'create_date'
        order = searchbar_sortings[sortby]['order']
        
        # default filter by value
        if not filterby:
            filterby = 'none'
        
        domain = AND([searchbar_filters[filterby]['domain']])

        # if search and search in
        if search and search_in:
            domain = AND([domain, ['|', ('name', 'ilike', search), ('tender_name', 'ilike', search)]])
            
        tender_count = Tender_sudo.search_count(domain)
        # pager
        pager = portal_pager(
            url="/open_tender",
            url_args = {'sortby': sortby, 'search_in': search_in, 
                        'search': search, 'filterby': filterby, 
                        'groupby': groupby,'tender_dashboard_selection':tender_dashboard_selection},
            total=tender_count,
            page=page,
            step=self._items_per_page
        )

        if groupby == 'status':
            order = "state, %s" % order

        if groupby in ['period_by_day','period_by_month','period_by_year']:
            order = "create_date desc, %s" % order


        tenders = Tender_sudo.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        # grouped_tenders = [tenders] if groupby != 'status' else [Tender_sudo.concat(*g) for _, g in groupbyelem(tenders, itemgetter('state'))]
        
        grouped_tenders = []
        if groupby == 'status':
            # Sort tenders by status
            tenders_sorted = sorted(tenders, key=lambda x: x.state)
            current_group = []
            current_status = None
            
            for tender in tenders_sorted:
                if tender.state != current_status:
                    # Start a new group
                    if current_group:
                        grouped_tenders.append(current_group)
                    current_group = [tender]
                    current_status = tender.state
                else:
                    # Add to current group
                    current_group.append(tender)
            # Append the last group
            if current_group:
                grouped_tenders.append(current_group)
        elif groupby == 'period_by_day':
            tenders_sorted = tenders
            old_formatdate=False
            for tender_rec in tenders_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = tender_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m-%d")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_tenders.append([tender_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_tenders)
                        grouped_tenders[len_group-1].append(tender_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_tenders.append([tender_rec])
        elif groupby == 'period_by_month':
            tenders_sorted = tenders
            old_formatdate=False
            for tender_rec in tenders_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = tender_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y-%m")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_tenders.append([tender_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_tenders)
                        grouped_tenders[len_group-1].append(tender_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_tenders.append([tender_rec])
        elif groupby == 'period_by_year':
            tenders_sorted = tenders
            old_formatdate=False
            for tender_rec in tenders_sorted:
                local_timezone = pytz.timezone(request.env.user.tz)
                formatdate = tender_rec.create_date.replace(tzinfo=pytz.utc).strftime("%Y")
                if not old_formatdate:
                    old_formatdate = formatdate
                    grouped_tenders.append([tender_rec])
                else:
                    if formatdate == old_formatdate:
                        len_group = len(grouped_tenders)
                        grouped_tenders[len_group-1].append(tender_rec)
                    else:
                        old_formatdate = formatdate
                        grouped_tenders.append([tender_rec])
        else:
            # If not grouped by status, keep tenders as they are
            grouped_tenders.append(tenders)
        
        
        values.update({
            'open_tenders': tenders,
            'grouped_tenders': grouped_tenders,
            'tender_dashboard_selection':tender_dashboard_selection,
            'page_name': 'open_tender',
            'default_url': '/open_tender',
            'tender_count': tender_count,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'search_in': search_in,
            'sortby': sortby,
            'groupby': groupby,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("equip3_purchase_vendor_portal.portal_open_tenders", values)

    @http.route(['/open_tender/<int:tender_id>'], type='http', auth="public", website=True)
    def portal_open_tender_form(self, tender_id, report_type=None, access_token=None, message=False, download=False,tender_dashboard_selection=False, **kw):
        if tender_dashboard_selection == 'False':
            tender_dashboard_selection = False
        tender_sudo = request.env['purchase.agreement'].sudo().search(
            [('id', '=', tender_id)], limit=1)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=tender_sudo, report_type=report_type, report_ref='sh_po_tender_management.action_report_purchase_tender', download=download)

        rfq_order = request.env['purchase.order'].sudo().search(
            [('agreement_id', '=', tender_sudo.id),('state','!=','cancel')])
        purchase_order = request.env['purchase.order'].sudo().search(
            [('agreement_id', '=', tender_sudo.id),('state','=','purchase')])
        jenis_user = 'public'
        if request.env.user == request.env.ref('base.public_user'):
            jenis_user = 'public'
        else: 
            if request.env.user.partner_id.is_vendor:
                jenis_user = 'is_vendor'
            else:
                jenis_user = 'bukan_vendor'
        values = {
            'token': access_token,
            'open_tender': tender_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': tender_sudo.partner_id.id,
            'report_type': 'html',
            'page_name': 'open_tender',
            'jumlah_peserta':len(rfq_order.mapped('partner_id')),
            'participants':rfq_order,
            'winners':purchase_order,
            'tender_dashboard_selection':tender_dashboard_selection,
            'jenis_user':jenis_user,
            # 'purchase_order_id': tender_sudo.purchase_order_ids and tender_sudo.purchase_order_ids[-1] or False,
            'purchase_order_id': next((purchase for purchase in tender_sudo.purchase_order_ids if purchase.partner_id == request.env.user.partner_id), False)
        }
        return request.render('equip3_purchase_vendor_portal.portal_open_tender_form_template', values)

    @http.route(['/my/open_tender', '/my/open_tender/page/<int:page>'], type='http', auth="public", website=True)
    def portal_my_home_open_tender(self, page=1):
        values = self._prepare_portal_layout_values()
        tender_obj = request.env['purchase.agreement']
        domain = [
            ('state', 'not in', ['draft', 'cancel']),
            '|',
            ('partner_ids', 'in', [request.env.user.partner_id.id]),
            ('partner_ids', '=', False)
        ]

        tender_count = tender_obj.sudo().search_count(domain)

        pager = portal_pager(
            url="/my/tender",
            total=tender_count,
            page=page,
        )

        tenders = tender_obj.sudo().search(
            domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'tenders': tenders,
            'page_name': 'open_tender',
            'pager': pager,
            'default_url': '/my/open_tender',
            'tender_count': tender_count,
        })
        return request.render("sh_po_tender_portal.portal_my_tenders", values)

    @http.route(['/my/open_tender/<int:tender_id>'], type='http', auth="user", website=True)
    def portal_my_open_tender_form(self, tender_id, report_type=None, access_token=None, message=False, download=False, **kw):
        tender_sudo = request.env['purchase.agreement'].sudo().search(
            [('id', '=', tender_id)], limit=1)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=tender_sudo, report_type=report_type, report_ref='sh_po_tender_management.action_report_purchase_tender', download=download)
        values = {
            'token': access_token,
            'tender': tender_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': tender_sudo.partner_id.id,
            'report_type': 'html',
        }
        return request.render('sh_po_tender_portal.portal_tender_form_template', values)

    @http.route(['/open_tender/rfq/create'], type='http', auth='user', website=True, csrf=False)
    def portal_open_tender_create_rfq(self, **kw):
        dic = {}
        # import pdb;pdb.set_trace()
        purchase_tender = request.env['purchase.agreement'].sudo().search(
            [('id', '=', int(kw.get('tender_id')))], limit=1)

        purchase_order = request.env['purchase.order'].sudo().search(
            [('agreement_id', '=', purchase_tender.id), ('partner_id', '=', request.env.user.partner_id.id), ('state', 'in', ['draft'])])
        for purchase in purchase_order:
            purchase.sh_cancel()
        # if purchase_order and len(purchase_order.ids) > 1:
        #     dic.update({
        #         'url': '/my/rfq'
        #     })
        # elif purchase_order and len(purchase_order.ids) == 1:
        #     dic.update({
        #         'url': '/my/rfq/'+str(purchase_order.id)
        #     })
        # else:
        order_dic = {}
        order_dic.update({
            'partner_id': request.env.user.partner_id.id,
            'agreement_id': purchase_tender.id,
            'date_order': fields.Datetime.now(),
            'user_id': purchase_tender.sh_purchase_user_id.id,
            'branch_id': purchase_tender.branch_id.id,
            'state': 'draft',
            'is_submit_quotation': True,
            'vendor_payment_terms': kw.get('vendor_payment_terms') or '',
            'term_condition_box': kw.get('rfq_note') or '',
            'service_level_agreement_box': kw.get('agreement_note') or '',
            'is_assets_orders': purchase_tender.is_assets_orders,
            'is_goods_orders': purchase_tender.is_goods_orders,
            'is_services_orders': purchase_tender.is_services_orders,
            'origin': purchase_tender.name,
        })
        if purchase_tender.sh_agreement_deadline:
            order_dic.update({
                'date_planned': purchase_tender.sh_agreement_deadline,
            })
        else:
            order_dic.update({
                'date_planned': fields.Datetime.now(),
            })
        if purchase_tender.set_single_delivery_date:
            order_dic.update({
                'is_delivery_receipt': purchase_tender.set_single_delivery_date,
            })
        if purchase_tender.destination_warehouse_id:
            order_dic.update({
                'destination_warehouse_id': purchase_tender.destination_warehouse_id.id,
            })
        if purchase_tender.set_single_delivery_destination:
            order_dic.update({
                'is_single_delivery_destination': purchase_tender.set_single_delivery_destination,
            })
        ctx = request.env.context.copy()
        ctx['goods_order'] = purchase_tender.is_goods_orders
        ctx['services_good'] = purchase_tender.is_services_orders
        ctx['assets_orders'] = purchase_tender.is_assets_orders
        purchase_order_id = request.env['purchase.order'].sudo().with_context(ctx).create(
            order_dic)
        line_ids = []
        for line in purchase_tender.sh_purchase_agreement_line_ids:
            line_vals = {
                'order_id': purchase_order_id.id,
                'product_id': line.sh_product_id.id,
                'agreement_id': purchase_tender.id,
                'branch_id': purchase_tender.branch_id.id,
                'status': 'draft',
                'name': line.sh_product_id.name,
                'product_qty': line.sh_qty,
                'product_uom': line.sh_product_id.uom_id.id,
                'price_unit': float(kw.get(str(line.id)).replace(',','')),
                'base_price': line.sh_price_unit
            }
            if purchase_tender.sh_agreement_deadline:
                line_vals.update({
                    'date_planned': purchase_tender.sh_agreement_deadline,
                })
            else:
                line_vals.update({
                    'date_planned': fields.Datetime.now(),
                })
            if line.dest_warehouse_id:
                line_vals.update({
                    'destination_warehouse_id': line.dest_warehouse_id.id,
                })
            line_ids.append((0, 0, line_vals))
        purchase_order_id.order_line = line_ids

        message = "Quotation Created"
        return request.redirect('/open_tender/'+str(purchase_tender.id)+"?message="+message)

    @http.route(['/attachment/download', ], type='http', auth='user')
    def download_file(self, attachment_id):
        # Check if this is a valid attachment id
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "res_model", "res_id", "type", "url"]
        )
        if attachment:
            attachment = attachment[0]
        if attachment["type"] == "url":
            if attachment["url"]:
                return redirect(attachment["url"])
            else:
                return request.not_found()
        elif attachment["datas"]:
            data = io.BytesIO(base64.standard_b64decode(attachment["datas"]))
            return http.send_file(data, filename=attachment['name'], as_attachment=True)
        else:
            return request.not_found()
