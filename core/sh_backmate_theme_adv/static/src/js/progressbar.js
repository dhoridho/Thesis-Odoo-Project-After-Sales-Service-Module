odoo.define("sh_backmate_theme.Loading", function (require) {
    "use strict";


    var Loading = require('web.Loading');
    var config = require('web.config');
    var core = require('web.core');
    var framework = require('web.framework');
    var Widget = require('web.Widget');
    var rpc = require('web.rpc');

    var progress_style = 'none';


    rpc.query({
        model: 'sh.back.theme.config.settings',
        method: 'search_read',
        domain: [['id', '=', 1]],
        fields: ['progress_style']
    }).then(function (data) {
        if (data) {
            if (data[0]['progress_style'] == 'style_1') {
                progress_style = 'style_1';
            }
        }
    });

    var _t = core._t;

    Loading.include({

        on_rpc_event: function (increment) {

            var self = this;
            if (!this.count && increment === 1) {
                // Block UI after 3s
                if (progress_style == 'style_1') {
                    NProgress.configure({ showSpinner: false });
                    NProgress.start();
                }

                this.long_running_timer = setTimeout(function () {
                    self.blocked_ui = true;
                    framework.blockUI();
                }, 3000);
            }

            this.count += increment;
            if (this.count > 0) {
                // if (progress_style == 'none') {
                //     if (config.isDebug()) {
                //         this.$el.text(_.str.sprintf(_t("Loading (%d)"), this.count));
                //     } else {
                //         this.$el.text(_t("Loading"));
                //     }
                //     this.$el.show();
                // }

                this.getParent().$el.addClass('oe_wait');
            } else {
                this.count = 0;
                clearTimeout(this.long_running_timer);
                // Don't unblock if blocked by somebody else
                if (progress_style == 'style_1') {
                    NProgress.done();
                }


                if (self.blocked_ui) {
                    this.blocked_ui = false;
                    framework.unblockUI();
                }
                this.$el.fadeOut();
                this.getParent().$el.removeClass('oe_wait');
            }
        },
    });

});