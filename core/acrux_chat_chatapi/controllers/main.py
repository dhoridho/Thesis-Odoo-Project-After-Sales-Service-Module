# -*- coding: utf-8 -*-

import json
import logging
from odoo import http
from odoo.http import request, Response
from odoo.addons.acrux_chat.tools import get_image_from_url
_logger = logging.getLogger(__name__)


def log_request():
    data = json.dumps(request.jsonrequest, indent=2)
    _logger.info('\n%s' % data)


def get_connector(connector_uuid, instanceid):
    connector = request.env['acrux.chat.connector'].sudo()
    return connector.search([('uuid', '=', connector_uuid), ('ca_app_name', '=', instanceid)], limit=1)


class ChatChatApiWebhook(http.Controller):

    @http.route('/acrux_webhook/chatapi/<string:connector_uuid>', auth='public', type='json', method=['POST'])
    def webhook_chatapi(self, connector_uuid, **post):
        ''' Connector searched for according to 'connector_uuid'. '''
        log_request()
        parse_ttype = {'chat': 'text', 'ptt': 'audio', 'document': 'file'}

        try:
            body = request.jsonrequest
            if body:
                Conversation = request.env['acrux.chat.conversation'].sudo()
                instanceId = body.get('instanceId')
                connector_id = get_connector(connector_uuid, instanceId)
                if not connector_id:
                    return Response(status=404)

                ChatUpdate = body.get('chatUpdate', [])  # old - new
                for contact in ChatUpdate:
                    old = contact.get('old', {}) or {}
                    new = contact.get('new', {}) or {}
                    search_number = old.get('id') or new.get('id')
                    old_image = old.get('image') or ''
                    new_image = new.get('image') or ''
                    go = bool(new_image and new_image.startswith('http') and old_image != new_image)
                    number, sep, is_group = search_number.partition('-')
                    if go and not is_group:
                        number, sep, aux = number.partition('@')
                        conv_id = Conversation.search([('number', '=', '+' + number),
                                                       ('connector_id', '=', connector_id.id)])
                        if conv_id:
                            raw_image = get_image_from_url(new_image)
                            conv_id.image_128 = raw_image
                    return Response(status=200)

                ack = body.get('ack', [])  # delivered - viewed
                for data in ack:
                    return Response(status=200)

                messages = body.get('messages', [])
                for mess in messages:
                    if not mess.get('fromMe'):
                        url = False
                        # chat, image, ptt, document, audio, video, location, call_log, vcard
                        ttype = mess.get('type')
                        ttype = parse_ttype.get(ttype, ttype)
                        name = mess.get('senderName')  # or 'chatName'?
                        number = mess.get('author').split('@')[0].split('-')[0]
                        # TODO: contact
                        if ttype == 'text':
                            text = mess.get('body')
                        elif ttype in ['image', 'audio', 'video', 'file']:
                            text = mess.get('caption') or ttype
                            url = mess.get('body')
                        elif ttype == 'call_log':
                            ttype = 'text'
                            text = '[Call]'
                        else:
                            ttype = 'text'
                            text = 'Not allowed, type %s' % mess.get('type')
                        data = {
                            'ttype': ttype,
                            'connector_id': connector_id.id,
                            'name': name,
                            'number': '+' + number,
                            'message': text,
                            'url': url
                        }
                        Conversation.new_message(data)
            return Response(status=200)
        except Exception:
            request._cr.rollback()
            _logger.error('Error', exc_info=True)
            return Response(status=500)  # Internal Server Error

# {
#     "instanceId": "150505",
#     "messages": [
#         {
#             "author": "56979764016@c.us",
#             "body": "aaaa",               : text or url
#             "caption": null,
#             "chatId": "56979764016@c.us", : 56979764016-56979764016@c.us
#             "chatName": "José",
#             "fromMe": false,
#             "id": "false_56979764016@c.us_3EB0FFF1C01C22D4E1B9",
#             "isForwarded": 0,
#             "messageNumber": 28,
#             "quotedMsgBody": null,
#             "quotedMsgId": null,
#             "self": 1,
#             "senderName": "José",
#             "time": 1594851044,
#             "type": "chat"
#         }
#     ]
# }
# {
#     "chatUpdate": [
#         {
#             "old": {
#                 "id": "56672217777@c.us",
#                 "name": "AcruxLab",
#                 "image": "https://pps.whatsapp.net/v/t61.24694-24/116275375_206105710830820_6412222560233075794_n.jpg?oh=668bc7b1c303b4d9a1aacb1911a4f028&oe=5F251A72",
#                 "metadata": {
#                     "isGroup": false,
#                     "participants": [],
#                     "groupInviteLink": null
#                 }
#             },
#             "new": {
#                 "id": "56672217777@c.us",
#                 "name": "AcruxLab",
#                 "metadata": {
#                     "isGroup": false,
#                     "participants": [],
#                     "groupInviteLink": null
#                 },
#                 "image": "https://pps.whatsapp.net/v/t61.24694-24/116796288_582707929061061_3204454255506287173_n.jpg?oh=b114c1180d46b4959e8f3bcad7f0843f&oe=5F252FA2"
#             }
#         }
#     ],
#     "instanceId": "150505"
# }
