# -*- coding: utf-8 -*-

from odoo import http,fields, _
from odoo.http import request, route
import json
import base64
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo import fields, api, SUPERUSER_ID, tools


class CustomerSignature(http.Controller):
    
    @http.route(['/customer/signature/1'], type='http', auth="public", website=True)
    def create_signature(self, **kw):
        values = {}
        signature_id = request.env['sale.customer.esignature'].with_context(active_test=False).search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        if signature_id:
            values['terms_conditions'] = signature_id.terms_conditions
            if signature_id.active:
                return request.redirect('/customer/signature/6')
        return request.render("equip3_sale_esignature.customer_signature_form_view", values)

    @http.route(['/customer/signature/2'], type='http', auth="public", website=True)
    def select_country(self, **kw):
        partner = request.env.user.partner_id
        pic_partner_id = partner.child_ids.filtered(lambda r: r.type == 'pic')
        countries = request.env["res.country"].sudo().search([])
        country_states = request.env["res.country"].state_ids
        values = {
            'country_states': country_states,
            'countries': countries,
            }
        signature_id = request.env['sale.customer.esignature'].with_context(active_test=False).search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        if not signature_id:
            signature_id = request.env['sale.customer.esignature'].create({
                'user_id': request.env.user.id,
                'terms_conditions': True,
            })
        values['terms_conditions'] = signature_id.terms_conditions
        values['country'] = signature_id.country_id or pic_partner_id.country_id
        return request.render("equip3_sale_esignature.customer_signature_form_view_second_page", values)

    @http.route(['/customer/signature/3'], type='http', auth="public", website=True)
    def upload_img(self, **post):
        values = {}
        signature_id = request.env['sale.customer.esignature'].with_context(active_test=False).search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        if signature_id and post.get('country_id'):
            signature_id.sudo().write({
                'country_id': int(post.get('country_id')),
            })
        values = {
            'identity_image': signature_id and signature_id.identity_image or False,
        }
        return request.render("equip3_sale_esignature.customer_signature_form_view_third_page", values)

    @http.route(['/customer/signature/4'], type='http', auth="public", website=True)
    def upload_img_selfie(self, **post):
        values = {}
        signature_id = request.env['sale.customer.esignature'].with_context(active_test=False).search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        if signature_id and post:
            identity_image = post.get('identity_image', False)
            if identity_image:
                new_identity_image = identity_image.replace("data:image/png;base64,", "");
                signature_id.sudo().write({
                    'identity_image': new_identity_image,
                })
        values = {
            'selfie_img': signature_id and signature_id.selfie_img or False,
        }
        return request.render("equip3_sale_esignature.customer_signature_form_view_fourth_page", values)

    @http.route(['/register/privy'], type='http', auth='public', website=True, csrf=False)
    def register_privy(self, **post):
        partner = request.env.user.partner_id
        pic_partner_id = partner.child_ids.filtered(lambda r: r.type == 'pic')
        if post:
            partner.sudo().write({'identity_number': post.get('identity_number', False)})
            post.pop('identity_number')
            post['country_id'] = int(post.get('country_id')) if post.get('country_id') else False
            post['state_id'] = int(post.get('state_id')) if post.get('state_id') else False
            if pic_partner_id:
                pic_partner_id.write(post)
            else:
                post['type'] = 'pic'
                partner.sudo().write({
                    'child_ids': [(0, 0, post)]
                })
        return json.dumps({})

    @http.route(['/privy/status'], type='http', auth='public', website=True, csrf=False)
    def privy_status(self, **post):
        signature_id = request.env['sale.customer.esignature'].search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        signature_id.sudo().check_privy_status()
        return json.dumps({})

    @http.route(['/customer/signature/5'], type='http', auth="public", website=True)
    def personal_data(self, **post):
        values = {}
        partner = request.env.user.partner_id
        pic_partner_id = partner.child_ids.filtered(lambda r: r.type == 'pic')
        signature_id = request.env['sale.customer.esignature'].with_context(active_test=False).search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        if signature_id and post:
            selfie_image = post.get('selfie_image', False)
            if selfie_image:
                new_selfie_image = selfie_image.replace("data:image/png;base64,", "");
                signature_id.sudo().write({
                    'selfie_img': new_selfie_image,
                })
        values.update({
            'partner': partner,
            'pic_partner_id': pic_partner_id,
        })
        return request.render("equip3_sale_esignature.customer_signature_form_view_fifth_page", values)

    @http.route(['/customer/signature/6'], type='http', auth="public", website=True)
    def create_data(self, **post):
        values = {}
        signature_id = request.env['sale.customer.esignature'].with_context(active_test=False).search([('user_id', '=', request.env.user.id)], order="id desc", limit=1)
        selfie_image_attachment_id = request.env['ir.attachment'].sudo().search([('res_model', '=', 'sale.customer.esignature'), ('res_field', '=', 'selfie_img'), ('res_id', '=', signature_id.id)], limit=1, order="id desc")
        if selfie_image_attachment_id and not selfie_image_attachment_id.access_token:
            selfie_image_attachment_id.generate_access_token()
        identity_image_attachment_id = request.env['ir.attachment'].sudo().search([('res_model', '=', 'sale.customer.esignature'), ('res_field', '=', 'identity_image'), ('res_id', '=', signature_id.id)], limit=1, order="id desc")
        if identity_image_attachment_id and not identity_image_attachment_id.access_token:
            identity_image_attachment_id.generate_access_token()
        if signature_id and post and not signature_id.active:
            identity_number = post.get('identity_number', False)
            full_name = post.get('full_name', False)
            date_of_birth = post.get('date_of_birth', False)
            phone_no = post.get('phone_no', False)
            email_id = post.get('email_id', False)
            signature_dict = {
                'identity_number': identity_number,
                'full_name': full_name,
                "selfie_img_name": "selfie.png",
                "identity_image_name": "identity.png",
                'date_of_birth': date_of_birth,
                'phone_no': phone_no,
                'email_id': email_id,
                'active': True,
            }
            signature_id.sudo().write(signature_dict)
            signature_id.sudo().send_privy_data()
        values = {
            'sale_esignature_id': signature_id,
            'selfie_attachment_id': selfie_image_attachment_id,
            'identity_attachment_id': identity_image_attachment_id,
        }
        return request.render("equip3_sale_esignature.customer_signature_final_form_view", values)

