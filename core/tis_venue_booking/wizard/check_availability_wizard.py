# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import fields, models, api, _
from datetime import datetime, timedelta
from odoo.osv import expression
from odoo.exceptions import UserError

#model for info messages
class MessageWizard(models.TransientModel):
    _name = 'message.wizard'

    message = fields.Text('Message', required=True)

    def action_ok(self):
        """ close wizard"""
        return {'type': 'ir.actions.act_window_close'}


class CheckAvailabilityWizard(models.TransientModel):
    _name = 'check.availability.wizard'
    _description = 'Check availability wizard'

    location_id = fields.Many2one('state.cities', string='Location')
    booking_type = fields.Selection(selection=[('day', 'Day'),
                                               ('hourly', 'Hour')], string='Booking Type', default="day")
    search_by = fields.Selection(selection=[('venue', 'Venue'),
                                            ('others', 'Others')], string='Search By', default="venue")
    from_date = fields.Datetime(string="Date From", index=True)
    to_date = fields.Datetime(string="Date To", index=True)
    venue_id = fields.Many2one('venue.venue', string='Venue')
    amenities = fields.Many2many('amenities.amenities', string='Amenities')
    services = fields.Many2many('venue.services', string='Services')
    budget = fields.Float(string='Budget')
    capacity = fields.Float(string='Capacity')
    _sql_constraints = [
        ('date_check2', "CHECK ((from_date < to_date))", "The start date must be anterior to the end date.")

    ]

    def search_action(self):
        if not self.location_id and not self.venue_id and not self.from_date and not self.to_date and not self.budget and not self.capacity and not self.amenities and not self.services:
            raise UserError(_('Please enter any value .'))
        if self.search_by == 'venue':
            if not self.venue_id:
                raise UserError(_('Please Select a venue'))
            if self.venue_id:
                if self.from_date and self.to_date:
                    bookings = self.env['booking.booking'].search([
                        ('venue_id', '=', self.venue_id.id),('state','=','confirm'),
                        '|', '|',
                        '&', ('from_date', '<=', self.from_date), ('to_date', '>=', self.from_date),
                        '&', ('from_date', '<=', self.to_date), ('to_date', '>=', self.to_date),
                        '&', ('from_date', '>', self.from_date), ('to_date', '<', self.to_date), ]
                    )
                    if bookings:
                        domain = [('id','in', bookings.ids)]
                        raise UserError(_('Venue is not available for selected period .'))
                        # return {
                        #     'name': self.venue_id.name,
                        #     'view_type': 'form',
                        #     'view_mode': 'calendar',
                        #     'view_id': self.env.ref('tis_venue_booking.booking_calendar_view').id,
                        #     'res_model': 'booking.booking',
                        #     'type': 'ir.actions.act_window',
                        #     'res_id': self.venue_id,
                        #     'domain': domain,
                        #     'target': '_new',
                        #     'context': {
                        #         'search_default_venue_id': [self.venue_id.id]
                        #     }
                        # }
                    else:
                        return {
                            'name': self.venue_id.name,
                            'view_type': 'form',
                            'view_mode': 'calendar',
                            'view_id': self.env.ref('tis_venue_booking.booking_calendar_view').id,
                            'res_model': 'booking.booking',
                            'type': 'ir.actions.act_window',
                            'res_id': self.venue_id,
                            'target': '_new',
                            'context': {
                                'search_default_venue_id': [self.venue_id.id]
                            }
                        }
                        # raise UserError(_('Venue is available for selected period .'))

                if not self.from_date and not self.to_date:
                    return {
                        'name': self.venue_id.name,
                        'view_type': 'form',
                        'view_mode': 'calendar',
                        'view_id': self.env.ref('tis_venue_booking.booking_calendar_view').id,
                        'res_model': 'booking.booking',
                        'type': 'ir.actions.act_window',
                        'res_id': self.venue_id,
                        'target': '_new',
                        'context': {
                            'search_default_venue_id': [self.venue_id.id]
                        }
                    }
        elif self.search_by == 'others':
            venue_domain = []
            available_venues = ''
            if self.budget:
                if self.booking_type == 'day':
                    venue_domain.append(('charges_per_day', '<=', self.budget))
                elif self.booking_type == 'hour':
                    venue_domain.append(('charges_per_hour', '<=', self.budget))
            if self.capacity:
                venue_domain.append(('capacity', '<=', self.capacity))
            if self.location_id:
                venue_domain.append(('location_id', '=', self.location_id.id))
            if self.amenities:
                venue_amenities = []
                for amenity in self.amenities:
                    for rec in self.env['venue.amenities'].search([('amenities_id', '=', amenity.id)]):
                        if rec.id not in venue_amenities:
                            venue_amenities.append(rec.id)
                venue_domain.append(('venue_amenities_ids', 'in', venue_amenities))
            if self.services:
                venue_services = []
                for service in self.services:
                    for rec in self.env['venue.services'].search([('id', '=', service.id)]):
                        if rec.id not in venue_services:
                            venue_services.append(rec.id)
                venue_domain.append(('services_ids', 'in', venue_services))
            venues = self.env['venue.venue'].search(venue_domain)
            if venues:
                if self.from_date and self.to_date:
                    for venue in venues:
                        bookings = self.env['booking.booking'].search([('venue_id', '=', self.venue_id.id),
                                                                       ('state', '=', 'confirm'),
                                                                       '|', '|',
                                                                       '&', ('from_date', '<=', self.from_date),
                                                                       ('to_date', '>=', self.from_date),
                                                                       '&', ('from_date', '<=', self.to_date),
                                                                       ('to_date', '>=', self.to_date),
                                                                       '&', ('from_date', '>', self.from_date),
                                                                       ('to_date', '<', self.to_date), ])
                        if not bookings:
                            available_venues = available_venues + ',' + venue.name
                    if available_venues:
                        message_id = self.env['message.wizard'].create(
                            {'message': _('Venues %s  are  available on these dates') % available_venues[1:]})
                        return {
                            'name': _('Available Venues'),
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'message.wizard',
                            # pass the id
                            'res_id': message_id.id,
                            'target': 'new'
                        }
                        # raise UserError(
                        #     _('Venues %s  are  available on these dates') % available_venues[1:])
                    else:
                        raise UserError(
                            _('Venues  are not  available on these dates'))
                else:
                    return {
                        'name': _('Booking'),
                        'view_type': 'form',
                        'view_mode': 'calendar',
                        'view_id': self.env.ref('tis_venue_booking.booking_calendar_view').id,
                        'res_model': 'booking.booking',
                        'type': 'ir.actions.act_window',
                        'target': '_new',
                        'domain': [('venue_id', 'in', venues.ids)]
                    }
            else:
                raise UserError('No venues are available.')


