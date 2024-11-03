# -*- coding: utf-8 -*-
import pytz

from odoo import models, fields, api
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import time
from datetime import date
from datetime import datetime, timedelta


class hotel_room_dashboard(models.Model):
    """ Class for showing Rooms Dashboard"""
    _name = 'hotel.room.dashboard'
    _description = 'Room Dashboard'

    name = fields.Char('Name', )

    def open_dashboard(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/hotel_room_dashboard/web/',
            'target': 'self',
        }


class hotel_reservation(models.Model):
    _inherit = 'hotel.reservation'

    """ Inherited to set default values in reservation form"""

    def action_folio_confirm(self):
        search_id = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if search_id and search_id.state == 'draft':
            search_id.action_confirm()
        return True

    def action_folio_checkout(self):
        search_id = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if search_id and search_id.state == 'progress':
            search_id.action_checkout()

    def action_folio_done(self):
        search_id = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if search_id and search_id.state == 'check_out':
            search_id.action_done()

    # @api.model
    # def default_get(self, fields):
    #     res = super(hotel_reservation, self).default_get(fields)
    #     print ("context--------", self._context)
    #     if 'checkin' in self._context and 'checkout' in self._context and 'date_order' in res:
    #         room_obj = self.env['hotel.room']
    #         # print("ccccccccccccccccccccc",str(self._context['booking_data'][0]).split("_")[0])
    #         room_brw = room_obj.search([('id', '=', self._context['hotel_resource'])])
    #         pricelist = self.env['sale.shop'].browse(int(self._context['shop'])).pricelist_id.id
    #         if pricelist == False:
    #             raise UserError(('Please set the Pricelist on the shop  %s to proceed further') % room_brw.shop_id.name)
    #
    #         res['checkin'] =self._context['checkin']
    #         res['checkout'] = self._context['checkout']
    #
    #         res['shop_id'] = int(self._context['shop'])
    #         res['pricelist_id'] = pricelist
    #         res['note'] = self._context['checkin']
    #         ctx = self._context and self._context.copy() or {}
    #         ctx.update({'date': self._context['checkin']})
    #
    #
    #         print("room_brw.product_id.uom_id.id::::::::",room_brw.product_id.uom_id.id)
    #         # res_line = {
    #         #     'categ_id': room_brw.categ_id.id,
    #         #     'room_number': room_brw.product_id.id,
    #         #     'checkin': self._context['checkin'],
    #         #     'checkout':self._context['checkout'],
    #         #     'price': self.env['product.pricelist'].with_context(ctx).price_get(room_brw.product_id.id, 1,{
    #         #         'uom':  room_brw.product_id.uom_id.id,
    #         #
    #         #     })[pricelist]
    #         # }
    #         #
    #         #
    #         #
    #         # res['reservation_line'] = [[0, 0, res_line]]
    #
    #
    #
    #
    #         # print("res['reservation_line'] ::::::::::::;;",res['reservation_line'] )
    #         print("\n\n\nyessssss res==========", res, "\n\n")
    #     return res

    def write(self, vals):

        # print("ffffffffffffffffffffffffffff", vals)

        return super(hotel_reservation, self).write(vals)

    def get_folio_status(self):
        folio_record = self.env['hotel.folio'].search([('reservation_id', '=', self.id)])
        if folio_record:
            return folio_record.state

        return False

    # def update_reservation_old(self, resourceId, description):
    #     print("fffffffffffffffff", resourceId, description)

    def update_reservation_line(self, description, start, end, resourceId, start_only_date, end_only_date):
        reservation = self.env['hotel.reservation'].search([('reservation_no', '=', description)])

        # print("reservation::::::::::::::::", reservation, resourceId)

        if resourceId:
            room_id = self.env['product.product'].search([('id', '=', resourceId)])
            # print("room_id:::::::::", room_id)
        for line_id in reservation:
            for line in line_id.reservation_line:
                if line.room_number.id == room_id.id:

                    # print("line_id::::::::::::", line_id.folio_id)
                    if start:
                        line.write({'checkin': start})
                    if end:
                        line.write({'checkout': end})

                if reservation.state == 'confirm':
                    # print("reservation:::::::::::::::::", reservation.state)

                    hotel_history = self.env['hotel.room.booking.history'].search([('booking_id', '=', reservation.id)])
                    # print("hotel_history::::::::::::::::::", hotel_history)
                    for hotel_history_line in hotel_history:
                        # print("hotel_history_line.product_id.id::::::::;", hotel_history_line.product_id,
                        #       line.room_number.name)
                        if hotel_history_line.product_id == line.room_number.id and hotel_history.booking_id.id == line.line_id.id:
                            if hotel_history_line.name == line.room_number.name:
                                if start:
                                    hotel_history_line.write({"check_in": start})
                                    hotel_history_line.write({"check_in_date": start_only_date})
                                if end:
                                    hotel_history_line.write({"check_out": end})
                                    hotel_history_line.write({"check_out_date": end_only_date})

        if reservation:
            folio = self.env['hotel.folio'].search([('reservation_id', '=', reservation.reservation_no)])
            # print("folio:::::::::::::", folio)

            for folio_line in folio.room_lines:
                # print("folio_line::::::::::;", folio_line.product_id, room_id.id)

                if folio_line.product_id.id == room_id.id:
                    if start:
                        folio_line.write({'checkin_date': start})
                    if end:
                        folio_line.write({'checkout_date': end})
                    folio_line.on_change_checkout()

    def update_room(self, description, resourceId, start1, end1, old_id, start_only_date, end_only_date):
        # print("resourceId::::::::::::", description, resourceId, start1, end1, old_id, start_only_date, end_only_date)
        # print("ffffffffffffff",)

        if resourceId:
            room_id = self.env['product.product'].search([('id', '=', resourceId)])
            # print("room_id:::::::::", room_id)
        if old_id:
            room_id_old = self.env['product.product'].search([('id', '=', old_id)])
            # print("room_id:::::::::", room_id_old)

        reservation = self.env['hotel.reservation'].search([('reservation_no', '=', description)])

        # print("reservation::::::::::::::::", reservation, resourceId)

        if resourceId:
            room_id = self.env['product.product'].search([('id', '=', resourceId)])
            # print("room_id:::::::::", room_id)
        for line_id in reservation:
            for line in line_id.reservation_line:

                if room_id_old:
                    if line.room_number.id == room_id_old.id:

                        # print("line_id::::::::::::", line_id.folio_id)
                        if start1:
                            line.write({'checkin': start1})
                        if end1:
                            line.write({'checkout': end1})

                        if room_id:
                            line.write({'room_number': room_id.id})
                            line.write({'categ_id': room_id.categ_id.id})
                if reservation.state != 'draft':
                    # print("reservation:::::::::::::::::",reservation.state)

                    hotel_history = self.env['hotel.room.booking.history'].search([('booking_id', '=', reservation.id)])
                    hotel_room = self.env['hotel.room'].search([('product_id', '=', room_id.id)])
                    # print("hotel_history::::::::::::::::::", hotel_history)
                    for hotel_history_line in hotel_history:
                        # print("hotel_history_line.product_id.id::::::::;",hotel_history_line.product_id,room_id_old.id)
                        if hotel_history_line.product_id == room_id_old.id and hotel_history.booking_id.id == line.line_id.id:
                            # print("hhhhhhhhhhhhhhhhhhhhhhhhhhhhhh")
                            if start1:
                                hotel_history_line.write({"check_in": start1})
                                hotel_history_line.write({"check_in_date": start_only_date})
                            if end1:
                                hotel_history_line.write({"check_out": end1})
                                hotel_history_line.write({"check_out_date": end_only_date})
                            if hotel_room:
                                hotel_history_line.write({"history_id": hotel_room.id})
                                hotel_history_line.write({"name": hotel_room.name})
                            if room_id:
                                hotel_history_line.write({"product_id": room_id.id})
                                hotel_history_line.write({"category_id": room_id.categ_id.id})

        if reservation:
            folio = self.env['hotel.folio'].search([('reservation_id', '=', reservation.reservation_no)])
            # print("folio:::::::::::::", folio)

            for line in folio.room_lines:
                # print("line:::::::::", line)
                if room_id_old:
                    if line.product_id.id == room_id_old.id:
                        # print("line:::::::::::::::::::::::", line)

                        if room_id:
                            line.write({"product_id": room_id.id})
                            line.write({"name": room_id.name})
                            line.write({"categ_id": room_id.categ_id.id})

                        if end1:
                            # print("ffffffffffffffffffffffff2", end1)
                            line.write({'checkout_date': end1})

                        if start1:
                            # print("ffffffffffffffffffffffff", start1)
                            line.write({'checkin_date': start1})

                        line.on_change_checkout()

                else:
                    if room_id:
                        line.write({"product_id": room_id.id})
                        line.write({"name": room_id.name})
                        line.write({"categ_id": room_id.categ_id.id})

                    if end1:
                        # print("ffffffffffffffffffffffff2", end1)
                        line.write({'checkout_date': end1})

                    if start1:
                        # print("ffffffffffffffffffffffff", start1)
                        line.write({'checkin_date': start1})
                    line.on_change_checkout()

    @api.model
    def default_get(self, fields):
        res = super(hotel_reservation, self).default_get(fields)
        # print("contextdddddddddddd--------", fields)
        if 'booking_data' in self._context and 'booking_data' in self._context and 'date_order' in res:
            room_obj = self.env['hotel.room']
            room_brw = room_obj.search([('name', '=', str(self._context['booking_data'][0]).split("_")[0])])
            pricelist = self.env['sale.shop'].browse(int(self._context['shop'])).pricelist_id.id
            # print("pricelist:::::::::::::::", pricelist)
            if not pricelist:
                raise UserError(('Please set the Pricelist on the shop  %s to proceed further') % room_brw.shop_id.name)

            res['checkin'] = str(self._context['booking_data'][0]).split("_")[1] + " " + "11:00:00"
            res['checkout'] = str(self._context['booking_data'][-1]).split("_")[1] + " " + "09:00:00"

            res['shop_id'] = int(self._context['shop'])
            res['pricelist_id'] = pricelist
            ctx = self._context and self._context.copy() or {}
            ctx.update({'date': str(self._context['booking_data'][0]).split("_")[1] + " " +
                                str(res['date_order']).split(" ")[1]})

            res_line = {
                'categ_id': room_brw.categ_id.id,
                'room_number': room_brw.product_id.id,
                'checkin': res['checkin'],
                'checkout': res['checkout'],
                'price': self.env['product.pricelist'].with_context(ctx).price_get(room_brw.product_id.id, 1, {
                    'uom': room_brw.product_id.uom_id.id,
                    'date': str(self._context['booking_data'][0]).split("_")[1] + " " +
                            str(res['date_order']).split(" ")[1],
                })[pricelist]
            }

            res['reservation_line'] = [[0, 0, res_line]]
            # print("\n\n\nyessssss res==========", res, "\n\n")
        else:
            if 'shop' in self._context and 'hotel_resource' in self._context:
                room_obj = self.env['hotel.room']
                # print("ccccccccccccccccccccc1")
                room_brw = room_obj.search([('id', '=', self._context['hotel_resource'])])
                pricelist = self.env['sale.shop'].browse(int(self._context['shop'])).pricelist_id.id
                if pricelist == False:
                    raise UserError(
                        ('Please set the Pricelist on the shop  %s to proceed further') % room_brw.shop_id.name)
                res['shop_id'] = int(self._context['shop'])
                res['pricelist_id'] = pricelist

        return res
