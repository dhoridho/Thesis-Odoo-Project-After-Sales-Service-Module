# -*- coding: utf-8 -*-
import json
import requests
import re
import logging
from odoo import models, api, fields
# from odoo.addons.acrux_chat.tools import get_image_from_url
from odoo.addons.acrux_chat.tools import phone_format, date2local
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)

API3_ENDPOINT = "https://api3.qiscus.com/api/v2/sdk/"
API_MULTICHANNEL = "https://multichannel-api.qiscus.com/"

class QiscussConversation(models.Model):
    _inherit = 'acrux.chat.conversation'

    @api.model
    def get_import_templates(self):
        return [{
            'label': 'Import Template for Conversation',
            'template': '/equip3_crm_whatsapp/static/xls/acrux_chat_conversation.xlsx'
        }]

    def _default_team_user(self):
        if self.env.user.has_group('acrux_chat.group_chat_basic') and not self.env.user.has_group('acrux_chat.group_chat_basic_extra'):
            return self.env.user.sale_team_id.ids
        else:
            return self.env['crm.team'].search([]).ids

    room_id = fields.Char('Qiscus Room ID')
    room_name = fields.Char('Qiscus Room Name')
    session_status = fields.Char('Session Status')
    team_ids = fields.Many2many(
        'crm.team', default=_default_team_user)



    # @api.model
    # def create(self, vals):
    #     print("Value in CREATE Conversation: %s" % (vals))
    #     res = super(QiscussConversation, self).create(vals)
    #     if vals.get('connector_id') and vals.get('number'):
    #         conn_id = self.env['acrux.chat.connector'].browse([vals.get('connector_id')])
    #         if conn_id.connector_type == 'qiscuss':
    #             # param = {'chatId': '%s@c.us' % vals.get('number').strip('+')}
    #             app_id = conn_id.qc_app_name
    #             sdk_token = conn_id.qc_sdk_token
    #             header = {
    #                 'qiscus-sdk-app-id': app_id,
    #                 'qiscus-sdk-token': sdk_token
    #             }
    #             # param = {'chatId': '%s@c.us' % vals.get('number').strip('+')}
    #             phone_number = vals.get('number').strip('+')
    #             param = {'id': phone_number}
    #
    #             try:
    #                 # data = conn_id.qc_request('get', 'dialog', param, timeout=10)
    #                 data = conn_id.qc_request('get', 'user_rooms?page=1&show_participants=true&limit=50&room_type=default', headers=header, timeout=20, api_url=API3_ENDPOINT)
    #                 room_info = data.get('rooms_info')
    #                 if room_info:
    #                     for room in room_info:
    #                         rooms = {}
    #                         room_id = room.get('id')
    #                         room_name = room.get('room_name')
    #                         last_chat = room.get('last_comment')
    #                         user_avatar = last_chat.get('user_avatar_url')
    #                         if room_name == phone_number:
    #                             rooms.update({
    #                                 'room_id': room_id,
    #                                 'room_name': room_name,
    #                             })
    #                             if user_avatar and user_avatar.startswith('http'):
    #                                 raw = get_image_from_url(user_avatar)
    #                                 if raw:
    #                                     rooms.update({'image_128': raw})
    #                             res.write(rooms)
    #             except Exception as e:
    #                 pass
    #     return res

    def conversation_send_read(self):
        super(QiscussConversation, self).conversation_send_read()
        for conv_id in self:
            conn_id = conv_id.connector_id
            if conn_id.connector_type == 'qiscuss':
                room_id = conv_id.room_id
                path = f'api/v2/customer_rooms/{room_id}/mark_as_read'
                try:
                    payload = {}
                    url = conn_id.qc_get_endpoint(path, api_url=API_MULTICHANNEL)
                    header = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'app_id': conn_id.qc_app_name,
                        'Authorization': conn_id.apikey
                    }
                    data = json.dumps({'phone': conv_id.number.lstrip('+')})
                    requests.post(url, data=payload, headers=header, timeout=1, verify=conn_id.verify)
                except Exception as _e:
                    pass

    @api.model
    def new_message(self, msg_data):
        # conn_id = self.connector_id
        connector_id = msg_data['connector_id']
        conn_id = self.env['acrux.chat.connector'].browse(connector_id)
        res = super(QiscussConversation, self).new_message(msg_data)
        if conn_id.connector_type == 'qiscuss':
            number_format = phone_format(msg_data['number'], formatted=True)
            # conversation = self.search([('number_format', '=', number_format),
            #                             ('connector_id', '=', msg_data['connector_id'])])
            conversation = self.search([('number', 'ilike', msg_data['number']),
                                        ('connector_id', '=', msg_data['connector_id'])])
            if conversation:
                conversation.write({
                    'room_id': msg_data['room_id'],
                    'room_name': msg_data['room_name']
                })
                res.write({
                    'comment_id': msg_data['comment_id']
                })
        return res

    def send_message(self, msg_data):
        self.ensure_one()
        # for conv_id in self:
        conn_id = self.connector_id
        if conn_id.connector_type == 'qiscuss':
            if not 'template_id' in msg_data:
                template_obj = self.env['qiscus.template'].search([('name', 'ilike', 'chatroom_default_answer_text')],
                                                                  limit=1)
                msg_data.update({'template_id': template_obj.id})
            if self.status != 'current':
                raise ValidationError('You can\'t write in this conversation, please refresh the screen.')
            if self.sellman_id != self.env.user:
                raise ValidationError('This conversation is no longer attended to by you.')
            AcruxChatMessages = self.env['acrux.chat.message']
            message_obj = AcruxChatMessages.create(msg_data)
            message_obj.qc_message_send(msg_data)
            res = {'id': message_obj.id,
                    'date_message': date2local(self, message_obj.date_message),
                    'res_model': message_obj.res_model,
                    'res_id': message_obj.res_id,
                    }
            return res
        else:
            res = super(QiscussConversation, self).send_message(msg_data)
        return res

    @api.model
    def sync_conversation(self):
        conn_id = self.env['acrux.chat.connector'].search([('qc_status', '=', True)], limit=1)
        if conn_id.connector_type == 'qiscuss':
            app_id = conn_id.qc_app_name
            sdk_token = conn_id.qc_sdk_token
            header = {
                'qiscus-sdk-app-id': app_id,
                'qiscus-sdk-token': sdk_token
            }
            try:
                data = conn_id.qc_request('get', 'user_rooms?page=1&show_participants=true&limit=50&room_type=default',
                                          headers=header, timeout=20, api_url=API3_ENDPOINT)
                room_info = data.get('results').get('rooms_info')
                if room_info:
                    for room in room_info:
                        rooms = {}
                        channel_id = json.loads(room.get('options')).get('channel_id')
                        last_chat = room.get('last_comment')
                        room_id = last_chat.get('room_id_str') or ''
                        room_name = last_chat.get('room_name') or ''
                        emails = last_chat.get('email') or ''
                        if re.match('^[0-9]+$', room_name):
                            phone_number = room_name
                        elif re.match('^[0-9]+$', emails):
                            phone_number = emails
                        else:
                            phone_number = room_id
                        message = last_chat.get('message')
                        payload = last_chat.get('payload')
                        user_avatar = last_chat.get('user_avatar_url')
                        ttype = last_chat.get('type')
                        comment_id = last_chat.get('comment_before_id_str')
                        msg_id = last_chat.get('unique_temp_id').replace('wa_', '')
                        if channel_id == conn_id.qc_channel_id:
                            # _logger.info('Qiscuss New Message: %s' % room)
                            # _logger.info('Phone Number: %s' % phone_number)
                            AcruxChatMessages = self.env['acrux.chat.message'].search(
                                ['&', ('connector_id', '=', conn_id.id), '|',
                                 ('comment_id', '=', comment_id), ('msgid', 'ilike', msg_id)], limit=1)
                            if not AcruxChatMessages:
                                data = {
                                    'ttype': ttype,
                                    'connector_id': conn_id.id,
                                    'name': room_name,
                                    'number': phone_number,
                                    'message': message,
                                    'message_id': msg_id,
                                    'comment_id': comment_id,
                                    'room_id': room_id,
                                    'room_name': room_name,
                                    'url': None
                                }
                                self.new_message(data)
            except Exception as e:
                _logger.info(e)
                pass

    # def qc_update_status(self, msg_data):
    #     try:
    #         AcruxChatMessages = self.env['acrux.chat.message'].search(
    #             ['&', ('connector_id', '=', msg_data['connector_id']), '|',
    #              ('comment_id', '=', msg_data['comment_id']), ('msgid', 'ilike', msg_data['message_id'])])
    #         if AcruxChatMessages:
    #             AcruxChatMessages.write({
    #                 'status': msg_data['status']
    #             })
    #     except Exception as e:
    #         _logger.info(e)
    #         pass