# -*- coding: utf-8 -*-

from odoo import models, api, _
from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

from requests import request as req
from requests.exceptions import ConnectionError, HTTPError, Timeout, RequestException
import urllib
import json
import logging
from datetime import datetime, timedelta
import pytz, ast

_logger = logging.getLogger(__name__)

OPG = 5  # Order Per Page


class Website(models.Model):
    _inherit = 'website'

    def is_delivery_control_access(self, user_id):
        usr = self.env['res.users'].sudo().browse(user_id)
        res = usr.has_group('pragmatic_delivery_control_app.group_delivery_control_app_manager') or usr.has_group(
            'pragmatic_delivery_control_app.group_delivery_control_app_user')
        return res

    def check_user(self):
        flag = self.is_delivery_control_access(self._context.get('uid'))
        if self.env['res.users'].browse(self._context.get('uid')).has_group('sbarro_cca.group_cca'):
            flag = False
        return flag

    def aslocaltimestr(self, utc_dt, local_tz):
        local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
        return local_tz.normalize(local_dt).strftime('%Y-%m-%d %H:%M:%S')

    def _get_timezone(self):
        """Returns time zone of superuser """
        user_pool = self.env['res.users']
        user = user_pool.browse(self._uid)
        user_tz = pytz.timezone(
            user.partner_id.tz) if user.partner_id.tz else pytz.utc
        return user_tz

    @api.model
    def get_date_order_to_timezone(self, order_id):
        sale_order_status = http.request.env['sale.order.status'].sudo()
        sale_order_brw = self.env['sale.order'].browse(order_id)
        sale_order_status_brw = sale_order_status.search([('sale_order_id', '=', order_id), ('order_status', '=', '1')],
                                                         limit=1)
        date_order_tme = ''
        if sale_order_brw.confirm_order_date:
            date_order_val = datetime.strptime(
                sale_order_brw.confirm_order_date, "%Y-%m-%d %H:%M:%S")
            local_tz = self._get_timezone()
            date_order_tme = self.aslocaltimestr(date_order_val, local_tz)
        return date_order_tme

    @api.model
    def get_create_date_timezone(self, driver_msg_id):
        create_date_val = datetime.strptime(
            driver_msg_id.create_date, "%Y-%m-%d %H:%M:%S")
        local_tz = self._get_timezone()
        create_date_time = self.aslocaltimestr(create_date_val, local_tz)

        return create_date_time


