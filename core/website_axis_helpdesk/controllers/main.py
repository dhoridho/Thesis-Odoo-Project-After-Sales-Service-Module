# -*- coding: utf-8 -*-

from odoo import http
from odoo.http import request
import odoo
import base64
import io
from werkzeug.utils import redirect

from datetime import datetime,date,timedelta
import calendar
import dateutil.relativedelta


class WebsiteManageHelpdesk(http.Controller):

    @http.route('/getData', type='json', auth='public', website=True)
    def getData(self, **kwargs):
        teamlead_id = 0
        team_id = 0
        assignUser_id = 0
        domain = []
        if kwargs.get('teamLead_id'):
            teamlead_id = int(kwargs.get('teamLead_id'))
            domain.append(('user_id', '=', teamlead_id))
        if kwargs.get('team_id'):
            team_id = int(kwargs.get('team_id'))
            domain.append(('team_id', '=', team_id))
        if kwargs.get('assignUser_id'):
            assignUser_id = int(kwargs.get('assignUser_id'))
            domain.append(('user_id', '=', assignUser_id))

        if kwargs.get('custome_date_id'):
            custome_date_id = kwargs.get('custome_date_id')
            if custome_date_id:
                date_str = custome_date_id
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                today = date.today()
                start_date = date_obj
                end_date = datetime(today.year, today.month, today.day, 23, 59, 59)
                domain.append(('create_date', '>=', start_date))
                domain.append(('create_date', '<=', end_date))

        if kwargs.get('date_id'):
            date_id = int(kwargs.get('date_id'))
            if date_id == 1:
                today = date.today()
                start_date = datetime(today.year, today.month, today.day)
                end_date = datetime(today.year, today.month, today.day, 23, 59, 59)
                domain.append(('create_date', '>=', start_date))
                domain.append(('create_date', '<=', end_date))
            if date_id == 2:
                today = date.today()
                yesterday = today - timedelta(days=1)
                start_date = datetime(yesterday.year, yesterday.month, yesterday.day)
                end_date = datetime(yesterday.year, yesterday.month, yesterday.day, 23, 59, 59)
                domain.append(('create_date', '>=', start_date))
                domain.append(('create_date', '<=', end_date))
            if date_id == 3:
                # date_str = '2021-07-06'
                # date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_obj = datetime.today()
                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday
                end_of_week = start_of_week + timedelta(days=6)  # Sunday
                domain.append(('create_date', '>=', start_of_week))
                domain.append(('create_date', '<=', end_of_week))

            # This is not calculated currectly  for other date filter...
            if date_id == 4:
                # date_str = '2021-10-12'
                # date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_obj = datetime.today()

                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                start_of_week = date_obj + timedelta(days=-date_obj.weekday(), weeks=-1)  # Monday
                end_of_week = date_obj + timedelta(-date_obj.weekday() - 1)  # Sunday

                domain.append(('create_date', '>=', start_of_week))
                domain.append(('create_date', '<=', end_of_week))
            if date_id == 5:
                # date_str = '2021-06-06'
                # date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_obj = datetime.today()

                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                # start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday
                # end_of_week = start_of_week + timedelta(days=6)  # Sunday
                start_of_month = date_obj.replace(day=1)
                end_of_month = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])
                domain.append(('create_date', '>=', start_of_month))
                domain.append(('create_date', '<=', end_of_month))

            if date_id == 6:
                # date_str = '2021-08-06'
                # date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_obj = datetime.today()

                date_obj = date_obj + dateutil.relativedelta.relativedelta(months=-1)

                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                start_of_month = date_obj.replace(day=1)
                end_of_month = date_obj.replace(day=calendar.monthrange(date_obj.year, date_obj.month)[1])
                domain.append(('create_date', '>=', start_of_month))
                domain.append(('create_date', '<=', end_of_month))

            if date_id == 7:
                # date_str = '2021-07-06'
                # date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_obj = datetime.today()

                x =('%s-01-01'% (date_obj.year))
                y =('%s-12-31'% (date_obj.year))
                start_of_year = datetime.strptime(x,  '%Y-%m-%d')
                end_of_year = datetime.strptime(y,  '%Y-%m-%d')
                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                # start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday
                # end_of_week = start_of_week + timedelta(days=6)  # Sunday
                domain.append(('create_date', '>=', start_of_year))
                domain.append(('create_date', '<=', end_of_year))

            if date_id == 8:
                # date_str = '2021-07-06'
                # date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                date_obj = datetime.today()

                x = ('%s-01-01' % (date_obj.year -1))
                y = ('%s-12-31' % (date_obj.year -1))
                start_of_year = datetime.strptime(x, '%Y-%m-%d')
                end_of_year = datetime.strptime(y, '%Y-%m-%d')
                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                # start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday
                # end_of_week = start_of_week + timedelta(days=6)  # Sunday
                domain.append(('create_date', '>=', start_of_year))
                domain.append(('create_date', '<=', end_of_year))

            if date_id == 9:
                date_str = '2021-07-06'
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')

                # last_day = calendar.monthrange(datetime.date.today().year, datetime.date.today().month)[1]
                # month_starting = datetime.date.today().replace(day=1)
                # month_ending = datetime.date.today().replace(day=last_day)

                start_of_week = date_obj - timedelta(days=date_obj.weekday())  # Monday
                end_of_week = start_of_week + timedelta(days=6)  # Sunday

        team_data = request.env['helpdesk.ticket'].sudo().search(domain)

        teamdata_new = {}
        teamdata_inprogress = {}
        teamdata_solved = {}
        teamdata_cancelled = {}
        teamdata_others = {}
        for data in team_data:
            dict = {}
            if data.stage_id.name == 'New':
                dict['number'] = data.number
                dict['customer'] = data.partner_id.name
                dict['create_date'] = data.create_date
                dict['write_date'] = data.write_date
                dict['assign_user'] = data.user_id.name
                dict['stage'] = data.stage_id.name
                teamdata_new[data.id] = dict
            if data.stage_id.name == 'In Progress':
                dict['number'] = data.number
                dict['customer'] = data.partner_id.name
                dict['create_date'] = data.create_date
                dict['write_date'] = data.write_date
                dict['assign_user'] = data.user_id.name
                dict['stage'] = data.stage_id.name
                teamdata_inprogress[data.id] = dict
            if data.stage_id.name == 'Solved':
                dict['number'] = data.number
                dict['customer'] = data.partner_id.name
                dict['create_date'] = data.create_date
                dict['write_date'] = data.write_date
                dict['assign_user'] = data.user_id.name
                dict['stage'] = data.stage_id.name
                teamdata_solved[data.id] = dict
            if data.stage_id.name == 'Cancelled':
                dict['number'] = data.number
                dict['customer'] = data.partner_id.name
                dict['create_date'] = data.create_date
                dict['write_date'] = data.write_date
                dict['assign_user'] = data.user_id.name
                dict['stage'] = data.stage_id.name
                teamdata_cancelled[data.id] = dict
            if data.stage_id.name not in ['New','In Progress','Solved','Cancelled']:
                dict['number'] = data.number
                dict['customer'] = data.partner_id.name
                dict['create_date'] = data.create_date
                dict['write_date'] = data.write_date
                dict['assign_user'] = data.user_id.name
                dict['stage'] = data.stage_id.name
                teamdata_others[data.id] = dict
        len_teamdata_new = len(teamdata_new)
        len_teamdata_inprogress = len(teamdata_inprogress)
        len_teamdata_solved = len(teamdata_solved)
        len_teamdata_cancelled = len(teamdata_cancelled)
        len_teamdata_others = len(teamdata_others)
        result = {
            'teamdata_new': teamdata_new,
            'teamdata_inprogress': teamdata_inprogress,
            'teamdata_solved': teamdata_solved,
            'teamdata_cancelled': teamdata_cancelled,
            'teamdata_others': teamdata_others,
            'len_teamdata_new': len_teamdata_new,
            'len_teamdata_inprogress': len_teamdata_inprogress,
            'len_teamdata_solved': len_teamdata_solved,
            'len_teamdata_cancelled': len_teamdata_cancelled,
            'len_teamdata_others': len_teamdata_others,
        }
        return result

    @http.route('/search_helpdesk_tickets', type='http', auth='user', website=True)
    def search_create_helpdesk_tickets_details(self , **kwargs):
        helpdesk_tickets = request.env['helpdesk.ticket'].sudo().search([])
        return  request.render('website_axis_helpdesk.search_helpdesk_ticket_page', {'ticket': helpdesk_tickets})

    @http.route(['/helpdesk/search/ticket'], type='http', methods=['POST'],auth='user', website=True, csrf=False)
    def helpdesk_search_ticket(self , **kwargs):
        ticket_id = request.env['helpdesk.ticket'].search([('number','=', kwargs.get('search'))])
        if ticket_id:
            return request.redirect('/helpdesk/ticket/%s' % (ticket_id.id))
        else:
            return request.render('website_axis_helpdesk.helpdesk_error_message', {'error_message': ticket_id})



    @http.route(['/helpdesk/form'], type='http', auth="user", website=True)
    def helpdesk_form(self, **post):
        helpdesk_tickets = request.env['helpdesk.ticket'].sudo().search([])
        helpdesk_tickets_type = request.env['helpdesk.ticket.type'].sudo().search([])
        res_config_param = request.env['res.config.settings'].sudo().search([])
        if res_config_param:
            res_config = request.env['res.config.settings'].sudo().search([])[-1]
        else:
            res_config = res_config_param

        partner_name = ""
        partner_email =""
        select = request.env['res.users'].search([('id','=', 2)])
        if not select:
            partner_name = http.request.env.user.name
            partner_email = http.request.env.user.email
        return request.render("website_axis_helpdesk.tmp_helpdesk_ticket_form",
                              {'my_tickets': helpdesk_tickets,
                               'ticket_types': helpdesk_tickets_type,
                               'partner_name':partner_name,
                               'partner_email':partner_email,
                               'is_attachment': res_config.is_attachment})


    @http.route(['/helpdesk/form/submit'], type='http', auth="user", website=True)
    def helpdesk_form_submit(self, **post):

        # attached_files = request.httprequest.files.getlist('attachment')
        # print("Multiple Attchment attached_files:..:", attached_files)

        ticket = request.env['helpdesk.ticket'].sudo().create({
            'ticket_type_id': post.get('ticket_type_id'),
            'name': post.get('name'),
            'partner_name': post.get('partner_name'),
            'partner_email': post.get('partner_email'),
            'priority': post.get('priority'),
            'description': post.get('description'),
        })
        if post.get('attachment'):
            file = post.get('attachment')
            name = post.get('attachment').filename


            attachment_id = request.env['ir.attachment'].sudo().create({
                'name': name,
                'res_name': name,
                'type': 'binary',
                'datas': base64.b64encode(file.read()),
                'res_model': 'helpdesk.ticket',
                'res_id': ticket.id
            })

            ticket.sudo().write({'attachment_ids': [(6, 0, attachment_id.ids)]})

        vals = {
            'ticket': ticket,
        }
        return request.render("website_axis_helpdesk.tmp_helpdesk_ticket_form_success", vals)

    @http.route(['/ticket/attachment/download/<int:attachment_id>'], type='http', auth="user", website=True)
    def download_attcahment_tickets(self, attachment_id=None, **post):
        attachment = request.env['ir.attachment'].sudo().search_read(
            [('id', '=', int(attachment_id))],
            ["name", "datas", "type", "res_model", "res_id", "type", "url"]
        )
        if attachment:
            attachment = attachment[0]
        else:
            return redirect('//ticket/attachment/download/%s'%attachment_id)

        if attachment["type"] == "url":
            if attachment["url"]:
                return redirect(attachment["url"])
            else:
                return request.not_found()
        elif attachment["datas"]:
            data = io.BytesIO(base64.standard_b64decode(attachment["datas"]))
            return http.send_file(data, filename=attachment['name'], as_attachment=True)
        else:
            return request.not_found()

    @http.route(['/portal/get_id'], type='json', auth="user", website=True, csrf=False)
    def get_ticket_id(self, **post):
        base_value = request.params['id']
        send_data = request.env['helpdesk.ticket'].sudo().search([('id','=',base_value )])
        if request.env.is_admin():
            send_data.is_customer_replied = False
        else:
            send_data.is_customer_replied = True

       
