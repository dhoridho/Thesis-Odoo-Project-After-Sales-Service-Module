# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from psycopg2 import OperationalError
from odoo.http import request
from lxml import etree
from urllib.parse import urlparse
import os
import csv
import logging

_logger = logging.getLogger(__name__)


class CeisaBeacukaiOffice(models.Model):
    _name = 'ceisa.beacukai.office'
    _description = 'Beacukai Office'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaBeacukaiOffice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')
    state = fields.Boolean('State', default=False)


class CeisaPabeanOffice(models.Model):
    _name = 'ceisa.pabean.office'
    _description = 'Pabean Office'

    @api.model
    def default_get(self, fields):
        res = super(CeisaPabeanOffice, self).default_get(fields)
        # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
        ceisa_inventory = self.env.company.is_ceisa_it_inventory
        if ceisa_inventory:
            res['is_ceisa_it_inventory'] = ceisa_inventory
        return res

    def _default_value_ceisa(self):
        # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
        ceisa_inventory = self.env.company.is_ceisa_it_inventory
        if ceisa_inventory:
            return True
        return False

    name = fields.Char('Name')
    code = fields.Char('Code')
    country_code = fields.Char('Country Code')
    beacukai_office_id = fields.Many2one('ceisa.beacukai.office')
    country_id = fields.Many2one('res.country', string='Country')
    # country_id = fields.Many2one('res.country', string='Country', compute="_compute_country", store=True)
    is_ceisa_it_inventory = fields.Boolean(string='Set Ceisa 4.0', default=_default_value_ceisa)

    _sql_constraints = [
        ('pabean_office_code_uniq', 'UNIQUE(code)', 'Code of Port already exist or should be unique'),
    ]


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        Overrides orm field_view_get.
        @return: Dictionary of Fields, arch and toolbar.
        """
        res = super(CeisaPabeanOffice, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        custom_view = self.env['ir.ui.view.custom'].search([('user_id', '=', self.env.uid), ('ref_id', '=', view_id)], limit=1)
        if custom_view:
            res.update({'custom_view_id': custom_view.id,
                        'arch': custom_view.arch})
        res.update({
            'arch': self._arch_preprocessing(res['arch']),
            'toolbar': {'print': [], 'action': [], 'relate': []}
        })
        return res

    @api.model
    def _arch_preprocessing(self, arch):
        def remove_unauthorized_children(node):
            for child in node.iterchildren():
                if child.tag == 'action' and child.get('invisible'):
                    node.remove(child)
                else:
                    remove_unauthorized_children(child)
            return node

        archnode = etree.fromstring(arch)
        # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
        ceisa_inventory = self.env.company.is_ceisa_it_inventory
        if ceisa_inventory:
            archnode.set('js_class', 'button_ports_masterdata')

        return etree.tostring(remove_unauthorized_children(archnode), pretty_print=True, encoding='unicode')

    @api.depends('code')
    def _compute_country(self):
        '''Method to compute user.'''
        for rec in self:
            country_code = rec.code[:2]
            country_id = self.env['res.country'].browse(country_code).id
            rec.country_id = country_id

    @api.model
    def get_national_masterdata(self):
        max_rows = self.env['ir.config_parameter'].get_param('ceisa.master.data.import.rows')
        # if int(max_rows) > 1000:
        #     raise ValidationError('Maximum rows has been limit for 1000 records.')
        line = keys = ['code', 'name']
        cursor = self.pool.cursor()
        try:
            directory = os.path.realpath(os.path.join(os.path.dirname(__file__), '../data/files'))
            filename = directory + '/national_ports.csv'
            file_reader = []
            vals_list = []
            with open(filename, 'r') as file:
                csvreader = csv.reader(file, delimiter=',')
                file_reader.extend(csvreader)
                for i in range(len(file_reader)):
                    field = list(map(str, file_reader[i]))
                    values = dict(zip(keys, field))
                    if values:
                        if i == 0:
                            continue
                        else:
                            vals_list.append((field[0], field[1]))

            if vals_list:
                args = ','.join(cursor.mogrify("(%s,%s,%s)", (i[0], i[1], i[0][:2])).decode('utf-8')
                                for i in vals_list)
                sql = "INSERT INTO ceisa_pabean_office(code,name,country_code) VALUES %s RETURNING id"
                self.env.cr.execute(sql % args)
                self.env.cr.commit()
            else:
                raise ValidationError('Data not found or something wrong with the datas. Please contact your administrator.')
        # except Exception:
        #     raise ValidationError(_("Please Select Valid File Format !"))
        except OperationalError as e:
            if e.pgcode == '55P03':
                _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
            else:
                raise e
        finally:
            cursor.close()


    @api.model
    def get_oversea_masterdata(self):
        max_rows = self.env['ir.config_parameter'].get_param('ceisa.master.data.import.rows')
        # if int(max_rows) > 1000:
        #     raise ValidationError('Maximum rows has been limit for 1000 records.')
        line = keys = ['code', 'name']
        cursor = self.pool.cursor()
        try:
            directory = os.path.realpath(os.path.join(os.path.dirname(__file__), '../data/files'))
            filename = directory + '/overseas_ports.csv'
            file_reader = []
            vals_list = []
            with open(filename, 'r') as file:
                csvreader = csv.reader(file, delimiter=',')
                file_reader.extend(csvreader)
                for i in range(len(file_reader)):
                    field = list(map(str, file_reader[i]))
                    values = dict(zip(keys, field))
                    if values:
                        if i == 0:
                            continue
                        else:
                            vals_list.append((field[0], field[1]))

            if vals_list:
                args = ','.join(cursor.mogrify("(%s,%s,%s)", (i[0], i[1], i[0][:2])).decode('utf-8')
                                for i in vals_list)

                sql = "INSERT INTO ceisa_pabean_office(code,name,country_code) VALUES %s RETURNING id"
                self.env.cr.execute(sql % args)
                self.env.cr.commit()
            else:
                raise ValidationError('Data not found or something wrong with the datas. Please contact your administrator.')
        # except Exception:
        #     raise ValidationError(_("Please Select Valid File Format !"))
        except OperationalError as e:
            if e.pgcode == '55P03':
                _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
            else:
                raise e
        finally:
            cursor.close()

class CeisaStorehouseLocation(models.Model):
    _name = 'ceisa.storehouse.location'
    _description = 'Storehouse Location'

    name = fields.Char('Name')
    code = fields.Char('Code')
    office_code = fields.Char('Office Code')
    beacukai_office_id = fields.Many2one('ceisa.beacukai.office', string='Beacukai Office ID')

    _sql_constraints = [
        ('storehouse_location_code_uniq', 'UNIQUE(code, office_code)', 'Code of Storehouse Location already exist or should be unique'),
    ]

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaStorehouseLocation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)

        custom_view = self.env['ir.ui.view.custom'].search([('user_id', '=', self.env.uid), ('ref_id', '=', view_id)], limit=1)
        if custom_view:
            res.update({'custom_view_id': custom_view.id,
                        'arch': custom_view.arch})
        res.update({
            'arch': self._arch_preprocessing(res['arch']),
            'toolbar': {'print': [], 'action': [], 'relate': []}
        })
        return res

    @api.model
    def _arch_preprocessing(self, arch):
        def remove_unauthorized_children(node):
            for child in node.iterchildren():
                if child.tag == 'action' and child.get('invisible'):
                    node.remove(child)
                else:
                    remove_unauthorized_children(child)
            return node

        archnode = etree.fromstring(arch)
        # add the js_class 'board' on the fly to force the webclient to
        # instantiate a BoardView instead of FormView
        # ceisa_inventory = self.env["ir.config_parameter"].sudo().get_param("is_ceisa_it_inventory")
        ceisa_inventory = self.env.company.is_ceisa_it_inventory
        if ceisa_inventory:
            archnode.set('js_class', 'button_storehouse_location_masterdata')

        return etree.tostring(remove_unauthorized_children(archnode), pretty_print=True, encoding='unicode')

    @api.depends('office_code')
    def _compute_storehouse_location_id(self):
        for rec in self:
            # rec.beacukai_office_id = self.env['ceisa.beacukai.office'].browse(rec.office_code)
            rec.beacukai_office_id = self.env['ceisa.beacukai.office'].search([('code', '=', rec.office_code)], limit=1)

    @api.model
    def get_storehouse_masterdata(self):
        max_rows = self.env['ir.config_parameter'].get_param('ceisa.master.data.import.rows')
        # if int(max_rows) > 1000:
        #     raise ValidationError('Maximum rows has been limit for 1000 records.')
        line = keys = ['code', 'name']
        cursor = self.pool.cursor()
        try:
            directory = os.path.realpath(os.path.join(os.path.dirname(__file__), '../data/files'))
            filename = directory + '/storehouse_location.csv'
            file_reader = []
            vals_list = []
            with open(filename, 'r') as file:
                csvreader = csv.reader(file, delimiter=',')
                file_reader.extend(csvreader)
                for i in range(len(file_reader)):
                    field = list(map(str, file_reader[i]))
                    values = dict(zip(keys, field))
                    if values:
                        if i == 0:
                            continue
                        else:
                            office_code = field[2]
                            if office_code:
                                office_id = self.env['ceisa.beacukai.office'].search([('code', '=', office_code)], limit=1).id
                                vals_list.append((field[0], field[1], field[2], office_id))
            if vals_list:
                args = ','.join(cursor.mogrify("(%s,%s,%s,%s)", (i[0], i[1], i[2], i[3])).decode('utf-8')
                                for i in vals_list)
                sql = "INSERT INTO ceisa_storehouse_location(code,name,office_code,beacukai_office_id) VALUES %s RETURNING id"
                self.env.cr.execute(sql % args)
                self.env.cr.commit()
            else:
                raise ValidationError('Data not found or something wrong with the datas. Please contact your administrator.')
        # except Exception:
        #     raise ValidationError(_("Please Select Valid File Format !"))
        except OperationalError as e:
            if e.pgcode == '55P03':
                _logger.debug('Another transaction already locked documents rows. Cannot process documents.')
            else:
                raise e
        finally:
            cursor.close()


class CeisaContainer(models.Model):
    _name = 'ceisa.container'
    _description = 'Container Box Size'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaContainer, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaContainerType(models.Model):
    _name = 'ceisa.container.type'
    _description = 'Container Box Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaContainerType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')



class CeisaDocumentType(models.Model):
    _name = 'ceisa.document.type'
    _description = 'Document Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaDocumentType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaExportCategory(models.Model):
    _name = 'ceisa.export.category'
    _description = 'Export Category'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaExportCategory, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaExportCategoryFTZ(models.Model):
    _name = 'ceisa.export.category.ftz'
    _description = 'Export Category FTZ'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaExportCategoryFTZ, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')



class CeisaIncoterm(models.Model):
    _name = 'ceisa.incoterm'
    _description = 'Incoterm'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaIncoterm, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaLocation(models.Model):
    _name = 'ceisa.locations'
    _description = 'Locations'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaLocation, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaPaymentTerm(models.Model):
    _name = 'ceisa.payment.term'
    _description = 'Payment Term'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaPaymentTerm, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProcedureType(models.Model):
    _name = 'ceisa.procedure.type'
    _description = 'Procedure Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaProcedureType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaReasonExport(models.Model):
    _name = 'ceisa.reason.export'
    _description = 'Reason Export'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaReasonExport, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')
    document_code = fields.Char('Document Code')
    document_code_id = fields.Many2one('ceisa.document.type', string='Document ID')


class CeisaTradeTransactionType(models.Model):
    _name = 'ceisa.trade.transaction.type'
    _description = 'Trade Transaction Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaTradeTransactionType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaTradeWay(models.Model):
    _name = 'ceisa.trade.way'
    _description = 'Trade Way'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaTradeWay, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')



class CeisaEntitasType(models.Model):
    _name = 'ceisa.entitas.type'
    _description = 'Entitas Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaEntitasType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')



class CeisaPackageType(models.Model):
    _name = 'ceisa.package.type'
    _description = 'Package Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaPackageType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductSources(models.Model):
    _name = 'ceisa.product.sources'
    _description = 'Package Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaProductSources, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductFTZSources(models.Model):
    _name = 'ceisa.product.ftz.sources'
    _description = 'Package Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaProductFTZSources, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductUnit(models.Model):
    _name = 'ceisa.product.unit'
    _description = 'Product Unit'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaProductUnit, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaGuaranteeType(models.Model):
    _name = 'ceisa.guarantee.type'
    _description = 'Guarantee Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaGuaranteeType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaBusinessStatus(models.Model):
    _name = 'ceisa.business.status'
    _description = 'Business Status'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaBusinessStatus, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaFacilities(models.Model):
    _name = 'ceisa.facilities'
    _description = 'Ceisa Facilities'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaFacilities, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaFacilitiesFee(models.Model):
    _name = 'ceisa.facilities.fee'
    _description = 'Ceisa Facilities Fee'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaFacilitiesFee, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaPermit(models.Model):
    _name = 'ceisa.permit'
    _description = 'Ceisa Permit'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaPermit, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaRespons(models.Model):
    _name = 'ceisa.respons'
    _description = 'Ceisa Respons'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaRespons, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaSpecialSpecification(models.Model):
    _name = 'ceisa.special.specification'
    _description = 'Ceisa Special Specification'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaSpecialSpecification, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaStatus(models.Model):
    _name = 'ceisa.status'
    _description = 'Ceisa Status'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaStatus, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')



class CeisaTaxType(models.Model):
    _name = 'ceisa.tax.type'
    _description = 'Tax Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaTaxType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaTPBType(models.Model):
    _name = 'ceisa.tpb.type'
    _description = 'TPB Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaTPBType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductCondition(models.Model):
    _name = 'ceisa.product.condition'
    _description = 'Product Condition'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaProductCondition, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductCategory(models.Model):
    _name = 'ceisa.product.category'
    _description = 'Product Category'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaProductCategory, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')
    document_type_id = fields.Many2one('ceisa.document.type')



class CeisaExportPurpose(models.Model):
    _name = 'ceisa.export.purpose'
    _description = 'Export Purpose'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaExportPurpose, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')
    document_type_id = fields.Many2one('ceisa.document.type')



class CeisaImportPurpose(models.Model):
    _name = 'ceisa.import.purpose'
    _description = 'Import Purpose'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaImportPurpose, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')
    document_type_id = fields.Many2one('ceisa.document.type')



class CeisaVDType(models.Model):
    _name = 'ceisa.vd.type'
    _description = 'VD Type'

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(CeisaVDType, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        debug_mode = request.session.debug
        if debug_mode == '1' and ((self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_export_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_import_administrator') or self.env.user.has_group(
                'equip3_manuf_it_inventory.group_ceisa_transfer_administrator')) and self.env.user.has_group(
                'base.group_no_one')):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res

    name = fields.Char('Name')
    code = fields.Char('Code')


