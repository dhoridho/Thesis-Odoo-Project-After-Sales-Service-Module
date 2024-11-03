# -*- coding: utf-8 -*-
import logging
from odoo import models
from odoo import fields
from odoo import api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError
from ..tools import DEFAULT_IMAGE_URL
from ..tools import get_image_url
from ..tools import create_attachment_from_url, date2local, date_timedelta, phone_format
_logger = logging.getLogger(__name__)


class AcruxChatConversation(models.Model):
    _name = 'acrux.chat.conversation'
    _description = 'Chat Conversation'

    name = fields.Char('Name', required=True)
    number = fields.Char('Number Original', required=True)
    number_format = fields.Char('Number', compute='_compute_number_format',
                                store=True, readonly=True)
    image_128 = fields.Image("Avatar", max_width=128, max_height=128)
    image_url = fields.Char('Avatar Url', compute='_image_update', store=True,
                            default=DEFAULT_IMAGE_URL, required=True)
    connector_id = fields.Many2one('acrux.chat.connector', 'Connector', required=True,
                                   ondelete='cascade')
    res_partner_id = fields.Many2one('res.partner', 'Client', ondelete='set null')
    status = fields.Selection([('new', 'New'),
                               ('current', 'Current'),
                               ('done', 'Done')], 'Status', required=True,
                              default='new')
    chat_message_ids = fields.One2many('acrux.chat.message', 'contact_id',
                                       'Messages')
    sellman_id = fields.Many2one('res.users', 'Sellman')
    last_sent = fields.Datetime('Last sent', help='Last message sent to the partner.')
    last_received = fields.Datetime('Last Received', help='To prevent send message with extra fee.')
    last_received_first = fields.Datetime('First Unanswered', help='First unanswered message.')
    company_id = fields.Many2one('res.company', related='connector_id.company_id', string='Company',
                                 store=True, readonly=True)
    team_id = fields.Many2one('crm.team', related='connector_id.team_id', store=False)
    border_color = fields.Char(related='connector_id.border_color', store=False)

    @api.constrains('status', 'sellman_id')
    def _constrain_status(self):
        for r in self:
            if r.status == 'current' and not r.sellman_id:
                raise ValidationError(_('Have to set sellman to set conversation to "current"'))

    @api.constrains('number_format', 'connector_id')
    def _constrains_number_format(self):
        for rec in self:
            if rec.number_format:
                if self.search_count([('connector_id', '=', rec.connector_id.id),
                                      ('number_format', '=', rec.number_format)]) > 1:
                    raise ValidationError(_('Number in connector has to be unique.'))

    @api.model
    def create(self, vals):
        if not vals.get('last_sent'):
            # to release if not send message
            vals.update({'last_sent': fields.Datetime.now()})
        return super(AcruxChatConversation, self).create(vals)

    def event_create(self, event):
        Message = self.env['acrux.chat.message']
        for rec in self:
            txt = dict(Message._fields['event'].selection).get(event)
            data = {'ttype': 'info',
                    'from_me': True,  # By convention
                    'contact_id': rec.id,
                    'event': event,
                    'text': '%s (%s)' % (txt, rec.sellman_id.name or 'Undefined')}
            Message.create(data)

    @api.depends('image_128', 'res_partner_id.image_128')
    def _image_update(self):
        for rec in self:
            if rec.image_128 and rec.write_date:
                rec.image_url = get_image_url(self, rec, rec.image_128)
            elif rec.res_partner_id.image_128:
                rec.image_url = get_image_url(self, rec.res_partner_id, rec.res_partner_id.image_128)
            else:
                rec.image_url = DEFAULT_IMAGE_URL

    @api.depends('number')
    def _compute_number_format(self):
        for rec in self:
            rec.number_format = phone_format(rec.number, formatted=True)

    @api.depends('name', 'number_format')
    def name_get(self):
        result = []
        full_name = self._context.get('full_name')
        for conv in self:
            if full_name:
                result.append((conv.id, 'To: %s (%s) | From: %s' % (conv.name, conv.number_format, conv.connector_id.name)))
            else:
                result.append((conv.id, '%s (%s)' % (conv.name, conv.number_format)))
        return result

    @api.model
    def get_to_done(self):
        return {'status': 'done',
                'sellman_id': False}

    @api.model
    def get_to_current(self):
        return {'sellman_id': self.env.user.id,
                'status': 'current'}

    @api.model
    def get_to_new(self):
        return {'status': 'new',
                'sellman_id': False}

    @api.model
    def new_message(self, data):
        '''
        Processes received message (WebHook).
        :param data:
            ttype:
            connector_id:
            name:
            number:
            message:
        :return: objetc message_id
        '''
        url = data['url']
        del data['url']
        AcruxChatMessages = self.env['acrux.chat.message']
        number_format = phone_format(data['number'], formatted=True)
        conversation = self.search([('number_format', '=', number_format),
                                    ('connector_id', '=', data['connector_id'])])
        if not conversation:
            conversation = self.create({'name': data['name'] or data['number'],
                                        'connector_id': data['connector_id'],
                                        'number': data['number']})

        message_id = AcruxChatMessages.create({'text': data['message'],
                                               'contact_id': conversation.id,
                                               'ttype': data['ttype'],
                                               'from_me': False})
        if data['ttype'] in ['image', 'audio', 'video', 'file']:
            attach_id = create_attachment_from_url(self.env, data['message'], url, message_id)
            message_id.write({'res_model': 'ir.attachment', 'res_id': attach_id.id})

        user_active = conversation.sellman_id.acrux_chat_active
        if conversation.status == 'done':
            conversation.write(self.get_to_new())
            limit = 50
        elif conversation.status == 'current':
            if not user_active:
                conversation.write(self.get_to_new())
                limit = 50
            else:
                limit = 1
        else:
            limit = 1

        data_to_send = conversation.build_dict(limit)
        channel = None
        if conversation.sellman_id:
            channel = (self._cr.dbname, self._name, conversation.sellman_id.id)
        else:
            channel = (self._cr.dbname, self._name)
        self.env['bus.bus'].sendone(channel, {'new_messages': data_to_send})
        return message_id

    @api.model
    def new_message_event(self, connector_id, msgid, reason):
        AcruxChatMessages = self.env['acrux.chat.message']
        message_id = AcruxChatMessages.search([('connector_id', '=', connector_id.id),
                                               ('msgid', '=', msgid)], limit=1)
        if message_id:
            message_id.error_msg = reason
            conv_id = message_id.contact_id
            if conv_id.sellman_id:
                channel = (self._cr.dbname, self._name, conv_id.sellman_id.id)
            else:
                channel = (self._cr.dbname, self._name)
            data_to_send = conv_id.build_dict(limit=0)
            data_to_send[0]['messages'] = message_id.getJsDitc()
            self.env['bus.bus'].sendone(channel, {'error_messages': data_to_send})

    def send_message(self, msg_data):
        ''' Call from JavaScript '''
        self.ensure_one()
        if self.status != 'current':
            raise ValidationError(_('You can\'t write in this conversation, please refresh the screen.'))
        if self.sellman_id != self.env.user:
            raise ValidationError(_('This conversation is no longer attended to by you.'))
        AcruxChatMessages = self.env['acrux.chat.message']
        message_obj = AcruxChatMessages.create(msg_data)
        message_obj.message_send()
        return {'id': message_obj.id,
                'date_message': date2local(self, message_obj.date_message),
                'res_model': message_obj.res_model,
                'res_id': message_obj.res_id,
                }

    def send_message_and_bus(self, msg_data):
        ''' msg_data = {
                'ttype': 'info',
                'from_me': True,
                'contact_id': self.conversation_id,
                'res_model': False,
                'res_id': False,
                'text': 'un texto',
            }
        '''
        for conv_id in self:
            result = conv_id.send_message(msg_data)
            message_id = self.env['acrux.chat.message'].browse([result['id']])
            if conv_id.sellman_id:
                channel = (self._cr.dbname, self._name, conv_id.sellman_id.id)
            else:
                channel = (self._cr.dbname, self._name)
            data_to_send = conv_id.build_dict(limit=0)
            data_to_send[0]['messages'] = message_id.getJsDitc()
            self.env['bus.bus'].sendone(channel, {'new_messages': data_to_send})

    def get_fields_to_read(self):
        return ['id', 'name', 'sellman_id', 'status', 'team_id', 'image_url',
                'number_format', 'border_color']

    def build_dict(self, limit, offset=0):
        AcruxChatMessages = self.env['acrux.chat.message']
        field_names = self.get_fields_to_read()
        conversations = self.read(field_names)
        if limit > 0:
            for conv in conversations:
                message_id = AcruxChatMessages.search([('contact_id', '=', conv['id'])],
                                                      limit=limit, offset=offset)
                message = message_id.getJsDitc()
                message.reverse()
                conv['messages'] = message
        return conversations

    @api.model
    def search_active_conversation(self):
        ''' For present user '''
        domain = ['|', ('status', '=', 'new'),
                  '&', ('status', '=', 'current'),
                       ('sellman_id', '=', self.env.user.id)]
        conversations = self.search(domain)
        return conversations.build_dict(50)

    def conversation_send_read(self):
        ''' Send notification of read message.
            For inherit on each Connector. '''
        pass

    @api.model
    def conversation_verify(self):
        ''' Call from cron or direct '''
        Connector = self.env['acrux.chat.connector']
        empty_conv = to_done_ids = to_news_ids = self.env['acrux.chat.conversation']
        for conn_id in Connector.search([]):
            add_ids = self.search([('connector_id', '=', conn_id.id),
                                   ('status', '=', 'current')])
            to_news = empty_conv
            if conn_id.time_to_reasign:
                date_to_news = date_timedelta(minutes=-conn_id.time_to_reasign)
                to_news = add_ids.filtered(lambda x: x.last_received_first and
                                           x.last_received_first < date_to_news)
                to_news.event_create('unanswered')
            date_to_done = date_timedelta(minutes=-30)
            to_done = add_ids.filtered(lambda x: not x.last_received_first and x.last_sent and
                                       x.last_sent < date_to_done)
            to_done_ids |= to_done
            to_news_ids |= to_news
        all_ids = to_done_ids + to_news_ids
        if len(all_ids):
            conv_delete_ids = all_ids.read(['id', 'sellman_id'])
            to_done_ids.write(self.get_to_done())
            to_news_ids.write(self.get_to_new())
            data_to_send = {'new_messages': to_news_ids.build_dict(50),
                            'delete_taken_conversation': conv_delete_ids}
            self.env['bus.bus'].sendone((self._cr.dbname, self._name), data_to_send)
        _logger.info('________ | conversation_verify: %s to new, %s to done' % (len(to_news_ids), len(to_done_ids)))

    def block_conversation(self):
        # it's mine
        self.ensure_one()
        if self.status in ['new', 'done']:
            self.write(self.get_to_current())
            data_to_send = {'id': self.id, 'sellman_id': [self.env.user.id, self.env.user.name]}
            self.env['bus.bus'].sendone((self._cr.dbname, self._name),
                                        {'delete_conversation': [data_to_send]})
        else:
            if self.sellman_id.id != self.env.user.id:
                raise ValidationError(_('Customer is already being served for %s') % self.sellman_id.name)
        if not self._context.get('no_send_read'):
            self.conversation_send_read()

    def release_conversation(self):
        self.write(self.get_to_done())

    @api.model
    def search_product(self, string):
        ProductProduct = self.env['product.product']
        if string:
            domain = ['|', ('name', 'ilike', string), ('default_code', 'ilike', string)]
        else:
            domain = []
        fields = ['id', 'name', 'list_price', 'qty_available', 'uom_id', 'write_date']
        out = ProductProduct.search_read(domain, fields, order='list_price', limit=16)
        return out

    def init_and_notify(self):
        self.ensure_one()
        self.block_conversation()
        data_to_send = self.build_dict(50)
        channel = (self._cr.dbname, self._name, self.sellman_id.id)
        self.env['bus.bus'].sendone(channel, {'init_conversation': data_to_send})
