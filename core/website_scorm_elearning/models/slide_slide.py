# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import os
import base64
import zipfile
import tempfile
import shutil
from werkzeug import urls
from odoo.http import request
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import url_for


class SlidePartnerRelation(models.Model):
    _inherit = 'slide.slide.partner'

    lms_session_info_ids = fields.One2many('lms.session.info', 'slide_partner_id', 'LMS Session Info')
    lms_scorm_karma = fields.Integer("Scorm Karma")


class LmsSessionInfo(models.Model):
    _name = 'lms.session.info'

    name = fields.Char("Name")
    value = fields.Char("Value")
    slide_partner_id = fields.Many2one('slide.slide.partner')


class Channel(models.Model):
    """ A channel is a container of slides. """
    _inherit = 'slide.channel'

    nbr_scorm = fields.Integer("Number of Scorms", compute="_compute_slides_statistics", store=True)
    nbr_sharepoint = fields.Integer("Number of Sharepoints", compute="_compute_slides_statistics", store=True)

    @api.depends('slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.completion_time',
                 'slide_ids.likes', 'slide_ids.dislikes', 'slide_ids.total_views', 'slide_ids.is_category', 'slide_ids.active')
    def _compute_slides_statistics(self):
        super(Channel, self)._compute_slides_statistics()


class Slide(models.Model):
    _inherit = 'slide.slide'

    slide_type = fields.Selection(
        selection_add=[('scorm', 'Scorm')], ondelete={'scorm': 'set default'})
    scorm_data = fields.Many2many('ir.attachment')
    nbr_scorm = fields.Integer("Number of Scorms", compute="_compute_slides_statistics", store=True)
    nbr_sharepoint = fields.Integer("Number of Sharepoints", compute="_compute_slides_statistics", store=True)
    filename = fields.Char()
    embed_code = fields.Text('Embed Code', readonly=True, compute='_compute_embed_code')
    scorm_version = fields.Selection([
        ('scorm11', 'Scorm 1.1/1.2'),
        ('scorm2004', 'Scorm 2004 Edition')
    ], default="scorm11")
    scorm_passed_xp = fields.Integer("Scorm Passed Xp")
    scorm_completed_xp = fields.Integer("Scorm Completed Xp")

    @api.depends('slide_ids.sequence', 'slide_ids.slide_type', 'slide_ids.is_published', 'slide_ids.is_category')
    def _compute_slides_statistics(self):
        super(Slide, self)._compute_slides_statistics()

    def _compute_quiz_info(self, target_partner, quiz_done=False):
        res = super(Slide, self)._compute_quiz_info(target_partner)
        for slide in self:
            slide_partner_id = self.env['slide.slide.partner'].sudo().search([
                ('slide_id', '=', slide.id),
                ('partner_id', '=', target_partner.id)
            ], limit=1)
            if res[slide.id].get('quiz_karma_won'):
                res[slide.id]['quiz_karma_won'] += slide_partner_id.lms_scorm_karma
            else:
                res[slide.id]['quiz_karma_won'] = slide_partner_id.lms_scorm_karma
        return res

    @api.onchange('scorm_data')
    def _on_change_scorm_data(self):
        if self.scorm_data:
            if len(self.scorm_data) > 1:
                raise ValidationError(_("Only one scorm package allowed per slide."))
            tmp = self.scorm_data.name.split('.')
            ext = tmp[len(tmp) - 1]
            if ext != 'zip':
                raise ValidationError(_("The file must be a zip file.!!"))
            self.read_files_from_zip()
        else:
            if self.filename:
                folder_dir = self.filename.split('scorm')[-1].split('/')[1]
                path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
                target_dir = '/'.join(p for p in path.split('/')[:len(path.split('/')) - 1]) + '/static/media/scorm/' + folder_dir
                if os.path.isdir(target_dir):
                    shutil.rmtree(target_dir)

    @api.depends('document_id', 'slide_type', 'mime_type')
    def _compute_embed_code(self):
        for rec in self:
            if rec.slide_type == 'scorm' and rec.scorm_data:
                rec.embed_code = "<iframe src='%s' allowFullScreen='true' frameborder='0'></iframe>" % (rec.filename)
            else:
                res = super(Slide, rec)._compute_embed_code()
                return res

    def read_files_from_zip(self):
        file = base64.decodebytes(self.scorm_data.datas)
        fobj = tempfile.NamedTemporaryFile(delete=False)
        fname = fobj.name
        fobj.write(file)
        zipzip = self.scorm_data.datas
        f = open(fname, 'r+b')
        f.write(base64.b64decode(zipzip))
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        with zipfile.ZipFile(fobj, 'r') as zipObj:
            listOfFileNames = zipObj.namelist()
            html_file_name = ''
            package_name = ''
            html_file_name = list(filter(lambda x: 'index.html' in x, listOfFileNames))
            if not html_file_name:
                html_file_name = list(filter(lambda x: 'index_lms.html' in x, listOfFileNames))
                if not html_file_name:
                    html_file_name = list(filter(lambda x: 'story.html' in x, listOfFileNames))
            # for fileName in sorted(listOfFileNames):
            #     filename = fileName.split('/')
            #     package_name = self.scorm_data.name.split('.')[0]
            #     if 'index.html' in filename:
            #         html_file_name = '/'.join(filename)
            #         break
            #     elif 'index_lms.html' in filename:
            #         html_file_name = '/'.join(filename)
            #         break
            #     elif 'story.html' in filename:
            #         html_file_name = '/'.join(filename)
            #         break
            source_dir = '/'.join(p for p in path.split('/')[:len(path.split('/')) - 1]) + '/static/media/scorm/' + str(package_name)
            zipObj.extractall(source_dir)
            self.filename = '/website_scorm_elearning/static/media/scorm/%s/%s' % (str(package_name), html_file_name[0] if len(html_file_name) > 0 else None)
        f.close()
