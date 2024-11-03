# -*- coding: utf-8 -*-

from odoo import fields, models, api, _, tools
import googlemaps
from datetime import datetime
from odoo.exceptions import UserError, ValidationError
import requests
import logging
_logger = logging.getLogger(__name__)

import json



class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_state = fields.Selection([
        ('ready', 'Ready'),
        ('assigned', 'Assigned'),
        ('paid', 'Paid'),
        ('delivered', 'Delivered'),
        ('issues', 'Issues'),
        ('complete', 'Complete')
    ], string="Delivery state", default="ready")
    order_source = fields.Selection([('erp', 'ERP'), ('web', 'Web')], string="Source", default="erp")
    driver_id = fields.Many2one('res.partner', string="Driver")
    order_driver_message_ids = fields.One2many(
        'order.driver.message', 'order_id', 'Order Driver Message Ref')
    payment_status_with_driver = fields.Boolean("Payment Status with driver")
    # capture driver moving location
    latitude = fields.Char('Latitude')
    longitude = fields.Char('Longitude')
    distance_btn_2_loc = fields.Float("Distance in KM", copy=False)

    @api.onchange('warehouse_id')
    def onchange_warehouse(self):
        self.latitude = self.warehouse_id.partner_id.partner_latitude
        self.longitude = self.warehouse_id.partner_id.partner_longitude

    # @api.model
    # def create(self, vals):
    #     res = super(SaleOrder, self).create(vals)
    #
    #
    #     google_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
    #     gmaps = googlemaps.Client(key=google_api_key)
    #
    #     # if res.partner_shipping_id.partner_latitude and res.partner_shipping_id.partner_longitude and res.warehouse_id.partner_id.partner_latitude and res.warehouse_id.partner_id.partner_longitude:
    #     source = (res.warehouse_id.partner_id.partner_latitude, res.warehouse_id.partner_id.partner_longitude)
    #     destination = (res.partner_shipping_id.partner_latitude, res.partner_shipping_id.partner_longitude)
    #     # elif not res.partner_shipping_id.partner_latitude and res.partner_shipping_id.partner_longitude:
    #     #     raise ValidationError("Partner's Latitude and Longitutde is missing")
    #     # else:
    #     #     raise ValidationError("Warehouse Latitude and Longitutde is missing")
    #     distance = gmaps.distance_matrix(source, destination)["rows"][0]["elements"][0]["distance"]
    #     res.distance_btn_2_loc = distance['value'] * 0.002
    #
    #
    #     # Delete previous cache
    #     # self.delete_previous_cache()
    #     if res.warehouse_id:
    #         res.write({
    #             'latitude': res.warehouse_id.partner_id.partner_latitude,
    #             'longitude': res.warehouse_id.partner_id.partner_longitude,
    #         })
    #     return res

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        google_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
        if not google_api_key:
            raise ValidationError(" Field value in system parameters is required")
        else:
            try:
                gmaps = googlemaps.Client(key=google_api_key)
            except Exception as e:
                _logger.exception(e)
            if res.partner_shipping_id.partner_latitude and res.partner_shipping_id.partner_longitude:
                if res.partner_shipping_id.partner_latitude and res.partner_shipping_id.partner_longitude and res.warehouse_id.partner_id.partner_latitude and res.warehouse_id.partner_id.partner_longitude:
                    source = (res.warehouse_id.partner_id.partner_latitude, res.warehouse_id.partner_id.partner_longitude)
                    destination = (res.partner_shipping_id.partner_latitude, res.partner_shipping_id.partner_longitude)
                elif not res.partner_shipping_id.partner_latitude and res.partner_shipping_id.partner_longitude:
                    raise ValidationError(_("Partner's Latitude and Longitutde is missing"))
                else:
                    raise ValidationError(_("Warehouse Latitude and Longitutde is missing"))

                try:
                    distance = gmaps.distance_matrix(source, destination)["rows"][0]["elements"][0]["distance"]
                    res.distance_btn_2_loc = distance['value'] * 0.002
                except Exception as e:
                    _logger.error(_("Invalid source or destination address."))
                    _logger.exception(e)

                # Delete previous cache
                # self.delete_previous_cache()
                if res.warehouse_id:
                    res.write({
                        'latitude': res.warehouse_id.partner_id.partner_latitude,
                        'longitude': res.warehouse_id.partner_id.partner_longitude,
                    })
                    return res
                else:
                    return False
            else:
                res.write({
                    'latitude': '',
                    'longitude': '',
                })
            return res

    def _action_confirm(self):
        confirm = super(SaleOrder, self)._action_confirm()
        if self.env.user != self.env.ref('base.public_user'):

            Param = self.env['res.config.settings'].sudo().get_values()
            if Param.get('whatsapp_instance_id') and Param.get('whatsapp_token'):
                if self.partner_id.country_id.phone_code and self.partner_id.mobile:
                    url = 'https://api.chat-api.com/instance' + Param.get('whatsapp_instance_id') + '/sendMessage?token=' + Param.get('whatsapp_token')
                    headers = {
                        "Content-Type": "application/json",
                    }
                    msg = "Your order " + self.name + " has confirmed."
                    whatsapp_msg_number = self.partner_id.mobile
                    whatsapp_msg_number_without_space = whatsapp_msg_number.replace(" ", "");
                    whatsapp_msg_number_without_code = whatsapp_msg_number_without_space.replace('+' + str(self.partner_id.country_id.phone_code), "")
                    tmp_dict = {
                        "phone": "+" + str(self.partner_id.country_id.phone_code) + "" + whatsapp_msg_number_without_code,
                        "body": msg

                    }
                    response = requests.post(url, json.dumps(tmp_dict), headers=headers)

                    if response.status_code == 201 or response.status_code == 200:
                        _logger.info("\nSend Message successfully")
                        mail_message_obj = self.env['mail.message']
                        comment = "fa fa-whatsapp"
                        body_html = tools.append_content_to_html('<div class = "%s"></div>' % tools.ustr(comment), msg)
                        # body_msg = self.convert_to_html(body_html)
                        mail_message_id = mail_message_obj.sudo().create({
                            'res_id': self.id,
                            'model': 'sale.order',
                            'body': body_html,
                        })
                else:
                    raise ValidationError("Please enter partner mobile number or select country for partner")
        all_pickings_obj = self.env['picking.order']
        for picking in self.picking_ids:
            if picking.state != 'cancel':
                all_pickings_id = all_pickings_obj.sudo().create({
                    'sale_order': self.id,
                    'picking': picking.id,
                    'distance_btn_2_loc': self.distance_btn_2_loc,
                    'zip_code': self.partner_shipping_id.zip,
                })
        ir_config = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
        if not ir_config:
            raise ValidationError(" Field value in system parameters is required")

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()

        all_pickings_obj = self.env['picking.order'].search([('sale_order','=',self.name)],limit=1)
        if all_pickings_obj:
            all_pickings_obj.sale_order.delivery_state = 'ready'
            all_pickings_obj.sudo().unlink()

    # def assign_driver(self):
    #     driver_cron = self.env['ir.cron'].sudo().search([('name', '=', 'Assign Driver Cron')])
    #     orders = self.sudo().search([('delivery_state', '=', 'ready'), ('state', '=', 'sale'),
    #                                  ('confirmation_date', '<', driver_cron.nextcall)])
    #     # orders = self.sudo().search([])
    #     google_api_key = self.env['ir.config_parameter'].sudo().get_param('google.api_key_geocode')
    #     gmaps = googlemaps.Client(key=google_api_key)
    #
    #     all_pickings_obj = self.env['picking.order']
    #
    #     for rec in orders:
    #         # rec.write({
    #         #     'driver_id': None,
    #         #     'delivery_state': 'ready'
    #         # })
    #
    #         drivers = rec.warehouse_id.driver_ids
    #
    #         destination = (rec.partner_shipping_id.partner_latitude, rec.partner_shipping_id.partner_longitude)
    #         smallest_distance = None
    #
    #         for driver in drivers:
    #             source = (driver.driver_id.partner_latitude, driver.driver_id.partner_longitude)
    #
    #             distance = gmaps.distance_matrix(source, destination)["rows"][0]["elements"][0]["distance"]
    #             if smallest_distance and smallest_distance > distance['value']:
    #                 smallest_distance = (distance['value'])
    #                 driver_obj = driver.driver_id
    #             elif not smallest_distance:
    #                 smallest_distance = (distance['value']) * 2 if distance['value'] else (distance['value'] + 1) * 2
    #                 driver_obj = driver.driver_id
    #
    #         if rec.picking_ids:
    #             for picking in rec.picking_ids:
    #                 # sale_order_line = self.env['sale.order.line'].create({
    #                 #     'product_id': rec.warehouse_id.product_id.id,
    #                 #     'product_uom_qty': 1,
    #                 #     'price_unit': smallest_distance*driver_obj.drive_rate/1000,
    #                 #     'order_id': rec.id,
    #                 # })
    #
    #                 picking.write({
    #                     'owner_id': driver_obj.id,
    #                 })
    #
    #                 picking.action_assign_owner()
    #                 rec.write({
    #                     'driver_id': driver_obj.id,
    #                     'delivery_state': 'assigned',
    #                     'distance_btn_2_loc': smallest_distance,
    #                 })
    #
    #             picking_id = all_pickings_obj.search([('sale_order', '=', rec.id)])
    #             if not picking_id:
    #                 all_pickings_obj.sudo().create({
    #                     'distance_btn_2_loc': smallest_distance,
    #                     'state': 'assigned',
    #                     'sale_order': rec.id,
    #                     'delivery_boy': driver_obj.id,
    #                     'picking': rec.warehouse_id.id,
    #                     'assigned_date': datetime.now(),
    #                 })


class SaleOrderDriverMessage(models.Model):
    _name = "order.driver.message"
    _description = 'Order Driver Message'

    order_id = fields.Many2one('sale.order', 'Sale Order')
    message = fields.Char("Message")
    send_to_driver = fields.Boolean("Send To Driver")
    partner_id = fields.Many2one('res.partner', string='Messenger')
