# Instructions for Adding Gantt view

You can add acs.webcam.mixin in your custom model and add acs_webcam_url in view and it will work without any further changes.

EG:

In PY
------
class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner','acs.webcam.mixin']

    def acs_webcam_retrun_action(self):
        self.ensure_one()
        return self.env.ref('acs_hms_base.action_patient').id
        (Action of your object)

in View
---------
    <field name="acs_webcam_url" widget="webcam_redirect_button"/>

For updating image on any custom field you can set call it using following url
-----
web_base_url + '/acs/webcam/' + model_name + '/' + str(record_id) '/' + str(field_name)

EG: https://www.almightycs.com/acs/webcam/hms.patient/5/new_field 