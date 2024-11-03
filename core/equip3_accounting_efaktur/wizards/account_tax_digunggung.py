from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class AccountTaxDigunggung(models.TransientModel):
    _name = 'account.tax.digunggung'
    _description = 'Account Tax Digunggung'


    tax_report = fields.Selection([('keluaran','PPN Keluaran Digunggung'),('masukkan','PPN Masukan Digunggung')], string='Tax Report', required=True)
    start_date_digunggung = fields.Date('Start Date', required=True)
    end_date_digunggung = fields.Date('End Date', required=True)
    partner_id = fields.Many2one('res.partner', 'Partner', required=True)
    company_id = fields.Many2one('res.company', store=True, readonly=True, default=lambda self: self.env.company)
    
    def confirm(self):
        filt = []
        move_ids = []
        ppn_account_taxes = self.env['account.tax'].search([('is_ppn','=',True)])
        if ppn_account_taxes:
            filt.append(('tax_ids','in',ppn_account_taxes.ids))
        view_name = 'Invoices'
        for rec in self:
            view_name = rec.tax_report == 'keluaran' and 'PPN Keluaran Digunggung' or 'PPN Masukan Digunggung'
            if rec.tax_report == 'keluaran':
                filt.append(('move_id.move_type','=','out_invoice'))
            if rec.tax_report == 'masukkan':
                filt.append(('move_id.move_type','=','in_invoice'))
            if rec.partner_id:
                filt.append(('partner_id', '=', rec.partner_id.id))
            if rec.start_date_digunggung:
                filt.append(('date','>=',rec.start_date_digunggung))
            if rec.end_date_digunggung:
                filt.append(('date','<=',rec.end_date_digunggung))
            # filt.append(('move_id.l10n_id_tax_number','=',False))

            move_lines = self.env['account.move.line'].search(filt)

            if move_lines:
                move_ids = [x.move_id.id for x in move_lines]
                
        return {
            'name':  _(view_name),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,kanban,form',
            'res_model': 'account.move',
            'views_id': self.env.ref('account.view_out_invoice_tree').id,
            'domain': [('id','in',move_ids)],
        }
    
    
    