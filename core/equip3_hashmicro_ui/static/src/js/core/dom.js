odoo.define('equip3_hashmicro_ui.dom', function(require){
    "use strict";

    const dom = require('web.dom');

    function renderButton(options) {
        var jQueryParams = _.extend({
            type: 'button',
        }, options.attrs || {});

        var extraClasses = jQueryParams.class;
        if (extraClasses) {
            // If we got extra classes, check if old oe_highlight/oe_link
            // classes are given and switch them to the right classes (those
            // classes have no style associated to them anymore).
            // TODO ideally this should be dropped at some point.
            extraClasses = extraClasses.replace(/\boe_highlight\b/g, 'btn-primary')
                                        .replace(/\boe_link\b/g, 'btn-link');
        }

        jQueryParams.class = 'btn';
        if (options.size) {
            jQueryParams.class += (' btn-' + options.size);
        }
        jQueryParams.class += (' ' + (extraClasses || 'btn-secondary'));

        var $button = $('<button/>', jQueryParams);

        if (options.icon) {
            if (options.icon.substr(0, 3) === 'fa-' || options.icon.substr(0, 4) === 'o-hm') {
                let icon = options.icon;
                if (options.icon.substr(0, 4) === 'o-hm'){
                    icon = 'o-hm-icon ' + icon;
                }
                $button.append($('<i/>', {
                    class: 'fa fa-fw o_button_icon ' + icon,
                }));
            } else {
                $button.append($('<img/>', {
                    src: options.icon,
                }));
            }
        }
        if (options.text) {
            $button.append($('<span/>', {
                text: options.text,
            }));
        }

        return $button;
    }

    dom.renderButton = renderButton;
    return dom;
});