odoo.define('wt_tricsa_website.cart', function (require) {
'use strict';

    const publicWidget = require('web.public.widget');

    publicWidget.registry.maintenance_request_form = publicWidget.Widget.extend({
        selector: '.form-horizontal',
        events: {
            'change select[name="facility_area"]': '_onChangefacArea',
        },

        start: function () {

            this.$fac_area = this.$('select[name="facility_area"]');
            this.$fac_areaOptions = this.$fac_area.filter(':enabled').find('option:not(:first)');
            this.$equipment = this.$('select[name="equipment_id"]');
            this.$equipmentOptions = this.$equipment.filter(':enabled').find('option:not(:first)');
            this._adaptEquipmentForm();

        },

        _onChangefacArea: function () {
            this._adaptEquipmentForm();
        },

        /**
         * @private
         */

        _adaptEquipmentForm: function () {
            var $fac_area = this.$('select[name="facility_area"]');
            var fac_area_id = ($fac_area.val() || 0);
            this.$equipmentOptions.detach();
            var $displayedequipment = this.$equipmentOptions.filter('[data-fac-area=' + fac_area_id + ']');
            var cb = $displayedequipment.appendTo(this.$equipment).show().length;
            // this.$equipment.parent().toggle(cb >= 1);
        },
    });
});
