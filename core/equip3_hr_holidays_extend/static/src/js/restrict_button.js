odoo.define('equip3_hr_holidays_extend.BasicView', function (require) {
"use strict";
var BasicView = require('web.BasicView');
var session = require('web.session');
BasicView.include({
//Restrict Archive button only for Self service group on Leave Balance
        init: function(viewInfo, params) {
            var self = this;
            this._super.apply(this, arguments);
            const model =  ['hr.leave.balance'] ;
            if(model.includes(self.controllerParams.modelName))
            {
                session.user_has_group('equip3_hr_employee_access_right_setting.group_responsible').then(function (has_group) {
                    if (!has_group) {
                        self.controllerParams.archiveEnabled = 'False' in viewInfo.fields;
                    }
                });
            }
        },
    });
});



