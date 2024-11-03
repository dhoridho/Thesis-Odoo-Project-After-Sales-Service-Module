from odoo import _, api, models, fields
from odoo.exceptions import ValidationError


class HrContractIncomeTax(models.Model):
    _inherit = 'hr.contract.income.tax'

    @api.depends('furniture_value_indicator', 'annual_value')
    def _get_furniture_value(self):
        for rec in self:
            fur_value = 0.0
            if rec.furniture_value_indicator == 'P':
                fur_value = rec.annual_value * 0.40
            elif rec.furniture_value_indicator == 'F':
                fur_value = rec.annual_value * 0.50
            rec.furniture_value = fur_value

    @api.depends('total_taxable_value',
                 'taxalble_value_of_utilities_housekeeping',
                 'taxable_value_of_hotel_acco',
                 'cost_of_home_leave_benefits', 'interest_payment',
                 'insurance_payment', 'free_holidays', 'edu_expenses',
                 'non_monetary_awards', 'entrance_fees', 'gains_from_assets',
                 'cost_of_motor', 'car_benefits', 'non_monetary_benefits')
    def get_total_value_of_benefits(self):
        for rec in self:
            total = 0.0
            total = rec.total_taxable_value + \
                rec.taxalble_value_of_utilities_housekeeping + \
                rec.taxable_value_of_hotel_acco + \
                rec.cost_of_home_leave_benefits + rec.interest_payment + \
                rec.insurance_payment + rec.free_holidays + \
                rec.edu_expenses + rec.non_monetary_awards + \
                rec.entrance_fees + rec.gains_from_assets + \
                rec.cost_of_motor + rec.car_benefits + \
                rec.non_monetary_benefits
            rec.total_value_of_benefits = total

    @api.depends('actual_hotel_accommodation', 'employee_paid_amount')
    def _get_hotel_acco(self):
        for rec in self:
            rec.taxable_value_of_hotel_acco = 0.0
            rec.taxable_value_of_hotel_acco = \
                rec.actual_hotel_accommodation - rec.employee_paid_amount

    @api.depends('utilities_misc_value', 'driver_value', 'employer_paid_amount')
    def get_taxable_value_utilities(self):
        for rec in self:
            rec.taxalble_value_of_utilities_housekeeping = 0.0
            rec.taxalble_value_of_utilities_housekeeping = \
                rec.utilities_misc_value + \
                rec.driver_value + rec.employer_paid_amount

    @api.depends('place_of_residence_taxable_value', 'total_rent_paid')
    def _get_total_taxable_value(self):
        for rec in self:
            rec.total_taxable_value = 0.0
            rec.total_taxable_value = (
                rec.place_of_residence_taxable_value - rec.total_rent_paid)

    @api.depends('annual_value', 'furniture_value', 'rent_landloard')
    def _get_residence_taxable_values(self):
        for rec in self:
            rec.place_of_residence_taxable_value = 0.0
            rec.place_of_residence_taxable_value = (
                rec.annual_value + rec.furniture_value) or rec.rent_landloard

    #  ---------------------------
    #    Appendix 8A Fields
    #  ---------------------------
    address = fields.Text("Address:")
    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")
    no_of_days = fields.Integer("No. of days:")
    no_of_emp = fields.Integer(
        "Number of employee(s) sharing the premises (exclude family members \
        who are not employees):")
    annual_value = fields.Float(
        "a) Annual Value (AV) of Premises for the period provided (state \
        apportioned amount, if applicable)")
    furniture_value_indicator = fields.Selection(
        [('P', 'Partially furnished'), ('F', 'Fully furnished')],
        'b).Furniture & Fitting Indicator')
    rent_landloard = fields.Float(
        "C).Rent paid to landlord including rental of Furniture & Fittings")
    total_rent_paid = fields.Float(
        "e).Total Rent paid by employee for Place of Residence")
    utilities_misc_value = fields.Float(
        "g).Utilities/Telephone/Pager/Suitcase/Golf Bag & \
        Accessories/Camera/Electronic Gadgets")
    driver_value = fields.Float(
        "h).Driver [ Annual Wages X (Private / Total Mileage)]")
    employer_paid_amount = fields.Float(
        "i).Servant / Gardener / Upkeep of Compound")
    actual_hotel_accommodation = fields.Float(
        "a).Actual Hotel accommodation/Serviced Apartment within hotel \
        building")
    employee_paid_amount = fields.Float("b).Amount paid by the employee")
    cost_of_home_leave_benefits = fields.Float(
        " Cost of home leave passages and incidental benefits")
    no_of_passanger = fields.Integer("No.of passages for self:")
    spouse = fields.Integer("Spouse")
    children = fields.Integer("Children")
    pioneer_service = fields.Selection([('yes', 'Yes'), ('no', 'No')])
    interest_payment = fields.Float()
    insurance_payment = fields.Float(
        "c.Life insurance premiums paid by the employer:")
    free_holidays = fields.Float(
        "d.Free or subsidised holidays including air passage, etc.:")
    edu_expenses = fields.Float(
        "e.   Educational expenses including tutor provided:")
    non_monetary_awards = fields.Float(
        "f.   Non-monetary awards for long service (for awards exceeding $200 \
        in value) :")
    entrance_fees = fields.Float(
        "g.   Entrance/transfer fees and annual subscription to social or \
        recreational clubs :")
    gains_from_assets = fields.Float(
        "h.   Gains from assets, e.g. vehicles, property, etc. sold to \
        employees at a price lower than open market value :")
    cost_of_motor = fields.Float(
        "i.   Full cost of motor vehicles given to employee :")
    car_benefits = fields.Float("j).Car benefits (See Explanatory Note 16)")
    non_monetary_benefits = fields.Float(
        "k).Other non-monetary benefits which do not fall within the above \
        items")
    furniture_value = fields.Float(
        compute='_get_furniture_value', string='Value of Furniture & Fitting')
    total_value_of_benefits = fields.Float(
        compute='get_total_value_of_benefits',
        string=" TOTAL VALUE OF BENEFITS-IN-KIND (ITEMS 2 TO 4) TO BE \
        REFLECTED IN ITEM d9 OF FORM IR8A")
    taxable_value_of_hotel_acco = fields.Float(
        compute='_get_hotel_acco',
        string="c).Taxable Value of Hotel Accommodation")
    taxalble_value_of_utilities_housekeeping = fields.Float(
        compute='get_taxable_value_utilities',
        string="j).Taxable value of utilities and housekeeping costs")
    total_taxable_value = fields.Float(
        compute='_get_total_taxable_value',
        string="f).Total Taxable Value of Place of Residence")
    place_of_residence_taxable_value = fields.Float(
        compute='_get_residence_taxable_values',
        string="d).Taxable Value of Place of Residence")

    @api.onchange('from_date', 'to_date')
    def onchange_no_of_days(self):
        """Return the number of days"""
        for rec in self:
            if rec.from_date and rec.to_date:
                if rec.from_date > rec.to_date:
                    raise ValidationError(_("Please select valid date!"))
                diff = rec.to_date - rec.from_date
                noofday = str(diff.days)
                rec.no_of_days = int(noofday) + 1
