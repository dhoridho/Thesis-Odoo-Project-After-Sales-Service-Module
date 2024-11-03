# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

from odoo import models, api, fields, _


class IrModels(models.Model):
    _inherit = 'ir.model'

    fields_schema = fields.Html(string='Read Schema', compute="_compute_schema")
    fields_post_Schema = fields.Html(string='Create Schema', compute="_compute_schema")

    def _compute_schema(self):
        field_names = self.field_id.mapped('name')
        field_list_string = ''
        for field in self.field_id:
            if field.ttype == 'many2one':
                field_list_string += "&nbsp; &nbsp; &nbsp; &nbsp; '%s' &nbsp; ['id', 'name'], &nbsp; &nbsp; # %s Field <br/>" % (field.name, field.ttype)
            elif field.ttype in ['one2many', 'many2many']:
                field_list_string += "&nbsp; &nbsp; &nbsp; &nbsp; '%s' &nbsp; ['id'], &nbsp; &nbsp; # %s Field <br/>" % (field.name, field.ttype)
            else:
                field_list_string += "&nbsp; &nbsp; &nbsp; &nbsp; '%s', <br/>" % field.name
        html_div = "<div> { <br/> &nbsp; &nbsp; '%s' { <br/> %s <br/> &nbsp; &nbsp; } <br/> }</div>" % (self.model, field_list_string)
        self.fields_schema = html_div
        self.fields_post_Schema = html_div
