odoo.define("simpily_access_management.custom_filter_item", function (require) {
  "use strict";

  const ControlPanel = require("web.ControlPanel");
  const { patch } = require("web.utils");
  var rpc = require("web.rpc");

  patch(ControlPanel, "ControlPanelPatchBits", {
    async mounted() {
      var self = this;
      this._super(...arguments);
      self.removedFields = await rpc.query({
        model: "access.management",
        method: "get_hidden_field",
        args: ["", this?.props?.view?.model],
      });
      this.removedFields.forEach((element) => {
        delete self.fields[element];
      });
    },

    async patched() {
      var self = this;
      this._super(...arguments);
      self.removedFields = await rpc.query({
        model: "access.management",
        method: "get_hidden_field",
        args: ["", this?.props?.view?.model],
      });
      this.removedFields.forEach((element) => {
        delete self.fields[element];
      });
    },
  });
});
