# -*- coding: utf-8 -*-
import hashlib
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from ..tools import date2local, date_timedelta


class AcruxChatMessages(models.Model):
    _inherit = 'acrux.chat.base.message'
    _name = 'acrux.chat.message'
    _description = 'Chat Message'
    _order = 'date_message desc'

    name = fields.Char('name', compute='_compute_name', store=True)
    msgid = fields.Char('Message Id')
    contact_id = fields.Many2one('acrux.chat.conversation', 'Contact',
                                 required=True, ondelete='cascade')
    connector_id = fields.Many2one('acrux.chat.connector', related='contact_id.connector_id',
                                   string='Connector', store=True, readonly=True)
    date_message = fields.Datetime('Date', required=True, default=fields.Datetime.now)
    from_me = fields.Boolean('Message From Me')
    company_id = fields.Many2one('res.company', related='contact_id.company_id',
                                 string='Company', store=True, readonly=True)
    ttype = fields.Selection(selection_add=[('contact', 'Contact'),
                                            ('product', 'Product')],
                             ondelete={'contact': 'cascade',
                                       'product': 'cascade'})
    error_msg = fields.Char('Error Message', readonly=True)
    event = fields.Selection([('unanswered', 'Unanswered Message'),
                              ('new_conv', 'New Conversation'),
                              ('res_conv', 'Resume Conversation')],
                             string='Event')
    user_id = fields.Many2one('res.users', string='Sellman', compute='_compute_user_id',
                              store=True)
    is_direct = fields.Boolean('is Direct', default=False)

    @api.depends('contact_id')
    def _compute_user_id(self):
        for r in self:
            user_id = r._get_user_id()
            r.user_id = user_id or self.env.user.id

    def _get_user_id(self):
        user_id = False
        if self.contact_id.sellman_id:
            user_id = self.contact_id.sellman_id.id
        return user_id

    @api.depends('text')
    def _compute_name(self):
        for r in self:
            if r.text:
                r.name = r.text[:10]
            else:
                r.name = '/'

    def conversation_update_time(self):
        for mess in self:
            is_info = bool(mess.ttype and mess.ttype.startswith('info'))
            if not is_info:
                data = {}
                cont = mess.contact_id
                if mess.from_me:
                    data.update({'last_sent': mess.date_message})
                    if cont.last_received:
                        data.update({'last_received_first': False})
                else:
                    # nº message
                    data.update({'last_received': mess.date_message})
                    # 1º message
                    if not cont.last_received_first:
                        data.update({'last_received_first': mess.date_message})
                if data:
                    cont.write(data)

    @api.model
    def create(self, vals):
        if vals.get('contact_id'):
            Conv = self.env['acrux.chat.conversation']
            conv_id = Conv.browse([vals.get('contact_id')])
            if not conv_id.last_received:
                vals.update(event='new_conv')
            elif conv_id.last_received < date_timedelta(minutes=-12 * 60):
                ''' After 12 hours it is resume '''
                vals.update(event='res_conv')
        ret = super(AcruxChatMessages, self).create(vals)
        ret.conversation_update_time()
        return ret

    @api.model
    def clean_number(self, number):
        return number.replace('+', '').replace(' ', '')

    @api.model
    def unlink_attachment(self, attach_to_del_ids, only_old=True):
        data = [('id', 'in', attach_to_del_ids)]
        if only_old:
            data.append(('delete_old', '=', True))
        to_del = self.env['ir.attachment'].sudo().search(data)
        erased_ids = to_del.ids
        to_del.unlink()
        return erased_ids

    def unlink(self):
        ''' Delete attachment too '''
        mess_ids = self.filtered(lambda x: x.res_model == 'ir.attachment' and x.res_id)
        attach_to_del = mess_ids.mapped('res_id')
        ret = super(AcruxChatMessages, self).unlink()
        if attach_to_del:
            self.unlink_attachment(attach_to_del)
        return ret

    def getJsDitc(self):
        out = self.read(['id', 'text', 'ttype', 'date_message', 'from_me', 'res_model',
                         'res_id', 'error_msg'])
        for x in out:
            x['date_message'] = date2local(self, x['date_message'])
        return out

    @api.model
    def get_url_image(self, res_model, res_id, field='image_chat', prod_id=None):
        url = False
        if not prod_id:
            prod_id = self.env[res_model].search([('id', '=', res_id)], limit=1)
        prod_id = prod_id if len(prod_id) == 1 else False
        if prod_id:
            field_obj = getattr(prod_id, field)
            if not field_obj:
                return prod_id, False
            check_weight = self.message_check_weight(field=field_obj)
            if check_weight:
                hash_id = hashlib.sha1((prod_id.write_date or prod_id.create_date or '').encode('utf-8')).hexdigest()[0:7]
                url = '/web/static/chatresource/%s/%s_%s/%s' % (prod_id._name, prod_id.id, hash_id, field)
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                url = base_url.rstrip('/') + url
        return prod_id, url

    @api.model
    def get_url_attach(self, att_id):
        url = False
        attach_id = self.env['ir.attachment'].sudo().search([('id', '=', att_id)], limit=1)
        attach_id = attach_id if len(attach_id) == 1 else False
        if attach_id:
            self.message_check_weight(value=attach_id.file_size, raise_on=True)
            access_token = attach_id.generate_access_token()[0]
            url = '/web/chatresource/%s/%s' % (attach_id.id, access_token)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = base_url.rstrip('/') + url
        return attach_id, url

    def message_parse(self):
        '''For inherit on each Connector
           Return message formated '''
        self.ensure_one()
        return False

    def message_send(self):
        '''For inherit on each Connector.
           Return msgid '''
        self.ensure_one()
        if not self.ttype.startswith('info'):
            self.message_check_allow_send()
        return False

    def message_check_allow_send(self):
        '''For inherit on each Connector.
           raise when error '''
        for rec in self:
            if rec.text and len(rec.text) >= 4000:
                raise ValidationError(_('Message is to large (4.000 caracters).'))

    def message_check_weight(self, field=None, value=None, raise_on=False):
        '''For inherit on each Connector.
           raise if required '''
        self.ensure_one()
        return True
