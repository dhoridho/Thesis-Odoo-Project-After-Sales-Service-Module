    # -*- coding: utf-8 -*-
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models ,_
from odoo.exceptions import UserError


class PatientMenstrualHistory(models.Model):
    _name = 'hms.patient.menstrual_history'
    _description =  'Menstrual History'
    _rec_name = 'patient_id'
    
    patient_id = fields.Many2one('hms.patient',string ='Patient', ondelete='cascade')
    lmp = fields.Date(string='LMP', help="Last Menstrual Period", required=True)
    lmp_length = fields.Integer(string='Length', required=True)
    frequency = fields.Selection([('amenorrhea', 'Amenorrhea'),
                ('oligomenorrhea', 'Oligomenorrhea'),
                ('eumenorrhea', 'Eumenorrhea'),
                ('polymenorrhea', 'Polymenorrhea'),
                ], string='Frequency')
    volume = fields.Selection([('amenorrhea', 'Amenorrhea'),
                ('hypomenorrhea', 'Hypomenorrhea'),
                ('normal', 'Normal'),
                ('menorrhagia', 'Menorrhagia'),
                ], string='Volume')
    is_regular = fields.Boolean(string ='Regular')
    dysmenorrhea = fields.Boolean(string ='Dysmenorrhea', help="Painful menstruation, typically involving abdominal cramps.")
    
    
class PatientPregnancy(models.Model):
    _name = 'hms.patient.pregnancy'
    _description = 'Patient Pregnancy'
    _rec_name = 'patient_id'
    
    def _get_pregnancy_data(self):
        for rec in self:
            rec.pdd = (rec.lmp or fields.Datetime.now()) + timedelta(days=280)
            # if rec.pregnancy_end_date:
            #     gestational_age = datetime.date(
            #         rec.pregnancy_end_date) - rec.lmp
            #     rec.pregnancy_end_age = (gestational_age.days) / 7
            # else:
            #     rec.pregnancy_end_age = 2

    @api.depends('patient_id', 'patient_id.birthday', 'lmp')
    def get_patient_age(self):
        for rec in self:
            age = ''
            if rec.patient_id.birthday:
                end_data = rec.lmp or fields.Datetime.now()
                delta = relativedelta(end_data, rec.patient_id.birthday)
                age = str(delta.years) + _(" Year") + str(delta.months) + _(" Month ")
            rec.age = age

    patient_id = fields.Many2one('hms.patient', string='Patient' ,required=True, ondelete='restrict')
    physician_id = fields.Many2one('hms.physician', string='Physician')
    gravida = fields.Integer(string='Pregnancy #')
    lmp = fields.Date(string='Last Menstrual Period', help="Last Menstrual Period", required=True)
    fetus = fields.Integer(string='#Fetus', required=True)
    warning = fields.Boolean(string='Warn', help='Check this box if this is pregancy is or was NOT normal')
    pdd = fields.Date(compute=_get_pregnancy_data, string='Pregnancy Due Date', help='Expected Due date')
    prenatal_evaluation_ids = fields.One2many('hms.patient.prenatal.evaluation', 'patient_preg_id', string='Prenatal Evaluations')
    perinatal_ids = fields.One2many('hms.perinatal', 'patient_preg_id', string='Perinatal Info')
    puerperium_monitor_ids = fields.One2many('hms.puerperium.monitor', 'patient_preg_id', string='Puerperium monitor')
    monozygotic = fields.Boolean('Monozygotic', help="Twins derived from a single ovum, and so identical.")
    pregnancy_end_result = fields.Selection([
        ('live_birth', 'Live birth'),
        ('abortion', 'Abortion'),
        ('stillbirth', 'Stillbirth'),
        ('status_unknown', 'Status unknown')], string='Result', help="Result of the pregnancy.")
    pregnancy_end_date = fields.Datetime(string='End of Pregnancy', help='Actual date when pregnancy ends.')
    iugr = fields.Selection([
        ('symmetric', 'Symmetric'),
        ('assymetric', 'Assymetric'),
    ], string='IUGR', help="Intrauterine growth restriction (IUGR) refers to poor growth of a fetus while in the mother's womb during pregnancy.")
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id)
    age = fields.Char(compute="get_patient_age", string='Age', store=True,
        help="Computed patient age at the moment of the evaluation")


