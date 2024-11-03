from odoo import models, fields, api, _
from odoo.http import request
from odoo.tools import float_round
from odoo.exceptions import ValidationError
from lxml import etree
import json


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_assembly_context(self):
        context = {
            'from_date': self.env.context.get('from_date', False) or '',
            'to_date': self.env.context.get('to_date', False) or '',
            'warehouse': self.env.context.get('warehouse', False)
        }
        return context

    @api.model
    def retrieve_assembly_dashboard(self):
        warehouses = {}
        for warehouse in self.env['stock.warehouse'].search([
            ('branch_id', 'in', self._context.get('allowed_branch_ids'))
        ]):
            warehouses[warehouse.id] = warehouse.name

        context = self._prepare_assembly_context()
        if warehouses.keys() and not context.get('warehouse'):
            context.update({
                'warehouse': list(warehouses.keys())[0],
                'change': True,
            })
        assembly_context = {'warehouses': warehouses, 'context': context, 'has_access': True}
        request.session['assembly_context'] = context
        return assembly_context

    @api.depends('stock_move_ids.product_qty', 'stock_move_ids.state')
    @api.depends_context(
        'lot_id', 'owner_id', 'package_id', 'from_date', 'to_date',
        'location', 'warehouse'
    )
    def _compute_quantities(self):
        super(ProductProduct, self)._compute_quantities()
        assembly_products = self.filtered(lambda p: p.type != 'service' and p.produceable_in_assembly)

        res = assembly_products._compute_quantities_dict(self._context.get('lot_id'), self._context.get('owner_id'), self._context.get('package_id'), self._context.get('from_date'), self._context.get('to_date'))
        for product in assembly_products:
            product.assembly_safety_stock_qty = product._get_safety_stock_qty(self.env.context.get('warehouse'))
            product.assembly_to_produce_qty = max(0.0, product.assembly_safety_stock_qty - product.qty_available + product.outgoing_qty)

        # Services need to be set with 0.0 for all quantities
        services = self - assembly_products
        services.assembly_safety_stock_qty = 0.0
        services.assembly_to_produce_qty = 0.0

    def _get_safety_stock_qty(self, warehouse):
        self.ensure_one()
        domain = [('warehouse_id', '=', warehouse)] if warehouse else []
        safety_stock = self.env['assembly.safety.stock'].search(domain)
        safety_stock_lines = safety_stock.mapped('stock_line_ids')
        product_stock_lines = safety_stock_lines.filtered(lambda s: s.product_id == self)
        return sum(product_stock_lines.mapped('product_qty'))

    def action_assembly(self):
        self.ensure_one()

        assembly_context = request.session.get('assembly_context', dict())
        warehouse_id = assembly_context.get('warehouse', False)

        context = self.env.context.copy()
        context.update({
            'default_create_date': fields.Datetime.now(),
            'default_create_uid': self.env.user.id,
            'default_finished_qty': self.assembly_to_produce_qty,
            'default_warehouse_id': warehouse_id,
            'default_bom_id': self.assembly_bom_id.id,
            'default_branch_id': self.env.branch.id,
            'readonly_fields': True,
            'return_action': True
        })

        action = {
            'name': _('Assembly Production Record'),
            'type': 'ir.actions.act_window',
            'res_model': 'assembly.production.record',
            'view_mode': 'form',
            'target': 'new',
            'context': context
        }
        return action

    def action_disassembly(self):
        action = self.action_assembly()
        context = action['context']
        context.update({'default_finished_qty': 1})
        action.update({'name': _('Disassembly Production Record')})
        return action

    def assembly_create_next_lot(self, product_qty, expiration_date=False, force_company=False):
        self.ensure_one()

        stock_production_lot = self.env['stock.production.lot'].with_context(force_blank_expiration_date=True)
        company_id = force_company or self.company_id.id or self.env.company.id

        values = {
            'product_id': self.id,
            'company_id': company_id,
            'assembly_qty': product_qty,
            'assembly_expiration_date': expiration_date
        }

        if not self.is_sn_autogenerate and not self.is_in_autogenerate:
            values.update({'name': self.env['ir.sequence'].next_by_code('stock.lot.serial')})
            return stock_production_lot.create(values)

        if self.tracking == 'serial':
            digits = self.digits
            seq_to_update = 'current_sequence'
            current_seq = int(float(self.current_sequence))
        else:
            digits = self.in_digits
            seq_to_update = 'in_current_sequence'
            current_seq = int(float(self.in_current_sequence))

        while True:
            auto_sequence = self.product_tmpl_id._get_next_lot_and_serial(current_sequence=current_seq)
            lot_id = stock_production_lot.search([('name', '=', auto_sequence)])
            if not lot_id:
                break
            current_seq += 1

        if not lot_id:
            values.update({'name': auto_sequence})
            lot_id = stock_production_lot.create(values)

        # update for next sequence
        self.write({seq_to_update: str(current_seq + 1).zfill(digits)})

        return lot_id

    def _assembly_is_auto_generate(self):
        self.ensure_one()
        return (self.tracking == 'serial' and self.is_sn_autogenerate) or (self.tracking == 'lot' and self.is_in_autogenerate)

    def _assembly_is_manual_generate(self):
        self.ensure_one()
        return (self.tracking == 'serial' and not self.is_sn_autogenerate) or (self.tracking == 'lot' and not self.is_in_autogenerate)

    @api.model
    def assign_assembly_bom(self, domain):
        BoM = self.env['mrp.bom'].with_context(branch_id=self.env.branch.id, equip_bom_type='assembly')
        company_id = self.env.company.id
        products = self.search(domain)
        products_with_bom = products.filtered(lambda o: o.assembly_bom_id)
        for product in products - products_with_bom:
            bom = BoM._bom_find(product=product, company_id=company_id, bom_type='normal')
            if bom:
                product.assembly_bom_id = bom.id
                products_with_bom |= product
        return products_with_bom.ids

    assembly_safety_stock_qty = fields.Float(
        'Assembly Safety Stock', compute='_compute_quantities',
        digits='Product Unit of Measure', store=False)
    assembly_to_produce_qty = fields.Float(
        'Assembly To Produce', compute='_compute_quantities',
        digits='Product Unit of Measure', store=False)
    assembly_bom_id = fields.Many2one('mrp.bom', string='Assembly BoM', domain="""[
        ('equip_bom_type', '=', 'assembly'),
        ('type', '=', 'normal'),
        '|', 
            '&', 
                ('product_id', '=', id), 
                ('product_id.product_tmpl_id.produceable_in_assembly', '=', True),
            '&', 
                '&', 
                    ('product_id', '=', False), 
                    ('product_tmpl_id.product_variant_ids', '=', id),
                ('product_tmpl_id.produceable_in_assembly', '=', True),
    ]""")
