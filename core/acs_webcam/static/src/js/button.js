odoo.define('acs_webcam.backend.button', function (require) {
'use strict';

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var field_registry = require('web.field_registry');

var _t = core._t;

//ACS: widget is like product redirct button
var WidgetWebcamButton = AbstractField.extend({
    events: {
        'click': '_onClick',
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    isSet: function () {
        return true;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
     _render: function () {
        this.$el.empty();
        var text = _t("Take Picture");
        var $iconval = $("<span class='fa fa-camera mr4' aria-label='Take Picture' style='color: #875a7b !important;' title='Take Picture'/>")
        var $val = $("<span style='cursor:pointer;'>").addClass('o_stat_text o_not_hover text-success').text(text);
        this.$el.append($iconval).append($val);
    },

    //--------------------------------------------------------------------------
    // Handler
    //--------------------------------------------------------------------------

    /**
     * Redirects to the website page of the record.
     *
     * @private
     */
    _onClick: function () {
        this.trigger_up('button_clicked', {
            attrs: {
                type: 'object',
                name: 'acs_open_website_url',
            },
            record: this.record,
        });
    },
});

field_registry
    .add('webcam_redirect_button', WidgetWebcamButton)
});
