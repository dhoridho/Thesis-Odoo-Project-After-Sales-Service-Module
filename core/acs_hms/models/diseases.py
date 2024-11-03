# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo.osv import expression


class ACSDiseases(models.Model):
    _name = 'hms.diseases'
    _description = "Diseases"

    category = fields.Many2one('diseases.category', string='Category', ondelete='cascade',
        help='Select the category for this disease This is usually'\
        'associated to the standard. For instance, the chapter on the ICD-10'\
        'will be the main category for the disease')
    info = fields.Text(string='Extra Info')
    code = fields.Char(string='Code', help='Specific Code for the Disease (eg, Code for ICD-10)', index=True)
    name = fields.Char(string='Name', required=True, translate=True,  help='Disease name', index=True)
    protein = fields.Char(string='Protein involved', help='Name of the protein(s) affected')
    gene = fields.Char(string='Gene')
    chromosome = fields.Char(string='Affected Chromosome', help='chromosome number')
    classification = fields.Selection([
        ('icd9','ICD-9'),
        ('icd10', 'ICD-10'), 
        ('vaccine', 'ICD-11')], string="Classification")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class ACSDiseasesCategory(models.Model):
    _name = 'diseases.category'
    _description = "Diseases Category"

    name = fields.Char(string='Category Name', required=True, index=True)
    parent_id = fields.Many2one('diseases.category', ondelete='cascade', string='Parent Category')

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for rec in self:
            if not rec._check_recursion():
                raise ValidationError(_('You cannot create a recursive hierarchy.'))


class ACSPatientDisease(models.Model):
    _name = 'hms.patient.disease'
    _description = "Patient Diseases"

    disease = fields.Many2one('hms.diseases', ondelete='set null', string='Disease')
    description = fields.Char(string='Treatment Description')
    diagnosed_date = fields.Date(string='Date of Diagnosis')
    healed_date = fields.Date(string='Healed')
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician',
        help='Physician who treated or diagnosed the patient')    
    is_allergy = fields.Boolean(string='Allergic Disease')
    pregnancy_warning = fields.Boolean(string='Pregnancy warning')
    patient_id = fields.Many2one('hms.patient', ondelete='cascade', string='Patient')
    lactation = fields.Boolean('Lactation')
    disease_severity = fields.Selection([
            ('mild', 'Mild'),
            ('moderate', 'Moderate'),
            ('severe', 'Severe'),
        ], string='Severity',index=True)
    status = fields.Selection([
            ('acute', 'Acute'),
            ('chronic', 'Chronic'),
            ('unchanged', 'Unchanged'),
            ('healed', 'Healed'),
            ('improving', 'Improving'),
            ('worsening', 'Worsening'),
        ], string='Status of the disease',index=True)
    is_infectious = fields.Boolean(string='Infectious Disease',
        help='Check if the patient has an infectious' \
        'transmissible disease')
    allergy_type = fields.Selection([
            ('da', 'Drug Allergy'),
            ('fa', 'Food Allergy'),
            ('ma', 'Misc Allergy'),
            ('mc', 'Misc Contraindication'),
        ], string='Allergy type',index=True)
    age = fields.Char(string='Age when diagnosed',
        help='Patient age at the moment of the diagnosis. Can be estimative')
    treatment_id = fields.Many2one('hms.treatment', ondelete='cascade', 
        string='Treatment', help="Treatment Id")


class ACSDiseaseGene(models.Model):
    _name = 'disease.gene'
    _description = 'Disease Genetic'

    name = fields.Char(string='Official Name', required=True)
    gene_id = fields.Char(string='Gene ID', help="default code from NCBI Entrez database.")
    long_name = fields.Char(string='Official Long Name', required=True)
    location = fields.Char(string='Location', required=True, help="Locus of the chromosome")
    chromosome = fields.Char(string='Affected Chromosome', required=True)
    info = fields.Text(string='Information')
    dominance = fields.Selection([
            ('d', 'dominant'),
            ('r', 'recessive')
        ], 'Dominance', index=True)


class PatientGeneticRisk(models.Model):
    _name = 'hms.patient.genetic.risk'
    _description = 'Patient Genetic Risks'

    patient_id = fields.Many2one('hms.patient', ondelete='cascade', 
        string='Patient', index=True)
    disease_gene = fields.Many2one('disease.gene', ondelete='restrict',
        string='Disease Gene', required=True)


class FamilyDiseases(models.Model):
    _name = 'hms.patient.family.diseases'
    _description = 'Family Diseases'

    patient_id = fields.Many2one('hms.patient', ondelete='cascade', string='Patient', index=True)
    diseases_ids = fields.Many2many('hms.diseases', 'rz_id','pz_id','cz_id' ,'Disease', required=True)
    xory = fields.Selection([
            ('m', 'Maternal'),
            ('f', 'Paternal')
        ], 'Maternal or Paternal')
    relative = fields.Selection([
            ('mother', 'Mother'),
            ('father', 'Father'),
            ('brother', 'Brother'),
            ('sister', 'Sister'),
            ('aunt', 'Aunt'),
            ('uncle', 'Uncle'),
            ('nephew', 'Nephew'),
            ('niece', 'Niece'),
            ('grandfather', 'Grandfather'),
            ('grandmother', 'Grandmother'),
            ('cousin', 'Cousin')
        ], 'Relative',
        help="First degree = siblings, mother and father; second degree = "
        "Uncles, nephews and Nieces; third degree = Grandparents and cousins",required=True)