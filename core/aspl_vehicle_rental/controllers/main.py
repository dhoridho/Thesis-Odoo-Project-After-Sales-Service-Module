# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

from odoo import http
from odoo.http import request
from datetime import datetime
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.osv import expression
import json


class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        rental_order_detail = request.env['fleet.vehicle.order'].sudo()
        rental_order_count = rental_order_detail.search_count([
            ('customer_name', '=', request.env.user.partner_id.id)
        ])
        values.update({
            'rental_order_count': rental_order_count,
        })
        return values

    @http.route('/order', type='http', auth='public', website=True)
    def order(self, page=1, date_begin=None, date_end=None, sortby=None):
        values = self._prepare_portal_layout_values()
        order_id = request.env['fleet.vehicle.order'].sudo().search(
            [('customer_name', '=', request.env.user.partner_id.id)])
        searchbar_sortings = {
            'date': {'label': ('Start Date'), 'order': 'from_date desc'},
            'date1': {'label': ('End Date'), 'order': 'to_date desc'},
            'stage': {'label': ('Stage'), 'order': 'state'},
        }
        # default sortby order
        if not sortby:
            sortby = 'date'
        searchbar_sortings[sortby]['order']
        values.update({'order_id': order_id,
                       'page_name': 'rental_order',
                       'searchbar_sortings': searchbar_sortings,
                       'sortby': sortby,})
        return request.render("aspl_vehicle_rental.rental_order", values)


