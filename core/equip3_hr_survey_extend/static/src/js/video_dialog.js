odoo.define('wysiwyg.widgets.VideoDialog', function (require) {
    'use strict';

    var core = require('web.core');
    var Dialog = require('wysiwyg.widgets.Dialog');

    var _t = core._t;
    var recordedBlobs = [];
    /**
     * Allows to customize video content and style.
     */

    var VideoDialog = Dialog.extend({
        template: 'wysiwyg.widget.video',
        xmlDependencies: (Dialog.prototype.xmlDependencies || []).concat([
            '/web_elearning_video/static/src/xml/wysiwyg.xml'
        ]),
        events: {
            'click .note-record-btn': '_onClickStart',
            'click .note-pause-btn': '_onClickPause',
            'click .note-retry-btn': '_onClickStart',
            'click .note-continue-btn': '_onClickContinue',
            'click .note-record-done-btn': '_onClickDone',
            'click .note-video-play': '_onPlayVideo',
            'click .note-video-download': '_onDownloadVideo',
            'click #video_setting_survey': '_onClickSetting', 
            'click .done_config_testing': '_onClickDoneConfig', 
            'click #test_speaker_audio': '_onClickPlayTestSound', 
            'click #config_mic_test': '_onClickRecordTestSound', 
            'click #config_cam_test': '_onClickRecordTestCamera', 
            'click #button_stop_test_camera': '_onClickCloseTestCamera', 

        },

        /**
         * @constructor
         */
        init: function (parent, media, editable) {
            this._super(parent, _.extend({}, {
                title: _t("Add Video")
            }, {}));
            this.constraints = { audio: true, video: true };
            this.mediaRecorder;
            this.media = media;
            this.editable = editable;

            this.seconds = 0;
            this.minutes = 0;
            this.hours = 0;
            this.timerInterval = null;
        },
        start: function () {
            recordedBlobs = []
            this.gumVideo = this.$('video.gum').get(0);
            this.gumVideo2 = this.$('video.gum');
            this.startButton = this.$('button.note-record-btn');
            this.doneButton = this.$('button.note-record-done-btn');
            this.playButton = this.$('button.note-video-play');
            this.pauseButton = this.$('button.note-pause-btn');
            this.downloadButton = this.$('button.note-video-download');
            this.recordedVideo = this.$('video.note-video-input');
            this.retryButton = this.$('button.note-retry-btn');
            this.continueButton = this.$('button.note-continue-btn');
            this.timerBackground = this.$('div.timer-background');
            this.timer = this.$('div.timer');
            this.textsettings = this.$('p.textsettings');
            this.settingviews = this.$('div.settingviews');

            this.gumVideo2.css({ "display": 'none', 'width': '54%', 'margin': 'auto'});
            this.recordedVideo.css({ "display": 'none', 'width': '54%', 'margin': 'auto'});
            this.retryButton.css({ "display": 'none'});
            this.continueButton.css({ "display": 'none'});
            this.pauseButton.css({ "display": 'none'});
            this.doneButton.css({ "display": 'none'});
            this.playButton.css({ "display": 'none'});
            this.downloadButton.css({ "display": 'none'});
            this.timerBackground.css({ "display": "none", "position": 'absolute', 'left': '23%', 'right': '23%', 'background-color': 'lightgray', 'opacity': '50%', 'padding': '20px'});
            this.timer.css({ "display": "none", 'font-weight': 'bold', 'font-size': '20px', 'text-align': 'center', 'position': 'absolute', 'left': '47%', 'color': 'white', 'margin-top': '5px'});

            var self = this;
            navigator.mediaDevices.getUserMedia(this.constraints)
                .then(stream => {
                    self.gumVideo.srcObject = stream;
                    window.stream = stream;
                })
                .catch(error => {
                    alert('Error accessing media devices.', error);
                });
        },

        _onClickSetting: function(ev) {
            this.$('div.modal_recording').css({ "display": 'none'});
            $('footer.modal-footer').css({ "display": 'none'});
            $('div#modal_video_setting_survey').css({ "display": 'initial'});
            // $('#modal_video_setting_survey').modal({backdrop: 'static', keyboard: false})
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
            // start();
        },

        _onClickDoneConfig: function (ev) {
            this.$('div#modal_video_setting_survey').css({ "display": 'none'});
            this.$('div.modal_recording').css({ "display": 'initial'});
            $('footer.modal-footer').css({ "display": 'initial'});

            // Stop Play Test Sound
            var audioElement = document.getElementById("audio-playback1");
            audioElement.pause();
            $('#test_speaker_audio .fa').addClass('fa-play')
            $('#test_speaker_audio .fa').removeClass('fa-stop')
        },

        _onClickPlayTestSound: function (ev) {
            ev.preventDefault();
            var audioElement = document.getElementById("audio-playback1");
            audioElement.currentTime = 0;
            if ($('#test_speaker_audio .fa').hasClass('fa-play')) {
                audioElement.play();
                $('#test_speaker_audio .fa').removeClass('fa-play')
                $('#test_speaker_audio .fa').addClass('fa-stop')
            } else {
                audioElement.pause();
                $('#test_speaker_audio .fa').addClass('fa-play')
                $('#test_speaker_audio .fa').removeClass('fa-stop')
            }
        },

        _onClickRecordTestSound: function (ev) {
            ev.preventDefault();
            let recorder, audio_stream;
            const downloadAudio = document.getElementById("downloadButton");
            const recordButton = document.getElementById("config_mic_test");
            const preview = document.getElementById("audio-playback");
            if ($('#config_mic_test .fa').hasClass('fa-stop')) {
                $('#config_mic_test .fa').addClass('fa-microphone')
                $('#config_mic_test .fa').removeClass('fa-stop')
                preview.pause();
            }
            
            else if ($('#config_mic_test .fa').hasClass('fa-microphone')) {
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

                        var timeout_status = setTimeout(function () {
                            $('#config_mic_test .fa').addClass('fa-microphone')
                            $('#config_mic_test .fa').removeClass('fa-stop')
                            $('#config_mic_test .fa').removeClass('fa-circle')                      
                        }, 7000);
                    });
                $('#config_mic_test .fa').removeClass('fa-microphone')
                $('#config_mic_test .fa').addClass('fa-circle')
            }
        },

        _onClickRecordTestCamera: function (ev) {
            ev.preventDefault();

            this.$('div.video_setting_body').css({ "display": 'none'});
            this.$('div.modal-footer').css({ "display": 'none'});

            this.gumVideo2.css({ "display": 'initial'});
            this.$('div.test_camera_footer').css({ "display": 'flex'});
        },

        _onClickCloseTestCamera: function (ev) {
            ev.preventDefault();

            this.$('div.video_setting_body').css({ "display": 'initial'});
            this.$('div.modal-footer').css({ "display": 'flex'});

            this.gumVideo2.css({ "display": 'none'});
            this.$('div.test_camera_footer').css({ "display": 'none'});
        },

        _onClickPause: function (ev) {
            this.mediaRecorder.pause();
            this._stopTimer();

            this.pauseButton.css({ "display": 'none'});
            this.continueButton.css({ "display": 'initial'});
        },

        _onClickContinue: function (ev) {
            this.mediaRecorder.resume();
            this._startTimer();

            this.pauseButton.css({ "display": 'initial'});
            this.continueButton.css({ "display": 'none'});
        },

        _onClickStart: function (ev) {
            var self = this;
            recordedBlobs = []
            var options = { mimeType: 'video/webm;codecs=vp9', bitsPerSecond: 100000 };
            try {
                this.mediaRecorder = new MediaRecorder(window.stream, options);
            } catch (e0) {
                console.log('Unable to create MediaRecorder with options Object: ', options, e0);
                try {
                    options = { mimeType: 'video/webm;codecs=vp8', bitsPerSecond: 100000 };
                    this.mediaRecorder = new MediaRecorder(window.stream, options);
                } catch (e1) {
                    console.log('Unable to create MediaRecorder with options Object: ', options, e1);
                    try {
                        options = 'video/mp4';
                        this.mediaRecorder = new MediaRecorder(window.stream, options);
                    } catch (e2) {
                        alert('MediaRecorder is not supported by this browser.');
                        console.error('Exception while creating MediaRecorder:', e2);
                        return;
                    }
                }
            }

            this.doneButton.get(0).disabled = false;

            this.startButton.css({ "display": 'none'});
            this.retryButton.css({ "display": 'none'});
            this.recordedVideo.css({ "display": 'none'});
            this.textsettings.css({ "display": 'none'});
            this.settingviews.css({ "display": 'none'});
            this.gumVideo2.css({ "display": 'initial'});
            this.pauseButton.css({ "display": 'initial'});
            this.doneButton.css({ "display": 'initial'});
            this.timerBackground.css({ "display": 'initial'});
            this.timer.css({ "display": 'initial'});

            ev.currentTarget.disabled = true;
            this.mediaRecorder.ondataavailable = self.handleDataAvailable;
            this.mediaRecorder.start(10);
            this._resetTimer();
            this._startTimer();
        },

        _startTimer: function () {
            this.timer.css({'background-color': 'red'});
            var self = this;
            this.timerInterval = setInterval(function () {
                self._updateTimer();
            }, 1000);
        },

        _updateTimer: function () {
            this.seconds++;
            if (this.seconds >= 60) {
                this.seconds = 0;
                this.minutes++;
                if (this.minutes >= 60) {
                    this.minutes = 0;
                    this.hours++;
                }
            }
            this.timer.text(this._formatTime(this.hours, this.minutes, this.seconds));
        },

        _stopTimer: function () {
            this.timer.css({'background-color': 'darkgrey'});
            clearInterval(this.timerInterval);
        },

        _resetTimer: function () {
            this.seconds = 0;
            this.minutes = 0;
            this.hours = 0;
            this.timer.text("00:00:00");
        },

        _formatTime: function (hours, minutes, seconds) {
            return (hours ? (hours > 9 ? hours : "0" + hours) : "00") +
                ":" +
                (minutes ? (minutes > 9 ? minutes : "0" + minutes) : "00") +
                ":" +
                (seconds > 9 ? seconds : "0" + seconds);
        },

        _onClickDone: function (ev) {
            this.mediaRecorder.stop();
            this._stopTimer();
            ev.currentTarget.disabled = true;

            //PlayVideo
            var type = (recordedBlobs[0] || {}).type;
            var superBuffer = new Blob(recordedBlobs, { type });
            this.recordedVideo.get(0).src = window.URL.createObjectURL(superBuffer);

            this.retryButton.get(0).disabled = false;

            this.gumVideo2.css({ "display": 'none'});
            this.pauseButton.css({ "display": 'none'});
            this.continueButton.css({ "display": 'none'});
            this.doneButton.css({ "display": 'none'});
            this.retryButton.css({ "display": 'initial'});
            this.recordedVideo.css({ "display": 'initial'});
            this.timerBackground.css({ "display": 'none'});
            this.timer.css({ "display": 'none'});

        },

        handleDataAvailable: function (event) {
            if (event.data && event.data.size > 0) {
                recordedBlobs.push(event.data);
            }
        },

        _onPlayVideo: function (ev) {
            var type = (recordedBlobs[0] || {}).type;
            var superBuffer = new Blob(recordedBlobs, { type });
            this.recordedVideo.get(0).src = window.URL.createObjectURL(superBuffer);
        },

        _onDownloadVideo: function (ev) {
            var blob = new Blob(recordedBlobs, { type: 'video/webm' });
            var url = window.URL.createObjectURL(blob);
            var a = document.createElement('a');
            a.style.display = 'none';
            a.href = url;
            a.download = 'recording.webm';
            document.body.appendChild(a);
            a.click();
            setTimeout(function () {
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            }, 100);
        },

        save: async function () {
            if (recordedBlobs.length !== 0) {
                const attachmentObj = await this.addAttachment();
                this.recordedVideo.get(0).removeAttribute('src');
                this.recordedVideo.get(0).load();
                if (typeof (window.stream) == "object") {
                    window.stream.getTracks().forEach((track) => {
                        track.stop();
                    });
                }
                this.final_data = attachmentObj;
                let url = window.location.origin + '/web/content/' + attachmentObj.id + '?controls=1';
                let videoUrl = `
                    <div class="media_iframe_video iframe_custom o_we_selected_image">
                        <div class="media_iframe_video_size" contenteditable="false" style="padding-bottom:10px;">&nbsp;</div>
                        <video controls="controls">
                            <source src="${url}" type="video/webm" />
                        </video>
                    </div><br/>`;
                var pTag = this.editable.find('p');
                if (pTag.length > 1) {
                    pTag.last().append(videoUrl);
                } else {
                    pTag.append(videoUrl);
                }

                // create video
                var self = this
                var params = {}

                params['base64'] = attachmentObj.datas

                var route = "/interview/save/videofile";
                var submitPromise = self._rpc({
                    route: _.str.sprintf('%s', route),
                    params: params,
                });
            }
            this.close();
        },

        destroy: function () {
            if (typeof (window.stream) == "object") {
                window.stream.getTracks().forEach((track) => {
                    track.stop();
                });
            }
            return this._super(...arguments);
        },

        blobToBase64: blob => {
            const reader = new FileReader();
            reader.readAsDataURL(blob);
            return new Promise(resolve => {
                reader.onloadend = () => {
                    resolve(reader.result);
                };
            });
        },

        addAttachment: async function () {
            let videoAttachment;
            if (recordedBlobs) {
                let type = (recordedBlobs[0] || {}).type;
                let superBuffer = new Blob(recordedBlobs, { type });
                const bs64Video = await this.blobToBase64(superBuffer)
                videoAttachment = await this._rpc({
                    route: '/web_editor/attachment/add_data',
                    params: {
                        'name': 'recording.webm',
                        'data': bs64Video.split(',')[2],
                        'res_id': $.summernote.options.res_id,
                        'res_model': $.summernote.options.res_model,
                    },
                })
            }
            return videoAttachment;
        }
    });
    return VideoDialog;
});