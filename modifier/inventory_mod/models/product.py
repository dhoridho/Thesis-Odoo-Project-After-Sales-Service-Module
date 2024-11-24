from odoo import models, fields, api, _
from odoo.exceptions import UserError,ValidationError


class StockProductionLot2(models.Model):
    _inherit = 'stock.production.lot'

    variant_barcode_label = fields.Char(
        string='Display barcode label', related='product_id.variant_barcode_label')
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id', string='Product Template', store=True)
    warna = fields.Char(string='Warna',
                        compute='_compute_attribute')
    lebar = fields.Char(string='Lebar',
                        compute='_compute_attribute')
    k_motif = fields.Char(string='K.Motif',
                          compute='_compute_attribute')
    jenis_print = fields.Char(string='Jenis Print',
                              compute='_compute_attribute')
    jenis_kain = fields.Char(string='Jenis Kain',
                              compute='_compute_attribute')

    @api.depends('name', 'product_tmpl_id', 'product_id')
    def _compute_attribute(self):
        for record in self:
            record.warna = next(
                (a.name for a in record.product_id.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'warna'), '-')
            record.lebar = next(
                (a.name for a in record.product_id.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'lebar'), '-')
            record.k_motif = next(
                (a.name for a in record.product_id.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'motif'), '-')
            record.jenis_print = next(
                (a.name for a in record.product_id.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'jenis print'), '-')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    lot_ids = fields.One2many('stock.production.lot',
                              'product_tmpl_id', string='Lots')
    default_code = fields.Char(string="Product Code", default=" ")
    # auto_generate_product_code = fields.Boolean(
    #     string='Auto Generate Product Code', compute='_generate_product_code', store=True)
    product_brand_id = fields.Many2one(string='Product Brand')
    product_brand_ids = fields.Many2many('product.brand','product_brand_relation', 'tmpl_id', 'brand_id', string='Product Brands')
    is_archived = fields.Boolean(string='Archived', default=False)
    active =  fields.Boolean(tracking=True)

#     def write(self, vals):
#         if 'active' in vals:
#             if not self.env.user.has_group('base.group_system'):
#                 raise ValidationError("Only administrators can activate this record.")
#             if not self.is_archived:
#                 raise ValidationError("Cannot deactivate record if it is not archived.")
#             if vals.get('active'):
#                 vals['is_archived'] = False
#         return super(ProductTemplate, self).write(vals)
#
#     def active_is_archived(self):
#         if not self.env.user.has_group('base.group_system'):
#             raise ValidationError("Only administrators can activate this record.")
#         self.write({'is_archived': True})
#         return True
#
#     @api.constrains('default_code')
#     def _check_unique_default_code(self):
#         for record in self:
#             if record.default_code:
#                 count = self.search_count([('default_code', '=', record.default_code)])
#                 if count > 1:
#                     raise ValidationError("Product Code must be unique!")
#
#     @api.depends('categ_id.auto_generate_product_code')
#     def _generate_product_code(self):
#         for product in self:
#             product.auto_generate_product_code = product.categ_id.auto_generate_product_code

    # @api.onchange('categ_id')
    # def onchange_categ_id_seq(self):
    #     pass
    #
    # @api.onchange('categ_id', 'product_prefix', 'category_sequence')
    # def _onchange_categ_id(self):
    #     pass
    #
    # @api.model
    # def create(self, vals):
    #     code = vals.get('categ_id')
    #     if code:
    #         categ = self.env["product.category"].browse(code)
    #         sequence_code = categ.sequence_code_id
    #         if sequence_code:
    #             vals['default_code'] = sequence_code.next_by_id() or ''
    #         else:
    #             vals['default_code'] = ''
    #     return super(ProductTemplate, self,).create(vals)
    #
        
    # def genereate_product_code_action(self):
    #     for doc in self:
    #         if doc.default_code == '' or not doc.default_code:
    #             categ = doc.categ_id
    #             sequence_code = categ.sequence_code_id
    #             if sequence_code:
    #                 doc.default_code = sequence_code.next_by_id() or ''
    #             else:
    #                 doc.default_code = ''
    #         else:
    #             doc.default_code = doc.default_code
    #         for product in doc.product_variant_ids:
    #             if product.default_code == '' or not product.default_code:
    #                 categ = doc.categ_id
    #                 sequence_code = categ.sequence_code_id
    #                 if sequence_code:
    #                     product.default_code = sequence_code.next_by_id() or ''
    #                 else:
    #                     product.default_code = ''


    

    # return for fix product creation error

    # @api.onchange('type')
    # def _onchange_type_change_categ(self):
    #     return
    

    # def write(self, values):
    #     if values.get('code') or values.get('product_code') :
    #         print('debug')
    #     res = super(ProductTemplate,self).write(values)
        
    #     return res

    # @api.model
    # def create(self, vals):
    #     categ = self.env['product.category'].search([('id', '=', vals['categ_id'])])
    #     seq_id = self.env['product.template'].search([('default_code', 'ilike', categ.category_prefix )], order='id DESC', limit=1)
    #     if seq_id:
    #         number = seq_id.in_current_sequence.lstrip('0')
    #         number_str = str( int(number) + 1)
    #         number_length = len(number)
    #         original_number_length = seq_id.in_digits - number_length
    #         add_zero_original_number = '0' * original_number_length
    #         next_sequence = add_zero_original_number + number_str
    #         vals['in_current_sequence'] = next_sequence
    #         vals['current_sequence'] = next_sequence
    #         remove_string = vals['default_code'][:-int(vals['digits'])]
    #         vals['default_code'] = remove_string + next_sequence
    #     res = super(ProductTemplate, self).create(vals)
    #     return res

    # @api.onchange('categ_id')
    # def onchange_categ_id(self):
    #     if self.categ_id:
    #         if self.categ_id.attribute_line_ids:
    #             vals = []
    #             for attr_line in self.categ_id.attribute_line_ids:
    #                 vals.append((0, 0, {
    #                     'attribute_id': attr_line.attribute_id.id,
    #                 }))
    #             self.attribute_line_ids = vals


