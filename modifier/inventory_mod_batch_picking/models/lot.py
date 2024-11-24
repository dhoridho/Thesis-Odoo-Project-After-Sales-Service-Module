from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    no_container = fields.Char(string='Nomor Container', store=True)
    qc_date = fields.Date(string='Quality Control Date')
    pack_grade = fields.Selection(string='Grade', selection=[(
        'a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E')], default='a')
    stock_owner_id = fields.Many2one('res.partner', string='Stock Owner')
    active = fields.Boolean(string="Active", default=True)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    stock_owner_id = fields.Many2one(related='lot_id.stock_owner_id')
    no_container = fields.Char(related='lot_id.no_container')
    pack_grade = fields.Selection(string='Grade', selection=[(
        'a', 'A'), ('b', 'B'), ('c', 'C'), ('d', 'D'), ('e', 'E')], default='a', related='lot_id.pack_grade')
    warna = fields.Char(string='Warna', related='product_id.warna')
    lebar = fields.Char(string='Lebar', related='product_id.lebar')
    k_motif = fields.Char(string='Kode Motif', related='product_id.k_motif')
    jenis_print = fields.Char(string='Jenis Print', related='product_id.jenis_print')
    jenis_kain = fields.Char(string='Jenis Kain', related='product_id.jenis_kain')
    gr_jual = fields.Char(string='Gramasi', related='product_id.gr_jual')
    gr_beli = fields.Char(string='Gramasi Beli', related='product_id.gr_beli')
    alias_print = fields.Char(string='Alias Jenis Print', related='product_id.alias_print')
    panjang = fields.Char(string='Panjang', related='product_id.panjang')

    def fix_no_container(self):
        for rec in self:
            rec.write({
                'no_container': rec.lot_id.no_container or False
            })