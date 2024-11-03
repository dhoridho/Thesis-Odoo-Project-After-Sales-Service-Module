# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.http import request


class SlideController(http.Controller):

    @http.route(['/website/publish/slide'], type='json', auth="user", website=True)
    def publish(self, id):
        slide_id = request.env['slide.slide'].browse(id)
        return bool(slide_id.website_published)
    