class Product(models.Model):
    _inherit = 'product.product'
    
    warna = fields.Char(string='Warna',
                        compute='_compute_attribute_product')
    lebar = fields.Char(string='Lebar',
                        compute='_compute_attribute_product')
    k_motif = fields.Char(string='K.Motif',
                          compute='_compute_attribute_product')
    jenis_print = fields.Char(string='Jenis Print',
                              compute='_compute_attribute_product')
    jenis_kain = fields.Char(string='Jenis Kain',
                              compute='_compute_attribute_product')
    gr_jual = fields.Char(string='Gramasi',
                              compute='_compute_attribute_product')
    gr_beli = fields.Char(string='Gramasi Beli',
                              compute='_compute_attribute_product')
    panjang = fields.Char(string='Panjang',
                              compute='_compute_attribute_product')
    alias_print = fields.Char(string='Alias Jenis Print',
                              compute='_compute_attribute_product')
    label = fields.Char(string='Label',
                              compute='_compute_attribute_product')
    tipe = fields.Char(string='Tipe',
                              compute='_compute_attribute_product')
    jenis_proses = fields.Char(string='Jenis Proses',
                              compute='_compute_attribute_product')
    tipe_weaving = fields.Char(string='Tipe Weaving',
                              compute='_compute_attribute_product')
    is_archived = fields.Boolean(string='Archived',related='product_tmpl_id.is_archived')
    active =  fields.Boolean(tracking=True)

    
    def generate_product_varian_code(self):
        for doc in self:
            if doc.default_code == '' or not doc.default_code:
                categ = doc.categ_id
                sequence_code = categ.sequence_code_id
                if sequence_code:
                    doc.default_code = sequence_code.next_by_id() or ''
                else:
                    doc.default_code = ''
            else:
                doc.default_code = doc.default_code
    
    # @api.constrains('default_code')
    # def _check_unique_default_code(self):
    #     for record in self:
    #         if record.default_code:
    #             count = self.search_count([('default_code', '=', record.default_code)])
    #             if count > 1:
    #                 raise ValidationError("Product Code must be unique!")
    #
    # @api.model
    # def create(self,vals):
    #     res = super(Product,self).create(vals)
    #     if res.default_code == '' or not res.default_code:
    #         categ = res.product_tmpl_id.categ_id
    #         if categ.sequence_code_id:
    #             sequence_code = categ.sequence_code_id
    #             if sequence_code:
    #                 res.default_code = sequence_code.next_by_id() or ''
    #             else:
    #                 res.default_code = ''
    #     return res
    #
    @api.depends('name', 'product_tmpl_id', 'product_template_attribute_value_ids')
    def _compute_attribute_product(self):
        for record in self:
            record.warna = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'warna'), '-')
            record.lebar = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'lebar'), '-')
            record.k_motif = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'motif'), '-')
            record.jenis_print = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'jenis print'), '-')
            record.jenis_kain = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'jenis kain'), '-')
            record.gr_jual = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'gramasi jual'), '-')
            record.gr_beli = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'gramasi beli'), '-')
            record.panjang = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'panjang'), '-')
            record.alias_print = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'alias jenis print'), '-')
            record.label = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'label'), '-')
            record.tipe = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'tipe'), '-')
            record.jenis_proses = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'jenis proses'), '-')
            record.tipe_weaving = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'tipe weaving'), '-')

    variant_barcode_label = fields.Char(string='Display barcode label',
                                        compute='_compute_variant_barcode_label')

    kode_motif = fields.Char(string='KodeMotif',
                             compute='_compute_attribute')

    def search_attribute(self, attribute_name):
        for record in self:
            attribute = next(
                (a.name for a in self.product_template_attribute_value_ids if a.attribute_id.name.lower() == attribute_name.lower()), '-')

            return attribute



    # return for fix product creation error
    @api.onchange('type')
    def _onchange_type_change_categ(self):
        return

    @api.depends('product_tmpl_id', 'product_template_attribute_value_ids')
    def _compute_attribute(self):
        for record in self:
            record.kode_motif = next(
                (a.name for a in record.product_template_attribute_value_ids if a.attribute_id.name.lower() == 'motif'), '-')

    def _get_combination_name_variant(self):
        """Exclude values from single value lines or from no_variant attributes."""
        true_barcode_label = self.product_tmpl_id.attribute_line_ids.filtered(
            lambda a:  a.barcode_label)
        variant_product = self.product_template_attribute_value_ids.filtered(
            lambda a:  a.attribute_id in true_barcode_label.mapped("attribute_id"))
        return ", ".join([ptav.name for ptav in variant_product])

    @api.depends('name', 'product_template_attribute_value_ids', 'product_tmpl_id', 'product_tmpl_id.attribute_line_ids')
    def _compute_variant_barcode_label(self):
        for record in self:
            combination_name = record._get_combination_name_variant()
            display_name = "%s (%s)" % (record.name, combination_name)
            record.variant_barcode_label = display_name

    default_qty_roll = fields.Float(string='Standard Quantity / Pack')

    def name_get(self):
        original_result = super(Product, self).name_get()
        result = []
        for record in original_result:
            product = self.browse(record[0])
            attribute_values = product.product_template_attribute_value_ids
            attribute_name = '('
            for attribute_value in attribute_values:
                if attribute_value.attribute_id.name != 'GRAMASI BELI':
                    attribute_name += f"{attribute_value.name} / "
            attribute_name = attribute_name[:-2] + ')'
            result.append((record[0], record[1] + ' ' + attribute_name))
        return result

    def display_print(self):
        self.ensure_one()
        attributes_to_exclude = ['GRAMASI BELI', 'JENIS PRINT']
        display_print_parts = []
        for attribute_line in self.attribute_line_ids:
            if attribute_line.attribute_id.name.upper() not in attributes_to_exclude:
                for value in attribute_line.value_ids:
                    display_print_parts.append(value.name)
        display_print = " / ".join(display_print_parts)
        return f"[{self.default_code}] {self.name} ({display_print})"

