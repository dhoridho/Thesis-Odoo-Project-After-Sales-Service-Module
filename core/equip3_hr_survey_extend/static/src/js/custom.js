$(document).ready(function () { 

    'use strict';

    function callRecording(){
        let constraintObj = { 
                audio: false, 
                video: { 
                    facingMode: "user", 
                    width: { min: 640, ideal: 1280, max: 1920 },
                    height: { min: 480, ideal: 720, max: 1080 } 
                } 
            }; 
            // width: 1280, height: 720  -- preference only
            // facingMode: {exact: "user"}
            // facingMode: "environment"
            
            //handle older browsers that might implement getUserMedia in some way
            if (navigator.mediaDevices === undefined) {
                navigator.mediaDevices = {};
                navigator.mediaDevices.getUserMedia = function(constraintObj) {
                    let getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
                    if (!getUserMedia) {
                        return Promise.reject(new Error('getUserMedia is not implemented in this browser'));
                    }
                    return new Promise(function(resolve, reject) {
                        getUserMedia.call(navigator, constraintObj, resolve, reject);
                    });
                }
            }else{
                navigator.mediaDevices.enumerateDevices()
                .then(devices => {
                    devices.forEach(device=>{
                        console.log(device.kind.toUpperCase(), device.label);
                        //, device.deviceId
                    })
                })
                .catch(err=>{
                    console.log(err.name, err.message);
                })
            }

            navigator.mediaDevices.getUserMedia(constraintObj)
            .then(function(mediaStreamObj) {
                //connect the media stream to the first video element
                let video = document.querySelector('video');
                if ("srcObject" in video) {
                    video.srcObject = mediaStreamObj;
                } else {
                    //old version
                    video.src = window.URL.createObjectURL(mediaStreamObj);
                }
                
                video.onloadedmetadata = function(ev) {
                    //show in the video element what is being captured by the webcam
                    video.play();
                };
                
                //add listeners for saving video/audio
                let start = document.getElementById('btnStart');
                let stop = document.getElementById('btnStop');
                let vidSave = document.getElementById('vid2');
                let mediaRecorder = new MediaRecorder(mediaStreamObj);
                let chunks = [];
                
                start.addEventListener('click', (ev)=>{
      
                    mediaRecorder.start();
                })
                stop.addEventListener('click', (ev)=>{
                    mediaRecorder.stop();

                });
                mediaRecorder.ondataavailable = function(ev) {
                    chunks.push(ev.data);
                }
                mediaRecorder.onstop = (ev)=>{
                    let blob = new Blob(chunks, { 'type' : 'video/mp4;' });
                    chunks = [];
                    let videoURL = window.URL.createObjectURL(blob);
                    vidSave.src = videoURL;
                }
            })
            .catch(function(err) { 
                console.log(err.name, err.message); 
            });
    }

        
    if($('#video_setting_survey').length>0){
        var tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        var firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
        // callRecording()

    }

    $('body').bind('copy paste cut',function(e) {
      e.preventDefault();
      alert('Cut, Copy & Paste options are disabled !!');
    });


    


    $("#video_setting_survey").click(function(){
            $('#modal_video_setting_survey').modal({backdrop: 'static', keyboard: false})
            const videoElement = document.querySelector('video');
            const audioInputSelect = document.querySelector('select#choose_microphone_select');
            const audioOutputSelect = document.querySelector('select#choose_speaker_select');
            const videoSelect = document.querySelector('select#choose_camera_select');
            const selectors = [audioInputSelect, audioOutputSelect, videoSelect];

            audioOutputSelect.disabled = !('sinkId' in HTMLMediaElement.prototype);

            function gotDevices(deviceInfos) {
              // Handles being called several times to update labels. Preserve values.
              const values = selectors.map(select => select.value);
              selectors.forEach(select => {
                while (select.firstChild) {
                  select.removeChild(select.firstChild);
                }
              });

              for (let i = 0; i !== deviceInfos.length; ++i) {
                const deviceInfo = deviceInfos[i];
                const option = document.createElement('option');
                option.value = deviceInfo.deviceId;
                if (deviceInfo.kind === 'audioinput') {
                  option.text = deviceInfo.label || `Microphone ${audioInputSelect.length + 1}`;
                  audioInputSelect.appendChild(option);
                } else if (deviceInfo.kind === 'audiooutput') {
                  option.text = deviceInfo.label || `Speaker ${audioOutputSelect.length + 1}`;
                  audioOutputSelect.appendChild(option);
                } else if (deviceInfo.kind === 'videoinput') {
                  option.text = deviceInfo.label || `Camera ${videoSelect.length + 1}`;
                  videoSelect.appendChild(option);
                } else {
                  console.log('Some other kind of source/device: ', deviceInfo);
                }
              }
              selectors.forEach((select, selectorIndex) => {
                if (Array.prototype.slice.call(select.childNodes).some(n => n.value === values[selectorIndex])) {
                  select.value = values[selectorIndex];
                }
              });
            }

            navigator.mediaDevices.enumerateDevices().then(gotDevices).catch(handleError);

            // Attach audio output device to video element using device/sink ID.
            function attachSinkId(element, sinkId) {
              if (typeof element.sinkId !== 'undefined') {
                element.setSinkId(sinkId)
                    .then(() => {
                      console.log(`Success, audio output device attached: ${sinkId}`);
                    })
                    .catch(error => {
                      let errorMessage = error;
                      if (error.name === 'SecurityError') {
                        errorMessage = `You need to use HTTPS for selecting audio output device: ${error}`;
                      }
                      console.error(errorMessage);
                      // Jump back to first output device in the list as it's the default.
                      audioOutputSelect.selectedIndex = 0;
                    });
              } else {
                console.warn('Browser does not support output device selection.');
              }
            }

            function changeAudioDestination() {
              const audioDestination = audioOutputSelect.value;
        
              attachSinkId(videoElement, audioDestination);
            }

            function gotStream(stream) {
              window.stream = stream; // make stream available to console
           
              videoElement.srcObject = stream;
              // Refresh button list in case labels have become available
              return navigator.mediaDevices.enumerateDevices();
            }

            function handleError(error) {
              console.log('navigator.MediaDevices.getUserMedia error: ', error.message, error.name);
            }

            function start() {
              if (window.stream) {
                window.stream.getTracks().forEach(track => {
                  track.stop();
                });
              }
              const audioSource = audioInputSelect.value;
              const videoSource = videoSelect.value;
              const constraints = {
                audio: {deviceId: audioSource ? {exact: audioSource} : undefined},
                video: {deviceId: videoSource ? {exact: videoSource} : undefined}
              };
              navigator.mediaDevices.getUserMedia(constraints).then(gotStream).then(gotDevices).catch(handleError);
            }

            audioInputSelect.onchange = start;
            audioOutputSelect.onchange = changeAudioDestination;

            videoSelect.onchange = start;
            start();


        });
    $("#config_cam_test").click(function(){
        $('#modal_test_cam_setting_survey').modal({backdrop: 'static', keyboard: false})
            let constraintObj = { 
                audio: false, 
                video: { 
                    facingMode: "user", 
                    width: { min: 640, ideal: 1280, max: 1920 },
                    height: { min: 480, ideal: 720, max: 1080 } 
                } 
                }; 
            // width: 1280, height: 720  -- preference only
            // facingMode: {exact: "user"}
            // facingMode: "environment"
            //handle older browsers that might implement getUserMedia in some way
            if (navigator.mediaDevices === undefined) {
                navigator.mediaDevices = {};
                navigator.mediaDevices.getUserMedia = function(constraintObj) {
                    let getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
                    if (!getUserMedia) {
                        return Promise.reject(new Error('getUserMedia is not implemented in this browser'));
                    }
                    return new Promise(function(resolve, reject) {
                        getUserMedia.call(navigator, constraintObj, resolve, reject);
                    });
                }
            }else{
                navigator.mediaDevices.enumerateDevices()
                .then(devices => {
                    devices.forEach(device=>{
                        //, device.deviceId
                    })
                })
                .catch(err=>{
                    console.log(err.name, err.message);
                })
            }

            navigator.mediaDevices.getUserMedia(constraintObj)
            .then(function(mediaStreamObj) {
                //connect the media stream to the first video element
                // let video = document.querySelector('video_testing2');
                const video = document.querySelector('video#video_testing');
                if ("srcObject" in video) {
                    video.srcObject = mediaStreamObj;
                } else {
                    //old version
                    video.src = window.URL.createObjectURL(mediaStreamObj);
                }
                
                video.onloadedmetadata = function(ev) {
                    //show in the video element what is being captured by the webcam
                    video.play();
                };
                
         
                let mediaRecorder = new MediaRecorder(mediaStreamObj);
                let chunks = [];
                 mediaRecorder.start();
                
                
                mediaRecorder.ondataavailable = function(ev) {
                    chunks.push(ev.data);
                }
                
            })
            .catch(function(err) { 
                console.log(err.name, err.message); 
            });
        });
    // $("#button_stop_test_camera").click(function(){


    //     });

    var audioElement = document.getElementById("audio-playback1");

    
    audioElement.addEventListener('ended', function() {
        $('#test_speaker_audio .fa').addClass('fa-play')
        $('#test_speaker_audio .fa').removeClass('fa-stop')
    }, false);

    $("#range_sound_screen").change(function(){
        var allaudio = document.querySelector('audio');
        allaudio.volume = parseFloat($("#range_sound_screen").val())/10;
    })

    $('.done_config_testing').click(function(){
        const preview = document.getElementById("audio-playback");
        if($('#config_mic_test .fa').hasClass('fa-stop')){
            $('#config_mic_test').click()
        }
        if($('#test_speaker_audio .fa').hasClass('fa-stop')){
            $("#test_speaker_audio").click()
        }
        window.stream.getTracks().forEach(function(track) {
          track.stop();
        });
    })


    var audioElement1 = document.getElementById("audio-playback");

    
    audioElement1.addEventListener('ended', function() {
        $('#config_mic_test .fa').addClass('fa-microphone')
        $('#config_mic_test .fa').removeClass('fa-stop')
        $('#config_mic_test .fa').removeClass('fa-circle')
    }, false);


    $("#config_mic_test").click(function(){
        let recorder, audio_stream;
        const downloadAudio = document.getElementById("downloadButton");
        const recordButton = document.getElementById("config_mic_test");
        const preview = document.getElementById("audio-playback");
        if($('#config_mic_test .fa').hasClass('fa-stop')){
            $('#config_mic_test .fa').addClass('fa-microphone')
            $('#config_mic_test .fa').removeClass('fa-stop')
            preview.pause();
        }
        else if($('#config_mic_test .fa').hasClass('fa-microphone')){
            $(".done_config_testing").css('pointer-events', 'none')
            $(".done_config_testing").css('opacity', 0.4)
            $("#config_mic_test").css('pointer-events', 'none')
            $("#config_mic_test").css('opacity', 0.4)
                navigator.mediaDevices.getUserMedia({ audio: true })
                    .then(function (stream) {
                        audio_stream = stream;
                        recorder = new MediaRecorder(stream);

                        // when there is data, compile into object for preview src
                        recorder.ondataavailable = function (e) {
                            const url = URL.createObjectURL(e.data);
                            preview.src = url;
                        };
                        recorder.start();

                        var timeout_status = setTimeout(function () {
                             recorder.stop();
                            audio_stream.getAudioTracks()[0].stop();

                            setTimeout(function () {
                                $('#config_mic_test .fa').removeClass('fa-circle')
                                $('#config_mic_test .fa').addClass('fa-stop')
                                preview.play();
                                $("#config_mic_test").css('pointer-events', 'inherit')
                                $("#config_mic_test").css('opacity', 1)
                                $(".done_config_testing").css('pointer-events', 'inherit')
                                $(".done_config_testing").css('opacity', 1)
                            }, 1000);                            
                            
                        }, 3000);
                    });
                $('#config_mic_test .fa').removeClass('fa-microphone')
                $('#config_mic_test .fa').addClass('fa-circle')

            }
        

        

    });


    $("#test_speaker_audio").click(function(){
        audioElement.currentTime = 0;
        if($('#test_speaker_audio .fa').hasClass('fa-play')){
            audioElement.play();
            $('#test_speaker_audio .fa').removeClass('fa-play')
            $('#test_speaker_audio .fa').addClass('fa-stop')
        }
        else{
            audioElement.pause();
            $('#test_speaker_audio .fa').addClass('fa-play')
        $('#test_speaker_audio .fa').removeClass('fa-stop')
        }
        

    });

    

})
odoo.define('equip3_hr_survey_extend.custom', ['survey.form'], function (require) {
    "use strict";

    var survey = require('survey.form');
    // console.log("survey", survey);

    var DataSet = survey.include({
        events: _.extend({}, survey.prototype.events, {
            'click .open_qustion_popup': 'OpenQuestionPopup', 
            'click .button_confirm_done_response': 'ButtonConfirmDoneResponse', 
            'click .start_kraepelin': 'ButtonStartKraepelin', 
            'click .button_submit_survey_fill': 'ButtonSubmitSurvey', 
            'click #video_setting_survey': 'ButtonClickSetting', 
            // 'click .btn-survey-form-start': 'ButtonStartSurvey',
            'input .input_field': '_onInputField',

        }),

        // /**
        // * @override
        // */
        // start: function () {
        //     var self = this;
        //     this.fadeInOutDelay = 400;
        //     return this._super.apply(this, arguments).then(function () {
        //         if (self.events.hasOwnProperty('click .start_kraepelin')) {
        //             self.$('button.button_submit_survey_fill').css({ "display": 'none'});
        //             self.$('span.d-md-inline').removeClass('d-md-inline').css({ "display": 'none'});
                    
        //         }
        //     });
        // },

        _onInputField: function (event) {
            var $input = $(event.currentTarget);
            var maxLength = $input.attr('maxlength');
            var inputValue = $input.val();

            if (inputValue.length >= maxLength) {
                var $allInputs = $('.input_field');
                var currentIndex = $allInputs.index($input);
                var $nextInput = $allInputs.eq(currentIndex + 1);

                while ($nextInput.length && $nextInput.prop('disabled')) {
                    currentIndex++;
                    $nextInput = $allInputs.eq(currentIndex + 1);
                }

                if ($nextInput.length) {
                    $nextInput.focus();
                }
            }
        },

        ButtonClickSetting: function(event1) {
            $('#modal_video_setting_survey').modal({backdrop: 'static', keyboard: false})
            const videoElement = document.querySelector('video');
            const audioInputSelect = document.querySelector('select#choose_microphone_select');
            const audioOutputSelect = document.querySelector('select#choose_speaker_select');
            const videoSelect = document.querySelector('select#choose_camera_select');
            const selectors = [audioInputSelect, audioOutputSelect, videoSelect];

            audioOutputSelect.disabled = !('sinkId' in HTMLMediaElement.prototype);

            function gotDevices(deviceInfos) {
              // Handles being called several times to update labels. Preserve values.
              const values = selectors.map(select => select.value);
              selectors.forEach(select => {
                while (select.firstChild) {
                  select.removeChild(select.firstChild);
                }
              });

              for (let i = 0; i !== deviceInfos.length; ++i) {
                const deviceInfo = deviceInfos[i];
                const option = document.createElement('option');
                option.value = deviceInfo.deviceId;
                if (deviceInfo.kind === 'audioinput') {
                  option.text = deviceInfo.label || `Microphone ${audioInputSelect.length + 1}`;
                  audioInputSelect.appendChild(option);
                } else if (deviceInfo.kind === 'audiooutput') {
                  option.text = deviceInfo.label || `Speaker ${audioOutputSelect.length + 1}`;
                  audioOutputSelect.appendChild(option);
                } else if (deviceInfo.kind === 'videoinput') {
                  option.text = deviceInfo.label || `Camera ${videoSelect.length + 1}`;
                  videoSelect.appendChild(option);
                } else {
                  console.log('Some other kind of source/device: ', deviceInfo);
                }
              }
              selectors.forEach((select, selectorIndex) => {
                if (Array.prototype.slice.call(select.childNodes).some(n => n.value === values[selectorIndex])) {
                  select.value = values[selectorIndex];
                }
              });
            }

            navigator.mediaDevices.enumerateDevices().then(gotDevices).catch(handleError);

            // Attach audio output device to video element using device/sink ID.
            function attachSinkId(element, sinkId) {
              if (typeof element.sinkId !== 'undefined') {
                element.setSinkId(sinkId)
                    .then(() => {
                      console.log(`Success, audio output device attached: ${sinkId}`);
                    })
                    .catch(error => {
                      let errorMessage = error;
                      if (error.name === 'SecurityError') {
                        errorMessage = `You need to use HTTPS for selecting audio output device: ${error}`;
                      }
                      console.error(errorMessage);
                      // Jump back to first output device in the list as it's the default.
                      audioOutputSelect.selectedIndex = 0;
                    });
              } else {
                console.warn('Browser does not support output device selection.');
              }
            }

            function changeAudioDestination() {
              const audioDestination = audioOutputSelect.value;
        
              attachSinkId(videoElement, audioDestination);
            }

            function gotStream(stream) {
              window.stream = stream; // make stream available to console
           
              videoElement.srcObject = stream;
              // Refresh button list in case labels have become available
              return navigator.mediaDevices.enumerateDevices();
            }

            function handleError(error) {
              console.log('navigator.MediaDevices.getUserMedia error: ', error.message, error.name);
            }

            function start() {
              if (window.stream) {
                window.stream.getTracks().forEach(track => {
                  track.stop();
                });
              }
              const audioSource = audioInputSelect.value;
              const videoSource = videoSelect.value;
              const constraints = {
                audio: {deviceId: audioSource ? {exact: audioSource} : undefined},
                video: {deviceId: videoSource ? {exact: videoSource} : undefined}
              };
              navigator.mediaDevices.getUserMedia(constraints).then(gotStream).then(gotDevices).catch(handleError);
            }

            audioInputSelect.onchange = start;
            audioOutputSelect.onchange = changeAudioDestination;

            videoSelect.onchange = start;
            start();
        },

        ButtonSubmitSurvey: function(event1) {
            var self = this
            if ($(".table-kraepelin")[0]) {
                var questionArray = []
                var answerArray = []

                // $("span.rand_num").each(function(){
                //     questionArray.push($(this).text())
                // });

                // $("table.table-kraepelin :input").each(function(){
                //     answerArray.push($(this).val())
                // });
                var rowIndex = 1
                var timer = self.$('[class^="timer-"]');
                timer.each(function(){
                    $(`.rand_num_col-${rowIndex}`).each(function(){
                        questionArray.push($(this).text())
                    });
                    $(`.input-${rowIndex}`).each(function(){
                        answerArray.push($(this).val())
                    });
                    rowIndex+=1
                });

                var currentUrl = window.location.href;
                var parts = currentUrl.split('/');
                var accessToken = parts[parts.length - 1].replace('#', '');

                var self = this
                var params = {}

                params['access_token'] = accessToken
                params['question_array'] = questionArray
                params['answer_array'] = answerArray

                var route = "/survey/save/kraepelin";
                var submitPromise = self._rpc({
                    route: _.str.sprintf('%s', route),
                    params: params,
                });
            }
        },

        _onKeyDown: function (event) {
            var keyCode = event.keyCode;
            if (keyCode === 13) {  // Enter
                event.preventDefault();
                if ($(".start_kraepelin")[0]) {
                    return;
                }
            }
            // If user is answering a text input, do not handle keydown
            if (this.$("textarea").is(":focus") || this.$('input').is(':focus')) {
                if (keyCode === 8) {
                // Backspace key was pressed
                    var $currentInput = this.$("input:focus");
                    var $prevRow = $currentInput.closest("tr").prev("tr");
                    var $prevInput = $prevRow.find("input:not(:disabled)").last();
                    if ($prevInput.length) {
                        $prevInput.focus();
                    }
                }
                return;
            }
            // If in session mode and question already answered, do not handle keydown
            if (this.$('fieldset[disabled="disabled"]').length !== 0) {
                return;
            }

            var self = this;
            var keyCode = event.keyCode;
            var letter = String.fromCharCode(keyCode).toUpperCase();
            // Handle Start / Next / Submit
            if (keyCode === 13 || keyCode === 39) {  // Enter or arrow-right: go Next
                event.preventDefault();
                if (!this.preventEnterSubmit && this.$('button[type="submit"]').length != 0) {
                    var isFinish = this.$('button[value="finish"]').length !== 0;
                    this._submitForm({isFinish: isFinish});
                }
            } else if (keyCode === 37) {  // arrow-left: previous (if available)
                // It's easier to actually click on the button (if in the DOM) as it contains necessary
                // data that are used in the event handler.
                // Again, global selector necessary since the navigation is outside of the form.
                $('.o_survey_navigation_submit[value="previous"]').click();
            } else if (self.options.questionsLayout === 'page_per_question'
                       && letter.match(/[a-z]/i)) {
                var $choiceInput = this.$(`input[data-selection-key=${letter}]`);
                if ($choiceInput.length === 1) {
                    $choiceInput.prop("checked", !$choiceInput.prop("checked")).trigger('change');

                    // Avoid selection key to be typed into the textbox if 'other' is selected by key
                    event.preventDefault();
                }
            }
        },

        formatTime: function(totalSeconds) {
            var minutes = Math.floor(totalSeconds / 60);
            var seconds = totalSeconds % 60;
            return minutes + ":" + (seconds < 10 ? "0" : "") + seconds;
        },

        startTimer: async function(rowIndex) {
            var self = this;
            var timer = self.$('[class^="timer-"]');
            
            if (rowIndex <= (timer.length * 2)) {
                var currentTimerValue = self.$(`.timerValue-${rowIndex}`);
                var currentTimer = self.$(`.timer-${rowIndex}`);
                var currentInput = self.$(`.input-${rowIndex}`);
                var currentColumn1 = self.$(`.column-${rowIndex}`);
                var currentColumn2 = self.$(`.column-${rowIndex + 1}`);
                var timeLeft = currentTimerValue.text()
            
                currentTimer.css({"display": "revert"});
                currentInput.prop('disabled', false);
                currentColumn1.css({"background-color": "white"});
            
                // Define an asynchronous function to iterate over input fields
                var iterateInputFields = async function() {
                    return new Promise((resolve) => {
                        var $inputFields = self.$('.input_field');
                        $inputFields.each(function(index, element) {
                            if (!$(element).prop('disabled')) {
                                $(element).focus();
                                resolve(); // Resolve the promise once focus is set
                                return false; // Exit the loop after focusing on the first non-disabled input field
                            }
                        });
                    });
                };
                if(rowIndex == 1){
                    await iterateInputFields(); // Wait for focus to be set on the input field
                }
            
                var timerInterval = setInterval(async function() {
                    timeLeft--;
                
                    var formattedTime = self.formatTime(timeLeft);
                    currentTimer.text(formattedTime);
                
                    if (timeLeft <= 0) {
                        clearInterval(timerInterval);
                        currentTimer.css({"display": "none"});
                        currentInput.prop('disabled', true);
                        currentColumn1.css({"background-color": "lightgrey"});
                        await new Promise((resolve) => {
                            setTimeout(resolve, 2000); // Delay of 2 seconds
                        });
                        await self.startTimer(rowIndex + 1);
                        await iterateInputFields(); // Wait for focus to be set on the input field
                    }
                }, 1000);
            }
        },

        ButtonStartKraepelin: function (event1) {
            var kraepelinTable = this.$('table.table-kraepelin')
            
            kraepelinTable.css({ "display": 'revert'});
            this.$('.start_kraepelin').css({ "display": 'none'});
            this.$('.loading_span').css({ "display": 'none'});
            this.$('button[type="submit"]').css({ "display": 'revert'});
            $('.o_survey_form').css({ "margin-left": '0'});

            if (kraepelinTable.outerWidth() < $(window).width()) {
                kraepelinTable.css({ "margin": 'auto'});
            } else {
                kraepelinTable.css({ "margin": 'initial'});
            }

            var timer = this.$('[class^="timer-"]');
            var timerValue1 = this.$('.timerValue-1');
            var totalSeconds = timerValue1.text()
            var formattedTime = this.formatTime(totalSeconds);
            timer.text(formattedTime)
            this.startTimer(1);
        },

        ButtonStartSurvey: function (event) {
            var self = this;
            setTimeout(function () {
                self.fadeInOutDelay = 400;
                self.ButtonStartKraepelin();
            }, 2000);
        },

        ButtonConfirmDoneResponse: function (event1) {
            var searchParams = new URLSearchParams(window.location.search)
            var $this = $(event1.target)
            var $parent = $($this.parents()[5])
            var self = this
            var $input = $parent.find('input[type="file"]');       
            var name = $input.attr('name')
            var file = $input[0].files[0]; 
            var reader = new FileReader();
            var params = {}
            if (file) {
                const reader = new FileReader();
                reader.onload = function(evt) { 
                  var route = "/survey/save/videofiles";
                  const metadata = `name: ${file.name}, type: ${file.type}, size: ${file.size}, contents:`;
                  const contents = evt.target.result;
                  params['base64'] = String(contents).split(',')[1]
                  params['file_name'] = file.name
                  params['question'] = name
                  params['applicant_id'] = searchParams.get('applicantId')
                  var submitPromise = self._rpc({
                            route: _.str.sprintf('%s/%s/%s', route, self.options.surveyToken, self.options.answerToken),
                            params: params,
                        });
                };
                reader.readAsDataURL(file);
              }
        },
        OpenQuestionPopup: function (event1) {
            console.log('adada0----')
            var this_js = this
            var $this = $(event1.target)
            var modalmodal = $($($($this).parent()).find('.modal_open_qustion_popup'))
            modalmodal.modal({backdrop: 'static', keyboard: false})


                
              // $('body').on('DOMSubtreeModified', function(){
                var youtube_player = $($($($this).parent()).find('.youtube_player'))
                var countdown = $($($($($this).parent()).find('.countdown')))
                var countdownduration = $($($($($this).parent()).find('.countdownduration')))
                var filevalue = $($($($($this).parent()).find('input[type="file"]')))

                var layeryoutube = false
                if(youtube_player.length==0 && !filevalue.val()){
                    $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 0.5);
                    $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "none");

                    // $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                    // $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                    $($($($this).parent()).find('.youtube_player')).css("display", "none");
                    $($($($this).parent()).find('.information_text_youtube')).css("display", "none");
                    $($($($this).parent()).find('.div_preparation_time')).css("display", "block");
                    
                    var prepare_time = $($($($this).parent()).find('.all_player')).data('preparation_time')
                    var durationtime = $($($($this).parent()).find('.all_player')).data('response_time')
                    var questionId = $($($($this).parent()).find('.all_player')).attr('id').replace('all_player_','')
                    var timer2 = prepare_time+":00";
                    // var timer2 = "00"+":05";
                    var timer2_ori = timer2
                    var interval = setInterval(function() {


                      var timer = timer2.split(':');
                      //by parsing integer, I avoid all extra string processing
                      var minutes = parseInt(timer[0], 10);
                      var seconds = parseInt(timer[1], 10);
                      --seconds;
                      minutes = (seconds < 0) ? --minutes : minutes;
                      if (minutes < 0) {
                        $($($($this).parent()).find('.div_preparation_time')).css("display", "none");
                        $($($($this).parent()).find('.vid1')).css("display", "block");
                        $($($($this).parent()).find('.div_response_record')).css("display", "flex");
                        $($($($this).parent()).find('.duration_record')).css("display", "block");
                        var video1 = $($($($this).parent()).find('.vid1'))[0]
                        var video3 = $($($($this).parent()).find('.vid3'))[0]
                        var closse =  $($($($this).parent()).find('.modal_close_qustion_popup'))[0]
                        var stop = $($($($this).parent()).find('.submit_done_response_record'))[0]
                        var submit_response_record = $($($($this).parent()).find('.submit_response_record'))[0]
                        var button_confirm_done_response = $($($($this).parents()[1]).find('.button_confirm_done_response'))[0]
                        var button_confirm_cancel_response = $($($($this).parents()[1]).find('.button_confirm_cancel_response'))[0]
                        var retry_response_record =  $($($($this).parents()[1]).find('.retry_response_record'))[0]
                        var input_file = $($($($this).parent()).find('input[type="file"]'))
                        var done_answering_record = $($($($this).parents()[1]).find('.done_answering_record'))[0]
                        $($($($this).parent()).find('.settingviews')).css("display", "none");
                        $($($($this).parent()).find('.textsettings')).css("display", "none");
                        this_js.callRecording1(done_answering_record,input_file,retry_response_record,video1,video3,closse,stop,submit_response_record,questionId,button_confirm_done_response,button_confirm_cancel_response)



                        var timer3 = durationtime+":00";
                        // var timer3 = "00"+":05";
                        var timer3_ori = timer3
                        var interval1 = setInterval(function() {


                          var timertimer = timer3.split(':');
                                if(countdownduration.html()) {
                                    timertimer = countdownduration.html().split(':')
                                }
                          //by parsing integer, I avoid all extra string processing
                          var minutes1 = parseInt(timertimer[0], 10);
                          var seconds1 = parseInt(timertimer[1], 10);
                          --seconds1;
                          minutes1 = (seconds1 < 0) ? --minutes1 : minutes1;
                          if (minutes1 < 0) {
                            $($($($this).parent()).find('.vid1')).css("display", "none");
                            $($($($this).parent()).find('.vid3')).css("display", "block");
                            $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                            $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                            $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                             countdownduration.html('00' + ':' + '00');
                             $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                            $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                          }
                          if (minutes1 < 0) clearInterval(interval1);
                          seconds1 = (seconds1 < 0) ? 59 : seconds1;
                          seconds1 = (seconds1 < 10) ? '0' + seconds1 : seconds1;
                          //minutes = (minutes < 10) ?  minutes : minutes;
                          countdownduration.html(minutes1 + ':' + seconds1);
                          timer3 = minutes1 + ':' + seconds1;
                          if (minutes1 < 0) {
                            countdownduration.html('00:00');
                            }

                        }, 1000);
                        $('.button_confirm_done_response').click(function(){
                            clearInterval(interval1);
                            $($($($this).parent()).find('.vid1')).css("display", "none");
                            $($($($this).parent()).find('.vid3')).css("display", "block");
                            $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                            $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                            $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                             countdownduration.html('00' + ':' + '00');
                             $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                            $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                            countdownduration.html('00:00');
                        })

                      }
                      if (minutes < 0) clearInterval(interval);
                      seconds = (seconds < 0) ? 59 : seconds;
                      seconds = (seconds < 10) ? '0' + seconds : seconds;
                      //minutes = (minutes < 10) ?  minutes : minutes;
                      countdown.html(minutes + ':' + seconds);
                      timer2 = minutes + ':' + seconds;
                      if (minutes < 0) {
                            countdown.html('00:00');
                            }

                    }, 1000);
                    $('.retry_response_record').click(function(){

                        $($($($this).parent()).find('.vid3')).css("display", "none");
                        $($($($this).parent()).find('.vid1')).css("display", "block");

       
                        $($($($this).parent()).find('.submit_response_record')).css("display", "none");
                        $($($($this).parent()).find('.done_answering_record')).css("display", "block");
                    })

                    $('.done_answering_record').click(function(){
                            $($($($this).parent()).find('.vid1')).css("display", "none");
                            $($($($this).parent()).find('.vid3')).css("display", "block");
                            $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                            var text = $($($($this).parent()).find('.retry_response_record')).text()
                            text = text.replace('Retry (','')
                            var number = text.replace(' retries left)','')
                            number-=1
                            var text = "Retry ("+number+" retries left)"
                            if (number==0){
                                $($($($this).parent()).find('.retry_response_record')).css("opacity", 1);
                                $($($($this).parent()).find('.retry_response_record')).css("pointer-events", "unset");
                            }
                                
                            $($($($this).parent()).find('.retry_response_record')).css("opacity", 1);
                            $($($($this).parent()).find('.retry_response_record')).css("pointer-events", "unset");
                             $($($($this).parent()).find('.submit_response_record')).css("display", "block");
           
  
                    })
                    
                    $('.start_response_record').click(function(){
                            clearInterval(interval);
                            $($($($this).parent()).find('.settingviews')).css("display", "none");
                            $($($($this).parent()).find('.textsettings')).css("display", "none");

                            $('.button_confirm_done_response').click(function(){
                                clearInterval(interval1);
                                $($($($this).parent()).find('.vid1')).css("display", "none");
                                $($($($this).parent()).find('.vid3')).css("display", "block");
                                $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                                $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                                $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                                 countdownduration.html('00' + ':' + '00');
                                 $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                                countdownduration.html('00:00');
                            })
                            $($($($this).parent()).find('.div_preparation_time')).css("display", "none");
                            $($($($this).parent()).find('.vid1')).css("display", "block");
                            $($($($this).parent()).find('.div_response_record')).css("display", "flex");
                            $($($($this).parent()).find('.duration_record')).css("display", "block");
                            var video1 = $($($($this).parent()).find('.vid1'))[0]
                            var video3 = $($($($this).parent()).find('.vid3'))[0]
                            var closse =  $($($($this).parent()).find('.modal_close_qustion_popup'))[0]
                            var stop = $($($($this).parent()).find('.submit_done_response_record'))[0]
                            var submit_response_record = $($($($this).parent()).find('.submit_response_record'))[0]
                            var button_confirm_done_response = $($($($this).parents()[1]).find('.button_confirm_done_response'))[0]
                            var button_confirm_cancel_response = $($($($this).parents()[1]).find('.button_confirm_cancel_response'))[0]
                            var retry_response_record =  $($($($this).parents()[1]).find('.retry_response_record'))[0]
                            var input_file = $($($($this).parent()).find('input[type="file"]'))
                            var done_answering_record = $($($($this).parents()[1]).find('.done_answering_record'))[0]

                            this_js.callRecording1(done_answering_record,input_file,retry_response_record,video1,video3,closse,stop,submit_response_record,questionId,button_confirm_done_response,button_confirm_cancel_response)



                            var timer3 = durationtime+":00";
                            // var timer3 = "00"+":05";
                            var timer3_ori = timer3
                            var interval1 = setInterval(function() {
                                var timertimer = timer3.split(':');
                                if(countdownduration.html()) {
                                    timertimer = countdownduration.html().split(':')
                                }
                              
                              //by parsing integer, I avoid all extra string processing
                              var minutes1 = parseInt(timertimer[0], 10);
                              var seconds1 = parseInt(timertimer[1], 10);
                              --seconds1;
                              minutes1 = (seconds1 < 0) ? --minutes1 : minutes1;
                              if (minutes1 < 0) {
                                $($($($this).parent()).find('.vid1')).css("display", "none");
                                $($($($this).parent()).find('.vid3')).css("display", "block");
                                $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                                $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                                $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                                 countdownduration.html('00' + ':' + '00');
                                 $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                              }
                              if (minutes1 < 0) clearInterval(interval1);
                              seconds1 = (seconds1 < 0) ? 59 : seconds1;
                              seconds1 = (seconds1 < 10) ? '0' + seconds1 : seconds1;
                              //minutes = (minutes < 10) ?  minutes : minutes;
                              countdownduration.html(minutes1 + ':' + seconds1);
                              timer3 = minutes1 + ':' + seconds1;
                              if (minutes1 < 0) {
                                countdownduration.html('00:00');
                                }

                            }, 1000);
                        })

                }
                  if(youtube_player.length>0 && !filevalue.val()){
                        var video_src = youtube_player.attr('src')
                        var video_id = youtube_player.attr('id')
                        var regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=|\?v=)([^#\&\?]*).*/;
                        var match = video_src.match(regExp);
                        if (match && match[2].length == 11) {
                            video_src =  match[2];
                        }

                        if (typeof(YT) == 'undefined' || typeof(YT.Player) == 'undefined') {
                            var tag = document.createElement('script');
                            tag.src = "https://www.youtube.com/iframe_api";
                            var firstScriptTag = document.getElementsByTagName('script')[0];
                            firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
                        }
                            
                        $.getScript("https://www.youtube.com/iframe_api", function() {
                            window.YT.ready(function() {
                                layeryoutube = new YT.Player(video_id, { 
                                    height: '400',
                                    width: '800',
                                    rel:0,
                                    controls:0,
                                    showinfo:0,
                                    rel:0,
                                    videoId: video_src,
                                    events: {
                                        'onReady': onPlayerReady
                                    }
                                });
                            });
                        });
                        

                        function onPlayerReady(event) {
                 
                            layeryoutube.addEventListener('onStateChange', function(e) {

                                if (e.data==2){
             
                                    event.target.playVideo();
                                  
                                }
                                else if (e.data==1 || e.data==-1 || e.data==3 || e.data==5) {
                               
                                        $($($($this).parent()).find('.youtube_player')).css("pointer-events", "none");
                            
                             
                                    

                                    $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 0.5);
                                    $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "none");
                                }
                                else if (e.data==0) {
                                    // $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                    // $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                                    $($($($this).parent()).find('.youtube_player')).css("display", "none");
                                    $($($($this).parent()).find('.information_text_youtube')).css("display", "none");
                                    $($($($this).parent()).find('.div_preparation_time')).css("display", "block");
                                    
                                    var prepare_time = $($($($this).parent()).find('.all_player')).data('preparation_time')
                                    var durationtime = $($($($this).parent()).find('.all_player')).data('response_time')
                                    var questionId = $($($($this).parent()).find('.all_player')).attr('id').replace('all_player_','')
                                    var timer2 = prepare_time+":00";
                                    // var timer2 = "00"+":05";
                                    var timer2_ori = timer2
                                    var interval = setInterval(function() {


                                      var timer = timer2.split(':');
                                      //by parsing integer, I avoid all extra string processing
                                      var minutes = parseInt(timer[0], 10);
                                      var seconds = parseInt(timer[1], 10);
                                      --seconds;
                                      minutes = (seconds < 0) ? --minutes : minutes;
                                      if (minutes < 0) {
                                        $($($($this).parent()).find('.div_preparation_time')).css("display", "none");
                                        $($($($this).parent()).find('.vid1')).css("display", "block");
                                        $($($($this).parent()).find('.div_response_record')).css("display", "flex");
                                        $($($($this).parent()).find('.duration_record')).css("display", "block");
                                        var video1 = $($($($this).parent()).find('.vid1'))[0]
                                        var video3 = $($($($this).parent()).find('.vid3'))[0]
                                        var closse =  $($($($this).parent()).find('.modal_close_qustion_popup'))[0]
                                        var stop = $($($($this).parent()).find('.submit_done_response_record'))[0]
                                        var submit_response_record = $($($($this).parent()).find('.submit_response_record'))[0]
                                        var button_confirm_done_response = $($($($this).parents()[1]).find('.button_confirm_done_response'))[0]
                                        var button_confirm_cancel_response = $($($($this).parents()[1]).find('.button_confirm_cancel_response'))[0]
                                        var retry_response_record =  $($($($this).parents()[1]).find('.retry_response_record'))[0]
                                        var input_file = $($($($this).parent()).find('input[type="file"]'))
                                        var done_answering_record = $($($($this).parents()[1]).find('.done_answering_record'))[0]
                                        this_js.callRecording1(done_answering_record,input_file,retry_response_record,video1,video3,closse,stop,submit_response_record,questionId,button_confirm_done_response,button_confirm_cancel_response)


                                        var timer3 = durationtime+":00";
                                        // var timer3 = "00"+":05";
                                        var timer3_ori = timer3
                                        var interval1 = setInterval(function() {


                                          var timertimer = timer3.split(':');
                                if(countdownduration.html()) {
                                    timertimer = countdownduration.html().split(':')
                                }
                                          //by parsing integer, I avoid all extra string processing
                                          var minutes1 = parseInt(timertimer[0], 10);
                                          var seconds1 = parseInt(timertimer[1], 10);
                                          --seconds1;
                                          minutes1 = (seconds1 < 0) ? --minutes1 : minutes1;
                                          if (minutes1 < 0) {
                                            $($($($this).parent()).find('.vid1')).css("display", "none");
                                            $($($($this).parent()).find('.vid3')).css("display", "block");
                                            $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                                            $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                                            $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                                             countdownduration.html('00' + ':' + '00');
                                             $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                            $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                                          }
                                          if (minutes1 < 0) clearInterval(interval1);
                                          seconds1 = (seconds1 < 0) ? 59 : seconds1;
                                          seconds1 = (seconds1 < 10) ? '0' + seconds1 : seconds1;
                                          //minutes = (minutes < 10) ?  minutes : minutes;
                                          countdownduration.html(minutes1 + ':' + seconds1);
                                          timer3 = minutes1 + ':' + seconds1;
                                          if (minutes1 < 0) {
                                            countdownduration.html('00:00');
                                            }

                                        }, 1000);
                                        $('.button_confirm_done_response').click(function(){
                                            clearInterval(interval1);
                                            $($($($this).parent()).find('.vid1')).css("display", "none");
                                            $($($($this).parent()).find('.vid3')).css("display", "block");
                                            $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                                            $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                                            $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                                             countdownduration.html('00' + ':' + '00');
                                             $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                            $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                                            countdownduration.html('00:00');
                                        })


                                      }
                                      if (minutes < 0) clearInterval(interval);
                                      seconds = (seconds < 0) ? 59 : seconds;
                                      seconds = (seconds < 10) ? '0' + seconds : seconds;
                                      //minutes = (minutes < 10) ?  minutes : minutes;
                                      countdown.html(minutes + ':' + seconds);
                                      timer2 = minutes + ':' + seconds;
                                      if (minutes < 0) {
                                            countdown.html('00:00');
                                            }

                                    }, 1000);

                                    $('.retry_response_record').click(function(){



                                            $($($($this).parent()).find('.vid3')).css("display", "none");
                                            $($($($this).parent()).find('.vid1')).css("display", "block");

                                            $($($($this).parent()).find('.submit_response_record')).css("display", "none");
                                            $($($($this).parent()).find('.done_answering_record')).css("display", "block");
                                            $($($($this).parent()).find('.retry_response_record')).css("pointer-events", "none");
                                            $($($($this).parent()).find('.retry_response_record')).css("opacity",0.7);
                                        })

                                        $('.done_answering_record').click(function(){
                                                $($($($this).parent()).find('.vid1')).css("display", "none");
                                                $($($($this).parent()).find('.vid3')).css("display", "block");
                                                $($($($this).parent()).find('.submit_done_response_record'))[0].click()

                                                var text = $($($($this).parent()).find('.retry_response_record')).text()
                                                text = text.replace('Retry (','')
                                                var number = text.replace(' retries left)','')
                                                number-=1
                                                var text = "Retry ("+number+" retries left)"
                                                if (number==0){
                                                    $($($($this).parent()).find('.retry_response_record')).css("opacity", 1);
                                                    $($($($this).parent()).find('.retry_response_record')).css("pointer-events", "unset");
                                                }
                                                    


                                                 $($($($this).parent()).find('.submit_response_record')).css("display", "block");
                                                 countdownduration.html('00:00');

                               
                      
                                        })
                                        
                                        $('.start_response_record').click(function(){
                                                clearInterval(interval);

                                                $('.button_confirm_done_response').click(function(){
                                                    clearInterval(interval1);
                                                    $($($($this).parent()).find('.vid1')).css("display", "none");
                                                    $($($($this).parent()).find('.vid3')).css("display", "block");
                                                    $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                                                    $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");
                                                    $($($($this).parent()).find('.block_if_count_null')).css("pointer-events", "none");
                                                     countdownduration.html('00' + ':' + '00');
                                                     $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                                    $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                                                    countdownduration.html('00:00');
                                                })
                                                $($($($this).parent()).find('.div_preparation_time')).css("display", "none");
                                                $($($($this).parent()).find('.vid1')).css("display", "block");
                                                $($($($this).parent()).find('.div_response_record')).css("display", "flex");
                                                $($($($this).parent()).find('.duration_record')).css("display", "block");
                                                var video1 = $($($($this).parent()).find('.vid1'))[0]
                                                var video3 = $($($($this).parent()).find('.vid3'))[0]
                                                var closse =  $($($($this).parent()).find('.modal_close_qustion_popup'))[0]
                                                var stop = $($($($this).parent()).find('.submit_done_response_record'))[0]
                                                var submit_response_record = $($($($this).parent()).find('.submit_response_record'))[0]
                                                var button_confirm_done_response = $($($($this).parents()[1]).find('.button_confirm_done_response'))[0]
                                                var button_confirm_cancel_response = $($($($this).parents()[1]).find('.button_confirm_cancel_response'))[0]
                                                var retry_response_record =  $($($($this).parents()[1]).find('.retry_response_record'))[0]
                                                var input_file = $($($($this).parent()).find('input[type="file"]'))
                                                var done_answering_record = $($($($this).parents()[1]).find('.done_answering_record'))[0]

                                                this_js.callRecording1(done_answering_record,input_file,retry_response_record,video1,video3,closse,stop,submit_response_record,questionId,button_confirm_done_response,button_confirm_cancel_response)



                                                var timer3 = durationtime+":00";
                                                // var timer3 = "00"+":05";
                                                var timer3_ori = timer3
                                                var interval1 = setInterval(function() {


                                                  var timertimer = timer3.split(':');
                                                    if(countdownduration.html()) {
                                                        timertimer = countdownduration.html().split(':')
                                                    }
                                                  //by parsing integer, I avoid all extra string processing
                                                  var minutes1 = parseInt(timertimer[0], 10);
                                                  var seconds1 = parseInt(timertimer[1], 10);
                                                  --seconds1;
                                                  minutes1 = (seconds1 < 0) ? --minutes1 : minutes1;
                                                  if (minutes1 < 0) {
                                                    $($($($this).parent()).find('.vid1')).css("display", "none");
                                                    $($($($this).parent()).find('.vid3')).css("display", "block");
                                                    $($($($this).parent()).find('.submit_done_response_record'))[0].click()
                                                    // $($($($this).parent()).find('.div_response_record a')).css("opacity", "0.7");

                                                    var text = $($($($this).parent()).find('.retry_response_record')).text()
                                                    text = text.replace('Retry (','')
                                                    var number = text.replace(' retries left)','')
                                                    if (number !=0){
                                                        $($($($this).parent()).find('.retry_response_record')).css("opacity", 1);
                                                        $($($($this).parent()).find('.retry_response_record')).css("pointer-events", "unset");
                                                    }

                                                     countdownduration.html('00' + ':' + '00');
                                                    //  $($($($this).parent()).find('.modal_close_qustion_popup')).css("opacity", 1);
                                                    // $($($($this).parent()).find('.modal_close_qustion_popup')).css("pointer-events", "unset");
                                                  }
                                                //   if (minutes1 < 0) clearInterval(interval1);
                                                  seconds1 = (seconds1 < 0) ? 59 : seconds1;
                                                  seconds1 = (seconds1 < 10) ? '0' + seconds1 : seconds1;
                                                  //minutes = (minutes < 10) ?  minutes : minutes;
                                                  countdownduration.html(minutes1 + ':' + seconds1);
                                                  timer3 = minutes1 + ':' + seconds1;
                                                  if (minutes1 < 0) {
                                                    countdownduration.html('00:00');
                                                    }

                                                }, 1000);
                                            })
                         

                                }
                            });
                          }
                    
                      }
                // });
              
        },

        callRecording1: function (done_answering_record,input_file,retry_response_record,video1,video3,closse,stop,submit_response_record,questionId,button_confirm_done_response,button_confirm_cancel_response) {
            let constraintObj = { 
                audio: true, 
                video: { 
                    facingMode: "user", 
                    width: { min: 800, ideal: 800, max: 800 },
                    height: { min: 350, ideal: 350, max: 350 } 
                } 
            }; 
            // width: 1280, height: 720  -- preference only
            // facingMode: {exact: "user"}
            // facingMode: "environment"
            
            //handle older browsers that might implement getUserMedia in some way
            if (navigator.mediaDevices === undefined) {
                navigator.mediaDevices = {};
                navigator.mediaDevices.getUserMedia = function(constraintObj) {
                    let getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
                    if (!getUserMedia) {
                        return Promise.reject(new Error('getUserMedia is not implemented in this browser'));
                    }
                    return new Promise(function(resolve, reject) {
                        getUserMedia.call(navigator, constraintObj, resolve, reject);
                    });
                }
            }else{
                navigator.mediaDevices.enumerateDevices()
                .then(devices => {
                    devices.forEach(device=>{
                        console.log(device.kind.toUpperCase(), device.label);
                        //, device.deviceId
                    })
                })
                .catch(err=>{
                    console.log(err.name, err.message);
                })
            }

            navigator.mediaDevices.getUserMedia(constraintObj)
            .then(function(mediaStreamObj) {
                //connect the media stream to the first video element
                // var stream = mediaStreamObj;
                //      var tracks = stream.getTracks();
                //       tracks.forEach((track) => {
                //         track.start();
                //       });
                let video = video1;
                if ("srcObject" in video) {
                    video.srcObject = mediaStreamObj;
                } else {
                    //old version
                    video.src = window.URL.createObjectURL(mediaStreamObj);
                }
                
                video.onloadedmetadata = function(ev) {
                    //show in the video element what is being captured by the webcam
                    video.play();
                };
                
                //add listeners for saving video/audio
   
                let vidSave = video3;
              

                let mediaRecorder = new MediaRecorder(mediaStreamObj);
                let chunks = [];
                
                mediaRecorder.start();

                retry_response_record.addEventListener('click', (ev)=>{
                    var text = $(retry_response_record).text()
                    text = text.replace('Retry (','')
                    var number = text.replace(' retries left)','')
                    number-=1
                    var text = "Retry ("+number+" retries left)"
                    if (parseInt(number)==0) {
                        $(retry_response_record).css("opacity", "0.7");
                        $(retry_response_record).css("pointer-events", "none");

                    }
                    var countdownduration  = $($($(retry_response_record).parents()[1]).find('.countdownduration'))
                    var videoplay  = $($($(retry_response_record).parents()[1]).find('.vid3'))
                    var durationtime = $($($(retry_response_record).parents()[3]).find('.all_player')).data('response_time')
                    countdownduration.html(durationtime+':00');
                    $(retry_response_record).text(text)
                    if(mediaRecorder.state!='inactive') {
                        mediaRecorder.stop();
                        setTimeout(function () {
                            mediaRecorder.start();
                            }, 1000);     
                    }
                    else{
                        mediaRecorder.start();
                    }
                    // if ( !videoplay[0].paused ) {
                        setTimeout(function () {
                            videoplay.trigger('pause');
                            }, 1000); 
                    // }
                    
                    
                });

                submit_response_record.addEventListener('click', (ev)=>{
                 
                    $('#modal_all_player_'+questionId).modal()
                    
                });
                button_confirm_cancel_response.addEventListener('click', (ev)=>{
  
                    $('#modal_all_player_'+questionId).modal('toggle')
                    
                });
                button_confirm_done_response.addEventListener('click', (ev)=>{
  
                    $('#modal_all_player_'+questionId).modal('toggle')
                    
                });
                stop.addEventListener('click', (ev)=>{

                    if(mediaRecorder.state!='inactive') {
                        mediaRecorder.stop();
                    }
                        
                    
                });

                done_answering_record.addEventListener('click', (ev)=>{
                    if(mediaRecorder.state!='inactive') {
                        mediaRecorder.stop();
                    }
                    $(done_answering_record).hide();
                    $(retry_response_record).css("visibility", "unset");
                    $(submit_response_record).css("visibility", "unset");
                    

                    
                });

                closse.addEventListener('click', (ev)=>{
                    var stream = mediaStreamObj;
                     var tracks = stream.getTracks();
                      tracks.forEach((track) => {
                        track.stop();
                      });
                    
                });
                mediaRecorder.ondataavailable = function(ev) {
                    chunks.push(ev.data);
                }
                mediaRecorder.onstop = (ev)=>{
                    console.log('onstoponstoponstoponstop')
                    let blob = new Blob(chunks ,{ 'type' : 'video/mp4;' });
                    chunks = [];
                    let file = new File([blob], "youtube.mp4",{type:"mime/type", lastModified:new Date().getTime()});
                    let container1 = new DataTransfer();
                    container1.items.add(file);
                    input_file[0].files = container1.files;
                    let videoURL = window.URL.createObjectURL(blob);
                    vidSave.src = videoURL;
                    vidSave.play()
                }
            })
            .catch(function(err) { 
                console.log(err.name, err.message); 
            });
        },

        _submitForm: function (options) {

            
              
            var self = this;
            var params = {};
            if (options.previousPageId) {
                params.previous_page_id = options.previousPageId;
            }

            const queryString = window.location.search;
            const urlParams = new URLSearchParams(queryString);
            params['survey_id'] = parseInt(urlParams.get('surveyId'));
            params['applicant_id'] = parseInt(urlParams.get('applicantId'));
            params['job_position'] = parseInt(urlParams.get('jobPosition'));
            params['training_id'] = parseInt(urlParams.get('trainingId'));
            params['employee_id'] = parseInt(urlParams.get('employeeId'));
            params['test_type'] = parseInt(urlParams.get('testType'));


            var route = "/survey/submit";

            if (this.options.isStartScreen) {
                route = "/survey/begin";
                // Hide survey title in 'page_per_question' layout: it takes too much space
                if (this.options.questionsLayout === 'page_per_question') {
                    this.$('.o_survey_main_title').fadeOut(400);
                }
            } else {
                var $form = this.$('form');
                var formData = new FormData($form[0]);

                if (!options.skipValidation) {
                    // Validation pre submit
                    if (!this._validateForm($form, formData)) {
                        return;
                    }
                }

                this._prepareSubmitValues(formData, params);
            }

            // prevent user from submitting more times using enter key
            this.preventEnterSubmit = true;

            if (this.options.sessionInProgress) {
                // reset the fadeInOutDelay when attendee is submitting form
                this.fadeInOutDelay = 400;
                // prevent user from clicking on matrix options when form is submitted
                this.readonly = true;
            }

            var submitPromise = self._rpc({
                route: _.str.sprintf('%s/%s/%s', route, self.options.surveyToken, self.options.answerToken),
                params: params,
            });
            this._nextScreen(submitPromise, options);
            console.log('next page 2')
            
            var timerIntervalSubmit = setInterval(function() {
                if ($(".start_kraepelin")[0]){
                    self.$('button.button_submit_survey_fill').css({ "display": 'none'});
                    self.$('span.d-md-inline').removeClass('d-md-inline').css({ "display": 'none'});
                    self.ButtonStartSurvey()
                    clearInterval(timerIntervalSubmit);
                }
            }, 500);
            
            // this.callRecording1()
            
        }


    });

    return {
        DataSet: DataSet,
    };


});



