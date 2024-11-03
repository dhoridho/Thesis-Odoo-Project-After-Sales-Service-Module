import sys
import json
import logging
import requests
from odoo import _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)
TIMEOUT = (10, 20)


def log_request_error(param, req=None):
    try:
        param = json.dumps(param, indent=4, sort_keys=True, ensure_ascii=False)[:1000]
        if req is not None:
            _logger.error('\nSTATUS: %s\nSEND: %s\nRESULT: %s' % (req.status_code, req.request.headers, req.text and req.text[:1000]))
    except Exception as e:
        pass
    _logger.error(param, exc_info=True)


def ca_get_endpoint(self, resource_path):
    api_key = self.env['ir.config_parameter'].sudo().get_param('chat.api.token')
    end_point = self.env['ir.config_parameter'].sudo().get_param('chat.api.url')
    return '%s/%s?token=%s' % (end_point.strip('/'), resource_path, api_key)


def ca_request(self, req_type, path, param={}, timeout=False):
    
    def response_handle_error(req):
        error = False
        try:
            ret = req.json()
        except ValueError as _e:
            ret = {}
        err = ret.get('error', 'Send Error')
        message = ret.get('message', 'Send Error')
        if req.status_code == 401:
            error = err
        elif not 200 <= req.status_code <= 299:
            error = err or message
        if error:
            log_request_error([error, req_type, path, param], req)
            raise ValidationError(error)
        return ret
    
    result = {}
    timeout = timeout or TIMEOUT
    url = ca_get_endpoint(self, path)
    header = {'Accept': 'application/json'}
    req = False
    try:
        if req_type == 'post':
            data = json.dumps(param)
            header.update({'Content-Type': 'application/json'})
            w = len(data) / 20000
            timeout = (int(max(10, w)), 20)
            try:
                req = requests.post(url, data=data, headers=header, timeout=timeout, verify=True)
            except ConnectionError:
                raise ValidationError(_('Not connect to API Chat Server. Limit reached or not active.'))
            result = response_handle_error(req)
        elif req_type == 'get':
            if path == 'qr_code':
                header = {'Accept': 'image/png', 'Content-Type': 'application/json'}
            try:
                req = requests.get(url, params=param, headers=header, timeout=timeout, verify=True)
            except ConnectionError:
                raise ValidationError(_('Not connect to API Chat Server. Limit reached or not active.'))
            result = response_handle_error(req)
    except requests.exceptions.SSLError as _err:
        log_request_error(['SSLError', req_type, path, param])
        raise UserError(_('Error! Could not connect to Chat-Api server.\nPlease in the connector settings, set the parameter "Verify" to false by unchecking it and try again.'))
    except requests.exceptions.ConnectTimeout as _err:
        log_request_error(['ConnectTimeout', req_type, path, param])
        raise UserError(_('Timeout error. Try again...'))
    except (requests.exceptions.HTTPError, requests.exceptions.RequestException, requests.exceptions.ConnectionError) as _err:
        log_request_error(['requests', req_type, path, param])
        ex_type, _ex_value, _ex_traceback = sys.exc_info()
        raise UserError(_('Error! Could not connect to Chat-Api account.\n%s') % ex_type)
    print_result(req_type, url, result, param, req)
    return result

def print_result(req_type, url, result, param, req):
    try:
        Host = request.httprequest.headers.get('Host')
        if Host.startswith('localhost'):
            print('status =', req and req.status_code or 'except request')
            print(request.httprequest.headers)
            print('%%%% => %s %s' % (req_type.upper(), url))
            if param:
                body = param.get('body', False)
                if body:
                    param['body'] = body[0:100]
                data = json.dumps(param, indent=2, sort_keys=True)
                data = data.replace('\\"', "'")
                print(data)
            print('################ resultado')
            data = json.dumps(result, indent=2, sort_keys=True)
            print(data)
    except RuntimeError:
        pass
