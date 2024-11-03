from odoo import models, fields, api, _,SUPERUSER_ID
from datetime import date, datetime,timedelta
from odoo.exceptions import UserError, ValidationError

class ConsignmentAgreement(models.Model):
    _name = 'consignment.agreement'
    _description = 'Consignment Agreement'
    _order = "name DESC"

    def _reset_sequence(self):
        for rec in self:
            current_sequence = 1
            for line in rec.line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def _domain_analytic_group(self):
        return [('company_id','=',self.env.company.id)]

    def _get_account_tag_ids(self):
        return self.env['account.analytic.tag'].search([('company_id', '=', self.env.company.id)]).ids

    name = fields.Char(string='Reference', copy=False,default='New')
    title = fields.Char(string='Agreement Name')
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain="[('is_vendor', '=', True)]")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
        default=lambda self: self.env.company.currency_id.id)
    destination_warehouse_id = fields.Many2one('stock.warehouse', string="Destination", domain="[('company_id', '=', company_id),('branch_id','=',branch_id)]")
    account_tag_ids = fields.Many2many('account.analytic.tag', 'account_analytic_tag_consignment_rel', 'consignment_id', 'account_tag_id',
                                       string="Analytic Group", domain=_domain_analytic_group, default=_get_account_tag_ids)
    date_end = fields.Date(string='Agreement Period', default=lambda self: fields.Date.context_today(self) + timedelta(days=90))
    auto_create_bill = fields.Boolean(string='Auto Create Bill')
    confirm_date = fields.Datetime(string='Confirm Date')
    pricing_method = fields.Selection([('cost_price', 'Cost Price'),
                                       ('sale_price', 'Sale Price'),
                                       ('both_price', 'Both Price')],
                                       default='cost_price')
    bill_cycle = fields.Integer('Bill Cycle')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', required=True, default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
                                domain=lambda self: [('id', 'in', self.env.branches.ids)])
    state = fields.Selection(string='Status', required=True, readonly=True, copy=False, selection=[
            ('draft', 'Draft'),
            ('confirm', 'Confirm'),
            ('cancel', 'Canceled'),
            ('done', 'Done'),
        ], default='draft')
    description = fields.Text()
    sale_picking_count = fields.Integer('Orders', compute='_compute_sale_picking_count')
    picking_count = fields.Integer('Receiving Notes', compute='_compute_picking_count')
    move_count = fields.Integer('Bills', compute='_compute_move_count')
    move_entry_count = fields.Integer('Journal Entry', compute='_compute_move_count')
    set_single_delivery_destination = fields.Boolean("Single Delivery Destination", default=True)
    line_ids = fields.One2many('consignment.agreement.line', 'consignment_id', copy=True)
    is_transfer_back = fields.Boolean(string='Is Transfer Back', compute='_compute_is_transfer_back')
    picking_ids = fields.Many2many(comodel_name='stock.picking', string='Pickings')
    picking_out_count = fields.Integer('Delivery Order', compute='_compute_picking_out_count')
    payment_term_id = fields.Many2one(comodel_name='account.payment.term', string='Payment Terms', domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
        
    @api.depends('line_ids.available_quantity')
    def _compute_is_transfer_back(self):
        for rec in self:
            rec.is_transfer_back = any(line.available_quantity > 0 for line in rec.line_ids)


    @api.model
    def create(self,vals):
        vals['name'] = self.env['ir.sequence'].sudo().next_by_code('purchase.requisition.consignment.new')
        if 'line_ids' in vals:
            if not vals['line_ids']:
                raise ValidationError("Can't save Consignment because there's no product in order line!")
        res = super(ConsignmentAgreement, self).create(vals)
        return res


    @api.onchange('pricing_method')
    def onchange_pricing_method(self):
        for rec in self:
            if rec.pricing_method == 'cost_price':
                for line in self.line_ids:
                    line.method = 'cost_price'
                    line.sale_price = 0
                    line.margin = 0
                    line.margin_amount = 0
                    line.cost_price = 0

            if rec.pricing_method == 'sale_price':
                for line in self.line_ids:
                    line.method = 'sale_price'
                    line.sale_price = 0
                    line.margin = 0
                    line.margin_amount = 0
                    line.cost_price = 0

            if rec.pricing_method == 'both_price':
                for line in self.line_ids:
                    line.method = False
                    line.sale_price = 0
                    line.margin = 0
                    line.margin_amount = 0
                    line.cost_price = 0

    @api.onchange('set_single_delivery_destination')
    def onchange_set_single_delivery_destination(self):
        for rec in self:
            if rec.set_single_delivery_destination == True:
                for line in rec.line_ids:
                    line.destination_warehouse_id = False
            else:
                for line in rec.line_ids:
                    line.destination_warehouse_id = rec.destination_warehouse_id

    @api.onchange('destination_warehouse_id')
    def onchange_destination_warehouse_id(self):
        for rec in self:
            for line in rec.line_ids:
                if rec.destination_warehouse_id:
                    line.destination_warehouse_id = rec.destination_warehouse_id


    def _compute_sale_picking_count(self):
        # query = f'''select so.id from stock_valuation_layer_source as svls
        #             left join stock_valuation_layer_stock_valuation_layer_source_rel as rel ON svls.id = rel.stock_valuation_layer_source_id
        #             left join stock_valuation_layer as svl ON rel.stock_valuation_layer_id = svl.id
        #             left join stock_move as sm ON sm.id = svl.stock_move_id
        #             left join sale_order_line as sol ON sol.id = sm.sale_line_id
        #             left join sale_order as so ON so.id = sol.order_id
        #             where svls.consignment_id = {self.id}
        #         '''
        # self.env.cr.execute(query)
        # data = tuple(item[0] for item in self.env.cr.fetchall())
        # if data:
        #     self.sale_picking_count = len(data)
        # else:
        #     self.sale_picking_count = 0
        for record in self:
            svll_line = self.env['stock.valuation.layer.line'].search([('consignment_source_id', '=', record.id), ('svl_source_id.sale_id', '!=', False)])
            sale_id = svll_line.mapped('sale_id')
            record.sale_picking_count = len(sale_id)

    def _compute_move_count(self):
        for record in self:
            record.move_count = self.env['account.move'].search_count([('consignment_id', '=', record.id), ('move_type', '=', 'in_invoice')])
            record.move_entry_count = self.env['account.move'].search_count([('consignment_id', '=', record.id), ('move_type', '=', 'entry')])

    def _compute_picking_count(self):
        for record in self:
            picking_count = self.env['stock.picking'].search_count([('consignment_id', '=', record.id), ('picking_type_code', '=', 'incoming')])
            if picking_count:
                record.picking_count = picking_count
            else:
                record.picking_count = 0
                
    @api.depends('picking_ids')
    def _compute_picking_out_count(self):
        for rec in self:
            rec.picking_out_count = sum(1 for picking in rec.picking_ids if picking.picking_type_id.code == 'outgoing')

    def action_view_sale(self):
        # query = f'''select sol.id from stock_valuation_layer_source as svls
        #             left join stock_valuation_layer_stock_valuation_layer_source_rel as rel ON svls.id = rel.stock_valuation_layer_source_id
        #             left join stock_valuation_layer as svl ON rel.stock_valuation_layer_id = svl.id
        #             left join stock_move as sm ON sm.id = svl.stock_move_id
        #             left join sale_order_line as sol ON sol.id = sm.sale_line_id
        #             left join sale_order as so ON so.id = sol.order_id
        #             where svls.consignment_id = {self.id}
        #         '''
        # self.env.cr.execute(query)
        # data = tuple(item[0] for item in self.env.cr.fetchall())
        # return{
        #     "name"      : "Sale Order Line",
        #     "view_mode" : "tree, form",
        #     "views"     : [(self.env.ref('equip3_sale_operation.view_sale_order_line_tree').id, 'tree'), (False, 'form')],
        #     "res_model" : "sale.order.line",
        #     "view_id"   : False,
        #     "type"      : "ir.actions.act_window",
        #     "domain"    : [('id','in',data)]
        # }
        svll_line = self.env['stock.valuation.layer.line'].search([('consignment_source_id', '=', self.id), ('svl_source_id.sale_id', '!=', False)])
        sale_id = svll_line.mapped('sale_id')
        
        return{
            "name"      : "Sale Order Line",
            "view_mode" : "tree, form",
            "views"     : [(self.env.ref('equip3_sale_operation.view_sale_order_line_tree').id, 'tree'), (False, 'form')],
            "res_model" : "sale.order.line",
            "view_id"   : False,
            "type"      : "ir.actions.act_window",
            "domain"    : [('id','in',sale_id.order_line.ids)]
        }

    def action_view_picking(self):
        result = self.env["ir.actions.actions"]._for_xml_id('equip3_inventory_operation.stock_picking_receiving_note')
        pick_ids = self.mapped('id')
        if not pick_ids or len(pick_ids) >= 1:
            result['domain'] = "[('consignment_id','in',%s), ('picking_type_code', '=', 'incoming')]" % (pick_ids)
            # result['domain'] = "[('consignment_id','in',%s)]" % (pick_ids)
            result['context'] = {'picking_type_code': 'incoming',
                                'incoming' : False,
                                'outgoing_location' : True,
                                'date_done_string': 'Received On',
                                'group_header': False,
                                'create': False,
                                'default_is_consignment': True}
        return result
    
    def action_view_picking_out(self):
        self.ensure_one()
        result = self.env["ir.actions.actions"]._for_xml_id('equip3_inventory_operation.action_delivery_order')
        result['domain'] = "[('id','in', %s), ('picking_type_code', '=', 'outgoing')]" % (self.picking_ids.ids)
        return result
    

    def action_view_vendor_bill(self):
        self.ensure_one()

        form_view_ref = self.env.ref('account.view_move_form', False)
        tree_view_ref = self.env.ref('account.view_in_invoice_tree', False)

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_in_invoice_type')
        result.update({
            'domain': [('consignment_id', '=', self.id), ('move_type', '=', 'in_invoice')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        })
        return result

    def action_view_journal_entry(self):
        self.ensure_one()

        form_view_ref = self.env.ref('account.view_move_form', False)
        tree_view_ref = self.env.ref('account.view_move_tree', False)

        result = self.env['ir.actions.act_window']._for_xml_id('account.action_move_journal_line')
        result.update({
            'domain': [('consignment_id', '=', self.id), ('move_type', '=', 'entry')],
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        })
        return result

    def open_wizard(self):
        return {
            'name': 'Receiving Consignment',
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.qty.consignment.agreement',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'
            rec.confirm_date = fields.datetime.now()

    def create_vendor_bill(self):
        self.ensure_one()
        if any(not line.product_id.categ_id.consignment_commision_account for line in self.line_ids):
            raise ValidationError(_('Please set Consignment Commision Account first!'))
        
        return {
            'name': 'Create Vendor Bill',
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.for.create.vendor.bill',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }
        
    def action_transfer_back(self):
        self.ensure_one()
        return {
            'name': 'Transfer Back',
            'type': 'ir.actions.act_window',
            'res_model': 'transfer.back.consignment',
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }



class ConsignmentAgreementLine(models.Model):
    _name = 'consignment.agreement.line'
    _description = 'Consignment Agreement Line'

    def unlink(self):
        approval = self.consignment_id
        res = super(ConsignmentAgreementLine, self).unlink()
        approval._reset_sequence()
        return res

    @api.model
    def create(self,vals):
        res = super(ConsignmentAgreementLine, self).create(vals)
        if not self.env.context.get("keep-line_sequence", False):
            res.consignment_id._reset_sequence()
        return res

    consignment_id = fields.Many2one('consignment.agreement', required=True, string='Consignment Agreement', ondelete='cascade')
    company_id = fields.Many2one('res.company')
    branch_id = fields.Many2one('res.branch')
    destination_warehouse_id = fields.Many2one('stock.warehouse', string="Destination", domain="[('company_id', '=', company_id),('branch_id','=',branch_id)]")
    sequence = fields.Integer(required=True, index=True, help='Use to arrange calculation sequence', string='No')
    sequence2 = fields.Integer(
            string="No #2",
            related="sequence",
            readonly=True,
            store=True,
    )
    product_id = fields.Many2one('product.product')
    product_description_variants = fields.Char('Description')
    purchase_stock = fields.Float(string='Purchase Stock', copy=False)
    receiving_quantities = fields.Float('Received Quantities', copy=False)
    sold_quantities = fields.Float('Sold Quantities', copy=False)
    billed_quantities = fields.Float('Billed Quantities', copy=False,compute='get_billed_qty')
    product_uom_id = fields.Many2one('uom.uom', string='UOM')
    account_tag_ids_line = fields.Many2many(
        'account.analytic.tag', string="Analytic Groups")
    method = fields.Selection([('cost_price', 'Cost Price'),
                                ('sale_price', 'Sale Price')])
    sale_price = fields.Float('Sale Price')
    margin = fields.Float('Margin (%)')
    margin_amount = fields.Float('Margin Amount')
    cost_price = fields.Float('Cost Price')
    available_quantity = fields.Float(string='Available Quantity', compute='get_available_quantity', store=True)        
    transfer_back_qty = fields.Float(string='Transfer Back Quantity', compute='get_transfer_back_qty', store=True)
    
    @api.depends('consignment_id.picking_ids.move_ids_without_package', 'consignment_id.picking_ids.state')
    def get_transfer_back_qty(self):
        for record in self:
            total_qty = 0
            
            for picking in record.consignment_id.picking_ids:
                if picking.picking_type_id.code == 'outgoing' and picking.state == 'done':
                    total_qty += sum(
                        move.quantity_done
                        for move in picking.move_ids_without_package
                        if move.product_id == record.product_id
                    )
            record.transfer_back_qty = total_qty

    @api.onchange('margin')
    def _onchange_method_line_margin_amount(self):
        for rec in self:
            if rec.method == 'sale_price' and rec.sale_price and rec.margin:
                rec.margin_amount = (rec.sale_price * rec.margin) / 100
                rec.price_unit =  rec.sale_price - rec.margin_amount

    # @api.depends('consignment_id.sale_picking_count')
    # def get_sold_qty(self):
    #     for rec in self:
    #         if rec.consignment_id and rec.product_id:
    #             query = f'''select svls.taken_qty,svl.product_id,svls.consignment_id from stock_valuation_layer_source as svls
    #                         inner join stock_valuation_layer_stock_valuation_layer_source_rel as rel ON svls.id = rel.stock_valuation_layer_source_id
    #                         inner join stock_valuation_layer as svl ON rel.stock_valuation_layer_id = svl.id
    #                         where svls.consignment_id = {rec.consignment_id.id} and svl.product_id = {rec.product_id.id}
    #                     '''
    #             self.env.cr.execute(query)
    #             data = tuple(item[0] for item in self.env.cr.fetchall())
    #         if data:
    #             rec.sold_quantities = int(sum(data))
    #         else:
    #             rec.sold_quantities = 0

    # @api.depends('consignment_id.move_count')
    def get_billed_qty(self):
        for rec in self:
            account_move = self.env['account.move'].search([('consignment_id', '=', rec.consignment_id.id), ('move_type', '=', 'in_invoice')])
            rec.billed_quantities = 0
            if rec.consignment_id and account_move:
                for move in account_move:
                    if move.sale_order_line_ids:
                        for so in move.sale_order_line_ids:
                            if rec.product_id.id == so.product_id.id:
                                rec.billed_quantities += so.qty_delivered
            else:
                rec.billed_quantities = 0
                
    @api.depends('receiving_quantities', 'sold_quantities', 'transfer_back_qty')
    def get_available_quantity(self):
        for rec in self:
            rec.available_quantity = rec.receiving_quantities - rec.sold_quantities - rec.transfer_back_qty


    @api.model
    def default_get(self, fields):
        res = super(ConsignmentAgreementLine, self).default_get(fields)
        if self._context:
            context_keys = self._context.keys()
            next_sequence = 1
            if 'line_ids' in context_keys:
                if len(self._context.get('line_ids')) > 0:
                    next_sequence = len(self._context.get('line_ids')) + 1
            res.update({'sequence': next_sequence})
        if self.consignment_id.pricing_method != 'both_price':
            self.method = self.consignment_id.pricing_method
        else:
            self.method = False
        return res

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_description_variants = self.product_id.display_name
            self.product_uom_id = self.product_id.uom_po_id

