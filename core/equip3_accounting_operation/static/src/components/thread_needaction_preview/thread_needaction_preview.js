odoo.define("equip3_accounting_operation/static/src/components/thread_needaction_preview/thread_needaction_preview.js", function (require) {
    "use strict";

    const {patch} = require("web.utils");
    const ThreadNeedactionPreview = require("mail/static/src/components/thread_needaction_preview/thread_needaction_preview.js");

    patch(ThreadNeedactionPreview, "equip3_accounting_operation/static/src/components/thread_needaction_preview/thread_needaction_preview.js", {
        /**
         * @private
         * @param {MouseEvent} ev
         */
        _onClick(ev) {
            if (this.thread.model === "account.move") {
                const markAsRead = this._markAsReadRef.el;
                if (markAsRead && markAsRead.contains(ev.target)) {
                    // handled in `_onClickMarkAsRead`
                    return;
                }
                this.env.bus.trigger('do-action', {
                    action: {
                        name: this.env._t("Bill"),
                        type: 'ir.actions.act_window',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'current',
                        res_model: this.thread.model,
                        res_id: this.thread.id,
                    },
                });
                if (!this.env.messaging.device.isMobile) {
                    this.env.messaging.messagingMenu.close();
                }
            }
            else {
                return this._super(...arguments);
            }
        }
    });
});