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


def get_connector(connector_uuid, appid='ublch-mqh1qsdhhbd1rj2'):
    connector = request.env['acrux.chat.connector'].sudo()
    return connector.search([('qc_channel_id', '=', connector_uuid), ('qc_app_name', '=', appid)], limit=1)

def get_contact(messages):
    kontak = []
    if messages:
        for msg in messages:
            if 'name' in msg:
                kontak.append({'name': msg.get('name')('formatted_name')})
            if 'phones' in msg:
                for pon in msg.get('phones'):
                    kontak.append({'phone': pon.get('phone'), 'type': pon.get('type'), 'wa_id': pon.get('wa_id') if 'wa_id' in pon else False})
    return kontak


class ChatQiscussWebhook(http.Controller):

    @http.route('/qiscuss_webhook/wa/<string:connector_uuid>', auth='public', type='json', method=['OPTIONS', 'POST'], csrf=False)
    def webhook_qiscuss(self, connector_uuid, **post):
        ''' Connector searched for according to 'connector_uuid'. '''
        # log_request()
        parse_ttype = {'chat': 'text', 'ptt': 'audio', 'document': 'file',
                       'contacts': 'contact', 'voice': 'audio'}
        try:
            body = request.jsonrequest
            # if request.httprequest.method == 'POST':
            #     data = json.loads(request.httprequest.data)
            #     json_object = json.dumps(data)
            #     body = json.loads(json_object)

            # _logger.info("\nResult from Webhook: %s" % (body))
            if body:
                Conversation = request.env['acrux.chat.conversation'].sudo()
                connector_id = get_connector(connector_uuid)
                if not connector_id:
                    return Response(status=404)

                if 'contacts' in body:
                    Contacts = body.get('contacts')  # old - new
                    for contact in Contacts:
                        # _logger.info("Contacts from Webhook: %s" % (contact))
                        name = contact.get('profile').get('name')
                        room_id = contact.get('wa_id')
                        room_name = contact.get('profile').get('name')
                    # conv_id = Conversation.search([('number', '=', '+' + room_id),
                    #                                ('connector_id', '=', connector_id.id)])
                    # return Response(status=200)
                # ack = body.get('ack', [])  # delivered - viewed
                # for data in ack:
                #     return Response(status=200)
                if 'messages' in body:
                    messages = body.get('messages', [])
                    for mess in messages:
                        number = mess.get('from')
                        ttype = mess.get('type')
                        ttype = parse_ttype.get(ttype, ttype)
                        msg_id = mess.get('id')
                        # TODO: contact
                        if ttype == 'text':
                            text = mess.get('text').get('body')
                        # elif ttype in ['image', 'audio', 'video', 'file']:
                        #     text = mess.get('image')('caption') or ttype
                        #     url = mess.get('body')
                        elif ttype == 'image':
                            text = mess.get('image').get('caption')
                        elif ttype == 'audio':
                            text = mess.get('voice').get('caption') or ttype
                        elif ttype == 'file':
                            text = mess.get('document').get('caption')
                        elif ttype == 'call_log':
                            ttype = 'text'
                            text = '[Call]'
                        elif ttype == 'contact':
                            contact_data = get_contact(mess.get('contacts'))
                            text = f'\n'.join(contact_data)
                        elif ttype == 'location':
                            addresses = [{
                                'address': mess.get('location').get('address'),
                                'latitude': mess.get('location').get('latitude'),
                                'longitude': mess.get('location').get('longitude'),
                                'name': mess.get('location').get('name'),
                                'url': mess.get('location').get('url')
                            }]
                            text = '\n'.join(addresses)
                        else:
                            ttype = 'text'
                            text = 'Not allowed, type %s' % mess.get('type')
                        data = {
                            'ttype': ttype,
                            'connector_id': connector_id.id,
                            'name': name,
                            'number': '+' + number,
                            'message': text,
                            'url': None,
                            'room_id': room_id,
                            'room_name': room_name,
                            'comment_id': msg_id,
                            'message_id': msg_id,
                            'is_direct': False
                        }
                        Conversation.new_message(data)
            return Response(status=200)
        except Exception:
            request._cr.rollback()
            _logger.error('Error', exc_info=True)
            return Response(status=500)  # Internal Server Error

