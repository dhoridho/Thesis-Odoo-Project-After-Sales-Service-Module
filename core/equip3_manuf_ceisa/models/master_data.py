# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CeisaBeacukaiOffice(models.Model):
    _name = 'ceisa.beacukai.office'
    _description = 'Beacukai Office'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaPabeanOffice(models.Model):
    _name = 'ceisa.pabean.office'
    _description = 'Pabean Office'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaContainer(models.Model):
    _name = 'ceisa.container'
    _description = 'Container Box Size'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaContainerType(models.Model):
    _name = 'ceisa.container.type'
    _description = 'Container Box Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaContainerCategory(models.Model):
    _name = 'ceisa.container.category'
    _description = 'Container Box Category'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaDocumentType(models.Model):
    _name = 'ceisa.document.type'
    _description = 'Document Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaExportCategory(models.Model):
    _name = 'ceisa.export.category'
    _description = 'Export Category'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaExportType(models.Model):
    _name = 'ceisa.export.type'
    _description = 'Export Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaImportType(models.Model):
    _name = 'ceisa.import.type'
    _description = 'Import Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaIncoterm(models.Model):
    _name = 'ceisa.incoterm'
    _description = 'Incoterm'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaInsuranceType(models.Model):
    _name = 'ceisa.insurance.type'
    _description = 'Insurance Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaLocation(models.Model):
    _name = 'ceisa.locations'
    _description = 'Locations'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaPaymentTerm(models.Model):
    _name = 'ceisa.payment.term'
    _description = 'Payment Term'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProcedureType(models.Model):
    _name = 'ceisa.procedure.type'
    _description = 'Procedure Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaReasonExport(models.Model):
    _name = 'ceisa.reason.export'
    _description = 'Reason Export'

    name = fields.Char('Name')
    code = fields.Char('Code')
    document_code = fields.Char('Document Code')


class CeisaTradeTransactionType(models.Model):
    _name = 'ceisa.trade.transaction.type'
    _description = 'Trade Transaction Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaTradeWay(models.Model):
    _name = 'ceisa.trade.way'
    _description = 'Trade Way'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaIdentityType(models.Model):
    _name = 'ceisa.identity.type'
    _description = 'Identity Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaEntitasType(models.Model):
    _name = 'ceisa.entitas.type'
    _description = 'Entitas Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaTransportationType(models.Model):
    _name = 'ceisa.transportation.type'
    _description = 'Transportation Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaPackageType(models.Model):
    _name = 'ceisa.package.type'
    _description = 'Package Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductSources(models.Model):
    _name = 'ceisa.product.sources'
    _description = 'Package Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductFTZSources(models.Model):
    _name = 'ceisa.product.ftz.sources'
    _description = 'Package Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaProductUnit(models.Model):
    _name = 'ceisa.product.unit'
    _description = 'Product Unit'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaGuaranteeType(models.Model):
    _name = 'ceisa.guarantee.type'
    _description = 'Guarantee Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaAPIType(models.Model):
    _name = 'ceisa.api.type'
    _description = 'API Type'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaBusinessStatus(models.Model):
    _name = 'ceisa.business.status'
    _description = 'Business Status'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaFacilities(models.Model):
    _name = 'ceisa.facilities'
    _description = 'Ceisa Facilities'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaPermit(models.Model):
    _name = 'ceisa.permit'
    _description = 'Ceisa Permit'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaRespons(models.Model):
    _name = 'ceisa.respons'
    _description = 'Ceisa Respons'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaSpecialSpecification(models.Model):
    _name = 'ceisa.special.specification'
    _description = 'Ceisa Special Specification'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaStatus(models.Model):
    _name = 'ceisa.status'
    _description = 'Ceisa Status'

    name = fields.Char('Name')
    code = fields.Char('Code')


class CeisaTutupPU(models.Model):
    _name = 'ceisa.tutup.pu'
    _description = 'Ceisa Tutup PU'

    name = fields.Char('Name')
    code = fields.Char('Code')


