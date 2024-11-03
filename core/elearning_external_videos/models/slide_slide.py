# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import requests
import PyPDF2
from odoo import api, fields, models, _
from werkzeug import urls
import hashlib
import hmac
import time
from odoo.exceptions import Warning, UserError, AccessError, ValidationError
from odoo.http import request
from odoo.addons.http_routing.models.ir_http import url_for

class Channel(models.Model):
    """ A channel is a container of slides. """
    _inherit = 'slide.channel'
    _name = 'slide.channel'

    nbr_zoom_meeting = fields.Integer('Zoom Meeting', compute='_compute_slides_statistics', store=True)
    nbr_externalvideo = fields.Integer('External Videos (mp4)', compute='_compute_slides_statistics', store=True)
    nbr_googledrivevideo = fields.Integer('Google Drive Videos', compute='_compute_slides_statistics', store=True)
    nbr_clapprvideo = fields.Integer('External Videos (livestream and other supported)', compute='_compute_slides_statistics', store=True)
    nbr_vimeovideo = fields.Integer('Vimeo Videos', compute='_compute_slides_statistics', store=True)
    nbr_localvideo = fields.Integer('Local Video', compute='_compute_slides_statistics', store=True)
    nbr_presentation_g_drive = fields.Integer('Presentation - by Google Drive', compute='_compute_slides_statistics', store=True)
    nbr_sharepoint = fields.Integer('Sharepoint', compute='_compute_slides_statistics', store=True)

