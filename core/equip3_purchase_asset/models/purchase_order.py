
from odoo import api, fields, models, SUPERUSER_ID, _
from dateutil.relativedelta import relativedelta
from odoo.tools.float_utils import float_compare, float_round
from odoo.exceptions import ValidationError, UserError


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False)
    
    def _create_picking(self):
        context = dict(self.env.context) or {}
        StockPicking = self.env['stock.picking']
        is_asset = False
        for order in self:
            is_asset = order.order_line.filtered(lambda x: x.product_id.type == 'asset') or False
            # for line in order.order_line:
            #     if line.product_id.type == 'asset':
            #         is_asset = True
            #         continue
            # if is_asset:
            #     continue

        if context.get('assets_orders') or is_asset:
            for order in self:
                temp_data = []
                final_data = []
                for line in order.order_line:
                    if {'date_planned': line.date_planned, 'warehouse_id': line.destination_warehouse_id.id} in temp_data:
                        filter_lines = list(filter(lambda r:r.get('date_planned') == line.date_planned and r.get('warehouse_id') == line.destination_warehouse_id.id, final_data))
                        if filter_lines:
                            filter_lines[0]['lines'].append(line)
                    else:
                        temp_data.append({
                            'date_planned': line.date_planned,
                            'warehouse_id': line.destination_warehouse_id.id
                        })
                        final_data.append({
                            'date_planned': line.date_planned,
                            'warehouse_id': line.destination_warehouse_id.id,
                            'lines': [line]
                        })
                for line_data in final_data:
                    if any(product.type in ['product', 'consu', 'asset'] for product in order.order_line.product_id):
                        order = order.with_company(order.company_id)
                        pickings = order.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel'))
                        res = order._prepare_picking()
                        warehouse_id = self.env['stock.warehouse'].browse([line_data.get('warehouse_id')])
                        picking_type_id = self.env['stock.picking.type'].search([('warehouse_id', '=', warehouse_id.id), ('code', '=', 'incoming')], limit=1)
                        if picking_type_id:
                            res.update({
                                'picking_type_id': picking_type_id.id,
                                'location_dest_id': picking_type_id.default_location_dest_id.id,
                                'date': line_data.get('date_planned'),
                            })
                        picking = StockPicking.with_user(SUPERUSER_ID).create(res)
                        lines = self.env['purchase.order.line']
                        for new_line in line_data.get('lines'):
                            lines += new_line
                        moves = lines.with_context(assets_orders=True)._create_stock_moves(picking)
                        moves = moves.filtered(lambda x: x.state not in ('done', 'cancel'))._action_confirm()
                        seq = 0
                        for move in sorted(moves, key=lambda move: move.date):
                            seq += 5
                            move.sequence = seq
                        moves._action_assign()
                        picking.message_post_with_view('mail.message_origin_link',
                            values={'self': picking, 'origin': order},
                            subtype_id=self.env.ref('mail.mt_note').id)
            return True
        else:
            return super()._create_picking()
    
    def copy(self, default=None):
        default = dict(default or {})
        default.setdefault("date_order", self.date_order)
        res = super(PurchaseOrder, self).copy(default)
        return res
    
    @api.depends('amount_untaxed', 'branch_id', 'currency_id')
    def _compute_approval_matrix_id(self):
        res = super(PurchaseOrder, self)._compute_approval_matrix_id()
        for record in self:
            if record.is_assets_orders and record.is_approval_matrix and record.company_id and record.branch_id and record.amount_untaxed:
                approval_matrix_id = self.env['approval.matrix.purchase.order'].search([
                            ('minimum_amt', '<=', record.amount_untaxed), 
                            ('maximum_amt', '>=', record.amount_untaxed),
                            ('branch_id', '=', record.branch_id.id),
                            ('company_id', '=', record.company_id.id),
                            ('currency_id', '=', record.currency_id.id),
                            ('order_type', '=', "assets_order")], limit=1)
                if not approval_matrix_id:
                    raise ValidationError(_("You don’t have approval matrix for this RFQ, please set Purchase Order Approval Matrix first"))
                record.approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
        return res
    
    @api.depends('amount_untaxed','approval_matrix_id')
    def _compute_approval_matrix_direct(self):
        res = super(PurchaseOrder, self)._compute_approval_matrix_direct()
        for record in self:
            if record.is_approval_matrix_direct and record.dp and record.is_assets_orders:
                approval_matrix_id = self.env['approval.matrix.direct.purchase'].search([
                    ('minimum_amt', '<=', record.amount_untaxed),
                    ('maximum_amt', '>=', record.amount_untaxed),
                    ('company_id', '=', record.company_id.id),
                    ('branch_id', '=', record.branch_id.id),
                    ('order_type', '=', "assets_order")
                    ], limit=1)
                record.direct_approval_matrix_id = approval_matrix_id and approval_matrix_id.id or False
        return res
    
    @api.model
    def action_purchase_order_menu(self):
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        res = super(PurchaseOrder, self).action_purchase_order_menu()
        if is_good_services_order:
            self.env.ref("equip3_purchase_asset.menu_purchase_assets_order").active = True
        else:
            self.env.ref("equip3_purchase_asset.menu_purchase_assets_order").active = False
        return res
    
    def write(self, vals):
        context = dict(self.env.context) or {}
        if 'state' in vals and vals['state'] == 'purchase':
            reference_formatting = self.env['ir.config_parameter'].sudo().get_param('reference_formatting')
            if not self.exp_po or (self.is_revision_po and self.origin.startswith('RFQ')):
                if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
                # if self.env.company.is_good_services_order:
                    if self.is_assets_orders and not context.get('default_dp'):
                        vals['name2'] = context.get('name') or self.name
                        if reference_formatting == 'new' or not self.is_revision_po or self.origin.startswith('RFQ'):
                            vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order.seqs.assests')
                    elif self.is_assets_orders and context.get('default_dp'):
                        vals['name'] = self.env['ir.sequence'].next_by_code('direct.purchase.seqs.a')
        return super(PurchaseOrder, self).write(vals)
    
    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        if context.get('goods_order') == None and context.get('services_good') == None and context.get('assets_orders') == None and 'origin' in vals:
            if vals.get('origin') and '/A/' in vals['origin']:
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.request.seqs.a')
        res = super(PurchaseOrder , self).create(vals)
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':
        # if self.env.company.is_good_services_order:
            if context.get('assets_orders'):
                res.name = self.env['ir.sequence'].next_by_code('purchase.order.seqs.a')
            if res.is_assets_orders and res.dp:
                name = self.env['ir.sequence'].next_by_code('direct.purchase.seqs.a')
                res.name = name
                res.name_dp = name 
        return res
    
    @api.model
    def retrieve_dashboard(self):
        res = super(PurchaseOrder, self).retrieve_dashboard()
        po = self.env['purchase.order']
        context = dict(self.env.context) or {}
        one_week_ago = fields.Datetime.to_string(fields.Datetime.now() - relativedelta(days=7))
        query = """SELECT AVG(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)),
                          AVG(extract(epoch from age(po.date_approve,po.create_date)/(24*60*60)::decimal(16,2))),
                          SUM(CASE WHEN po.date_approve >= %s THEN COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total) ELSE 0 END),
                          MIN(curr.decimal_places)
                   FROM purchase_order po
                   JOIN res_company comp ON (po.company_id = comp.id)
                   JOIN res_currency curr ON (comp.currency_id = curr.id)
                   WHERE po.state in ('purchase', 'done')
                    AND po.is_goods_orders = %s
                    AND po.company_id = %s
                """
        if context.get('goods_order'):
            res['all_to_send'] = po.search_count([('state', '=', 'draft'), ('is_goods_orders', '=', True)])
            res['my_to_send'] = po.search_count([('state', '=', 'draft'), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', True)])
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('is_goods_orders', '=', True)])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', True)])
            res['all_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('is_goods_orders', '=', True)])
            res['my_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_goods_orders', '=', True)])
            self._cr.execute(query, (one_week_ago, True, self.env.company.id))
        elif context.get('services_good'):
            res['all_to_send'] = po.search_count([('state', '=', 'draft'), ('is_services_orders', '=', True)])
            res['my_to_send'] = po.search_count([('state', '=', 'draft'), ('user_id', '=', self.env.uid), ('is_services_orders', '=', True)])
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('is_services_orders', '=', True)])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_services_orders', '=', True)])
            res['all_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('is_services_orders', '=', True)])
            res['my_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_services_orders', '=', True)])
        elif context.get('assets_orders'):
            res['all_to_send'] = po.search_count([('state', '=', 'draft'), ('is_assets_orders', '=', True)])
            res['my_to_send'] = po.search_count([('state', '=', 'draft'), ('user_id', '=', self.env.uid), ('is_assets_orders', '=', True)])
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('is_assets_orders', '=', True)])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_assets_orders', '=', True)])
            res['all_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('is_assets_orders', '=', True)])
            res['my_late'] = po.search_count([('state', 'in', ['draft', 'sent', 'to approve']), ('date_order', '<', fields.Datetime.now()), ('user_id', '=', self.env.uid), ('is_assets_orders', '=', True)])
        else:
            res['all_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now())])
            res['my_waiting'] = po.search_count([('state', 'in', ('waiting_for_approve', 'rfq_approved')), ('date_order', '>=', fields.Datetime.now()), ('user_id', '=', self.env.uid)])
        if not context.get('goods_order'):
            self._cr.execute(query, (one_week_ago, False, self.env.company.id))
        values = self.env.cr.fetchone()
        res['all_avg_order_value'] = round(values[0] or 0, values[3])
        res['all_avg_days_to_purchase'] = round(values[1] or 0, 2)
        res['all_total_last_7_days'] = round(values[2] or 0, values[3])
        order_value = res['all_avg_order_value']
        res['all_avg_order_value'] = f'{order_value:,}'
        last_7_days = res['all_total_last_7_days']
        res['all_total_last_7_days'] = f'{last_7_days:,}'
        return res
    
class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # OVERRIDE
    def _compute_qty_received_method(self):
        super(PurchaseOrderLine, self)._compute_qty_received_method()
        for line in self:
            if not line.display_type:
                if line.product_id.type in ['consu', 'product','asset']:
                    line.qty_received_method = 'stock_moves'
    
    @api.model
    def _default_domain(self):
        res = super(PurchaseOrderLine, self)._default_domain()
        context = dict(self.env.context) or {}
        if context.get('assets_orders'):
            return [('type', '=', 'asset')]
        return res

    @api.onchange('dp_line')
    def onchange_product_type(self):
        product_domain = {}
        res = super(PurchaseOrderLine ,self).onchange_product_type()
        # if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order'):
        #     if self.dp_line and self.order_id.is_assets_orders:
        #         return {'domain': {'product_template_id': [('tracking', '=', 'none'), ('can_be_direct','=',True), ('type', '=', 'asset'), ('purchase_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', self.order_id.company_id.id)]}}
        return res 
    
    def _prepare_stock_moves(self, picking):
        context = dict(self.env.context) or {}
        if context.get('assets_orders'):
            self.ensure_one()
            res = []
            if self.product_id.type not in ['product', 'consu', 'asset']:
                return res

            qty = 0.0
            price_unit = self._get_stock_move_price_unit()
            outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
            for move in outgoing_moves:
                qty -= move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')
            for move in incoming_moves:
                qty += move.product_uom._compute_quantity(move.product_uom_qty, self.product_uom, rounding_method='HALF-UP')

            move_dests = self.move_dest_ids
            if not move_dests:
                move_dests = self.move_ids.move_dest_ids.filtered(lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'supplier')

            if not move_dests:
                qty_to_attach = 0
                qty_to_push = self.product_qty - qty
            else:
                move_dests_initial_demand = self.product_uom._compute_quantity(
                    sum(move_dests.filtered(lambda m: m.state != 'cancel' and not m.location_dest_id.usage == 'supplier').mapped('product_qty')),
                    self.product_uom, rounding_method='HALF-UP')
                qty_to_attach = move_dests_initial_demand - qty
                qty_to_push = self.product_qty - move_dests_initial_demand

            if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_attach, self.product_id.uom_id)
                res.append(self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom))
            if float_compare(qty_to_push, 0.0, precision_rounding=self.product_uom.rounding) > 0:
                product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_push, self.product_id.uom_id)
                extra_move_vals = self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
                extra_move_vals['move_dest_ids'] = False  # don't attach
                res.append(extra_move_vals)
            return res
        else:
            return super()._prepare_stock_moves(picking)
    
    is_assets_orders = fields.Boolean(string="Assets Orders", default=False, related="order_id.is_assets_orders", store=True)
    