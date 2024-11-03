from odoo import models, fields, api


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    quality_point_ids = fields.Many2many('sh.qc.point', string='Quality Points', domain="[('id', 'in', quality_point_second_ids)]")
    quality_point_second_ids = fields.Many2many('sh.qc.point', string='Second Quality Points', compute="_compute_quality_point_ids")
    
    @api.depends('product_id')
    def _compute_quality_point_ids(self):
        for r in self:
            point_ids = []
            if r.product_id:
                point_ids = self.env['sh.qc.point'].search([('product_ids', 'in', r.product_id.ids)]).ids
            r.quality_point_second_ids = [(6, 0, point_ids)]
                

class MrpRoutingWorkcenter(models.Model):
    _inherit = 'mrp.routing.workcenter'

    quality_point_ids = fields.Many2many('sh.qc.point', string='Quality Points', domain="[('id', 'in', quality_point_second_ids)]")
    quality_point_second_ids = fields.Many2many('sh.qc.point', string='Second Quality Points', compute="_compute_quality_point_ids")
    
    @api.depends('bom_id', 'bom_id.product_id', 'bom_id.product_tmpl_id')
    def _compute_quality_point_ids(self):
        for r in self:
            point_ids = []
            if (r.bom_id.product_id or r.bom_id.product_tmpl_id) and r.bom_id:
                product_ids = r.bom_id.product_id.ids or r.bom_id.product_tmpl_id.product_variant_ids.ids
                point_ids = self.env['sh.qc.point'].search([('product_ids', 'in', product_ids)]).ids
            r.quality_point_second_ids = [(6, 0, point_ids)]
