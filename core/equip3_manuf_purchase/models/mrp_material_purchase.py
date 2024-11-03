from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import pytz

def convert_tz(dt, tz_from, tz_to):
    if isinstance(dt, str):
        dt = fields.Datetime.from_string(dt)
    if isinstance(tz_from, str):
        tz_from = pytz.timezone(tz_from)
    if isinstance(tz_to, str):
        tz_to = pytz.timezone(tz_to)
    dt = tz_from.localize(dt).astimezone(tz_to)
    return dt.replace(tzinfo=None)


class MRPMaterialPurchase(models.Model):
    _name = 'mrp.material.purchase'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'MRP Material Purchase'

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.material.purchase', sequence_date=None) or _('New')
        return super(MRPMaterialPurchase, self).create(vals)

    @api.model
    def _defaut_date_from(self):
        now = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        return convert_tz(now, self.env.user.tz, pytz.utc)

    @api.model
    def _defaut_date_to(self):
        now = fields.Datetime.now().replace(hour=23, minute=59, second=59)
        return convert_tz(now, self.env.user.tz, pytz.utc)

    name = fields.Char(
        string='Reference', 
        required=True, 
        copy=False, 
        readonly=True, 
        default=lambda self: _('New'),
        tracking=True)
    
    mrp_production_ids = fields.Many2many(
        'mrp.production', 
        'mrp_material_purchase_ids', 
        string='Production Order',
        tracking=True,
        domain="[('state', 'in', ('confirmed', 'progress')), ('create_date', '>=', date_from), ('create_date', '<=', date_to)]")
    
    company_id = fields.Many2one(
        'res.company', 
        string='Company', 
        required=True, 
        index=True,
        default=lambda self: self.env.company, 
        tracking=True)

    state = fields.Selection(
        selection=[('draft', 'Draft'), ('submitted', 'Submitted')], 
        string='Status', 
        readonly=True, 
        copy=False, 
        index=True, 
        default='draft', 
        tracking=True)
    
    branch_id = fields.Many2one('res.branch', 
        string='Branch', 
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)], 
        readonly=True,
        states={'draft': [('readonly', False)]}, 
        tracking=True)
    
    finished_product_ids = fields.One2many(
        'mrp.material.purchase.finished.product', 
        'mrp_material_purchase_id', 
        string='Finished Products')
    
    component_ids = fields.One2many(
        'mrp.material.purchase.component', 
        'mrp_material_purchase_id', 
        string='Components')
    
    purchase_request_count = fields.Integer(compute='_compute_purchase_request_count')
    material_request_count = fields.Integer(compute='_compute_material_request_count')

    date_from = fields.Datetime('Period', index=True, copy=False, default=_defaut_date_from)
    date_to = fields.Datetime('Date To', index=True, copy=False, default=_defaut_date_to)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    is_calculated = fields.Boolean()

    def _compute_purchase_request_count(self):
        for record in self:
            record.purchase_request_count = self.env['purchase.request'].search_count([
                ('mrp_material_to_purchase_id', '=', record.id)])

    def _compute_material_request_count(self):
        for record in self:
            record.material_request_count = self.env['material.request'].search_count([
                ('material_purchase_id', '=', record.id)])

    @api.onchange('date_from', 'date_to')
    def _onchange_date_from_to(self):
        domain = [
            ('state', 'in', ['confirmed', 'progress'])
        ]
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))

        if self.date_from and self.date_to:
            production_ids = self.env['mrp.production'].search(domain)
            self.mrp_production_ids = [(6, 0, production_ids.ids)]
    
    @api.onchange('mrp_production_ids')
    def _onchange_mrp_production_ids(self):
        groups = {}
        for move in self.mrp_production_ids.move_finished_only_ids:
            finished = move.finished_id
            finished_bom = finished.bom_id
            finished_uom = finished.product_uom_id
            bom_quantity = move.product_uom._compute_quantity(move.product_uom_qty, finished_uom)
            if (move.product_id, finished_bom) not in groups:
                groups[(move.production_id, move.product_id, finished_bom)] = bom_quantity
            else:
                groups[(move.production_id, move.product_id, finished_bom)] += bom_quantity

        finished_values = [(5,)]
        for (production, product, bom), quantity in groups.items():
            finished = bom.finished_ids.filtered(lambda o: o.product_id == product)
            finished_values += [(0, 0, {
                'production_id': production.id,
                'product_id': product.id,
                'product_bom': bom.id,
                'product_uom_qty': quantity,
                'uom_id': finished.product_uom_id.id,
                'finished_uom_id': finished.product_uom_id.id
            })]
        self.finished_product_ids = finished_values

    @api.onchange('finished_product_ids')
    def _onchange_finished_product_ids(self):
        self.is_calculated = False

    def action_calculate(self):
        self.ensure_one()
        
        groups = {}
        for line in self.finished_product_ids:
            production = line.production_id

            if production:
                for move in production.move_raw_ids:
                    material = move.product_id
                    location = move.location_id

                    if (material, location) not in groups:
                        groups[(material, location)] = move.product_qty
                    else:
                        groups[(material, location)] += move.product_qty
            else:
                bom_quantity = line.uom_id._compute_quantity(line.product_uom_qty, line.finished_uom_id)
                for values in line.product_bom._boom(bom_quantity):
                    product = self.env['product.product'].browse(values['product_id'])
                    operation = self.env['mrp.routing.workcenter'].browse(values['operation_id'])
                    location = operation._get_workcenter().location_id
                    material_uom = self.env['uom.uom'].browse(values['product_uom'])

                    quantity = material_uom._compute_quantity(values['product_qty'], product.uom_id)

                    if (product, location) not in groups:
                        groups[(product, location)] = quantity
                    else:
                        groups[(product, location)] += quantity

        material_values = [(5,)]
        for (product, location), quantity in groups.items():
            warehouse = location.get_warehouse()

            res = product.with_context(warehouse_id=warehouse.id, location=location.id)._compute_quantities_dict(None, None, None)
            quantities = res[product.id]

            qty_available = quantities['qty_available']
            to_purchase = max(0, quantity - qty_available)
            
            material_values += [(0, 0, {
                'product_id': product.id,
                'location_id': location.id,
                'qty_available': qty_available,
                'incoming_qty': quantities['incoming_qty'],
                'outgoing_qty': quantities['outgoing_qty'],
                'virtual_available': quantities['virtual_available'],
                'needed': quantity, 
                'to_purchase': to_purchase
            })]
        
        self.component_ids = material_values
        self.is_calculated = True

    def action_submit_pr(self):
        if not self.is_calculated:
            raise ValidationError(_('Please claculate first!'))
        
        component_ids = self.component_ids.filtered(lambda x: x.to_purchase > 0.0)

        if not component_ids:
            raise ValidationError(_('No components to purchase!'))
        
        name = self.name
        company = self.company_id
        branch = self.branch_id
        now = fields.Datetime.now()
        today = now.date()

        purchase_request_vals = []
        for sequence, component in enumerate(component_ids):
            product = component.product_id
            location = component.location_id
            warehouse_id = location.get_warehouse().id

            picking_type = self.env['stock.picking.type'].search([
                ('default_location_dest_id', '=', location.id)
            ], limit=1)
        
            purchase_request_vals += [{
                'picking_type_id': picking_type.id,
                'company_id': company.id,
                'branch_id': branch.id,
                'origin': name,
                'destination_warehouse': warehouse_id,
                'request_date': now,
                'is_readonly_origin': True,
                'is_goods_orders': True,
                'is_single_request_date': True,
                'is_single_delivery_destination': True,
                'mrp_material_to_purchase_id': self.id,
                'line_ids': [(0, 0, {
                    'sequence2': sequence + 1,
                    'name': product.display_name,
                    'product_id': product.id,
                    'product_uom_id': component.product_uom_id.id,
                    'product_qty': component.to_purchase,
                    'date_required': today,
                    'dest_loc_id': warehouse_id,
                    'mrp_force_location_dest_id': location.id
                })]
            }]
        
        if purchase_request_vals:
            self.env['purchase.request'].create(purchase_request_vals)
            self.state = 'submitted'

    def action_submit_mr(self):
        if not self.is_calculated:
            raise ValidationError(_('Please claculate first!'))
        
        component_ids = self.component_ids.filtered(lambda x: x.to_purchase > 0.0)

        if not component_ids:
            raise ValidationError(_('No components to purchase!'))

        name = self.name
        company = self.company_id
        branch = self.branch_id
        now = fields.Datetime.now()
        today = now.date()
        
        material_request_vals = []
        for component in component_ids:
            product = component.product_id
            location = component.location_id
            warehouse_id = location.get_warehouse().id

            material_request_vals += [{
                'requested_by': self.env.user.id,
                'branch_id': branch.id,
                'company_id': company.id,
                'destination_warehouse_id': warehouse_id,
                'destination_location_id': location.id,
                'schedule_date': now,
                'source_document': name,
                'material_purchase_id': self.id,
                'product_line': [(0, 0, {
                    'description': product.display_name,
                    'product': product.id,
                    'product_unit_measure': product.uom_id.id,
                    'quantity': component.to_purchase,
                    'destination_warehouse_id': warehouse_id,
                })],
            }]

        if material_request_vals:
            self.env['material.request'].create(material_request_vals)
            self.state = 'submitted'

    def action_view_model(self, action_name, action_model, action_view, action_domain):
        self.ensure_one()
        if not action_name or not action_model or not action_view or not action_domain:
            return
        result = self.env['ir.actions.actions']._for_xml_id(action_name)
        records = self.env[action_model].search(action_domain)
        if not records:
            return
        if len(records) > 1:
            result['domain'] = [('id', 'in', records.ids)]
        else:
            form_view = [(self.env.ref(action_view).id, 'form')]
            if 'views' in result:
                result['views'] = form_view + [(s, v) for s, v in result['views'] if v != 'form']
            else:
                result['views'] = form_view
            result['res_id'] = records.id
        result['context'] = str(dict(eval(result.get('context', '').strip() or '{}', self._context), create=False))
        return result

    def action_view_purchase_request(self):
        return self.action_view_model(
            'purchase_request.purchase_request_form_action',
            'purchase.request',
            'purchase_request.view_purchase_request_form',
            [('mrp_material_to_purchase_id', '=', self.id)],
        )

    def action_view_material_request(self):
        return self.action_view_model(
            'equip3_inventory_operation.material_request_action',
            'material.request',
            'equip3_inventory_operation.material_request_form_view',
            [('material_purchase_id', '=', self.id)],
        )


