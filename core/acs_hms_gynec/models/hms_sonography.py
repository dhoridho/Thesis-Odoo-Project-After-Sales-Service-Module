# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class SystemicExamination(models.Model):
    _name = "systemic.examination"
    _description = "Systemic Examination"
    _rec_name = 'patient_id'

    patient_id = fields.Many2one("hms.patient",string="Patient",required=True)
    date = fields.Datetime(string='Date',default=fields.Datetime.now,required=True)
    bp = fields.Char(string='Blood Pressure')
    weight = fields.Float(string='Weight')
    pa = fields.Char(string='P/A', help="Per Abdominal Examination")
    pv = fields.Char(string='P/V', help="Per Vaginal Examination")
    pr = fields.Char(string='P/R', help="Per Rectal Examination")
    remarks = fields.Text(string='Remarks')
    exa_type = fields.Selection([
        ('abdominal', 'Abdominal'), 
        ('vaginal', 'Vaginal'), 
        ('rectal', 'Rectal')], string='Examination Type', default='abdominal')
    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", string='Appointment', required=True)
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',default=lambda self: self.env.user.company_id.id)


class AppointmentSonographyPelvis(models.Model):
    _name = 'hms.appointment.sonography.pelvis'
    _description = "Sound waves to make pictures of the organs inside your pelvis"
    _rec_name = 'patient_id'

    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", string='Appointment', required=True)
    patient_id = fields.Many2one("hms.patient", string="Name", required=True)
    date = fields.Date(string='Date',default=fields.Date.context_today, required=True)
    lmp = fields.Date('LMP', help="Last Menstrual Period", required=True)
    uterus = fields.Char('Uterus')
    uterus_size = fields.Char('Uterus size')
    endometrial_thickness = fields.Char('Endometrial Thickness', help="Commonly measured parameterin ultrasound. The thickness of the endometrium, will depend on whether the patient is of reproductive age or postmenopausal and, if of reproductive age, at what point in the menstrual cycle they are examined. ")
    left_ovary_size = fields.Char('Left Ovary size')
    right_ovary_size = fields.Char('Right Ovary size')
    conclusion = fields.Text('Conclusion')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',related='appointment_id.company_id')
    endometrial_echo_seen_centrally = fields.Boolean(string="Endometrial echo is seen Centrally", default=True)
    evidence_of_intrauterine = fields.Boolean(string="There is no evidence of intrauterine or extrauterine mass or gestation.", default=True)
    free_fluid_in_pod = fields.Boolean(string="There is no free fluid in POD (Pouch of Douglas)", default=True)
    cerix_normal = fields.Boolean(string="Cerix appears to be normal", default=True)

    def print_sono_elvis_report(self):
        self.ensure_one()
        return self.env.ref('acs_hms_gynec.action_report_sono_pelvis').report_action(self)


class AppointmentSonographyFollicalLine(models.Model):
    _name = 'sonography.follical.line'
    _description = 'Follical Line'

    follical_id = fields.Many2one('hms.appointment.sonography.follical', ondelete="cascade", string='Report')
    date = fields.Date(string='Date',default=fields.Date.context_today)
    cycle_day = fields.Char(string='Day/Cycle')
    left_ovary_size = fields.Char(string='Lt ovary', help="Left Ovary Size")
    right_ovary_size = fields.Char(string='Rt ovary', help="Right Ovary Size")
    endometriulm = fields.Char(string='Endometriulm')
    curvical_mucus = fields.Char(string='Curvical mucus')


class AppointmentSonographyFollical(models.Model):
    _name = 'hms.appointment.sonography.follical'
    _description  = 'Looking at the ovaries and uterus internally using a sterile (clean) transducer paying particular attention to the follicles within the ovaries.'
    _rec_name = 'patient_id'

    date = fields.Date(string='Date',default=fields.Date.context_today, required=True)
    lmp = fields.Date('LMP', help="LMP")
    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", string='Appointment', required=True)
    patient_id = fields.Many2one('hms.patient', string="Name", required=True)
    line_ids = fields.One2many('sonography.follical.line', 'follical_id', 'Sonography Obstetric Reports')
    conclusion = fields.Text('Conclusion')
    advice = fields.Text('Advice')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',related='appointment_id.company_id')

    def print_sono_follical_report(self):
        self.ensure_one()
        return self.env.ref('acs_hms_gynec.action_report_sono_follical').report_action(self)


