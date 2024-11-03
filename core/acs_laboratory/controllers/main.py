# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
import base64

class ACSHms(http.Controller):

    @http.route(['/validate/patientlaboratorytest/<labresult_unique_code>'], type='http', auth="public", website=True)
    def labresult_details(self, labresult_unique_code, **post):
        if labresult_unique_code:
            labresult = request.env['patient.laboratory.test'].sudo().search([('unique_code','=',labresult_unique_code)], limit=1)
            if labresult:
                return request.render("acs_laboratory.acs_labresult_details", {'labresult': labresult})
        return request.render("acs_hms.acs_no_details")


class HMSPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(HMSPortal, self)._prepare_portal_layout_values()
        lab_result_count = 0
        if request.env['patient.laboratory.test'].check_access_rights('read', raise_exception=False):
            lab_result_count = request.env['patient.laboratory.test'].search_count([])

        lab_request_count = 0
        if request.env['acs.laboratory.request'].check_access_rights('read', raise_exception=False):
            lab_request_count = request.env['acs.laboratory.request'].search_count([])
        values.update({
            'lab_result_count': lab_result_count,
            'lab_request_count': lab_request_count,
        })
        return values

    #Lab Result
    @http.route(['/my/lab_results', '/my/lab_results/page/<int:page>'], type='http', auth="user", website=True)
    def my_lab_results(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        if not sortby:
            sortby = 'date'

        sortings = {
            'date': {'label': _('Newest'), 'order': 'date_analysis desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

        order = sortings.get(sortby, sortings['date'])['order']
 
        pager = portal_pager(
            url="/my/lab_results",
            url_args={},
            total=values['lab_result_count'],
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected

        lab_results = request.env['patient.laboratory.test'].search([],
            order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'sortings': sortings,
            'sortby': sortby,
            'lab_results': lab_results,
            'page_name': 'lab_result',
            'default_url': '/my/lab_results',
            'searchbar_sortings': sortings,
            'pager': pager
        })
        return request.render("acs_laboratory.lab_results", values)

    @http.route(['/my/lab_results/<int:result_id>'], type='http', auth="user", website=True)
    def my_lab_test_result(self, result_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('patient.laboratory.test', result_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return request.render("acs_laboratory.my_lab_test_result", {'lab_result': order_sudo})

    #Lab Request
    @http.route(['/my/lab_requests', '/my/lab_requests/page/<int:page>'], type='http', auth="user", website=True)
    def my_lab_requests(self, page=1, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        user = request.env.user
        if not sortby:
            sortby = 'date'

        sortings = {
            'date': {'label': _('Newest'), 'order': 'date desc'},
            'name': {'label': _('Name'), 'order': 'name'},
        }

        order = sortings.get(sortby, sortings['date'])['order']
 
        pager = portal_pager(
            url="/my/lab_requests",
            url_args={},
            total=values['lab_request_count'],
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        lab_requests = request.env['acs.laboratory.request'].search([],
            order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'sortings': sortings,
            'sortby': sortby,
            'lab_requests': lab_requests,
            'page_name': 'lab_request',
            'default_url': '/my/lab_requests',
            'searchbar_sortings': sortings,
            'pager': pager
        })
        return request.render("acs_laboratory.lab_requests", values)

    @http.route(['/my/lab_requests/<int:request_id>'], type='http', auth="user", website=True)
    def my_lab_test_request(self, request_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('acs.laboratory.request', request_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return request.render("acs_laboratory.my_lab_test_request", {'lab_request': order_sudo})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: