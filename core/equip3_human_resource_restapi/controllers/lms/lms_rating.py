from datetime import datetime, timedelta
from itertools import count
from odoo.http import route,request
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT,consteq, plaintext2html,html2plaintext
import json
from ....restapi.controllers.helper import *
from werkzeug.exceptions import NotFound, Forbidden
from odoo.addons.portal.controllers.mail import *


def _check_special_access(res_model, res_id, token='', _hash='', pid=False):
    record = request.env[res_model].browse(res_id).sudo()
    if token:  # Token Case: token is the global one of the document
        token_field = request.env[res_model]._mail_post_token_field
        return (token and record and consteq(record[token_field], token))
    elif _hash and pid:  # Signed Token Case: hash implies token is signed by partner pid
        return consteq(_hash, record._sign_token(pid))
    else:
        raise Forbidden()

def _message_post_helper(res_model, res_id, message, token='', _hash=False, pid=False, nosubscribe=True, **kw):
    """ Generic chatter function, allowing to write on *any* object that inherits mail.thread. We
        distinguish 2 cases:
            1/ If a token is specified, all logged in users will be able to write a message regardless
            of access rights; if the user is the public user, the message will be posted under the name
            of the partner_id of the object (or the public user if there is no partner_id on the object).

            2/ If a signed token is specified (`hash`) and also a partner_id (`pid`), all post message will
            be done under the name of the partner_id (as it is signed). This should be used to avoid leaking
            token to all users.

        Required parameters
        :param string res_model: model name of the object
        :param int res_id: id of the object
        :param string message: content of the message

        Optional keywords arguments:
        :param string token: access token if the object's model uses some kind of public access
                             using tokens (usually a uuid4) to bypass access rules
        :param string hash: signed token by a partner if model uses some token field to bypass access right
                            post messages.
        :param string pid: identifier of the res.partner used to sign the hash
        :param bool nosubscribe: set False if you want the partner to be set as follower of the object when posting (default to True)

        The rest of the kwargs are passed on to message_post()
    """
    record = request.env[res_model].browse(res_id)

    # check if user can post with special token/signed token. The "else" will try to post message with the
    # current user access rights (_mail_post_access use case).
    if token or (_hash and pid):
        pid = int(pid) if pid else False
        if _check_special_access(res_model, res_id, token=token, _hash=_hash, pid=pid):
            record = record.sudo()
        else:
            raise Forbidden()

    # deduce author of message
    author_id = request.env.user.partner_id.id if request.env.user.partner_id else False

    # Token Case: author is document customer (if not logged) or itself even if user has not the access
    if token:
        if request.env.user._is_public():
            # TODO : After adding the pid and sign_token in access_url when send invoice by email, remove this line
            # TODO : Author must be Public User (to rename to 'Anonymous')
            author_id = record.partner_id.id if hasattr(record, 'partner_id') and record.partner_id.id else author_id
        else:
            if not author_id:
                raise NotFound()
    # Signed Token Case: author_id is forced
    elif _hash and pid:
        author_id = pid

    email_from = None
    if author_id and 'email_from' not in kw:
        partner = request.env['res.partner'].sudo().browse(author_id)
        email_from = partner.email_formatted if partner.email else None

    message_post_args = dict(
        body=message,
        message_type=kw.pop('message_type', "comment"),
        subtype_xmlid=kw.pop('subtype_xmlid', "mail.mt_comment"),
        author_id=author_id,
        **kw
    )

    # This is necessary as mail.message checks the presence
    # of the key to compute its default email from
    if email_from:
        message_post_args['email_from'] = email_from

    return record.with_context(mail_create_nosubscribe=nosubscribe).message_post(**message_post_args)

