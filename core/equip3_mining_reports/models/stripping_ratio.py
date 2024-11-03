from odoo import models, fields, api


class MiningStrippingRatio(models.Model):
    _name = 'mining.stripping.ratio'
    _description = 'Stripping Ratio'
    _rec_name = 'site_id'

    @api.depends('site_id')
    def _compute_allowed_operations(self):
        conf = self.env['mining.production.conf']
        for record in self:
            conf_ids = conf.search([('site_id', '=', record.site_id.id)])
            record.allowed_operation_ids = [(6, 0, conf_ids.mapped('operation_id').ids)]

    @api.depends('site_id', 'waste_operation_id')
    def _compute_allowed_waste(self):
        conf = self.env['mining.production.conf']
        for record in self:
            waste_ids = []
            if record.site_id and record.waste_operation_id:
                conf_ids = conf.search([
                    ('site_id', '=', record.site_id.id),
                    ('operation_id', '=', record.waste_operation_id.id)
                ])
                if record.waste_operation_id.operation_type_id in ('shipment', 'extraction'):
                    field_name = 'product_ids'
                else:
                    field_name = 'output_ids'
                waste_ids = conf_ids.mapped(field_name).filtered(lambda p: p.mining_economic_product == 'non-economic').ids
            record.allowed_waste_ids = [(6, 0, waste_ids)]

    @api.depends('site_id', 'ore_operation_id')
    def _compute_allowed_ore(self):
        conf = self.env['mining.production.conf']
        for record in self:
            ore_ids = []
            if record.site_id and record.ore_operation_id:
                conf_ids = conf.search([
                    ('site_id', '=', record.site_id.id),
                    ('operation_id', '=', record.ore_operation_id.id)
                ])
                if record.ore_operation_id.operation_type_id in ('shipment', 'extraction'):
                    field_name = 'product_ids'
                else:
                    field_name = 'output_ids'
                ore_ids = conf_ids.mapped(field_name).filtered(lambda p: p.mining_economic_product == 'economic').ids
            record.allowed_ore_ids = [(6, 0, ore_ids)]


    site_id = fields.Many2one(comodel_name='mining.site.control', string='Mining Site')
    waste_operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Waste Operation', domain="[('id', 'in', allowed_operation_ids)]")
    waste_ids = fields.Many2many(comodel_name='product.product', relation='waste_product_rel', string='Waste', domain="[('id', 'in', allowed_waste_ids)]")
    ore_operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Ore Operation', domain="[('id', 'in', allowed_operation_ids)]")
    ore_ids = fields.Many2many(comodel_name='product.product', relation='ore_product_rel', string='Ore', domain="[('id', 'in', allowed_ore_ids)]")

    # technical fields
    allowed_operation_ids = fields.Many2many('mining.operations.two', compute=_compute_allowed_operations)
    allowed_waste_ids = fields.Many2many('product.product', compute=_compute_allowed_waste)
    allowed_ore_ids = fields.Many2many('product.product', compute=_compute_allowed_ore)

    @api.onchange('site_id')
    def _onchange_site_id(self):
        conf_id = self.env['mining.production.conf'].search([
            ('site_id', '=', self.site_id.id)
        ], limit=1)
        if not conf_id:
            return
        operation_id = conf_id.operation_id
        self.waste_operation_id = operation_id.id
        self.ore_operation_id = operation_id.id
        if operation_id.operation_type_id in ('shipment', 'extraction'):
            field_name = 'product_ids'
        else:
            field_name = 'output_ids'
        self.waste_ids = [(6, 0, conf_id[field_name].filtered(lambda p: p.mining_economic_product == 'non-economic').ids)]
        self.ore_ids = [(6, 0, conf_id[field_name].filtered(lambda p: p.mining_economic_product == 'economic').ids)]
