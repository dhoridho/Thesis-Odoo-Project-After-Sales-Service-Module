# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from lxml import etree


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    is_pos_bom = fields.Boolean('POS BoM')
    is_configure_components = fields.Boolean('Configure Components')
    branch_id = fields.Many2one('res.branch','Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)])


    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(MrpBom, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self.env.user.has_group('equip3_pos_masterdata.group_pos_user') and not self.env.user.has_group('equip3_pos_masterdata.group_pos_manager'):
            root = etree.fromstring(res['arch'])
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res
    

class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    is_pos_bom = fields.Boolean('POS BoM', related='bom_id.is_pos_bom')
    is_extra = fields.Boolean('Extra?')
    additional_cost = fields.Float(string='Additional Cost', digits=0) 
    is_configure_components = fields.Boolean('Configure Components', related='bom_id.is_configure_components')
    is_configurable = fields.Boolean('Configurable?')

    @api.onchange('is_extra')
    def _onchange_is_extra(self):
        self.is_configurable = self.is_extra

    @api.model
    def create(self, vals):
        if vals.get('is_extra') == True:
            vals['is_configurable'] = True
        return super(MrpBomLine, self).create(vals)

    def write(self, vals):
        if vals.get('is_extra') == True:
            vals['is_configurable'] = True
        return super(MrpBomLine, self).write(vals)