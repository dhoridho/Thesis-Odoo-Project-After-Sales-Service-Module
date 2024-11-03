from odoo import api, fields, models, _

      
class MiningProdPlanOutput(models.Model):
    _name = 'mining.production.plan.output'
    _description = 'Production Output'

    @api.depends(
        'operation_id',
        'mining_prod_plan_id', 'mining_prod_plan_id.mining_site_id', 'mining_prod_plan_id.mining_project_id', 'mining_prod_plan_id.assets_ids', 'mining_prod_plan_id.assets_ids.assets_id', 'mining_prod_plan_id.operation_ids', 'mining_prod_plan_id.operation_ids.operation_id',
        'mining_prod_line_id', 'mining_prod_line_id.mining_site_id', 'mining_prod_line_id.mining_project_id', 'mining_prod_line_id.assets_ids', 'mining_prod_line_id.assets_ids.assets_id', 'mining_prod_line_id.operation_id',
        'mining_prod_act_id', 'mining_prod_act_id.mining_site_id', 'mining_prod_act_id.mining_project_id', 'mining_prod_act_id.assets_ids', 'mining_prod_act_id.assets_ids.assets_id', 'mining_prod_act_id.operation_id'
    )
    def _compute_mining_prod_plan_id(self):
        for record in self:
            operation_ids = self.env['mining.operations.two']
            mining_site_id = self.env['mining.site.control']
            mining_project_id = self.env['mining.project.control']
            asset_ids = self.env['maintenance.equipment']

            operation_id = record.operation_id

            if record.mining_prod_act_id:
                operation_ids = record.mining_prod_act_id.operation_id
                mining_site_id = record.mining_prod_act_id.mining_site_id
                mining_project_id = record.mining_prod_act_id.mining_project_id
                asset_ids = record.mining_prod_act_id.assets_ids
            elif record.mining_prod_line_id:
                operation_ids = record.mining_prod_line_id.operation_id
                mining_site_id = record.mining_prod_line_id.mining_site_id
                mining_project_id = record.mining_prod_line_id.mining_project_id
                asset_ids = record.mining_prod_line_id.assets_ids
            elif record.mining_prod_plan_id:
                operation_ids = record.mining_prod_plan_id.operation_ids.mapped('operation_id')
                mining_site_id = record.mining_prod_plan_id.mining_site_id
                mining_project_id = record.mining_prod_plan_id.mining_project_id
                asset_ids = record.mining_prod_plan_id.assets_ids

            operation_ids = operation_ids.filtered(lambda o: o.operation_type_id != 'shipment')
            operation_type = operation_id.operation_type_id

            product_ids = mining_site_id.operation_ids.filtered(lambda o: o.operation_id == operation_id)\
                .mapped('output_ids' if operation_type == 'production' else 'product_ids')
            asset_ids = asset_ids.filtered(lambda a: a.operation_id == operation_id)\
                .mapped('assets_id').filtered(lambda a: a.fac_area == mining_project_id.facilities_area_id)

            record.operation_ids = [(6, 0, operation_ids.ids)]
            record.product_ids = [(6, 0, product_ids.ids)]
            record.asset_ids = [(6, 0, asset_ids.ids)]

    
    mining_prod_plan_id = fields.Many2one(comodel_name='mining.production.plan', string='Mining Production Plan')
    mining_prod_line_id = fields.Many2one(comodel_name='mining.production.line', string='Mining Production Lines')
    mining_prod_act_id = fields.Many2one(comodel_name='mining.production.actualization', string='Mining Production Actualization')

    qty = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    qty_done = fields.Float(string='Quantity Done', digits='Product Unit of Measure')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='UoM', required=True)

    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=True, domain="[('id', 'in', product_ids)]")
    asset_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset', required=True, domain="[('id', 'in', asset_ids)]")
    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, domain="[('id', 'in', operation_ids)]")

    product_ids = fields.Many2many(comodel_name='product.product', string='Allowed Products', compute=_compute_mining_prod_plan_id)
    asset_ids = fields.Many2many(comodel_name='maintenance.equipment', string='Allowed Assets', compute=_compute_mining_prod_plan_id)
    operation_ids = fields.Many2many(comodel_name='mining.operations.two', string='Allowed Operations', compute=_compute_mining_prod_plan_id)
    
    original_move = fields.Boolean(copy=False)

    @api.onchange('product_id')
    def onchange_product_id(self):
        uom_id = False
        if self.product_id:
            uom_id = self.product_id.uom_id.id
        self.uom_id = uom_id

    @api.onchange('asset_ids')
    def _onchange_asset_ids(self):
        if self.asset_ids:
            self.asset_id = self.asset_ids[0].id or self.asset_ids[0]._origin.id

    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        if self.product_ids:
            self.product_id = self.product_ids[0].id or self.product_ids[0]._origin.id