class CustomerPortal(CustomerPortal):
    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })

        if post and request.httprequest.method == 'POST':
            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in self.MANDATORY_BILLING_FIELDS}
                values.update({key: post[key] for key in self.OPTIONAL_BILLING_FIELDS if key in post})
                for field in set(['country_id', 'state_id']) & set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except:
                        values[field] = False
                values.update({'zip': values.pop('zipcode', '')})
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])

        values.update({
            'partner': partner,
            'pic_partner': partner.child_ids.filtered(lambda r: r.type == 'pic'),
            'countries': countries,
            'states': states,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'redirect': redirect,
            'page_name': 'my_details',
        })
        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    def details_form_validate(self, data):
        error = dict()
        error_message = []

        # Validation
        for field_name in self.MANDATORY_BILLING_FIELDS:
            if not data.get(field_name):
                error[field_name] = 'missing'

        # email validation
        if data.get('email') and not tools.single_email_re.match(data.get('email')):
            error["email"] = 'error'
            error_message.append(_('Invalid Email! Please enter a valid email address.'))

        # vat validation
        partner = request.env.user.partner_id
        if data.get("vat") and partner and partner.vat != data.get("vat"):
            if partner.can_edit_vat():
                if hasattr(partner, "check_vat"):
                    if data.get("country_id"):
                        data["vat"] = request.env["res.partner"].fix_eu_vat_number(int(data.get("country_id")), data.get("vat"))
                    partner_dummy = partner.new({
                        'vat': data['vat'],
                        'country_id': (int(data['country_id'])
                                       if data.get('country_id') else False),
                    })
                    try:
                        partner_dummy.check_vat("tyu")
                    except ValidationError:
                        error["vat"] = 'error'
            else:
                error_message.append(_('Changing VAT number is not allowed once document(s) have been issued for your account. Please contact us directly for this operation.'))

        # error message for empty required fields
        if [err for err in error.values() if err == 'missing']:
            error_message.append(_('Some required fields are empty.'))
        
        # unknown = [k for k in data if k not in self.MANDATORY_BILLING_FIELDS + self.OPTIONAL_BILLING_FIELDS]
        # if unknown:
        #     error['common'] = 'Unknown field'
        #     error_message.append("Unknown field '%s'" % ','.join(unknown))
        

        partner = request.env['res.users'].browse(request.uid).partner_id
        if not partner.can_edit_vat():
            if 'vat' in data and (data['vat'] or False) != (partner.vat or False):
                error['vat'] = 'error'
                error_message.append(_('Changing VAT number is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
            if 'name' in data and (data['name'] or False) != (partner.name or False):
                error['name'] = 'error'
                error_message.append(_('Changing your name is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
            if 'company_name' in data and (data['company_name'] or False) != (partner.company_name or False):
                error['company_name'] = 'error'
                error_message.append(_('Changing your company name is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))

        return error, error_message    
