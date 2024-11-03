# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta, date
from odoo import tools


class LabourEstimateTemplate(models.Model):
    _inherit = "labour.estimate.template"

    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section_name = fields.Many2one('section.line', string='Section')
    product_id = fields.Many2one('product.product', string='Product', required=True, domain="[('type', '=', 'labour'), ('group_of_product', '=', group_of_product)]")
    




                

    