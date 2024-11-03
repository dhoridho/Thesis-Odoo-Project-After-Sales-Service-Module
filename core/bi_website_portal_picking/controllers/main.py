# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.http import request
from werkzeug.exceptions import Forbidden, NotFound
import base64
from odoo.tools import consteq, plaintext2html
from odoo.addons.website.controllers.main import QueryURL
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools import groupby as groupbyelem
from operator import itemgetter

def _has_token_access(res_model, res_id, token=''):
    record = request.env[res_model].browse(res_id).sudo()
    token_field = request.env[res_model]._mail_post_token_field
    return (token and record and consteq(record[token_field], token))

def _message_post_helper(res_model='', res_id=None, message='', token='', nosubscribe=True, **kw):
    """ Generic chatter function, allowing to write on *any* object that inherits mail.thread.
        If a token is specified, all logged in users will be able to write a message regardless
        of access rights; if the user is the public user, the message will be posted under the name
        of the partner_id of the object (or the public user if there is no partner_id on the object).

        :param string res_model: model name of the object
        :param int res_id: id of the object
        :param string message: content of the message

        optional keywords arguments:
        :param string token: access token if the object's model uses some kind of public access
                             using tokens (usually a uuid4) to bypass access rules
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    record = request.env[res_model].browse(res_id)
    author_id = request.env.user.partner_id.id if request.env.user.partner_id else False
    if token:
        access_as_sudo = _has_token_access(res_model, res_id, token=token)
        if access_as_sudo:
            record = record.sudo()
            if request.env.user._is_public():
                author_id = record.partner_id.id if hasattr(record, 'partner_id') else author_id
            else:
                if not author_id:
                    raise NotFound()
        else:
            raise Forbidden()
    kw.pop('csrf_token', None)
    kw.pop('attachment_ids', None)
    return record.with_context(mail_create_nosubscribe=nosubscribe).message_post(body=message,
                                                                                   message_type=kw.pop('message_type', "comment"),
                                                                                   subtype=kw.pop('subtype', "mt_comment"),
                                                                                   author_id=author_id,
                                                                                   **kw)

class PortalPicking(CustomerPortal):

    def _get_search_picking(self, post):
        # OrderBy will be parsed in orm and so no direct sql injection
        # id is added to be sure that order is a unique sort key
        return '%s ,id desc' % post.get('picking_ftr','write_date desc')

    def _get_search_picking_domain(self, search):
        domain = []
        if search:
            for srch in search.split(" "):
                domain = [('name', 'ilike', srch)]
        return domain

    def _prepare_portal_layout_values(self):
        values = super(PortalPicking, self)._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        delivery_list = []
        stock_picking_delivey = request.env['stock.picking.type'].sudo().search([('code','=','outgoing')])
        for delivery in stock_picking_delivey:
            delivery_list.append(delivery.id)

        if request.env.user.has_group('base.group_erp_manager'):
            picking_count = request.env['stock.picking'].sudo().search_count([('picking_type_id','in',delivery_list)])
        else:
            picking_count = request.env['stock.picking'].sudo().search_count([('picking_type_id','in',delivery_list),('partner_id','=', partner.id)])
        values['delivery_order_count'] = picking_count

        receipt_list = []
        stock_picking_receipt = request.env['stock.picking.type'].sudo().search([('code','=','incoming')])
        for receipt in stock_picking_receipt:
            receipt_list.append(receipt.id)

        if request.env.user.has_group('base.group_erp_manager'):
            receipt_count = request.env['stock.picking'].sudo().search_count([('picking_type_id','in',receipt_list)])
        else:
            receipt_count = request.env['stock.picking'].sudo().search_count([('picking_type_id','in',receipt_list),('partner_id','=',partner.id)])
        values['receipt_order_count'] = receipt_count

        return values

    @http.route(['/my/delivery_orders', '/my/delivery_orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_picking(self, page=1, date_begin=None, date_end=None, sortby=None,search="", **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        stock_picking = request.env['stock.picking']
        domain = self._get_search_picking_domain(search)
        keep = QueryURL('/my/delivery_orders' , search=search, order=kw.get('order'))

        # count for pager
        repair_count = stock_picking.sudo().search_count(domain)
        # make pager
        delivery_list = []
        stock_picking_delivey = request.env['stock.picking.type'].sudo().search([('code','=','outgoing')])
        for delivery in stock_picking_delivey:
            delivery_list.append(delivery.id)
        if request.env.user.has_group('base.group_erp_manager'):
            domain += [('picking_type_id','in',delivery_list)]
        else:
            domain += [('picking_type_id','in',delivery_list),('partner_id','=',partner.id)]

        format_str = '%d%m%Y'

        if kw.get('time_ftr') == "filter all":
            domain += []

        if kw.get('time_ftr') == "current date":
            current_date = date.today()
            Previous_Date = date.today() + timedelta(days=1)
            domain += [('scheduled_date','>=',current_date),('scheduled_date','<',Previous_Date)]

        if kw.get('time_ftr') == "last month":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month-1)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        if kw.get('time_ftr') == "last week":
            domain+=[('scheduled_date','>=', ((date.today()  + relativedelta(days=0, weeks=-1)).strftime('%Y-%m-%d'))),
            ('scheduled_date','<=', ((date.today()  + relativedelta(days=6, weeks=-1)).strftime('%Y-%m-%d')))]

        if kw.get('time_ftr') == "last year":
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year-1))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year-1))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        if kw.get('time_ftr') == "current month":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        if kw.get('time_ftr') == "current week":
            domain+=[('scheduled_date','<=', ((date.today() - relativedelta(days=1, weeks=-1)).strftime('%Y-%m-%d'))),
            ('scheduled_date','>=', ((date.today() - relativedelta(days=7, weeks=-1)).strftime('%Y-%m-%d')))]

        if kw.get('time_ftr') == "current year":
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        if kw.get('time_ftr') == "current quarter":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            month_sec = '{:02d}'.format(date.today().month+2)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month_sec))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        pager = request.website.pager(
            url="/my/delivery_orders",
            total=repair_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        partner = request.env.user.partner_id
        picking = request.env['stock.picking'].sudo().search(domain, order=self._get_search_picking(kw))

        if kw.get('picking_group') == "status":
            grouped_picking = [request.env['stock.picking'].sudo().concat(*g) for k, g in groupbyelem(picking, itemgetter('state'))]
        elif kw.get('picking_group') == "document":
            grouped_picking = [request.env['stock.picking'].sudo().concat(*g) for k, g in groupbyelem(picking, itemgetter('origin'))]
        elif kw.get('picking_group') == "responsible":
            grouped_picking = [request.env['stock.picking'].sudo().concat(*g) for k, g in groupbyelem(picking, itemgetter('user_id'))]
        else:
            grouped_picking = [picking]
        if picking:
            values.update({
            # 'picking': picking,
            'page_name': 'stock_picking',
            'pager': pager,
            'keep' : keep,
            'grouped_picking' : grouped_picking,
            'groupby': kw.get('picking_group'),
            'default_url': '/my/delivery_orders',
            'users':request.env.user,
            })
        else:
            values.update({
            # 'picking': picking,
            'page_name': 'stock_picking',
            'pager': pager,
            'keep' : keep,
            'grouped_picking' : grouped_picking,
            'groupby': kw.get('picking_group'),
            'default_url': '/my/delivery_orders',
            'users':request.env.user,
            'khush' : 'khush'
            })
        
        return request.render("bi_website_portal_picking.portal_my_picking", values)

    @http.route(['/my/receipt', '/my/receipt/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_receipt(self, page=1, date_begin=None, date_end=None, sortby=None,search="", **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        stock_picking = request.env['stock.picking']
        domain = self._get_search_picking_domain(search)
        keep = QueryURL('/my/receipt' , search=search, order=kw.get('order'))

        # count for pager
        repair_count = stock_picking.search_count(domain)
        # make pager
        receipt_list = []
        stock_picking_receipt = request.env['stock.picking.type'].sudo().search([('code','=','incoming')])
        for receipt in stock_picking_receipt:
            receipt_list.append(receipt.id)
        if request.env.user.has_group('base.group_erp_manager'):
            domain += [('picking_type_id','in',receipt_list)]
        else:
            domain += [('picking_type_id','in',receipt_list),('partner_id','=',partner.id)]
        format_str = '%d%m%Y'

        if kw.get('time_ftr') == "filter all":
            domain += []
            
        if kw.get('time_ftr') == "current date":
            current_date = date.today()
            Previous_Date = date.today() + timedelta(days=1)
            domain += [('scheduled_date','>=',current_date),('scheduled_date','<',Previous_Date)]

        if kw.get('time_ftr') == "last month":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month-1)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]
            
        if kw.get('time_ftr') == "last week":
            domain+=[('scheduled_date','>=', ((date.today()  + relativedelta(days=0, weeks=-1)).strftime('%Y-%m-%d'))),
            ('scheduled_date','<=', ((date.today()  + relativedelta(days=6, weeks=-1)).strftime('%Y-%m-%d')))]
            
        if kw.get('time_ftr') == "last year":
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year-1))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year-1))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]
        
        if kw.get('time_ftr') == "current month":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        if kw.get('time_ftr') == "current week":
            domain+=[('scheduled_date','<=', ((date.today() - relativedelta(days=1, weeks=-1)).strftime('%Y-%m-%d'))),
            ('scheduled_date','>=', ((date.today() - relativedelta(days=7, weeks=-1)).strftime('%Y-%m-%d')))]

        if kw.get('time_ftr') == "current year":
            from_month = []
            to_month = []
            from_month.append('01')
            from_month.append('01')
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append('12')
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        if kw.get('time_ftr') == "current quarter":
            from_month = []
            to_month = []
            from_month.append('01')
            month = '{:02d}'.format(date.today().month)
            month_sec = '{:02d}'.format(date.today().month+2)
            from_month.append(str(month))
            from_month.append(str(date.today().year))
            to_month.append('30')
            to_month.append(str(month_sec))
            to_month.append(str(date.today().year))
            from_string = ''.join(from_month)
            to_string = ''.join(to_month)
            from_date = datetime.strptime(from_string, format_str)
            to_date = datetime.strptime(to_string, format_str)
            domain+=[('scheduled_date','>=',from_date),('scheduled_date','<=',to_date)]

        pager = request.website.pager(
            url="/my/receipt",
            total=repair_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        partner = request.env.user.partner_id
        picking = request.env['stock.picking'].sudo().search(domain, order=self._get_search_picking(kw))
        
        if kw.get('picking_group') == "status":
            grouped_picking = [request.env['stock.picking'].sudo().concat(*g) for k, g in groupbyelem(picking, itemgetter('state'))]
        elif kw.get('picking_group') == "document":
            grouped_picking = [request.env['stock.picking'].sudo().concat(*g) for k, g in groupbyelem(picking, itemgetter('origin'))]
        elif kw.get('picking_group') == "responsible":
            grouped_picking = [request.env['stock.picking'].sudo().concat(*g) for k, g in groupbyelem(picking, itemgetter('user_id'))]        
        else:
            grouped_picking = [picking]
        if picking:
            values.update({
            # 'receipt': picking,
            'page_name': 'stock_picking',
            'pager': pager,
            'keep' : keep,
            'grouped_picking' : grouped_picking,
            'groupby': kw.get('picking_group'),
            'default_url': '/my/receipt',
            'users':request.env.user,
            })
        else:
            values.update({
            # 'receipt': picking,
            'page_name': 'stock_picking',
            'pager': pager,
            'keep' : keep,
            'grouped_picking' : grouped_picking,
            'groupby': kw.get('picking_group'),
            'default_url': '/my/receipt',
            'users':request.env.user,
            'khush' : 'khush'
            })
        
        return request.render("bi_website_portal_picking.portal_my_receipt", values)

    @http.route(['/picking/view/detail/<model("stock.picking"):picking>'],type='http',auth="user",website=True)
    def picking_view(self, picking,report_type=None, category='', search='',access_token=None, download=False, **kwargs):
        context = dict(request.env.context or {})
        picking_obj = request.env['stock.picking']
        
        context.update(active_id=picking.id)
        picking_list = []
        picking_data = picking_obj.sudo().browse(int(picking))
        for items in picking_data:
            picking_list.append(items)

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=picking_data, report_type=report_type, report_ref='stock.action_report_delivery', download=download)
            
        return http.request.render('bi_website_portal_picking.picking_portal_template',{
            'picking_list': picking,
            'report_type': 'html',
            'force_refresh': True,
            'redirect_url': picking_data.get_portal_url(),
        })

    @http.route(['/receipt/view/detail/<model("stock.picking"):picking>'],type='http',auth="user",website=True)
    def receipt_view(self, picking,report_type=None, category='', search='',access_token=None, download=False, **kwargs):
        context = dict(request.env.context or {})
        picking_obj = request.env['stock.picking']
        
        context.update(active_id=picking.id)
        receipt_list = []
        picking_data = picking_obj.browse(int(picking))
        for items in picking_data:
            receipt_list.append(items)

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=picking_data, report_type=report_type, report_ref='stock.action_report_delivery', download=download)
            
        return http.request.render('bi_website_portal_picking.receipt_portal_template',{
            'receipt_list': picking,
            'report_type': 'html',
            'force_refresh': True,
            'redirect_url': picking_data.get_portal_url(),
        })

class PortalChatter(http.Controller):

    @http.route(['/mail/chatter_post_with_attachment'], type='http', methods=['POST'], auth='public', website=True,sitemap=False)
    def portal_chatter_post(self, res_model, res_id, message, **kw):
        url = request.httprequest.referrer
        Attachments = request.env['ir.attachment']
        upload_file = request.httprequest.files.getlist('upload')
        attachment = []
        request_repair_obj = request.env[res_model].sudo().browse(int(res_id)) 
        if upload_file:
            for i in range(len(upload_file)):
                if upload_file[i].filename:
                    attachment_id = Attachments.sudo().create({
                        'name': upload_file[i].filename,
                        'type': 'binary',
                        'datas': base64.encodestring(upload_file[i].read()),
                        'datas_fname': upload_file[i].filename,
                        'public': True,
                        'res_model': res_model,
                        'res_id': request_repair_obj.id,
                        'support_ticket_id' : request_repair_obj.id,
                    })
                    attachment.append(attachment_id.id)     
        if message:
            # message is received in plaintext and saved in html
            message = plaintext2html(message)
            new_data = _message_post_helper(res_model, int(res_id), message, **kw)
            if attachment:
                new_data.attachment_ids = attachment
            url = url + "#discussion"
        return request.redirect(url)