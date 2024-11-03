odoo.define(
    "advance_access_management.CustomGroupByItem",
    function (require) {
      "use strict";
  
      const { patch } = require("web.utils");
      const GroupByMenu = require("web.GroupByMenu");
      var rpc = require("web.rpc");
  
      patch(GroupByMenu, "advance_access_management.GroupByMenuHideFieldPatch", {
        async willStart() {
          await this._super(...arguments);
          const res = await rpc.query({
            model: "access.management",
            method: "is_custom_group_available",
            args: ["", this.env.action.res_model],
          });
          this.hideGroupby = Boolean(res);
        },
      });
    }
  );
  