class WebsiteCustomer(http.Controller):
    @http.route([
        '/page/manage/delivery',
        '/page/manage/delivery/page/<int:page>',
    ], type='http', auth="public", website=True)
    def manage_sale_order_delivery(self, page=0, search='', opg=False, domain=None, **post):
        if domain is None:
            domain = []
        if opg:
            try:
                opg = int(opg)
            except ValueError:
                opg = OPG
            post["ppg"] = opg
        else:
            opg = OPG

        so = request.env['sale.order'].sudo()
        usr = request.env['res.users'].sudo().browse(request.uid)

        domain.append(('state', '=', 'sale'))
        url = "/page/manage/delivery"
        so_count = so.search_count(domain)
        pager = request.website.pager(url=url, total=so_count, page=page, step=opg, scope=7, url_args=post)
        sale_orders = so.search(domain, limit=opg, offset=pager['offset'], order="id desc")

        warehouses = http.request.env['stock.warehouse'].sudo().search_read(domain=[], fields=['name'])
        values = {
            'pager': pager,
            'search_count': so_count,  # common for all searchbox
            'sale_orders': sale_orders,
            'warehouses': warehouses,
            'wh_id': usr.warehouse_id.id
        }
        return request.render("pragmatic_delivery_control_app.manage_sale_order_delivery", values)

    # @http.route('/page/order-view/<order>', type='http', auth='public', website=True, csrf=False)
    # def get_sale_order_details(self, order=None):
    #     so = http.request.env['sale.order'].sudo()
    #     sale_order = so.browse([int(str(order))])
    #     order_driver_msg = http.request.env['order.driver.message'].sudo().search(
    #         [('order_id', '=', sale_order.id)])
    #     api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])
    #     if len(api_key) == 1:
    #         maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"
    #     else:
    #         maps_url = "//maps.google.com/maps/api/js?key=&amp;libraries=places&amp;language=en-AU"
    #
    #     return request.render('pragmatic_delivery_control_app.order-view', {'maps_script_url': maps_url,'order': sale_order,
    #                                                  'msg_dict': order_driver_msg,
    #                                                  'longitude': sale_order.partner_shipping_id.partner_longitude,
    #                                                  'latitude': sale_order.partner_shipping_id.partner_latitude,
    #                                                  'driver_longitude': sale_order.longitude,
    #                                                  'driver_latitude': sale_order.latitude})

    @http.route('/update-driver-location', type='http', auth='public', website=True)
    def update_drivers_live_location(self, **post):
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")

        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

            picking_orders = request.env['picking.order'].sudo().search([('state', 'in', ['assigned', 'accept']),
                                                                         ('delivery_boy', '=', res_partner.id),
                                                                         ('state', '!=', 'delivered'),
                                                                         ('state', '!=', 'canceled')])
            sale_orders = picking_orders.mapped('sale_order')
            orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
                                                             order='distance_btn_2_loc asc')

            warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
            routes = [[warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                       warehouse_driver[0].warehouse_id.partner_id.partner_longitude]]


            if post.get('lat') and post.get('lng'):
                routes = [[float(post.get('lat')), float(post.get('lng'))]]

            for rec in orders:
                routes.append([rec.partner_shipping_id.partner_latitude, rec.partner_shipping_id.partner_longitude, rec.name])

            routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                           warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            return json.dumps({'routes': routes})
        return json.dumps({})

    @http.route('/page/route/map', type='http', auth='public', website=True)
    def route_map(self, page=0, search='', opg=False, domain=None, **kwargs):
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")

        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])
            picking_orders = request.env['picking.order'].sudo().search([('state', 'in', ['assigned', 'accept']),
                                                                         ('delivery_boy', '=', res_partner.id),
                                                                         ('state', '!=', 'delivered'),
                                                                         ('state', '!=', 'canceled')])
            sale_orders = picking_orders.mapped('sale_order')
            orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
                                                             order='distance_btn_2_loc asc')

            warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
            routes = []
            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude, warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])

            if len(api_key) == 1:
                maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"

            for rec in orders:
                routes.append([rec.partner_shipping_id.partner_latitude, rec.partner_shipping_id.partner_longitude, rec.name])

            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            if picking_orders.ids:
                return request.render("pragmatic_delivery_control_app.route-map-view-driver", {
                    'maps_script_url': maps_url,
                    'picking_ids': picking_orders.ids,
                    'routes': json.dumps(routes)
                })

            else:
                return request.render("pragmatic_delivery_control_app.route-map-view-driver", {
                    'maps_script_url': maps_url,
                })

    # @http.route('/page/route/map/order_details', type='http', auth='public', website=True)
    # def order_map_route(self, page=0, search='', opg=False, domain=None, **kwargs):
    #     res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
    #     res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])
    #     picking_orders = request.env['picking.order'].sudo().search([('state', 'in', ['assigned', 'accept']),
    #                                                                  ('delivery_boy', '=', res_partner.id),
    #                                                                  ('state', '!=', 'delivered'),
    #                                                                  ('state', '!=', 'canceled')])
    #     sale_orders = picking_orders.mapped('sale_order')
    #     orders = request.env['sale.order'].sudo().search([('id', 'in', sale_orders.ids)],
    #                                                      order='distance_btn_2_loc asc')
    #     routes = []
    #
    #     for rec in orders:
    #         routes.append([rec.partner_shipping_id.partner_latitude, rec.partner_shipping_id.partner_longitude, rec.name])
    #
    #     order_details = ast.literal_eval(kwargs.get('waypoints_start'))
    #
    #     for record in range(1,len(order_details)-1):
    #         for rec in routes:
    #             lat_1 = float(format(rec[0])[0:5])
    #             lat_2 = float(format(order_details[record][0])[0:5])
    #             lng_1 = float(format(rec[1])[0:5])
    #             lng_2 = float(format(order_details[record][1])[0:5])
    #
    #             if lat_1 == lat_2 and lng_1 == lng_2:
    #                 order_details[record].append(rec[2])
    #
    #         if len(order_details[record]) == 1:
    #             order_details[record].append('')
    #
    #     if picking_orders.ids:
    #         return json.dumps({'order_details': order_details})
    #
    #     else:
    #         return json.dumps({})

    @http.route('/get-driver', type='http', auth='public', website=True, csrf=False)
    def get_all_driver(self, **post):
        driver_list = []
        warehouse = http.request.env['stock.warehouse'].sudo().browse(int(post.get('warehouse_id')))
        for driver in warehouse.driver_ids:
            if driver.status == 'available':
                vals = {
                    'name': driver.driver_id.name,
                    'id': driver.driver_id.id,
                }
                driver_list.append(vals)
        return json.dumps(driver_list)

    @http.route('/update_pickings', type='http', auth='public', website=True, csrf=False)
    def update_pickings(self, **post):
        res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
        res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

        if post.get('pickings'):
            pickings = ast.literal_eval(post.get('pickings'))

            picking_id = http.request.env['picking.order'].sudo().search([('id', 'in', pickings)])

            purchase_order_obj = request.env['purchase.order']
            purchase_order_line_obj = request.env['purchase.order.line']

            po_id = purchase_order_obj.sudo().create({
                'partner_id': res_partner.id,
            })

            uom_id = request.env['uom.uom'].sudo().search([('name', '=', 'Units')])

            purchase_order_line_obj.sudo().create({
                'product_id': request.env.user.company_id.company_delivery_product.id,
                'name': "Total Distance Travelled {} KM".format(int(post.get('total_distance')) / 1000),
                'product_qty': 1,
                'product_uom': uom_id.id,
                'price_unit': int(post.get('total_distance')) * res_partner.drive_rate / 1000,
                'date_planned': datetime.now(),
                'order_id': po_id.id,
            })

            # print("PAY TO DELIVERY BOY:::::::::::::::::::::::::",
            #       int(post.get('total_distance')) * res_partner.drive_rate / 1000)

        # for rec in picking_id:
        #     rec.action_picking_order_delivered()
        return json.dumps({})

    @http.route('/assign-driver', type='http', auth='public', website=True, csrf=False)
    def assign_driver(self, **post):
        driver_list = []
        #         picking_ids = registry['stock.picking'].search([('state','in',['assigned'])])
        #         registry['stock.picking'].browse(cr,SUPERUSER_ID,int(post.get('delivery_id'))).write({'owner_id':int(post.get('driver_id'))})
        sale_order = http.request.env['sale.order'].sudo().browse(int(post.get('order_id')))
        if sale_order.picking_ids:
            for picking in sale_order.picking_ids:
                picking.write(
                    {'owner_id': int(post.get('driver_id'))})
                driver_list.append('Assigned to driver')
                picking.action_done()
                sale_order.write({'driver_id': int(post.get('driver_id')), 'delivery_state': 'assigned'})
        else:
            driver_list.append("Picking not available")

        return json.dumps(driver_list)

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

    @http.route('/cancel/order', type='http', auth='public', website=True, csrf=False)
    def cancel_sale_order(self, **post):
        order_id = post.get('order_id')
        order = http.request.env['sale.order'].sudo().browse(int(order_id))
        order.action_cancel()
        _logger.info(
            _("Sale order %s has been cancelled from delivery control panel." % (order.name)))
        return json.dumps({'status': 'true'})
