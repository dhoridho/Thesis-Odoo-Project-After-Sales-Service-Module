# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, exceptions, fields, models, _
import urllib.parse
from odoo.http import request
import logging
import base64
import re

_logger = logging.getLogger(__name__)


def replace_body_html(body):
    if body:
        if type(body) != str:
            body = body.decode()

        body = body.replace('background-color:#875A7B','background-color:#ECB22E')
        body = body.replace('background-color: #875A7B','background-color:#ECB22E')
        body = body.replace('background-color :#875A7B','background-color:#ECB22E')
        body = body.replace('background-color : #875A7B','background-color:#ECB22E')

        body = body.replace('border-color:#875A7B','border-color:#ECB22E')
        body = body.replace('border-color: #875A7B','border-color:#ECB22E')
        body = body.replace('border-color :#875A7B','border-color:#ECB22E')
        body = body.replace('border-color : #875A7B','border-color:#ECB22E')

        body = body.replace('border:1px solid #875A7B','border:1px solid #ECB22E')
        body = body.replace('border :1px solid #875A7B','border:1px solid #ECB22E')
        body = body.replace('border: 1px solid #875A7B','border:1px solid #ECB22E')
        body = body.replace('border : 1px solid #875A7B','border:1px solid #ECB22E')

    return body


class MailComposer(models.TransientModel):

    _inherit = 'mail.compose.message'


    def onchange_template_id(self, template_id, composition_mode, model, res_id):
        res = super(MailComposer, self).onchange_template_id(template_id, composition_mode, model, res_id)
        if res.get('value') and res['value'].get('body'):
            body = res['value']['body']
            if body:
                body = replace_body_html(body)
                res['value']['body'] = body

        return res



class MailThread(models.AbstractModel):

    _inherit = 'mail.thread'

    def message_notify(self, *,
                       partner_ids=False, parent_id=False, model=False, res_id=False,
                       author_id=None, email_from=None, body='', subject=False, **kwargs):
        if body:
            body = replace_body_html(body)
        res = super(MailThread, self).message_notify(
                       partner_ids=partner_ids, parent_id=parent_id, model=model, res_id=res_id,
                       author_id=author_id, email_from=email_from, body=body, subject=subject, **kwargs)
        return res

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, *,
                     body='', subject=None, message_type='notification',
                     email_from=None, author_id=None, parent_id=False,
                     subtype_xmlid=None, subtype_id=False, partner_ids=None, channel_ids=[],
                     attachments=None, attachment_ids=None,
                     add_sign=True, record_name=False,
                     **kwargs):

        if body:
            body = replace_body_html(body)

        res =  super(MailThread, self).message_post( 
                     body=body, subject=subject, message_type=message_type,
                     email_from=email_from, author_id=author_id, parent_id=parent_id,
                     subtype_xmlid=subtype_xmlid, subtype_id=subtype_id, partner_ids=partner_ids, channel_ids=channel_ids,
                     attachments=attachments, attachment_ids=attachment_ids,
                     add_sign=add_sign, record_name=record_name,
                     **kwargs)
        return res



    def _notify_get_action_link(self, link_type, **kwargs):
        """ Prepare link to an action: view document, follow document, ... """
        res = super(MailThread, self)._notify_get_action_link(link_type, **kwargs)
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        res = res.replace(base_url,'')
        current_action_model_id = False
        if self._name != 'mail.thread':
            current_action_model_id = request.session.get('history_action_'+self._name) or False
        else:
            if kwargs.get('model'):
                current_action_model_id = request.session.get('history_action_'+kwargs['model']) or False

        if '/mail/view' in res and 'res_id' in res and '?' in res and current_action_model_id:
            res = res.replace('res_id','id')
            res = res.replace('/mail/view?','/web#')
            if 'action' not in res:
                res+='&view_type=form&action='+str(current_action_model_id)
            if 'id=' in res:
                parsed_url = res.split('#')[1]
                query_params = urllib.parse.parse_qs(parsed_url)
                res_id = query_params['id'][0]
                encrypt_id = base64.b64encode(res_id.encode())
                encrypt_id = encrypt_id.decode()
                encrypt_id = encrypt_id.replace('=','!')
                res = re.sub(r'id=\d+', 'hashcode='+encrypt_id, res)
        res = base_url+ '/web?db='+self._cr.dbname+'&redirect='+urllib.parse.quote(res, safe='')
        return res



class MailTemplate(models.Model):
    _inherit = 'mail.template'


    def send_mail(self, res_id, force_send=False, raise_exception=False, email_values=None, notif_layout=False):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        current_action_model_id = request.session.get('history_action_'+self._name) or False
        if self._context.get('url'):
            old_url = self._context['url']
            if 'model' in old_url and 'res_id' in old_url and '?' in old_url and current_action_model_id:
                old_url = old_url.replace('/web?','/web#')
                old_url = old_url.replace('res_id','id')
                if 'action' not in old_url:
                    old_url+='&view_type=form&action='+str(current_action_model_id)


            if 'id=' in old_url:
                parsed_url = old_url.split('#')[1]
                query_params = urllib.parse.parse_qs(parsed_url)
                rec_id = query_params['id'][0]
                encrypt_id = base64.b64encode(rec_id.encode())
                encrypt_id = encrypt_id.decode()
                encrypt_id = encrypt_id.replace('=','!')
                old_url = re.sub(r'id=\d+', 'hashcode='+encrypt_id, old_url)

            new_url = base_url+ '/web?db='+self._cr.dbname+'&redirect='+urllib.parse.quote(old_url, safe='')
            self.env.context = dict(self.env.context)
            self.env.context.update({'url': new_url})


        data = self
        if data.body_html:
            body = data.body_html
            body = replace_body_html(body)
            data.write({'body_html':body})
        res = super(MailTemplate, self).send_mail(res_id, force_send, raise_exception, email_values, notif_layout)

        return res


class MailMail(models.Model):
    _inherit = 'mail.mail'

    @api.model
    def create(self, vals):
        if vals.get('body_html'):
            body = vals['body_html']
            body = replace_body_html(body)
            vals['body_html'] = body
        return super(MailMail, self).create(vals)


class MailMessage(models.Model):
    _inherit = 'mail.message'

    action_id_position = fields.Integer()


    def message_format(self):
        res = super(MailMessage, self).message_format()
        count = 0
        for message in self:
            message = message.sudo()
            res[count]['action_id_position'] = message.action_id_position
            count+=1

        return res


    @api.model
    def create(self, vals):
        body = False
        if vals.get('body'):
            body = vals['body']
            body = replace_body_html(body)
            vals['body'] = body
        if vals.get('model'):
            try:
                current_action_model_id = request.session.get('history_action_'+vals['model']) or False
            except Exception as e:
                current_action_model_id = False
                _logger.info(f"Error in mail.message create: {e}")
            if current_action_model_id:
                vals['action_id_position'] = current_action_model_id
                if body:
                    check_split = body.split(' ')
                    for check in check_split:
                        if 'web' in check and 'model' in check and 'id' in check and '#' in check and '&' in check:
                            check = check.replace('href =','')
                            check = check.replace('href=','')
                            check = check.replace('"','')
                            new_url = check+'&view_type=form&action='+str(current_action_model_id)
                            body = body.replace(check,new_url)
                            vals['body'] = body.replace(check,new_url)

        return super(MailMessage, self).create(vals)