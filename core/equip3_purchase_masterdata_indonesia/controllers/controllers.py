# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import http,fields
from odoo.http import request
import json
import base64

from odoo import fields, api, SUPERUSER_ID
from odoo.addons.sh_vendor_signup.controllers.main import CreateVendor

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.equip3_purchase_vendor_portal.controllers.controllers import CustomerPortal

class CustomeCreateVendor(CreateVendor):
    @http.route(['/vendor/gender_infos'], auth='public', type='http',  methods=['GET'], csrf=True)
    def gender_infos(self, **kw):
        return json.dumps({
            'data': [{'id':'male', 'name': 'Male'}, {'id':'female', 'name':'Female'}],
        })

    @http.route(['/vendor/civil_infos'], auth='public', type='http',  methods=['GET'], csrf=True)
    def civil_infos(self, **kw):
        return json.dumps({
            'data': [{'id':'pns', 'name':'PNS'},
                     {'id':'non_pns', 'name':'Non PNS'},
                     {'id':'tni', 'name':'TNI'},
                     {'id':'polri', 'name':'POLRI'},
                     {'id':'bumn', 'name':'BUMN'},
                     {'id':'bumd', 'name':'BUMD'},
                     {'id':'lainnya', 'name':'Lainnya'}],
        })

    @http.route(['/vendor/title_infos'], auth='public', type='http', methods=['GET'], csrf=True)
    def title_infos(self, **kw):
        titles = request.env['res.partner.title'].sudo().search([])
        return json.dumps({
            'data': [{'id': title.id, 'name': title.name} for title in titles],
        })
    @http.route(['/vendor/res_bank_infos'], auth='public', type='http', methods=['GET'], csrf=True)
    def res_bank_infos(self, **kw):
        titles = request.env['res.bank'].sudo().search([])
        return json.dumps({
            'data': [{'id': title.id, 'name': title.name} for title in titles],
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

        def replacer(s, newstring, index, nofail=False):
            # raise an error if index is outside of the string
            if not nofail and index not in range(len(s)):
                raise ValueError("index outside given string")

            # if not erroring, but the index is still not in the correct range..
            if index < 0:  # add it to the beginning
                return newstring + s
            if index > len(s):  # add it to the end
                return s + newstring

            # insert the new string between "slices" of the original
            return s[:index] + newstring + s[index + 1:]

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
            vendor_siup = post.get('file_siup', False)
            vendor_npwp = post.get('vendor_vat', False)
            vendor_pkp = post.get('l10n_id_pkp', False)
            faktur_pajak_gabungan = post.get('faktur_pajak_gabungan', False)
            company_size = post.get('company_size', False)
            company_size2 = post.get('company_size2', False)
            capital_revenue = post.get('capital_revenue', False)
            vendor_salinan_anggaran_dasar = post.get('salinan_anggaran_dasar', False)
            vendor_surat_persetujuan_dirjen_ahu = post.get('surat_persetujuan_dirjen_ahu', False)
            vendor_akta_perubahan_pengurus_terakhir = post.get('akta_perubahan_pengurus_terakhir', False)
            vendor_sppkp = post.get('sppkp', False)
            vendor_surat_keterangan_tidak_kena_pajak = post.get('surat_keterangan_tidak_kena_pajak', False)
            vendor_surat_pernyataan_dan_kuasa = post.get('surat_pernyataan_dan_kuasa', False)
            if vendor_siup:
                siup = base64.b64encode(vendor_siup.read())
            else:
                siup = False
            if vendor_salinan_anggaran_dasar:
                salinan_anggaran_dasar = base64.b64encode(vendor_salinan_anggaran_dasar.read())
            else:
                salinan_anggaran_dasar = False
            if vendor_surat_persetujuan_dirjen_ahu:
                surat_persetujuan_dirjen_ahu = base64.b64encode(vendor_surat_persetujuan_dirjen_ahu.read())
            else:
                surat_persetujuan_dirjen_ahu = False
            if vendor_akta_perubahan_pengurus_terakhir:
                akta_perubahan_pengurus_terakhir = base64.b64encode(vendor_akta_perubahan_pengurus_terakhir.read())
            else:
                akta_perubahan_pengurus_terakhir = False
            if vendor_sppkp:
                sppkp = base64.b64encode(vendor_sppkp.read())
            else:
                sppkp = False
            if vendor_surat_keterangan_tidak_kena_pajak:
                surat_keterangan_tidak_kena_pajak = base64.b64encode(vendor_surat_keterangan_tidak_kena_pajak.read())
            else:
                surat_keterangan_tidak_kena_pajak = False
            if vendor_surat_pernyataan_dan_kuasa:
                surat_pernyataan_dan_kuasa = base64.b64encode(vendor_surat_pernyataan_dan_kuasa.read())
            else:
                surat_pernyataan_dan_kuasa = False
            if post.get('vendor_image', False):
                img = post.get('vendor_image')
                image = base64.b64encode(img.read())
            multi_users_value = request.httprequest.form.getlist('category_section')
            for l in range(0, len(multi_users_value)):
                multi_users_value[l] = int(multi_users_value[l])
            country = 'country_id' in post and post['country_id'] != '' and request.env['res.country'].browse(
                int(post['country_id']))
            country = country and country.exists()
            vendor_country_id = request.env['res.country'].browse(int(vendor_country))
            if vendor_country_id and vendor_country_id.code == 'ID':
                if vendor_mobile and vendor_mobile[0] == "0":
                    vendor_mobile = replacer(vendor_mobile,"+62",0)
                if vendor_phone and vendor_phone[0] == "0":
                    vendor_phone = replacer(vendor_phone,"+62",0)
            if company_size:
                company_size = company_size.replace(",", "")
            if company_size2:
                company_size2 = company_size2.replace(",", "")
            if capital_revenue:
                capital_revenue = capital_revenue.replace(",", "")

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
                'file_siup': siup,
                'vat': vendor_npwp,
                'l10n_id_pkp': vendor_pkp,
                'faktur_pajak_gabungan': faktur_pajak_gabungan,
                'customer_rank': 0,
                'supplier_rank': 1,
                'company_size': company_size,
                'company_size2': company_size2,
                'capital_revenue': capital_revenue,
                'salinan_anggaran_dasar': salinan_anggaran_dasar,
                'surat_persetujuan_dirjen_ahu': surat_persetujuan_dirjen_ahu,
                'akta_perubahan_pengurus_terakhir': akta_perubahan_pengurus_terakhir,
                'sppkp': sppkp,
                'surat_keterangan_tidak_kena_pajak': surat_keterangan_tidak_kena_pajak,
                'surat_pernyataan_dan_kuasa': surat_pernyataan_dan_kuasa,
            }
            vendor_id = request.env['res.partner'].sudo().create(vendor_dic)

            if vendor_id:
                vendor_id.is_vendor = True
                quote_msg = {
                    'success': 'Vendor ' + vendor_name + ' created successfully.'
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
                        number_key = 'vendor_c_id_' + numbered_key
                        gender_key = 'vendor_c_gender_' + numbered_key
                        place_key = 'vendor_c_place_' + numbered_key
                        birthdate_key = 'vendor_c_birth_' + numbered_key
                        civil_key = 'vendor_c_civil_' + numbered_key
                        employee_key = 'vendor_c_employee_' + numbered_key
                        type_contact_key = 'vendor_c_type_contact_' + numbered_key

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
                        if post.get(number_key, False):
                            vendor_dic["id_number"] = post.get(number_key)
                        if post.get(gender_key, False):
                            vendor_dic["gender"] = post.get(gender_key)
                        if post.get(place_key, False):
                            vendor_dic["place"] = post.get(place_key)
                        if post.get(birthdate_key, False):
                            vendor_dic["birthdate"] = post.get(birthdate_key)
                        if post.get(civil_key, False):
                            vendor_dic["civil"] = post.get(civil_key)
                        if post.get(employee_key, False):
                            vendor_dic["employee_number"] = post.get(employee_key)
                        if post.get(type_contact_key, False):
                            vendor_dic["type"] = post.get(type_contact_key)
                        else:
                            vendor_dic["type"] = 'contact'

                        vendor_dic["is_vendor"] = True
                        vendor_dic["parent_id"] = vendor_id.id

                        # fill list:
                        contact_id = request.env["res.partner"].sudo().create(vendor_dic)
                        if contact_id:
                            contacts.append(contact_id.id)
            bank_dic = {k: v for k, v in post.items() if k.startswith('vendor_bank_bank_')}
            if vendor_id and bank_dic:
                for key, value in bank_dic.items():
                    vendor_bank_dic = {}
                    if "vendor_bank_bank_" in key:
                        numbered_key = key.replace("vendor_bank_bank_", "") or ''
                        bank_key = 'vendor_bank_bank_' + numbered_key
                        account_number_key = 'vendor_bank_account_number_' + numbered_key

                        if post.get(bank_key, False):
                            vendor_bank_dic["bank_id"] = post.get(bank_key)
                        if post.get(account_number_key, False):
                            vendor_bank_dic["acc_number"] = post.get(account_number_key)

                        vendor_bank_dic["partner_id"] = vendor_id.id

                        # fill list:
                        res_partner_bank_id = request.env["res.partner.bank"].sudo().create(vendor_bank_dic)

            try:
                if request.website.is_enable_auto_portal_user:
                    if request.website.is_enable_company_portal_user:
                        user_id = request.env['res.users'].sudo().search([('partner_id', '=', vendor_id.id)], limit=1)
                        if not user_id and vendor_id:
                            portal_wizard_obj = request.env['portal.wizard']
                            created_portal_wizard = portal_wizard_obj.sudo().with_context(bypass_constrains=True).create({})
                            if created_portal_wizard and vendor_id.email and request.env.user:
                                portal_wizard_user_obj = request.env['portal.wizard.user']
                                wiz_user_vals = {
                                    'wizard_id': created_portal_wizard.id,
                                    'partner_id': vendor_id.id,
                                    'email': vendor_id.email,
                                    'in_portal': True,
                                }
                                created_portal_wizard_user = portal_wizard_user_obj.sudo().with_context(bypass_constrains=True).create(wiz_user_vals)
                                if created_portal_wizard_user:
                                    created_portal_wizard.sudo().with_user(SUPERUSER_ID).with_context(bypass_constrains=True).action_apply()
                    if request.website.is_enable_company_contact_portal_user:
                        if len(contacts) > 0:
                            for contact in contacts:
                                user_id = request.env['res.users'].sudo().search([('partner_id', '=', contact)],
                                                                                 limit=1)
                                partner = request.env['res.partner'].sudo().browse(contact)
                                if not user_id and partner:
                                    portal_wizard_obj = request.env['portal.wizard']
                                    created_portal_wizard = portal_wizard_obj.sudo().with_context(bypass_constrains=True).create({})
                                    if created_portal_wizard and vendor_id.email and request.env.user:
                                        portal_wizard_user_obj = request.env['portal.wizard.user']
                                        wiz_user_vals = {
                                            'wizard_id': created_portal_wizard.id,
                                            'partner_id': partner.id,
                                            'email': partner.email,
                                            'in_portal': True,
                                        }
                                        created_portal_wizard_user = portal_wizard_user_obj.sudo().with_context(bypass_constrains=True).create(wiz_user_vals)
                                        if created_portal_wizard_user:
                                            created_portal_wizard.sudo().with_user(SUPERUSER_ID).with_context(bypass_constrains=True).action_apply()
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

class OpenTenderPortal(CustomerPortal):
    def _prepare_portal_layout_values(self):

        values = super(OpenTenderPortal, self)._prepare_portal_layout_values()
        tender_obj = request.env['purchase.agreement']
        domain = [
            ('tender_scope', '=', 'open_tender'),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        tenders = tender_obj.sudo().search(domain)
        tender_count = tender_obj.sudo().search_count(domain)
        values['tender_count'] = tender_count
        values['tenders'] = tenders
        return values

    def _prepare_open_tender_public_values(self):
        values = {}
        tender_obj = request.env['purchase.agreement']
        domain = [
            ('tender_scope', '=', 'open_tender'),
            ('state', 'not in', ['draft', 'cancel'])
        ]
        tenders = tender_obj.sudo().search(domain)
        tender_count = tender_obj.sudo().search_count(domain)
        values['tender_count'] = tender_count
        values['tenders'] = tenders
        return values

    # @http.route(['/open_tender', '/open_tender/page/<int:page>'], type='http', auth="public", website=True)
    # def portal_home_open_tender(self, page=1):
    #     values = self._prepare_open_tender_public_values()
    #     tender_obj = request.env['purchase.agreement']
    #     domain = [
    #         ('tender_scope', '=', 'open_tender'),
    #         ('state', 'not in', ['draft', 'cancel']),
    #         ('state2', 'not in', ['pending', 'cancel'])
    #     ]

    #     tender_count = tender_obj.sudo().search_count(domain)

    #     pager = portal_pager(
    #         url="/open_tender",
    #         total=tender_count,
    #         page=page,
    #     )

    #     tenders = tender_obj.sudo().search(
    #         domain, limit=self._items_per_page, offset=pager['offset'])

    #     values.update({
    #         'open_tenders': tenders,
    #         'page_name': 'open_tender',
    #         'pager': pager,
    #         'default_url': '/open_tender',
    #         'tender_count': tender_count,
    #     })
    #     return request.render("equip3_purchase_vendor_portal.portal_open_tenders", values)

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

        # Start ---------------------------------------------
        # Set vendor for Legal documents and comparison
        vendor = request.env.user.partner_id
        purchase_tender.partner_ids = [(4, vendor.id)]
        request.env['purchase.agreement.legal.document'].create({
            'legal_document_id': purchase_tender.id,
            'partner_id': vendor.id,
            'nomor_induk_berusaha': vendor.file_siup,
            'salinan_anggaran_dasar': vendor.salinan_anggaran_dasar,
            'surat_persetujuan_dirjen_ahu': vendor.surat_persetujuan_dirjen_ahu,
            'akta_perubahan_pengurus_terakhir': vendor.akta_perubahan_pengurus_terakhir,
            'surat_keterangan_tidak_kena_pajak': vendor.surat_keterangan_tidak_kena_pajak,
            'surat_pernyataan_dan_kuasa': vendor.surat_pernyataan_dan_kuasa
        })
        request.env['purchase.agreement.comparison'].create({
            'partner_id': vendor.id,
            'agreement_id': purchase_tender.id
        })
        # End ---------------------------------------------

        message = "Quotation Created"
        return request.redirect('/open_tender/'+str(purchase_tender.id)+"?message="+message)