class MRPMaterialPurchaseFinishedProducts(models.Model):
    _name = "mrp.material.purchase.finished.product"
    _description = "Fisihed Products on MPR Material to Purchase"

    mrp_material_purchase_id = fields.Many2one('mrp.material.purchase', index=True, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='mrp_material_purchase_id.company_id', store=True, index=True)

    production_id = fields.Many2one('mrp.production', string='Production Order')
    product_id = fields.Many2one('product.product', string='Finished Product', required=True, check_company=True)

    product_bom = fields.Many2one('mrp.bom', string='Bill of Material', required=True)
    finished_uom_id = fields.Many2one('uom.uom', string='Finished UoM')

    product_uom_qty = fields.Float(string='Quantity', default=1.0, digits='Product Unit of Measure', required=True)
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, domain="[('category_id', '=', uom_category_id)]")

    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='Product UoM')
    uom_category_id = fields.Many2one('uom.category', related='product_uom_id.category_id')

    @api.onchange('product_id', 'product_bom')
    def _onchange_product_bom(self):
        finished_line = self.product_bom.finished_ids.filtered(lambda o: o.product_id == self.product_id)
        self.uom_id = finished_line.product_uom_id.id
        self.finished_uom_id = finished_line.product_uom_id.id
        self.product_uom_qty = finished_line.product_qty


