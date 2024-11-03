odoo.define('equip3_hashmicro_ui.ListController', function(require){
    "use strict";

    var ListController = require('web.ListController');
    var core = require('web.core');
    var qweb = core.qweb;

    ListController.include({
        _updateSelectionBox() {
            this._renderHeaderButtons();
            if (this.$selectionBox) {
                this.$selectionBox.remove();
                this.$selectionBox = null;
            }
            if (this.selectedRecords.length) {
                const state = this.model.get(this.handle, {raw: true});
                this.$selectionBox = $(qweb.render('ListView.selection', {
                    isDomainSelected: this.isDomainSelected,
                    isPageSelected: this.isPageSelected,
                    nbSelected: this.selectedRecords.length,
                    nbTotal: state.count,
                }));
                this.$selectionBox.appendTo(this.$buttons);
            }
        },
    });
    return ListController;
});