$(document).ready(function () { 

    var Domain = $("input[name='server_name']").val();
    var MeetingName = $("input[name='meeting_name']").val();
    var MeetingPwd = $("input[name='meeting_pwd']").val();
    var ReturnUrl = $("input[name='site_url']").val();
    

    var domain = Domain;
    var options = {
        roomName: MeetingName,
        parentNode: document.getElementById('acs_videocall'),
        configOverwrite: {
            disableDeepLinking: true
        },
        interfaceConfigOverwrite: {
            SHOW_JITSI_WATERMARK: false,
            SHOW_WATERMARK_FOR_GUESTS: false,
        }
    }
    var api = new JitsiMeetExternalAPI(domain, options);
    
    if (MeetingPwd) {
        api.addEventListener('videoConferenceJoined' , function(event) {
            if (event.role === "moderator") {
                api.executeCommand('password', MeetingPwd);
            }
        });

        api.addEventListener('participantRoleChanged', function(event) {
            if (event.role === "moderator") {
                api.executeCommand('password', MeetingPwd);
            }
        });
        //setTimeout(function () {
        //}, 20000);
    }
    api.addEventListener('readyToClose' , function() {
        window.location.href = ReturnUrl;
    });
});