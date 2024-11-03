# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from dateutil.relativedelta import relativedelta
import pytz
from babel.dates import format_datetime, format_date
from datetime import date, datetime
from werkzeug.urls import url_encode

from odoo import http, _, fields
from odoo.http import request
from odoo.tools import html2plaintext, DEFAULT_SERVER_DATETIME_FORMAT as dtf
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.tools.misc import get_lang


class WebsiteCalendar(http.Controller): 
    
    @http.route([
        '/appointment/select',
    ], type='http', auth="public", website=True)
    def appointment_country_choice(self, message=None, **kwargs):
        appoint_group = request.env['appointment.group'].sudo().search([])
        
        value={
            'country_id':appoint_group.country_id,
            'state_id':appoint_group.state_id
        }    
        return request.render("website_booking_axis.appointment_country", value)

    @http.route([
        '/appointment',
    ], type='http', auth="public", website=True)
    def appointment_group_choice(self, appointment_type=None, employee_id=None, message=None, **post):
        appoint_group = request.env['appointment.group'].sudo().search([('country_id.id','=', post.get('id'))])
        value={
            'appoint_group':appoint_group
        }    
        return request.render("website_booking_axis.appointment_1", value)

    @http.route(['/website/appointment'], type='http', method=["POST"], auth="public", website=True)
    def appointees_info(self, prev_emp=False, **post):
        country_id = post.get('country_id')
        if 'id' in post:
            appoint_group_ids = request.env['appointment.group'].sudo().search([('product_template_id.id','=', post.get('id'))])
        value={
            'appoint_group_ids':appoint_group_ids,
            'country':country_id,
        }
        return request.render("website_booking_axis.appointees_availability",value)

    @http.route(['/website/appointment/slot'], type='http', auth="public", website=True)
    def appointment_slots(self,appointment_type=None,timezone=None, prev_emp=False, **post):
        country_id = post.get('country_id')
        appointment_timeslots = request.env['res.partner'].sudo().search([('id','=', post.get('id'))])   
        appointment_type = request.env['calendar.appointment.type'].sudo().search([('partner_id.id','=',post.get('id'))])
        if appointment_type:
            request.session['timezone'] = timezone or appointment_type.appointment_tz
            Slots = appointment_type.sudo()._get_appointment_slots(request.session['timezone'], appointment_type)
            value={
                'appointment_type':appointment_type,
                'slots':Slots,
                'country_id':country_id,

            }
            return request.render("website_booking_axis.slot", value)
        else:
            return request.render("website_booking_axis.slot_available")

    @http.route(['/website/appointment/form/<model("calendar.appointment.type"):appointment_type>/info'], type='http', auth="public", website=True)
    def appointment_form(self,appointment_type,**post):
        country_id = post.get("country")
        partner_data = {}
        if request.env.user.partner_id != request.env.ref('base.public_partner'):
            partner_data = request.env.user.partner_id.read(fields=['name', 'mobile', 'country_id', 'email'])[0]
        date_time = post.get('date_time')
        day_name = format_datetime(datetime.strptime(date_time, dtf), 'EEE', locale=get_lang(request.env).code)
        date_formated = format_datetime(datetime.strptime(date_time, dtf), locale=get_lang(request.env).code)
        country_get = request.env['appointment.group'].sudo().search([])
        return request.render("website_booking_axis.appointment_form", {
            'partner_data': partner_data,
            'appointment_type': appointment_type,
            'datetime': date_time,
            'datetime_locale': day_name + ' ' + date_formated,
            'datetime_str': date_time,
            'country': country_id,
        })                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                

    @http.route(['/website/calendar/<model("calendar.appointment.type"):appointment_type>/submit'], type='http', auth="public", website=True, method=["POST"])
    def calendar_appointment_submit(self, appointment_type, name, phone, email, country_id=False, **kwargs):
        datetime_str = kwargs.get('date_time')
        timezone = request.session['timezone']
        tz_session = pytz.timezone(timezone)
        date_start_backend = tz_session.localize(fields.Datetime.from_string(datetime_str)).astimezone(pytz.utc)
        date_start = datetime.strptime(datetime_str, dtf)
        date_end = date_start + relativedelta(hours=appointment_type.appointment_duration)
        date_end_backend = date_start_backend + relativedelta(hours=appointment_type.appointment_duration)
        country_id = int(country_id) if country_id else None
        country_name = country_id and request.env['res.country'].browse(country_id).name or ''
        Partner = request.env['res.partner'].sudo().search([('email', '=like', email)], limit=1)
        if Partner:
            if not Partner.mobile or len(Partner.mobile) <= 5 and len(phone) > 5:
                Partner.write({'mobile': phone})
            if not Partner.country_id:
                Partner.country_id = country_id
            Partner.start_datetime = date_start_backend.strftime(dtf)
        else:
            Partner = request.env['res.partner'].sudo().create({
                'name': name,
                'country_id': country_id,
                'mobile': phone,
                'email': email,
                'start_datetime':date_start_backend.strftime(dtf),
            })
            abcd = Partner.name
        description = ('Country: %s\n'
                       'Mobile: %s\n'
                       'Email: %s\n' % (country_name, phone, email))
        for question in appointment_type.question_ids:
            key = 'question_' + str(question.id)
            if question.question_type == 'checkbox':
                answers = question.answer_ids.filtered(lambda x: (key + '_answer_' + str(x.id)) in kwargs)
                description += question.name + ': ' + ', '.join(answers.mapped('name')) + '\n'
            elif kwargs.get(key):
                if question.question_type == 'text':
                    description += '\n* ' + question.name + ' *\n' + kwargs.get(key, False) + '\n\n'
                else:
                    description += question.name + ': ' + kwargs.get(key) + '\n'

        categ_id = request.env.ref('website_booking_axis.calendar_event_type_data_online_appointment')
        alarm_ids = appointment_type.reminder_ids and [(6, 0, appointment_type.reminder_ids.ids)] or [] 
        start_time = str(date_start.time())
        end_time = str(date_end.time())
        event = request.env['calendar.event'].sudo().create({
            'name': appointment_type.name,
            'start': date_start_backend.strftime(dtf),
            'start_at':date_start_backend.date(),
            'stop': date_end_backend.strftime(dtf),
            'description': description,
            'partner_new': Partner.id,
            'appointment_type_id': appointment_type.id,
            'start_time':start_time,
            'end_time':end_time,
        })
        value = {
            'event': event,
            'start_time':start_time,
            "start": date_start.strftime(dtf),
            'end_time':end_time,
        }
        return request.render('website_booking_axis.appointment_confirm',value)

class CustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super(CustomerPortal, self)._prepare_portal_layout_values()
        values['appointment_count'] = request.env['calendar.event'].search_count([])
        if values.get('sales_user', False):
            values['title'] = _("Salesperson")
        return values

    def _ticket_get_page_view_values(self, appointments, access_token, **kwargs):
        values = {
            'page_name': 'appointments',
            'appointments': appointments,
        }
        return self._get_page_view_values(appointments, access_token, values, False, **kwargs)

    @http.route(['/my/appointments'], type='http', auth="user", website=True)
    def my_appointments(self, page=1, date_begin=None, date_end=None, sortby=None, search=None, search_in='content', **kw):
        values = self._prepare_portal_layout_values()
        user = request.session.uid
        domain = []

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Subject'), 'order': 'name'},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': _('Search <span class="nolabel"> (in Content)</span>')},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'id': {'input': 'id', 'label': _('Search ID')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search)]])
            domain += search_domain

        appointments = request.env['calendar.event'].search(domain)
        values.update({
            'appointments': appointments,
            })

        return request.render("website_booking_axis.portal_appointment_layout",values)

    @http.route([
        '/my/appointment/<model("calendar.event"):appointment>'
    ], type='http', auth="public", website=True)
    def appointments_followup(self, appointment, **kw):
        values = self._prepare_portal_layout_values()
        date_end = appointment.start + relativedelta(hours=appointment.duration)
        start_time = appointment.start.time()
        end_time = date_end.time()
        appointment_description = request.env['res.partner'].search([('name','=',appointment.name)])
        values.update({
            'appointment': appointment,
            'start_time': start_time,
            'end_time': end_time,
            'appointment_description':appointment_description.appointment_group_ids.product_template_id.description
            })
        return request.render("website_booking_axis.appointments_followup",values)        