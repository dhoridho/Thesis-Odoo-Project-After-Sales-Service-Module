# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import http,fields
from odoo.http import request
import json
import base64

from odoo import fields, api, SUPERUSER_ID

class CreateVendor(http.Controller):
    
    @http.route(['/vendor_sign_up'], type='http', auth="public", website=True)
    def create_vendor(self, **post):
        quote_msg = {}
        emails = []
        image = 0
        multi_users_value = [0]
        contacts = []
        
        if post:
            vendor_name = post.get('vendor_name',False)
            vendor_email = post.get('vendor_email',False)
            vendor_phone = post.get('vendor_phone',False)
            vendor_mobile = post.get('vendor_mobile',False)
            vendor_street = post.get('vendor_street',False)
            vendor_street2 = post.get('vendor_street2',False)
            vendor_website = post.get('vendor_website',False)
            vendor_zip_code = post.get('vendor_zip_code',False)
            vendor_city = post.get('vendor_city',False)
            vendor_country = post.get('country_id',False)
            vendor_state = post.get('state_id',False)
            vendor_type = post.get('vendor_type',False)
            vendor_comment = post.get('vendor_comment',False)
            vendor_note = post.get('vendor_note',False)
            if post.get('vendor_image',False):
                img = post.get('vendor_image')
                image = base64.b64encode(img.read())
            multi_users_value = request.httprequest.form.getlist('category_section')
            for l in range(0, len(multi_users_value)): 
                multi_users_value[l] = int(multi_users_value[l])
            country = 'country_id' in post and post['country_id'] != '' and request.env['res.country'].browse(int(post['country_id']))
            country = country and country.exists()
            vendor_dic = {
                'name': vendor_name,
                'street':vendor_street,
                'street2':vendor_street2,
                'phone':vendor_phone,
                'mobile':vendor_mobile,
                'email':vendor_email,
                'website':vendor_website,
                'zip':vendor_zip_code,
                'city':vendor_city,
                'country_id':int(vendor_country) if int(vendor_country) else False,
                'state_id':int(vendor_state) if int(vendor_state) else False,
                'company_type':vendor_type,
                'vendor_products':vendor_comment,
                'comment':vendor_note,
                'image_1920':image,
                'vendor_product_categ_ids':[(6,0, multi_users_value)] or [],
                'customer_rank':0,
                'supplier_rank':1,
                }
            vendor_id = request.env['res.partner'].sudo().create(vendor_dic)
            
            
            if vendor_id:
                quote_msg = {
                    'success': 'Vendor ' + vendor_name + ' created successfully.'
                    }
                if request.website.is_enable_vendor_notification and request.website.sudo().user_ids.sudo():
                    for user in request.website.user_ids.sudo():
                        if user.sudo().partner_id.sudo() and user.sudo().partner_id.sudo().email:
                            emails.append(user.sudo().partner_id.sudo().email)
                email_values = {
                    'email_to': ','.join(emails),
                    'email_from':request.website.company_id.sudo().email,
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
                    vendor_id.id, email_values=email_values, notif_layout='mail.mail_notification_light', force_send=True)
            
            contact_dic =  {k: v for k, v in post.items() if  k.startswith('vendor_c_name_')}
            if vendor_id and contact_dic:
                for key, value in contact_dic.items():
                    vendor_dic = {}
                    if "vendor_c_name_" in key:
                        vendor_dic["name"] = value
                        
                        numbered_key = key.replace("vendor_c_name_","") or ''
                        email_key = 'vendor_c_email_' + numbered_key
                        phone_key = 'vendor_c_phone_' + numbered_key
                        
                        if post.get(email_key,False):
                            vendor_dic["email"] = post.get(email_key)
                        if post.get(phone_key,False):
                            vendor_dic["phone"] = post.get(phone_key)
                        
                        vendor_dic["type"] = 'contact'
                        vendor_dic["parent_id"] = vendor_id.id                            
                          
                        # fill list:
                        contact_id = request.env["res.partner"].sudo().create(vendor_dic)
                        if contact_id:
                            contacts.append(contact_id.id)
                        

            try:
                if request.website.is_enable_auto_portal_user:
                    if request.website.is_enable_company_portal_user:
                        user_id = request.env['res.users'].sudo().search([('partner_id','=',vendor_id.id)],limit=1)
                        if not user_id and vendor_id:
                            portal_wizard_obj = request.env['portal.wizard']
                            created_portal_wizard =  portal_wizard_obj.sudo().create({})
                            if created_portal_wizard and vendor_id.email and request.env.user:
                                portal_wizard_user_obj = request.env['portal.wizard.user']
                                wiz_user_vals = {
                                    'wizard_id': created_portal_wizard.id,
                                    'partner_id': vendor_id.id,
                                    'email' : vendor_id.email,
                                    'in_portal' : True,
                                    }
                                created_portal_wizard_user = portal_wizard_user_obj.sudo().create(wiz_user_vals)
                                if created_portal_wizard_user:
                                    created_portal_wizard.sudo().with_user(SUPERUSER_ID).action_apply()
                    if request.website.is_enable_company_contact_portal_user:
                        if len(contacts) > 0:
                            for contact in contacts:
                                user_id = request.env['res.users'].sudo().search([('partner_id','=',contact)],limit=1)
                                partner = request.env['res.partner'].sudo().browse(contact)
                                if not user_id and partner:
                                    portal_wizard_obj = request.env['portal.wizard']
                                    created_portal_wizard =  portal_wizard_obj.sudo().create({})
                                    if created_portal_wizard and vendor_id.email and request.env.user:
                                        portal_wizard_user_obj = request.env['portal.wizard.user']
                                        wiz_user_vals = {
                                            'wizard_id': created_portal_wizard.id,
                                            'partner_id': partner.id,
                                            'email' : partner.email,
                                            'in_portal' : True,
                                            }
                                        created_portal_wizard_user = portal_wizard_user_obj.sudo().create(wiz_user_vals)
                                        if created_portal_wizard_user:
                                            created_portal_wizard.sudo().with_user(SUPERUSER_ID).action_apply()
            except Exception as e:
                quote_msg = {
                    'fail': str(e)
                }
        
        countries = request.env["res.country"].sudo().search([])
        country_states = request.env["res.country"].state_ids
        
        values = {
            'page_name': 'vendor_sign_up_form_page',
            'default_url': '/vendor_sign_up',
            'quote_msg':quote_msg,
            'country_states': country_states,
            'countries': countries,
            }
        return request.render("sh_vendor_signup.vendor_sign_up_form_view",values)
            
    @http.route(['/vendor_sign_up/<model("res.country"):country>'], type='json', auth="public", methods=['POST'], website=True)
    def sh_country_infos(self, country,**kw):
        return dict(
            states=[(st.id, st.name, st.code) for st in country.state_ids],
            phone_code=country.phone_code,
            zip_required=country.zip_required,
            state_required=country.state_required,
        )
            
            
            
            
            