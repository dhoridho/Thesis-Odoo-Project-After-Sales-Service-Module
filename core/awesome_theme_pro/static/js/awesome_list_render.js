odoo.define('awesome.ListRenderer', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer')
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')

    ListRenderer.include({
        /**
         * rewrite to add class
         */
        _renderEmptyRow: function () {
            var $td = $('<td>&nbsp;</td>').attr('colspan', this._getNumberOfCols());
            return $('<tr class="awesome_empty_row">').append($td);
        },

        async _renderView() {
            await this._super.apply(this, arguments)
            if (BackendUserSetting.settings.table_style == "bordered") {
                console.log(this.$('table'))
                this.$('table').addClass('table-bordered');
            }
        },
    })

    return ListRenderer;
})