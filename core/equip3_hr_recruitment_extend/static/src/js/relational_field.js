odoo.define('equip3_hr_recruitment_extend.relational_fields', function (require) {
"use strict";
    var AbstractField = require('web.AbstractField');
    var relational_field = require('web.relational_fields');
    var FieldMany2One_extended = AbstractField.include({
        start: function () {
            // booleean indicating that the content of the input isn't synchronized
            // with the current m2o value (for instance, the user is currently
            // typing something in the input, and hasn't selected a value yet).as
            this.floating = false;
            //the below line was commented due to Monetary widget issue
//            this.$input = this.$('input');
            this.$external_button = this.$('.o_external_button');
            var self = this
            if (self.model == 'hr.job' || self.model == "job.stage.line" || self.model == "hr.applicant"){
                if (self.viewType === 'form' && self.formatType === "many2one") {
                    this._rpc({
                        model: 'ir.ui.view',
                        method: 'get_view_id',
                        args: ['hr.view_hr_job_form'],
                    }).then(function (rec) {
                        var mno = $('.o_external_button')
                        if (self.model == 'hr.job' || self.model == "job.stage.line" || self.model == "hr.applicant"){
                            $.each(mno, function(key,val){
                                $(val)[0].attributes[5].nodeValue = 'Edit'
                            })
                        }
                    });
                }
                else if (self.model === "job.stage.line" && self.formatType === "many2one") {
                    this._rpc({
                        model: 'ir.ui.view',
                        method: 'get_view_id',
                        args: ['hr.view_hr_job_form'],
                    }).then(function (rec) {
                        var mno = $('.o_external_button')
                        if (self.model == 'hr.job' || self.model == "job.stage.line" || self.model == "hr.applicant"){
                            $.each(mno, function(key,val){
                                $(val)[0].attributes[5].nodeValue = 'Edit'
                            })
                        }
                    });
                }
            }
            return this._super.apply(this, arguments);
        },
    });
    return FieldMany2One_extended;
});