class AppointmentSonographyObstetric(models.Model):
    _name = 'hms.appointment.sonography.obstetric'
    _description = 'Sound waves to produce pictures of a baby.'
    _rec_name = 'patient_id'

    date = fields.Date(string='Date',default=fields.Date.context_today, required=True)
    appointment_id = fields.Many2one('hms.appointment', ondelete="restrict", string='Appointment', required=True)
    patient_id = fields.Many2one("hms.patient",required=True)
    age = fields.Char(related='patient_id.age',string='Age')
    lmp = fields.Date(string='LMP', help="Last Menstrual Period", required=True)
    fetal_movement = fields.Char(string='Fetal Movement')
    cardiac_activity = fields.Boolean(string='Cardiac Activity')
    fhr = fields.Char(string='FHR', help="Fetal Heart Rate")
    fetues = fields.Selection([
        ('single', 'Single'),
        ('twins', 'Twins'),
    ], string='No. Of Fetues')
    presentation = fields.Selection([
        ('vertex', 'Vertex'),
        ('breech', 'Breech'),
        ('variable', 'Variable'),
        ('oblique', 'Oblique'),
        ('transverse', 'Transverse'),
        ], string='Presentation')
    placenta = fields.Selection([
        ('fundal', 'Fundal'),
        ('anterior', 'Anterior'),
        ('posterior', 'Posterior'),
        ('previa', 'Previa'),
        ('lawline', 'Lawline'),
        ], string='Placenta', help="Different position of Placenta")
    amniotic_fluid = fields.Selection([
        ('adequate', 'Adequate'),
        ('less', 'Less'),
        ], string='Amniotic Fluid')
    fluid_less = fields.Char(string='Fluid Value', help="Amniotic Fluid Level")
    #Fetal Parameters
    bpd = fields.Char(string='BPD', help="Biparietal diameter (BPD) is one of the basic biometric parameters used to assess fetal size. BPD together with head circumference (HC), abdominal circumference (AC), and femur length (FL) are computed to produce an estimate of fetal weight.")
    bpd_days = fields.Char(string='BPD Days')
    bpd_weeks = fields.Char(string='BPD Weeks')
    fl = fields.Char(string='FL', help="Femur Legth, length of the baby's femur, the long bone in the human thigh")
    fl_days = fields.Char(string='FL Days')
    fl_weeks = fields.Char(string='FL Weeks')
    hc = fields.Char(string='HC', help="Head circumference (HC) is one of the basic biometric parameters used to assess fetal size.")
    hc_days = fields.Char(string='HC Days')
    hc_weeks = fields.Char(string='HC Weeks')
    ac = fields.Char(string='AC', help="Abdominal circumference")
    ac_days = fields.Char(string='AC Days')
    ac_weeks = fields.Char(string='AC Weeks')
    crl = fields.Char(string='CRL', help="Crown-Rump Length, distance between the top of the embryo and its rump.")
    crl_days = fields.Char(string='CRL Days')
    crl_weeks = fields.Char(string='CRL Weeks')
    fetal_age = fields.Char(string='Average Estimated Fetal Age')
    edd = fields.Date(string='EDD', help='Estimated Delivery DAte')
    fetal_weight = fields.Char(string='Estimated Fetal Weight')
    cerrvix_lenght = fields.Char(string='Cervix Length')
    cerrvix_width = fields.Char(string='Cervix Width')
    internalos = fields.Char(string='Internal OS', help="The opening of this canal into the uterus.")
    sono_fetal_anomaly = fields.Char(string='Any Sonographically detectable fetal anomaly')
    impression = fields.Text(string='Impression')
    company_id = fields.Many2one('res.company', ondelete='restrict', 
        string='Hospital',related='appointment_id.company_id')

    def print_sono_obstetric_report(self):
        self.ensure_one()
        return self.env.ref('acs_hms_gynec.action_report_sono_obstetric').report_action(self)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: