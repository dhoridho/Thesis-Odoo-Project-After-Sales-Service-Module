odoo.define('equip3_crm_operation.FieldPercentPieNew', function (require) {
    "use strict";
    //
    var AbstractField = require('web.AbstractField');
    var registry = require('web.field_registry');
    var core = require('web.core');

    var qweb = core.qweb;
    var _t = core._t;
    var _lt = core._lt;

    var FieldPercentPieNew = AbstractField.extend({
        description: _lt("Percentage Pie New"),
        template: 'FieldPercentPieNew',
        supportedFieldTypes: ['integer', 'float'],

        /**
         * Register some useful references for later use throughout the widget.
         *
         * @override
         */
        start: function () {
            this.$leftMask = this.$('.o_mask_new').first();
            this.$rightMask = this.$('.o_mask_new').last();
            this.$pieValue = this.$('.o_pie_value_new');
            return this._super();
        },

        //--------------------------------------------------------------------------
        // Public
        //--------------------------------------------------------------------------

        /**
         * PercentPie widgets are always set since they basically only display info.
         *
         * @override
         */
        isSet: function () {
            return true;
        },

        //--------------------------------------------------------------------------
        // Private
        //--------------------------------------------------------------------------

        /**
         * This widget template needs javascript to apply the transformation
         * associated with the rotation of the pie chart.
         *
         * @override
         * @private
         */
        _render: function () {
            var value = this.value || 0;
            var degValue = 360*value/100;

            this.$rightMask.toggleClass('o_full_new', degValue >= 180);

            var leftDeg = 'rotate(' + ((degValue < 180)? 180 : degValue) + 'deg)';
            var rightDeg = 'rotate(' + ((degValue < 180)? degValue : 0) + 'deg)';
            this.$leftMask.css({transform: leftDeg, msTransform: leftDeg, mozTransform: leftDeg, webkitTransform: leftDeg});
            this.$rightMask.css({transform: rightDeg, msTransform: rightDeg, mozTransform: rightDeg, webkitTransform: rightDeg});
            this.$pieValue.text(Math.round(value) + '%');
        },
    });

    registry.add('percentpienew', FieldPercentPieNew)

    return FieldPercentPieNew

});

