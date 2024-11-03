odoo.define(
    "advance_access_management.filter_menu",
    function (require) {
      "use strict";
  
      const { patch } = require("web.utils");
      const FilterMenu = require("web.FilterMenu");
      var rpc = require("web.rpc");
  
      patch(FilterMenu, "FilterMenuHideFieldPatch", {
        async willStart() {
          await this._super(...arguments);
          const res = await rpc.query({
            model: "access.management",
            method: "is_custom_filter_available",
            args: ["", this.env.action.res_model],
          });
          this.hideFilter = Boolean(res);
        },
      });
    }
  );
  