class AcsPerinatal(models.Model):
    _name = 'hms.perinatal'
    _description =  'Time information immediately before and after birth'
    _rec_name = 'patient_preg_id'

    patient_preg_id = fields.Many2one('hms.patient.pregnancy', string='Perinatal Infomation', ondelete='cascade')
    admission_code = fields.Char(string='Admission Code', size=64)
    gravida_number = fields.Integer(string='Gravida #')
    abortion = fields.Boolean(string='Abortion')
    admission_date = fields.Datetime(string='Admission date', help="Date when she was admitted to give birth")
    prenatal_evaluations = fields.Integer(string='Prenatal evaluations', help="Number of visits to the doctor during pregnancy")
    start_labor_mode = fields.Selection([
        ('normal', 'Normal'),
        ('induced', 'Induced'),
        ('c-sec', 'c-section')], string='Labor mode')
    gestational_weeks = fields.Integer(string='Gestational weeks')
    gestational_days = fields.Integer(string='Gestational days')
    fetus_presentation = fields.Selection([
        ('correct', 'Correct'),
        ('occiput', 'Occiput / Cephalic Posterior'),
        ('fb', 'Frank Breech'),
        ('cb', 'Complete Breech'),
        ('trans', 'Transverse Lie'),
        ('foot', 'Footling Breech')], string='Fetus Presentation')
    dystocia = fields.Boolean(string='Dystocia', help="Types of Birth Breeches. Difficult birth")
    laceration = fields.Selection([
        ('perineal', 'Perineal'),
        ('vaginal', 'Vaginal'),
        ('cervical', 'Cervical'),
        ('broad_ligament', 'Broad Ligament'),
        ('vulvar', 'Vulvar'),
        ('rectal', 'Rectal'),
        ('bladder', 'Bladder'),
        ('urethral', 'Urethral')],string='Lacerations', help="Deep cut or tear in flesh")
    hematoma = fields.Selection([
        ('vaginal', 'Vaginal'),
        ('vulvar', 'Vulvar'),
        ('retroperitoneal', 'Retroperitoneal')], string='Hematoma',  help="Collection of blood outside of blood vessels.")
    placenta_incomplete = fields.Boolean(string='Incomplete Placenta')
    placenta_retained = fields.Boolean(string='Retained Placenta', help="The placenta remains in the womb a period after birth")
    abruptio_placentae = fields.Boolean(string='Abruptio Placentae', help='Premature separation of the placenta from the uterus')
    episiotomy = fields.Boolean(string='Episiotomy', help="A surgical cut made at the opening of the vagina during childbirth, to aid a difficult delivery and prevent rupture of tissues.")
    vaginal_tearing = fields.Boolean(string='Vaginal tearing',help='Tear occurs in your perineum – the area between your vagina and your anus.')
    forceps = fields.Boolean(string='Use of forceps')
    monitoring_ids = fields.One2many('hms.perinatal.monitor', 'perinatal_id', string='Monitors')
    discharge = fields.Datetime(string='Discharged from hospital')
    place_of_death = fields.Selection([
        ('hospital', 'Hospital'),
        ('delivery_room', 'At the delivery room'),
        ('transit', 'in transit to the hospital'),
        ('transfer', 'Being transferred to other hospital'),
    ],string='Place of Death')
    mother_deceased = fields.Boolean(string='Deceased', help="Mother died in the process")
    notes = fields.Text(string='Notes')


class PrenatalEvaluation(models.Model):
    _name = 'hms.patient.prenatal.evaluation'
    _description =  'Prenatal and Antenatal Evaluations'
    _rec_name = 'patient_id'

    patient_id = fields.Many2one('hms.patient', string='Patient')
    patient_preg_id = fields.Many2one('hms.patient.pregnancy', ondelete='cascade', string='Patient Pregnancy')
    gestational_weeks = fields.Float(string="Gestational Weeks")
    gestational_days = fields.Integer(string='Gestational days')
    hypertension = fields.Boolean(string='Hypertension', help='Check this box if the mother has hypertension')
    preeclampsia = fields.Boolean(string='Preeclampsia', help='Check this box if the mother has pre-eclampsia')
    overweight = fields.Boolean(string='Overweight', help='Check this box if the mother is overweight or obesity')
    diabetes = fields.Boolean(string='Diabetes', help='Check this box if the mother has glucose intolerance or diabetes')
    mother_weight = fields.Float("Weight")
    mother_bp = fields.Char("BP")
    systolic_bp = fields.Char("Systolic BP", size=3)
    diastolic_bp = fields.Char("Diastolic BP", size=3)
    invasive_placentation = fields.Selection([
        ('normal', 'Normal decidua'),
        ('accreta', 'Accreta'),
        ('increta', 'Increta'),
        ('percreta', 'Percreta'),
        ], string='Placentation', help="Formation, type and structure, or arrangement of the placenta.")
    placenta_previa = fields.Boolean(string='Placenta Previa', help="A condition in which the placenta partially or wholly blocks the neck of the uterus, so interfering with normal delivery of a baby")
    vasa_previa = fields.Boolean(string='Vasa Previa', help="condition in which fetal blood vessels cross or run near the internal opening of the uterus")
    fundal_height = fields.Integer(string='Fundal Height', help="Distance between the symphysis pubis and the uterine fundus (S-FD) in cm")
    fetus_heart_rate = fields.Integer(string='Fetus heart rate', help='Fetus heart rate')
    efw = fields.Integer(string='EFW', help="Estimated Fetal Weight")
    fetal_bpd = fields.Integer(string='BPD', help="Fetal Biparietal Diameter")
    fetal_ac = fields.Integer(string='AC', help="Fetal Abdominal Circumference")
    fetal_hc = fields.Integer(string='HC', help="Fetal Head Circumference")
    fetal_fl = fields.Integer(string='FL', help="Fetal Femur Length")
    oligohydramnios = fields.Boolean(string='Oligohydramnios', help="Condition in pregnancy characterized by a deficiency of amniotic fluid.")
    polihydramnios = fields.Boolean(string='Polihydramnios', help="A medical condition describing an excess of amniotic fluid in the amniotic sac")
    iugr = fields.Boolean(string='IUGR', help="Intra Uterine Growth Restriction")


