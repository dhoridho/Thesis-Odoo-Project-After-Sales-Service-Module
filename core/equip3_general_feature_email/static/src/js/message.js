odoo.define('equip3_general_feature_email.message', function (require){
    "use strict";

    const {
        registerClassPatchModel,
        registerFieldPatchModel,
    } = require('mail/static/src/model/model_core.js');
    const { attr, many2many, many2one, one2many } = require('mail/static/src/model/model_field.js');
    const threadJS = require('mail/static/src/models/message/message.js');


    registerClassPatchModel('mail.message', 'equip3_general_feature_email/static/src/js/message.js', {

        /**
         * Compute an url string that can be used inside a href attribute
         *
         * @override
         */
        convertData(data) {
            const data2 = this._super(data);
            // if('action_id_position' in data){
                data2.action_id_position = data.action_id_position
            // }
            return data2;
        },

    });

    registerFieldPatchModel('mail.message', 'equip3_general_feature_email/static/src/js/message.js', {
        action_id_position: attr({
            default: false,
        }),
    });


});
