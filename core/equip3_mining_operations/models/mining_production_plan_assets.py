from odoo import api, fields, models, _

      
class MiningProdPlanAssets(models.Model):
    _name = 'mining.production.plan.assets'
    _description = 'Production Assets'

    def _search_maintenance_equip(self, shelter, project_id, area_id, location_id):
        if project_id and area_id:
            search_me = self.env['maintenance.equipment'].search([('fac_area', '=', area_id.id), ('state', '=', 'operative')])
            if search_me:
                for me in search_me:
                    shelter.append(me.id)
                if location_id:
                    search_me_child = self.env['maintenance.equipment'].search([('fac_area', '=', location_id.id)])
                    if search_me_child:
                        for me_child in search_me_child:
                            shelter.append(me_child.id)
            
    @api.depends('mining_prod_plan_id', 
                 'mining_prod_line_id',
                 'mining_prod_act_id',
                 'mining_prod_plan_id.operation_ids', 
                 'mining_prod_plan_id.operation_ids.operation_id',
                 'mining_prod_plan_id.mining_project_id',
                 'mining_prod_line_id.mining_project_id',
                 'mining_prod_act_id.mining_project_id',)
    def _compute_mining_prod_plan_id(self):
        for record in self:
            operation_ids = []
            _assets = []
            if record.mining_prod_plan_id:
                operation_ids = record.mining_prod_plan_id.operation_ids.mapped('operation_id').ids
                record._search_maintenance_equip(_assets, 
                                                 record.mining_prod_plan_id.mining_project_id, 
                                                 record.mining_prod_plan_id.mining_project_id.facilities_area_id, 
                                                 record.mining_prod_plan_id.mining_project_id.facilities_area_id.parent_location)
            elif record.mining_prod_line_id:
                record._search_maintenance_equip(_assets, 
                                                 record.mining_prod_line_id.mining_project_id, 
                                                 record.mining_prod_line_id.mining_project_id.facilities_area_id, 
                                                 record.mining_prod_line_id.mining_project_id.facilities_area_id.parent_location)
            elif record.mining_prod_act_id:
                record._search_maintenance_equip(_assets, 
                                                 record.mining_prod_act_id.mining_project_id, 
                                                 record.mining_prod_act_id.mining_project_id.facilities_area_id, 
                                                 record.mining_prod_act_id.mining_project_id.facilities_area_id.parent_location)
            record.assets_ids = [(6, 0, _assets)]
            record.operation_ids = [(6, 0, operation_ids)]

    mining_prod_plan_id = fields.Many2one(comodel_name='mining.production.plan', string='Mining Production Plan')
    mining_prod_line_id = fields.Many2one(comodel_name='mining.production.line', string='Mining Production Lines')
    mining_prod_act_id = fields.Many2one(comodel_name='mining.production.actualization', string='Mining Production Actualization')

    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, domain="[('id', 'in', operation_ids)]")
    operation_ids = fields.Many2many(comodel_name='mining.operations.two', string='Allowed Operations', compute=_compute_mining_prod_plan_id)

    assets_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset', required=True, domain="[('id', 'in', assets_ids)]")
    assets_ids = fields.Many2many(comodel_name='maintenance.equipment', string='Assets', compute=_compute_mining_prod_plan_id)
    
    worker_ids = fields.Many2many(comodel_name='hr.employee', string='Worker')
    
    original_move = fields.Boolean(copy=False)
    duration = fields.Float(string='Duration')

    @api.onchange('assets_ids')
    def _onchange_assets_ids(self):
        if self.assets_ids:
            self.assets_id = self.assets_ids[0].id or self.assets_ids[0]._origin.id
