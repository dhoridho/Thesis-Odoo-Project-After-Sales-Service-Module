odoo.define("app_web_superbar.SuperbarModelExtension", function (require) {
    "use strict";

    const ActionModel = require("web/static/src/js/views/action_model.js");
    const SearchPanelModelExtension = require("web/static/src/js/views/search_panel_model_extension.js");


    class SuperbarModelExtension extends SearchPanelModelExtension {
        toggleCategoryValue(sectionId, valueId) {
            super.toggleCategoryValue(...arguments);
            console.log('patch toggleCategoryValue');
            // const { fieldName } = this.state.sections.get(sectionId);
            // const storageKey = this._getStorageKey(fieldName);
            // this.env.services.local_storage.setItem(storageKey, valueId);
        }
    }
    ActionModel.registry.add("Superbar", SuperbarModelExtension, 30);

    return SuperbarModelExtension;
});
