# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProductTemplateInherit(models.Model):
    _inherit = 'product.template'
    
    job_position = fields.Many2one('hr.job', string="Job Position")
    labour_type = fields.Boolean(string='Labour')