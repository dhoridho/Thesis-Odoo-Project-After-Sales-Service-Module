from odoo.http import request
from odoo import http, tools
import json
from ...pragmatic_odoo_delivery_boy.controllers.main_driver import WebsiteCustomerDriver
from datetime import datetime, timedelta

class WebsiteDeliveryControlAppInherit(WebsiteCustomerDriver):

    @http.route('/page/job/list/driver', type='http', auth='public', website=True)
    def job_list_website(self, page=0, search='', opg=False, domain=None, **kwargs):
        if request.env.user._is_public():
            return request.render("pragmatic_odoo_delivery_boy.logged_in_template")
        else:
            res_users = request.env['res.users'].sudo().search([('id', '=', request.env.user.id)])
            res_partner = request.env['res.partner'].sudo().search([('id', '=', res_users.partner_id.id)])
            picking_orders = request.env['picking.order'].sudo().search(
                [('state', 'in', ['assigned', 'accept', 'in_progress', 'paid','picked']), ('delivery_boy', '=', res_partner.id)],
                order='distance_btn_2_loc asc'
            )
            pos_references = picking_orders.filtered(lambda po: po.order_source == 'pos').mapped('name')
            pos_orders = request.env['pos.order'].sudo().search([('state', '=', 'paid'),
                                                          ('pos_reference', 'in', pos_references)])
            warehouse_driver = request.env['stock.warehouse.driver'].sudo().search([('driver_id', '=', res_partner.id)])
            routes = []
            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            api_key = http.request.env['ir.config_parameter'].sudo().search([('key', '=', 'google.api_key_geocode')])

            if len(api_key) == 1:
                maps_url = "//maps.google.com/maps/api/js?key=" + api_key.value + "&amp;libraries=places&amp;language=en-AU"
            for picking in picking_orders.sudo():
                if all([picking.sale_order, picking.sale_order.invoice_ids, not picking.invoice]):
                    picking.update({'invoice': picking.sale_order.invoice_ids[0], 'payment': 'paid'})
                    if picking.sale_order.partner_shipping_id:
                        routes.append([picking.sale_order.partner_shipping_id.partner_latitude,
                                       picking.sale_order.partner_shipping_id.partner_longitude])
            for pos_order in pos_orders:
                routes.append([pos_order.pos_delivery_order_ref.pos_partner_id.partner_latitude,
                               pos_order.pos_delivery_order_ref.pos_partner_id.partner_longitude])
            if warehouse_driver:
                routes.append([warehouse_driver[0].warehouse_id.partner_id.partner_latitude,
                               warehouse_driver[0].warehouse_id.partner_id.partner_longitude])

            if picking_orders:
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
                    'maps_script_url': maps_url,
                    'picking_ids': picking_orders.ids,
                    'routes': routes,
                    'picking_orders': picking_orders.sudo(),
                    'delivery_boy': res_partner,
                    'pos_orders': pos_orders,
                    'pos_ids': pos_orders.ids
                })
            else:
                return request.render("pragmatic_odoo_delivery_boy.manage_job_list", {
                    'maps_script_url': maps_url,
                    'delivery_boy': res_partner,
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
            picking_order.sudo().message_post(body="{} - {}".format(message, picking_order.delivery_boy.name),
                                       type='comment')
            picking_order.sudo().state = 'failed_delivery'
            picking_order.sudo().delivery_boy = False
            picking_order.sudo().sale_order.delivery_state = 'ready'

        return json.dumps({})
