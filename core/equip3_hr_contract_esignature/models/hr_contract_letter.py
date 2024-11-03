# -*- coding: utf-8 -*-

from odoo import models, fields, api


class hrContract(models.Model):
    _inherit = 'hr.contract.letter'
    
    notify_user = fields.Boolean()
    doc_process = fields.Boolean()
    custom_signature_placement = fields.Boolean()
    signature_drag_drop = fields.Boolean()
    pos_x = fields.Char()
    pos_y = fields.Char()
    signature_page = fields.Char()
    dimension = fields.Integer()