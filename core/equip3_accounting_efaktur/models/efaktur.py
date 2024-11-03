# -*- coding: utf-8 -*-

import time
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.misc import format_date
from ..models.account import AccountMove
import requests
from datetime import datetime
from lxml import etree
import json

class AccountEFaktur(models.Model):
    _name = "account.efaktur"

    year = fields.Many2one('sh.fiscal.year', string='Fiscal Year')
    record_id = fields.Integer()
    name = fields.Char(string='eFaktur Number', size=15, help="E-Faktur Format xxx-xx-xxxxxxxx")
    is_used = fields.Boolean(string='Is Used',default=False, compute='_compute_is_use')
    invoice_id = fields.One2many('account.move','nomor_seri', string='Invoice', domain="[('nomor_seri', 'in', [False,'']), ('state', 'in', ['posted']),('move_type', 'in', ['out_invoice','out_refund','out_receipt'])]")
    partner_id = fields.Many2one('res.partner', string='Customer', related='invoice_id.partner_id')
    invoice_date = fields.Date(string='last use on invoice date')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    is_pjap = fields.Boolean('Is PJAP')
    is_used_pjap = fields.Boolean(string='Is Used PJAP')
    branch_id = fields.Many2one('res.branch', readonly=True)
    is_cancel = fields.Boolean('Is Cancel')

    _sql_constraints = [
        ('name_uniq', 'unique (name, company_id)', 'The Nomor Seri Faktur Pajak is already generated. Please check your Nomor Seri Faktur Pajak')
    ]

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        result = super(AccountEFaktur, self).fields_view_get(view_id, view_type, toolbar=toolbar, submenu=submenu)
        doc = etree.XML(result['arch'])
        if self.env.company.is_centralized_efaktur != False:
            for field in doc.xpath('//field[@name="branch_id"]'):
                modifiers = json.loads(field.get('modifiers', '{}'))
                modifiers['column_invisible'] = True
                field.set('modifiers', json.dumps(modifiers))

        result['arch'] = etree.tostring(doc, encoding='unicode')
        return result

    @api.depends('partner_id')
    def _compute_is_use(self):
        for rec in self:
            if rec.partner_id.id == False:
                rec.is_used = False
            else:
                rec.is_used = True
                inv_id=[]
                for x in rec.invoice_id:
                    if not isinstance(x.id, models.NewId):
                        inv_id.append(x._origin.id)
                inv = self.env['account.move'].search([('id','in',inv_id)], order='invoice_date desc',limit=1)
                if len(inv)>0:
                    rec.invoice_date = inv[0].invoice_date

    @api.model
    def default_get(self, default_fields):
        """If we're creating a new account through a many2one, there are chances that we typed the account invoice_date
        instead of its name. In that case, switch both fields values.
        """
        if 'name' not in default_fields and 'invoice_date' not in default_fields:
            return super().default_get(default_fields)
        default_name = self._context.get('default_name')
        default_invoice_date = self._context.get('default_invoice_date')
        if default_name and not default_invoice_date:
            try:
                default_invoice_date = default_name
            except ValueError:
                pass
            if default_invoice_date:
                default_name = False
        contextual_self = self.with_context(default_name=default_name, default_invoice_date=default_invoice_date)
        return super(AccountEFaktur, contextual_self).default_get(default_fields)

    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #     args = args or []
    #     domain = []
    #     if name:
    #         domain = ['|', ('name', '= ilike', name.split(' ')[0] + '%'), ('name', operator, name)]
    #         if operator in expression.NEGATIVE_TERM_OPERATORS:
    #             domain = ['&', '!'] + domain[1:]
    #     return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        result = []
        for account in self:
            name = account.name + ' ' +  str(account.invoice_date)
            result.append((account.id, name))
        return result

    def name_get(self):
        result = []
        for res in self:
            if res.is_used == False:
                name = res.name
            else:
                invoice=''
                for inv in self.invoice_id:
                    invoice = format_date(self.env, inv.invoice_date) + ' '
                name = res.name + ' Last used on ' + format_date(self.env, res.invoice_date)
                # name = res.name + ' Last used on' + invoice
            result.append((res.id, name))
        return result

    def unlink(self):
        for rec in self:
            for invoice in rec.invoice_id:
                if invoice.state == 'posted':
                    raise UserError(_('Posted tax number cannot be deleted'))
        return super(AccountEFaktur,self).unlink()


