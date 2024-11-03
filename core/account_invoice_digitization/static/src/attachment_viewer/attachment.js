odoo.define('account_invoice_digitization/static/src/attachment_viewer/attachment.js', function (require) {
    'use strict';

const {
    registerClassPatchModel,
    registerFieldPatchModel,
    registerInstancePatchModel
} = require('mail/static/src/model/model_core.js');
const { attr } = require('mail/static/src/model/model_field.js');

    registerClassPatchModel('mail.attachment', 'account_invoice_digitization/static/src/attachment_viewer/attachment.js', {

        convertData(data) {
            const data2 = this._super(data)
            data2.enable_digitizer = data.enable_digitizer
            return data2
        },
    });

    registerFieldPatchModel('mail.attachment', 'account_invoice_digitization/static/src/attachment_viewer/attachment.js', {
        enable_digitizer: attr({default: false})

    });

    registerInstancePatchModel('mail.attachment', 'account_invoice_digitization/static/src/attachment_viewer/attachment.js', {
        _created() {
            this.onClickReload = this.onClickReload.bind(this)
        },
        async reloadAiData() {
            self = this
            await this.env.services.rpc({
                model: 'ir.attachment',
                method: 'create_document_from_attachment',
                args: [[self.id]],
            });

            window.location.reload();
        },

        async onClickReload(ev) {
            ev.stopPropagation();
            await this.reloadAiData()

        },
    });
});