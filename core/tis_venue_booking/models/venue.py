# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class VenueType(models.Model):
    _name = "venue.type"
    _description = 'Types of Venues'

    name = fields.Char(string="Name", required=True)
    image = fields.Binary(string='Image')


class StateCities(models.Model):
    _description = "State cities"
    _name = 'state.cities'
    _order = 'code'

    state_id = fields.Many2one('res.country.state', string='State', required=True)
    name = fields.Char(string='City Name', required=True)
    code = fields.Char(string='City Code', help='The city code.', required=True)

    _sql_constraints = [
        ('name_code_uniq', 'unique(state_id, code)', 'The code of the city must be unique by state !')
    ]

    def name_get(self):
        result = []
        for record in self:
            result.append(
                (record.id, "{}, {}, {} ".format(record.name, record.state_id.name, record.state_id.country_id.name)))
        return result


class CountryState(models.Model):
    _inherit = 'res.country.state'

    cities_ids = fields.One2many('state.cities', 'state_id', string='Cities')


class AmenitiesAmenities(models.Model):
    _name = "amenities.amenities"
    _description = 'Venue Amenities'

    name = fields.Char(string="Name", required=True)


class VenueVenue(models.Model):
    _name = 'venue.venue'
    _inherit = ['portal.mixin', 'mail.thread.cc', 'mail.activity.mixin', 'website.seo.metadata', 'website.published.multi.mixin', 'rating.mixin']
    _description = 'To show venue details and images'
    _order = "sequence,id"

    sequence = fields.Integer('sequence', help="Sequence for the handle.", default=10)
    name = fields.Char(string="Name", required=True)
    gallery_ids = fields.One2many('venue.gallery', 'venue_id', string='Gallery')
    services_ids = fields.Many2many('venue.services', 'service_name', string='Services')
    seating = fields.Integer(string="Seating")
    capacity = fields.Integer(string="Capacity")
    image_medium = fields.Binary("Venue image", attachment=True)
    latitude = fields.Float(string='Geo Latitude', digits=(16, 5))
    longitude = fields.Float(string='Geo Longitude', digits=(16, 5))
    charges_per_day = fields.Float(string="Charges Per Day")
    charges_per_hour = fields.Float(string="Charges Per Hour")
    taxes = fields.Many2many('account.tax', string='Taxes')
    additional_charges_per_day = fields.Float(string="Additional Charges Per Day",help="Mandatory additional charges will be applicable for this venue such as for any services.")
    additional_charges_per_hour = fields.Float(string="Additional Charges Per Hour",help="Mandatory additional charges will be applicable for this venue such as for any services.")
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('venue.venue'), index=1)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    venue_amenities_ids = fields.One2many('venue.amenities', 'venue_id', string="Amenities", copy=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account", copy=False,
                                          ondelete='set null',
                                          )
    allow_analytic = fields.Boolean(string='Allow Analytic', default=True)
    street = fields.Char(string='Street')
    street2 = fields.Char(string='Street2')
    zip = fields.Char(string='Zip', change_default=True)
    location_id = fields.Many2one('state.cities', string='Location', required=True)
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')
    email_from = fields.Char(string='Email')
    website = fields.Char(string='Website')
    venue_type_id = fields.Many2many('venue.type', string="Venue Type")
    start_time = fields.Float(string="Start Time")
    end_time = fields.Float(string="End Time")
    #about section
    about_venue = fields.Text(string="About")



    @api.onchange('analytic_account_id')
    def _onchange_analytic_account(self):
        if not self.analytic_account_id and self._origin:
            self.allow_analytic = False

    @api.model
    def _init_data_analytic_account(self):
        self.search([('analytic_account_id', '=', False), ('allow_analytic', '=', True)])._create_analytic_account()

    def _create_analytic_account(self):
        for venue in self:
            analytic_account = self.env['account.analytic.account'].create({
                'name': venue.name,
                'company_id': venue.company_id.id,
                'active': True,
            })
            venue.write({'analytic_account_id': analytic_account.id})

    @api.model
    def name_create(self, name):
        """ Create a venue with name_create should generate analytic account creation """
        values = {
            'name': name,
            'allow_analytic': True,
        }
        return self.create(values).name_get()[0]

    @api.model
    def create(self, values):
        venue_id = self.env['ir.config_parameter'].sudo().get_param('tis_venue_booking.venue_product_id')
        additional_charge_id = self.env['ir.config_parameter'].sudo().get_param(
            'tis_venue_booking.additional_charge_product_id')
        amenities_id = self.env['ir.config_parameter'].sudo().get_param(
            'tis_venue_booking.amenities_product_id')
        if not venue_id or not additional_charge_id or not amenities_id:
            raise UserError(
                _('Please Configure Venue Product, Additional Charge Product and Amenities Product in Configuration.'))
        allow_analytic = values['allow_analytic'] if 'allow_analytic' in values else \
            self.default_get(['allow_analytic'])['allow_analytic']
        if allow_analytic and not values.get('analytic_account_id'):
            analytic_account = self.env['account.analytic.account'].create({
                'name': values.get('name', _('Unknown Analytic Account')),
                'company_id': values.get('company_id', self.env.user.company_id.id),
                'active': True,
            })
            values['analytic_account_id'] = analytic_account.id
        return super(VenueVenue, self).create(values)

    def write(self, values):
        if values.get('allow_analytic'):
            for venue in self:
                if not venue.analytic_account_id and not values.get('analytic_account_id'):
                    venue._create_analytic_account()
        return super(VenueVenue, self).write(values)

    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id

    def view_location_map(self):
        for venue in self:
            url = "http://maps.google.com/maps?q=" + str(venue.latitude) + ',' + str(venue.longitude)
            return {
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': url
            }


class VenueAmenities(models.Model):
    _name = 'venue.amenities'
    _description = 'To show venue amenities and its rates'
    _rec_name = 'amenities_id'

    amenities_id = fields.Many2one("amenities.amenities", string='Name')
    charge_per_day = fields.Float(string="Charge Per Day")
    charge_per_hour = fields.Float(string="Charge Per Hour")
    taxes = fields.Many2many('account.tax', string='Taxes')
    venue_id = fields.Many2one('venue.venue')
    type = fields.Selection([
        ('inclusive', 'Inclusive'),
        ('additional', 'Additional')], string="Type", required=True)
    company_id = fields.Many2one(
        'res.company', 'Company',
        default=lambda self: self.env['res.company']._company_default_get('venue.amenities'), index=1)
    currency_id = fields.Many2one(
        'res.currency', 'Currency', compute='_compute_currency_id')
    booking_amenity_id = fields.Many2one("booking.amenities")

    def _compute_currency_id(self):
        main_company = self.env['res.company']._get_main_company()
        for template in self:
            template.currency_id = template.company_id.sudo().currency_id.id or main_company.currency_id.id


class VenueGallery(models.Model):
    _name = 'venue.gallery'
    _description = 'To display venues images'

    image = fields.Binary(string="Image", required=True)
    venue_id = fields.Many2one('venue.venue')
    image_type = fields.Selection([
        ('interior', 'Interior'),
        ('exterior', 'Exterior'),
        ('front_view', 'Front View'),
        ('top_view', 'Top View'),
        ('other', 'Other')], string="Type", required=True)

class VenueServices(models.Model):
    _name = 'venue.services'
    _description = 'To mention services provided at the venue'
    _rec_name = 'service_name'

    service_name = fields.Char(string="Name")
    venue_id = fields.Many2one('venue.venue')

