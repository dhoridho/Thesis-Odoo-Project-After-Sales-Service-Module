# -*- coding: utf-8 -*-
import base64
import json
import logging
import werkzeug
import math

from ast import literal_eval
from collections import defaultdict

from odoo import http, tools, _
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

_logger = logging.getLogger(__name__)

class WebsiteSlides(WebsiteSlides):
    def _build_channel_domain(self, base_domain, slide_type=None, my=False, **post):
        search_term = post.get('search')
        search_term_by = post.get('search_course_by')
        tags = self._extract_channel_tag_search(**post)

        domain = base_domain
        if search_term and search_term_by == "by_courses":
            domain = expression.AND([
                domain,
                ['|', ('name', 'ilike', search_term), ('description', 'ilike', search_term)]])

        if tags:
            # Group by group_id
            grouped_tags = defaultdict(list)
            for tag in tags:
                grouped_tags[tag.group_id].append(tag)

            # OR inside a group, AND between groups.
            group_domain_list = []
            for group in grouped_tags:
                group_domain_list.append([('tag_ids', 'in', [tag.id for tag in grouped_tags[group]])])

            domain = expression.AND([domain, *group_domain_list])

        if slide_type and 'nbr_%s' % slide_type in request.env['slide.channel']:
            domain = expression.AND([domain, [('nbr_%s' % slide_type, '>', 0)]])

        if my:
            domain = expression.AND([domain, [('partner_ids', '=', request.env.user.partner_id.id)]])
        return domain

    @http.route('/slides/all', type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_type=None, my=False, **post):
        """ Home page displaying a list of courses displayed according to some
        criterion and search terms.

          :param string slide_type: if provided, filter the course to contain at
           least one slide of type 'slide_type'. Used notably to display courses
           with certifications;
          :param bool my: if provided, filter the slide.channels for which the
           current user is a member of
          :param dict post: post parameters, including

           * ``search``: filter on course description / name;
           * ``channel_tag_id``: filter on courses containing this tag;
           * ``channel_tag_group_id_<id>``: filter on courses containing this tag
             in the tag group given by <id> (used in navigation based on tag group);
        """
        domain = request.website.website_domain()
        domain = self._build_channel_domain(domain, slide_type=slide_type, my=my, **post)

        order = self._channel_order_by_criterion.get(post.get('sorting'))

        channels = request.env['slide.channel'].search(domain, order=order)

        tag_groups = request.env['slide.channel.tag.group'].search(
            ['&', ('tag_ids', '!=', False), ('website_published', '=', True)])
        search_tags = self._extract_channel_tag_search(**post)

        search_term_by = post.get('search_course_by')
        search_term = post.get('search')
        if search_term_by == "by_content" and search_term:
            Content = request.env['slide.slide'].sudo().search([('channel_id','in',channels.ids),('name','ilike',search_term)]).ids
            contents = request.env['slide.slide'].sudo().browse(Content)
            return request.render("equip3_hr_elearning_extend.content_search_list", {
                'contents': contents,
            })

        values = self._prepare_user_values(**post)
        values.update({
            'channels': channels,
            'tag_groups': tag_groups,
            'search_term': post.get('search'),
            'search_slide_type': slide_type,
            'search_my': my,
            'search_tags': search_tags,
            'search_channel_tag_id': post.get('channel_tag_id'),
            'top3_users': self._get_top3_users(),
        })

        return request.render('website_slides.courses_all', values)