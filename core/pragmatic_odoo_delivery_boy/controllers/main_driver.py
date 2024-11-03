# -*- coding: utf-8 -*-
import requests

from odoo import models, api, _, SUPERUSER_ID
from odoo import http, tools
from odoo.addons.web.controllers.main import Home
# from odoo.addons.portal.controllers.web import Home

from odoo.http import request
from odoo.exceptions import ValidationError
from requests import request as req
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException
import urllib
import json
import logging
from datetime import datetime, timedelta
import pytz
from odoo.addons.pragmatic_delivery_control_app.controllers.main import WebsiteCustomer

_logger = logging.getLogger(__name__)
OPG = 5  # Order Per Pagess


class WebsiteCustomerDriver(http.Controller):

    @http.route('/assign-driver', type='http', auth='public', website=True, csrf=False)
    def assign_driver(self, **post):
        driver_list = []
        sale_order = http.request.env['sale.order'].sudo().browse(int(post.get('order_id')))
        all_pickings_obj = request.env['picking.order']
        if sale_order.picking_ids:
            for picking in sale_order.picking_ids:
                picking.write(
                    {'owner_id': int(post.get('driver_id'))})
                driver_list.append('Assigned to driver')
                picking.action_done()
                sale_order.write({'driver_id': int(post.get('driver_id')), 'delivery_state': 'assigned'})
                picking_id = all_pickings_obj.search([('sale_order', '=', sale_order.id)])
                if not picking_id:
                    all_pickings_id = all_pickings_obj.sudo().create({'state': 'assigned',
                                                                      'sale_order': int(post.get('order_id')),
                                                                      'delivery_boy': int(post.get('driver_id')),
                                                                      'picking': post.get('warehouse_id'),
                                                                      'assigned_date': datetime.now(),
                                                                      })
                else:
                    picking_id.write({
                        'delivery_boy': int(post.get('driver_id')),
                        'assigned_date': datetime.now(),
                        'state': 'assigned',
                    })
        else:
            driver_list.append("Picking not available")
        return json.dumps(driver_list)

    @http.route('/page/create_backorder', type='http', auth='public', website=True, csrf=False)
    def create_backorder(self, **post):
        picking_order_number = post.get('picking_order_number')

        picking_order = request.env['picking.order'].sudo().search([('id', '=', picking_order_number)])
        picking_order.back_order_boolean = True
        old_picking = picking_order.picking # source
        old_picking_id = picking_order.picking_id # destination
        move_line = []
        for x in old_picking.move_ids_without_package:
            move_line.append((0,0,{"product_id": x.product_id.id, 
                    "name" : x.product_id.name,
                    "product_uom": x.product_uom.id,
                    "location_id": x.location_id.id,
                    "location_dest_id": old_picking_id.location_dest_id.id,
                    "initial_demand" : x.initial_demand,
                    "product_uom_qty": x.product_uom_qty - x.quantity_done}))
        picking_back_order = request.env['stock.picking'].sudo().create([{'state': 'draft',
                                            'branch_id' : old_picking.location_id.branch_id.id,
                                            'location_id' : old_picking.location_id.id,
                                            'location_dest_id' : old_picking_id.location_dest_id.id,
                                            'picking_type_id' : old_picking.picking_type_id.id,
                                            'backorder_id' : old_picking.id,
                                            'move_ids_without_package' : move_line
                                            }])
        request.env['picking.order'].sudo().create([{'sale_order': picking_order.sale_order.id,
                                                        'picking' : picking_back_order.id,
                                                        'back_order' : old_picking.id
        }])


    @http.route('/page/order-view/<order>', type='http', auth='public', website=True, csrf=False)
    def get_sale_order_details(self, order=None):
        so = http.request.env['sale.order'].sudo()
        sale_order = so.browse([int(str(order))])
        picking_order = http.request.env['sale.order'].sudo().search(['sale_order','=', sale_order.id])
        order_driver_msg = http.request.env['order.driver.message'].sudo().search(
            [('order_id', '=', sale_order.id)])
        stock_pickings = http.request.env['stock.picking'].sudo().search(
            [('sale_id', '=', sale_order.id)])
        api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])
        if len(api_key) == 1:
            maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"
        else:
            maps_url = "//maps.google.com/maps/api/js?key=&amp;libraries=places&amp;language=en-AU"

        return request.render('pragmatic_odoo_delivery_boy.order-view', {'maps_script_url': maps_url, 'order': sale_order,
                                                                            'picking_order' : picking_order,
                                                                            'msg_dict': order_driver_msg,
                                                                            'longitude': sale_order.partner_shipping_id.partner_longitude,
                                                                            'latitude': sale_order.partner_shipping_id.partner_latitude,
                                                                            'driver_longitude': stock_pickings.owner_id.partner_longitude,
                                                                            'driver_latitude': stock_pickings.owner_id.partner_longitude
                                                                            })

    @http.route('/get-driver-location', type='http', auth='public', website=True, csrf=False)
    def get_driver_location(self, **post):
        driver_list = {}
        if post.get('order_number'):
            sale_order_details = http.request.env['sale.order'].sudo().search(
                [('id', '=', int(post.get('order_number')))])
            for item in sale_order_details:
                latitude = item.warehouse_id.partner_id.partner_latitude
                longitude = item.warehouse_id.partner_id.partner_longitude
                driver_list = {
                    'longitude': longitude,
                    'latitude': latitude,
                }
        return json.dumps(driver_list)

    @http.route('/get-issue', type='http', auth='public', website=True, csrf=False)
    def get_issue(self, **post):
        reason = {}
        if post.get('order_id'):
            sale_order = http.request.env['sale.order'].sudo().browse(int(post.get('order_id')))
            if sale_order.picking_ids:
                for pickings in sale_order.picking_ids:
                    if pickings.reason_ids:
                        for picking in sorted(pickings.reason_ids, key=lambda x: x.id, reverse=True)[0]:
                            reason = {
                                'issue': picking.reason_id.name,
                                'longitude': picking.longitude,
                                'latitude': picking.latitude,
                            }
                            reason.update({'shipping_longitude': sale_order.partner_shipping_id.partner_longitude,
                                           'shipping_latitude': sale_order.partner_shipping_id.partner_latitude})
                    if not pickings.reason_ids:
                        reason.update({})
        return json.dumps(reason)

    @http.route('/collect-payment', type='http', auth='public', website=True, csrf=False)
    def collect_payment(self, **post):
        if post.get('order_id'):
            sale_order_brw = http.request.env['sale.order'].sudo().browse(int(post.get('order_id')))
            sale_order_brw.write(
                {'payment_status_with_driver': True})
        return json.dumps({})

    @http.route('/page/get-message-details', type='http', auth='public', website=True, csrf=False)
    def get_sale_order_message_details(self, **post):
        order_id = post.get('order_id')
        sale_order = http.request.env['sale.order'].sudo().browse([int(str(order_id))])
        order_driver_msg_ids = http.request.env[
            'order.driver.message'].sudo().search([('order_id', '=', sale_order.id)])
        message_dict = {}
        message_list = []
        for each_driver_msg_id in order_driver_msg_ids:
            msg_date = http.request.env[
                'website'].get_create_date_timezone(each_driver_msg_id)
            message_dict = ({
                            'message': each_driver_msg_id.message,
                            'partner_id': each_driver_msg_id.partner_id.name,
                            'create_date': msg_date,
                            })
            message_list.append(message_dict)
        return json.dumps(message_list)

    @http.route('/driver/cancel/order', type='http', auth='public', website=True, csrf=False)
    def driver_cancel_sale_order(self, **post):
        order_id = post.get('order_id')
        picking_order = http.request.env['picking.order'].sudo().search([('sale_order', '=', (int(order_id)))])
        picking_order.action_picking_order_canceled()
        order = http.request.env['sale.order'].sudo().browse(int(order_id))
        order.action_cancel()
        _logger.info(
            _("Sale order %s has been cancelled from delivery control panel." % (order.name)))
        return json.dumps({'status': 'true'})

    @http.route('/proceed/checkout', type='http', auth='public', website=True, csrf=False)
    def cancel_sale_order(self, **post):
        order_id = post.get('order_id')
        order = http.request.env['sale.order'].sudo().browse(int(order_id))
        return json.dumps({'status': 'true'})

    @http.route('/delivered/order', type='http', auth='public', website=True, csrf=False)
    def delivered_order_driver(self, **post):
        order_id = post.get('order_id')
        picking_order = http.request.env['picking.order'].sudo().search([('sale_order', '=', (int(order_id)))])
        picking_order.action_picking_order_delivered()
        order = http.request.env['sale.order'].sudo().browse(int(order_id))
        order.action_delivered_sale_order()
        stock_picking = http.request.env['stock.picking'].sudo().search([('sale_id', '=', order.id)])
        for picking in stock_picking.filtered(lambda p:p.state not in ['cancel','done']):
            picking.action_assign()
            for ml in picking.move_ids_without_package:
                ml.quantity_done = ml.reserved_availability
            picking.button_validate()
        # res_validate = stock_picking.button_validate()
        # # stock_picking.action_done()
        # backorder_wizard = http.request.env[res_validate['res_model']].browse(res_validate['res_id'])
        # # backorder_wizard.send_sms()
        # # backorder_wizard.process()
        # if res_validate['res_model'] == 'confirm.stock.sms':
        #     res_validate = backorder_wizard.send_sms()
        # #     backorder_wizard.process()
        # if res_validate.get('res_model') == 'stock.immediate.transfer':
        #     backorder_wizard.process()
        Param = http.request.env['res.config.settings'].sudo().get_values()
        if Param.get('whatsapp_instance_id') and Param.get('whatsapp_token'):
            if order.partner_id.country_id.phone_code and order.partner_id.mobile:
                url = 'https://api.chat-api.com/instance' + Param.get('whatsapp_instance_id') + '/sendMessage?token=' + Param.get('whatsapp_token')
                headers = {
                    "Content-Type": "application/json",
                }
                whatsapp_msg_number = order.partner_id.mobile
                whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(order.partner_id.country_id.phone_code), "")
                msg = "Your order has delivered."
                tmp_dict = {
                    "phone": "+" + str(order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                    "body": msg

                }
                response = requests.post(url, json.dumps(tmp_dict), headers=headers)

                if response.status_code == 201 or response.status_code == 200:
                    _logger.info("\nSend Message successfully")

                    mail_message_obj = http.request.env['mail.message']
                    comment = "fa fa-whatsapp"
                    body_html = tools.append_content_to_html('<div class = "%s"></div>' % tools.ustr(comment), msg)
                    # body_msg = self.convert_to_html(body_html)
                    mail_message_id = mail_message_obj.sudo().create({
                        'res_id': picking_order.id,
                        'model': 'picking.order',
                        'body': body_html,
                    })
        # _logger.info(
        #     _("Sale order %s has been cancelled from delivery control panel." % (order.name)))
        return json.dumps({'state': 'true'})

    @http.route('/page/job/list/driver', type='http', auth='public', website=True)
    def job_list_website(self, page=0, search='', opg=False, domain=None, **kwargs):
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

            picking_orders = request.env['picking.order'].sudo().search(
                [('state', 'in', ['assigned', 'accept']), ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc')

            # sale_orders = picking_orders.mapped('sale_order')
            # orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
            #                                                  order='distance_btn_2_loc asc')
            warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])

            routes = []
            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude, warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])

            if len(api_key) == 1:
                maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"

            for picking in picking_orders:
                if all([picking.sale_order, picking.sale_order.invoice_ids, not picking.invoice]):
                    # picking_order = request.env['picking.order'].search([('sale_order', '=', rec.id)])
                    picking.update({'invoice': picking.sale_order.invoice_ids[0], 'payment': 'paid'})
                    routes.append([picking.sale_order.partner_shipping_id.partner_latitude, picking.sale_order.partner_shipping_id.partner_longitude])

            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            if picking_orders.ids:
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
                    'maps_script_url': maps_url,
                    'picking_ids': picking_orders.ids,
                    'routes': routes,
                    'picking_orders': picking_orders,
                    'delivery_boy': res_partner,
                })

            else:
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
                    'maps_script_url': maps_url,
                    'delivery_boy': res_partner,
                })
            
    def _get_search_picking_domain(self, search):
        domain = []
        if search:
            for srch in search.split(" "):
                domain = [('name', 'ilike', srch)]
        return domain

    @http.route('/page/job/list/driver/paid', type='http', auth='public', website=True)
    def job_list_paid_website(self, page=0, search='', opg=False, domain=None, **kwargs):
        domain = self._get_search_picking_domain(search)
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

            picking_orders = request.env['picking.order'].sudo().search(
                [('state', 'in', ['delivered']), ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc')

            # sale_orders = picking_orders.mapped('sale_order')
            # orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
            #                                                  order='distance_btn_2_loc asc')
            warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])

            routes = []
            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])

            if len(api_key) == 1:
                maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"

            for picking in picking_orders:
                if all([picking.sale_order, picking.sale_order.invoice_ids, not picking.invoice]):
                    # picking_order = request.env['picking.order'].search([('sale_order', '=', rec.id)])
                    picking.update({'invoice': picking.sale_order.invoice_ids[0], 'payment': 'paid'})
                    routes.append([picking.sale_order.partner_shipping_id.partner_latitude,
                                   picking.sale_order.partner_shipping_id.partner_longitude])

            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            if search:
                picking = request.env['stock.picking'].sudo().search(domain)
                sale_order = request.env['sale.order'].sudo().search(domain)
                if picking or sale_order:
                    picking_orders = request.env['picking.order'].sudo().search(['|',
                                                                                 ('picking_id','in',picking.ids),
                                                                                 ('sale_order','in', sale_order.ids)])
                else:
                    picking_orders = request.env['picking.order'].sudo().search(
                            [('state', 'in', ['delivered']), ('delivery_boy', '=', res_partner.id)],
                            order='distance_btn_2_loc asc')
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list_delivered", {
                    'maps_script_url': maps_url,
                    'picking_ids': picking_orders.ids,
                    'routes': routes,
                    'picking_orders': picking_orders,
                    'delivery_boy': res_partner,
                })

            if picking_orders.ids:
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list_delivered", {
                    'maps_script_url': maps_url,
                    'picking_ids': picking_orders.ids,
                    'routes': routes,
                    'picking_orders': picking_orders,
                    'delivery_boy': res_partner,
                })

            else:
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list_delivered", {
                    'maps_script_url': maps_url,
                    'delivery_boy': res_partner,
                })

    @http.route('/page/job/list/driver/reject', type='http', auth='public', website=True)
    def job_list_reject_website(self, page=0, search='', opg=False, domain=None, **kwargs):
        domain = self._get_search_picking_domain(search)
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

            reject_picking_orders = request.env['reject.picking.order'].sudo().search(
                [('driver_id', '=', res_partner.id)],order='id asc')
            
            if reject_picking_orders.ids:
                if search:
                    sale_order = request.env['sale.order'].sudo().search(domain)
                    if sale_order:
                        reject_picking_orders = request.env['picking.order'].sudo().search([('sale_order','in',sale_order.ids)])
                        reject_picking_orders = request.env['reject.picking.order'].sudo().search([('picking_id','in',reject_picking_orders.picking_id.ids)])
                    else:
                        reject_picking_orders = request.env['reject.picking.order'].sudo().search(
                            [('driver_id', '=', res_partner.id)],order='id asc')
                    return request.render("pragmatic_odoo_delivery_boy.manage_reject_job_list", {
                        'picking_ids': reject_picking_orders.ids,
                        'picking_orders': reject_picking_orders,
                        'delivery_boy': res_partner,
                    })

                else:
                    return request.render("pragmatic_odoo_delivery_boy.manage_reject_job_list", {
                        'picking_ids': reject_picking_orders.ids,
                        'picking_orders': reject_picking_orders,
                        'delivery_boy': res_partner,
                    })

            else:
                return request.render("pragmatic_odoo_delivery_boy.manage_reject_job_list", {
                    'picking_orders': reject_picking_orders,
                })
                # return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
                #     'delivery_boy': res_partner,
                # })


    @http.route('/page/job/list/customer', type='http', auth='public', website=True)
    def job_list_website_customer(self, page=0, search='', opg=False, domain=None, **kwargs):
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

            # picking_orders = request.env['picking.order'].sudo().search(
            #     [('partner_id', '=', res_partner.id)],
            #     order='distance_btn_2_loc asc')

            sale_orders = request.env['sale.order'].sudo().search(
                [('partner_id', '=', res_partner.id)],
                order='distance_btn_2_loc asc')
            for sale_order_id in sale_orders:
                if sale_order_id:
                    picking_orders = request.env['picking.order'].sudo().search(
                        [('sale_order', '=', sale_order_id.id)],
                        order='distance_btn_2_loc asc')

                # sale_orders = picking_orders.mapped('sale_order')
                # orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
                #                                                  order='distance_btn_2_loc asc')

                # warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
                # routes = [[warehouse_driver[0].warehouse_id.partner_id.partner_latitude, warehouse_driver[0].warehouse_id.partner_id.partner_longitude]]

                # api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])

                # if len(api_key) == 1:
                #     maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"

                # for rec in orders:
                #     if rec.invoice_ids:
                #         picking_order = request.env['picking.order'].search([('sale_order', '=', rec.id)])
                #         for pic in picking_order:
                #             pic.invoice = rec.invoice_ids[0]
                #             pic.payment = 'paid'
                #     routes.append([rec.partner_shipping_id.partner_latitude, rec.partner_shipping_id.partner_longitude])
                #
                # routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                #                warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

                if picking_orders.ids or sale_orders:
                    return request.render("pragmatic_odoo_delivery_boy.manage_job_list_customer", {
                        # 'maps_script_url': maps_url,
                        'picking_ids': picking_orders.ids,
                        # 'routes': routes,
                        'sale_orders': sale_orders,
                        'delivery_boy': res_partner,
                        'picking_orders': picking_orders,
                    })

            # else:
            return request.render("pragmatic_odoo_delivery_boy.manage_job_list_customer", {
                # 'maps_script_url': maps_url,
                'delivery_boy': res_partner,
            })

    @http.route('/page/job_list/order-view/<order>', type='http', auth='public', website=True, csrf=False)
    def get_sale_order_details1(self, order=None, **kwargs):
        so = http.request.env['sale.order'].sudo()
        sale_order = so.browse([int(str(order))])
        _logger.info(_("In get_sale_order_details sale_order: %s" % (sale_order)))
        order_driver_msg = http.request.env['order.driver.message'].sudo().search(
            [('order_id', '=', sale_order.id)])

        stock_pickings = http.request.env['stock.picking'].sudo().search(
            [('sale_id', '=', sale_order.id),('state', '!=', 'done')])

        picking_order_id = http.request.env['picking.order'].sudo().search([('sale_order', '=', sale_order.id), ('state', '!=', 'delivered')], limit=1)
        _logger.info(_("In get_sale_order_details picking_order_id: %s" % (picking_order_id)))
        # payment_transaction_obj = http.request.env['payment.transaction'].search([('id', 'in', sale_order.transaction_ids.ids)])
        for pick in picking_order_id:
            return request.render('pragmatic_odoo_delivery_boy.order-view-driver',
                                {
                                'order': sale_order,
                                'msg_dict': order_driver_msg,
                                'picking_order_payment_status': pick.payment.capitalize() if pick.payment else '',
                                'longitude': sale_order.partner_shipping_id.partner_longitude,
                                'latitude': sale_order.partner_shipping_id.partner_latitude,
                                'driver_longitude': stock_pickings.owner_id.partner_longitude,
                                'driver_latitude': stock_pickings.owner_id.partner_latitude,
                                'driver_mobile': stock_pickings.owner_id.mobile,
                                'picking_order': pick,
                                'stock_pickings' : stock_pickings
                                })

    @http.route('/page/job_list/order-view-delivered/<order>', type='http', auth='public', website=True, csrf=False)
    def get_sale_order_details_delivered(self, order=None, **kwargs):
        picking_order_id = http.request.env['picking.order'].sudo().search([('id', '=', order)], limit=1)
        _logger.info(_("In get_sale_order_details picking_order_id: %s" % (picking_order_id)))
        sale_order =  http.request.env['sale.order'].sudo().search([('id', '=', picking_order_id.sale_order.id)], limit=1)
        _logger.info(_("In get_sale_order_details sale_order: %s" % (sale_order)))
        order_driver_msg = http.request.env['order.driver.message'].sudo().search(
            [('order_id', '=', sale_order.id)])
        stock_pickings = http.request.env['stock.picking'].sudo().search(
            [('id', '=', picking_order_id.picking_id.id)])

        # payment_transaction_obj = http.request.env['payment.transaction'].search([('id', 'in', sale_order.transaction_ids.ids)])
        for pick in picking_order_id:
            return request.render('pragmatic_odoo_delivery_boy.order_view_driver_delivered',
                                {
                                'order': sale_order,
                                'msg_dict': order_driver_msg,
                                'picking_order_payment_status': pick.payment.capitalize() if pick.payment else '',
                                'longitude': sale_order.partner_shipping_id.partner_longitude,
                                'latitude': sale_order.partner_shipping_id.partner_latitude,
                                'driver_longitude': stock_pickings.owner_id.partner_longitude,
                                'driver_latitude': stock_pickings.owner_id.partner_latitude,
                                'driver_mobile': stock_pickings.owner_id.mobile,
                                'picking_order': pick,
                                'stock_pickings' : stock_pickings
                                })
    


    @http.route('/driver/issue/message', type='http', auth='public', website=True, csrf=False)
    def driver_issue_message(self, **post):
        if post.get('picking_order'):
            picking_order = request.env['picking.order'].search([('id', '=', post.get('picking_order'))])
            message = post.get('driver_message')
            vals = {
                'driver_id': picking_order.delivery_boy.id,
                'picking_id': picking_order.id,
                'assign_date': picking_order.assigned_date,
                'reject_date': datetime.now(),
                'reject_reason': message,
            }
            reject_picking = request.env['reject.picking.order'].sudo().create(vals)
            picking_order.message_post(body="{} - {}".format(message, picking_order.delivery_boy.name),
                                       type='comment')
            picking_order.state='failed_delivery'
            picking_order.delivery_boy = False
            picking_order.sale_order.delivery_state = 'ready'

        return json.dumps({})

    @http.route('/select/payment/status', type='http', auth='public', website=True, csrf=False)
    def customer_payment_status(self, **post):
        order_no = post.get('order_number')
        sale_order = http.request.env['sale.order'].sudo().browse(order_no)
        picking_order_id = http.request.env['picking.order'].sudo().search([('sale_order', '=', sale_order.id)])
        # if post.get('selectedValue') == 'cash_on_delivery':
        #     picking_order_id.write({'payment_status':'Cash On Delivery'})
        # elif post.get('selectedValue') == 'prepaid':
        #     picking_order_id.write({'payment_status': 'Prepaid'})

        if post.get('selectedValue') == 'credit_card':
            picking_order_id.write({'payment_status': 'Credit Card'})
        elif post.get('selectedValue') == 'debit_card':
            picking_order_id.write({'payment_status': 'Debit Card'})
        elif post.get('selectedValue') == 'cash_on_delivery':
            picking_order_id.write({'payment_status': 'Cash On Delivery'})

        return json.dumps({})

    @http.route('/paid/status', type='http', auth='public', website=True, csrf=False)
    def sale_order_paid_status(self, **post):
        _logger.info(_("In paid status post: %s" % (post)))
        if post.get('payment') == 'Paid':
            picking_order_number = post.get('picking_order_number')
            picking_order = http.request.env['picking.order'].sudo().search([('id', '=', picking_order_number)])
            so_obj = picking_order.sale_order
            so_obj.write({'delivery_state': 'paid'})
            picking_order.write({'payment': 'paid','state': 'paid'})
        return json.dumps({})

    @http.route('/order/driver_accept_reject_status_in_picked', type='http', auth='user', website=True, csrf=False)
    def order_accept_reject_status_by_driver_in_picked(self, **post):
        order_no = post.get('order_number')
        sale_order = http.request.env['sale.order'].sudo().search([('name','=',order_no)])
        picking_orders = request.env['picking.order'].sudo().search([('sale_order', '=', sale_order.id)])
        picking_orders = picking_orders.with_user(SUPERUSER_ID)
        timezone = sale_order._context.get('tz')
        create_date = datetime.now(pytz.timezone(timezone)).strftime("%Y-%m-%d %H:%M")
        
        for picking_order in picking_orders:
            if post.get('delivery_order_status') == 'picked':
        #         picking_order.pick_delivery()
        #         picking_order.message_post(body="<ul><li>Delivery Order Picked By {0}</li> <li>State: {2}</li> <li>Create Date: {1}</li></ul>".format(picking_order.delivery_boy.name,create_date,picking_order.sale_order.stage_id.name),type='comment')
                return json.dumps({'status': True})

    # Picking order filter by state (assigned,accept,picked,paid)
    @http.route('/page/job/list/driver', type='http', auth='public', website=True)
    def assiged_driver(self):
        print('\n\n\noooooooookjjjjjjjjjjjj')
        res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
        res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])
        picking_orders = request.env['picking.order'].sudo().search(
            [('state', 'in', ['assigned', 'accept', 'in_progress', 'paid', 'picked']),
             ('delivery_boy', '=', res_partner.id)],
            order='distance_btn_2_loc asc'
        )
        pos_references = picking_orders.filtered(lambda po: po.order_source == 'pos').mapped('name')
        pos_orders = request.env['pos.order'].sudo().search([('state', '=', 'paid'),
                                                             ('pos_reference', 'in', pos_references)])
        warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
        picking_orders_state_assigned = []
        if picking_orders:
            picking_orders_state_assigned = request.env['picking.order'].sudo().search(
                [('state', 'in', ['assigned']),
                 ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc'
            )

        picking_orders_state_accept = []
        if picking_orders:
            picking_orders_state_accept = request.env['picking.order'].sudo().search(
                [('state', 'in', ['accept']),
                 ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc'
            )
        picking_orders_state_picked = []
        if picking_orders:
            picking_orders_state_picked = request.env['picking.order'].sudo().search(
                [('state', 'in', ['picked']),
                 ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc'
            )
        picking_orders_state_paid = []
        if picking_orders:
            picking_orders_state_paid = request.env['picking.order'].sudo().search(
                [('state', 'in', ['paid']),
                 ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc'
            )
        else:
            if picking_orders.state == 'assigned':
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list_new_list", {
                    'delivery_boy': res_partner,
                    'picking_ids': picking_orders.ids,
                    'picking_orders': picking_orders.sudo(),
                    'pos_orders': pos_orders,
                    'pos_ids': pos_orders.ids
                })
        return request.render("pragmatic_odoo_delivery_boy.manage_job_list_new_list", {
            'picking_ids': picking_orders.ids,
            'picking_orders_state_assigned': picking_orders_state_assigned,
            'picking_orders_state_accept': picking_orders_state_accept,
            'picking_orders_state_picked': picking_orders_state_picked,
            'picking_orders_state_paid': picking_orders_state_paid,
            'delivery_boy': res_partner,
            'pos_orders': pos_orders,
            'pos_ids': pos_orders.ids
        })

    @http.route('/order/driver_accept_reject_status', type='http', auth='user', website=True, csrf=False)
    def order_accept_reject_status_by_driver(self, **post):
        order_no = post.get('order_number')
        sale_order = http.request.env['sale.order'].sudo().search([('name','=',order_no)])
        stage = post.get('delivery_order_status')
        picking_orders = request.env['picking.order'].sudo().search([('sale_order', '=', sale_order.id), ('state', '!=', 'delivered')])
        picking_orders = picking_orders.with_user(SUPERUSER_ID)
        timezone = sale_order._context.get('tz')
        create_date = datetime.now(pytz.timezone(timezone)).strftime("%Y-%m-%d %H:%M")
        for picking_order in picking_orders:
            if stage == 'accept':
                order_stage_id = request.env['order.stage'].sudo().search([('action_type', '=', 'assigned')])
                if order_stage_id:
                    sale_order.write({'delivery_state': 'assigned', 'stage_id':order_stage_id.id})
                    picking_order.write({'stage_id':order_stage_id.id, 'state': 'accept'})
                picking_order.message_post(body="<ul><li>Delivery Order Accepted By {0}</li> <li>State: {2}</li> <li>Create Date: {1}</li></ul>".format(picking_order.delivery_boy.name,create_date,picking_order.sale_order.stage_id.name),type='comment')
                return json.dumps({'status': True})
            
            
            elif stage == 'picked':
                qty_done = post.get('qty_done')
                picking_order.pick_delivery(qty_done)
                order_stage_id = request.env['order.stage'].sudo().search([('action_type', '=', 'picked')])
                if order_stage_id:
                    sale_order.write({'stage_id':order_stage_id.id})
                picking_order.message_post(body="<ul><li>Delivery Order Picked By {0}</li> <li>State: {2}</li> <li>Create Date: {1}</li></ul>".format(picking_order.delivery_boy.name,create_date,picking_order.sale_order.stage_id.name),type='comment')
                return json.dumps({'status': True})

            elif stage == 'reject':
                message = "<ul><li>Delivery Order Rejected By {0}</li> <li>State: {2}</li> <li>Create Date: {1}</li></ul>".format(picking_order.delivery_boy.name,create_date,picking_order.sale_order.stage_id.name)
                picking_order.message_post(body=message,type='comment')
                vals = {
                    'driver_id': picking_order.delivery_boy.id,
                    'picking_id': picking_order.id,
                    'assign_date': picking_order.assigned_date,
                    'reject_date': datetime.now(),
                    'reject_reason': post.get('reject_reason'),
                }
                reject_picking = request.env['reject.picking.order'].sudo().create(vals)
                picking_order.write({'state': 'created','delivery_boy': False})
                sale_order.write({'delivery_state':'ready'})
                return json.dumps({'status': False})

    @http.route('/change_delivery_boy_status', type='http', auth='public', website=True, csrf=False)
    def change_delivery_boy_status(self, **post):
        delivery_boy = post.get('delivery_boy') #Res Partner
        delivery_boy_status = post.get('delivery_boy_status')
        picking_orders = request.env['picking.order'].sudo().search([('delivery_boy', '=', int(delivery_boy))])
        if delivery_boy and delivery_boy_status:
            warehouse_driver = request.env['stock.warehouse.driver'].search([('driver_id','=',int(delivery_boy))])
            res_partner = request.env['res.partner'].search([('id','=',int(delivery_boy))])
            if delivery_boy_status.lower() == 'available' and res_partner and warehouse_driver:
                res_partner.write({'status': 'not_available'})
                warehouse_driver.write({'status' : 'not_available'})
                for picking in picking_orders:
                    if picking.state != 'accept':
                        picking.sale_order.write({'delivery_state': 'ready'})
                        picking.write({'state': 'created','delivery_boy': False})
                        picking.message_post(
                            body="Delivery Order Rejected By {}. Delivery Boy not available".format(picking.delivery_boy.name),
                            type='comment')
                return json.dumps({"driver_status" : 'Not Available','status_changed':True})

            elif delivery_boy_status.lower() == 'not available' and res_partner and warehouse_driver:
                res_partner.write({'status': 'available'})
                warehouse_driver.write({'status': 'available'})
                return json.dumps({"driver_status": 'Available','status_changed':True})

            else:
                return json.dumps({'status_changed':False})

    @http.route('/page/driver/settings', type='http', auth='public', website=True)
    def page_driver_settings(self, page=0, search='', opg=False, domain=None, **kwargs):
        # res_partner = request.env['res.partner'].search([('is_driver', '=', True)])
        warehouse_obj = request.env['stock.warehouse.driver'].search([])

        values = {
            'warehouse_obj': warehouse_obj
        }

        return request.render("pragmatic_odoo_delivery_boy.driver_settings", values)

    @http.route('/admin/delivery/routes', type='http', auth='public', website=True)
    def admin_delivery_list_website(self, page=0, search='', opg=False, domain=None, **kwargs):

        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")

        else:
            # res_partner = request.env['res.partner'].sudo().search([])

            picking_orders = request.env['picking.order'].sudo().search([('state', 'in', ['assigned', 'accept']),
                                                                         ('state', '!=', 'delivered'),
                                                                         ('state', '!=', 'canceled')])
            sale_orders = picking_orders.mapped('sale_order')
            orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
                                                             order='distance_btn_2_loc asc')
            warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '!=', False)])

            values = {
            'warehouses': warehouse_driver,
            }
            return request.render("pragmatic_odoo_delivery_boy.manage_admin_list", values)

    @http.route('/admin/delivery/routes/details/<driver_id>', type='http', auth='public', website=True, csrf=False)
    def admin_delivery_routes_details(self, order=None, **kwargs):
        res_partner = request.env['res.partner'].sudo().search([('id', '=', kwargs.get('driver_id'))])
        picking_orders = request.env['picking.order'].sudo().search([('state', 'in', ['assigned', 'accept','paid']),
                                                                     ('delivery_boy', '=', res_partner.id),
                                                                     ])

        sale_orders = picking_orders.mapped('sale_order')
        orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
                                                         order='distance_btn_2_loc asc')

        api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])

        if len(api_key) == 1:
            maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"
            # maps_url = "//maps.googleapis.com/maps/api/js?key=" + api_key.value + "&callback=initMap"

        routes = []
        warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
        routes = [[warehouse_driver[0].warehouse_id.partner_id.partner_latitude, warehouse_driver[0].warehouse_id.partner_id.partner_longitude]]

        for rec in orders:
            routes.append([rec.partner_id.partner_latitude, rec.partner_id.partner_longitude, rec.name, rec.partner_id.zip])
        routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                       warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

        if picking_orders.ids:
            return request.render("pragmatic_delivery_control_app.route-map-view", {
                'maps_script_url': maps_url,
                'picking_ids': picking_orders.ids,
                'routes': json.dumps(routes)
            })

        else:
            return request.render("pragmatic_delivery_control_app.route-map-view", {
                'maps_script_url': maps_url,
            })



    @http.route('/delivery/route/order-view/<order_id>', type='http', auth='public', website=True, csrf=False)
    def customer_delivery_routes(self, order=None, **kwargs):
        orders = request.env['sale.order'].sudo().search([('id', '=', kwargs.get('order_id'))])
        order_line = request.env['sale.order.line'].sudo().search([('order_id', '=', orders.id)])
        picking_orders = request.env['picking.order'].sudo().search([('sale_order', '=', orders.id),('delivery_boy','!=', False),
                                                                     '|', ('active', '=', True), ('active', '=', False),
                                                                     ])
        stock_picking = request.env['stock.picking'].sudo().search([('sale_id', '=', orders.id)])
        api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])
        if len(api_key) == 1:
            maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"
        routes = []

        # if picking_orders:
        #     routes = [[picking_orders.delivery_boy.partner_latitude, picking_orders.delivery_boy.partner_longitude]]
        # routes.append([orders.partner_id.partner_latitude, orders.partner_id.partner_longitude, orders.name, orders.partner_id.zip])
        order_stages = request.env['order.stage'].search([])
        if orders:
            return request.render("pragmatic_odoo_delivery_boy.route-map-customer-view", {
                'maps_script_url': maps_url,
                'orders': orders,
                'stock_picking': stock_picking,
                'picking_orders': picking_orders,
                'order_line':order_line,
                'order_stages': order_stages,
                'routes': json.dumps(routes)
            })

        else:
            return request.render("pragmatic_odoo_delivery_boy.route-map-customer-view", {
                'maps_script_url': maps_url,
            })

    @http.route('/customer/delivery/routes', type='http', auth='public', website=True)
    def customer_delivery_routes_website(self, page=0, search='', opg=False, domain=None, **kwargs):
        _logger.info("In customer delivery routes")
        # if request.env.user._is_public():
        #     return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        # else:
        #     res_users = request.env['res.users'].search([('id', '=', request.env.user.id)])
        #     res_partner = request.env['res.partner'].search([('id', '=', res_users.partner_id.id)])
        #
        #     picking_orders = request.env['picking.order'].search(
        #         [('state', 'in', ['assigned', 'accept']), ('delivery_boy', '=', res_partner.id)],
        #         order='distance_btn_2_loc asc')
        #
        #     sale_orders = picking_orders.mapped('sale_order')
        #     orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
        #                                                      order='distance_btn_2_loc asc')
        #
        #     warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
        #     routes = [[warehouse_driver[0].warehouse_id.partner_id.partner_latitude, warehouse_driver[0].warehouse_id.partner_id.partner_longitude]]
        #
        #     api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])
        #
        #     if len(api_key) == 1:
        #         maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"
        #
        #     for rec in orders:
        #         if rec.invoice_ids:
        #             picking_order = request.env['picking.order'].search([('sale_order', '=', rec.id)])
        #             for pic in picking_order:
        #                 pic.invoice = rec.invoice_ids[0]
        #                 pic.payment = 'paid'
        #         routes.append([rec.partner_shipping_id.partner_latitude, rec.partner_shipping_id.partner_longitude])
        #
        #     routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
        #                    warehouse_driver[0].warehouse_id.partner_id.partner_longitude])
        #
        #     if picking_orders.ids:
        #         return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
        #             'maps_script_url': maps_url,
        #             'picking_ids': picking_orders.ids,
        #             'routes': routes,
        #             'picking_orders': picking_orders,
        #             'delivery_boy': res_partner,
        #         })
        #
        #     else:
        #         return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
        #             'maps_script_url': maps_url,
        #             'delivery_boy': res_partner,
        #         })

    @http.route('/driver/status', type='http', auth='public', website=True, csrf=False)
    def driver_status(self, **post):
        return json.dumps({})

    @http.route('/customer/receipt', type='http', auth='public', website=True, csrf=False)
    def customer_receipt(self, order=None, **kwargs):

        return json.dumps({})

    # @http.route('/delivery/route/order-view/download/invoice/<orders_id>', type='http', auth='public', website=True, csrf=False)
    # def download_image_invoice(self, **post):
    #
    #     orders = request.env['sale.order'].sudo().browse(post.get('orders_id'))
    #     # message = _("<p>Dear %s,<br/>Here is your electronic ticket for the %s. </p>") % (client['name'], name)
    #
    #     filename = 'Order Details.jpg'
    #     receipt = request.env['ir.attachment'].sudo().create({
    #         'name': filename,
    #         'type': 'binary',
    #         # 'datas': ticket,
    #         'res_model': 'sale.order',
    #         'res_id': orders.id,
    #         'store_fname': filename,
    #         'mimetype': 'image/jpeg',
    #     })
    #     # return {
    #     #     'type': 'ir.actions.act_url',
    #     #     'url': '/web/content?model=sale.order&field=datas&id=%s&filename=website_order.xls' % (orders.id),
    #     #     'target': 'self',
    #     # }
    #     return request.render("pragmatic_odoo_delivery_boy.print_customer_receipt", receipt)
    #
    #     # return json.dumps({})


class Website(Home):

    def _login_redirect(self, uid, redirect=None):
        if not redirect and request.params.get('login_success'):
            if request.env['res.users'].browse(uid).has_group('base.group_user'):
                redirect = b'/web?' + request.httprequest.query_string
            elif request.env['res.users'].browse(uid).partner_id.is_driver:
                redirect = '/page/job/list/driver'
            else:
                redirect = '/my'
        return super(Website, self)._login_redirect(uid, redirect=redirect)
