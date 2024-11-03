odoo.define('sh_backmate_theme_adv.messaging_menu', function (require) {
    "use strict";
    const MessageMenu = require('mail/static/src/components/messaging_menu/messaging_menu.js')
    const core = require('web.core')

    MessageMenu.patch("sh_backmate_theme_adv.messaging_menu", T =>
        class extends T {

            async willUpdateProps(nextProps) {
                await super.willUpdateProps(nextProps);
            }

            mounted() {
                super.mounted()
            }

            patched() {
                super.patched()
            }

            _onClickToggler(ev) {
                // avoid following dummy href
                ev.preventDefault();
                if (!this.env.messaging) {
                    /**
                     * Messaging not created, which means essential models like
                     * messaging menu are not ready, so user interactions are omitted
                     * during this (short) period of time.
                     */
                    return;
                }
                this.messagingMenu.toggleOpen();
                if (!$('.o_web_client').hasClass('modal-open')) {
                    document.body.classList.add('modal-open');
                } else {
                    document.body.classList.remove('modal-open');
                }
            }
        }
    );

});
