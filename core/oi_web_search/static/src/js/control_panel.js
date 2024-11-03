odoo.define('oi_web_search.ControlPanel', function (require) {
    "use strict";
    
    const ControlPanel = require("web.ControlPanel");
    const SearchMenu = require("oi_web_search.SearchMenu");
    class MyControlPanel extends ControlPanel {
    	constructor() {
    		super(...arguments);
    	}
    }
        
    _.extend(MyControlPanel.components, {SearchMenu})
        
    return MyControlPanel;
    
});