odoo.define(
    "simpily_access_management.group_by_menu",
    function (require) {
      "use strict";
  
      const { patch } = require("web.utils");
      const GroupByMenu = require("web.GroupByMenu");
      var rpc = require("web.rpc");
  
      patch(GroupByMenu, "GroupByMenuHideFieldPatch", {
        async willStart() {
          await this._super(...arguments);
          const res = await rpc.query({
            model: "access.management",
            method: "get_hidden_field",
            args: ["", this?.env?.searchModel?.config?.modelName],
          });
          debugger
          this.fields = this.fields.filter((ele) => !res.includes(ele.name));
        },
      });
    }
  );
  