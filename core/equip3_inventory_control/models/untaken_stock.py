from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from datetime import datetime
import json

class UntakenStock(models.Model):
    _name = 'untaken.stock'
    _description = 'Untaken Stock'
    _rec_name = 'name'

    name = fields.Char(string="Reference", required=True, default="New")
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', required=True)
    location_ids = fields.Many2many('stock.location','us_id', 'location_id', 'us_location_id',  string='Location', required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)
    branch_id = fields.Many2one('res.branch', 'Branch', readonly=True, default=lambda self: self.env.branches if len(self.env.branches) == 1 else False,
                    domain=lambda self: [('id', 'in', self.env.branches.ids)])
    create_sc = fields.Boolean('Create Stock Count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('confirm', 'Confirmed'),
    ],
        default="draft")
    date_checked = fields.Datetime('Date Checked')
    untaken_stock_line_ids = fields.One2many('untaken.stock.line', 'untaken_stock_id', 'Untaken Stock Products', readonly=True)
    stock_count = fields.Many2one('stock.inventory', 'stock Count')
    domain_warehouse_id = fields.Char('Warehouse Domain', compute="_compute_location")

    @api.depends('branch_id')
    def _compute_location(self):
        if self.env.branches.ids:
            warehouse_ids = self.env['stock.warehouse'].search([('branch_id', 'in', self.env.branches.ids)])
            if warehouse_ids:
                self.domain_warehouse_id = json.dumps([('id', 'in', warehouse_ids.ids)])
            else:
                self.domain_warehouse_id = json.dumps([])
        else:
            self.domain_warehouse_id = json.dumps([])



    @api.model
    def create(self, vals):
        seq = self.env['ir.sequence'].next_by_code('untaken.stock')
        vals['name'] = seq
        res = super(UntakenStock, self).create(vals)
        return res

    def action_check(self):
        self.date_checked = datetime.now()
        product_list = []
        for loc in self.location_ids:
            # product_temp = []
            stock_move = self.env['stock.move'].search([])
            for move in stock_move:
                if move.location_dest_id.id == loc.id or move.location_id.id == loc.id:
                    if move.product_id.id not in product_list:
                        product_list.append(move.product_id.id)
            stock_count = self.env['stock.inventory'].search([])
            for sc in stock_count:
                # print('locids',sc.location_ids)
                if loc.id in sc.location_ids.ids:
                    if sc.inventoried_product == 'all_product':
                        # continue
                        product_list = []
                    if sc.inventoried_product == 'specific_product' or sc.inventoried_product == 'specific_category':
                        for product in sc.product_ids:
                            if product.id in product_list:
                                product_list.remove(product.id)
        vals = []
        if product_list:
            for prod in product_list:
                vals.append((0, 0, {
                    'product_id': prod,
                }))
            self.untaken_stock_line_ids = vals
        self.write({'state': 'in_progress'})
        # print('pl',product_list)


    def action_create_stock_count(self):
            reference_name = 'for' + ' ' + self.name
            stock_count = self.env['stock.inventory'].create({'name': reference_name, 'warehouse_id' : self.warehouse_id.id, 'location_ids' : self.location_ids.ids,
                                                          'inventoried_product' : 'specific_product', 'is_adj_value' : False})
            vals = []
            for product in self.untaken_stock_line_ids:
                stock_count.product_ids = [(4, product.product_id.id)]

            self.stock_count = stock_count.id
            self.write({'state': 'confirm'})
            # self.create_sc = False
            view = self.env.ref('stock.view_inventory_form')
            return {
                'name': _('Detailed Stock Count'),
                'view_mode': 'form',
                'res_model': 'stock.inventory',
                'view_id': view.id,
                'views': [(view.id, 'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
                'res_id': stock_count.id,
                # 'context': {'default_dst_path': dst_path}
                'context': self.env.context
            }

    def action_done(self):
        self.write({'state': 'confirm'})

class UntakenStockLine(models.Model):
    _name = 'untaken.stock.line'
    _description = 'Untaken Stock Line'

    product_id = fields.Many2one('product.product', 'Product')
    quantity = fields.Float('Quantity', related='product_id.qty_available')
    product_unit_measure = fields.Many2one('uom.uom', 'Unit of Measure', related='product_id.uom_id')
    untaken_stock_id = fields.Many2one('untaken.stock')



