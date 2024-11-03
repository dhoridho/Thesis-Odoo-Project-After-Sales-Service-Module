from odoo import api, fields, models, _
import datetime
from datetime import date, time
from odoo.exceptions import ValidationError

class StockQuantPackage(models.Model):
    _inherit = "stock.quant.package"

    name = fields.Char(readonly=True, default='New')
    max_weight = fields.Float("Maximum Weight", related="packaging_id.max_weight", readonly=True)
    package_status = fields.Selection([
                    ('packed', 'Packed'),
                    ('partial', 'Partial'),
                    ('empty', 'Empty')
                    ], 'Status', compute="_compute_package_staus", store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    package_expiration_date_time = fields.Date(string='Expiration Time')
    shipping_volume = fields.Float(string='Shipping Volume')
    owner_id_stock = fields.Many2one('res.partner', string='Responsibility')
    location_id_new = fields.Many2one('stock.location', 'Location')
    filter_location_id_new = fields.Many2many('stock.location', compute='_compute_location')
    barcode_packaging = fields.Char(string="Barcode Packagings")
    create_automatic = fields.Boolean(string="Create Automatic", store=True)


    @api.depends('create_automatic')
    def _onchange_create_automatic(self):
        for rec in self:
            if rec.create_automatic == True:
                for quant in rec.quant_ids:
                    quant.create_automatic = True
            else:
                for quant in rec.quant_ids:
                    quant.create_automatic = False


    @api.onchange('packaging_id')
    def _onchange_packaging_id(self):
        if self.packaging_id.packages_barcode_prefix and self.packaging_id.current_sequence:
            self.barcode_packaging = self.packaging_id.packages_barcode_prefix + self.packaging_id.current_sequence
        else:
            self.barcode_packaging = ''


    @api.constrains('quant_ids')
    def _onchange_quantity(self):
        if not self.create_automatic:
            for record in self.quant_ids:
                stock_quant = self.env['stock.quant'].search([('product_id', '=', record.product_id.id),('location_id', '=', record.location_id.id), ('package_id', '=', False)], limit=1)
                product_product = self.env['product.product'].search([('id', '=', record.product_id.id)], limit=1)
                product_template = self.env['product.template'].search([('id', '=', product_product.product_tmpl_id.id)], limit=1)
                total_stock_packages = self.env['stock.quant'].search([('product_id', '=', record.product_id.id),
                                                                        ('location_id', '=', record.location_id.id), 
                                                                        ('warehouse_id', '!=', False),
                                                                        ('package_id', '!=', False),
                                                                        ('create_automatic', '=', False)])
                qty = 0
                for x in total_stock_packages:
                    qty += x.available_quantity

                record.total_stock_in_package = qty
                if record.total_stock_in_package > stock_quant.available_quantity:
                    raise ValidationError(_('%s ' 'is not available in location', product_template.name))
                else:
                    pass

    @api.depends('warehouse_id')
    def _compute_location(self):
        for record in self:
            location_ids = self.env['stock.location'].search(['&',('warehouse_id', '=', record.warehouse_id.id), ('usage', '=', 'internal')])
            record.filter_location_id_new = [(6, 0, (location_ids).ids)]

    @api.onchange('location_id_new')
    def _onchange_location_id_new(self):
        self.location_id = self.location_id_new
        for x in self:
            for loc in x.quant_ids:
                loc.location_id = x.location_id_new

    @api.depends('quant_ids.package_id', 'quant_ids.location_id', 'quant_ids.company_id', 'quant_ids.owner_id', 'quant_ids.quantity', 'quant_ids.reserved_quantity')
    def _compute_package_info(self):
        result = super(StockQuantPackage, self)._compute_package_info()
        for rec in self:
            if rec.location_id_new:
                for x in rec:
                    x.location_id = x.location_id_new
            if rec.create_automatic:
                for x in rec.quant_ids:
                    x.product_description = x.product_id.product_tmpl_id.name
                    x.create_automatic = rec.create_automatic
        return result

    @api.model
    def action_package_unpack(self, vals):
        vals = [int(i) for i in vals]
        pack_ids = self.browse(vals)
        if pack_ids.filtered(lambda x: x.package_status == 'empty'):
            raise ValidationError(_("Selected Records contain Empty Packages!"))
        else:
            pack_ids.unpack()
        return True

    @api.depends('quant_ids', 'weight', 'max_weight')
    def _compute_package_staus(self):
        for rec in self:
            if len(rec.quant_ids) == 0:
                rec.package_status = 'empty'
            elif len(rec.quant_ids) >= 1 and rec.weight != rec.max_weight:
                rec.package_status = 'partial'
            elif len(rec.quant_ids) >= 1 and rec.weight == rec.max_weight:
                rec.package_status = 'packed'

    @api.model
    def create(self, vals):
        stock_quant_package_seq = self.env.ref('equip3_inventory_tracking.stock_quant_package_seq')
        record_id = self.search([], limit=1, order='id desc')
        check_today = False
        if record_id and record_id.create_date.date() == date.today():
            check_today = True
        if not check_today:
            stock_quant_package_seq.number_next_actual = 1
        vals['name'] = self.env['ir.sequence'].next_by_code(
            'stock.quant.package.seq') or 'New'
        if vals.get('packaging_id'):
            if vals.get('create_automatic'):
                product_packaging = self.env['product.packaging'].search([('id', '=', vals['packaging_id'])])
                for x in product_packaging:
                    digit = x.digits
                    new_seq = int(x.current_sequence) + 1
                    x.current_sequence = str(new_seq).zfill(digit)
            else:
                product_packaging = self.env['product.packaging'].search([('id', '=', vals['packaging_id'])])
                for x in product_packaging:
                    digit = x.digits
                    new_seq = int(x.current_sequence) + 1
                    x.current_sequence = str(new_seq).zfill(digit)

    #             if vals.get('quant_ids'):
    #                 product = ''
    #                 location = ''
    #                 quantity = 0.00
    #                 product = vals['quant_ids'][0][2]['product_id']
    #                 location = vals['quant_ids'][0][2]['location_id']
    #                 quantity = vals['quant_ids'][0][2]['quantity']
    #                 stock_quant = self.env['stock.quant'].search([('product_id', '=', product),
    #                                                             ('location_id', '=', location), 
    #                                                             ('package_id', '=', False)], limit=1)
    #                 total_stock_packages = self.env['stock.quant'].search([('product_id', '=',product),
    #                                                             ('location_id', '=', location), 
    #                                                             ('warehouse_id', '!=', False),
    #                                                             ('package_id', '!=', False)])
    #                 qty = 0
    #                 for x in total_stock_packages:
    #                     qty += x.available_quantity
    #                 for rec in stock_quant:
    #                     rec.quantity = rec.quantity - float(quantity)                                    
            
        result = super(StockQuantPackage, self).create(vals)
        return result

    # def write(self,vals):
    #     print('writeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee')
    #     if not self.create_automatic:
    #         for record in self.quant_ids:
    #             stock_quant = self.env['stock.quant'].search([('product_id', '=', record.product_id.id),('location_id', '=', record.location_id.id), ('package_id', '=', False)], limit=1)
    #             product_product = self.env['product.product'].search([('id', '=', record.product_id.id)], limit=1)
    #             product_template = self.env['product.template'].search([('id', '=', product_product.product_tmpl_id.id)], limit=1)
    #             total_stock_packages = self.env['stock.quant'].search([('product_id', '=', record.product_id.id),('location_id', '=', record.location_id.id), ('warehouse_id', '!=', False),('package_id', '!=', False)])
    #             qty = 0
    #             id = ''
    #             for x in total_stock_packages:
    #                 print('xxxxxxxxxxxxxxxxxx',x.quantity)
    #                 qty += x.available_quantity
    #                 if x.id == record.id:
    #                     print('masuk keifffffffffffff')
    #                     stock_quant.quantity = stock_quant.quantity - x.quantity
    #                 else:
    #                     print('masuk ke elseeeeeeeeeeeeeee')
    #                     pass
    #                     # stock_quant.quantity = stock_quant.quantity - x.quantity
    #     return super(StockQuantPackage, self).write(vals)

    def change_color_on_kanban(self):
        for record in self:
            color = 0
            if record.package_status == 'packed':
                color = 2
            elif record.package_status == 'partial':
                color = 5
            elif record.package_status == 'empty':
                color = 7
            record.color = color