class PuerperiumMonitor(models.Model):
    _name = 'hms.puerperium.monitor'
    _description = 'Puerperium Monitor'

    name = fields.Char(required=True)
    patient_preg_id = fields.Many2one('hms.patient.pregnancy', string='Pregnancy', ondelete='cascade')
    date = fields.Datetime(string='Date', required=True, help='Date when the Puerperium is done.')
    systolic = fields.Integer(string='Systolic Pressure', help="Measure of Blood Pressure")
    diastolic = fields.Integer(string='Diastolic Pressure', help="Measure of Blood Pressure")
    frequency = fields.Integer(string='Heart Frequency')
    lochia_amount = fields.Selection([
        ('normal', 'Normal'),
        ('abundant', 'Abundant'),
        ('hemorrhage', 'Hemorrhage'),
        ],string='Lochia amount', help="Amount of the vaginal discharge you have after a vaginal delivery")
    lochia_color = fields.Selection([
        ('rubra', 'Rubra'),
        ('serosa', 'Serosa'),
        ('alba', 'Alba'),
        ], string='Lochia color', help='Color of the vaginal discharge you have after a vaginal delivery')
    lochia_odor = fields.Selection([
        ('normal', 'Normal'),
        ('offensive', 'Offensive'),
        ], string='Lochia odor', help='Smell of The vaginal discharge you have after a vaginal delivery')
    uterus_involution = fields.Integer(string='Fundal Height', help="Distance between the symphysis pubis and the uterine fundus (S-FD) in cm")
    temperature = fields.Float(string='Temperature')


class PerinatalMonitor(models.Model):
    _name = 'hms.perinatal.monitor'
    _description = 'Perinatal monitor'
    
    perinatal_id = fields.Many2one('hms.perinatal', string='patient', ondelete='cascade')
    date = fields.Datetime(string='Date and Time')
    systolic = fields.Integer(string='Systolic Pressure')
    diastolic = fields.Integer(string='Diastolic Pressure')
    contractions = fields.Integer(string='Contractions')
    frequency = fields.Integer(string='Mother\'s Heart Frequency')
    dilation = fields.Integer(string='Cervix dilation')
    f_frequency = fields.Integer(string='Fetus Heart Frequency')
    meconium = fields.Boolean(string='Meconium')
    bleeding = fields.Boolean(string='Bleeding')
    fundal_height = fields.Integer(string='Fundal Height')
    fetus_position = fields.Selection([
        ('correct', 'Correct'),
        ('output', 'Occiput / Cephalic Posterior'),
        ('frank_breech', 'Frank Breech'),
        ('complete_breech', 'Complete Breech'),
        ('transverse_lie', 'Transverse Lie'),
        ('foot_breech', 'Footling Breech')], string='Fetus Position, Types of Birth Breeches')


class PatientMammographyHistory(models.Model):
    _name = 'hms.patient.mammography_history'
    _description =  'Mammography History'
    _order = "id desc"

    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, ondelete='cascade')
    date = fields.Date(string='Date', help="Date", required=True)
    result = fields.Selection([
        ('normal', 'normal'),
        ('abnormal', 'abnormal')], string='Result', help="Please check the lab test results if the module is installed")
    comments = fields.Char(string='Remarks')


class PatientPAPHistory(models.Model):
    _name = 'hms.patient.pap_history'
    _description =  'PAP Test History'
    _order = "id desc"

    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, ondelete='cascade')
    date = fields.Date(string='Date', help="Date", required=True)
    result = fields.Selection([
            ('negative', 'Negative'),
            ('c1', 'ASC-US'),
            ('c2', 'ASC-H'),
            ('g1', 'ASG'),
            ('c3', 'LSIL'),
            ('c4', 'HSIL'),
            ('g4', 'AIS'),
            ], string='Result', help="Please check the lab results if the module is installed")
    comments = fields.Char(string='Remarks')


class PatientColposcopyHistory(models.Model):
    _name = 'hms.patient.colposcopy_history'
    _description =  'Colposcopy History'
    _order = "id desc"

    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, ondelete='cascade')
    date = fields.Date(string='Date', help="Date", required=True)
    result = fields.Selection([
                    ('normal', 'normal'),
                    ('abnormal', 'abnormal'),
                    ], string='Result', help="Please check the lab test results if the module is installed")
    comments = fields.Char(string='Remarks')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   