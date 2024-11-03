from odoo import api, fields, models,_
import odoo
import requests
from odoo import http, _
from odoo.http import request
import json
from datetime import datetime
import pytz
from odoo.exceptions import UserError
from odoo import models , _
from odoo.exceptions import AccessDenied
from odoo import http, tools, SUPERUSER_ID
import logging
_logger = logging.getLogger(__name__)

class Website_acknowledgement_code(http.Controller):

    @http.route('/get_acknowledgement_code', type='http', auth="public", methods=['POST'], website=True)
    def get_acknowledgement_code(self, **kwargs):
        picking = request.env['picking.order'].sudo().search([('sale_order', '=' , kwargs['picking_order_number']),('state', 'in', ['picked','paid'])])
        picking = picking.with_user(SUPERUSER_ID)
        order_stage_id = request.env['order.stage'].sudo().search([('action_type', '=', 'delivered')])
        if picking.customer_code == kwargs['customer_code']:
            picking.action_picking_order_delivered()
            order = picking.sale_order
            order.sudo().write({
                'stage_id': order_stage_id.id
            })
            Param = http.request.env['res.config.settings'].sudo().get_values()
            if Param.get('whatsapp_instance_id') and Param.get('whatsapp_token'):
                if order.partner_id.country_id.phone_code and order.partner_id.mobile:
                    url = 'https://api.chat-api.com/instance' + Param.get(
                        'whatsapp_instance_id') + '/sendMessage?token=' + Param.get('whatsapp_token')
                    headers = {
                        "Content-Type": "application/json",
                    }
                    whatsapp_msg_number = order.partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace(
                        '+' + str(order.partner_id.country_id.phone_code), "")
                    msg = "Your order has delivered."
                    tmp_dict = {
                        "phone": "+" + str(
                            order.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
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
                            'res_id': picking.id,
                            'model': 'picking.order',
                            'body': body_html,
                        })
            picking.order_delivered()
        else:
            kwargs['error'] = ("Code Is Incorrect Re-Enter The Code.")  
            return http.request.render("pragmatic_delivery_acknowledgement.error_popup",kwargs)
        return request.redirect('/page/job/list/driver')
    
    def _get_search_picking_domain(self, search):
        domain = []
        if search:
            for srch in search.split(" "):
                domain = [('name', 'ilike', srch)]
        return domain

    @http.route('/driver/broadcast/order', type='http', auth='public', website=True)
    def broadcast_order(self, page=0, search='', opg=False, domain=None, **kwargs):
        domain = self._get_search_picking_domain(search)
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])

            picking_orders = request.env['picking.order'].sudo().search(
                [('state', 'in', ['created']), ('is_broadcast_order', '=',True)],
                order='distance_btn_2_loc asc')

            picking = picking_orders.picking
            store = request.env['store.configuration'].sudo().search([('delivery_boy_ids','in',request._uid)])
            user_picking = []
            for location in store.location_id:
                new_pickings = picking.filtered(lambda p: p.location_id == location)
                for np in new_pickings:
                    user_picking.append(np.id)
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
                    picking.update({'invoice': picking.sale_order.invoice_ids[0], 'payment': 'paid'})
                    routes.append([picking.sale_order.partner_shipping_id.partner_latitude,
                                   picking.sale_order.partner_shipping_id.partner_longitude])

            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            # if picking_orders.ids:
            if search:
                sale_order = request.env['sale.order'].sudo().search(domain)
                if sale_order:
                        picking_orders = request.env['picking.order'].sudo().search(['&','&',
                                                                                     ('sale_order','in',sale_order.ids),
                                                                                     ('is_broadcast_order', '=',True),
                                                                                     ('state', 'in', ['created'])])
                        return request.render("pragmatic_delivery_acknowledgement.manage_broadcast_order", {
                            'picking_ids':user_picking,
                            'picking_orders': picking_orders,
                        })
                else:
                    return request.render("pragmatic_delivery_acknowledgement.manage_broadcast_order", {
                            'maps_script_url': maps_url,
                            # 'picking_ids': picking_orders.ids,
                            'picking_ids':user_picking,
                            'routes': routes,
                            'picking_orders': picking_orders,
                            'delivery_boy': res_partner,
                        })



            if user_picking:
                return request.render("pragmatic_delivery_acknowledgement.manage_broadcast_order", {
                    'maps_script_url': maps_url,
                    # 'picking_ids': picking_orders.ids,
                    'picking_ids':user_picking,
                    'routes': routes,
                    'picking_orders': picking_orders,
                    'delivery_boy': res_partner,
                })
            else:
                return request.render("pragmatic_delivery_acknowledgement.manage_broadcast_order", {
                    # 'picking_ids': picking_orders,
                    'picking_ids':user_picking,
                    'picking_orders': picking_orders,
                })

    @http.route('/page/broadcast/order-view/<order>', type='http', auth='public', website=True, csrf=False)
    def get_broadcast_order_details(self, order=None, **kwargs):
        so = http.request.env['sale.order'].sudo()
        sale_order = so.browse([int(str(order))])
        order_driver_msg = http.request.env['order.driver.message'].sudo().search(
            [('order_id', '=', sale_order.id)])
        stock_pickings = http.request.env['stock.picking'].sudo().search(
            [('sale_id', '=', sale_order.id)])

        picking_order_id = http.request.env['picking.order'].sudo().search([('sale_order', '=', sale_order.id)])
        return request.render('pragmatic_delivery_acknowledgement.broadcast-order-view',
                              {
                                  'order': sale_order,
                                  'msg_dict': order_driver_msg,
                                  'picking_order_payment_status': picking_order_id.payment.capitalize() if picking_order_id.payment else '',
                                  'longitude': sale_order.partner_shipping_id.partner_longitude,
                                  'latitude': sale_order.partner_shipping_id.partner_latitude,
                                  'driver_longitude': stock_pickings.owner_id.partner_longitude,
                                  'driver_latitude': stock_pickings.owner_id.partner_latitude,
                                  'driver_mobile': stock_pickings.owner_id.mobile,
                                  'picking_order': picking_order_id,
                              })

    @http.route('/broadcast/accept_broadcast_order', type='http', auth="public", website=True, csrf=False)
    def accept_broadcast_order(self, **post):
        order_no = post.get('order_number')
        sale_order = http.request.env['sale.order'].sudo().search([('name', '=', order_no)])
        picking_order = request.env['picking.order'].sudo().search([('sale_order', '=', sale_order.id)])
        user_id = request.env['res.users'].browse(request._uid)
        if picking_order:
            picking_order.delivery_boy = user_id.partner_id.id
        timezone = sale_order._context.get('tz')
        create_date = datetime.now(pytz.timezone(timezone)).strftime("%Y-%m-%d %H:%M")
        if post.get('delivery_order_status') == 'accept':
            picking_order.write({'state': 'accept'})

            sale_order.write({'delivery_state': 'assigned'})
            # sale_order.write({'state': 'picked'})
            order_stage_id = request.env['order.stage'].search([('action_type', '=', 'assigned')])
            if order_stage_id:
                picking_order.write({'stage_id': order_stage_id.id})

            picking_order.message_post(
                body="<ul><li>Delivery Order Accepted By {0}</li> <li>State: {2}</li> <li>Create Date: {1}</li></ul>".format(
                    picking_order.delivery_boy.name, create_date, picking_order.sale_order.stage_id.name),
                type='comment')
            return json.dumps({'status': True})
        elif post.get('delivery_order_status') == 'reject':
            message = "<ul><li>Delivery Order Rejected By {0}</li> <li>State: {2}</li> <li>Create Date: {1}</li></ul>".format(
                picking_order.delivery_boy.name, create_date, picking_order.sale_order.stage_id.name)
            picking_order.message_post(body=message, type='comment')
            vals = {
                'driver_id': picking_order.delivery_boy.id,
                'picking_id': picking_order.id,
                'assign_date': picking_order.assigned_date,
                'reject_date': datetime.now(),
            }
            reject_picking = request.env['reject.picking.order'].sudo().create(vals)
            picking_order.write({'state': 'created', 'delivery_boy': False})
            sale_order.write({'delivery_state': 'ready'})
            return json.dumps({'status': False})