class MRPMaterialPurchaseComponent(models.Model):
    _name = "mrp.material.purchase.component"
    _description = "Components on MPR Material to Purchase"

    mrp_material_purchase_id = fields.Many2one('mrp.material.purchase', index=True, required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', related='mrp_material_purchase_id.company_id', store=True, index=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, readonly=True, check_company=True)
    product_uom_id = fields.Many2one('uom.uom', related='product_id.uom_id', string='Product UoM')
    location_id = fields.Many2one('stock.location', string='Location', required=True)

    qty_available = fields.Float(string='On Hand', readonly=True, digits='Product Unit of Measure')
    incoming_qty = fields.Float(string='Forecast Incoming', readonly=True, digits='Product Unit of Measure')
    outgoing_qty = fields.Float(string='Forecast Outgoing', readonly=True, digits='Product Unit of Measure')
    virtual_available = fields.Float(string='Forecasted', readonly=True, digits='Product Unit of Measure')

    needed = fields.Float(string='Needed', readonly=True, digits='Product Unit of Measure')
    to_purchase = fields.Float(string='To Purchase', digits='Product Unit of Measure')

    @api.constrains('to_purchase')
    def _check_to_purchase(self):
        for record in self:
            if record.to_purchase < 0:
                raise ValidationError(_("To purchase quantity must be positive!"))