# class AttributeLineRel(models.Model):
#     _name = 'filter_value_variant_rel'
#     _auto = False
#
#     line_id = fields.Many2one('product.attribute')
#     value_id = fields.Many2one('product.attribute.value')

#
class ProductattributeLine(models.Model):
    _inherit = 'product.template.attribute.line'

    product_tmpl_id = fields.Many2one(
        'product.template', string="Product Template", ondelete='cascade', required=False, index=True)
    barcode_label = fields.Boolean(string='Barcode Label', default=False)

    @api.onchange('attribute_id')
    def _onchange_attribute_id2(self):

        for doc in self:

            filter_attribute_variant = []
            filter_value_variant = []
            if doc.product_tmpl_id:
                attribute_line_categ = doc.product_tmpl_id.categ_id.attribute_line_ids
                filter_attribute_variant = [
                    (6, 0, attribute_line_categ.mapped('attribute_id').ids)]
                # filter_value_variant = [(6, 0, attribute_line_categ.mapped('value_ids').filtered(lambda line: line.attribute_id.id == doc.attribute_id.id).ids)]

                doc.filter_attribute_variant = filter_attribute_variant
                # doc.filter_value_variant = filter_value_variant

    filter_attribute_variant = fields.Many2many(
        comodel_name='product.attribute',
        string='filter attribute',
    )

    filter_value_variant = fields.Many2many(
        'product.attribute.value', 'filter_value_variant_rel', 'line_id', 'value_id', string='Filter Value Variant')


class ProductCateg(models.Model):
    _inherit = 'product.category'

    attribute_line_ids = fields.Many2many(
        comodel_name='product.template.attribute.line',
        string='Variant'
    )

    attribute_ids = fields.Many2many(
        comodel_name='product.attribute',
        string='Variant',
        compute='_compute_attributes_ids')

    sequence_code_id = fields.Many2one(
        comodel_name='ir.sequence', string='Sequence Code')

    # auto_generate_product_code = fields.Boolean(
    #     string='Auto Generate Product Code', default=False)

    # @api.onchange('auto_generate_product_code')
    # def onchange_auto_generate_product_code(self):
    #     if not self.auto_generate_product_code:
    #         self.sequence_code_id = False

    @api.depends('attribute_line_ids', 'attribute_line_ids.attribute_id')
    def _compute_attributes_ids(self):
        for record in self:
            record.attribute_ids = [
                (6, 0, record.attribute_line_ids.mapped('attribute_id').ids)]


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    def search_product_qty(self):
        for doc in self:
            if doc.product_qty <= 0:
                move_line = self.env['stock.move.line'].search([('lot_id', '=', doc.id)], order='create_date DESC', limit=1)
                qty = move_line.qty_done if move_line else 0
                return int(qty)
            else:
                return int(doc.product_qty)

    