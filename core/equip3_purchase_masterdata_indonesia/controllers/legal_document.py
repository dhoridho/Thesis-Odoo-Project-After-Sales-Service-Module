import base64
from io import BytesIO
from zipfile import ZipFile

from odoo import http
from odoo.http import request

class DownloadZipFile(http.Controller):
    @http.route("/download_attachments/", type="http", auth="user", website=True, cors="*")
    def download_attachments_vendor_routes(self, **data):
        partner_obj = request.env['res.partner'].search([('id', '=', data.get('res_id'))])

        for partner_rec in partner_obj:
            res_field_value = []
            if partner_rec.file_siup:
                res_field_value.append('file_siup')
            if partner_rec.salinan_anggaran_dasar:
                res_field_value.append('salinan_anggaran_dasar')
            if partner_rec.surat_persetujuan_dirjen_ahu:
                res_field_value.append('surat_persetujuan_dirjen_ahu')
            if partner_rec.akta_perubahan_pengurus_terakhir:
                res_field_value.append('akta_perubahan_pengurus_terakhir')
            if partner_rec.surat_keterangan_tidak_kena_pajak:
                res_field_value.append('surat_keterangan_tidak_kena_pajak')
            if partner_rec.surat_pernyataan_dan_kuasa:
                res_field_value.append('surat_pernyataan_dan_kuasa')

        attachments_items = request.env["ir.attachment"].sudo().search(
            [("res_id", "=", data.get('res_id')),
             ('res_model', '=', 'res.partner'),
             ('res_field', 'in', res_field_value)])

        in_memory = BytesIO()
        zip_archive = ZipFile(in_memory, "w")

        for attachment in attachments_items:
            ext = '.' + attachment.mimetype.split('/')[1]
            if ext == '.vnd.openxmlformats-officedocument.wordprocessingml.document':
                ext = '.docx'
            zip_archive.writestr(f"{attachment.name}{ext}", base64.b64decode(attachment.datas))

        zip_archive.close()
        res = http.send_file(in_memory, filename="LegalDocuments.zip", as_attachment=True)
        return res
