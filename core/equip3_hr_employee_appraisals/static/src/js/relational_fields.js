odoo.define('equip3_hr_employee_appraisals.relational_fields', function (require) {
    "use strict";
    var AbstractField = require('web.AbstractField');
    var relational_field = require('web.relational_fields');
    var FieldMany2One_extended = AbstractField.include({
        start: function () {
            // booleean indicating that the content of the input isn't synchronized
            // with the current m2o value (for instance, the user is currently
            // typing something in the input, and hasn't selected a value yet).
            this.floating = false;
            this.$external_button = this.$('.o_external_button');
            var self = this
            if (self.model === 'hr.goals' && self.viewType === 'form' && self.formatType === "many2one") {
                this._rpc({
                    model: 'ir.ui.view',
                    method: 'get_view_id',
                    args: ['equip3_hr_employee_appraisals.hr_goals_form_view']
                }).then(function (rec) {
                    var mno = $('.o_external_button')
                        $.each(mno, function (key, val) {
                            $(val).hide()
                        })
                });
            }
            
            return this._super.apply(this, arguments);
        },
    });
    return FieldMany2One_extended;
});