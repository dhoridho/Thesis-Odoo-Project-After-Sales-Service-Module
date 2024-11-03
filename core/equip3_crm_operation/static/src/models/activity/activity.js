odoo.define('equip3_crm_operation/static/src/models/activity/activity.js', function (require) {
'use strict';

const {
    registerClassPatchModel,
    registerInstancePatchModel,
} = require('mail/static/src/model/model_core.js');

registerClassPatchModel('mail.activity', 'equip3_crm_operation/static/src/models/activity/activity.js', {
    convertData(data) {
        const data2 = this._super(data);
        if ('attachment_ids' in data) {
            if (!data.attachment_ids) {
                data2.attachments = [['unlink-all']];
            } else {
                data2.attachments = [
                    ['insert-and-replace', data.attachment_ids.map(attachmentData =>
                        this.env.models['mail.attachment'].convertData(attachmentData)
                    )],
                ];
            }
        }
        return data2;
    },
});
});
