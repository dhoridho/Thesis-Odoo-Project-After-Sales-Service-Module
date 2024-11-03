# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


class AgreementGenerate(models.TransientModel):
    _name = 'agreement.generate.wizard'
    _description = 'Generate Purchase Agreement'

    @api.model
    def default_get(self, fields):
        rec = super(AgreementGenerate, self).default_get(fields)
        lines = []
        ctx = self.env.context.copy()
        active_id = ctx.get('active_ids', [])
        material_id = self.env['material.request'].browse(active_id)
        for material in material_id.product_line:
            lines.append((0, 0, {
                'no': material.no,
                'product_id': material.product.id,
                'description': material.description,
                'uom_id': material.product_unit_measure.id,
                'destination_warehouse_id': material.destination_warehouse_id.id,
                'purchase_qty': material.quantity,
                'request_date': material.request_date,
                'pur_agreement_id': material_id.id
            }))
        rec.update({'name': material_id.name, 'vendor_id': 1,
                    'pur_agreement_line_ids': lines, })
        return rec

    name = fields.Char(string="Name")
    vendor_id = fields.Many2one(
        comodel_name='res.partner', string='Vendor', required=True)
    pur_agreement_line_ids = fields.One2many(
        'agreement.generate.wizard.line', 'pur_agreement_id')

    def generate_agreement(self):
        lines = []
        for line in self.pur_agreement_line_ids:
            lines.append((0, 0, {
                'sh_product_id': line.product_id.id,
                'sh_product_description': line.description,
                'sh_product_uom_id': line.uom_id.id,
                'dest_warehouse_id': line.destination_warehouse_id.id,
                'sh_qty': line.purchase_qty,
            }))
        agreement_id = self.env['purchase.agreement'].create({
            'partner_ids': [(6, 0, [self.vendor_id.id])],
            'sh_source': self.name,
            'is_goods_orders': True,
            'sh_purchase_agreement_line_ids': lines,
        })
        return {
            'name': _('Purchase Agreement'),
            'domain': [],
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.agreement',
            'res_id': agreement_id.id,
            'view_id': False,
            'views': [(self.env.ref('sh_po_tender_management.sh_purchase_agreement_form_view').id, 'form')],
            'type': 'ir.actions.act_window'
        }


class AgreementGenerateLine(models.TransientModel):
    _name = 'agreement.generate.wizard.line'

    no = fields.Integer('No')
    product_id = fields.Many2one(
        'product.product', string='Product')
    description = fields.Text(string='Description')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse', string='Destination Warehouse')
    purchase_qty = fields.Float("Quantity To Purchase")
    request_date = fields.Date('Request Date', required='1')
    pur_agreement_id = fields.Many2one('agreement.generate.wizard')
