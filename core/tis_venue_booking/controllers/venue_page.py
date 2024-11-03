# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2019. All rights reserved.

from dateutil import parser

from odoo import http, _
from odoo.http import request
from datetime import datetime, timedelta
import json
import pytz

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT



class VenuePage(http.Controller):

    @http.route('/venue', type='http', auth="public", website=True)
    def render_venue_page(self, **kwargs):
        amenities = []
        location_dict = {}
        venues = http.request.env['venue.venue'].sudo().search([], limit=6)
        venue_rating = {}
        venue_type = request.env['venue.type'].search([])
        all_venues = http.request.env['venue.venue'].sudo().search([])
        all_locations = request.env['state.cities'].search([])

        for venue in venues:
            for amenity in venue.venue_amenities_ids:
                if amenity.amenities_id not in amenities:
                    amenities.append(amenity.amenities_id)
            venue_count = http.request.env['venue.venue'].sudo().search_count(
                [('location_id', '=', venue.location_id.id)])
            if venue.location_id and venue.location_id not in location_dict:
                location_dict.update({venue.location_id: venue_count})
            rating = request.website.viewref('tis_venue_booking.venue_second_page_template').active
            if rating:
                if venue in venue_rating:
                    venue_rating[venue] = request.env["ir.ui.view"]._render_template(
                        'portal_rating.rating_widget_stars_static', values={
                            'rating_avg': venue.rating_avg,
                            'rating_count': venue.rating_count
                        })
                else:
                    venue_rating[venue] = request.env["ir.ui.view"]._render_template(
                        'portal_rating.rating_widget_stars_static', values={
                            'rating_avg': venue.rating_avg,
                            'rating_count': venue.rating_count
                        })
        return http.request.render('tis_venue_booking.venue_page_template', {
            'venue_details': venues,
            'all_venues': all_venues,
            'amenities': amenities,
            'venue_places': location_dict,
            'venue_rating': venue_rating,
            'venue_type': venue_type,
            'all_locations': all_locations
        })

    def convert_to_datetime(self, input_date_string):
        date_processing = input_date_string[:-3]

        datetime_object = datetime.strptime(date_processing, '%m/%d/%Y %H:%M')
        return datetime_object

    # @http.route(['/venue/filtered'], type='http', auth="public", methods=['POST'], website=True)
    # def filtered_venue_page(self, **post):
    #     print('aaaaaaaaaaaaaaaaaaa', post)
    #     print('aaaaaaaaaaaaaaaaaaa', post.get('venue'))
    #     print('aaaaaaaaaaaaaaaaaaa', post.get('venue_type_id'))
    #     ven = []
    #     domain = []
    #     all_amenities = []
    #     location_dict = {}
    #     venue_rating = {}
    #     venue_type = request.env['venue.type'].search([])
    #     all_venues = http.request.env['venue.venue'].sudo().search([])
    #     for venue in all_venues:
    #         print('venue', venue)
    #         for amenity in venue.venue_amenities_ids:
    #             print('amenity', amenity)
    #             if amenity.amenities_id not in all_amenities:
    #                 all_amenities.append(amenity.amenities_id)
    #                 print('all_amenities', all_amenities)
    #         venue_count = http.request.env['venue.venue'].sudo().search_count(
    #             [('location_id', '=', venue.location_id.id)])
    #         print('venue_count', venue_count)
    #         if venue.location_id and venue.location_id not in location_dict:
    #             location_dict.update({venue.location_id: venue_count})
    #             print('location_dict', location_dict)
    #     if post.get('search_by') == 'venue':
    #         if post.get('venue') and not post.get('venue') == "-- select an option --":
    #             domain.append(('id', '=', post.get('venue')))
    #             print('domain', domain)
    #     elif post.get('search_by') == 'others':
    #         amenities_ids = request.httprequest.form.getlist('amenities')
    #         venue_amenities = []
    #         if amenities_ids:
    #             for amenity in amenities_ids:
    #                 amenity_rec = http.request.env['venue.amenities'].sudo().search(
    #                     [('amenities_id', '=', (int(amenity)))])
    #                 for rec in amenity_rec:
    #                     if rec.id not in venue_amenities:
    #                         venue_amenities.append(rec.id)
    #             domain.append(('venue_amenities_ids', 'in', venue_amenities))
    #         if post.get('capacity') and int(post.get('capacity')) > 0:
    #             domain.append(('capacity', '<=', int(post.get('capacity'))))
    #         if post.get('budget') and int(post.get('budget')) > 0:
    #             if post.get('booking_type') == 'day':
    #                 domain.append(('charges_per_day', '<=', int(post.get('budget'))))
    #             elif post.get('booking_type') == 'hour':
    #                 domain.append(('charges_per_hour', '<=', int(post.get('budget'))))
    #         if post.get('location'):
    #             domain.append(('location_id', '=', int(post.get('location'))))
    #     print('DOMAIN', domain)
    #     venues = http.request.env['venue.venue'].sudo().search(domain)
    #     print('venuesss', venues)
    #     rating = request.website.viewref('tis_venue_booking.venue_second_page_template').active
    #     for venue in venues:
    #         print('VENUE', venue.name)
    #         if rating:
    #             if venue in venue_rating:
    #                 venue_rating[venue] = request.env["ir.ui.view"]._render_template(
    #                     'portal_rating.rating_widget_stars_static', values={
    #                         'rating_avg': venue.rating_avg,
    #                         'rating_count': venue.rating_count
    #                     })
    #             else:
    #                 venue_rating[venue] = request.env["ir.ui.view"]._render_template(
    #                     'portal_rating.rating_widget_stars_static', values={
    #                         'rating_avg': venue.rating_avg,
    #                         'rating_count': venue.rating_count
    #                     })
    #
    #
    #         booking = http.request.env['booking.booking'].sudo().search(
    #             [
    #                 # ('venue_id', '=', venue.id), ('state', '=', 'confirm'),
    #                 ('venue_id', '=', post.get('venue')), ('state', '=', 'confirm'),
    #                 '|', '|',
    #                 '&', ('from_date', '<=', self.convert_to_datetime(post.get('booking_from'))),
    #                 ('to_date', '>=', self.convert_to_datetime(post.get('booking_from'))),
    #                 '&', ('from_date', '<=', self.convert_to_datetime(post.get('booking_to'))),
    #                 ('to_date', '>=', self.convert_to_datetime(post.get('booking_to'))),
    #                 '&', ('from_date', '>', self.convert_to_datetime(post.get('booking_from'))),
    #                 ('to_date', '<', self.convert_to_datetime(post.get('booking_to'))), ]
    #         )
    #         print('domain', domain)
    #         print("self.convert_to_datetime(post.get('booking_from'))", self.convert_to_datetime(post.get('booking_from')))
    #         print('booking ******************', booking)
    #         print('venue.......id', venue.id)
    #         print('venue______id', booking.venue_id)
    #         print('all_venues @@', all_venues)
    #         print('booking @@', booking)
    #
    #         if booking:
    #             print('strtretretetertreterterrey')
    #             print('ven', ven)
    #             print('all_venues', all_venues)
    #             print('venue_type', venue_type)
    #             errrrrorrrrrrr
    #             return http.request.render('tis_venue_booking.venue_canceled_page_template')
    #             # continue
    #         ven.append(venue)
    #         print('ven', ven)
    #     return http.request.render('tis_venue_booking.venue_detail_page', {
    #         'venue_details': ven,
    #         # 'all_venues': all_venues,
    #         'amenities': all_amenities,
    #         'venue_places': location_dict,
    #         'venue_rating': venue_rating,
    #         'venue_type': venue_type
    #     })

    ###############################################

    @http.route(['/venue/filtered'], type='http', auth="public", methods=['POST'], website=True)
    def filtered_venue_page(self, **post):
        global location, location_id
        all_amenities = []
        venues = []
        # from_date = post.get('booking_from')
        # to_date = post.get('booking_to')
        venue_type = request.env['venue.type'].search([])
        all_locations = request.env['state.cities'].search([])
        search_location_id = ''
        search_location_name = ""
        search_location = post.get('location')
        search_venue = post.get('venue')
        # only one venue case
        if search_venue != '-- select an option --' and search_location != '-- select an option --':
            display_venue = http.request.env['venue.venue'].sudo().search([('id', '=', search_venue)])
            all_venues = http.request.env['venue.venue'].sudo().search([('location_id.id', '=', search_location)])
            for venue in display_venue:
                for amenity in venue.venue_amenities_ids:
                    if amenity.amenities_id not in all_amenities:
                        all_amenities.append(amenity.amenities_id)
            return http.request.render('tis_venue_booking.venue_detail_page', {
                'venue_type': venue_type,
                'all_venues': all_venues,
                'get_venues': display_venue,
                'amenities': all_amenities,
                'all_locations': all_locations,
                'location': request.env['state.cities'].browse(int(post.get('location'))).name,
                'location_id': request.env['state.cities'].browse(int(post.get('location'))).id,
                'booking_from': post.get('booking_from'),
                'booking_to': post.get('booking_to'),
                'venue_id': request.env['venue.venue'].browse(int(post.get('venue'))).id,
                'venue': request.env['venue.venue'].browse(int(post.get('venue'))).name
            })
        # only venue and not location:
        if search_venue != '-- select an option --' and search_location == '-- select an option --':
            display_venue = http.request.env['venue.venue'].sudo().search([('id', '=', search_venue)])
            all_venues = http.request.env['venue.venue'].sudo().search([])
            for venue in display_venue:
                for amenity in venue.venue_amenities_ids:
                    if amenity.amenities_id not in all_amenities:
                        all_amenities.append(amenity.amenities_id)
            return http.request.render('tis_venue_booking.venue_detail_page', {
                'venue_type': venue_type,
                'all_venues': all_venues,
                'get_venues': display_venue,
                'amenities': all_amenities,
                'all_locations': all_locations,
                'location': '-- select an option --',
                'location_id': '-- select an option --',
                'booking_from': post.get('booking_from'),
                'booking_to': post.get('booking_to'),
                'venue_id': request.env['venue.venue'].browse(int(post.get('venue'))).id,
                'venue': request.env['venue.venue'].browse(int(post.get('venue'))).name
            })

        if search_location != '-- select an option --':
            search_location_id = request.env['state.cities'].browse(int(post.get('location'))).id
            search_location_name = request.env['state.cities'].browse(int(post.get('location'))).name
            all_venues = http.request.env['venue.venue'].sudo().search([('location_id.id', '=', search_location)])
            location = request.env['state.cities'].browse(int(post.get('location'))).name
            location_id = request.env['state.cities'].browse(int(post.get('location'))).id
        elif search_location == '-- select an option --':
            all_venues = http.request.env['venue.venue'].sudo().search([])
            location = '-- select an option --'
            location_id = '-- select an option --'
        all_locations = request.env['state.cities'].search([])
        for venue in all_venues:
            for amenity in venue.venue_amenities_ids:
                if amenity.amenities_id not in all_amenities:
                    all_amenities.append(amenity.amenities_id)
        booking = http.request.env['booking.booking'].sudo().search(
            [
                '|', '|',
                '&', ('from_date', '<=', self.convert_to_datetime(post.get('booking_from'))), (
                'to_date', '>=', self.convert_to_datetime(post.get('booking_from'))),
                '&', ('from_date', '<=', self.convert_to_datetime(post.get('booking_to'))), (
                'to_date', '>=', self.convert_to_datetime(post.get('booking_to'))),
                '&', ('from_date', '>', self.convert_to_datetime(post.get('booking_from'))), (
                'to_date', '<', self.convert_to_datetime(post.get('booking_to'))),
            ]
        )
        venue_ids = booking.mapped('venue_id')
        venue_options = http.request.env['venue.venue'].sudo().search([])
        all_venues = all_venues - venue_ids
        return http.request.render('tis_venue_booking.venue_detail_page', {
            'venue_type': venue_type,
            'all_venues': venue_options,
            'get_venues': all_venues,
            'amenities': all_amenities,
            'all_locations': all_locations,
            'location': location,
            'location_id': location_id,
            'booking_from': post.get('booking_from'),
            'booking_to': post.get('booking_to'),
            'venue_id': '-- select an option --',
            'venue': '-- select an option --'
        })

    @http.route('/filter/budget', type='http', auth="public", website=True, methods=['GET', 'POST'], csrf=False)
    def filter_budget(self, **value):
        global get_venue
        venue_type = request.env['venue.type'].search([])
        budget = value.get('budget')
        capacity = value.get('capacity')
        amenities = value.get('venue_amenity')
        search_location = value.get('location')
        from_date = value.get('date_from')
        to_date = value.get('date_to')
        search_venue = value.get('select_venue')
        type_of_venue = value.get('type_of_venue')
        booking_type = value.get('booking_type')
        single_data_list = []
        single_data_dict = {}
        if type_of_venue and type_of_venue != '':
            if amenities:
                amenities = json.loads(amenities)
                res_amenities = []
                for i in amenities:
                    i = int(i)
                    res_amenities.append(i)
                if capacity == '0' and budget != '0':
                    if booking_type == 'day':
                        venues_by_type = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_day', '<=', budget), ('venue_amenities_ids.amenities_id', 'in', res_amenities),
                             ('venue_type_id.id', '=', type_of_venue)])
                    else:
                        venues_by_type = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_hour', '<=', budget),
                             ('venue_amenities_ids.amenities_id', 'in', res_amenities),
                             ('venue_type_id.id', '=', type_of_venue)])
                elif budget == '0' and capacity != '0':
                    venues_by_type = http.request.env['venue.venue'].sudo().search(
                        [('capacity', '<=', capacity), ('venue_amenities_ids.amenities_id', 'in', res_amenities),
                         ('venue_type_id.id', '=', type_of_venue)])
                else:
                    if capacity == "0" and budget == "0":
                        if amenities:
                            venues_by_type = http.request.env['venue.venue'].sudo().search(
                                [('venue_amenities_ids.amenities_id', 'in', res_amenities),
                                 ('venue_type_id.id', '=', type_of_venue)])
                        if not amenities:
                            venues_by_type = http.request.env['venue.venue'].sudo().search(
                                [('venue_type_id.id', '=', type_of_venue)])

                    else:
                        if booking_type == 'day':
                            venues_by_type = http.request.env['venue.venue'].sudo().search(
                                [('charges_per_day', '<=', budget), ('capacity', '<=', capacity),
                                 ('venue_amenities_ids.amenities_id', 'in', res_amenities),
                                 ('venue_type_id.id', '=', type_of_venue)])
                        else:
                            venues_by_type = http.request.env['venue.venue'].sudo().search(
                                [('charges_per_hour', '<=', budget), ('capacity', '<=', capacity),
                                 ('venue_amenities_ids.amenities_id', 'in', res_amenities),
                                 ('venue_type_id.id', '=', type_of_venue)])

            if not amenities:
                if capacity == "0" and budget == "0":
                    venues_by_type = http.request.env['venue.venue'].sudo().search(
                        [('venue_type_id.id', '=', type_of_venue)])
                elif capacity == '0' and budget != '0':
                    if booking_type == 'day':
                        venues_by_type = http.request.env['venue.venue'].sudo().search([('charges_per_day', '<=', budget),
                                                                                        ('venue_type_id.id', '=',
                                                                                         type_of_venue)])
                    else:
                        venues_by_type = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_hour', '<=', budget),
                             ('venue_type_id.id', '=',type_of_venue)])
                elif budget == '0' and capacity != '0':
                    venues_by_type = http.request.env['venue.venue'].sudo().search([('capacity', '<=', capacity),
                                                                                    ('venue_type_id.id', '=',
                                                                                     type_of_venue)])
                else:
                    if booking_type == 'day':
                        venues_by_type = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_day', '<=', budget), ('capacity', '<=', capacity),
                             ('venue_type_id.id', '=', type_of_venue)])
                    else:
                        venues_by_type = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_hour', '<=', budget), ('capacity', '<=', capacity),
                             ('venue_type_id.id', '=', type_of_venue)])

            dict = {}
            result_dict = []
            for g in venues_by_type:
                img = g.image_medium
                if img:
                    res = img.decode("utf-8")
                else:
                    res = ''
                print(g.currency_id.symbol)
                dict = {
                    'id': g.id,
                    'venue': g.name or None,
                    'charge_per_day': g.charges_per_day or None,
                    'charge_per_hour': g.charges_per_hour or None,
                    'currency_id':g.currency_id.symbol,
                    'capacity': g.capacity or None,
                    'seating': g.seating or None,
                    'image': res
                }
                result_dict.append(dict)
            result_dict = json.dumps(result_dict)
            return result_dict

        if search_venue and search_venue != '-- select an option --':
            single_venue = http.request.env['venue.venue'].sudo().search([('id', '=', search_venue)])
            single_venue_image = single_venue.image_medium
            if single_venue_image:
                res = single_venue_image.decode("utf-8")
            else:
                res = ''
            single_data_dict = {
                'id': single_venue.id,
                'venue': single_venue.name or None,
                'charge_per_day': single_venue.charges_per_day or None,
                'charge_per_hour': single_venue.charges_per_hour or None,
                'currency_id': single_venue.currency_id.symbol,
                'capacity': single_venue.capacity or None,
                'seating': single_venue.seating or None,
                'image': res
            }
            single_data_list.append(single_data_dict)
            single_data_list = json.dumps(single_data_list)
            return single_data_list

        if search_location and search_location != '-- select an option --':
            rest = http.request.env['venue.venue'].sudo().search([('location_id.id', '!=', search_location)])
        if from_date:
            booking = http.request.env['booking.booking'].sudo().search(
                [
                    '|', '|',
                    '&', ('from_date', '<=', self.convert_to_datetime(from_date)), (
                    'to_date', '>=', self.convert_to_datetime(from_date)),
                    '&', ('from_date', '<=', self.convert_to_datetime(to_date)), (
                    'to_date', '>=', self.convert_to_datetime(to_date)),
                    '&', ('from_date', '>', self.convert_to_datetime(from_date)), (
                    'to_date', '<', self.convert_to_datetime(to_date)),
                ]
            )
            venue_ids = booking.mapped('venue_id')
            booked_venues = http.request.env['venue.venue'].sudo().search([('id', '=', venue_ids.id)])
        if amenities:
            amenities = json.loads(amenities)
            res_amenities = []
            for i in amenities:
                i = int(i)
                res_amenities.append(i)
            if capacity == '0' and budget != '0':
                if booking_type == 'day':
                    get_venue = http.request.env['venue.venue'].sudo().search(
                        [('charges_per_day', '<=', budget), ('venue_amenities_ids.amenities_id', 'in', res_amenities)])
                else:
                    get_venue = http.request.env['venue.venue'].sudo().search(
                        [('charges_per_hour', '<=', budget), ('venue_amenities_ids.amenities_id', 'in', res_amenities)])
            elif budget == '0' and capacity != '0':
                get_venue = http.request.env['venue.venue'].sudo().search(
                    [('capacity', '<=', capacity), ('venue_amenities_ids.amenities_id', 'in', res_amenities)])
            else:
                if capacity == "0" and budget == "0":
                    if amenities:
                        get_venue = http.request.env['venue.venue'].sudo().search(
                            [('venue_amenities_ids.amenities_id', 'in', res_amenities)])
                    if not amenities:
                        get_venue = http.request.env['venue.venue'].sudo().search([])
                else:
                    if booking_type == 'day':
                        get_venue = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_day', '<=', budget), ('capacity', '<=', capacity),
                             ('venue_amenities_ids.amenities_id', 'in', res_amenities)])
                    else:
                        get_venue = http.request.env['venue.venue'].sudo().search(
                            [('charges_per_hour', '<=', budget), ('capacity', '<=', capacity),
                             ('venue_amenities_ids.amenities_id', 'in', res_amenities)])

        if not amenities:
            if capacity == "0" and budget == "0":
                get_venue = http.request.env['venue.venue'].sudo().search([])
            elif capacity == '0' and budget != '0':
                if booking_type == 'day':
                    get_venue = http.request.env['venue.venue'].sudo().search([('charges_per_day', '<=', budget)])
                else:
                    get_venue = http.request.env['venue.venue'].sudo().search([('charges_per_hour', '<=', budget)])
            elif budget == '0' and capacity != '0':
                get_venue = http.request.env['venue.venue'].sudo().search([('capacity', '<=', capacity)])
            else:
                if booking_type == 'day':
                    get_venue = http.request.env['venue.venue'].sudo().search(
                        [('charges_per_day', '<=', budget), ('capacity', '<=', capacity)])
                else:
                    get_venue = http.request.env['venue.venue'].sudo().search(
                        [('charges_per_hour', '<=', budget), ('capacity', '<=', capacity)])
        dict = {}
        result_dict = []
        if get_venue:
            if from_date:
                get_venue = get_venue - booked_venues
                if search_location and search_location != '-- select an option --':
                    get_venue = get_venue - rest
            for g in get_venue:
                img = g.image_medium
                if img:
                    res = img.decode("utf-8")
                else:
                    res = ''
                dict = {
                    'id': g.id,
                    'venue': g.name or None,
                    'charge_per_day': g.charges_per_day or None,
                    'charge_per_hour': g.charges_per_hour or None,
                    'currency_id': g.currency_id.symbol,
                    'capacity': g.capacity or None,
                    'seating': g.seating or None,
                    'image': res
                }
                result_dict.append(dict)
            result_dict = json.dumps(result_dict)
        return result_dict

    @http.route('/options', type='http', auth="public", website=True, methods=['GET', 'POST'], csrf=False)
    def option_selected(self, **value):
        opt_dict = {}
        res_list = []
        location = value.get('location')
        if location == '-- select an option --':
            venue_options = http.request.env['venue.venue'].sudo().search([])
        else:
            venue_options = http.request.env['venue.venue'].sudo().search([('location_id.id', '=', location)])
        for venue in venue_options:
            opt_dict = {
                'id': venue.id or None,
                'name': venue.name or None,
            }
            res_list.append(opt_dict)
        res_list = json.dumps(res_list)
        return res_list

    @http.route(['/view/more'], type='http', auth="public", website=True)
    def view_more(self):
        all_amenities = []
        venue_type = request.env['venue.type'].search([])
        # take all loc
        all_locations = request.env['state.cities'].search([])
        # end
        all_venues = http.request.env['venue.venue'].sudo().search([])
        for venue in all_venues:
            for amenity in venue.venue_amenities_ids:
                if amenity.amenities_id not in all_amenities:
                    all_amenities.append(amenity.amenities_id)

        return http.request.render('tis_venue_booking.all_venues_listing', {
            'venue_type': venue_type,
            'all_venues': all_venues,
            # here also
            'all_locations': all_locations,
            'amenities': all_amenities,
        })

    @http.route(['/venue/by/type/<int:type_id>'], type='http', auth="public", website=True)
    def venues_by_type(self, type_id):
        all_amenities = []
        venue_type = request.env['venue.type'].search([])
        all_venues = http.request.env['venue.venue'].sudo().search([])
        venues_by_type = http.request.env['venue.venue'].sudo().search([('venue_type_id', '=', type_id)])
        all_locations = request.env['state.cities'].search([])

        for venue in all_venues:
            for amenity in venue.venue_amenities_ids:
                if amenity.amenities_id not in all_amenities:
                    all_amenities.append(amenity.amenities_id)

        return http.request.render('tis_venue_booking.venue_detail_page', {
            'venue_type': venue_type,
            'get_venues': venues_by_type,
            'all_venues': all_venues,
            'amenities': all_amenities,
            'all_locations': all_locations,
            'search_by_type': type_id,
            'location': '-- select an option --',
            'location_id': '-- select an option --',
            'venue_id': '-- select an option --',
            'venue': '-- select an option --'
        })

    @http.route(['/venue/<int:venue_id>'], type='http', auth="public", website=True)
    def venue_second_page(self, venue_id, **kwargs):
        venue = http.request.env['venue.venue'].sudo().browse(venue_id)
        rating = request.website.viewref('tis_venue_booking.venue_second_page_template').active
        if rating:
            rating = request.env["ir.ui.view"]._render_template(
                'portal_rating.rating_widget_stars_static', values={
                    'rating_avg': venue.rating_avg,
                    'rating_count': venue.rating_count
                })

        return http.request.render('tis_venue_booking.venue_second_page_template', {
            'venue_details': venue,
            'rating': rating
        })

    @http.route(['/venue/<int:venue_id>/booking'], type='http', auth="public", website=True)
    def venue_booking_page(self, venue_id, **kwargs):
        venue = http.request.env['venue.venue'].sudo().browse(venue_id)
        partner = request.env.user.partner_id if request.env.user != request.website.user_id else False
        return http.request.render('tis_venue_booking.venue_booking_page_template',
                                   {'venue_details': venue,
                                    'partner': partner})

    @http.route(['/tis_venue_booking/booking_submitted'], type='http', auth="public", methods=['POST'],
                website=True)
    def booking_submitted(self, **post):
        venue = http.request.env['venue.venue'].sudo().browse(int(post['venue']))
        partner = request.env.user.partner_id if request.env.user != request.website.user_id else False
        amenities_web = request.httprequest.form.getlist('amenity')
        quantity = request.httprequest.form.getlist('quantity')
        types = request.httprequest.form.getlist('type')
        note = post['narration']
        amenities_list = []
        date_frm = self.convert_to_datetime(post['booking_from'])
        date_to = self.convert_to_datetime(post['booking_to'])

        booking_days = request.env['booking.booking'].search(
            [
                ('venue_id', '=', venue.id), ('state', '=', 'confirm'),
                '|', '|',
                '&', ('from_date', '<=', date_frm), ('to_date', '>=', date_frm),
                '&', ('from_date', '<=', date_to), ('to_date', '>=', date_to),
                '&', ('from_date', '>', date_frm), ('to_date', '<', date_to), ]
        )
        if booking_days:
            return http.request.render('tis_venue_booking.venue_canceled_page_template')
        else:
            new_partner = request.env['res.partner']
            if not request.env['res.partner'].sudo().search([('id', '=', request.website.user_id.id)]):
                new_partner = request.env['res.partner'].sudo().create({'name': post['partner_id']})
            ind = 0
            for amenity in amenities_web:
                venue_amenity = http.request.env['venue.amenities'].sudo().search(
                    [('venue_id', '=', venue.id), ('amenities_id', '=', int(amenity))])
                amenities_data = {'amenities_id': venue_amenity.id,
                                  'quantity': quantity[ind],
                                  'types': types[ind],
                                  'price': venue_amenity.charge_per_hour if post.get(
                                      'booking_type') == 'hourly' else venue_amenity.charge_per_day,
                                  'taxes': venue_amenity.taxes
                                  }
                amenities_list.append((0, 0, amenities_data))
                ind += 1
            user_tz = http.request.env.user.tz or pytz.utc
            local = pytz.timezone(user_tz)

            from_time = venue.start_time
            to_time = venue.end_time

            if from_time == 0.0 and to_time == 0.0:
                now = datetime.strftime(pytz.utc.localize(
                    datetime.strptime(str(date_frm), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),
                                        "%Y-%m-%d %H:%M:%S")
                now_to_object = parser.parse(now)
                diff = now_to_object - date_frm
                hour_to_subtract = diff.seconds // 3600
                min_to_subtract = (diff.seconds // 60) % 60
                date_frm = date_frm - timedelta(hours=hour_to_subtract, minutes=min_to_subtract)
                date_to = date_to - timedelta(hours=hour_to_subtract, minutes=min_to_subtract)

            else:
                hours = int(float(from_time))
                st_seconds, st_minutes = divmod(from_time * 60, 3600)
                st_hours, st_minutes = divmod(st_minutes, 60)
                minutes = int(st_minutes)
                seconds = (minutes * 3600) % 60
                ehours = int(float(to_time))
                end_seconds, end_minutes = divmod(to_time * 60, 3600)
                end_hours, end_minutes = divmod(end_minutes, 60)
                eminutes = int(end_minutes)
                eseconds = (eminutes * 3600) % 60
                date_frm = date_frm.replace(hour=hours, minute=minutes, second=seconds)
                date_to = date_to.replace(hour=ehours, minute=minutes, second=eseconds)
                now = datetime.strftime(pytz.utc.localize(
                    datetime.strptime(str(date_frm), DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),
                                        "%Y-%m-%d %H:%M:%S")
                now_to_object = parser.parse(now)
                diff = now_to_object - date_frm
                hour_to_subtract = diff.seconds // 3600
                min_to_subtract = (diff.seconds // 60) % 60
                date_frm = date_frm - timedelta(hours=hour_to_subtract, minutes=min_to_subtract)
                date_to = date_to - timedelta(hours=hour_to_subtract, minutes=min_to_subtract)

            booking = request.env['booking.booking'].sudo().create({
                'partner_id': request.env.user.partner_id.id if request.env.user != request.website.user_id else new_partner.id,
                'venue_id': venue.id,
                'booking_type': post['booking_type'],
                'from_date': date_frm,
                'to_date': date_to,
                'mobile': post['mobile_number'],
                'partner_name': request.env.user.partner_id.name if request.env.user != request.website.user_id else new_partner.name,
                'narration': note,
                'booking_amenities_ids': amenities_list
            })
            report_data = request.env.ref('tis_venue_booking.action_report_booking_order')
            return http.request.render('tis_venue_booking.venue_confirmed_page_template',
                                       {'booking_details': booking,
                                        'report_data': report_data})
