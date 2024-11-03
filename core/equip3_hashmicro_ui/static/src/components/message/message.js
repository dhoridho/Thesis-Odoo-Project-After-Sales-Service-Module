odoo.define('equip3_hashmicro_ui/static/src/components/message/message.js', function (require) {
'use strict';

const components = {
    Message: require('mail/static/src/components/message/message.js'),
};

const { patch } = require('web.utils');

patch(components.Message, 'equip3_hashmicro_ui/static/src/components/message/message.js', {
    /**
     * @override
     */
     /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClick(ev) {
        if (ev.target.closest('.o_channel_redirect')) {
            this.env.messaging.openProfile({
                id: Number(ev.target.dataset.oeId),
                model: 'mail.channel',
            });
            // avoid following dummy href
            ev.preventDefault();
            return;
        }
        if (ev.target.tagName === 'A') {
            if ($(ev.target).is('a')) {
                window.location.href = $(ev.target).attr('href');
                $(ev.target).attr("target", "_self");
                window.location.reload();
            }
            else {
                if (ev.target.dataset.oeId && ev.target.dataset.oeModel) {
                    this.env.messaging.openProfile({
                        id: Number(ev.target.dataset.oeId),
                        model: ev.target.dataset.oeModel,
                    });
                    // avoid following dummy href
                    ev.preventDefault();
                }
                return;
            }
        }
        this.state.isClicked = !this.state.isClicked;
    }
});
});