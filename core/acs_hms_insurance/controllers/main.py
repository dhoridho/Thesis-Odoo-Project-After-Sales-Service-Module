# -*- coding: utf-8 -*-

from odoo import http, fields, _
from odoo.http import request
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo import fields as odoo_fields, http, tools, _, SUPERUSER_ID
import base64


class HMSPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):
        values = super(HMSPortal, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id.commercial_partner_id
        insurance_claim_count = 0
        if request.env['hms.insurance.claim'].check_access_rights('read', raise_exception=False):
            insurance_claim_count = request.env['hms.insurance.claim'].search_count([('patient_id.partner_id', '=', partner.id),('state','not in',['draft','cancel'])])
        values.update({
            'insurance_claim_count': insurance_claim_count,
        })
        return values

    @http.route(['/my/insuranceclaims', '/my/insuranceclaims/page/<int:page>'], type='http', auth="user", website=True)
    def my_insurance_claims(self, page=1, sortby=None, **kw):
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
            url="/my/insuranceclaims",
            url_args={},
            total=values['insurance_claim_count'],
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        partner = request.env.user.partner_id.commercial_partner_id

        insurance_claims = request.env['hms.insurance.claim'].sudo().search(
            [('patient_id.partner_id', '=', partner.id),
            ('state','not in',['draft','cancel'])],
            order=order, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'sortings': sortings,
            'sortby': sortby,
            'insurance_claims': insurance_claims,
            'page_name': 'insurance_claim',
            'default_url': '/my/insuranceclaims',
            'searchbar_sortings': sortings,
            'pager': pager
        })
        return request.render("acs_hms_insurance.insurance_claims", values)

    @http.route(['/my/insuranceclaims/<int:claim>'], type='http', auth="user", website=True)
    def my_insurance_claim(self, claim=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('hms.insurance.claim', claim, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        return request.render("acs_hms_insurance.my_insurance_claim", {'insurance_claim': order_sudo})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: