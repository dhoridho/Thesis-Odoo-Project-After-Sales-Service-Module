# -*- coding: utf-8 -*-
from odoo import models, api, fields


class QiscussAutoAnswer(models.Model):
    _inherit = 'acrux.chat.default.answer'

    template_id = fields.Many2one('qiscus.template', 'Template ID', ondelete='cascade')
    default_answer_type = fields.Selection([('text', 'Text'), ('image', 'Image'),
                              ('video', 'Video'), ('file', 'File'), ('location', 'Location')],
                             string='Type', required=True, default='text')

    @api.onchange('default_answer_type')
    def _onchange_default_answer_type(self):
        if self.default_answer_type:
            self.ttype = self.default_answer_type