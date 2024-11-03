from odoo import models, fields,api,_


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    color = fields.Char(string='Color', default=0)
    color_new = fields.Integer(string='Color', default=0)
    custom_color = fields.Char("Color", default='#a6a6a6')

    @api.onchange('color_new')
    def set_color_from_color_new(self):
        for rec in self:
            if rec.color_new:
                if rec.color_new == 0:
                    rec.color = rec.custom_color = '#FFFFFF'
                elif rec.color_new == 1:
                    rec.color = rec.custom_color = '#F0604F'
                elif rec.color_new == 2:
                    rec.color = rec.custom_color = '#F4A461'
                elif rec.color_new == 3:
                    rec.color = rec.custom_color = '#F7CD1E'
                elif rec.color_new == 4:
                    rec.color = rec.custom_color = '#6DC1ED'
                elif rec.color_new == 5:
                    rec.color = rec.custom_color = '#814968'
                elif rec.color_new == 6:
                    rec.color = rec.custom_color = '#EB7E7F'
                elif rec.color_new == 7:
                    rec.color = rec.custom_color = '#2C8397'
                elif rec.color_new == 8:
                    rec.color = rec.custom_color = '#475577'
                elif rec.color_new == 9:
                    rec.color = rec.custom_color = '#D6155F'
                elif rec.color_new == 10:
                    rec.color = rec.custom_color = '#31C381'
                elif rec.color_new == 11:
                    rec.color = rec.custom_color = '#9365B8'
            else:
                rec.color = rec.custom_color = '#a6a6a6'

    @api.onchange('custom_color')
    def set_color_from_custom_color(self):
        for rec in self:
            if rec.custom_color:
                rec.color = rec.custom_color
            else:
                rec.color = False
