odoo.define('equip3_general_attachment.attachment_box', function (require) {
    'use strict';

    const AttachmentBox = require('mail/static/src/components/attachment_box/attachment_box.js');
    const { patch } = require('web.utils');

    patch(AttachmentBox, 'equip3_general_attachment.attachment_box', {

        _onAttachmentCreated(ev) {
            console.log('_onAttachmentCreated');
            this._super(ev);
            this.trigger('reload');
            $('.o_form_refresh_cp').click();
        },
    
        /**
         * @private
         * @param {Event} ev
         */
        _onAttachmentRemoved(ev) {
            console.log('_onAttachmentRemoved');
            this._super(ev);

            var self = this
            setTimeout(function () {
                self.trigger('reload');
                $('.o_form_refresh_cp').click();
            }, 1500);
        }
    });
});
