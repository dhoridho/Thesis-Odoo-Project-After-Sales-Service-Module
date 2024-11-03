# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import functools
from odoo import http, tools, SUPERUSER_ID
from odoo.http import Response, request
from odoo.service import model
import json
import werkzeug
import urllib
from datetime import datetime, timedelta
from oauthlib.common import add_params_to_uri
from odoo.tools.safe_eval import safe_eval
from odoo.addons.web.controllers.main import WebClient
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, date_utils
from odoo.exceptions import UserError
import odoo
import base64
import sys
import logging
import binascii
import requests
from .deffered import DeferredException
import base64
import math
PAGE_DATA_LIMIT = 20


_logger = logging.getLogger(__name__)


def authenticate(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        auth, user, invalid = RestApi().valid_authentication(kwargs)
        if not user or invalid:
            return RestApi().get_response(401, str(401), {'code': 401, 'message': 'Authentication required'})
        return func(*args, **kwargs) 
    return wrapper

class RestApi(http.Controller):

    _VALIDATION_FIELDS = ['oauth_version',
        'oauth_consumer_key',
        'oauth_signature_method',
        'oauth_nonce',
        'oauth_timestamp',
    ]
    _METHOD_WITH_ARGS_KWARGS = dict(
    search = dict(arg=['domain',], kwargs=['offset', 'limit', 'order', 'context']),
    search_read = dict(arg=['domain',], kwargs=['fields','offset', 'limit', 'order', 'context']),
    read = dict(arg=['fields'], kwargs=['context']),
    read_group = dict(arg=['domain', 'fields', 'groupby',], kwargs=['offset', 'limit', 'context', 'orderby', 'lazy'],),
    default_get = dict(arg=['fields_list'], kwargs=['context'],),
    user_has_groups = dict(arg=['groups'], kwargs=['context'],),
    search_count = dict(arg=['domain'], kwargs=['context'],),
    name_create = dict(arg=['name',], kwargs=['context'],),
    name_search = dict(arg=[], kwargs=['name', 'args', 'operator', 'limit', 'context'],),
    fields_get = dict(arg=[], kwargs=['allfields','context','write_access','attributes',],),
    onchange = dict(arg=['values','field_name','field_onchange',], kwargs=['context'],),
    export_data = dict(arg=['fields_to_export',], kwargs=['raw_data', 'context'],),
    copy = dict(arg=['id',], kwargs=['default', 'context'],),
    check_field_access_rights = dict(arg=['operation', 'fields'], kwargs=['default', 'context'],),
    check_access_rights = dict(arg=['operation',], kwargs=['raise_exception', 'context'],),
    check_access_rule = dict(arg=['operation',], kwargs=['context'],),
    import_data = dict(arg=['fields', 'datas',], kwargs=['mode','current_module','noupdate','filename', 'context'],),)

    _HTTP_METHODS = dict(
    POST= 'create',
    GET= 'search_read',
    PUT= 'write',
    DELETE= 'unlink'
    )

    _GET_METHODS = ['search','search_read','read_group','search_count',]

    _HTTP_REQUEST_CODE = dict(
        create=201,
        write=200,
        search_read=200,
        unlink=200
        )
    def name_selection_groups(self,ids):
        return 'sel_groups_' + '_'.join(str(it) for it in ids)
    
    def get_group(self,xml_id):
        Group = request.env['res.groups'].sudo()
        for app, kind, gs, category_name in Group.get_groups_by_application():
            gs_list = [gs]
            group_ids = []
            if app.xml_id == xml_id:
                for gs in gs_list:
                    field_name = self.name_selection_groups(gs.ids)
                    for g in gs:
                        domain = [('model', '=', 'res.groups'), ('res_id', '=', g.id)]
                        model_data = request.env['ir.model.data'].search(domain, limit=1)
                        xml_id = "%s.%s" % (model_data.module, model_data.name)
                        group_ids.append({'id':g.id,
                                          'role_name':g.name,
                                          'hash_role':request.env.user.has_group(xml_id)
                                          })
                    return group_ids
        return group_ids

    def get_attatchment(self,model,resourse_id):
        attachment_list_ids = []
        attachment = request.env['ir.attachment'].search([('res_model','=',model),('res_id','=',resourse_id)])
        if attachment:
            for data in attachment:
                attachment_list_ids.append(
                    {   "id":data.id,
                        'name':data.name,
                        'datas':data.datas.decode("utf-8"),
                        "create_date":data.create_date.strftime("%m/%d/%Y")
                                            
                                            })
        return attachment_list_ids
    
    
    def update_one2many(self,parent_id_domain,obj,list_to_update):
        result = []
        to_delete = []
        if list_to_update:
            if all('id' not in data for data in list_to_update):
                data_delete = request.env[obj].search(parent_id_domain)
                if data_delete:
                    data_delete.unlink()         
            
            for data in list_to_update:
                if 'id' in data:
                    result.append((1,data['id'],data['values']))
                    to_delete.append(data['id'])
                elif not 'id' in data and 'values' in data:
                    result.append((0,0,data['values']))
                
            if to_delete:
                parent_id_domain.append(('id','not in',to_delete))
                data_delete = request.env[obj].search(parent_id_domain)
                data_delete.unlink()
        else:
            data_delete = request.env[obj].search(parent_id_domain)
            if data_delete:
                data_delete.unlink()
        return result
        
    
    def convert_time_to_float(self,time):
        if time:
            vals = time.split(':')
            t, hours = divmod(float(vals[0]), 24)
            t, minutes = divmod(float(vals[1]), 60)
            minutes = minutes / 60.0
            time_float = hours + minutes  
        else:
            time_float = 0
        return time_float
    
    def get_limit_offset(self,page=1,limit=None):
        offset = 0
        if page > 1:
            if not limit:
                offset = (page * PAGE_DATA_LIMIT) - PAGE_DATA_LIMIT
            else:
                offset =  (page * limit) - limit
        return offset
    
    def get_total_page(self,total_item,limit):
        total_page = math.ceil(total_item/limit)
        return total_page
    
    def return_params(self):
        param  = request.httprequest.url
        query = requests.utils.urlparse(str(param)).query
        params = dict(x.split('=') for x in query.split('&'))
        return params
        
    def convert_one2many(self,obj,request_param,user):
        try:
            read_record = self.perform_request(obj, kwargs=request_param, user=user)
            response_data = json.loads(read_record.data)
            if not str(obj) in response_data:
                return [response_data]
            return response_data[obj]
        except json.decoder.JSONDecodeError as e:
            return read_record.data
       
         
    def record_not_found(self):
        return self.get_response(200, '200', {"code":200,
                                              "data":[]
                                              })
    def update_create_failed(self):
        return self.get_response(401, '401', {"code":401,
                                              "message":"update or create failed",
                                              "data":[]
                                              })
    @http.route(['/start'], \
        type="http", auth="public", csrf=False, website=True)
    def start_service(self, **kwargs):
        auth, user, invalid = self.valid_authentication(kwargs)
        if not auth or not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})
        return self.get_response(200, '200', {'client_id': auth[0].consumer_key,
            'client_secret': auth[0].consumer_secret,
            'host': request.httprequest.url_root,
            'database': request.cr.dbname})

    @http.route(['/restapi/1.0/common/version'], \
        type="http", auth="public", csrf=False, website=True)
    def call_version(self, **kwargs):
        version_info =  WebClient().version_info()
        return self.get_response(200, '200', version_info)

    @http.route(['/restapi/1.0/common/oauth2/authorize'], \
        type="http", auth="user", csrf=True, website=True)
    def auth(self, **kwargs):
        """
            Redirect to redirect uri attached with code and state,
            if request is valid.
        """
        obj = request.env['auth.auth'].sudo()
        auth_code = obj.generate_token()
        kwargs.update(request.httprequest.data or {})
        auth_auth = obj.search([('consumer_key', '=', kwargs.get('client_id'))])
        if not auth_auth:
            return self.get_response(401, '401', {"code":401, "message": "Invalid Credentials."})
        redirect_uri = False
        if kwargs.get('redirect_uri'):
            redirect_uri = urllib.parse.unquote(kwargs.get('redirect_uri'))
        if redirect_uri not in [uri.url for uri in auth_auth.redirect_uris]:
            return self.get_response(400, '400', {"code":400, "message": "redirect uri mismatch."})
        if auth_auth.user_id.id != request.env.uid:
            return self.get_response(401, '401', {"code":401, "message": "Invalid User."})
        auth_auth.auth_code_ids = [(0, 0, {'auth_code': auth_code, 'used': False})]
        return werkzeug.utils.redirect(add_params_to_uri(redirect_uri, {'code': auth_code, 'state': kwargs.get('state')}))

    @http.route(['/restapi/1.0/common/oauth2/access_token'], \
        type="http", auth="public", csrf=False, website=True)
    def auth_access(self, **kwargs):
        """
            Return Access Token and its validity,
            if authentication code or refresh code attached with request is valid
        """
        kwargs.update(request.httprequest.data or {})
        obj = request.env['auth.auth'].sudo()
        auth_code_obj = request.env['auth.auth.code'].sudo()
        access_token = obj.generate_token()
        access_token_validity = datetime.now() + timedelta(minutes=30)
        token_validity = (access_token_validity - datetime.now()).total_seconds()
        auth_auth = obj.search([('consumer_key', '=', kwargs.get('client_id'))])

        if not auth_auth:
            return self.get_response(401, '401', {"code":401, "message": "Invalid Credentials."})
        if kwargs.get('grant_type') == 'authorization_code':
            if not auth_auth.refresh_token:
                auth_auth.refresh_token = auth_auth.generate_token()
            auth_code = auth_code_obj.search([('auth_id', '=', auth_auth.id), ('auth_code', '=', kwargs.get('code'))])
            if not auth_code:
                return self.get_response(401, '401', {"code":401, "message": "Invalid Authentication Code."})
            elif auth_code and auth_code.used:
                return self.get_response(400, '400', {"code":400, "message": "Authentication code expired"})
            auth_code.used = True
        if kwargs.get('grant_type') == 'refresh_token':
            auth_auth = obj.search([('id', '=', auth_auth.id), ('refresh_token', '=', kwargs.get('refresh_token'))])
            if not auth_auth:
                return self.get_response(400, '400', {"code":400, "message": "Invalid Refresh Token."})

        auth_auth.access_token_ids = [(0, 0, {'access_token': access_token, 'access_token_validity': access_token_validity})]

        result = self.get_response(200, '200', {"access_token":access_token,
            "access_token_validity": int(round(token_validity)),
            "token_type": 'Bearer',
            'refresh_token': auth_auth.refresh_token,})
        if request.httprequest.headers.get('Accept') == 'application/json':
            result.mimetype = 'application/json'
        return result

    def get_response(self, status_code, status, data=None):
        """Returns Response Object with given status code and status"""
        response = Response()
        response.status = status
        if data:
            try:
                response.data = isinstance(data, str) and data or json.dumps(data)
                if request.httprequest.headers.get('Accept') == 'application/json':
                    response.mimetype = 'application/json'
            except Exception as e:
                response.data = str(data)
        response.status_code = status_code
        return response

    def _get_credentials(self, kwargs):
        """
            Parse the credentials from request header and query string
        """
        if request.httprequest.headers.get('Authorization'):        
            if 'Bearer' in request.httprequest.headers.get('Authorization'):
                params = {'access_token': request.httprequest.headers.get('Authorization').split(' ')[1]}
            else:
                headers = [header.strip(',') for header in request.httprequest.headers.get('Authorization').split(' ')]
                params = [k_v.split('=') for k_v in headers if len(k_v.split('='))==2]
                params = dict([(val[0], eval(val[1])) for val in params])
            kwargs.update(params)
        return kwargs

    def _check_credentials(self, kwargs):
        """
            Validates the authentication, If request is using OAuth1.
        """
        kwargs = self._get_credentials(kwargs)
        if not set(self._VALIDATION_FIELDS)<set(list(kwargs)):
            print(kwargs)
            return False, False, self.get_response(401, '401', {'error': {'code': '401', 'message': 'Authentication Required'}})
        auth_auth_obj = request.env['auth.auth']
        result, err_msg = auth_auth_obj.authentication(kwargs,
            request.httprequest.method,
            request.httprequest.base_url)
        if not result and err_msg:
            return False, False, self.get_response(401, '401', err_msg)
        key = kwargs['oauth_consumer_key']
        user = auth_auth_obj.get_authorize_user(key)
        if not user:
            return False, False, self.get_response(401, '401', {'error': {'code': '401', 'message': 'Authentication Required'}})
        return key, user, False

    @http.route(['/restapi/1.0/common/oauth1/request_token'], \
        type="http", auth="public", csrf=False, website=True)
    def auth_request_token(self, **kwargs):
        """
            Returns the Request token if request is valid
        """
        key, user, invalid = self._check_credentials(kwargs)
        if invalid:
            return invalid
        request_token = user.generate_token()
        request_token_secret = user.generate_token()
        user.request_token_ids = [(0, 0, dict(request_token = request_token,
            request_token_secret = request_token_secret,
            request_token_validity = datetime.now() + timedelta(hours=24),
            callback_uri = kwargs.get('oauth_callback')))]
        return self.get_response(200, '200', {
            "oauth_token": request_token,
            "oauth_token_secret": request_token_secret,
            })

    @http.route(['/restapi/1.0/common/oauth1/authorize'], \
        type="http", auth="user", csrf=False, website=True)
    def auth_authorize(self, **kwargs):
        """
            Redirect to redirect uri attached with code and state,
            if request is valid.
        """
        auth_obj = request.env['auth.auth']
        auth_request_token_obj = request.env['auth.request.token']
        if kwargs.get('oauth_token'):
            user = auth_obj.get_authorize_user_request_token(kwargs.get('oauth_token'))
            if user:
                request_token = auth_request_token_obj.get_request_token(kwargs.get('oauth_token'), auth=user)
                request_token.token_verifier = auth_request_token_obj.generate_verifier()
                if request.uid != user.user_id.id and request.uid != 3:
                    return self.get_response(400, '400', {'error': {'code': '400', 'message': 'You are not authorized user for these credentials.'}})
                if request_token.callback_uri:
                    return werkzeug.utils.redirect(add_params_to_uri(urllib.parse.unquote(request_token.callback_uri),{'oauth_verifier':request_token.token_verifier,'oauth_token':request_token.request_token}))
                else:
                    return self.get_response(200, '200', {'oauth_verifier':request_token.token_verifier,'oauth_token':request_token.request_token})
        return self.get_response(400, '400', {'error': {'code': '400', 'message': 'Insufficient Data'}})

    @http.route(['/restapi/1.0/common/oauth1/access_token'], \
        type="http", auth="public", csrf=False, website=True)
    def auth_access_token(self, **kwargs):
        """
            Returns Access Token,
            if request is valid.
        """
        auth_obj = request.env['auth.auth']
        auth_request_token_obj = request.env['auth.request.token']
        args = self._get_credentials(kwargs)
        user = auth_obj.get_authorize_user(args.get('oauth_consumer_key'))
        if not user:
            return self.get_response(401, '401', {'error': {'code': '401', 'message': 'Invalid Consumer Key & Secret'}})
        valid_request = auth_request_token_obj.is_valid_request(args.get('oauth_token'), args.get('oauth_verifier'), auth=user)
        if not valid_request:
            return self.get_response(401, '401', {'error': {'code': '401', 'message': 'Invalid Credentials'}})
        elif datetime.strptime(valid_request.request_token_validity.strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT) < datetime.strptime(datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT):
            return self.get_response(400, '400', {'error': {'code': '400', 'message': 'Request Token Expired'}})
        kwargs['for_access_token'] = True
        key, user, invalid = self._check_credentials(kwargs)
        if invalid:
            return invalid
        
        user.access_token = auth_obj.generate_token()
        user.access_token_secret = auth_obj.generate_token()
        new_token = request.env['auth.access.token'].sudo().create({'access_token':user.access_token,'auth_id':user.id,'access_token_validity':datetime.now() + timedelta(days=3)})
        request
      
        result = self.get_response(200, '200', {
            "oauth_token": user.access_token,
            "oauth_token_secret": user.access_token_secret,
            })
        if request.httprequest.headers.get('Accept') == 'application/json':
            result.mimetype = 'application/json'
        return result

    def valid_authentication(self, kwargs):
        user, auth = False, False
        credentials = self._get_credentials(kwargs)
        if kwargs.get('oauth_signature'):
            kwargs['for_request_data'] = True
            key, auth, invalid = self._check_credentials(kwargs)
            if invalid:
                return False, False, invalid
            user = auth.user_id
        elif credentials.get('access_token'):
            access_token = request.env['auth.access.token'].sudo().search([('access_token', '=', credentials['access_token'])], limit=1,order='id desc')
            if not access_token or datetime.strptime(access_token.access_token_validity.strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT) < datetime.strptime(datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT), DEFAULT_SERVER_DATETIME_FORMAT):
                return False, False, self.get_response(401, str(401), {'code': 401, 'message': 'Access Token Invalid'})
            user, auth = access_token.auth_id.user_id, access_token.auth_id
        elif not request.httprequest.headers.get('Authorization'):
            redirect_url = add_params_to_uri(request.httprequest.base_url, kwargs)
            return False, False, werkzeug.utils.redirect(add_params_to_uri('web/login', {'redirect': redirect_url}))
        return auth, user, False

    def evaluate(self, s):
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        try:
            return eval(s)
        except Exception as e:
            try:
                return json.loads(s)
            except Exception as e:
                return s

    def generate_report(self, xml_id, ids):
        self_reports = {}
        self_reports = {'result': False, 'state': False, 'exception': None}
        try:
            result, format = request.env.ref(xml_id).sudo()._render_qweb_pdf(ids)
            if not result:
                tb = sys.exc_info()
                self_reports['exception'] = DeferredException('RML is not available at specified location or not enough data to print!', tb)
            self_reports['result'] = result
            self_reports['format'] = format
            self_reports['state'] = True
            self_reports.update({'id': ids})
        except Exception as exception:
            if hasattr(exception, 'name') and hasattr(exception, 'value'):
                self_reports['exception'] = DeferredException(tools.ustr(exception.name), tools.ustr(exception.value))
            else:
                tb = sys.exc_info()
                self_reports['exception'] = DeferredException(tools.exception_to_unicode(exception), tb)
            self_reports['state'] = True

        exc = self_reports['exception']
        if exc:
            raise UserError('%s: %s' % (exc.message, exc.traceback))
        if self_reports['state']:
            if tools.config['reportgz']:
                import zlib
                res2 = zlib.compress(result)
            else:
                if isinstance(result, str):
                    res2 = result.encode('latin1', 'replace')
                else:
                    res2 = result
            if res2:
                self_reports['result'] = base64.b64encode(res2).decode('utf-8')
        return self_reports

    @http.route(['/restapi/1.0/report/<string:xml_id>/<int:id>',\
        '/restapi/1.0/report/<string:xml_id>'], \
        type="http", auth="public", csrf=False, website=True)
    def call_report(self, xml_id, id=None, **kwargs):
        """
            Authenticate Request. If its valid, Send report data in binary format
        """
        auth, user, invalid = self.valid_authentication(kwargs)
        ids = [id] if id else []

        if not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})

        if request.httprequest.data and type(self.evaluate(request.httprequest.data)) is dict:
            kwargs.update(self.evaluate(request.httprequest.data))

        if kwargs.get('ids'):
            ids.extend(type(kwargs['ids']) is list and kwargs['ids'] or kwargs['ids'].split(','))
            ids = list(map(self.evaluate, ids))
        datas = []
        try:
            if not self.evaluate(kwargs.get('group')):
                for id in ids:
                    data = self.generate_report(xml_id, id)
                    datas.append(data)
            else:
                data = self.generate_report(xml_id, ids)
                datas.append(data)

        except Exception as e:
            return self.get_response(403, '403', {'error': {'code': 403, 'message': e}})
        if datas and not len(datas)>1:
            datas = datas[0]
        return self.get_response(200, str(200), {'report': datas})

    @http.route(['/restapi/1.0/object/<string:object>/<string:method>',], \
        type="http", auth="public", csrf=False, website=True)
    def perform_model_request(self, object, method, **kwargs):
        auth, user, invalid = self.valid_authentication(kwargs)
        if not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})
        return self.perform_request(object, id=None, method=method, kwargs=kwargs, user=user)

    @http.route(['/restapi/1.0/object/<string:object>',\
        '/restapi/1.0/object/<string:object>/<int:id>',\
        '/restapi/1.0/object/<string:object>/<int:id>/<string:method>'], \
        type="http", auth="public", csrf=False, website=True)
    def perform_multi_request(self, object, id=None, method=None, **kwargs):
        auth, user, invalid = self.valid_authentication(kwargs)
        if not user or invalid:
            return self.get_response(401, str(401   ), {'code': 401, 'message': 'Authentication required'})
        return self.perform_request(object, id=id, method=method, kwargs=kwargs, user=user)

    def perform_request(self, object, method=None, id=None, kwargs={}, user=None):
        """
            Authenticate User. If valid, perform openration as per request.
        """
        datas = {}

        request_code, request_data = 200, {}
        ids, payload = [id] if id else [], {}
        arguments, k_arguments = [], {}

        if not method:
            method = self._HTTP_METHODS.get(request.httprequest.method)
            request_code = self._HTTP_REQUEST_CODE.get(method)
        if method in ('create', 'write'):
            for f in ['vals', 'args']:
                payload = kwargs.get(f) and self.evaluate(kwargs[f])
                if not payload:
                    payload = request.httprequest.data and self.evaluate(request.httprequest.data).get(f) or {}
                if payload:
                    break
            if not payload:
                payload = request.httprequest.data and self.evaluate(request.httprequest.data) or {}
            if payload:
                payload = type(payload) is list and payload[0] or payload

        if request.httprequest.data and type(self.evaluate(request.httprequest.data)) is dict:
            kwargs.update(self.evaluate(request.httprequest.data))

        if kwargs.get('ids'):
            ids.extend(type(kwargs['ids']) is list and kwargs['ids'] or kwargs['ids'].split(','))
            ids = list(map(self.evaluate, ids))
        if self._METHOD_WITH_ARGS_KWARGS.get(method):
            args = self._METHOD_WITH_ARGS_KWARGS.get(method)
            arguments.extend([self.evaluate(kwargs.get(arg)) for arg in args['arg']])
            k_arguments = dict([(arg, self.evaluate(kwargs[arg])) for arg in args['kwargs'] if kwargs.get(arg)])
            if method in self._GET_METHODS:
                if type(self.evaluate(kwargs.get('domain'))) is list and ids:
                    arguments[0].append(('id', 'in', ids))
                elif ids:
                    arguments[0] = [('id', 'in', ids)]
                elif not self.evaluate(kwargs.get('domain')):
                    arguments[0] = []
            elif ids:
                arguments.insert(0, ids)
        elif method in ('create', 'write'):
            arguments = [ids, payload] if ids else [payload]
            method = ids and 'write' or 'create'
            k_arguments = kwargs.get('context') and {'context': self.evaluate(kwargs['context'])} or {}
        else:
            if ids:
                arguments.append(ids)
            arguments.extend((kwargs.get('args') and self.evaluate(kwargs['args'])) or (request.httprequest.data and self.evaluate(request.httprequest.data).get('args')) or [])
            k_arguments = (kwargs.get('kwargs') and self.evaluate(kwargs['kwargs'])) or (request.httprequest.data and self.evaluate(request.httprequest.data).get('kwargs') or {})
        try:
            data = model.execute_kw(request.cr.dbname, user.id, object, method, arguments, kw=k_arguments)
            request.cr.commit()
            records = []
            context = dict(request._context)
            if k_arguments.get('context', False):
                context.update(k_arguments['context'])
            if method in ['create', 'write']:
                env_obj = request.env[object].with_context(context).sudo()
                if id:
                    data = env_obj.search_read([('id', '=', id)])
                elif kwargs.get('ids'):
                    data = env_obj.search_read([('id', 'in', kwargs['ids'].split(','))])
                else:
                    data = env_obj.search_read([('id', '=', data)])

            data_description = object

            if method == 'search_count':
                data_description = 'count'

            if method == 'check_access_rights':
                data_description = 'return'
            
            if data and isinstance(data, list):
                for val in data:
                    if isinstance(val, dict):
                        for v in list(val):
                            if isinstance(val[v], bytes):
                                val[v] = val[v].decode('utf-8')
                if isinstance(data[0], int) or len(data)>1:
                    datas.update({data_description: data})
                    
                elif not id and len(data) == 1:
                    datas.update({data_description: [data[0]]})
                else:
                    datas.update({data_description: data[0]})
                
            elif data:
                if method == 'unlink':
                    datas = {}
                else:
                    datas.update({data_description: data})
            else:
                if method == 'search_count':
                    datas.update({data_description: 0})
                    return self.get_response(request_code, str(request_code), datas)
            #     return self.get_response(404, '404', {'code': 404, 'message': 'Record not found'})

        except requests.exceptions.RequestException:
            return self.get_response(403, '403', {'code': 403, 'message': "Connection Error"})
        except Exception as e:
            return self.get_response(403, '403', {'error': {'code': 403, 'message': hasattr(e, 'message') and str(e.message) or hasattr(e, 'name') and e.name or e}})

        fields_list, boolean_list = [], []
        if object in datas.keys() and datas[object] and isinstance(datas[object], dict):
            for name in request.env[object]._fields.keys():
                field_id = request.env['ir.model.fields']._get(object, name)
                if field_id.ttype in ['char', 'selection', 'binary', 'date', 'datetime']:
                    fields_list.append(name)
                elif field_id.ttype == 'boolean':
                    boolean_list.append(name)
            for data in datas[object]:
                if data in fields_list and datas[object].get(data) == False:
                    datas[object].update({data: ''})

        datas = json.dumps(datas, default=date_utils.json_default)
        result = self.get_response(request_code, str(request_code), datas)
        if request.httprequest.headers.get('Accept') == 'application/json':
            result.mimetype = 'application/json'
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: