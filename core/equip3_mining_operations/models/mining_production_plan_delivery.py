from distutils.command.config import config
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MiningProductionPlanDelivery(models.Model):
    _name = 'mining.production.plan.delivery'
    _description = 'Mining Production Plan Delivery'

    @api.depends(
        'operation_id', 'site_id',
        'mining_prod_plan_id', 'mining_prod_plan_id.mining_project_id', 'mining_prod_plan_id.assets_ids', 'mining_prod_plan_id.assets_ids.assets_id', 'mining_prod_plan_id.operation_ids', 'mining_prod_plan_id.operation_ids.operation_id',
        'mining_prod_line_id', 'mining_prod_line_id.mining_project_id', 'mining_prod_line_id.assets_ids', 'mining_prod_line_id.assets_ids.assets_id', 'mining_prod_line_id.operation_id',
        'mining_prod_act_id', 'mining_prod_act_id.mining_project_id', 'mining_prod_act_id.assets_ids', 'mining_prod_act_id.assets_ids.assets_id', 'mining_prod_act_id.operation_id'
    )
    def _compute_mining_prod_plan_id(self):
        prod_conf = self.env['mining.production.conf']
        for record in self:
            operation_ids = self.env['mining.operations.two']
            mining_project_id = self.env['mining.project.control']
            asset_ids = self.env['maintenance.equipment']

            site_id = record.site_id
            operation_id = record.operation_id
            
            if record.mining_prod_act_id:
                operation_ids = record.mining_prod_act_id.operation_id
                mining_project_id = record.mining_prod_act_id.mining_project_id
                asset_ids = record.mining_prod_act_id.assets_ids
            elif record.mining_prod_line_id:
                operation_ids = record.mining_prod_line_id.operation_id
                mining_project_id = record.mining_prod_line_id.mining_project_id
                asset_ids = record.mining_prod_line_id.assets_ids
            elif record.mining_prod_plan_id:
                operation_ids = record.mining_prod_plan_id.operation_ids.mapped('operation_id')
                mining_project_id = record.mining_prod_plan_id.mining_project_id
                asset_ids = record.mining_prod_plan_id.assets_ids

            conf_id = prod_conf.search([
                ('site_id', '=', site_id and site_id.id or False),
                ('operation_id', '=', operation_id and operation_id.id or False)
            ], limit=1)

            operation_ids = operation_ids.filtered(
                lambda o: o.operation_type_id == 'shipment')
            asset_ids = asset_ids.filtered(lambda a: a.operation_id == operation_id)\
                .mapped('assets_id').filtered(lambda a: a.fac_area == mining_project_id.facilities_area_id)
            product_ids = conf_id.product_ids

            record.operation_ids = [(6, 0, operation_ids.ids)]
            record.product_ids = [(6, 0, product_ids.ids)]
            record.asset_ids = [(6, 0, asset_ids.ids)]

    @api.depends('history_ids', 'history_ids.amount', 'mining_prod_act_id')
    def _compute_history_amount(self):
        for record in self:
            history_ids = record.history_ids.filtered(lambda h: h.mining_prod_act_id == record.mining_prod_act_id)
            total_amount = 0.0
            if history_ids:
                total_amount = history_ids[0].amount
            record.total_amount = total_amount

    mining_prod_plan_id = fields.Many2one(comodel_name='mining.production.plan', string='Mining Production Plan')
    mining_prod_line_id = fields.Many2one(comodel_name='mining.production.line', string='Mining Production Lines')
    mining_prod_act_id = fields.Many2one(comodel_name='mining.production.actualization', string='Mining Production Actualization')

    site_id = fields.Many2one('mining.site.control', string='Mining Site')

    operation_ids = fields.Many2many(comodel_name='mining.operations.two', string='Allowed Operations', compute=_compute_mining_prod_plan_id)
    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, domain="[('id', 'in', operation_ids)]")

    asset_ids = fields.Many2many(comodel_name='maintenance.equipment', compute=_compute_mining_prod_plan_id)
    asset_id = fields.Many2one(comodel_name='maintenance.equipment', string='Asset', domain="[('id', 'in', asset_ids)]", required=True)

    product_ids = fields.Many2many(comodel_name='product.product', compute=_compute_mining_prod_plan_id)
    product_id = fields.Many2one('product.product', string='Product', domain="[('id', 'in', product_ids)]", required=True)

    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

    amount = fields.Float(string='Amount', default=1.0, digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    original_move = fields.Boolean(copy=False)

    history_ids = fields.One2many('mining.production.plan.delivery.history', 'delivery_id', string='History')
    total_amount = fields.Float(digits='Product Unit of Measure', compute=_compute_history_amount)

    mpa_state = fields.Selection(related='mining_prod_act_id.state', string='MPA Status')

    @api.constrains('operation_id', 'uom_id')
    def _check_uom(self):
        for record in self:
            operation_id = record.operation_id
            uom_id = record.uom_id
            if not operation_id or not uom_id:
                continue
            operation_uom_id = operation_id.uom_id
            if uom_id.category_id != operation_uom_id.category_id:
                raise ValidationError(_('UoM %s (%s) have different category with operation UoM %s (%s)' % (
                    uom_id.display_name, uom_id.category_id.display_name, operation_uom_id.display_name, operation_uom_id.category_id.display_name
                )))

    @api.onchange('operation_id', 'site_id')
    def _onchange_operation_site(self):
        conf_id = self.env['mining.production.conf'].search([
            ('site_id', '=', self.site_id and self.site_id.id or False),
            ('operation_id', '=', self.operation_id and self.operation_id.id or False),
        ], limit=1)
        self.location_src_id = conf_id and conf_id.location_src_id.id or False
        self.location_dest_id = conf_id and conf_id.location_dest_id.id or False
        self.product_id = conf_id and conf_id.product_ids[0].id or False
        self.uom_id = self.operation_id and self.operation_id.uom_id.id or False

    @api.onchange('asset_ids')
    def _onchange_asset_ids(self):
        if self.asset_ids:
            self.asset_id = self.asset_ids[0].id or self.asset_ids[0]._origin.id

    def _prepare_history_values(self):
        self.ensure_one()
        prod_plan_id = self.mining_prod_plan_id
        prod_line_id = self.mining_prod_line_id
        prod_act_id = self.mining_prod_act_id
        site_id = prod_act_id.mining_site_id or prod_line_id.mining_site_id or prod_plan_id.mining_site_id
        pit_id = prod_act_id.mining_project_id or prod_line_id.mining_project_id or prod_plan_id.mining_project_id
        return {
            'delivery_id': self.id,
            'mining_prod_plan_id': prod_plan_id and prod_plan_id.id or False,
            'mining_prod_line_id': prod_line_id and prod_line_id.id or False,
            'mining_prod_act_id': prod_act_id and prod_act_id.id or False,
            'operation_id': self.operation_id and self.operation_id.id or False,
            'site_id': site_id and site_id.id or False,
            'pit_id': pit_id and pit_id.id or False,
            'product_id': self.product_id and self.product_id.id or False,
            'asset_id': self.asset_id and self.asset_id.id or False,
            'location_src_id': self.location_src_id and self.location_src_id.id or False,
            'location_dest_id': self.location_dest_id and self.location_dest_id.id or False,
            'uom_id': self.uom_id and self.uom_id.id or False
        }

    def action_iteration(self):
        self.ensure_one()
        history_ids = self.history_ids.filtered(lambda h: h.mining_prod_act_id == self.mining_prod_act_id)
        if not history_ids:
            history_values = self._prepare_history_values()
            history_id = self.env['mining.production.plan.delivery.history'].create(history_values)
        else:
            history_id = history_ids[0]

        context = self._prepare_history_values()
        del context['delivery_id']
        context['history_id'] = history_id.id

        context = {'default_' + key: value for key, value in context.items()}

        action = {
            'name': _('Delivery Iteration'),
            'type': 'ir.actions.act_window',
            'res_model': 'mining.production.plan.delivery.iteration',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }
        view_xml_id = 'equip3_mining_operations.view_mining_production_plan_delivery_iteration_form'
        if self.env.context.get('pop_back', False):
            view_xml_id += '_pop'
        action['view_id'] = self.env.ref(view_xml_id).id
        return action
    
    def action_history(self):
        self.ensure_one()
        history_ids = self.history_ids.filtered(lambda h: h.mining_prod_act_id == self.mining_prod_act_id)
        if not history_ids:
            history_values = self._prepare_history_values()
            history_id = self.env['mining.production.plan.delivery.history'].create(history_values)
        else:
            history_id = history_ids[0]

        action = {
            'name': _('Delivery History'),
            'type': 'ir.actions.act_window',
            'res_model': 'mining.production.plan.delivery.history',
            'res_id': history_id.id,
            'view_mode': 'form',
            'target': 'new'
        }
        view_xml_id = 'equip3_mining_operations.view_mining_production_plan_delivery_history_form'
        if self.env.context.get('pop_back', False):
            view_xml_id += '_pop'
        action['view_id'] = self.env.ref(view_xml_id).id
        return action


class MiningProductionPlanDeliveryHistory(models.Model):
    _name = 'mining.production.plan.delivery.history'
    _description = 'Mining Production Plan Delivery History'

    @api.depends('iteration_ids', 'iteration_ids.amount')
    def _compute_amount(self):
        for record in self:
            record.amount = sum(record.iteration_ids.mapped('amount'))

    delivery_id = fields.Many2one('mining.production.plan.delivery', string='Delivery', required=True, ondelete='cascade')

    mining_prod_plan_id = fields.Many2one('mining.production.plan', string='Production Plan')
    mining_prod_line_id = fields.Many2one('mining.production.line', string='Production Line')
    mining_prod_act_id = fields.Many2one('mining.production.actualization', string='Actualization')
    
    site_id = fields.Many2one('mining.site.control', string='Mining Site')
    pit_id = fields.Many2one('mining.project.control', string='Mining Pit')
    operation_id = fields.Many2one('mining.operations.two', string='Operation')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    product_id = fields.Many2one('product.product', string='Product')

    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)

    amount = fields.Float(string='Amount', digits='Product Unit of Measure', compute=_compute_amount)
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    iteration_ids = fields.One2many('mining.production.plan.delivery.iteration', 'history_id', string='Iterations')

    mpa_state = fields.Selection(related='mining_prod_act_id.state', string='MPA Status')

    @api.constrains('operation_id', 'uom_id')
    def _check_uom(self):
        for record in self:
            operation_id = record.operation_id
            uom_id = record.uom_id
            if not operation_id or not uom_id:
                continue
            operation_uom_id = operation_id.uom_id
            if uom_id.category_id != operation_uom_id.category_id:
                raise ValidationError(_('UoM %s (%s) have different category with operation UoM %s (%s)' % (
                    uom_id.display_name, uom_id.category_id.display_name, operation_uom_id.display_name, operation_uom_id.category_id.display_name
                )))

    def action_save_and_pop_back(self):
        self.ensure_one()
        return self.mining_prod_line_id.pop_actualization(self.mining_prod_act_id.id)


class MiningProductionPlanDeliveryIteration(models.Model):
    _name = 'mining.production.plan.delivery.iteration'
    _description = 'Mining Production Plan Delivery Iteration'

    @api.model
    def create(self, vals):
        records = super(MiningProductionPlanDeliveryIteration, self).create(vals)

        context = dict()
        for key, value in self.env.context.items():
            if not key.startswith('default_'):
                context[key] = value
        stock_picking = self.env['stock.picking'].with_context(context)
        
        for record in records:
            warehouse_id = record.location_src_id.get_warehouse()
            picking_type_id = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', warehouse_id.id), 
                ('code', '=', 'outgoing')
            ], limit=1)
            picking_values = {
                'picking_type_id': picking_type_id.id,
                'location_id': record.location_src_id.id,
                'location_dest_id': record.location_dest_id.id,
                'company_id': record.mining_prod_act_id.company_id.id,
                'branch_id': record.mining_prod_act_id.branch_id.id,
                'move_ids_without_package': [(0, 0, {
                    'mining_prod_plan_id': record.mining_prod_plan_id and record.mining_prod_plan_id.id or False,
                    'mining_prod_line_id': record.mining_prod_line_id and record.mining_prod_line_id.id or False,
                    'mining_prod_act_id': record.mining_prod_act_id and record.mining_prod_act_id.id or False,
                    'mining_operation_id': record.operation_id and record.operation_id.id or False,
                    'mining_delivery_id': record.history_id.delivery_id.id if record.history_id and record.history_id.delivery_id else False,
                    'product_id': record.product_id.id,
                    'name': record.mining_prod_act_id and record.mining_prod_act_id.name or record.product_id.display_name,
                    'initial_demand': record.amount,
                    'product_uom_qty': record.amount,
                    'product_uom': record.uom_id.id,
                    'location_id': record.location_src_id.id,
                    'location_dest_id': record.location_dest_id.id,
                })]
            }
            record.picking_id = stock_picking.create(picking_values)
        return records

    def unlink(self):
        for record in self:
            if not record.picking_id:
                continue
            if record.picking_id.state != 'draft':
                raise ValidationError(_('Cannot delete iteration when picking already post!'))
            else:
                record.picking_id.unlink()
        return super(MiningProductionPlanDeliveryIteration, self).unlink()

    history_id = fields.Many2one('mining.production.plan.delivery.history', string='History', required=True, ondelete='cascade')

    mining_prod_plan_id = fields.Many2one('mining.production.plan', string='Production Plan')
    mining_prod_line_id = fields.Many2one('mining.production.line', string='Production Line')
    mining_prod_act_id = fields.Many2one('mining.production.actualization', string='Production Actualization')

    site_id = fields.Many2one('mining.site.control', string='Mining Site')
    pit_id = fields.Many2one('mining.project.control', string='Mining Pit')
    operation_id = fields.Many2one('mining.operations.two', string='Operation')
    asset_id = fields.Many2one('maintenance.equipment', string='Asset')
    product_id = fields.Many2one('product.product', string='Product')

    location_src_id = fields.Many2one('stock.location', string='Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', required=True)
    amount = fields.Float(string='Amount', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UoM', required=True)

    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)

    @api.constrains('operation_id', 'uom_id')
    def _check_uom(self):
        for record in self:
            operation_id = record.operation_id
            uom_id = record.uom_id
            if not operation_id or not uom_id:
                continue
            operation_uom_id = operation_id.uom_id
            if uom_id.category_id != operation_uom_id.category_id:
                raise ValidationError(_('UoM %s (%s) have different category with operation UoM %s (%s)' % (
                    uom_id.display_name, uom_id.category_id.display_name, operation_uom_id.display_name, operation_uom_id.category_id.display_name
                )))

    def action_save_and_pop_back(self):
        self.ensure_one()
        return self.mining_prod_line_id.pop_actualization(self.mining_prod_act_id.id)