class Equip3HumanResourceLmsRating(PortalChatter,RestApi):
    @http.route(['/api/lms/forum/rating/create'],type='json', auth="user", methods=['POST'])
    def post_create_lms_rating(self, **kw):
        res_model = 'slide.channel'
        request_data = request.jsonrequest
        message = request_data.get("message")
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        attachment_ids = []
        token_ids = []
        IrAttachment = request.env['ir.attachment']
        if request_data.get('attachment_ids'):
            for data_attachment in request_data.get('attachment_ids'):
                access_token = False
                if not request.env.user.has_group('base.group_user'):
                    IrAttachment = IrAttachment.sudo().with_context(binary_field_real_user=IrAttachment.env.user)
                    access_token = IrAttachment._generate_access_token()
                attachment = IrAttachment.create({
                    'name': data_attachment['filename'],
                    'datas': data_attachment['file'],
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'access_token': access_token,
                })
                token_ids.append(access_token)
                attachment_ids.append(attachment.id)
        res_id = int(request_data.get('slide_channel_id'))
        attachment_ids = [int(attachment_id) for attachment_id in attachment_ids]
        attachment_tokens = [attachment_token for attachment_token in token_ids if token_ids]
        self._portal_post_check_attachments(attachment_ids, attachment_tokens)
        if message or attachment_ids:
            if message:
                general_text =  message
                message = plaintext2html(message)
                
            post_values = {
                'res_model': res_model,
                'res_id': res_id,
                'message': message,
                'send_after_commit': False,
                'attachment_ids': False,
                "rating_value":request_data.get("rating"),
                "pid":request.env.user.partner_id.id,
                "rating_feedback":general_text
            }
            message = _message_post_helper(**post_values)
            if attachment_ids:
                record = request.env[res_model].browse(res_id)
                message_values = {'res_id': res_id, 'model': res_model}
                attachments = record._message_post_process_attachments([], attachment_ids, message_values)

                if attachments.get('attachment_ids'):
                    message.sudo().write(attachments)
                    
        slide_channel = request.env[res_model].sudo().browse(int(res_id))
        request.env.user.add_karma(slide_channel.karma_gen_channel_rank)
                    
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Create Rating Successful"
                                              })
    
    
    @http.route(['/api/lms/forum/rating/update'],type='json', auth="user", methods=['PUT'])
    def post_update_lms_rating(self, **kw):
        res_model = 'slide.channel'
        request_data = request.jsonrequest
        message = request_data.get("message")
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        
        attachment_ids = []
        token_ids = []
        IrAttachment = request.env['ir.attachment']
        if request_data.get('attachment_ids'):
            for data_attachment in request_data.get('attachment_ids'):
                access_token = False
                if not request.env.user.has_group('base.group_user'):
                    IrAttachment = IrAttachment.sudo().with_context(binary_field_real_user=IrAttachment.env.user)
                    access_token = IrAttachment._generate_access_token()
                attachment = IrAttachment.create({
                    'name': data_attachment['filename'],
                    'datas': data_attachment['file'],
                    'res_model': 'mail.compose.message',
                    'res_id': 0,
                    'access_token': access_token,
                })
                token_ids.append(access_token)
                attachment_ids.append(attachment.id)
        res_id = int(request_data.get('slide_channel_id'))
        attachment_ids = [int(attachment_id) for attachment_id in attachment_ids]
        attachment_tokens = [attachment_token for attachment_token in token_ids if token_ids]
        self._portal_post_check_attachments(attachment_ids, attachment_tokens)        
        message_id = int(request_data.get('message_id'))
        message_body = plaintext2html(message)
        domain = [
            ('model', '=', res_model),
            ('res_id', '=', res_id),
            ('is_internal', '=', False),
            ('author_id', '=', request.env.user.partner_id.id),
            ('message_type', '=', 'comment'),
            ('id', '=', message_id)
        ]  # restrict to the given message_id
        message = request.env['mail.message'].search(domain, limit=1)
        if not message:
            return self.update_create_failed() 
        message.sudo().write({
            'body': message_body,
            'attachment_ids': [(6,0, [aid]) for aid in attachment_ids],
        })
        if request_data.get('rating'):
            domain = [('res_model', '=', res_model), ('res_id', '=', res_id), ('is_internal', '=', False), ('message_id', '=', message.id)]
            rating = request.env['rating.rating'].sudo().search(domain, order='write_date DESC', limit=1)
            rating.write({
                'rating': float(request_data.get('rating')),
                'feedback': html2plaintext(message.body),
            })
        
        return self.get_response(200, '200', {"code":200, 
                                              "message":"Update Rating Successful"
                                              })   
        
