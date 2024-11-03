from odoo import models, fields, api

class NomorSeriEfakturWizard(models.TransientModel):
    _name = 'nomor.seri.efaktur.wizard'
    _description = 'Add Nomor Seri E-faktur Wizard'

    # Example field, adjust according to actual needs
    l10n_id_kode_transaksi = fields.Selection([
            ('01', '01 Kepada Pihak yang Bukan Pemungut PPN (Customer Biasa)'),
            ('02', '02 Kepada Pemungut Bendaharawan (Dinas Kepemerintahan)'),
            ('03', '03 Kepada Pemungut Selain Bendaharawan (BUMN)'),
            ('04', '04 DPP Nilai Lain (PPN 1%)'),
            ('05', '05 Besaran Tertentu (Pasal 9A ayat (1) UU PPN)'),
            ('06', '06 Penyerahan Lainnya (Turis Asing)'),
            ('07', '07 Penyerahan yang PPN-nya Tidak Dipungut (Kawasan Ekonomi Khusus/ Batam)'),
            ('08', '08 Penyerahan yang PPN-nya Dibebaskan (Impor Barang Tertentu)'),
            ('09', '09 Penyerahan Aktiva ( Pasal 16D UU PPN )'),
        ], string='Kode Transaksi', help='Dua digit pertama nomor pajak',
       )
    status_code = fields.Selection(selection=[
                  ('0', '0 - Normal'),
                  ('1', '1 - Pengganti')
                  ], string='Kode Status', default='0', required=True)
    
    nomor_seri = fields.Many2one('account.efaktur', string="Nomor Seri E-Faktur")
    l10n_id_tax_number = fields.Char('Tax Number', compute='_compute_tax_number')


    @api.depends('l10n_id_kode_transaksi', 'status_code', 'nomor_seri')
    def _compute_tax_number(self):
        for record in self:
            # Convert each field value to string, replacing False with an empty string
            kode_transaksi = record.l10n_id_kode_transaksi or ''
            status_code = record.status_code or ''
            nomor_seri = record.nomor_seri.name or ''
            
            # Concatenate the values with a specific format if needed
            record.l10n_id_tax_number = f"{kode_transaksi}{status_code}{nomor_seri}"

    def apply_nomor_seri(self):
        active_ids = self.env.context.get('active_ids')
        records = self.env['account.move'].browse(active_ids)
        # Implement the logic to add nomor seri to the selected records
        # This is a placeholder, replace with actual logic
        for record in records:
            record.write({
                'l10n_id_kode_transaksi': self.l10n_id_kode_transaksi,
                'status_code': self.status_code,
                'nomor_seri': self.nomor_seri,
                'l10n_id_tax_number': self.l10n_id_tax_number,
            })