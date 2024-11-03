# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd. - ©
# Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta


class PartnerBinding(models.TransientModel):
    _name = 'partner.binding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _mail_post_access = 'read'
    _description = 'Partner Binding'

    action = fields.Selection([
        ('exist', 'Link to an existing customer'),
        ('create', 'Create a new customer'),
    ], 'Related Customer')
    partner_id = fields.Many2one('res.partner', 'Customer')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange',
                              track_sequence=2, default=lambda self: self.env.user)
    if_customer = fields.Boolean(string=' If Customer', default=False)

    @api.model
    def default_get(self, fields):
        res = super(PartnerBinding, self).default_get(fields)
        booking = self.env['booking.booking'].browse(self._context.get('active_ids', []))
        if 'action' in fields and not res.get('action'):
            res['action'] = 'exist' if booking.partner_id else 'create'
        if 'partner_id' in fields:
            res['partner_id'] = booking.partner_id.id
        if booking.partner_id:
            res['if_customer'] = True
        else:
            res['if_customer'] = False
        return res

    def action_apply(self):
        bookings = self.env['booking.booking'].browse(self._context.get('active_ids', []))
        today = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        if self.action == 'exist':
            for values in bookings:
                values['partner_id'] = self.partner_id
                values['partner_name'] = self.partner_id.name
                values['email_from'] = bookings.email_from if bookings.email_from else self.partner_id.email
                values['street'] = bookings.street if bookings.street else self.partner_id.street
                values['street2'] = bookings.street2 if bookings.street2 else self.partner_id.street2
                values['city'] = bookings.city if bookings.city else self.partner_id.city
                values['zip'] = bookings.zip if bookings.zip else self.partner_id.zip
                values['state_id'] = bookings.state_id if bookings.state_id else self.partner_id.state_id
                values['country_id'] = bookings.country_id if bookings.country_id else self.partner_id.country_id
                values['phone'] = bookings.phone if bookings.phone else self.partner_id.phone
                values['mobile'] = bookings.mobile if bookings.mobile else self.partner_id.mobile
                values['website'] = bookings.website if bookings.website else self.partner_id.website
                values['state'] = 'confirm'
            bookings.confirmation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return
        elif self.action == 'create':
            if bookings.partner_name:
                partner = self.env['res.partner'].create({
                    'name': bookings.partner_name,
                    'phone': bookings.phone,
                    'mobile': bookings.mobile,
                    'street': bookings.street,
                    'street2': bookings.street2,
                    'zip': bookings.zip,
                    'city': bookings.city,
                    'country_id': bookings.country_id.id,
                    'state_id': bookings.state_id.id,
                    'website': bookings.website,
                    'email': bookings.email_from,
                    'is_company': 'is_company',
                    'type': 'contact'
                })
                bookings.partner_id = partner.id
                bookings.state = 'confirm'
                bookings.confirmation_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            else:
                raise UserError(_('Please Add Customer Details in Customer Info Page.'))