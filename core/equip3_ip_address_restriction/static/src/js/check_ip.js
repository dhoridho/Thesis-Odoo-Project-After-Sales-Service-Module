odoo.define('equip3_ip_address_restriction.check_ip', function (require) {
    "use strict";

    var session = require('web.session');

    function getIpAddress() {
        console.log('Getting IP address...');  // Log when the function is called
        $.get('https://api.ipify.org?format=json', function(data) {
            console.log('Server response:', data);  // Log the raw server response
            var ip = data.ip; 
            session.rpc('/update_ip', {ip: ip});
            console.log('IP address updated to ' + ip);  // Log the IP address
        });
    }

    setInterval(getIpAddress, 5 * 60 * 1000);  // Check IP every 5 minute
});