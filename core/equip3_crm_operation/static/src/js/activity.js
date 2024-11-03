odoo.define('equip3_crm_operation.activity', function (require) {
'use strict';

const {patch} = require("web.utils");
const components = {
    Activity: require('mail/static/src/components/activity/activity.js'),
    AttachmentList: require('mail/static/src/components/attachment_list/attachment_list.js')
};

components.Activity.components['AttachmentList'] = components.AttachmentList;

});