class VehicleSearch(http.Controller):

    @http.route('/search-vehicle', type='http', auth='public', website=True)
    def search_vehicle(self, **post):
        return request.render("aspl_vehicle_rental.vehicle_search", {})

    @http.route('/booking_form', type='http', auth='public', website=True)
    def booking_form(self, **post):
        vehicle_list = []
        date_from = datetime.strptime(post['date_from'], '%d-%m-%Y').date()
        date_to = datetime.strptime(post['date_to'], '%d-%m-%Y').date()
        request.session['date_from'] = date_from
        request.session['date_to'] = date_to
        if post:
            vehicle_type_ids = request.env['fleet.vehicle.type'].search([('name', '=', post['vehicle_type'])])
            request.env.cr.execute("""select id from fleet_vehicle where vehicle_type=%s AND fuel_type=%s AND id NOT IN
                                        (select vl.vehicle_id  from fleet_vehicle_order vo,vehicle_order_line vl,fleet_vehicle fv
                                        Where vo.state NOT IN('cancel','close') AND vo.id=vl.vehicle_order_id AND (((vo.from_date BETWEEN %s AND %s) OR (vo.to_date BETWEEN %s AND %s))
                                        OR  ((%s BETWEEN vo.from_date AND vo.to_date) OR(%s BETWEEN vo.from_date AND vo.to_date)))) """,
                                   (vehicle_type_ids.id, post['fuel_type'],
                                    date_from, date_to, date_from, date_to,
                                    date_from, date_to,))

        vehicle_data = request.env.cr.fetchall()
        if vehicle_data:
            for vehicles in vehicle_data:
                vehicle_list.append(request.env['fleet.vehicle'].sudo().search([('id', '=', vehicles)]))
            return request.render("aspl_vehicle_rental.vehicle_search",
                                  {'vehicle_id': vehicle_list, 'post_data': post})
        else:
            return request.render("aspl_vehicle_rental.vehicle_search", {"error": True})

    @http.route('/booking_form/create_quotation/<model("fleet.vehicle"):vehicle_id>', type='http', auth='public', website=True)
    def create_qutation(self, vehicle_id, **post):
        vehicle_order = {'vehicle_id': vehicle_id}
        return request.render("aspl_vehicle_rental.vehicle", vehicle_order)

    @http.route('/vehicle_cart_update', type='http', auth='public', website=True)
    def vehicle_cart_update(self, **post):
        vehicle_order_list = []
        total_day = (request.session.get('date_to') - request.session.get('date_from')).days
        fleet_order_id = request.env['fleet.vehicle.order'].sudo().search(
            [('customer_name', '=', request.env.user.partner_id.id),
             ('from_date', '=', request.session.get('date_from')), ('to_date', '=', request.session.get('date_to')), ('state', '=', 'draft')])
        if post and post['vehicle_id_cart']:
            vehicle_id = request.env['fleet.vehicle'].sudo().search([('id', '=', post['vehicle_id_cart'])])
            if not post['enter_km']:
                vehicle_order_list.append((0, 0, {'vehicle_id': vehicle_id.id,
                                                  'price_based': 'per_day',
                                                  'enter_days': total_day,
                                                  'price': vehicle_id.rate_as_per_day,
                                                  }))
            else:
                vehicle_order_list.append((0, 0, {'vehicle_id': vehicle_id.id,
                                                  'price_based': 'per_km',
                                                  'enter_days': total_day,
                                                  'enter_kms': post['enter_km'],
                                                  'price': vehicle_id.rate_as_per_km,
                                                  }))
            if fleet_order_id:
                fleet_order_id.write(({'vehicle_order_lines_ids': vehicle_order_list}))
                return request.render("aspl_vehicle_rental.vehicle_cart_update", {'vehicle_order_id': fleet_order_id})
            else:
                order_id = request.env['fleet.vehicle.order'].sudo().create(
                    {'customer_name': request.env.user.partner_id.id,
                     'from_date': request.session.get('date_from'),
                     'to_date': request.session.get('date_to'),
                     'state': 'draft',
                     'station_id': vehicle_id.auto_station_id.id,
                     'vehicle_type_id': vehicle_id.vehicle_type.id,
                     'vehicle_order_lines_ids': vehicle_order_list,
                     })
                order_id.vehicle_order_lines_ids._get_subtotal()
                request.session['order_id'] = order_id.id
                return request.render("aspl_vehicle_rental.vehicle_cart_update", {'vehicle_order_id': order_id})

    @http.route('/view_cart', type='http', auth='public', website=True)
    def view_cart(self, **post):
        if post:
            order_id = request.env['fleet.vehicle.order'].sudo().search([('id', '=', post['rental_order'])])
        else:
            order_id = request.env['fleet.vehicle.order'].sudo().search([('id', '=', request.session.get('order_id'))])
        request.session['order_id'] = order_id.id
        return request.render("aspl_vehicle_rental.vehicle_cart_update", {'vehicle_order_id': order_id})

    def _get_rental_payment_values(self, order, **kwargs):
        values = dict(
            website_rental_order=order,
            errors=[],
            partner=order.customer_name.id,
            order=order,
            payment_action_id=request.env.ref('payment.action_payment_acquirer').id,
            return_url= '/rental/payment/validate',
            bootstrap_formatting= True
        )

        domain = expression.AND([
            ['&', ('state', 'in', ['enabled', 'test']), ('company_id', '=', order.company_id.id)],
            ['|', ('website_id', '=', False), ('website_id', '=', request.website.id)],
            ['|', ('country_ids', '=', False), ('country_ids', 'in', [order.customer_name.country_id.id])]
        ])
        acquirers = request.env['payment.acquirer'].search(domain)
        values['acquirers'] = [acq for acq in acquirers if (acq.payment_flow == 'form' and acq.view_template_id) or
                                    (acq.payment_flow == 's2s' and acq.registration_view_template_id)]
        values['tokens'] = request.env['payment.token'].search(
            [('partner_id', '=', order.customer_name.id),
            ('acquirer_id', 'in', acquirers.ids)])

        return values

    @http.route('/rental/payment/validate', type='http', auth="public", website=True, csrf=False)
    def payment_validate(self, transaction_id=None, rental_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :
         - UDPATE ME
        """
        outstanding_info = False
        order = request.env['fleet.vehicle.order'].sudo().browse(request.session.get('order_id'))
        if order:
            if not order.invoice_ids:
                order.confirm()
            invoice_id = order.contract_ids[0].create_invoice()
            invoices = order.mapped('invoice_ids').filtered(lambda inv: inv.state == 'posted')
            for inv in invoices:
                if inv.invoice_has_outstanding:
                    outstanding_info = json.loads(inv.invoice_outstanding_credits_debits_widget)
            transaction_id = request.env['payment.transaction'].browse(request.session.get('__website_sale_last_tx_id'))
            if outstanding_info:
                if 'content' in outstanding_info:
                    for item in outstanding_info['content']:
                        credit_aml_id = outstanding_info['content'][0]['id'] or False
                        # credit_aml_id = item.get('id', False)
                if credit_aml_id and inv.state == 'posted':
                    inv.js_assign_outstanding_line(credit_aml_id)
                assert order.id == request.session.get('order_id')
            vals = {'payment_token_id': post.get('pm_id'), 'return_url': post.get('return_url')}

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        return request.render('aspl_vehicle_rental.rental_order_comfirmation')

    @http.route(['/rental/payment/transaction/',
                 '/rental/payment/transaction/<int:so_id>',
                 '/rental/payment/transaction/<int:so_id>/<string:access_token>'], type='json', auth="public",
                website=True)
    def payment_transaction(self, acquirer_id, save_token=False, so_id=None, access_token=None, token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False
        try:
            acquirer_id = int(acquirer_id)
        except:
            return False
        # Retrieve the sale order
        if so_id:
            env = request.env['fleet.vehicle.order']
            domain = [('id', '=', so_id)]
            if access_token:
                env = env.sudo()
                domain.append(('access_token', '=', access_token))
            order = env.search(domain, limit=1)
        else:
            order = request.env['fleet.vehicle.order'].sudo().browse(request.session.get('order_id'))
        # Ensure there is something to proceed
        assert order.customer_name.id != request.website.partner_id.id
        # Create transaction
        vals = {'acquirer_id': acquirer_id,
                'return_url': '/rental/payment/validate',
                'currency_id': request.env.user.company_id.currency_id.id,
                'amount': order.total_amount,
                'partner_id': order.customer_name.id,
                }
        if save_token:
            vals['type'] = 'form_save'
        if token:
            vals['payment_token_id'] = int(token)
        transaction = order._create_payment_transaction(vals)
        # store the new transaction into the transaction list and if there's an old one, we remove it
        # until the day the ecommerce supports multiple orders at the same time
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()

        PaymentProcessing.add_payment_transaction(transaction)
        request.session['__website_sale_last_tx_id'] = transaction.id
        return transaction.render_rental_button(order)

    @http.route('/checkout', type='http', auth='public', website=True, csrf=False)
    def checkout(self, **post):
        rental_order_id = request.env['fleet.vehicle.order'].sudo().search([('id', '=', request.session.get('order_id'))])
        render_values = self._get_rental_payment_values(rental_order_id, **post)
        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')
        return request.render("aspl_vehicle_rental.checkout_process", render_values)

    @http.route('/get_vehicle_type', type='json', auth='public', website=True)
    def get_vehicle_type(self, type_id):
        types = False
        if type_id:
            type_ids = request.env['fleet.vehicle.type'].sudo().search([('type_id', '=', int(type_id))])
            types = [types.name for types in type_ids]
        return types

    @http.route('/get_rate_details', type='json', auth='public', website=True)
    def get_rate_details(self, units, vehicle_id):
        total_day = (request.session.get('date_to') - request.session.get('date_from')).days
        vehicle_id = request.env['fleet.vehicle'].sudo().search([('id', '=', vehicle_id)])

        if units == 'per_day':
            vehicle_details = {'rate': vehicle_id.rate_as_per_day, 'total_days': total_day,
                               'from_date': request.session.get('date_from'), 'to_date': request.session.get('date_to')}
            return vehicle_details
        else:
            vehicle_details = {'rate': vehicle_id.rate_as_per_km, 'from_date': request.session.get('date_from'), 'to_date': request.session.get('date_to')}
            return vehicle_details

    @http.route('/vehical_ordel_line/remove', type='json', auth="user")
    def remove_line(self, id, **kwrgs):
        line_id = request.env['vehicle.order.line'].browse(int(id))
        line_id.unlink()
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