class AccountEFakturGenerate(models.Model):
    _name = "account.efaktur.generate"


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    year = fields.Many2one('sh.fiscal.year', string='Year')
    nsfp_id = fields.Many2one('nsfp.registration','NSFP Range')
    start = fields.Char(string='Start', size=15, help="E-Faktur Format xxx-xx-xxxxxxxx")
    end = fields.Char(string='End', size=15, help="E-Faktur Format xxx-xx-xxxxxxxx")
    is_pajak_express_integration = fields.Boolean('Is Pajak Express Integration', compute='_compute_pajak_integration')
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)
    is_centralized_efaktur = fields.Boolean('Centralized E-Faktur', compute='_compute_is_centralized_efaktur')
    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch)    

    @api.depends('company_id')
    def _compute_is_centralized_efaktur(self):
        for rec in self:
            rec.is_centralized_efaktur = rec.company_id.is_centralized_efaktur
        
    @api.depends('year')
    def _compute_pajak_integration(self):
        for rec in self:
            is_pajak_express_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
            rec.is_pajak_express_integration = is_pajak_express_integration

    def _prepare_efaktur_integration_line(self,prefix,year,start,end,record_id,branch):
        list_line=[]
        for x in range(int(start),int(end)+1):
            lines_dict={'record_id':record_id,
                        'is_pjap': True,
                        'year': year,
                        'name': str(prefix) + str(self._addnumb(x)),                            
                        'branch_id': branch,
                        }
            list_line.append(lines_dict)
        return list_line
    
    def _prepare_efaktur_line(self,prefix,year,start,end,branch):
        list_line=[]
        for x in range(int(start),int(end)+1):
            lines_dict={'year': year,
                        'name': str(prefix) + str(self._addnumb(x)),                            
                        'branch_id': branch,
                        }
            list_line.append(lines_dict)
        return list_line

    def _addnumb(self,number):
        numb = str(number)        
        while len(numb) < 8:
            numb = str('0') + str(numb)
        return numb

    def confirm(self):
        prefix=''
        years=''
        start_number = ''
        end_number = ''
        for vals in self:
            is_pajak_express_integration = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration', False)
            if is_pajak_express_integration:
                if vals.nsfp_id.start and vals.nsfp_id.end:
                    if len(vals.nsfp_id.start) < 15 or len(vals.nsfp_id.end) < 15:
                        raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                else:
                    raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                start = vals.nsfp_id.start
                end = vals.nsfp_id.end
                if start[3] != '-' or start[6] != '-' or end[3] != '-' or end[6] != '-' or start[4:6] != end[4:6] or start[:3] != end[:3]:
                    raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                prefix = vals.nsfp_id.start[:7]
                years = vals.year.id
                branch = vals.branch_id.id
                start_number = vals.nsfp_id.start[7:]
                end_number = vals.nsfp_id.end[7:]
                if start[4:6].isnumeric() == False or end[4:6].isnumeric() == False or start[:3].isnumeric() == False or end[:3].isnumeric() == False or end_number.isnumeric() == False or end_number.isnumeric() == False:
                    raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                list_line = self._prepare_efaktur_integration_line(prefix,years,start_number,end_number,vals.nsfp_id.record_id,branch)
            else:
                if vals.start and vals.end:
                    if len(vals.start) < 15 or len(vals.end) < 15:
                        raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                else:
                    raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                start = vals.start
                end = vals.end
                if start[3] != '-' or start[6] != '-' or end[3] != '-' or end[6] != '-' or start[4:6] != end[4:6] or start[:3] != end[:3]:
                    raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                prefix = vals.start[:7]
                years = vals.year.id
                branch = vals.branch_id.id
                start_number = vals.start[7:]
                end_number = vals.end[7:]
                if start[4:6].isnumeric() == False or end[4:6].isnumeric() == False or start[:3].isnumeric() == False or end[:3].isnumeric() == False or end_number.isnumeric() == False or end_number.isnumeric() == False:
                    raise UserError(_("Please check your region code and year code at your Nomor E-Faktur !"))
                list_line = self._prepare_efaktur_line(prefix,years,start_number,end_number,branch)
        efaktur = self.env['account.efaktur'].create(list_line)
        vals.nsfp_id.is_use = True
        return {
                'name':  _('E-Faktur'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.efaktur',
                'views_id': self.env.ref('equip3_accounting_efaktur.view_account_efaktur_tree').id,
                'domain': [('name', 'in', [x['name'] for x in list_line])]
            }

class EfakturExport(models.Model):
    _name = 'efaktur.export'

    partner_id = fields.Many2one('res.partner', string='Customer', domain="[('country_id','=',100),('l10n_id_pkp','=',True)]")
    tax_report_id = fields.Selection([
        ('in', 'PPN Masukan'),('out','PPN Keluaran')
    ], string='Tax Report', default='out')
    date_from = fields.Date(string='Start Date', default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, tracking=True, readonly=True)
    unduh = fields.Binary(
        string='Download All E-Faktur',
    )
    
    
    @api.onchange('date_from','date_to')
    def _checkvalid(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                check = time.mktime(rec.date_to.timetuple()) - time.mktime(rec.date_from.timetuple())
                if check < 0:
                    raise UserError('End Date Must Be Greater Than Start Date!')
    
    def confirm(self):
        allowed_tax = self.env['account.tax'].search([('is_ppn','=',True)])
        filt = [('state','=','posted'), ('move_type','=','out_invoice'), ('amount_tax_signed','!=',0),('line_ids.tax_ids','in',allowed_tax.ids)]
        # filt = [('state','=','posted'), ('move_type','=','out_invoice')]
        pajak_express = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
        if pajak_express:
            filt.append(('is_upload_djp','=',True))
        for rec in self:
            if rec.partner_id:
                filt.append(('partner_id', '=', f'{rec.partner_id.name}'))
            if rec.date_from:
                filt.append(('invoice_date','>=',f'{rec.date_from}'))
            if rec.date_to:
                filt.append(('invoice_date','<=',f'{rec.date_to}'))
            return {
                'name':  _('PPN Keluaran'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_out_invoice_tree').id,
                'domain': f"{filt}",
                'context' : {'default_move_type': 'out_invoice',
                             'is_ppn_invisible': False,
                             'def_invisible': True,
                             'partner_id.l10n_id_pk': True,
                             'partner_id.vat': True
                             },
            }

class ExportEfaktur(models.Model):
    _name = 'export.efaktur'

    partner_id = fields.Many2one('res.partner', string='Vendor', domain="[('country_id','=',100)]")
    tax_report_id = fields.Selection([
        ('in', 'PPN Masukan'),('out','PPN Keluaran')
    ], string='Tax Reports', default='in')
    date_from = fields.Date(string='Start Date', default=fields.Date.context_today)
    date_to = fields.Date(string='End Date', default=fields.Date.context_today)
    company_id = fields.Many2one(
        'res.company', string='Company',
        default=lambda self: self.env.company, tracking=True, readonly=True)
    
    @api.onchange('date_from','date_to')
    def _checkvalid(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                check = time.mktime(rec.date_to.timetuple()) - time.mktime(rec.date_from.timetuple())
                if check < 0:
                    raise UserError('End Date Must Be Greater Than Start Date!')
    
    def confirm(self):
        allowed_tax = self.env['account.tax'].search([('is_ppn','=',True)])
        pajak_express = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
        filt = [('state','=','posted'), ('move_type','=','in_invoice'), ('amount_tax_signed','!=',0),('line_ids.tax_ids','in',allowed_tax.ids)]
        # filt = [('state','=','posted'), ('move_type','=','in_invoice')]
        if pajak_express:
            filt.append(('is_upload_pajak_masukkan','=',True))
        for rec in self:
            if rec.partner_id:
                filt.append(('partner_id', '=', f'{rec.partner_id.name}'))
            if rec.date_from:
                filt.append(('invoice_date','>=',f'{rec.date_from}'))
            if rec.date_to:
                filt.append(('invoice_date','<=',f'{rec.date_to}'))
            
            return {
                'name':  _('PPN Masukan'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_in_invoice_tree').id,
                'domain': f"{filt}",
                'context' : {'default_move_type': 'in_invoice',
                             'is_ppn_invisible': False,
                             'def_invisible': True,
                             'partner_id.l10n_id_pk':True,
                             'partner_id.vat':True
                             }
            }
            
class ExportPajakKeluaran(models.Model):
    _name = 'export.retur.pajak.keluaran'

    partner_id = fields.Many2one('res.partner', string='Customer')
    date_from = fields.Date(string='Start Date',)
    date_to = fields.Date(string='End Date',)
    tax_report_id = fields.Selection([
        ('in', 'Pajak Masukan'),
        ('out', 'Pajak Keluaran'),
        ('retur_in', 'Retur Pajak Masukan'),
        ('retur_out', 'Retur Pajak Keluaran')
    ], string='Tax Reports', default='retur_out')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True, readonly=True)

    @api.onchange('date_from','date_to')
    def _checkvalid(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                check = time.mktime(rec.date_to.timetuple()) - time.mktime(rec.date_from.timetuple())
                if check < 0:
                    raise UserError('End Date Must Be Greater Than Start Date!')
                
    def confirm(self):
        filt = [('state','=','posted'),('move_type','=','out_refund'),('partner_id.l10n_id_pkp','=',True)]
        pajak_express = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
        if pajak_express:
            filt.append(('is_upload_djp_cn','=',True))
        for rec in self:
            if rec.partner_id:
                filt.append(('partner_id', '=', f'{rec.partner_id.name}'))
            if rec.date_from:
                filt.append(('invoice_date','>=',f'{rec.date_from}'))
            if rec.date_to:
                filt.append(('invoice_date','<=',f'{rec.date_to}'))
            return {
                'name':  _('Retur Pajak Keluaran'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_invoice_tree').id,
                'domain': f"{filt}",
                'context' : {'default_move_type': 'out_refund',
                             'is_ppn_invisible': False,
                             'def_invisible': True,
                             'partner_id.l10n_id_pk':True,
                             'partner_id.vat':True
                             }
            }
        
class ExportPajakMasukan(models.Model):
    _name = 'export.retur.pajak.masukan'

    partner_id = fields.Many2one('res.partner', string='Customer')
    date_from = fields.Date(string='Start Date',)
    date_to = fields.Date(string='End Date',)
    tax_report_id = fields.Selection([
        ('in', 'Pajak Masukan'),
        ('out', 'Pajak Keluaran'),
        ('retur_in', 'Retur Pajak Masukan'),
        ('retur_out', 'Retur Pajak Keluaran')
    ], string='Tax Reports', default='retur_in')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True, readonly=True)

    @api.onchange('date_from','date_to')
    def _checkvalid(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                check = time.mktime(rec.date_to.timetuple()) - time.mktime(rec.date_from.timetuple())
                if check < 0:
                    raise UserError('End Date Must Be Greater Than Start Date!')
                
    def confirm(self):
        filt = [('state','=','posted'), ('move_type','=','in_refund'),('partner_id.l10n_id_pkp','=',True)]
        pajak_express = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.is_pajak_express_integration')
        if pajak_express:
            filt.append(('is_upload_pajak_masukkan','=',True))
        for rec in self:
            if rec.partner_id:
                filt.append(('partner_id', '=', f'{rec.partner_id.name}'))
            if rec.date_from:
                filt.append(('invoice_date','>=',f'{rec.date_from}'))
            if rec.date_to:
                filt.append(('invoice_date','<=',f'{rec.date_to}'))
            return {
                'name':  _('Retur Pajak Masukan'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree,kanban,form',
                'res_model': 'account.move',
                'views_id': self.env.ref('account.view_in_invoice_tree').id,
                'domain': f"{filt}",
                'context' : {'default_move_type': 'in_refund',
                             'is_ppn_invisible': False,
                             'def_invisible': True,
                             'partner_id.l10n_id_pk':True,
                             'partner_id.vat':True
                             }
            }

class NSFPRegistration(models.Model):
    _name = "nsfp.registration"
    _order = "id desc"
    
    record_id =  fields.Integer()
    fiscal_year = fields.Many2one('sh.fiscal.year')
    start = fields.Char(string='Start', size=100, help="E-Faktur Format xxx-xx-xxxxxxxx" ,default="0000000000000")
    end = fields.Char(string='End', size=100,default="0000000000000")
    last_number  = fields.Char()
    registration_date = fields.Char()
    is_use = fields.Boolean()
    company_id = fields.Many2one('res.company', string='Company')
    
    
    def syncron_djp(self):
        self.ensure_one()
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            x_token = self.company_id.pjap_x_token
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token}
            pajak_get = requests.get(pajak_express_transaction_url+f"/efaktur/nsfp?id={self.record_id}",headers=header_x)
            pajak_get_response =  pajak_get.json()
            pajak_formatted = pajak_get_response['data'][0]['terakhir'][:3] + "-" + pajak_get_response['data'][0]['terakhir'][3:5] + "-" + pajak_get_response['data'][0]['terakhir'][5:]
            date_obj = datetime.strptime(pajak_get_response['data'][0]['tanggal'] , '%Y%m%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            self.registration_date = formatted_date
            self.last_number = pajak_formatted
        
    
    def name_get(self):
        result = []
        for record in self:
            result.append((record.id, "{} to {}".format(record.start, record.end)))
        return result
    
    def unlink(self):
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            for record in self:
                x_token = record.company_id.pjap_x_token
                header_x = {"Authorization": f"Bearer {token}",
                            "x-token":x_token
                            }
                json_request = {"id": str(record.record_id)}
                pajak_nsfp = requests.post(pajak_express_transaction_url + "/efaktur/nsfp/delete",headers=header_x,json=json_request)
                pajak_response =  pajak_nsfp.json()
                if pajak_response['status'] == 0:
                    raise ValidationError(f"{pajak_response['message']}")
                faktur_to_delete = self.env['account.efaktur'].search([('record_id','=',record.record_id)])
                if faktur_to_delete:
                    for data in faktur_to_delete:
                        if not data.is_used:
                            data.unlink()
                        
    
        return super(NSFPRegistration,self).unlink()
    
    def write(self, vals):
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            if 'company_id' in vals:
                company_vals = vals.get('company_id')
                company = self.env['res.company'].browse(company_vals)
                x_token = company.pjap_x_token
            else:
                x_token = self.company_id.pjap_x_token
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token}
            json_request = {}
            if 'start' in vals and 'end' in vals:
                json_request = {"id": self.record_id,
                                "nfAwal": str(vals['start']).replace('-',''),
                                "nfAkhir": str(vals['end']).replace('-',''),
                                "tanggal": datetime.now().strftime("%Y%m%d"),
                                "terakhir": ""
                                }
            elif 'start' in vals and not 'end' in vals:
                json_request = {"id": self.record_id,
                                "nfAwal": str(vals['start']).replace('-',''),
                                "nfAkhir": str(self.end).replace('-',''),
                                "tanggal": datetime.now().strftime("%Y%m%d"),
                                "terakhir": ""
                                }
            elif not 'start' in vals and 'end' in vals:
                json_request = {"id": self.record_id,
                                "nfAwal": str(self.start).replace('-',''),
                                "nfAkhir": str(vals['end']).replace('-',''),
                                "tanggal": datetime.now().strftime("%Y%m%d"),
                                "terakhir": ""
                                }
            pajak_nsfp = requests.post(pajak_express_transaction_url + "/efaktur/nsfp",headers=header_x,json=json_request)
            pajak_response =  pajak_nsfp.json()
            if pajak_response['status'] == 0:
                raise ValidationError(f"{pajak_response['message']}")
            pajak_get = requests.get(pajak_express_transaction_url+f"/efaktur/nsfp?id={self.record_id}",headers=header_x)
            pajak_get_response =  pajak_get.json()
            pajak_formatted = pajak_get_response['data'][0]['terakhir'][:3] + "-" + pajak_get_response['data'][0]['terakhir'][3:5] + "-" + pajak_get_response['data'][0]['terakhir'][5:]
            date_obj = datetime.strptime(pajak_get_response['data'][0]['tanggal'] , '%Y%m%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            vals.update({'last_number':pajak_formatted,'registration_date':formatted_date})
        result =  super(NSFPRegistration,self).write(vals)
        return result
    
    
    def generate_api_secret(self,url,npwp,token):
        header = {"Authorization": f"Bearer {token}",
                   "npwp":npwp
                   }
        api_secret = requests.get(url + '/api/client-store',headers=header)
        secret_response =  api_secret.json()
        header_x = {"Authorization": f"Bearer {token}",
                    "X-Tenant":"foo",
                    "api-key":secret_response['data']['api_key'],
                    "api-secret":secret_response['data']['api_secret']
                   }
        x_token = requests.post(url+"/api/client-token",headers=header_x)
        x_token_response = x_token.json()
        return x_token_response['data']['token']
    
    @api.onchange('fiscal_year')
    def _onchange_fiscal_year(self):
        for record in self:
            input_format = '%Y'
            output_format = '%y'
            if record.fiscal_year:
                year = datetime.strptime(record.fiscal_year.name,input_format)
                start = str(record.start)
                start = start[:3] + year.strftime(output_format) + start[5:]
                record.start = start
                
                end = str(record.end)
                end = end[:3] + year.strftime(output_format) + end[5:]
                record.end = end
                
                
    def pajak_express_url(self):
        pajak_express_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_url')
        return pajak_express_url
    
    def pajak_express_transaction_url(self):
        pajak_express_transaction_url = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_transaction_url')
        return pajak_express_transaction_url
        
   
    def login(self):
       pajak_express_url = self.pajak_express_url()
       pajak_express_username = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_username')
       pajak_express_password = self.env['ir.config_parameter'].sudo().get_param('equip3_accounting_efaktur.pajak_express_password')
       payload = {'email':pajak_express_username,'password':pajak_express_password}
       login = requests.post(pajak_express_url + '/api/login',data=payload)
       return login
    
    
    @api.model
    def create(self, vals):
        result = super(NSFPRegistration, self).create(vals)
        pajak_express_transaction_url = self.pajak_express_transaction_url()
        login  = self.login()
        if login.status_code == 200:
            response = login.json()
            token = response['data']['token']
            x_token = result.company_id.pjap_x_token
            header_x = {"Authorization": f"Bearer {token}",
                        "x-token":x_token
                        }
            json_request = {"id": None,
                            "nfAwal": str(result.start).replace('-',''),
                            "nfAkhir": str(result.end).replace('-',''),
                            "tanggal": datetime.now().strftime("%Y%m%d"),
                            "terakhir": ""
                            }
            pajak_nsfp = requests.post(pajak_express_transaction_url + "/efaktur/nsfp",headers=header_x,json=json_request)
            pajak_response =  pajak_nsfp.json()
            if pajak_response['status'] == 0:
                raise ValidationError(f"{pajak_response['message']}")
             
            result.record_id = pajak_response['data']['id']    
            pajak_get = requests.get(pajak_express_transaction_url+f"/efaktur/nsfp?id={result.record_id}",headers=header_x)
            pajak_get_response =  pajak_get.json()
            pajak_formatted = pajak_get_response['data'][0]['terakhir'][:3] + "-" + pajak_get_response['data'][0]['terakhir'][3:5] + "-" + pajak_get_response['data'][0]['terakhir'][5:]
            date_obj = datetime.strptime(pajak_get_response['data'][0]['tanggal'] , '%Y%m%d')
            formatted_date = date_obj.strftime('%Y-%m-%d')
            result.last_number = pajak_formatted   
            result.registration_date = formatted_date 
        return result


    @api.onchange('company_id')
    def _onchange_company_id(self):
        for rec in self:
            if rec.company_id and not rec.company_id.pjap_x_token:
                raise ValidationError(_('You need to generate x-token first in Company.'))