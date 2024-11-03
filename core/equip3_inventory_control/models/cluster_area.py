from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ClusterArea(models.Model):
    _name = 'cluster.area'
    _description = 'Cluster Area'

    name = fields.Char(string='Cluster', required=True)
    
    warehouse_id = fields.Many2many(comodel_name='stock.warehouse', string='Warehouse', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True,default=lambda self: self.env.company)
    warehouse_line = fields.One2many(comodel_name='cluster.warehouse.line', inverse_name='cluster_id', string='Cluster Lines')
    
    @api.constrains('warehouse_line')
    def _check_warehouse_unique(self):
        """show warning if warehouse selected more than once within the same warehouse"""
        for rec in self:
            warehouse_ids = []
            for line in rec.warehouse_line:
                if line.warehouse_id.id in warehouse_ids:
                    raise ValidationError(_('%s already selected') % (line.warehouse_id.name.title()))
                warehouse_ids.append(line.warehouse_id.id)
    
    
class ClusterWarehouseLine(models.Model):
    _name = 'cluster.warehouse.line'
    _description = 'Cluster Warehouse Line'
    _rec_name = 'warehouse_id'
    
    cluster_id = fields.Many2one(comodel_name='cluster.area', string='Cluster')
    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse')
    