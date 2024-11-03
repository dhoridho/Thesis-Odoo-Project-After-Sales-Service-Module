odoo.define('app_odoo_boost.mail.Manager', function (require) {
    "use strict";

    // todo: 改为 owl
    const components = {
        ChatWindowManager: require('mail/static/src/components/chat_window_manager/chat_window_manager.js'),
    };
//
//     var session = require('web.session');
//     var MailManager = require('mail.Manager');
//
// //从前端停止 im_status，后端代码在 source/bus/controllers/main.py
//     MailManager.include({
//         //--------------------------------------------------------------------------
//         // Private
//         //--------------------------------------------------------------------------
//         /**
//          * Fetch the list of im_status for partner with id in ids list and triggers
//          * an update.
//          *
//          * @private
//          * @param {Object} data
//          * @param {integer[]} data.partnerIDs
//          * @return {Deferred}
//          */
//         _fetchImStatus: function (data) {
//             var self = this;
//             var def = Promise.reject();
//             if (session.app_disable_poll || !session.app_enable_discuss) {
//                 return Promise.all([def]);
//             } else {
//                 return self._super.apply(this, arguments);
//             }
//         },
//         _fetchMissingImStatus: function (data) {
//             var self = this;
//             var def = Promise.reject();
//             if (session.app_disable_poll || !session.app_enable_discuss) {
//                 return Promise.all([def]);
//             } else {
//                 return self._super.apply(this, arguments);
//             }
//         },
//     });

});