class Slide(models.Model):
    _inherit = 'slide.slide'
    _name = 'slide.slide'

    # content
    slide_type = fields.Selection(selection_add=[
        ('presentation_g_drive', 'Presentation - by Google Drive'),
        ('externalvideo', 'MP4 external video'),
        ('sharepoint', 'Sharepoint'),
        ('googledrivevideo', 'Google Drive video (put long id, example: 1oOIeTJwf4CWTRmcOONtTigfGDQpCMHPe)'),
        ('clapprvideo', 'External video (mp4, etc, livestream m3u8 and other supported formats)'),
        ('vimeovideo', 'Vimeo Video'),
        ('localvideo', 'Local Video (Ensure upload size limit in your server)'),
        ("zoom_meeting", "Zoom Meeting")],
        ondelete={'externalvideo': 'set default',
                  'presentation_g_drive': 'set default',
                  'googledrivevideo': 'set default',
                  'sharepoint': 'set default',
                  'clapprvideo': 'set default',
                  'vimeovideo': 'set default',
                  'localvideo': 'set default',
                  'zoom_meeting': 'set default'})
    external_url = fields.Char(string="External video URL")
    sharepoint_url = fields.Char(string="Sharepoint video URL")
    localvideo_mime_type = fields.Char(string="Localvideo mime type")
    zoom_meeting_ID = fields.Char(string="Meeting ID")
    zoom_meeting_name = fields.Char(string="Zoom Meeting Name", help="Paste Here Zoom Meeting Name")
    zoom_meeting_pwd = fields.Char(string="Zoom Meeting PWD", help="Paste Here Zoom Meeting PWD")
    nbr_zoom_meeting = fields.Integer('Zoom Meeting', compute='_compute_slides_statistics', store=True)
    nbr_externalvideo = fields.Integer('External Video', compute='_compute_slides_statistics', store=True)
    nbr_googledrivevideo = fields.Integer('Google Drive Video', compute='_compute_slides_statistics', store=True)
    nbr_clapprvideo = fields.Integer('External Video (livestream and other supported)', compute='_compute_slides_statistics', store=True)
    nbr_vimeovideo = fields.Integer('Vimeo Video', compute='_compute_slides_statistics', store=True)
    nbr_presentation_g_drive = fields.Integer('Presentation - by Google Drive', compute='_compute_slides_statistics', store=True)
    nbr_sharepoint = fields.Integer('Sharepoint', compute='_compute_slides_statistics', store=True)
    nbr_localvideo = fields.Integer('Local Video', compute='_compute_slides_statistics', store=True)
    g_drive_link = fields.Char(string="Google Drive Link")

    def generateZoomSignature(self, data):
        ts = int(round(time.time() * 1000)) - 30000;
        msg = data['apiKey'] + str(data['meetingNumber']) + str(ts) + str(data['role']);
        message = base64.b64encode(bytes(msg, 'utf-8'));
        # message = message.decode("utf-8");
        secret = bytes(data['apiSecret'], 'utf-8')
        hash = hmac.new(secret, message, hashlib.sha256);
        hash = base64.b64encode(hash.digest());
        hash = hash.decode("utf-8");
        tmpString = "%s.%s.%s.%s.%s" % (data['apiKey'], str(data['meetingNumber']), str(ts), str(data['role']), hash);
        signature = base64.b64encode(bytes(tmpString, "utf-8"));
        signature = signature.decode("utf-8");
        return signature.rstrip("=");

    @api.depends('document_id', 'slide_type', 'mime_type', 'external_url', 'g_drive_link')
    def _compute_embed_code(self):
        base_url = request and request.httprequest.url_root or self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        if base_url[-1] == '/':
            base_url = base_url[:-1]
        for record in self:
            if record.slide_type == 'scorm' and record.scorm_data:
                record.embed_code = "<iframe src='%s' allowFullScreen='true' frameborder='0'></iframe>" % (record.filename)
                continue
            if record.datas and (not record.document_id or record.slide_type in ['document', 'presentation']):
                slide_url = str('/slides/embed/%s?page=1' % record.id)
                record.embed_code = '<iframe src="%s" class="o_wslides_iframe_viewer" allowFullScreen="true" height="%s" width="%s" frameborder="0"></iframe>' % (slide_url, 315, 420)
            elif record.slide_type == 'video' and record.document_id:
                if not record.mime_type:
                    # embed youtube video
                    query = urls.url_parse(record.url).query
                    query = query + '&theme=light' if query else 'theme=light'
                    record.embed_code = '<iframe src="//www.youtube-nocookie.com/embed/%s?%s" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id, query)
                else:
                    # embed google doc video
                    record.embed_code = '<iframe src="//drive.google.com/file/d/%s/preview" allowFullScreen="true" frameborder="0"></iframe>' % (record.document_id)
            else:
                record.embed_code = False

        for record in self:
            if record.slide_type == 'presentation_g_drive':
                content_url = 'https://drive.google.com/file/d/' + record.g_drive_link + '/preview'
                record.embed_code ='<iframe id="googleDrivePresentation' + str(record.id) + '" src="' + content_url + '"></iframe>'
            if record.slide_type == 'externalvideo':
                content_url = record.external_url
                record.embed_code = '<video class="external_video" controls controlsList="nodownload"><source src="' + content_url + '" type="video/mp4"/></video>'
            if record.slide_type == 'googledrivevideo':
                content_url = 'https://drive.google.com/file/d/' + record.external_url + '/preview'
                record.embed_code ='<div class="drivehidecontrols"></div><iframe id="googleDriveVideo' + str(record.id) + '" class="external_video" src="' + content_url + '" oncontextmenu="return false" onload="disableContext()"></iframe>'
            if record.slide_type == 'clapprvideo':
                content_url = record.external_url
                record.embed_code = content_url
            if record.slide_type == 'vimeovideo':
                vimeo_parse = self.parse_video_url(record.external_url)
                content_url = 'https://player.vimeo.com/video/' + vimeo_parse[1]
                record.embed_code = '<iframe class="vimeoVideo" src="' + content_url + '" allowfullscreen="allowfullscreen" mozallowfullscreen="mozallowfullscreen" msallowfullscreen="msallowfullscreen" oallowfullscreen="oallowfullscreen" webkitallowfullscreen="webkitallowfullscreen"></iframe>'
            if record.slide_type == 'zoom_meeting':
                config = self.env['ir.config_parameter'].sudo()
                config_elearning_zoom_integration = config.get_param('elearning_zoom_integration')
                if config_elearning_zoom_integration:
                    zoom_api_key = config.get_param('elearning_zoom_api_key')
                    zoom_api_secret = config.get_param('elearning_zoom_api_secret')
                    zoom_data = {'apiKey': zoom_api_key.strip(),
                                 'apiSecret': zoom_api_secret.strip(),
                                 'meetingNumber': record.zoom_meeting_ID.strip(),
                                 'role': 0}  # role 0 is atendee
                    zoom_signature = self.generateZoomSignature(zoom_data)
                    current_user_name = 'Username'
                    zoom_name = str(base64.b64encode(current_user_name.encode('utf-8')), 'utf-8')
                    content_url = '/elearning_external_videos/static/meeting.html?name=' + zoom_name + '&mn=' + record.zoom_meeting_ID.strip() + '&email=&pwd=' + record.zoom_meeting_pwd.strip() + '&role=0&lang=en-US&signature=' + zoom_signature + '&china=0&apiKey=' + zoom_api_key + ''
                    record.embed_code = '<!--<div class="hidecontrols"></div>--><iframe allow="microphone; camera; fullscreen" id="zoom_meeting_' + str(
                        record.id) + '" class="external_video" src="' + content_url + '" frameborder="0" wmode="transparent" oncontextmenu="return false"></iframe>'
                else:
                    raise ValidationError('You must enable Zoom Meetings in Elearning/Settings')
            if record.slide_type == 'localvideo':
                vals = {
                    "video/mp4": b'MPEG-4',
                    "video/webm": b'libVorbis',
                    "video/ogg": b'Ogg'
                }
                data = base64.b64decode(record.datas)

                for key, value in vals.items():
                    if data.find(value) != -1:
                        record.mime_type = key

                content_url = 'data:' + record.mime_type + ';base64,' + record.datas.decode("utf-8")
                record.embed_code = '<video class="local_video" controls controlsList="nodownload"><source src="' + content_url + '" type="' + record.mime_type + '"/></video>'

    def parse_video_url(self, url):
        url_obj = urls.url_parse(url)
        if url_obj.ascii_host == 'vimeo.com':
            if url_obj.path:
                url_path = url_obj.path[1:]
                splited = url_path.split('/')
                if len(splited) == 2:
                    url_path = splited[0] + '?h=' + splited[1]
                response = requests.get("https://vimeo.com/api/oembed.json?url=" + url)
            else:
                url_path = False
                response = False
            return ('vimeo', url_path if url_obj.path else False, response)

    @api.onchange('slide_type', 'external_url')
    def onchange_slide_type(self):
        for record in self:
            if record.slide_type == 'zoom_meeting':
                config = self.env['ir.config_parameter'].sudo()
                config_elearning_zoom_integration = config.get_param('elearning_zoom_integration')
                if not config_elearning_zoom_integration:
                    raise ValidationError('You must enable Zoom Meetings in Elearning/Settings')
            if record.slide_type == 'vimeovideo' and record.external_url:
                parse_url = self.parse_video_url(record.external_url)
                if parse_url[2]:
                    jsonResponse = parse_url[2].json()
                    if 'duration' in jsonResponse:
                        record.completion_time = jsonResponse['duration']/3600
                    else:
                        record.completion_time = 0
                    if 'title' in jsonResponse:
                        record.name = jsonResponse['title']
                    else:
                        record.name = 'Video with security restrictions (embed in this domain for example). Verify in your vimeo account or contact with video owner.'
                    if 'description' in jsonResponse:
                        record.description = jsonResponse['description']
                    else:
                        record.description = 'Video with security restrictions (embed in this domain for example). Verify in your vimeo account or contact with video owner.'
                    if 'thumbnail_url' in jsonResponse:
                        record.image_1920 = base64.b64encode(requests.get(jsonResponse['thumbnail_url']).content)
                    else:
                        record.image_1920 = False

    @api.onchange('datas')
    def _on_change_datas(self):
        #res = super(Slide, self)._on_change_datas()
        vals = {
            "video/mp4": b'MPEG-4',
            "video/webm": b'libVorbis',
            "video/ogg": b'Ogg'
        }
        if self.datas:
            data = base64.b64decode(self.datas)
            if data.startswith(b'%PDF-'):
                pdf = PyPDF2.PdfFileReader(io.BytesIO(data), overwriteWarnings=False)
                self.completion_time = (5 * len(pdf.pages)) / 60
            else:
                if self.slide_type == 'infographic':
                    self.image_1920 = self.datas
                    self.datas = None
                    return
                for key, value in vals.items():
                    if data.find(value) != -1:
                        self.mime_type = key
                if self.slide_type == 'localvideo':
                    if self.mime_type not in ["video/mp4", "video/webm", "video/ogg"]:
                        self.datas = False
                        #self.mime_type = False
                        return {
                            'warning': {
                                'title': 'Warning!',
                                'message': 'The media file format is not supported. Please upload only mp4, ogg or webm files.'
                            }
                        }
        #return res
