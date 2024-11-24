from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
from PyPDF2 import PdfFileMerger
class StockMove(models.Model):
    _inherit = 'stock.move'

    qty_to_generate = fields.Float(string='Quantity to Generate')

    attachment_pdf_ids = fields.One2many('move_attachment.lot_pdf', 'move_id', string='Attachment PDF')
    qty_per_lot = fields.Integer(string="Quantity Per Lot")


    @api.onchange('product_id')
    def onchange_assign_lot(self):
        for res in self :
            res.qty_per_lot = res.product_id.default_qty_roll


    def action_show_details(self):
        self.ensure_one()
        action = super(StockMove,self).action_show_details()
        action['context']['default_qty_per_lot'] = self.product_id.default_qty_roll
        # action['context']['default_qty_to_generate'] = self.dpl_quantity
        self.onchange_assign_lot()
        # self.onchange_to_generate()
        self.onchange_get_attributes()
        return action



    # product_template_attribute_value_ids

    attributes_ids = fields.Many2many(
        comodel_name='product.attribute',
        relation='product_atrtribute_id_rel',
        column1='productattr_id',
        column2='atrtribute_id',
        string='Attributes'
        )


    @api.onchange('product_id')
    def onchange_get_attributes(self):
        for record in self :
            if record.product_id :
                true_barcode_label = record.product_id.product_tmpl_id.attribute_line_ids

                variant_product = record.product_id.product_template_attribute_value_ids.filtered(lambda a:  a.attribute_id in true_barcode_label.mapped("attribute_id"))

                record.attributes_ids = [(6, 0, variant_product.mapped("attribute_id").ids)]

    def _get_combination_name_variant(self):
        """Exclude values from single value lines or from no_variant attributes."""

        variant_product = self.product_id.product_template_attribute_value_ids.filtered(lambda a:  a.attribute_id in self.attributes_ids)
        return variant_product

    binary_merge_pdf = fields.Binary(string='Report ')
    file_name = fields.Char(string='File Name')

    def merge_pdf(self):
        # Validasi untuk memastikan PDF telah dihasilkan dan belum digabungkan
        pdf_content = []

        # Mengumpulkan semua file PDF yang telah dihasilkan
        for pdf in self.attachment_pdf_ids.filtered(lambda x: x.is_generated == True):
            pdf_content.append(base64.b64decode(pdf.binary_pdf))

        # Menggabungkan semua PDF menggunakan PyPDF2
        merger = PdfFileMerger()
        for pdf in pdf_content:
            merger.append(io.BytesIO(pdf))

        merged_pdf_io = io.BytesIO()
        merger.write(merged_pdf_io)
        merger.close()

        # Menyimpan hasil PDF yang telah digabungkan ke binary field
        self.binary_merge_pdf = base64.b64encode(merged_pdf_io.getvalue())
        self.file_name = f"{self.product_id.display_name} Lot Barcode Label.pdf"
    def generate_label_report(self):
        self.attachment_pdf_ids = [(5, 0, 0)]
        # variant_product = self._get_combination_name_variant()
        lot_ids = self.move_line_ids.mapped('lot_id')
        if not lot_ids :
            # move_line = self.move_line_ids.mapped('lot_name')
            move_line = self.move_line_ids
            batch_size = 50
            for i in range(0, len(move_line), batch_size):
                batch = move_line[i:i + batch_size]

                self.attachment_pdf_ids.create({
                        'move_id': self.id,
                        'move_line_ids': [(6, 0, batch.ids)],
                        'is_generated': False
                    })



        lot_ids = self.lot_ids
        batch_size = 50
        for i in range(0, len(lot_ids), batch_size):
            batch = lot_ids[i:i + batch_size]

            self.attachment_pdf_ids.create({
                'move_id': self.id,
                'lot_ids': [(6, 0, batch.ids)],
                'is_generated': False
            })



