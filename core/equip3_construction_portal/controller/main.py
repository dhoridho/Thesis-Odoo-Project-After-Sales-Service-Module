# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import http, fields
from odoo.http import request, Response
import json
import base64
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.sh_po_tender_portal.controllers.portal import TenderRFQPOrtal
# from odoo.tools import date_utils, groupby as groupbyelem
#
# from odoo import fields, api, SUPERUSER_ID, _
# from xlrd import open_workbook
# from dateutil.relativedelta import relativedelta
# from odoo.osv.expression import AND
# from operator import itemgetter
from collections import OrderedDict
from odoo.addons.purchase.controllers.portal import CustomerPortal
# from odoo.addons.sh_po_tender_portal.controllers.portal import TenderRFQPOrtal
from odoo import models, fields, api, _

class CustomPurchaseRFQPOrtal(TenderRFQPOrtal):

    @http.route(['/subcon/tender/retreat'], type='http', auth="user", website=True, csrf=False)
    def subcon_tender_retreat(self, access_token=None,is_subcon_tender=False, **kw):
        if kw.get('order_id'):
            purchase_order = request.env['purchase.order'].sudo().browse(int(kw.get('order_id')))
            purchase_order.sudo().write({
                'state': 'retreat'
            })
        url = '/subcon/tender/update' + str(kw.get('order_id'))
        if is_subcon_tender:
            url += "?is_subcon_tender=True"
        return url

    @http.route(['/subcon/tender/update'], type='http', auth="user", website=True, csrf=False)
    def custom_subcon_tender_update(self, access_token=None, is_subcon_tender=False, **kw):
        print('----- custom_subcon_tender_update kw --------', kw)
        if kw.get('order_id'):
            purchase_order = request.env['purchase.order'].sudo().search(
                [('id', '=', int(kw.get('order_id')))], limit=1)
            if purchase_order and purchase_order.agreement_id.state != 'closed':
                # if purchase_order.order_line:
                if purchase_order.variable_line_ids:
                    for k, v in kw.items():
                        # if k != 'order_id' and 'qty' not in k and k.isdigit():
                        variable_lines = request.env['rfq.variable.line'].sudo().search(
                            [('variable_id', '=', purchase_order.id), ('id', '=', int(kw['variable_id']))], limit=1)
                        if variable_lines:
                            if 'unit_price' in kw.keys():
                                updated_price = kw['unit_price']
                                if ',' in updated_price:
                                    updated_price = updated_price.replace(",", "")
                                variable_lines.sudo().write({
                                    'sub_total': float(updated_price),
                                })
                            if 'quantity' in kw.keys():
                                variable_lines.sudo().write({
                                    'quantity': float(kw['quantity']),
                                })
                        variable_lines.onchange_total()
                print('---------- total_all -----------', purchase_order.total_all)
                # if k == 'rfq_note':
                if 'rfq_note' in kw.keys() and len(kw['rfq_note']):
                    purchase_order.sudo().write({
                        'term_condition_box': kw.get(k),
                    })
                if 'agreement_note' in kw.keys() and len(kw['agreement_note']):
                    purchase_order.sudo().write({
                        'service_level_agreement_box': kw.get(k),
                    })
        print('---------purchase_order------------', purchase_order)
        url = '/subcon/tender/update' + str(kw.get('order_id'))
        if is_subcon_tender:
            url+= "?is_subcon_tender=True"
        return request.redirect(url)


class SubconTenderSubmissionPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(SubconTenderSubmissionPortal, self)._prepare_portal_layout_values()

        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        values['st_submission_count'] = request.env['purchase.order'].search_count(
            ['&','&','|',('state', 'in', ['draft', 'sent', 'retreat']),'&',
             ('state','=','cancel'),
             ('name','ilike','RFQ'),
             ('partner_id', 'in', partner_id_list),
             ('agreement_id','!=',False),
             ('tender_scope','!=','open_tender')])
        print("--------------- value ------- upper ---------", values)
        return values

    def _subcon_tender_submission_order_get_page_view_values(self, current, access_token, **kwargs):
        access_url = '/my/subcon/tender/submission'
        if request.session:
            ids = request.session['my_subcon_tender_history']
        if current.id in ids and (hasattr(current, 'website_url') or hasattr(current, 'access_url')):
            attr_name = 'access_url' if hasattr(current, 'access_url') else 'website_url'
            idx = ids.index(current.id)
            return {
                'prev_record': idx != 0 and access_url + str(current.browse(ids[idx - 1]).id),
                'next_record': idx < len(ids) - 1 and access_url + str(current.browse(ids[idx + 1]).id),
            }
        return {}

    @http.route(['/my/subcon/tender/submission', '/my/subcon/tender/submission/page/<int:page>'], type='http', auth="user", website=True)
    def portal_subcon_tender_submission(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']
        domain = [('po','=',False)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]
        #
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
        #
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': ['&','&','|',('state', 'in', ['draft', 'sent', 'retreat']),'&',('state','=','cancel'),('name','ilike','RFQ'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
            'draft': {'label': _('Request For Quotation'), 'domain': [('state', '=', 'draft'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
            'sent': {'label': _('Sent'), 'domain': [('state', 'in', ['sent']), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
        }
        # # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        st_submission_count = PurchaseOrder.search_count(domain)
        dmn = [('is_subcontracting', '=', True), ('partner_id', 'in', partner_id_list),
               ('tender_scope', '=', 'invitiation_tender')]
        # st_submission_count = PurchaseOrder.search_count(dmn)
        # make pager
        pager = portal_pager(
            url="/my/subcon/tender/submission",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=values['st_submission_count'],
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        subcon_tender_sub = PurchaseOrder.sudo().search(
            domain,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_subcon_tender_history'] = subcon_tender_sub.ids[:100]
        print('--------- PurchaseOrder ------->', PurchaseOrder)
        print('------- subcon_tender_sub ------>', subcon_tender_sub)
        values.update({
            'date': date_begin,
            'rfqs': subcon_tender_sub,
            'page_name': 'subcon_tender',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/subcon/tender/submission',
        })
        return request.render("equip3_construction_portal.open_subcon_tender_submission_template", values)

    @http.route(['/my/subcon/tender/submission/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_subcon_tender_submission_form(self, quote_id, report_type=None, access_token=None, message=False, download=False,
                                  **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type,
                                     report_ref='purchase.report_purchase_quotation', download=download)
        values1 = {
            'token': access_token,
            'subcon_tenders': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
            'page_name': 'subcon_tender',
        }

        values2 = self._subcon_tender_submission_order_get_page_view_values(quote_sudo, access_token, **kw)
        values = {**values1, **values2}
        return request.render('equip3_construction_portal.portal_subcon_tender_submission_form_templates', values)

    @http.route(['/subcon/tender/update<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_subcon_tender_update(self, quote_id=None, report_type=None, access_token=None, message=False, download=False,
                              is_subcon_tender=False, **kw):
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
        # portal_template = "equip3_purchase_vendor_portal.sh_portal_my_rfq_order_update"
        if is_subcon_tender:
            values.update({
                'quotes': False,
                'subcon_tenders': quote_sudo,
                'page_name': 'subcon_tender',
            })
            portal_template = "equip3_construction_portal.portal_subcon_tender_submission_form_templates"
        return request.render(portal_template, values)

class SubconPurchaseOrderPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(SubconPurchaseOrderPortal, self)._prepare_portal_layout_values()
        partner_id_list = []
        partner_id_list.append(request.env.user.partner_id.id)
        partner_obj = request.env['res.partner'].search([('parent_id', '=', request.env.user.partner_id.id)])
        for child_id in partner_obj:
            partner_id_list.append(child_id.id)

        values['subcon_po_count'] = request.env['purchase.order'].search_count(
            [('partner_id', 'in', partner_id_list),
             ('po', '=', True),
             ('tender_scope','!=','open_tender'),
             ('state1','=','purchase'),
             ('is_subcontracting', '=', True)])
        print("--------------- value ------- upper ---------", values)
        return values

    def _subcon_purchase_order_get_page_view_values(self, current, access_token, **kwargs):
        access_url = '/my/subcon/purchase/order'
        if request.session:
            ids = request.session['my_subcon_po_history']
        if current.id in ids and (hasattr(current, 'website_url') or hasattr(current, 'access_url')):
            attr_name = 'access_url' if hasattr(current, 'access_url') else 'website_url'
            idx = ids.index(current.id)
            return {
                'prev_record': idx != 0 and access_url + str(current.browse(ids[idx - 1]).id),
                'next_record': idx < len(ids) - 1 and access_url + str(current.browse(ids[idx + 1]).id),
            }
        return {}

    @http.route(['/my/subcon/purchase/order', '/my/subcon/purchase/order/page/<int:page>'], type='http', auth="user", website=True)
    def portal_subcon_purchase_order(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        PurchaseOrder = request.env['purchase.order']
        domain = [('po', '=', True)]

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin),
                       ('create_date', '<=', date_end)]
        #
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
        #
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': ['&','&','|',('state', 'in', ['draft', 'sent', 'retreat']),'&',('state','=','cancel'),('name','ilike','RFQ'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
            'draft': {'label': _('Request For Quotation'), 'domain': [('state', '=', 'draft'), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
            'sent': {'label': _('Sent'), 'domain': [('state', 'in', ['sent']), ('partner_id', 'in', partner_id_list),('agreement_id','!=',False),('tender_scope','!=','open_tender')]},
        }
        # # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        # count for pager
        submission_count = PurchaseOrder.search_count(domain)
        dmn = [('is_subcontracting', '=', True), ('partner_id', 'in', partner_id_list),
               ('tender_scope', '=', 'invitiation_tender')]
        domain_new = [('partner_id', 'in', partner_id_list),
         ('po', '=', True),
         ('tender_scope', '!=', 'open_tender'),
         ('state1', '=', 'purchase'),
         ('is_subcontracting', '=', True)]
        submission_count = PurchaseOrder.search_count(dmn)
        # make pager
        pager = portal_pager(
            url="/my/subcon/purchase/order",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=values['subcon_po_count'],
            page=page,
            step=self._items_per_page
        )
        # search the purchase orders to display, according to the pager data
        subcon_po_sub = PurchaseOrder.sudo().search(
            domain_new,
            order=order,
            limit=self._items_per_page,
            offset=pager['offset']
        )
        request.session['my_subcon_po_history'] = subcon_po_sub.ids[:100]
        print('--------- subcon_po_sub ------->', subcon_po_sub)
        print('--------- PurchaseOrder ------->', PurchaseOrder)
        values.update({
            'date': date_begin,
            'rfqs': subcon_po_sub,
            'page_name': 'subcon_po',
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'default_url': '/my/subcon/purchase/order',
        })
        return request.render("equip3_construction_portal.ba_subcon_purchase_order_template", values)

    @http.route(['/my/subcon/purchase/order/<int:quote_id>'], type='http', auth="user", website=True)
    def portal_my_subcon_purchase_order_form(self, quote_id, report_type=None, access_token=None, message=False,
                                                download=False,
                                                **kw):
        quote_sudo = request.env['purchase.order'].sudo().browse(quote_id)
        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=quote_sudo, report_type=report_type,
                                     report_ref='purchase.report_purchase_quotation', download=download)
        values1 = {
            'token': access_token,
            'subcon_po_quote': quote_sudo,
            'message': message,
            'bootstrap_formatting': True,
            'partner_id': quote_sudo.partner_id.id,
            'report_type': 'html',
            'page_name': 'subcon_po',
        }

        values2 = self._subcon_purchase_order_get_page_view_values(quote_sudo, access_token, **kw)
        values = {**values1, **values2}
        return request.render('equip3_construction_portal.ba_portal_subcon_purchase_order_form_templates', values)

