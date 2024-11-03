# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models, _


class AdvertisementImages(models.Model):
    _name = "advertisement.images"
    _order = "sequence asc"

    name = fields.Char(string="Name")
    sequence = fields.Integer("Sequence")
    description = fields.Text(string="Description")
    ad_image = fields.Binary(string="Image")
    image_type = fields.Selection([('image','Image'), ('url','URL')], string="Image Type", default='image')
    file_type = fields.Selection([('image','Image'), ('video','Video')], string="File Type", default='image')
    video_type = fields.Selection([('video','Video'), ('url','URL')], string="Video Type", default='video')
    ad_video = fields.Binary(string="Video")
    video_url = fields.Char(string="URL")
    ace_video_url = fields.Char(string="URL")
    is_youtube_url = fields.Boolean("Is Youtube URL?")
    url = fields.Char(string="URL")
    ad_video_fname = fields.Char('AD Video Filename')
    image_duration = fields.Integer(string="Image duration(Sec.)", default=1)

    @api.model
    def create(self, vals):
        if vals.get('is_youtube_url') and vals.get('ace_video_url'):
            if vals['is_youtube_url'] and len(vals['ace_video_url']) != 0:
                videoUrl = vals['ace_video_url']
                embedUrl = re.sub(r"(?ism).*?=(.*?)$", r"https://www.youtube.com/embed/\1", videoUrl)
                vals['video_url'] = embedUrl
        return super(AdvertisementImages, self).create(vals)

    def write(self, vals):
        if vals.get('is_youtube_url') and vals.get('ace_video_url'):
            if vals['is_youtube_url'] != '' and vals['ace_video_url']:
                videoUrl = vals['ace_video_url']
                embedUrl = re.sub(r"(?ism).*?=(.*?)$", r"https://www.youtube.com/embed/\1", videoUrl)
                vals['video_url'] = embedUrl
        elif vals.get('ace_video_url') and self.is_youtube_url:
            videoUrl = vals['ace_video_url']
            embedUrl = re.sub(r"(?ism).*?=(.*?)$", r"https://www.youtube.com/embed/\1", videoUrl)
            vals['video_url'] = embedUrl
        return super(AdvertisementImages, self).write(vals)