class BarcodeLabel(models.AbstractModel):
    _name = 'report.stock.report_lot_label'
    _description = "Barcode label"


    @api.model
    def _get_report_values(self, docids, data=None):
        attributes_name = False

        lot = self.env['stock.production.lot'].browse(docids)
        if 'lot_ids' in data :
            lot = self.env['stock.production.lot'].browse(data['lot_ids'])
            # attributes_name = data['attributes_name']

        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'stock.production.lot',
            'docs': lot,
            # 'attributes_name': attributes_name,
        }

class BarcodeLabel2(models.AbstractModel):
    _name = 'report.inventory_mod.report_lot_label_move'
    _description = "Barcode label Move"


    @api.model
    def _get_report_values(self, docids, data=None):
        attributes_name = False

        move_line = self.env['stock.move.line'].browse(docids)
        if 'move_line' in data :
            move_line = self.env['stock.move.line'].browse(data['move_line'])
            # attributes_name = data['attributes_name']

        return {
            'data': data,
            'doc_ids': docids,
            'doc_model': 'stock.move.line',
            'docs': move_line,
            # 'attributes_name': attributes_name,
        }



class Attachment_lot_pdf(models.Model):
    _name = 'move_attachment.lot_pdf'
    _description = "Barcode label Move"

    name = fields.Char(string='Name', compute='get_name', store=True)
    move_id = fields.Many2one('stock.move', string='Move')
    move_line_ids = fields.Many2many('stock.move.line', string='Move Line')
    lot_ids = fields.Many2many('stock.production.lot', string='Lot')
    binary_pdf = fields.Binary(string='PDF')
    is_generated = fields.Boolean(string='Is Generated', default=False)
    is_merged = fields.Boolean(string='Is Merged', default=False)

    @api.depends('move_id')
    def get_name(self):
        for res in self :
            res.name = res.move_id.picking_id.name or res.move_id.name or ""

    def generate_pdf(self):
        for res in self :
            if res.move_line_ids:
                data = {'move_line': res.move_line_ids.ids}
                pdf_content, _ = res.env.ref('inventory_mod.action_report_lot_label_move')._render_qweb_pdf(res.move_line_ids.ids,data=data)
                res.binary_pdf = base64.b64encode(pdf_content)
                res.is_generated = True
            if res.lot_ids:
                data = {'lot_ids': res.lot_ids.ids,'attributes_name': []}
                pdf_content, _ = res.env.ref('stock.action_report_lot_label')._render_qweb_pdf(res.lot_ids.ids,data=data)
                res.binary_pdf = base64.b64encode(pdf_content)
                res.is_generated = True

    def reset_generate_pdf(self):
        for res in self :
            res.binary_pdf = False
            res.is_generated = False


    def cron_generate_pdf(self):
        records = self.search([('is_generated','=',False)],limit=1)
        records.sudo().generate_pdf()
        return

    def merge_pdf(self):
        # Collect all PDFs from selected records
        pdf_content = []
        move_lines = self.env['stock.move.line']
        common_name = self[0].name

        for record in self:
            if record.name != common_name:
                raise UserError("All records must have the same name.")
            if record.binary_pdf:
                pdf_content.append(base64.b64decode(record.binary_pdf))
                move_lines |= record.move_line_ids

        # Merge PDFs using PyPDF2
        merger = PdfFileMerger()
        for pdf in pdf_content:
            merger.append(io.BytesIO(pdf))

        merged_pdf_io = io.BytesIO()
        merger.write(merged_pdf_io)
        merger.close()

        # Create a new record with the merged PDF and associated move lines
        new_record = self.create({
            'move_id': self[0].move_id.id,  # Assuming all records have the same move_id
            'move_line_ids': [(6, 0, move_lines.ids)],
            'binary_pdf': base64.b64encode(merged_pdf_io.getvalue()),
            'is_generated': True,
            'is_merged': True,
        })
        new_record.name = common_name + ' (merge)'
        new_record.display_name = common_name + ' (merge)'

        return new_record
