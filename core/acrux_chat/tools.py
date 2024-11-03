# -*- coding: utf-8 -*-
import base64
import codecs
import io
import json
import requests
import logging
import pytz
from datetime import datetime, timedelta
import phonenumbers
from PIL import Image
from odoo import fields, _
from odoo.exceptions import UserError
from odoo.tools import image_process, image_to_base64, DEFAULT_SERVER_DATETIME_FORMAT
_logger = logging.getLogger(__name__)

TIMEOUT = (10, 20)
DEFAULT_IMAGE = 'placeholder.png'
DEFAULT_IMAGE_URL = '/web/static/src/img/' + DEFAULT_IMAGE


def log_request_error(param, req=None):
    try:
        param = json.dumps(param, indent=4, sort_keys=True, ensure_ascii=False)[:1000]
        if req is not None:
            _logger.error('\nSTATUS: %s\nSEND: %s\nRESULT: %s' %
                          (req.status_code, req.request.headers, req.text and req.text[:1000]))
    except Exception as _e:
        pass
    _logger.error(param, exc_info=True)


def date2local(self, date_field):
    # date_out = fields.Datetime.context_timestamp(self, date_field)
    tz = self.env.context.get('tz') or self.env.user.tz
    if not tz:
        tz = 'Asia/Jakarta'
    date_out = fields.Datetime.context_timestamp(self.with_context(tz=tz), timestamp=date_field)
    _logger.info('result date2local: %s' % date_out)
    return date_out


def date2local_str(self, date_field, out='%Y-%m-%d %H:%M:%S'):
    local = date2local(self, date_field)
    return local.strftime(out)


def date_timedelta(minutes=False, days=False):
    '''
    :param minutes: integer
    :param days: integer
    :return: datetime
    '''
    assert not(minutes and days), 'minutes or days please (as integer).'
    minutes = minutes or days * 24 * 60
    ret = datetime.now() + timedelta(minutes=minutes)
    return ret


def date_delta_seconds(date_field1, date_field2='now'):
    if not date_field1 or not date_field2:
        return 0
    d1 = datetime.strptime(date_field1, DEFAULT_SERVER_DATETIME_FORMAT)
    if date_field2 == 'now':
        d2 = datetime.now()
    else:
        d2 = datetime.strptime(date_field2, DEFAULT_SERVER_DATETIME_FORMAT)
    return int(abs((d1 - d2).total_seconds()))


def get_binary_attach(env, model, res_id, field, fields_ret=['mimetype']):
    attach = env['ir.attachment'].sudo().search_read(
        domain=[('res_model', '=', model), ('res_id', '=', res_id),
                ('res_field', '=', field)], fields=fields_ret,
        limit=1)
    return attach and attach[0]


def get_image_url(self, res_id, res_id_field, link_field='image_128', put_default=True):
    ''' get url from model image '''
    if res_id_field:
        unique = date2local_str(self, res_id.write_date, out='%d%m%Y%H%M%S')
        url = '/web/image?model=%s&id=%s&field=%s&unique=%s' % \
              (res_id._name, res_id.id, link_field, unique)
    else:
        url = False
        if put_default:
            url = DEFAULT_IMAGE_URL
    return url


def get_image_from_url(url):
    try:
        if not url or not isinstance(url, (str, bytes)) or not url.startswith('http'):
            return False
        r = requests.get(url, timeout=TIMEOUT)
        if not 200 <= r.status_code <= 299:
            return False
        datas = base64.b64encode(r.content)
        return datas.decode()
    except requests.exceptions.ConnectTimeout as _err:
        log_request_error(['get_image_from_url / ConnectTimeout', url])
        # raise Warning(_('Timeout error. Try again...'))
        return False
    except (requests.exceptions.HTTPError,
            requests.exceptions.RequestException,
            requests.exceptions.ConnectionError) as _err:
        log_request_error(['get_image_from_url / requests', url])
        # ex_type, ex_value, ex_traceback = sys.exc_info()
        # raise Warning(_('Error! Could not request image.\n%s') % ex_type)
        return False


def create_attachment_from_url(env, text, url, message_id):
    r = requests.get(url, timeout=TIMEOUT)
    datas = base64.b64encode(r.content)
    vals = {
        'name': text,
        'datas': datas,
        'store_fname': text,
        'res_model': 'acrux.chat.message',
        'res_id': message_id.id,
        'delete_old': True,
    }
    return env['ir.attachment'].sudo().create(vals)


def phone_info(env, number):
    '''
    :param number: valid number with code
    :return: phone_code, national_number, country_id
    '''
    try:
        number = number.lstrip(' +')
        nbr = phonenumbers.parse('+' + number)
        phone_code = nbr.country_code
        national_number = nbr.national_number
        country_code = phonenumbers.phonenumberutil.region_code_for_country_code(phone_code)
        country_id = env['res.country'].search([('code', '=', country_code)], limit=1)
        return phone_code, national_number, country_id
    except Exception as _e:
        return False, False, False


def phone_format(number, country_id=None, formatted=False, raise_error=True):
    '''
    From WhatsApp (Is valid number): add +, Not country_id
        ( phone_format('+' + self.number) )
    Manual entry: del +, Add country_id
        ( phone_format(self.mobile.lstrip('+'), self.country_id) ) '''
    try:
        number = number.lstrip(' +')
        if country_id and len(country_id) == 1:
            code = country_id.phone_code
            region = country_id.code
        else:
            number = '+' + number
            code = None
            region = None
        nbr = phonenumbers.parse(number, region=region)
        if code and code != nbr.country_code:
            nbr = False
    except phonenumbers.phonenumberutil.NumberParseException as _e:
        nbr = False
    if nbr and not phonenumbers.is_valid_number(nbr):
        nbr = False
    if not nbr:
        if raise_error:
            raise UserError(str(number) + _(' Invalid number.'))
        else:
            return False
    if formatted:
        format_number = phonenumbers.format_number(nbr, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
    else:
        format_number = phonenumbers.format_number(nbr, phonenumbers.PhoneNumberFormat.E164)
    return format_number


def image2jpg(env, content):
    if not content:
        return False
    if isinstance(content, str):
        content = content.encode('ascii')

    config_size = env['ir.config_parameter'].sudo().get_param('acrux_image_resize', 500)
    if config_size == 'original':
        size = (0, 0)
    else:
        size = (min(int(config_size), 1024), min(int(config_size), 1024))
    try:
        ret = image_process(content, size=size, quality=80, output_format='JPEG')
    except IOError as _e:
        image_stream = io.BytesIO(codecs.decode(content, 'base64'))
        image = Image.open(image_stream)
        if image.mode == 'P':
            if 'transparency' in image.info:
                alpha = image.convert('RGBA').split()[-1]
                bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
                bg.paste(image, mask=alpha)
            image = image.convert('RGB')
        opt = {'format': 'JPEG', 'optimize': True, 'quality': 80}
        # stream = io.BytesIO()
        # image.save(stream, **opt)

        to_base64 = image_to_base64(image, **opt)
        ret = image_process(to_base64, size=size, quality=80, output_format='JPEG')
    except Exception as _e:
        ret = False
        _logger.error('Could not convert image to JPG.')

    return ret
